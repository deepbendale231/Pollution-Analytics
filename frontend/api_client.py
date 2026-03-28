from __future__ import annotations

import logging
import os
from typing import Any

import requests
import streamlit as st
from dotenv import load_dotenv

logging.basicConfig(level=logging.DEBUG)

load_dotenv()

def _resolve_base_url() -> str:
    # Streamlit Cloud uses st.secrets instead of local .env files.
    secrets_url = None
    try:
        secrets_url = st.secrets.get("API_BASE_URL")
    except Exception:
        secrets_url = None

    return (
        secrets_url
        or os.getenv("API_BASE_URL")
        or os.getenv("AQI_API_BASE_URL")
        or "http://localhost:8000"
    ).rstrip("/")


BASE_URL = _resolve_base_url()

TIMEOUT_SECONDS = 10

CITY_ALIASES = {
    "bangalore": ["Bengaluru"],
    "bengaluru": ["Bangalore"],
}


def _request(method: str, endpoint: str, *, params: dict[str, Any] | None = None, json_body: dict[str, Any] | None = None):
    url = f"{BASE_URL}{endpoint}"
    try:
        logging.debug("%s %s params=%s json=%s", method, endpoint, params, json_body)
        response = requests.request(
            method=method,
            url=url,
            params=params,
            json=json_body,
            timeout=TIMEOUT_SECONDS,
        )
        logging.debug("%s %s -> %s: %s", method, endpoint, response.status_code, response.text[:200])
        response.raise_for_status()
        return response.json()
    except requests.ConnectionError as exc:
        logging.error("%s %s failed: %s", method, endpoint, exc)
        st.error("API unavailable")
        return None
    except requests.Timeout as exc:
        logging.error("%s %s timed out: %s", method, endpoint, exc)
        st.error("API unavailable")
        return None
    except requests.RequestException as exc:
        detail = ""
        if getattr(exc, "response", None) is not None:
            try:
                detail = str(exc.response.text)[:240]
            except Exception:
                detail = ""
        logging.error("%s %s request failed: %s | detail=%s", method, endpoint, exc, detail)
        if detail:
            st.error(f"API error for {endpoint}: {detail}")
        return None
    except Exception as exc:
        logging.error("%s %s unexpected error: %s", method, endpoint, exc)
        return None


def predict_aqi(
    city: str,
    pm25: float | None,
    pm10: float | None,
    no2: float | None,
    so2: float | None,
    temperature: float | None,
    humidity: float | None,
    wind_speed: float | None,
):
    try:
        payload = {
            "city": city,
            "pm25": pm25,
            "pm10": pm10,
            "no2": no2,
            "so2": so2,
            "temperature": temperature,
            "humidity": humidity,
            "wind_speed": wind_speed,
        }
        response = _request("POST", "/predict", json_body=payload)
        if not isinstance(response, dict):
            return response

        predicted = response.get("predicted_aqi", response.get("aqi"))
        lower = response.get("lower_bound", response.get("confidence_lower"))
        upper = response.get("upper_bound", response.get("confidence_upper"))

        try:
            if predicted is not None:
                response["predicted_aqi"] = float(predicted)
                response.setdefault("aqi", float(predicted))
            if lower is not None:
                lower_val = float(lower)
                response["lower_bound"] = lower_val
                response["confidence_lower"] = lower_val
            if upper is not None:
                upper_val = float(upper)
                response["upper_bound"] = upper_val
                response["confidence_upper"] = upper_val
        except (TypeError, ValueError):
            # Keep original payload if any field is unexpectedly non-numeric.
            return response

        return response
    except Exception as exc:
        logging.error("predict_aqi failed: %s", exc)
        return None


def get_forecast(city: str, days: int = 7):
    try:
        response = _request("GET", f"/forecast/{city}")
        if response is None:
            return None

        if isinstance(response, list):
            response = {"forecast": response}

        # Current backend returns a fixed 7-day forecast; trim if caller requests fewer days.
        if isinstance(response, dict) and isinstance(response.get("forecast"), list):
            response["forecast"] = response["forecast"][: max(days, 0)]
        return response
    except Exception as exc:
        logging.error("get_forecast failed: %s", exc)
        return None


def get_city_stats(city: str, days: int = 30):
    try:
        primary = _request("GET", f"/analytics/city/{city}/stats", params={"days": days})
        if primary is not None:
            return primary

        for alias in CITY_ALIASES.get(city.strip().lower(), []):
            logging.debug("Retrying city stats with alias city=%s for input city=%s", alias, city)
            fallback = _request("GET", f"/analytics/city/{alias}/stats", params={"days": days})
            if fallback is not None:
                return fallback

        return None
    except Exception as exc:
        logging.error("get_city_stats failed: %s", exc)
        return None


def get_city_pollutants(city: str):
    try:
        primary = _request("GET", f"/analytics/city/{city}/pollutants")
        if primary is not None:
            return primary

        for alias in CITY_ALIASES.get(city.strip().lower(), []):
            logging.debug("Retrying city pollutants with alias city=%s for input city=%s", alias, city)
            fallback = _request("GET", f"/analytics/city/{alias}/pollutants")
            if fallback is not None:
                return fallback

        return None
    except Exception as exc:
        logging.error("get_city_pollutants failed: %s", exc)
        return None


def get_city_ranking():
    try:
        return _request("GET", "/analytics/ranking")
    except Exception as exc:
        logging.error("get_city_ranking failed: %s", exc)
        return None


def compare_cities(city1: str, city2: str):
    try:
        return _request("GET", "/analytics/compare", params={"city1": city1, "city2": city2})
    except Exception as exc:
        logging.error("compare_cities failed: %s", exc)
        return None


def get_health_check():
    try:
        return _request("GET", "/health")
    except Exception as exc:
        logging.error("get_health_check failed: %s", exc)
        return None
