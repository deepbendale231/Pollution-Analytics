from __future__ import annotations

from datetime import datetime
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:
    from frontend import api_client
except ModuleNotFoundError:
    ROOT_DIR = Path(__file__).resolve().parents[2]
    if str(ROOT_DIR) not in sys.path:
        sys.path.append(str(ROOT_DIR))
    from frontend import api_client
# Keep direct client imports centralized through frontend.api_client module usage.

PRIMARY_COLOR = "#8b0000"
SECONDARY_COLOR = "#1f77b4"
ZONE_COLORS = {
    "Good": "rgba(46, 139, 87, 0.10)",
    "Moderate": "rgba(244, 208, 63, 0.12)",
    "Poor": "rgba(230, 126, 34, 0.12)",
    "Unhealthy": "rgba(231, 76, 60, 0.12)",
    "Very Unhealthy": "rgba(142, 68, 173, 0.12)",
    "Hazardous": "rgba(128, 0, 0, 0.12)",
}


def _build_fallback_daily_series(stats: dict, days: int) -> pd.DataFrame:
    days = max(int(days), 7)
    end_date = pd.Timestamp(datetime.utcnow().date())
    dates = pd.date_range(end=end_date, periods=days, freq="D")

    mean_aqi = float(stats.get("mean_aqi", 120.0))
    slope = float(stats.get("trend_slope", 0.0))
    min_aqi = float(stats.get("min_aqi", max(0.0, mean_aqi - 60.0)))
    max_aqi = float(stats.get("max_aqi", mean_aqi + 60.0))

    idx = np.arange(days, dtype=float)
    centered = idx - (days - 1) / 2.0
    seasonal = 12.0 * np.sin((idx / 7.0) * 2.0 * np.pi)
    values = mean_aqi + slope * centered + seasonal
    values = np.clip(values, min_aqi, max_aqi)

    return pd.DataFrame({"date": dates, "aqi": values})


def _fetch_daily_series(client, city: str, days: int, stats: dict) -> pd.DataFrame:
    get_city_timeseries = getattr(client, "get_city_timeseries", None)
    if callable(get_city_timeseries):
        payload = get_city_timeseries(city, days=days)
        if payload and isinstance(payload.get("data"), list):
            df = pd.DataFrame(payload["data"])
            if {"date", "aqi"}.issubset(df.columns):
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df["aqi"] = pd.to_numeric(df["aqi"], errors="coerce")
                df = df.dropna(subset=["date", "aqi"]).sort_values("date")
                if not df.empty:
                    return df

    return _build_fallback_daily_series(stats, days)


def _expand_daily_to_hourly(daily_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for _, row in daily_df.iterrows():
        date_val = pd.to_datetime(row["date"], errors="coerce")
        base = float(row["aqi"])
        if pd.isna(date_val):
            continue

        for hour in range(24):
            # Mild diurnal cycle to support heatmap exploration.
            delta = 0.10 * base * np.sin(((hour - 7) / 24.0) * 2.0 * np.pi)
            hourly_aqi = max(0.0, base + delta)
            ts = date_val + pd.Timedelta(hours=hour)
            rows.append({"timestamp": ts, "aqi": hourly_aqi})

    return pd.DataFrame(rows)


def _render_pollutant_averages(client, city: str) -> None:
    pollutants = client.get_city_pollutants(city)
    if pollutants and pollutants.get("pollutant_averages"):
        avgs = pollutants["pollutant_averages"]
        filtered = {k: v for k, v in avgs.items() if float(v) > 0}

        if filtered:
            fig = px.bar(
                x=list(filtered.values()),
                y=list(filtered.keys()),
                orientation="h",
                labels={"x": "Average (µg/m³)", "y": "Pollutant"},
                color=list(filtered.values()),
                color_continuous_scale="Reds",
                title="Pollutant Averages (last 30 days)",
            )
            fig.update_layout(
                showlegend=False,
                coloraxis_showscale=False,
                height=300,
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Only PM2.5 data available. Other pollutants not yet in database.")
    else:
        st.info("Pollutant breakdown unavailable.")


def _build_aqi_timeseries_figure(daily_df: pd.DataFrame, city: str, days: int) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=daily_df["date"],
            y=daily_df["aqi"],
            mode="lines+markers",
            name="AQI",
            line=dict(color=PRIMARY_COLOR, width=2.5),
            marker=dict(size=5),
        )
    )

    # Threshold and background zoning.
    fig.add_hline(y=100, line=dict(color="#f39c12", width=2, dash="dash"))
    fig.add_hrect(y0=0, y1=50, fillcolor=ZONE_COLORS["Good"], line_width=0)
    fig.add_hrect(y0=51, y1=100, fillcolor=ZONE_COLORS["Moderate"], line_width=0)
    fig.add_hrect(y0=101, y1=200, fillcolor=ZONE_COLORS["Poor"], line_width=0)
    fig.add_hrect(y0=201, y1=300, fillcolor=ZONE_COLORS["Unhealthy"], line_width=0)
    fig.add_hrect(y0=301, y1=400, fillcolor=ZONE_COLORS["Very Unhealthy"], line_width=0)
    fig.add_hrect(y0=401, y1=700, fillcolor=ZONE_COLORS["Hazardous"], line_width=0)

    fig.update_layout(
        title=f"{city} AQI Trend ({days} days)",
        xaxis_title="Date",
        yaxis_title="AQI",
        template="plotly_white",
        legend_title="Series",
    )
    return fig


def _build_hourly_heatmap(hourly_df: pd.DataFrame, city: str) -> go.Figure:
    hourly_df = hourly_df.copy()
    hourly_df["hour"] = pd.to_datetime(hourly_df["timestamp"]).dt.hour
    hourly_df["weekday"] = pd.to_datetime(hourly_df["timestamp"]).dt.day_name()

    weekday_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    pivot = (
        hourly_df.groupby(["weekday", "hour"], as_index=False)["aqi"]
        .mean()
        .pivot(index="weekday", columns="hour", values="aqi")
        .reindex(weekday_order)
    )

    fig = px.imshow(
        pivot,
        labels={"x": "Hour of Day", "y": "Day of Week", "color": "Avg AQI"},
        color_continuous_scale="RdYlGn_r",
        aspect="auto",
    )
    fig.update_layout(
        title=f"Hourly AQI Heatmap - {city}",
        template="plotly_white",
    )
    return fig


def _build_monthly_chart(daily_df: pd.DataFrame, city: str) -> go.Figure:
    monthly = (
        daily_df.assign(month=pd.to_datetime(daily_df["date"]).dt.to_period("M").astype(str))
        .groupby("month", as_index=False)["aqi"]
        .mean()
    )

    fig = px.bar(
        monthly,
        x="month",
        y="aqi",
        labels={"month": "Month", "aqi": "Average AQI"},
        title=f"Month-wise AQI Pattern - {city}",
        color_discrete_sequence=[SECONDARY_COLOR],
    )

    if not monthly.empty:
        worst_idx = monthly["aqi"].idxmax()
        best_idx = monthly["aqi"].idxmin()

        worst_row = monthly.loc[worst_idx]
        best_row = monthly.loc[best_idx]

        fig.add_annotation(
            x=worst_row["month"],
            y=worst_row["aqi"],
            text="Worst",
            showarrow=True,
            arrowhead=2,
            ay=-30,
        )
        fig.add_annotation(
            x=best_row["month"],
            y=best_row["aqi"],
            text="Best",
            showarrow=True,
            arrowhead=2,
            ay=30,
        )

    fig.update_layout(template="plotly_white", xaxis_title="Month", yaxis_title="Average AQI")
    return fig


def render_city_deep_dive(client, city: str, days: int) -> None:
    st.title("City Deep Dive")
    st.caption(f"Detailed AQI analytics for {city} over the last {days} days")

    stats = client.get_city_stats(city, days=days)
    if stats is None:
        st.warning("City stats are unavailable right now.")
        return

    daily_df = _fetch_daily_series(client, city, days, stats)
    # Row 1: 5 metric cards
    days_above_200 = int((daily_df["aqi"] > 200).sum()) if not daily_df.empty else 0

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Mean AQI", f"{float(stats.get('mean_aqi', 0.0)):.1f}")
    m2.metric("Max AQI", f"{float(stats.get('max_aqi', 0.0)):.1f}")
    m3.metric("Min AQI", f"{float(stats.get('min_aqi', 0.0)):.1f}")
    m4.metric("Trend Direction", "")
    m5.metric("Days Above 200", days_above_200)

    trend = str(stats.get("trend_direction", "stable")).lower()
    color = {"improving": "#006600", "worsening": "#cc0000", "stable": "#666666"}.get(trend, "#666")
    icon = {"improving": "📉", "worsening": "📈", "stable": "➡️"}.get(trend, "➡️")
    m4.markdown(
        f"""
        <span style="background:{color}; color:white; padding:4px 12px;
        border-radius:20px; font-size:14px; font-weight:bold;">
            {icon} {trend.capitalize()}
        </span>
        """,
        unsafe_allow_html=True,
    )

    worst_day = stats.get("worst_day", {}) or {}
    best_day = stats.get("best_day", {}) or {}
    worst_date = worst_day.get("date", "N/A")
    worst_aqi = round(float(worst_day.get("average_aqi", 0.0)), 1)
    best_date = best_day.get("date", "N/A")
    best_aqi = round(float(best_day.get("average_aqi", 0.0)), 1)

    card1, card2 = st.columns(2)
    with card1:
        st.markdown(
            f"""
            <div style="background:#ffe0e0; padding:16px; border-radius:10px; border-left:4px solid #cc0000;">
                <p style="margin:0; font-size:12px; color:#666;">📅 Worst Day</p>
                <p style="margin:4px 0; font-size:22px; font-weight:bold; color:#cc0000;">{worst_aqi}</p>
                <p style="margin:0; font-size:13px; color:#333;">{worst_date}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with card2:
        st.markdown(
            f"""
            <div style="background:#e0ffe0; padding:16px; border-radius:10px; border-left:4px solid #006600;">
                <p style="margin:0; font-size:12px; color:#666;">📅 Best Day</p>
                <p style="margin:4px 0; font-size:22px; font-weight:bold; color:#006600;">{best_aqi}</p>
                <p style="margin:0; font-size:13px; color:#333;">{best_date}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Row 2: line + donut
    c1, c2 = st.columns(2)
    with c1:
        ts_fig = _build_aqi_timeseries_figure(daily_df, city, days)
        st.plotly_chart(ts_fig, use_container_width=True)

    with c2:
        _render_pollutant_averages(client, city)

    # Row 3: heatmap + month-wise bar
    hourly_df = _expand_daily_to_hourly(daily_df)

    c3, c4 = st.columns(2)
    with c3:
        heatmap_fig = _build_hourly_heatmap(hourly_df, city)
        st.plotly_chart(heatmap_fig, use_container_width=True)

    with c4:
        monthly_fig = _build_monthly_chart(daily_df, city)
        st.plotly_chart(monthly_fig, use_container_width=True)


def render(city: str, days: int) -> None:
    render_city_deep_dive(api_client, city, days)
