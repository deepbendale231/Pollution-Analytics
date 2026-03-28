from __future__ import annotations

from datetime import datetime
from typing import Any
import re

import pandas as pd
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from components.prediction import predict_with_intervals
from ml.explainability import explain_prediction
from ml.forecast import generate_forecast
from ..services.db_service import run_query
from ..services.model_service import get_loaded_model_artifacts

router = APIRouter(tags=["predictions"])


CITY_COORDINATES: dict[str, tuple[float, float]] = {
    "delhi": (28.6139, 77.2090),
    "mumbai": (19.0760, 72.8777),
    "chennai": (13.0827, 80.2707),
    "kolkata": (22.5726, 88.3639),
    "bangalore": (12.9716, 77.5946),
    "bengaluru": (12.9716, 77.5946),
    "hyderabad": (17.3850, 78.4867),
    "pune": (18.5204, 73.8567),
    "ahmedabad": (23.0225, 72.5714),
}


class PredictRequest(BaseModel):
    city: str = Field(..., min_length=1, max_length=100)
    pm25: float = Field(..., ge=0)
    pm10: float = Field(..., ge=0)
    no2: float = Field(..., ge=0)
    so2: float = Field(..., ge=0)
    temperature: float
    humidity: float = Field(..., ge=0, le=100)
    wind_speed: float = Field(..., ge=0)


class PredictResponse(BaseModel):
    predicted_aqi: float
    lower_bound: float
    upper_bound: float
    confidence_width: float
    reliability: str
    health_category: str
    recommended_actions: list[str]


class ForecastPoint(BaseModel):
    date: str
    day_name: str
    predicted_aqi: float
    lower_bound: float
    upper_bound: float
    health_category: str
    advisory: str


class ForecastResponse(BaseModel):
    date: str
    day_name: str
    predicted_aqi: float
    lower_bound: float
    upper_bound: float
    health_category: str
    advisory: str


class ExplainResponse(BaseModel):
    predicted_aqi: float
    lower_bound: float
    upper_bound: float
    confidence_width: float
    reliability: str
    explanation: dict[str, Any]


def _determine_health_category(aqi: float) -> str:
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Moderate"
    if aqi <= 200:
        return "Unhealthy"
    if aqi <= 300:
        return "Very Unhealthy"
    return "Hazardous"


def _recommended_actions(category: str) -> list[str]:
    action_map = {
        "Good": [
            "Air quality is good; normal outdoor activity is fine.",
            "Continue routine monitoring and preventive practices.",
        ],
        "Moderate": [
            "Sensitive groups should reduce prolonged outdoor exertion.",
            "Prefer well-ventilated indoor activity during peak traffic hours.",
        ],
        "Unhealthy": [
            "Limit prolonged outdoor activity, especially for sensitive groups.",
            "Use protective masks when outdoors and keep indoor air clean.",
        ],
        "Very Unhealthy": [
            "Avoid outdoor exercise and unnecessary travel in polluted zones.",
            "Use indoor air purifiers and keep windows closed during peaks.",
        ],
        "Hazardous": [
            "Stay indoors as much as possible; avoid all strenuous outdoor activity.",
            "Follow local advisories and use medical-grade masks if stepping outside.",
        ],
    }
    return action_map[category]


def _build_feature_frame(payload: PredictRequest, expected_features: list[str]) -> pd.DataFrame:
    city_lat, city_lon = CITY_COORDINATES.get(payload.city.strip().lower(), (0.0, 0.0))

    source_values = {
        "pm25": payload.pm25,
        "pm10": payload.pm10,
        "no2": payload.no2,
        "so2": payload.so2,
        "temperature": payload.temperature,
        "humidity": payload.humidity,
        "wind_speed": payload.wind_speed,
        # Common feature names used by this project's trained model.
        "pollutant_min": payload.pm25,
        "pollutant_max": payload.pm10,
        "latitude": city_lat,
        "longitude": city_lon,
    }
    source_values_lower = {k.lower(): v for k, v in source_values.items()}

    mapped_feature_count = 0
    row: dict[str, float] = {}
    for feature in expected_features:
        normalized = re.sub(r"[^a-z0-9]", "", feature.lower())
        value = source_values_lower.get(feature.lower())

        if value is None and normalized in {"pm25", "pm2", "pm2_5", "pm2dot5", "pollutantmin"}:
            value = payload.pm25
        elif value is None and normalized in {"pm10", "pollutantmax"}:
            value = payload.pm10
        elif value is None and normalized in {"temperature", "temp"}:
            value = payload.temperature
        elif value is None and normalized in {"humidity", "rh"}:
            value = payload.humidity
        elif value is None and normalized in {"windspeed", "wind", "ws"}:
            value = payload.wind_speed
        elif value is None and normalized in {"no2", "nitrogendioxide"}:
            value = payload.no2
        elif value is None and normalized in {"so2", "sulfurdioxide"}:
            value = payload.so2
        elif value is None and normalized in {"latitude", "lat"}:
            value = city_lat
        elif value is None and normalized in {"longitude", "lon", "lng"}:
            value = city_lon
        elif value is None:
            value = 0.0

        if value != 0.0:
            mapped_feature_count += 1
        row[feature] = float(value)

    if mapped_feature_count == 0:
        raise ValueError(
            "Input features could not be mapped to trained model features. "
            "Retrain model with API feature set or update feature mapping."
        )

    return pd.DataFrame([row], columns=expected_features)


def _predict_with_bounds(payload: PredictRequest):
    model, scaler = get_loaded_model_artifacts()
    expected_features = list(getattr(scaler, "feature_names_in_", []))

    if not expected_features:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model scaler features are not available. Retrain and reload the model.",
        )

    input_df = _build_feature_frame(payload, expected_features)
    scaled_array = scaler.transform(input_df)
    scaled_df = pd.DataFrame(scaled_array, columns=input_df.columns)
    confidence = predict_with_intervals(model, scaled_df)

    predicted_aqi = float(confidence["prediction"][0])
    lower_bound = float(confidence["lower_bound"][0])
    upper_bound = float(confidence["upper_bound"][0])
    confidence_width = float(confidence["confidence_width"][0])
    reliability = str(confidence["reliability"][0])

    return model, scaler, input_df, predicted_aqi, lower_bound, upper_bound, confidence_width, reliability


@router.post(
    "/predict",
    response_model=PredictResponse,
    status_code=status.HTTP_200_OK,
)
def predict_aqi_endpoint(payload: PredictRequest) -> PredictResponse:
    try:
        _, _, _, predicted_aqi, lower_bound, upper_bound, confidence_width, reliability = _predict_with_bounds(payload)

        category = _determine_health_category(predicted_aqi)
        actions = _recommended_actions(category)

        return PredictResponse(
            predicted_aqi=predicted_aqi,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            confidence_width=confidence_width,
            reliability=reliability,
            health_category=category,
            recommended_actions=actions,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {exc}",
        ) from exc


@router.post(
    "/explain",
    response_model=ExplainResponse,
    status_code=status.HTTP_200_OK,
)
def explain_aqi_endpoint(payload: PredictRequest) -> ExplainResponse:
    try:
        model, scaler, input_df, predicted_aqi, lower_bound, upper_bound, confidence_width, reliability = _predict_with_bounds(payload)

        # The trained RF in this project is fit on scaled features; explain in scaled space.
        scaled_array = scaler.transform(input_df)
        scaled_df = pd.DataFrame(scaled_array, columns=input_df.columns)

        explanation = explain_prediction(
            model=model,
            X_train=scaled_df,
            single_input_df=scaled_df,
        )

        return ExplainResponse(
            predicted_aqi=predicted_aqi,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            confidence_width=confidence_width,
            reliability=reliability,
            explanation=explanation,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Explanation failed: {exc}",
        ) from exc


@router.get(
    "/forecast/{city}",
    response_model=list[ForecastResponse],
    status_code=status.HTTP_200_OK,
)
def forecast_city_endpoint(city: str) -> list[ForecastResponse]:
    try:
        forecast_source = run_query(
            """
            SELECT
                DATE(timestamp) as ds,
                AVG(
                    CASE
                        WHEN value <= 30  THEN value * 50.0/30
                        WHEN value <= 60  THEN 50  + (value-30)  * 50.0/30
                        WHEN value <= 90  THEN 100 + (value-60)  * 100.0/30
                        WHEN value <= 120 THEN 200 + (value-90)  * 100.0/30
                        WHEN value <= 250 THEN 300 + (value-120) * 100.0/130
                        ELSE                   400 + (value-250) * 100.0/130
                    END
                ) AS y
            FROM measurements
            WHERE city = %s
              AND parameter = 'pm25'
              AND value > 0
              AND timestamp >= (NOW() - INTERVAL 90 DAY)
            GROUP BY DATE(timestamp)
            ORDER BY ds ASC
            """,
            params=(city,),
        )

        if forecast_source.empty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No AQI history found for city '{city}' in the last 90 days.",
            )

        if len(forecast_source) < 10:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Insufficient data for forecast. Need at least 10 days of history for city '{city}'.",
            )

        forecast_list = generate_forecast(forecast_source[["ds", "y"]], city, periods=7)

        return [ForecastResponse(**item) for item in forecast_list]
    except HTTPException:
        raise
    except ValueError as exc:
        message = str(exc)
        if "No records found for city" in message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forecast generation failed: {exc}",
        ) from exc
