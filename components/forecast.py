from __future__ import annotations

from typing import Tuple

import pandas as pd
import plotly.graph_objects as go
from prophet import Prophet


def _build_india_holidays(start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
    years = list(range(start_date.year, end_date.year + 1))

    try:
        import prophet

        # Requested API path; fallback is handled below when unavailable.
        holidays = prophet.make_holidays(country="IN")  # type: ignore[attr-defined]
        if isinstance(holidays, pd.DataFrame) and {"ds", "holiday"}.issubset(holidays.columns):
            return holidays
    except Exception:
        pass

    from prophet.make_holidays import make_holidays_df

    return make_holidays_df(year_list=years, country="IN")


def forecast_city_aqi(
    df: pd.DataFrame,
    city: str,
    periods: int = 7,
) -> Tuple[go.Figure, pd.DataFrame]:
    """Forecast AQI for a single city and return a Plotly chart and forecast dataframe."""
    required_cols = {"date", "aqi_value", "city"}
    missing = required_cols.difference(df.columns)
    if missing:
        raise ValueError(
            "Input dataframe is missing required columns: "
            + ", ".join(sorted(missing))
        )

    city_df = df[df["city"].astype(str) == str(city)].copy()
    if city_df.empty:
        raise ValueError(f"No records found for city: {city}")

    city_df["date"] = pd.to_datetime(city_df["date"], errors="coerce")
    city_df["aqi_value"] = pd.to_numeric(city_df["aqi_value"], errors="coerce")
    city_df = city_df.dropna(subset=["date", "aqi_value"]).sort_values("date")

    if city_df.empty:
        raise ValueError(f"No valid date/aqi_value rows available after cleaning for city: {city}")

    prophet_df = city_df[["date", "aqi_value"]].rename(
        columns={"date": "ds", "aqi_value": "y"}
    )

    last_horizon_date = prophet_df["ds"].max() + pd.Timedelta(days=periods)
    holidays_df = _build_india_holidays(prophet_df["ds"].min(), last_horizon_date)

    model = Prophet(holidays=holidays_df, interval_width=0.90)
    model.fit(prophet_df)

    future = model.make_future_dataframe(periods=periods, freq="D")
    forecast = model.predict(future)

    history_last_date = prophet_df["ds"].max()
    forecast_7d = forecast[forecast["ds"] > history_last_date].head(periods).copy()

    result_df = forecast_7d[["ds", "yhat", "yhat_lower", "yhat_upper"]].rename(
        columns={
            "ds": "date",
            "yhat": "predicted_aqi",
            "yhat_lower": "lower_bound",
            "yhat_upper": "upper_bound",
        }
    )
    result_df["city"] = city
    result_df = result_df[["date", "city", "predicted_aqi", "lower_bound", "upper_bound"]]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=prophet_df["ds"],
            y=prophet_df["y"],
            mode="lines+markers",
            name="Historical AQI",
            line=dict(color="#1f77b4", width=2),
            marker=dict(size=5),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=forecast["ds"],
            y=forecast["yhat"],
            mode="lines",
            name="Forecast AQI",
            line=dict(color="#8b0000", width=2),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=forecast["ds"],
            y=forecast["yhat_upper"],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=forecast["ds"],
            y=forecast["yhat_lower"],
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(139, 0, 0, 0.18)",
            name="Uncertainty Band",
        )
    )

    fig.update_layout(
        title=f"AQI Forecast for {city} (Next {periods} Days)",
        xaxis_title="Date",
        yaxis_title="AQI",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )

    return fig, result_df
