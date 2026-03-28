from __future__ import annotations

import pandas as pd
from prophet import Prophet


def _aqi_health_category(aqi: float) -> str:
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Moderate"
    if aqi <= 200:
        return "Unhealthy"
    if aqi <= 300:
        return "Very Unhealthy"
    return "Hazardous"


def _aqi_advisory(category: str) -> str:
    mapping = {
        "Good": "Air quality is acceptable for outdoor activities.",
        "Moderate": "Sensitive groups should limit prolonged outdoor exertion.",
        "Unhealthy": "Reduce prolonged outdoor activity and use protective masks.",
        "Very Unhealthy": "Avoid strenuous outdoor activity and stay indoors when possible.",
        "Hazardous": "Remain indoors and follow local health advisories.",
    }
    return mapping.get(category, "Monitor AQI updates and limit exposure when needed.")


def _build_india_holidays(start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
    years = list(range(start_date.year, end_date.year + 1))

    try:
        import prophet

        holidays = prophet.make_holidays(country="IN")  # type: ignore[attr-defined]
        if isinstance(holidays, pd.DataFrame) and {"ds", "holiday"}.issubset(holidays.columns):
            return holidays
    except Exception:
        pass

    from prophet.make_holidays import make_holidays_df

    return make_holidays_df(year_list=years, country="IN")


def generate_forecast(city_df: pd.DataFrame, city_name: str, periods: int = 7) -> list[dict]:
    """Generate AQI forecast list for the next N days using Prophet."""
    df = city_df.copy()
    cols = set(df.columns)
    if {"ds", "y"}.issubset(cols):
        df["ds"] = pd.to_datetime(df["ds"], errors="coerce")
        df["y"] = pd.to_numeric(df["y"], errors="coerce")
        prophet_df = df[["ds", "y"]].dropna(subset=["ds", "y"]).sort_values("ds")
    elif {"date", "aqi_value"}.issubset(cols):
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["aqi_value"] = pd.to_numeric(df["aqi_value"], errors="coerce")
        df = df.dropna(subset=["date", "aqi_value"]).sort_values("date")
        prophet_df = df[["date", "aqi_value"]].rename(columns={"date": "ds", "aqi_value": "y"})
    else:
        raise ValueError(
            "city_df is missing required columns. Expected either 'ds'/'y' or 'date'/'aqi_value'."
        )

    if prophet_df.empty:
        raise ValueError(f"No valid rows available for city '{city_name}' after cleaning.")

    end_horizon = prophet_df["ds"].max() + pd.Timedelta(days=periods)
    holidays_df = _build_india_holidays(prophet_df["ds"].min(), end_horizon)

    model = Prophet(holidays=holidays_df, interval_width=0.90)
    model.fit(prophet_df)

    future = model.make_future_dataframe(periods=periods, freq="D")
    forecast = model.predict(future)

    last_observed = prophet_df["ds"].max()
    future_forecast = forecast[forecast["ds"] > last_observed].head(periods).copy()

    results: list[dict] = []
    for _, row in future_forecast.iterrows():
        dt = pd.to_datetime(row["ds"]).date()
        predicted = float(row["yhat"])
        lower = float(row["yhat_lower"])
        upper = float(row["yhat_upper"])
        category = _aqi_health_category(predicted)

        results.append(
            {
                "date": dt.isoformat(),
                "day_name": pd.to_datetime(dt).day_name(),
                "predicted_aqi": predicted,
                "lower_bound": lower,
                "upper_bound": upper,
                "health_category": category,
                "advisory": _aqi_advisory(category),
            }
        )

    return results
