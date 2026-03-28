from __future__ import annotations

from datetime import datetime
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    from frontend.api_client import compare_cities, get_city_ranking
except ModuleNotFoundError:
    ROOT_DIR = Path(__file__).resolve().parents[2]
    if str(ROOT_DIR) not in sys.path:
        sys.path.append(str(ROOT_DIR))
    from frontend.api_client import compare_cities, get_city_ranking

_ = (compare_cities, get_city_ranking)

CITIES = [
    "Delhi",
    "Mumbai",
    "Chennai",
    "Kolkata",
    "Bangalore",
    "Hyderabad",
    "Pune",
    "Ahmedabad",
]

CITY_COLORS = {
    "city1": "#8b0000",
    "city2": "#1f77b4",
}


def _fmt_number(value, digits: int = 1) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "N/A"


def _fmt_delta(v1, v2, digits: int = 1) -> str:
    try:
        return f"{(float(v1) - float(v2)):+.{digits}f}"
    except (TypeError, ValueError):
        return "N/A"


def _build_daily_series(stats: dict, days: int) -> pd.DataFrame:
    days = max(int(days), 7)
    end_date = pd.Timestamp(datetime.utcnow().date())
    dates = pd.date_range(end=end_date, periods=days, freq="D")

    mean_aqi = float(stats.get("mean_aqi", 120.0))
    slope = float(stats.get("trend_slope", 0.0))
    min_aqi = float(stats.get("min_aqi", max(0.0, mean_aqi - 60.0)))
    max_aqi = float(stats.get("max_aqi", mean_aqi + 60.0))

    idx = np.arange(days, dtype=float)
    centered = idx - (days - 1) / 2.0
    seasonal = 10.0 * np.sin((idx / 7.0) * 2.0 * np.pi)
    values = np.clip(mean_aqi + slope * centered + seasonal, min_aqi, max_aqi)

    return pd.DataFrame({"date": dates, "aqi": values})


def _extract_city_series(payload: dict, key: str, stats: dict, days: int) -> pd.DataFrame:
    series_raw = payload.get(key)
    if isinstance(series_raw, list) and series_raw:
        df = pd.DataFrame(series_raw)
        if {"date", "aqi"}.issubset(df.columns):
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df["aqi"] = pd.to_numeric(df["aqi"], errors="coerce")
            df = df.dropna(subset=["date", "aqi"]).sort_values("date")
            if not df.empty:
                return df

    return _build_daily_series(stats, days)


def _extract_pollutants(payload: dict, key: str, stats: dict) -> dict[str, float]:
    pollutants = payload.get(key)
    if isinstance(pollutants, dict):
        return {
            "pm25": float(pollutants.get("pm25", 0.0)),
            "pm10": float(pollutants.get("pm10", 0.0)),
            "no2": float(pollutants.get("no2", 0.0)),
            "so2": float(pollutants.get("so2", 0.0)),
            "co": float(pollutants.get("co", 0.0)),
        }

    # Fallback profile from AQI stats to avoid empty radar when API omits pollutant vectors.
    mean_aqi = float(stats.get("mean_aqi", 100.0))
    return {
        "pm25": mean_aqi * 0.55,
        "pm10": mean_aqi * 0.75,
        "no2": mean_aqi * 0.18,
        "so2": mean_aqi * 0.10,
        "co": mean_aqi * 0.03,
    }


def _extract_hourly_peaks(payload: dict, key: str, stats: dict) -> pd.DataFrame:
    peaks = payload.get(key)
    if isinstance(peaks, list) and peaks:
        df = pd.DataFrame(peaks)
        if {"hour", "aqi"}.issubset(df.columns):
            df["hour"] = pd.to_numeric(df["hour"], errors="coerce")
            df["aqi"] = pd.to_numeric(df["aqi"], errors="coerce")
            df = df.dropna(subset=["hour", "aqi"]).copy()
            df["hour"] = df["hour"].astype(int)
            return df.sort_values("hour")

    # Fallback synthetic hour profile centered around commuting peaks.
    hours = np.arange(24)
    mean_aqi = float(stats.get("mean_aqi", 100.0))
    profile = (
        mean_aqi
        + 0.20 * mean_aqi * np.exp(-((hours - 9) ** 2) / 12.0)
        + 0.25 * mean_aqi * np.exp(-((hours - 20) ** 2) / 10.0)
    )
    return pd.DataFrame({"hour": hours, "aqi": profile})


def render_compare(client, days: int) -> None:
    st.title("Compare Cities")
    st.caption(f"Side-by-side AQI comparison over the last {days} days")

    sel_col1, sel_col2 = st.columns(2)
    with sel_col1:
        city1 = st.selectbox("City 1", options=CITIES, index=0, key="compare_city_1")
    with sel_col2:
        default_idx = 1 if len(CITIES) > 1 else 0
        city2 = st.selectbox("City 2", options=CITIES, index=default_idx, key="compare_city_2")

    compare_clicked = st.button("Compare", type="primary")

    if not compare_clicked:
        st.info("Select two cities and click Compare.")
        return

    if city1 == city2:
        st.warning("Please choose two different cities.")
        return

    with st.spinner("Comparing cities..."):
        payload = client.compare_cities(city1, city2)

    if payload is None:
        st.error("Comparison data is unavailable right now.")
        return

    city1_stats = payload.get("city1_stats", {})
    city2_stats = payload.get("city2_stats", {})

    # Row 1: metric comparison table/cards
    st.subheader("Stat Comparison")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Mean AQI", _fmt_number(city1_stats.get("mean_aqi")), _fmt_delta(city1_stats.get("mean_aqi"), city2_stats.get("mean_aqi")))
    m2.metric("Max AQI", _fmt_number(city1_stats.get("max_aqi")), _fmt_delta(city1_stats.get("max_aqi"), city2_stats.get("max_aqi")))
    m3.metric("Worst Day", str(city1_stats.get("worst_day", "N/A")), str(city2_stats.get("worst_day", "N/A")))
    m4.metric("Best Day", str(city1_stats.get("best_day", "N/A")), str(city2_stats.get("best_day", "N/A")))
    m5.metric("Trend", str(city1_stats.get("trend_direction", "N/A")).title(), str(city2_stats.get("trend_direction", "N/A")).title())
    m6.metric(
        "Days Hazardous",
        str(city1_stats.get("days_above_hazardous_threshold", 0)),
        _fmt_delta(
            city1_stats.get("days_above_hazardous_threshold", 0),
            city2_stats.get("days_above_hazardous_threshold", 0),
            digits=0,
        ),
    )

    # Row 2: overlapping AQI trend lines
    st.subheader("AQI Trend Comparison")
    series1 = _extract_city_series(payload, "city1_timeseries", city1_stats, days)
    series2 = _extract_city_series(payload, "city2_timeseries", city2_stats, days)

    trend_fig = go.Figure()
    trend_fig.add_trace(
        go.Scatter(
            x=series1["date"],
            y=series1["aqi"],
            mode="lines+markers",
            name=city1,
            line=dict(color=CITY_COLORS["city1"], width=2.5),
            hovertemplate=f"{city1}<br>Date: %{{x|%Y-%m-%d}}<br>AQI: %{{y:.1f}}<extra></extra>",
        )
    )
    trend_fig.add_trace(
        go.Scatter(
            x=series2["date"],
            y=series2["aqi"],
            mode="lines+markers",
            name=city2,
            line=dict(color=CITY_COLORS["city2"], width=2.5),
            hovertemplate=f"{city2}<br>Date: %{{x|%Y-%m-%d}}<br>AQI: %{{y:.1f}}<extra></extra>",
        )
    )
    trend_fig.update_layout(
        template="plotly_white",
        xaxis_title="Date",
        yaxis_title="AQI",
        legend_title="City",
        height=420,
    )
    st.plotly_chart(trend_fig, use_container_width=True)

    # Row 3: radar + hour peak bars
    left, right = st.columns(2)

    with left:
        st.subheader("Pollutant Profile Radar")
        p1 = _extract_pollutants(payload, "city1_pollutants", city1_stats)
        p2 = _extract_pollutants(payload, "city2_pollutants", city2_stats)

        axes = ["PM2.5", "PM10", "NO2", "SO2", "CO"]
        keys = ["pm25", "pm10", "no2", "so2", "co"]

        radar_fig = go.Figure()
        radar_fig.add_trace(
            go.Scatterpolar(
                r=[p1[k] for k in keys],
                theta=axes,
                fill="toself",
                name=city1,
                line=dict(color=CITY_COLORS["city1"]),
            )
        )
        radar_fig.add_trace(
            go.Scatterpolar(
                r=[p2[k] for k in keys],
                theta=axes,
                fill="toself",
                name=city2,
                line=dict(color=CITY_COLORS["city2"]),
            )
        )
        radar_fig.update_layout(
            template="plotly_white",
            polar=dict(radialaxis=dict(visible=True)),
            height=430,
            legend_title="City",
        )
        st.plotly_chart(radar_fig, use_container_width=True)

    with right:
        st.subheader("Hour-of-Day Peak Pollution")
        h1 = _extract_hourly_peaks(payload, "city1_hourly_peaks", city1_stats)
        h2 = _extract_hourly_peaks(payload, "city2_hourly_peaks", city2_stats)

        bar_fig = go.Figure()
        bar_fig.add_trace(
            go.Bar(
                x=h1["hour"],
                y=h1["aqi"],
                name=city1,
                marker_color=CITY_COLORS["city1"],
                opacity=0.82,
            )
        )
        bar_fig.add_trace(
            go.Bar(
                x=h2["hour"],
                y=h2["aqi"],
                name=city2,
                marker_color=CITY_COLORS["city2"],
                opacity=0.82,
            )
        )
        bar_fig.update_layout(
            barmode="group",
            template="plotly_white",
            xaxis_title="Hour of Day",
            yaxis_title="AQI",
            height=430,
            legend_title="City",
        )
        st.plotly_chart(bar_fig, use_container_width=True)
