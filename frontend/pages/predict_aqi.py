from __future__ import annotations

import streamlit as st

from frontend.api_client import predict_aqi


def render(city: str, days: int) -> None:
    _ = days
    st.title("Predict AQI")
    st.caption(f"Run a one-off AQI prediction for {city}")

    col1, col2, col3 = st.columns(3)
    pm25 = col1.number_input("PM2.5", min_value=0.0, value=80.0, step=1.0)
    pm10 = col2.number_input("PM10", min_value=0.0, value=140.0, step=1.0)
    no2 = col3.number_input("NO2", min_value=0.0, value=35.0, step=1.0)

    col4, col5, col6, col7 = st.columns(4)
    so2 = col4.number_input("SO2", min_value=0.0, value=12.0, step=1.0)
    temperature = col5.number_input("Temperature (C)", value=30.0, step=0.5)
    humidity = col6.number_input("Humidity (%)", min_value=0.0, max_value=100.0, value=60.0, step=1.0)
    wind_speed = col7.number_input("Wind Speed", min_value=0.0, value=8.0, step=0.5)

    if st.button("Predict", type="primary"):
        result = predict_aqi(
            city=city,
            pm25=pm25,
            pm10=pm10,
            no2=no2,
            so2=so2,
            temperature=temperature,
            humidity=humidity,
            wind_speed=wind_speed,
        )
        if result is None:
            st.warning("Prediction is unavailable right now.")
            return

        predicted = result.get("predicted_aqi", result.get("aqi"))
        lower = result.get("lower_bound", result.get("confidence_lower"))
        upper = result.get("upper_bound", result.get("confidence_upper"))

        if predicted is None:
            st.error("Prediction response did not contain AQI value.")
            return

        c1, c2, c3 = st.columns(3)
        c1.metric("Predicted AQI", f"{float(predicted):.2f}")
        c2.metric("Lower Bound", f"{float(lower):.2f}" if lower is not None else "N/A")
        c3.metric("Upper Bound", f"{float(upper):.2f}" if upper is not None else "N/A")

        st.subheader("Health Category")
        st.write(result.get("health_category", "Unknown"))

        st.subheader("Recommended Actions")
        for action in result.get("recommended_actions", []):
            st.write(f"- {action}")
