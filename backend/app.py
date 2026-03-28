from __future__ import annotations

from fastapi import FastAPI
from fastapi import Query
from fastapi.middleware.cors import CORSMiddleware

from .routers.analytics import (
    CityStatsResponse,
    CompareResponse,
    RankingResponse,
    compare_cities as analytics_compare_cities,
    get_city_ranking as analytics_get_city_ranking,
    get_city_stats as analytics_get_city_stats,
    router as analytics_router,
)
from .routers.health import router as health_router
from .routers.predictions import router as predictions_router
from .services.model_service import load_model_artifacts

app = FastAPI(
    title="AQI Prediction API",
    description=(
        "REST API for AQI predictions, analytics endpoints, and health checks "
        "for Pollution Analytics."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(predictions_router)
app.include_router(analytics_router)


@app.get("/city/{city}/stats", response_model=CityStatsResponse, tags=["analytics"])
def city_stats_alias(city: str, days: int = Query(default=30, ge=1, le=365)) -> CityStatsResponse:
    return analytics_get_city_stats(city=city, days=days)


@app.get("/compare", response_model=CompareResponse, tags=["analytics"])
def compare_alias(city1: str, city2: str) -> CompareResponse:
    return analytics_compare_cities(city1=city1, city2=city2)


@app.get("/ranking", response_model=RankingResponse, tags=["analytics"])
def ranking_alias() -> RankingResponse:
    return analytics_get_city_ranking()


@app.on_event("startup")
async def startup_event() -> None:
    # Load model once when API starts and keep it in app state.
    app.state.model_bundle = load_model_artifacts()
