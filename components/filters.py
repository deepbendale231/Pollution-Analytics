from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st


def city_selector(df: pd.DataFrame) -> str:
    if "city" not in df.columns:
        return "All"
    cities = sorted(df["city"].dropna().astype(str).unique().tolist())
    return st.sidebar.selectbox("City", ["All", *cities])


def pollutant_selector(df: pd.DataFrame) -> str:
    if "pollutant_id" not in df.columns:
        return "All"
    pollutants = sorted(df["pollutant_id"].dropna().astype(str).unique().tolist())
    return st.sidebar.selectbox("Pollutant", ["All", *pollutants])


def date_range_selector(df: pd.DataFrame) -> tuple[date, date] | None:
    if "last_update" not in df.columns:
        return None

    parsed_dates = pd.to_datetime(df["last_update"], errors="coerce")
    valid_dates = parsed_dates.dropna()
    if valid_dates.empty:
        return None

    min_date = valid_dates.min().date()
    max_date = valid_dates.max().date()
    selected_range = st.sidebar.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if isinstance(selected_range, tuple) and len(selected_range) == 2:
        return selected_range[0], selected_range[1]

    if isinstance(selected_range, date):
        return selected_range, selected_range

    return min_date, max_date


def apply_filters(
    df: pd.DataFrame,
    selected_city: str,
    selected_pollutant: str,
    selected_date_range: tuple[date, date] | None,
) -> pd.DataFrame:
    filtered_df = df.copy()

    if selected_city != "All" and "city" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["city"].astype(str) == selected_city]

    if selected_pollutant != "All" and "pollutant_id" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["pollutant_id"].astype(str) == selected_pollutant]

    if selected_date_range is not None and "last_update" in filtered_df.columns:
        start_date, end_date = selected_date_range
        date_series = pd.to_datetime(filtered_df["last_update"], errors="coerce").dt.date
        filtered_df = filtered_df[(date_series >= start_date) & (date_series <= end_date)]

    return filtered_df


def get_filtered_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filters")
    selected_city = city_selector(df)
    selected_pollutant = pollutant_selector(df)
    selected_date_range = date_range_selector(df)
    return apply_filters(df, selected_city, selected_pollutant, selected_date_range)
