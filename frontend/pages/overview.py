"""Overview page for Pollution Analytics dashboard."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from frontend.api_client import get_city_ranking, get_city_stats
from frontend.components.india_map import create_aqi_map


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _city_coordinates() -> dict[str, tuple[float, float]]:
    # Fallback coordinates for common Indian cities when API doesn't provide lat/lon.
    return {
        "Delhi": (28.6139, 77.2090),
        "Mumbai": (19.0760, 72.8777),
        "Bengaluru": (12.9716, 77.5946),
        "Bangalore": (12.9716, 77.5946),
        "Kolkata": (22.5726, 88.3639),
        "Chennai": (13.0827, 80.2707),
        "Hyderabad": (17.3850, 78.4867),
        "Pune": (18.5204, 73.8567),
        "Ahmedabad": (23.0225, 72.5714),
        "Jaipur": (26.9124, 75.7873),
        "Lucknow": (26.8467, 80.9462),
        "Kanpur": (26.4499, 80.3319),
        "Nagpur": (21.1458, 79.0882),
        "Bhopal": (23.2599, 77.4126),
        "Patna": (25.5941, 85.1376),
        "Surat": (21.1702, 72.8311),
        "Visakhapatnam": (17.6868, 83.2185),
        "Vadodara": (22.3072, 73.1812),
        "Indore": (22.7196, 75.8577),
        "Thane": (19.2183, 72.9781),
        "Nashik": (19.9975, 73.7898),
        "Coimbatore": (11.0168, 76.9558),
        "Kochi": (9.9312, 76.2673),
        "Guwahati": (26.1445, 91.7362),
        "Chandigarh": (30.7333, 76.7794),
    }


def _build_city_aqi_dict(ranking: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    city_aqi: dict[str, dict[str, Any]] = {}
    coord_map = _city_coordinates()

    for row in ranking:
        city = str(row.get("city") or row.get("city_name") or "").strip()
        if not city:
            continue

        aqi = _to_float(row.get("aqi") or row.get("average_aqi") or row.get("avg_aqi"))
        if aqi is None:
            continue

        lat = _to_float(row.get("latitude") or row.get("lat"))
        lon = _to_float(row.get("longitude") or row.get("lon") or row.get("lng"))

        if lat is None or lon is None:
            fallback = coord_map.get(city)
            if fallback is not None:
                lat, lon = fallback

        if lat is None or lon is None:
            continue

        city_aqi[city] = {
            "aqi": aqi,
            "lat": lat,
            "lon": lon,
            "last_updated": row.get("last_updated"),
        }

    return city_aqi


def _render_metrics(overview: dict[str, Any], total_cities: int, total_records: int) -> None:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Avg AQI", f"{_to_float(overview.get('avg_aqi') or overview.get('mean_aqi')) or 0:.1f}")
    with col2:
        st.metric("Worst City AQI", f"{_to_float(overview.get('worst_city_aqi')) or 0:.1f}")
    with col3:
        st.metric("Total Cities", total_cities)
    with col4:
        st.metric("Total Records", total_records)


def _render_rankings(ranking: list[dict[str, Any]]) -> None:
    if not ranking:
        st.info("No city ranking data available.")
        return

    st.subheader("Top Cities by AQI")
    st.caption("Enhanced CPCB-styled table view")

    def _cpcb_color(aqi: float | None) -> str:
        if aqi is None:
            return "#9E9E9E"
        if aqi <= 50:
            return "#2E7D32"  # green
        if aqi <= 100:
            return "#D4A900"  # yellow
        if aqi <= 200:
            return "#F57C00"  # orange
        if aqi <= 300:
            return "#C62828"  # red
        if aqi <= 400:
            return "#6A1B9A"  # purple
        return "#8B0000"  # dark red

    def _format_rank(idx: int) -> str:
        rank_value = idx + 1
        if rank_value == 1:
            return "🥇"
        if rank_value == 2:
            return "🥈"
        if rank_value == 3:
            return "🥉"
        return str(rank_value)

    def _format_aqi(value: float | None) -> str:
        if value is None:
            return "—"
        return f"<b>{value:.1f}</b>"

    def _format_vs_last_month(value: float | None) -> str:
        if value is None:
            return "<span style='color:#9E9E9E'>—</span>"
        return f"{value:.1f}"

    def _format_change(value: float | None) -> str:
        if value is None:
            return "⚪ —"
        if value > 0:
            return f"🔴 +{value:.1f}"
        if value < 0:
            return f"🟢 {value:.1f}"
        return "⚪ 0.0"

    rows: list[dict[str, Any]] = []
    avg_column_colors: list[str] = []
    default_cell_color = "#F7F7F7"

    sorted_ranking = sorted(
        ranking,
        key=lambda row: _to_float(row.get("average_aqi") or row.get("avg_aqi") or row.get("aqi")) or -1,
        reverse=True,
    )

    for idx, row in enumerate(sorted_ranking):
        city = str(row.get("city") or row.get("city_name") or "—")
        avg_aqi = _to_float(row.get("average_aqi") or row.get("avg_aqi") or row.get("aqi"))
        prev_aqi = _to_float(row.get("previous_month_average_aqi"))
        delta = _to_float(row.get("delta_vs_previous_month"))

        rows.append(
            {
                "#": _format_rank(idx),
                "City": city,
                "Avg AQI": _format_aqi(avg_aqi),
                "vs Last Month": _format_vs_last_month(prev_aqi),
                "Change": _format_change(delta),
            }
        )
        avg_column_colors.append(_cpcb_color(avg_aqi))

    table = go.Figure(
        data=[
            go.Table(
                columnwidth=[0.7, 2.0, 1.3, 1.6, 1.4],
                header=dict(
                    values=["#", "City", "Avg AQI", "vs Last Month", "Change"],
                    fill_color="#0F172A",
                    font=dict(color="white", size=13),
                    align=["center", "left", "center", "center", "center"],
                    height=40,
                ),
                cells=dict(
                    values=[
                        [r["#"] for r in rows],
                        [r["City"] for r in rows],
                        [r["Avg AQI"] for r in rows],
                        [r["vs Last Month"] for r in rows],
                        [r["Change"] for r in rows],
                    ],
                    fill_color=[
                        [default_cell_color] * len(rows),
                        [default_cell_color] * len(rows),
                        avg_column_colors,
                        [default_cell_color] * len(rows),
                        [default_cell_color] * len(rows),
                    ],
                    font=dict(
                        color=[
                            ["#111827"] * len(rows),
                            ["#111827"] * len(rows),
                            ["white"] * len(rows),
                            ["#111827"] * len(rows),
                            ["#111827"] * len(rows),
                        ],
                        size=12,
                    ),
                    align=["center", "left", "center", "center", "center"],
                    height=36,
                ),
            )
        ]
    )

    table.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=max(280, 48 + (len(rows) * 36)))
    st.plotly_chart(table, use_container_width=True)

    st.markdown(
        """
        <div style="display:flex;flex-wrap:nowrap;gap:8px;overflow-x:auto;padding-top:6px;">
            <span style="background:#2E7D32;color:#fff;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:700;">0-50 Good</span>
            <span style="background:#D4A900;color:#fff;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:700;">51-100 Satisfactory</span>
            <span style="background:#F57C00;color:#fff;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:700;">101-200 Moderate</span>
            <span style="background:#C62828;color:#fff;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:700;">201-300 Poor</span>
            <span style="background:#6A1B9A;color:#fff;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:700;">301-400 Very Poor</span>
            <span style="background:#8B0000;color:#fff;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:700;">401+ Severe</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _warn_api_result(data: Any, label: str) -> None:
    if data is None:
        st.warning(f"{label}: API call returned None — check terminal logs")
        return

    try:
        if len(data) == 0:
            st.warning(f"{label}: API returned empty list — database may have no records")
    except TypeError:
        return


def render(city: str, days: int) -> None:
    st.title("Pollution Overview")

    try:
        overview = get_city_stats(city, days=days)
        _warn_api_result(overview, "City stats")
    except Exception as exc:
        st.error(f"Unable to load overview data: {exc}")
        return

    if not isinstance(overview, dict):
        overview = {}

    try:
        ranking_payload = get_city_ranking()
        _warn_api_result(ranking_payload, "City ranking")
        if isinstance(ranking_payload, dict):
            ranking = ranking_payload.get("rankings", [])
        elif isinstance(ranking_payload, list):
            ranking = ranking_payload
        else:
            ranking = []

        if not isinstance(ranking, list):
            ranking = []
    except Exception as exc:
        st.warning(f"Could not load city ranking for map: {exc}")
        ranking = []

    total_cities = len(ranking)
    total_records = int(sum(_to_float(row.get("readings_count")) or 0 for row in ranking))
    if total_records == 0 and total_cities > 0:
        total_records = total_cities
    worst_city_aqi = max((_to_float(row.get("aqi") or row.get("average_aqi")) or 0 for row in ranking), default=0)
    overview["worst_city_aqi"] = worst_city_aqi

    _render_metrics(overview, total_cities=total_cities, total_records=total_records)

    st.markdown("---")
    st.subheader("Live AQI Map Across India")

    city_aqi_dict = _build_city_aqi_dict(ranking)
    if city_aqi_dict:
        india_map = create_aqi_map(city_aqi_dict)
        st_folium(india_map, width=None, height=500)
    else:
        st.info("City location data is currently unavailable for map rendering.")

    st.markdown("---")
    _render_rankings(ranking)
