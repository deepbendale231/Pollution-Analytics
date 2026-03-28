from __future__ import annotations

import numpy as np
import pandas as pd

REQUIRED_RAW_COLUMNS = {
    "city",
    "parameter",
    "value",
    "unit",
    "timestamp",
    "latitude",
    "longitude",
}

# CPCB AQI breakpoint table (concentration and index ranges).
# Concentration ranges follow commonly used CPCB/NAQI breakpoint definitions.
BREAKPOINTS: dict[str, list[tuple[float, float, int, int]]] = {
    "pm25": [
        (0, 30, 0, 50),
        (31, 60, 51, 100),
        (61, 90, 101, 200),
        (91, 120, 201, 300),
        (121, 250, 301, 400),
        (251, 500, 401, 500),
    ],
    "pm10": [
        (0, 50, 0, 50),
        (51, 100, 51, 100),
        (101, 250, 101, 200),
        (251, 350, 201, 300),
        (351, 430, 301, 400),
        (431, 600, 401, 500),
    ],
    "no2": [
        (0, 40, 0, 50),
        (41, 80, 51, 100),
        (81, 180, 101, 200),
        (181, 280, 201, 300),
        (281, 400, 301, 400),
        (401, 800, 401, 500),
    ],
    "so2": [
        (0, 40, 0, 50),
        (41, 80, 51, 100),
        (81, 380, 101, 200),
        (381, 800, 201, 300),
        (801, 1600, 301, 400),
        (1601, 2000, 401, 500),
    ],
    "co": [
        (0, 1.0, 0, 50),
        (1.1, 2.0, 51, 100),
        (2.1, 10.0, 101, 200),
        (10.1, 17.0, 201, 300),
        (17.1, 34.0, 301, 400),
        (34.1, 50.0, 401, 500),
    ],
    "o3": [
        (0, 50, 0, 50),
        (51, 100, 51, 100),
        (101, 168, 101, 200),
        (169, 208, 201, 300),
        (209, 748, 301, 400),
        (749, 1000, 401, 500),
    ],
    "nh3": [
        (0, 200, 0, 50),
        (201, 400, 51, 100),
        (401, 800, 101, 200),
        (801, 1200, 201, 300),
        (1201, 1800, 301, 400),
        (1801, 2000, 401, 500),
    ],
    "pb": [
        (0, 0.5, 0, 50),
        (0.6, 1.0, 51, 100),
        (1.1, 2.0, 101, 200),
        (2.1, 3.0, 201, 300),
        (3.1, 3.5, 301, 400),
        (3.6, 10.0, 401, 500),
    ],
}


def _to_ist(series: pd.Series) -> pd.Series:
    ts = pd.to_datetime(series, errors="coerce", utc=True)
    return ts.dt.tz_convert("Asia/Kolkata")


def _remove_outliers_iqr(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby("parameter")["value"]
    q1 = grouped.transform(lambda s: s.quantile(0.25))
    q3 = grouped.transform(lambda s: s.quantile(0.75))
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    keep = iqr.isna() | (iqr == 0) | ((df["value"] >= lower) & (df["value"] <= upper))
    return df[keep].reset_index(drop=True)


def _sub_index(parameter: str, concentration: float) -> float:
    if pd.isna(concentration):
        return np.nan
    rows = BREAKPOINTS.get(parameter)
    if not rows:
        return np.nan

    c = float(max(concentration, 0.0))
    for c_low, c_high, i_low, i_high in rows:
        if c_low <= c <= c_high:
            return ((i_high - i_low) / (c_high - c_low)) * (c - c_low) + i_low

    if c > rows[-1][1]:
        return 500.0
    return np.nan


def _health_category(aqi: float) -> str:
    if pd.isna(aqi):
        return "Unknown"
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Satisfactory"
    if aqi <= 200:
        return "Moderate"
    if aqi <= 300:
        return "Poor"
    if aqi <= 400:
        return "Very Poor"
    return "Severe"


def transform_openaq_dataframe(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Clean and transform OpenAQ measurements into hourly city records ready for MySQL insert."""
    missing = REQUIRED_RAW_COLUMNS.difference(raw_df.columns)
    if missing:
        raise ValueError("raw_df is missing required columns: " + ", ".join(sorted(missing)))

    df = raw_df.copy()
    df["city"] = df["city"].astype(str)
    df["parameter"] = df["parameter"].astype(str).str.lower()
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    # Step 1: convert to IST
    df["timestamp"] = _to_ist(df["timestamp"])
    df = df.dropna(subset=["timestamp", "value", "city", "parameter"]).copy()

    # Step 2: remove outliers per pollutant
    df = _remove_outliers_iqr(df)

    # Step 3: aggregate hourly averages per city per parameter
    df["timestamp"] = df["timestamp"].dt.floor("h")
    hourly = (
        df.groupby(["city", "parameter", "timestamp"], as_index=False)
        .agg(
            value=("value", "mean"),
            unit=("unit", "first"),
            latitude=("latitude", "mean"),
            longitude=("longitude", "mean"),
        )
        .sort_values(["city", "timestamp", "parameter"])
        .reset_index(drop=True)
    )

    # Step 4 and 5: AQI from PM2.5 and PM10 sub-indices, final = max(sub-indices)
    aqi_source = hourly[hourly["parameter"].isin(["pm25", "pm10"])].copy()
    aqi_source["sub_index"] = aqi_source.apply(
        lambda r: _sub_index(str(r["parameter"]), float(r["value"])),
        axis=1,
    )

    aqi_rows = (
        aqi_source.groupby(["city", "timestamp"], as_index=False)
        .agg(
            value=("sub_index", "max"),
            latitude=("latitude", "mean"),
            longitude=("longitude", "mean"),
        )
        .assign(parameter="aqi_value", unit="AQI")
    )

    combined = pd.concat([hourly, aqi_rows], ignore_index=True, sort=False)

    # Step 6: health category from AQI value (joined back on city/timestamp)
    aqi_category = aqi_rows[["city", "timestamp", "value"]].copy()
    aqi_category["health_category"] = aqi_category["value"].apply(_health_category)
    aqi_category = aqi_category.rename(columns={"value": "aqi_value"})

    combined = combined.merge(
        aqi_category[["city", "timestamp", "aqi_value", "health_category"]],
        on=["city", "timestamp"],
        how="left",
    )

    combined = combined[[
        "city",
        "parameter",
        "value",
        "unit",
        "timestamp",
        "latitude",
        "longitude",
        "aqi_value",
        "health_category",
    ]]

    # MySQL DATETIME compatibility: keep IST wall-clock, remove tz info.
    combined["timestamp"] = pd.to_datetime(combined["timestamp"], errors="coerce").dt.tz_localize(None)

    return combined.sort_values(["city", "timestamp", "parameter"]).reset_index(drop=True)
