from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PredictionRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "city": "Delhi",
                "pm25": 128.4,
                "pm10": 214.9,
                "no2": 42.1,
                "so2": 14.0,
                "co": 1.6,
                "temperature": 31.5,
                "humidity": 62.0,
                "wind_speed": 8.3,
            }
        },
    )

    city: str = Field(..., min_length=1, max_length=100, description="City name for AQI prediction.")
    pm25: float | None = Field(None, description="PM2.5 concentration in ug/m3.", examples=[128.4])
    pm10: float | None = Field(None, description="PM10 concentration in ug/m3.", examples=[214.9])
    no2: float | None = Field(None, description="NO2 concentration in ug/m3.", examples=[42.1])
    so2: float | None = Field(None, description="SO2 concentration in ug/m3.", examples=[14.0])
    co: float | None = Field(None, description="CO concentration in mg/m3 or configured unit.", examples=[1.6])
    temperature: float | None = Field(None, description="Ambient temperature in Celsius.", examples=[31.5])
    humidity: float | None = Field(None, description="Relative humidity percentage.", examples=[62.0])
    wind_speed: float | None = Field(None, description="Wind speed in km/h.", examples=[8.3])


    @field_validator("pm25", "pm10", "no2", "so2", "co", "humidity", "wind_speed", mode="after")
    @classmethod
    def validate_non_negative(cls, value: float | None, info):
        if value is None:
            return value
        if value < 0:
            raise ValueError(f"{info.field_name} cannot be negative.")
        return value


    @field_validator("pm25", mode="after")
    @classmethod
    def validate_pm25_range(cls, value: float | None):
        if value is None:
            return value
        if value > 1000:
            raise ValueError("pm25 out of expected range (0 to 1000).")
        return value


    @field_validator("pm10", mode="after")
    @classmethod
    def validate_pm10_range(cls, value: float | None):
        if value is None:
            return value
        if value > 1500:
            raise ValueError("pm10 out of expected range (0 to 1500).")
        return value


    @field_validator("no2", mode="after")
    @classmethod
    def validate_no2_range(cls, value: float | None):
        if value is None:
            return value
        if value > 1000:
            raise ValueError("no2 out of expected range (0 to 1000).")
        return value


    @field_validator("so2", mode="after")
    @classmethod
    def validate_so2_range(cls, value: float | None):
        if value is None:
            return value
        if value > 1500:
            raise ValueError("so2 out of expected range (0 to 1500).")
        return value


    @field_validator("co", mode="after")
    @classmethod
    def validate_co_range(cls, value: float | None):
        if value is None:
            return value
        if value > 100:
            raise ValueError("co out of expected range (0 to 100).")
        return value


    @field_validator("humidity", mode="after")
    @classmethod
    def validate_humidity_range(cls, value: float | None):
        if value is None:
            return value
        if value > 100:
            raise ValueError("humidity out of expected range (0 to 100).")
        return value


    @field_validator("temperature", mode="after")
    @classmethod
    def validate_temperature_range(cls, value: float | None):
        if value is None:
            return value
        if value < -50 or value > 60:
            raise ValueError("temperature out of expected range (-50 to 60).")
        return value


    @field_validator("wind_speed", mode="after")
    @classmethod
    def validate_wind_speed_range(cls, value: float | None):
        if value is None:
            return value
        if value > 150:
            raise ValueError("wind_speed out of expected range (0 to 150).")
        return value
