from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from ..services.db_service import run_query

router = APIRouter(prefix="/analytics", tags=["analytics"])

HAZARDOUS_THRESHOLD = 400.0


class DayAQIStat(BaseModel):
    date: date
    average_aqi: float


class CityStatsResponse(BaseModel):
    city: str
    days: int
    mean_aqi: float
    median_aqi: float
    max_aqi: float
    min_aqi: float
    worst_day: DayAQIStat
    best_day: DayAQIStat
    days_above_hazardous_threshold: int
    trend_direction: str
    trend_slope: float


class PollutantsBreakdownResponse(BaseModel):
    city: str
    days: int
    pollutant_averages: dict[str, float]


class CompareResponse(BaseModel):
    city1: str
    city2: str
    city1_stats: CityStatsResponse
    city2_stats: CityStatsResponse


class RankingItem(BaseModel):
    rank: int
    city: str
    average_aqi: float
    previous_month_average_aqi: float | None
    delta_vs_previous_month: float | None


class RankingResponse(BaseModel):
    days: int
    rankings: list[RankingItem]


def _safe_float(value) -> float:
    return float(value) if value is not None and not pd.isna(value) else float("nan")


def _trend_direction_from_slope(slope: float) -> str:
    if slope <= -0.2:
        return "improving"
    if slope >= 0.2:
        return "worsening"
    return "stable"


def _trend_direction_from_daily(daily: pd.DataFrame) -> tuple[str, float]:
    if daily.empty:
        return "stable", 0.0

    y = daily["average_aqi"].to_numpy(dtype=float)
    if len(y) >= 2:
        x = np.arange(len(y), dtype=float)
        slope = float(np.polyfit(x, y, 1)[0])
    else:
        slope = 0.0

    # Compare latest week to previous week for a more intuitive short-term trend.
    recent_avg = float(np.mean(y[-7:])) if len(y) >= 1 else float("nan")
    prior_avg = float(np.mean(y[-14:-7])) if len(y) >= 14 else float("nan")

    pct_change = 0.0
    if not np.isnan(prior_avg) and abs(prior_avg) > 1e-9:
        pct_change = ((recent_avg - prior_avg) / prior_avg) * 100.0

    if pct_change <= -3.0 or slope <= -0.15:
        return "improving", slope
    if pct_change >= 3.0 or slope >= 0.15:
        return "worsening", slope
    return "stable", slope


def _load_city_aqi(city: str, days: int) -> pd.DataFrame:
    return run_query(
        """
                SELECT
                        timestamp,
                        CASE
                                WHEN value <= 30 THEN value * 50.0 / 30
                                WHEN value <= 60 THEN 50 + (value - 30) * 50.0 / 30  -- sanity: pm25=60 => AQI=100
                                WHEN value <= 90 THEN 100 + (value - 60) * 100.0 / 30 -- sanity: pm25=90 => AQI=200
                                WHEN value <= 120 THEN 200 + (value - 90) * 100.0 / 30
                                WHEN value <= 250 THEN 300 + (value - 120) * 100.0 / 130
                                ELSE 400 + (value - 250) * 100.0 / 130
                        END AS aqi_value
        FROM measurements
        WHERE city = %s
                    AND parameter = %s
          AND timestamp >= (NOW() - INTERVAL %s DAY)
        ORDER BY timestamp ASC
        """,
                params=(city, "pm25", days),
    )


def _compute_city_stats(city: str, days: int) -> CityStatsResponse:
    df = _load_city_aqi(city, days)
    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No AQI records found for city '{city}' in the last {days} days.",
        )

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["aqi_value"] = pd.to_numeric(df["aqi_value"], errors="coerce")
    df = df.dropna(subset=["timestamp", "aqi_value"]).copy()

    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No valid AQI records found for city '{city}' in the last {days} days.",
        )

    daily = (
        df.assign(day=df["timestamp"].dt.date)
        .groupby("day", as_index=False)
        .agg(average_aqi=("aqi_value", "mean"))
        .sort_values("day")
    )

    worst = daily.loc[daily["average_aqi"].idxmax()]
    best = daily.loc[daily["average_aqi"].idxmin()]

    trend, slope = _trend_direction_from_daily(daily)
    hazardous_days = int((daily["average_aqi"] > HAZARDOUS_THRESHOLD).sum())

    return CityStatsResponse(
        city=city,
        days=days,
        mean_aqi=float(df["aqi_value"].mean()),
        median_aqi=float(df["aqi_value"].median()),
        max_aqi=float(df["aqi_value"].max()),
        min_aqi=float(df["aqi_value"].min()),
        worst_day=DayAQIStat(date=worst["day"], average_aqi=float(worst["average_aqi"])),
        best_day=DayAQIStat(date=best["day"], average_aqi=float(best["average_aqi"])),
        days_above_hazardous_threshold=hazardous_days,
        trend_direction=trend,
        trend_slope=slope,
    )


@router.get("/city/{city}/stats", response_model=CityStatsResponse, status_code=status.HTTP_200_OK)
def get_city_stats(city: str, days: int = Query(default=30, ge=1, le=365)) -> CityStatsResponse:
    try:
        return _compute_city_stats(city=city, days=days)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute city stats: {exc}",
        ) from exc


@router.get(
    "/city/{city}/pollutants",
    response_model=PollutantsBreakdownResponse,
    status_code=status.HTTP_200_OK,
)
def get_city_pollutants(city: str) -> PollutantsBreakdownResponse:
    try:
        df = run_query(
            """
            SELECT parameter, AVG(value) AS avg_value
            FROM measurements
            WHERE city = %s
              AND parameter IN ('pm25', 'pm10', 'no2', 'so2', 'co')
              AND timestamp >= (NOW() - INTERVAL 30 DAY)
            GROUP BY parameter
            """,
            params=(city,),
        )

        if df.empty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No pollutant records found for city '{city}' in the last 30 days.",
            )

        breakdown = {str(row["parameter"]): float(row["avg_value"]) for _, row in df.iterrows()}
        for pollutant in ["pm25", "pm10", "no2", "so2", "co"]:
            breakdown.setdefault(pollutant, 0.0)

        return PollutantsBreakdownResponse(city=city, days=30, pollutant_averages=breakdown)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute pollutant breakdown: {exc}",
        ) from exc


@router.get("/compare", response_model=CompareResponse, status_code=status.HTTP_200_OK)
def compare_cities(city1: str = Query(..., min_length=1), city2: str = Query(..., min_length=1)) -> CompareResponse:
    if city1.strip().lower() == city2.strip().lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="city1 and city2 must be different.",
        )

    try:
        city1_stats = _compute_city_stats(city=city1, days=30)
        city2_stats = _compute_city_stats(city=city2, days=30)
        return CompareResponse(
            city1=city1,
            city2=city2,
            city1_stats=city1_stats,
            city2_stats=city2_stats,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare cities: {exc}",
        ) from exc


@router.get("/ranking", response_model=RankingResponse, status_code=status.HTTP_200_OK)
def get_city_ranking() -> RankingResponse:
    try:
        ranking_df = run_query(
            """
            SELECT
                current_data.city,
                current_data.avg_aqi AS average_aqi,
                prev_data.avg_aqi AS previous_month_average_aqi,
                (current_data.avg_aqi - prev_data.avg_aqi) AS delta_vs_previous_month
            FROM (
                SELECT
                    city,
                    AVG(
                        CASE
                            WHEN value <= 30 THEN value * 50.0 / 30
                            WHEN value <= 60 THEN 50 + (value - 30) * 50.0 / 30  -- sanity: pm25=60 => AQI=100
                            WHEN value <= 90 THEN 100 + (value - 60) * 100.0 / 30 -- sanity: pm25=90 => AQI=200
                            WHEN value <= 120 THEN 200 + (value - 90) * 100.0 / 30
                            WHEN value <= 250 THEN 300 + (value - 120) * 100.0 / 130
                            ELSE 400 + (value - 250) * 100.0 / 130
                        END
                    ) AS avg_aqi
                FROM measurements
                WHERE parameter = 'pm25'
                  AND timestamp >= (NOW() - INTERVAL 30 DAY)
                GROUP BY city
            ) AS current_data
            LEFT JOIN (
                SELECT
                    city,
                    AVG(
                        CASE
                            WHEN value <= 30 THEN value * 50.0 / 30
                            WHEN value <= 60 THEN 50 + (value - 30) * 50.0 / 30  -- sanity: pm25=60 => AQI=100
                            WHEN value <= 90 THEN 100 + (value - 60) * 100.0 / 30 -- sanity: pm25=90 => AQI=200
                            WHEN value <= 120 THEN 200 + (value - 90) * 100.0 / 30
                            WHEN value <= 250 THEN 300 + (value - 120) * 100.0 / 130
                            ELSE 400 + (value - 250) * 100.0 / 130
                        END
                    ) AS avg_aqi
                FROM measurements
                WHERE parameter = 'pm25'
                  AND timestamp >= (NOW() - INTERVAL 60 DAY)
                  AND timestamp < (NOW() - INTERVAL 30 DAY)
                GROUP BY city
            ) AS prev_data
                ON current_data.city = prev_data.city
            ORDER BY current_data.avg_aqi DESC
            """
        )

        if ranking_df.empty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No AQI records found for ranking.",
            )

        rankings: list[RankingItem] = []
        for idx, row in ranking_df.reset_index(drop=True).iterrows():
            prev_avg = row["previous_month_average_aqi"]
            delta = row["delta_vs_previous_month"]

            rankings.append(
                RankingItem(
                    rank=idx + 1,
                    city=str(row["city"]),
                    average_aqi=float(row["average_aqi"]),
                    previous_month_average_aqi=None if pd.isna(prev_avg) else float(prev_avg),
                    delta_vs_previous_month=None if pd.isna(delta) else float(delta),
                )
            )

        return RankingResponse(days=30, rankings=rankings)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute city ranking: {exc}",
        ) from exc
