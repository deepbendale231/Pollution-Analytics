from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from components.prediction import predict_with_confidence
from PYTHON.model_manager import load_model
from ..schemas.request import PredictionRequest
from ..schemas.response import PredictionResponse

_MODEL_CACHE: dict[str, Any] = {}


def load_model_artifacts() -> dict[str, Any]:
    model, scaler = load_model()
    _MODEL_CACHE["model"] = model
    _MODEL_CACHE["scaler"] = scaler
    return _MODEL_CACHE


def get_loaded_model_artifacts() -> tuple[Any, Any]:
    model = _MODEL_CACHE.get("model")
    scaler = _MODEL_CACHE.get("scaler")
    if model is None or scaler is None:
        model, scaler = load_model()
        _MODEL_CACHE["model"] = model
        _MODEL_CACHE["scaler"] = scaler
    return model, scaler


def predict_aqi(payload: PredictionRequest) -> PredictionResponse:
    model, scaler = get_loaded_model_artifacts()

    expected_features = list(getattr(scaler, "feature_names_in_", []))
    if not expected_features:
        raise ValueError("Model scaler feature names are unavailable.")

    payload_values = {
        "city": payload.city,
        "pm25": payload.pm25,
        "pm10": payload.pm10,
        "no2": payload.no2,
        "so2": payload.so2,
        "co": payload.co,
        "temperature": payload.temperature,
        "humidity": payload.humidity,
        "wind_speed": payload.wind_speed,
    }

    mapped_row: dict[str, float] = {}
    for feature in expected_features:
        val = payload_values.get(feature)
        mapped_row[feature] = 0.0 if val is None else float(val)

    features_df = pd.DataFrame([mapped_row], columns=expected_features)
    confidence = predict_with_confidence(model, features_df)

    predicted = float(np.asarray(confidence["prediction"])[0])
    lower = float(np.asarray(confidence["lower_bound"])[0])
    upper = float(np.asarray(confidence["upper_bound"])[0])

    if predicted <= 50:
        category = "Good"
        actions = ["Air quality is acceptable for outdoor activities."]
    elif predicted <= 100:
        category = "Moderate"
        actions = ["Sensitive individuals should limit prolonged outdoor activity."]
    elif predicted <= 200:
        category = "Unhealthy"
        actions = ["Reduce prolonged outdoor exertion and consider masks outdoors."]
    elif predicted <= 300:
        category = "Very Unhealthy"
        actions = ["Avoid outdoor exercise and keep indoor air as clean as possible."]
    else:
        category = "Hazardous"
        actions = ["Stay indoors and follow health advisories closely."]

    return PredictionResponse(
        aqi=predicted,
        confidence_lower=lower,
        confidence_upper=upper,
        health_category=category,
        recommendations=actions,
    )
