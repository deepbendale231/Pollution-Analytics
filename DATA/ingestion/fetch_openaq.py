from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests

OPENAQ_URL = "https://api.openaq.org/v2/measurements"
DEFAULT_LIMIT = 1000
DEFAULT_TIMEOUT = 10
MAX_RETRIES = 3
PROJECT_ROOT = Path(__file__).resolve().parents[2]

TARGET_PARAMETERS = ["pm25", "pm10", "no2", "so2", "co"]
MAJOR_INDIAN_CITIES = [
    "Delhi",
    "Mumbai",
    "Chennai",
    "Kolkata",
    "Bangalore",
    "Hyderabad",
    "Pune",
    "Ahmedabad",
]

LOGGER = logging.getLogger(__name__)


def _build_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "User-Agent": "pollution-analytics-openaq-ingestion/1.0",
    }

    api_key = os.getenv("OPENAQ_API_KEY")
    if api_key:
        headers["X-API-Key"] = api_key

    return headers


def _request_with_retry(
    session: requests.Session,
    params: dict,
    max_retries: int = MAX_RETRIES,
    base_backoff_seconds: float = 1.0,
) -> dict:
    headers = _build_headers()

    for attempt in range(max_retries):
        try:
            response = session.get(
                OPENAQ_URL,
                params=params,
                headers=headers,
                timeout=DEFAULT_TIMEOUT,
            )

            if response.status_code == 429:
                retry_after_header = response.headers.get("Retry-After")
                if retry_after_header and retry_after_header.isdigit():
                    sleep_seconds = float(retry_after_header)
                else:
                    sleep_seconds = base_backoff_seconds * (2 ** attempt)
                LOGGER.warning(
                    "Rate limited by OpenAQ (429). Retrying in %.1f seconds (attempt %s/%s).",
                    sleep_seconds,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(sleep_seconds)
                continue

            if 500 <= response.status_code < 600:
                sleep_seconds = base_backoff_seconds * (2 ** attempt)
                LOGGER.warning(
                    "OpenAQ server error %s. Retrying in %.1f seconds (attempt %s/%s).",
                    response.status_code,
                    sleep_seconds,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(sleep_seconds)
                continue

            response.raise_for_status()
            return response.json()

        except requests.RequestException as exc:
            if attempt >= max_retries - 1:
                raise RuntimeError(
                    f"Failed to fetch OpenAQ data after {max_retries} attempts."
                ) from exc

            sleep_seconds = base_backoff_seconds * (2 ** attempt)
            LOGGER.warning(
                "Request to OpenAQ failed: %s. Retrying in %.1f seconds (attempt %s/%s).",
                exc,
                sleep_seconds,
                attempt + 1,
                max_retries,
            )
            time.sleep(sleep_seconds)

    raise RuntimeError("Unexpected retry loop termination while fetching OpenAQ data.")


def _fetch_city_parameter(
    session: requests.Session,
    city: str,
    parameter: str,
    limit: int,
) -> list[dict]:
    page = 1
    city_records: list[dict] = []

    while True:
        params = {
            "country": "IN",
            "city": city,
            "parameter": parameter,
            "limit": limit,
            "page": page,
            "sort": "desc",
            "order_by": "datetime",
        }

        payload = _request_with_retry(session=session, params=params)
        results = payload.get("results", [])

        if not results:
            break

        for row in results:
            coordinates = row.get("coordinates") or {}
            datetime_info = row.get("date") or {}
            city_records.append(
                {
                    "city": row.get("city") or city,
                    "parameter": row.get("parameter") or parameter,
                    "value": row.get("value"),
                    "unit": row.get("unit"),
                    "timestamp": datetime_info.get("utc") or datetime_info.get("local"),
                    "latitude": coordinates.get("latitude"),
                    "longitude": coordinates.get("longitude"),
                }
            )

        if len(results) < limit:
            break

        page += 1

    return city_records


def fetch_openaq_measurements(
    cities: Iterable[str] | None = None,
    parameters: Iterable[str] | None = None,
    limit: int = DEFAULT_LIMIT,
) -> pd.DataFrame:
    """Fetch OpenAQ measurements for target Indian cities and pollutant parameters."""
    cities_to_fetch = list(cities or MAJOR_INDIAN_CITIES)
    parameters_to_fetch = [p.lower() for p in (parameters or TARGET_PARAMETERS)]

    all_records: list[dict] = []

    with requests.Session() as session:
        for city in cities_to_fetch:
            city_start_count = len(all_records)
            for parameter in parameters_to_fetch:
                try:
                    records = _fetch_city_parameter(
                        session=session,
                        city=city,
                        parameter=parameter,
                        limit=limit,
                    )
                    all_records.extend(records)
                except Exception as exc:
                    # Missing/unsupported cities or intermittent API failures should not stop the full run.
                    LOGGER.warning(
                        "Skipping city=%s parameter=%s due to fetch error: %s",
                        city,
                        parameter,
                        exc,
                    )

            city_total = len(all_records) - city_start_count
            LOGGER.info("Fetched %s records for %s", city_total, city)

    df = pd.DataFrame(
        all_records,
        columns=[
            "city",
            "parameter",
            "value",
            "unit",
            "timestamp",
            "latitude",
            "longitude",
        ],
    )

    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
        df = df.dropna(subset=["timestamp", "value"])

    return df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    data = fetch_openaq_measurements()
    LOGGER.info("Total fetched records: %s", len(data))
    print(data.head())
