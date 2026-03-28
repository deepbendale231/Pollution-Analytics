from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    from frontend import api_client
    from frontend.api_client import get_forecast
except ModuleNotFoundError:
    ROOT_DIR = Path(__file__).resolve().parents[2]
    if str(ROOT_DIR) not in sys.path:
        sys.path.append(str(ROOT_DIR))
    from frontend import api_client
    from frontend.api_client import get_forecast


def _aqi_category(aqi: float) -> str:
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


def _category_color(category: str) -> str:
    color_map = {
        "Good": "#2E8B57",
        "Satisfactory": "#F4D03F",
        "Moderate": "#E67E22",
        "Poor": "#E74C3C",
        "Very Poor": "#8E44AD",
        "Severe": "#800000",
    }
    return color_map.get(category, "#5D6D7E")


def _advisory(category: str) -> str:
    messages = {
        "Good": "Air quality is comfortable for outdoor activity.",
        "Satisfactory": "Sensitive individuals should monitor prolonged exposure.",
        "Moderate": "Reduce prolonged outdoor exertion, especially near traffic.",
        "Poor": "Limit outdoor activity and use masks when outside.",
        "Very Poor": "Avoid strenuous activity outdoors and protect indoor air quality.",
        "Severe": "Stay indoors as much as possible and follow public advisories.",
    }
    return messages.get(category, "Monitor AQI updates and limit exposure.")


def render_forecast(client, city: str) -> None:
    st.title("Forecast")
    st.caption(f"7-day AQI forecast for {city}")

    response = client.get_forecast(city, days=7)
    if response is None:
        st.warning("Forecast is unavailable right now.")
        return

    forecast = response.get("forecast", [])
    if not forecast:
        st.info("No forecast points returned.")
        return

    df = pd.DataFrame(forecast)
    df["date"] = pd.to_datetime(df.get("date"), errors="coerce")
    df["predicted_aqi"] = pd.to_numeric(df.get("predicted_aqi"), errors="coerce")
    df["lower_bound"] = pd.to_numeric(df.get("lower_bound"), errors="coerce")
    df["upper_bound"] = pd.to_numeric(df.get("upper_bound"), errors="coerce")
    df["health_category"] = df.get("health_category", "")
    df["day_name"] = df.get("day_name", pd.to_datetime(df["date"], errors="coerce").dt.day_name())
    df["advisory"] = df.get("advisory", "")
    df = df.dropna(subset=["date", "predicted_aqi", "lower_bound", "upper_bound"]).sort_values("date")

    if df.empty:
        st.info("No valid forecast rows available.")
        return

    # Display-friendly date text (no time component).
    df["date_display"] = pd.to_datetime(df["date"]).dt.strftime("%b %d, %Y")

    peak_idx = df["predicted_aqi"].idxmax()
    best_idx = df["predicted_aqi"].idxmin()

    col1, col2, col3 = st.columns(3)
    col1.metric("📈 Peak Forecast", f"{df['predicted_aqi'].max():.0f}", df.loc[peak_idx, "date_display"])
    col2.metric("📉 Best Day", f"{df['predicted_aqi'].min():.0f}", df.loc[best_idx, "date_display"])
    col3.metric("📊 7-Day Average", f"{df['predicted_aqi'].mean():.0f}")

    # Ribbon-style chart with uncertainty band.
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=pd.concat([df["date"], df["date"][::-1]]),
            y=pd.concat([df["upper_bound"], df["lower_bound"][::-1]]),
            fill="toself",
            fillcolor="rgba(255, 100, 100, 0.15)",
            line=dict(color="rgba(255,255,255,0)"),
            name="Confidence Band",
            showlegend=True,
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["lower_bound"],
            line=dict(color="rgba(100,100,255,0.4)", width=1, dash="dot"),
            name="Lower Bound",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["upper_bound"],
            line=dict(color="rgba(255,100,100,0.4)", width=1, dash="dot"),
            name="Upper Bound",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["predicted_aqi"],
            mode="lines+markers",
            line=dict(color="#ff4444", width=3),
            marker=dict(size=7, color="#ff4444"),
            name="Predicted AQI",
        )
    )

    fig.add_hline(y=100, line_dash="dash", line_color="orange", annotation_text="Moderate threshold (100)")
    fig.add_hline(y=200, line_dash="dash", line_color="red", annotation_text="Poor threshold (200)")

    fig.update_layout(
        title=f"7-Day AQI Forecast — {city}",
        xaxis_title="Date",
        yaxis_title="AQI",
        height=420,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="rgba(200,200,200,0.2)"),
        xaxis=dict(gridcolor="rgba(200,200,200,0.2)"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Styled forecast table.
    category_colors = {
        "Good": "#00b050",
        "Satisfactory": "#92d050",
        "Moderate": "#ffff00",
        "Poor": "#ff7c00",
        "Very Unhealthy": "#ff0000",
        "Hazardous": "#7030a0",
        "Severe": "#7030a0",
        "Very Poor": "#7030a0",
    }
    row_colors = [category_colors.get(str(c), "#ffffff") for c in df["health_category"]]

    fig_table = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=["Date", "Day", "Predicted AQI", "Lower", "Upper", "Category", "Advisory"],
                    fill_color="#1a1a2e",
                    font=dict(color="white", size=13),
                    align="left",
                    height=36,
                ),
                cells=dict(
                    values=[
                        df["date_display"],
                        df["day_name"],
                        df["predicted_aqi"].round(1),
                        df["lower_bound"].round(1),
                        df["upper_bound"].round(1),
                        df["health_category"],
                        df["advisory"],
                    ],
                    fill_color=[
                        ["#f9f9f9"] * len(df),
                        ["#f9f9f9"] * len(df),
                        row_colors,
                        ["#f9f9f9"] * len(df),
                        ["#f9f9f9"] * len(df),
                        row_colors,
                        ["#f9f9f9"] * len(df),
                    ],
                    font=dict(size=12),
                    align="left",
                    height=32,
                ),
            )
        ]
    )
    fig_table.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=280)
    st.plotly_chart(fig_table, use_container_width=True)

    # CSV download kept unchanged.
    table_df = pd.DataFrame(
        {
            "Date": df["date_display"],
            "Day": df["day_name"],
            "Predicted AQI": df["predicted_aqi"],
            "Lower": df["lower_bound"],
            "Upper": df["upper_bound"],
            "Category": df["health_category"],
            "Advisory": df["advisory"],
        }
    )

    st.subheader("Forecast Data")

    csv_data = table_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Forecast CSV",
        data=csv_data,
        file_name=f"{city.lower()}_7_day_forecast.csv",
        mime="text/csv",
    )


def render(city: str, days: int) -> None:
    _ = days
    render_forecast(api_client, city)
