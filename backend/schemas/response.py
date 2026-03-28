from __future__ import annotations

from datetime import date as dt_date
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PredictionResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "aqi": 182.4,
                "confidence_lower": 160.2,
                "confidence_upper": 205.8,
                "health_category": "Unhealthy",
                "recommendations": [
                    "Limit prolonged outdoor activity.",
                    "Use masks in high-traffic areas.",
                ],
            }
        }
    )

    aqi: float = Field(..., description="Predicted AQI value.", examples=[182.4])
    confidence_lower: float = Field(..., description="Lower confidence bound for predicted AQI.", examples=[160.2])
    confidence_upper: float = Field(..., description="Upper confidence bound for predicted AQI.", examples=[205.8])
    health_category: str = Field(..., description="AQI health category based on CPCB bands.", examples=["Unhealthy"])
    recommendations: list[str] = Field(..., description="Recommended actions based on health category.")


class DayForecast(BaseModel):
    date: dt_date = Field(..., description="Forecast date.", examples=["2026-03-28"])
    predicted_aqi: float = Field(..., description="Predicted AQI for the day.", examples=[176.3])
    lower_bound: float = Field(..., description="Lower uncertainty bound.", examples=[152.5])
    upper_bound: float = Field(..., description="Upper uncertainty bound.", examples=[201.8])


class ForecastResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "city": "Delhi",
                "forecast": [
                    {
                        "date": "2026-03-28",
                        "predicted_aqi": 176.3,
                        "lower_bound": 152.5,
                        "upper_bound": 201.8,
                    }
                ],
            }
        }
    )

    city: str = Field(..., description="City name for the forecast.", examples=["Delhi"])
    forecast: list[DayForecast] = Field(..., description="7-day AQI forecast entries.")


class CityStatsResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "city": "Delhi",
                "days": 30,
                "mean_aqi": 178.2,
                "median_aqi": 171.4,
                "max_aqi": 312.7,
                "min_aqi": 82.9,
                "worst_day": "2026-03-17",
                "best_day": "2026-03-03",
                "days_above_hazardous_threshold": 2,
                "trend_direction": "worsening",
                "trend_slope": 0.42,
            }
        }
    )

    city: str = Field(..., description="City name.")
    days: int = Field(..., description="Lookback window in days.", examples=[30])
    mean_aqi: float = Field(..., description="Mean AQI over the lookback period.")
    median_aqi: float = Field(..., description="Median AQI over the lookback period.")
    max_aqi: float = Field(..., description="Maximum AQI observed.")
    min_aqi: float = Field(..., description="Minimum AQI observed.")
    worst_day: dt_date = Field(..., description="Day with highest average AQI.")
    best_day: dt_date = Field(..., description="Day with lowest average AQI.")
    days_above_hazardous_threshold: int = Field(..., description="Count of days above hazardous threshold.")
    trend_direction: str = Field(..., description="Trend direction based on linear regression slope.", examples=["stable"])
    trend_slope: float = Field(..., description="Slope of AQI trend line.", examples=[0.12])


class ComparisonResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "city1": "Delhi",
                "city2": "Mumbai",
                "city1_stats": {
                    "city": "Delhi",
                    "days": 30,
                    "mean_aqi": 178.2,
                    "median_aqi": 171.4,
                    "max_aqi": 312.7,
                    "min_aqi": 82.9,
                    "worst_day": "2026-03-17",
                    "best_day": "2026-03-03",
                    "days_above_hazardous_threshold": 2,
                    "trend_direction": "worsening",
                    "trend_slope": 0.42,
                },
                "city2_stats": {
                    "city": "Mumbai",
                    "days": 30,
                    "mean_aqi": 132.6,
                    "median_aqi": 129.1,
                    "max_aqi": 208.4,
                    "min_aqi": 74.8,
                    "worst_day": "2026-03-18",
                    "best_day": "2026-03-05",
                    "days_above_hazardous_threshold": 0,
                    "trend_direction": "stable",
                    "trend_slope": 0.05,
                },
            }
        }
    )

    city1: str = Field(..., description="First city name.")
    city2: str = Field(..., description="Second city name.")
    city1_stats: CityStatsResponse = Field(..., description="Statistics summary for city1.")
    city2_stats: CityStatsResponse = Field(..., description="Statistics summary for city2.")


class ErrorResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "NOT_FOUND",
                "message": "No AQI records found for city 'Delhi'.",
                "timestamp": "2026-03-27T15:30:00Z",
            }
        }
    )

    code: str = Field(..., description="Machine-readable error code.", examples=["VALIDATION_ERROR"])
    message: str = Field(..., description="Human-readable error message.")
    timestamp: datetime = Field(..., description="UTC timestamp when error was raised.")


class HealthResponse(BaseModel):
    status: str = Field(..., description="API health status.", examples=["ok"])
    timestamp: datetime = Field(..., description="UTC timestamp of health check.")
    model_loaded: bool = Field(..., description="Whether model artifacts are loaded and ready.")


class AnalyticsSummaryResponse(BaseModel):
    total_records: int = Field(..., description="Total AQI records included in summary.")
    average_aqi: float = Field(..., description="Average AQI for summary scope.")
