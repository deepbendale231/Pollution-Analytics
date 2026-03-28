"""API tests for FastAPI backend endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app import app


class _DummyScaler:
    feature_names_in_ = [
        "pm25",
        "pm10",
        "no2",
        "so2",
        "temperature",
        "humidity",
        "wind_speed",
    ]

    def transform(self, x):
        return x


class _DummyModel:
    pass


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Create a module-scoped FastAPI test client with startup model loading mocked."""
    with patch("backend.app.load_model_artifacts", return_value={"model": _DummyModel(), "scaler": _DummyScaler()}):
        with TestClient(app) as test_client:
            yield test_client


@pytest.fixture
def valid_predict_payload() -> dict:
    """Return a valid prediction request payload used across prediction tests."""
    return {
        "city": "Delhi",
        "pm25": 85.0,
        "pm10": 140.0,
        "no2": 36.0,
        "so2": 14.0,
        "temperature": 31.0,
        "humidity": 62.0,
        "wind_speed": 7.5,
    }


def test_predict_valid_input(client: TestClient, valid_predict_payload: dict) -> None:
    """POST /predict with valid features should return 200 and AQI in 0-500."""
    mock_interval_payload = {
        "prediction": [156.3],
        "lower_bound": [141.0],
        "upper_bound": [172.6],
        "confidence_width": [31.6],
        "reliability": ["high"],
    }

    with patch("backend.routers.predictions.get_loaded_model_artifacts", return_value=(_DummyModel(), _DummyScaler())), patch(
        "backend.routers.predictions.predict_with_intervals", return_value=mock_interval_payload
    ):
        response = client.post("/predict", json=valid_predict_payload)

    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["predicted_aqi"] <= 500


def test_predict_missing_city(client: TestClient, valid_predict_payload: dict) -> None:
    """POST /predict without city should fail validation with 422."""
    invalid_payload = {k: v for k, v in valid_predict_payload.items() if k != "city"}

    response = client.post("/predict", json=invalid_payload)

    assert response.status_code == 422


def test_predict_negative_pm25(client: TestClient, valid_predict_payload: dict) -> None:
    """POST /predict with pm25=-10 should fail validation with 422."""
    invalid_payload = dict(valid_predict_payload)
    invalid_payload["pm25"] = -10

    response = client.post("/predict", json=invalid_payload)

    assert response.status_code == 422


def test_predict_response_has_confidence_bounds(client: TestClient, valid_predict_payload: dict) -> None:
    """POST /predict should include lower_bound and upper_bound keys in the response."""
    mock_interval_payload = {
        "prediction": [132.0],
        "lower_bound": [118.5],
        "upper_bound": [146.7],
        "confidence_width": [28.2],
        "reliability": ["medium"],
    }

    with patch("backend.routers.predictions.get_loaded_model_artifacts", return_value=(_DummyModel(), _DummyScaler())), patch(
        "backend.routers.predictions.predict_with_intervals", return_value=mock_interval_payload
    ):
        response = client.post("/predict", json=valid_predict_payload)

    assert response.status_code == 200
    body = response.json()
    assert "lower_bound" in body
    assert "upper_bound" in body


def test_forecast_valid_city(client: TestClient) -> None:
    """GET /forecast/Delhi should return 200 and exactly 7 forecast entries."""
    start_dt = datetime(2026, 1, 1)
    db_rows = [
        {
            "city": "Delhi",
            "date": start_dt + timedelta(days=i),
            "aqi_value": 120 + (i % 9),
        }
        for i in range(45)
    ]
    forecast_rows = [
        {
            "date": f"2026-03-{10 + i:02d}",
            "day_name": "Monday",
            "predicted_aqi": 150.0 + i,
            "lower_bound": 140.0 + i,
            "upper_bound": 160.0 + i,
            "health_category": "Unhealthy",
            "advisory": "Limit outdoor activity.",
        }
        for i in range(7)
    ]

    with patch("backend.routers.predictions.run_query", return_value=pd.DataFrame(db_rows)), patch(
        "backend.routers.predictions.generate_forecast", return_value=forecast_rows
    ):
        response = client.get("/forecast/Delhi")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 7


def test_forecast_invalid_city(client: TestClient) -> None:
    """GET /forecast/FakeCity should return 404 when no historical data exists."""
    with patch("backend.routers.predictions.run_query", return_value=pd.DataFrame(columns=["city", "date", "aqi_value"])):
        response = client.get("/forecast/FakeCity")

    assert response.status_code == 404


def test_city_stats_valid(client: TestClient) -> None:
    """GET /city/Mumbai/stats should return 200 with mean_aqi in payload."""
    start_dt = datetime(2026, 2, 1)
    stats_rows = [
        {
            "timestamp": start_dt + timedelta(days=i),
            "aqi_value": 95 + (i % 12),
        }
        for i in range(30)
    ]

    with patch("backend.routers.analytics.run_query", return_value=pd.DataFrame(stats_rows)):
        response = client.get("/city/Mumbai/stats")

    assert response.status_code == 200
    body = response.json()
    assert "mean_aqi" in body


def test_compare_cities(client: TestClient) -> None:
    """GET /compare should return 200 and include both city names in response."""
    start_dt = datetime(2026, 2, 1)
    city_rows = [
        {
            "timestamp": start_dt + timedelta(days=i),
            "aqi_value": 110 + (i % 8),
        }
        for i in range(30)
    ]

    with patch("backend.routers.analytics.run_query", return_value=pd.DataFrame(city_rows)):
        response = client.get("/compare", params={"city1": "Delhi", "city2": "Mumbai"})

    assert response.status_code == 200
    body = response.json()
    assert body.get("city1") == "Delhi"
    assert body.get("city2") == "Mumbai"


def test_ranking(client: TestClient) -> None:
    """GET /ranking should return 200 and a non-empty rankings list."""
    ranking_df = pd.DataFrame(
        [
            {
                "city": "Delhi",
                "average_aqi": 178.2,
                "previous_month_average_aqi": 165.4,
                "delta_vs_previous_month": 12.8,
            },
            {
                "city": "Mumbai",
                "average_aqi": 133.1,
                "previous_month_average_aqi": 129.0,
                "delta_vs_previous_month": 4.1,
            },
        ]
    )

    with patch("backend.routers.analytics.run_query", return_value=ranking_df):
        response = client.get("/ranking")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body.get("rankings"), list)
    assert len(body["rankings"]) > 0


def test_health_check(client: TestClient) -> None:
    """GET /health should return 200 and model_loaded=true."""
    with patch("backend.routers.health.get_loaded_model_artifacts", return_value=(object(), object())):
        response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body.get("model_loaded") is True
