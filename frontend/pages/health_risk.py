"""Health risk page with impact visualizations and advisories."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import streamlit as st

try:
    from frontend.api_client import get_city_pollutants, get_city_stats
    from frontend.components.health_impact import (
        cigarettes_equivalent,
        get_activity_advisory,
        get_mask_recommendation,
        safe_outdoor_hours,
    )
except ModuleNotFoundError:
    ROOT_DIR = Path(__file__).resolve().parents[2]
    if str(ROOT_DIR) not in sys.path:
        sys.path.append(str(ROOT_DIR))
    from frontend.api_client import get_city_pollutants, get_city_stats
    from frontend.components.health_impact import (
        cigarettes_equivalent,
        get_activity_advisory,
        get_mask_recommendation,
        safe_outdoor_hours,
    )


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _render_cigarette_impact(pm25_value: float) -> None:
    st.subheader("PM2.5 Health Impact")
    cig = cigarettes_equivalent(pm25_value)

    full_icons = min(int(round(cig)), 20)
    overflow = max(int(round(cig)) - 20, 0)

    icon_line = "🚬" * full_icons if full_icons > 0 else "No visible cigarette-equivalent impact"
    if overflow > 0:
        icon_line = f"{icon_line} + {overflow} more"

    st.markdown(
        f"**Equivalent cigarette exposure (daily): {cig:.1f}**\n\n{icon_line}"
    )


def _render_safe_hours(aqi: float) -> None:
    st.subheader("Safe Outdoor Hours by Group")
    hours = safe_outdoor_hours(aqi)

    groups = [
        ("Healthy Adults", "healthy_adult"),
        ("Children", "child"),
        ("Seniors", "elderly"),
        ("Asthma/COPD", "asthmatic"),
    ]

    cols = st.columns(4)
    for idx, (label, key) in enumerate(groups):
        value = float(hours.get(key, 0.0))
        if value >= 6:
            color = "#2e7d32"
            badge = "Safe"
        elif value >= 2:
            color = "#f9a825"
            badge = "Caution"
        else:
            color = "#c62828"
            badge = "Limit"

        with cols[idx]:
            st.markdown(
                f"""
<div style=\"padding:14px;border-radius:10px;background:{color};color:white;\">
    <div style=\"font-size:0.95rem;font-weight:600;\">{label}</div>
  <div style=\"font-size:1.35rem;font-weight:700;\">{value:.1f} hrs</div>
  <div style=\"font-size:0.85rem;opacity:0.95;\">{badge}</div>
</div>
""",
                unsafe_allow_html=True,
            )


def _render_mask_recommendation(aqi: float) -> None:
    st.subheader("Mask Recommendation")
    recommendation = get_mask_recommendation(aqi)

    if recommendation.startswith("Mandatory"):
        st.error(recommendation)
    elif recommendation.startswith("Recommended"):
        st.warning(recommendation)
    else:
        st.info(recommendation)


def _render_activity_advisory(aqi: float) -> None:
    st.subheader("Activity Advisory")
    advisory = get_activity_advisory(aqi)

    for group, guidance in advisory.items():
        with st.expander(group, expanded=False):
            st.write(guidance)


def _extract_health_snapshot(city: str, days: int) -> tuple[float | None, float | None]:
    try:
        stats_payload = get_city_stats(city, days=days)
        pollutants_payload = get_city_pollutants(city)

        aqi = None
        pm25 = None

        if isinstance(stats_payload, dict):
            aqi = _to_float(stats_payload.get("aqi") or stats_payload.get("mean_aqi") or stats_payload.get("average_aqi"))

        if isinstance(pollutants_payload, dict):
            pollutant_averages = pollutants_payload.get("pollutant_averages", {})
            if isinstance(pollutant_averages, dict):
                pm25 = _to_float(
                    pollutant_averages.get("pm25")
                    or pollutant_averages.get("pm2_5")
                    or pollutant_averages.get("PM2.5")
                )

        return aqi, pm25
    except Exception:
        return None, None


def render(city: str, days: int) -> None:
    st.title("Health Risk Insights")

    st.caption(f"Health impact view for {city} over the last {days} days")

    aqi, pm25 = _extract_health_snapshot(city, days)

    if aqi is None:
        st.warning("Could not fetch city-specific AQI from API. Using fallback AQI: 150.")
        aqi = 150.0
    if pm25 is None:
        st.warning("Could not fetch city-specific PM2.5 from API. Using fallback PM2.5: 60 ug/m3.")
        pm25 = 60.0

    st.markdown(f"**City:** {city}  ")
    st.markdown(f"**Current AQI:** {aqi:.1f} | **PM2.5:** {pm25:.1f} ug/m3")

    _render_cigarette_impact(pm25)
    st.markdown("---")

    _render_safe_hours(aqi)
    st.markdown("---")

    _render_mask_recommendation(aqi)
    st.markdown("---")

    _render_activity_advisory(aqi)
