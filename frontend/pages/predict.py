from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import plotly.graph_objects as go
import streamlit as st

try:
    from frontend.api_client import predict_aqi
except ModuleNotFoundError:
    ROOT_DIR = Path(__file__).resolve().parents[2]
    if str(ROOT_DIR) not in sys.path:
        sys.path.append(str(ROOT_DIR))
    from frontend.api_client import predict_aqi

_ = predict_aqi

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


def _show_health_banner(health_category: str) -> None:
    category = (health_category or "").strip().lower()

    if category in {"good", "satisfactory", "moderate"}:
        st.success(f"Health Category: {health_category}")
        return

    if category in {"poor", "unhealthy"}:
        st.warning(f"Health Category: {health_category}")
        return

    st.error(f"Health Category: {health_category}")


def _extract_shap_items(shap_values: Any) -> list[tuple[str, float]]:
    if isinstance(shap_values, dict):
        extracted: list[tuple[str, float]] = []
        for key, value in shap_values.items():
            try:
                extracted.append((str(key), float(value)))
            except (TypeError, ValueError):
                continue
        return extracted

    if isinstance(shap_values, list):
        extracted_list: list[tuple[str, float]] = []
        for item in shap_values:
            if isinstance(item, dict):
                feature = item.get("feature") or item.get("name")
                value = item.get("value")
                if feature is None:
                    continue
                try:
                    extracted_list.append((str(feature), float(value)))
                except (TypeError, ValueError):
                    continue
        return extracted_list

    return []


def _render_shap_chart(shap_values: Any) -> None:
    items = _extract_shap_items(shap_values)
    if not items:
        return

    # Sort by absolute contribution for a clearer local explanation.
    items = sorted(items, key=lambda x: abs(x[1]), reverse=True)
    features = [f for f, _ in items]
    values = [v for _, v in items]

    colors = ["#d62728" if v > 0 else "#1f77b4" for v in values]

    fig = go.Figure(
        data=[
            go.Bar(
                x=values,
                y=features,
                orientation="h",
                marker_color=colors,
                text=[f"{v:+.2f}" for v in values],
                textposition="outside",
            )
        ]
    )
    fig.update_layout(
        title="SHAP Feature Contributions",
        xaxis_title="Contribution to AQI",
        yaxis_title="Feature",
        template="plotly_white",
        height=max(300, 34 * len(features) + 120),
    )

    st.plotly_chart(fig, use_container_width=True)


def render_predict(client) -> None:
    st.title("Predict AQI")

    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.subheader("Input Parameters")

        city = st.selectbox("City", options=CITIES, index=0)

        pm25 = st.number_input("PM2.5", min_value=0.0, max_value=1000.0, value=120.0, step=1.0)
        pm10 = st.number_input("PM10", min_value=0.0, max_value=1500.0, value=200.0, step=1.0)
        no2 = st.number_input("NO2", min_value=0.0, max_value=1000.0, value=45.0, step=1.0)
        so2 = st.number_input("SO2", min_value=0.0, max_value=1500.0, value=18.0, step=1.0)

        temperature = st.number_input("Temperature (C)", min_value=-50.0, max_value=60.0, value=30.0, step=0.5)
        humidity = st.number_input("Humidity (%)", min_value=0.0, max_value=100.0, value=60.0, step=1.0)
        wind_speed = st.number_input("Wind Speed (km/h)", min_value=0.0, max_value=150.0, value=8.0, step=0.5)

        predict_clicked = st.button("Predict AQI", type="primary")

    with right_col:
        st.subheader("Results")

        if not predict_clicked:
            st.info("Submit the form to view prediction results.")
            return

        with st.spinner("Predicting..."):
            response = client.predict_aqi(
                city=city,
                pm25=pm25,
                pm10=pm10,
                no2=no2,
                so2=so2,
                temperature=temperature,
                humidity=humidity,
                wind_speed=wind_speed,
            )

        if response is None:
            st.error("Prediction service is currently unavailable.")
            return

        predicted_aqi = response.get("predicted_aqi", response.get("aqi"))
        lower = response.get("confidence_lower", response.get("lower_bound"))
        upper = response.get("confidence_upper", response.get("upper_bound"))
        category = str(response.get("health_category", "Unknown"))

        if predicted_aqi is None:
            st.error("Prediction response did not contain AQI value.")
            return

        st.metric("Predicted AQI", f"{float(predicted_aqi):.2f}")

        b1, b2 = st.columns(2)
        b1.metric("Lower Bound", f"{float(lower):.2f}" if lower is not None else "N/A")
        b2.metric("Upper Bound", f"{float(upper):.2f}" if upper is not None else "N/A")

        _show_health_banner(category)

        actions = response.get("recommended_actions") or response.get("recommendations") or []
        if actions:
            st.subheader("Recommended Actions")
            bullet_text = "\n".join(f"- {str(action)}" for action in actions)
            st.info(bullet_text)

        shap_values = response.get("shap_values")
        if shap_values is not None:
            st.subheader("SHAP Waterfall")
            _render_shap_chart(shap_values)
