from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

try:
    from frontend.api_client import compare_cities
except ModuleNotFoundError:
    ROOT_DIR = Path(__file__).resolve().parents[2]
    if str(ROOT_DIR) not in sys.path:
        sys.path.append(str(ROOT_DIR))
    from frontend.api_client import compare_cities


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


def _render_stats_column(title: str, stats: dict) -> None:
    st.subheader(title)
    st.metric("Mean AQI", f"{stats.get('mean_aqi', 0):.1f}")
    st.metric("Median AQI", f"{stats.get('median_aqi', 0):.1f}")
    st.metric("Max AQI", f"{stats.get('max_aqi', 0):.1f}")
    st.metric("Trend", str(stats.get("trend_direction", "N/A")).title())


def render(city: str, days: int) -> None:
    _ = days
    st.title("Compare Cities")

    default_index = 1 if city == "Delhi" else 0
    city2 = st.selectbox("Select second city", options=CITIES, index=default_index)

    if city2 == city:
        st.info("Choose a different city to compare.")
        return

    response = compare_cities(city, city2)
    if response is None:
        st.warning("Comparison data is unavailable right now.")
        return

    col1, col2 = st.columns(2)
    with col1:
        _render_stats_column(city, response.get("city1_stats", {}))
    with col2:
        _render_stats_column(city2, response.get("city2_stats", {}))
