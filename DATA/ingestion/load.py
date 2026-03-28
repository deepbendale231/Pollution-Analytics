from __future__ import annotations

import time
from typing import Any

import pandas as pd

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS measurements (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    city VARCHAR(100) NOT NULL,
    parameter VARCHAR(30) NOT NULL,
    value DOUBLE NULL,
    unit VARCHAR(30) NULL,
    timestamp DATETIME NOT NULL,
    latitude DOUBLE NULL,
    longitude DOUBLE NULL,
    aqi_value DOUBLE NULL,
    health_category VARCHAR(30) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY ux_city_parameter_timestamp (city, parameter, timestamp),
    KEY idx_city_parameter_timestamp (city, parameter, timestamp)
);
"""

UPSERT_SQL = """
INSERT INTO measurements (
    city,
    parameter,
    value,
    unit,
    timestamp,
    latitude,
    longitude,
    aqi_value,
    health_category
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    value = VALUES(value),
    unit = VALUES(unit),
    latitude = VALUES(latitude),
    longitude = VALUES(longitude),
    aqi_value = VALUES(aqi_value),
    health_category = VALUES(health_category),
    updated_at = CURRENT_TIMESTAMP;
"""


def _chunked(df: pd.DataFrame, chunk_size: int):
    for start in range(0, len(df), chunk_size):
        yield df.iloc[start : start + chunk_size]


def _fetch_existing(cursor, keys: list[tuple[str, str, Any]]) -> dict[tuple[str, str, Any], tuple]:
    if not keys:
        return {}

    placeholders = ", ".join(["(%s, %s, %s)"] * len(keys))
    sql = f"""
    SELECT city, parameter, timestamp, value, unit, latitude, longitude, aqi_value, health_category
    FROM measurements
    WHERE (city, parameter, timestamp) IN ({placeholders})
    """

    flat_params: list[Any] = []
    for key in keys:
        flat_params.extend(key)

    cursor.execute(sql, tuple(flat_params))
    rows = cursor.fetchall()
    existing: dict[tuple[str, str, Any], tuple] = {}
    for row in rows:
        existing[(row[0], row[1], row[2])] = row[3:]
    return existing


def _normalize_input(df: pd.DataFrame) -> pd.DataFrame:
    required = {"city", "parameter", "value", "unit", "timestamp", "latitude", "longitude"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError("df is missing required columns: " + ", ".join(sorted(missing)))

    out = df.copy()
    out["city"] = out["city"].astype(str)
    out["parameter"] = out["parameter"].astype(str)
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")
    out["latitude"] = pd.to_numeric(out["latitude"], errors="coerce")
    out["longitude"] = pd.to_numeric(out["longitude"], errors="coerce")

    if "aqi_value" not in out.columns:
        out["aqi_value"] = pd.NA
    else:
        out["aqi_value"] = pd.to_numeric(out["aqi_value"], errors="coerce")

    if "health_category" not in out.columns:
        out["health_category"] = pd.NA

    out = out.dropna(subset=["city", "parameter", "timestamp"]).reset_index(drop=True)
    return out


def create_measurements_table(connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(CREATE_TABLE_SQL)
    connection.commit()


def insert_measurements(df: pd.DataFrame, connection) -> dict[str, Any]:
    """Insert/upsert measurements in 500-row batches and return summary stats."""
    start = time.perf_counter()
    data = _normalize_input(df)

    inserted = 0
    updated = 0
    skipped = 0

    if data.empty:
        return {"inserted": 0, "updated": 0, "skipped": 0, "duration_seconds": 0.0}

    create_measurements_table(connection)

    try:
        with connection.cursor() as cursor:
            for chunk in _chunked(data, 500):
                keys = [
                    (row.city, row.parameter, row.timestamp.to_pydatetime())
                    for row in chunk.itertuples(index=False)
                ]
                existing = _fetch_existing(cursor, keys)

                to_write = []
                for row in chunk.itertuples(index=False):
                    key = (row.city, row.parameter, row.timestamp.to_pydatetime())
                    existing_vals = existing.get(key)

                    new_vals = (
                        None if pd.isna(row.value) else float(row.value),
                        row.unit,
                        None if pd.isna(row.latitude) else float(row.latitude),
                        None if pd.isna(row.longitude) else float(row.longitude),
                        None if pd.isna(row.aqi_value) else float(row.aqi_value),
                        None if pd.isna(row.health_category) else str(row.health_category),
                    )

                    if existing_vals is None:
                        inserted += 1
                        to_write.append((row.city, row.parameter, *new_vals[:2], key[2], *new_vals[2:]))
                        continue

                    if tuple(existing_vals) == new_vals:
                        skipped += 1
                        continue

                    updated += 1
                    to_write.append((row.city, row.parameter, *new_vals[:2], key[2], *new_vals[2:]))

                if to_write:
                    cursor.executemany(UPSERT_SQL, to_write)

        connection.commit()
    except Exception:
        connection.rollback()
        raise

    duration = round(time.perf_counter() - start, 4)
    return {
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "duration_seconds": duration,
    }
