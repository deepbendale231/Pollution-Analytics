# Pollution Analytics

Production-style air quality intelligence platform for Indian cities, with real-time data ingestion, AQI prediction, explainability, forecasting, and an interactive decision dashboard.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-FF4B4B?logo=streamlit&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-Data-4479A1?logo=mysql&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Executive Summary

Pollution Analytics turns heterogeneous particulate and pollutant readings into operational AQI intelligence:

- Live ingestion from external sources into a structured MySQL store.
- Standards-aware analytics and KPI computation.
- ML-backed AQI prediction with confidence intervals.
- Time-series forecasting for near-term planning.
- Health-risk interpretation for sensitive population groups.
- A modern Streamlit control plane for analysts and city-ops users.

The system is built for practical usage, not only experimentation: deterministic APIs, dashboard workflows, explainability outputs, and scheduled pipelines are all included.

## Core Capabilities

- AQI prediction endpoint with bounds and reliability metadata.
- 7-day forecast endpoint and uncertainty visualization.
- City-level analytics: trend, best/worst day, pollutant averages.
- Comparison workflow for city-vs-city intelligence.
- Interactive map and ranking for operational prioritization.
- Health-risk panel with mask guidance and safe-hours recommendations.
- Scheduled ingestion runtime with structured pipeline logging.

## Architecture

```text
                        +----------------------+
                        |  Scheduler Pipeline  |
                        |  (APScheduler)       |
                        +----------+-----------+
                                   |
                                   v
+-----------+    +----------------------+    +------------------+
|  Source   | -> | Ingestion + Transform| -> | MySQL (AQ Store) |
|  APIs     |    | + Validation          |    |                  |
+-----------+    +----------------------+    +---------+--------+
                                                         |
                                 +-----------------------+-----------------------+
                                 |                                               |
                                 v                                               v
                       +-------------------+                           +-------------------+
                       | FastAPI Service   |                           | Streamlit UI      |
                       | (analytics, ML,   |<--------------------------| (interactive ops  |
                       | forecast, health) |                           | dashboard)         |
                       +-------------------+                           +-------------------+
```

## Repository Structure

| Path | Purpose |
|---|---|
| `backend/` | FastAPI app, routers, business logic |
| `frontend/` | Streamlit app, pages, API client, components |
| `scheduler/` | Periodic ingestion orchestration |
| `ml/` | Forecasting and explainability modules |
| `DATA/` | source datasets and ingestion utilities |
| `SQL/` | SQL analysis scripts |
| `tests/` | API and integration tests |
| `models/` | serialized model artifacts |
| `outputs/` | generated reports and exported analysis |

## Technology Stack

| Layer | Technologies |
|---|---|
| Backend/API | FastAPI, Uvicorn, Pydantic |
| Data | MySQL, Pandas, NumPy |
| ML | scikit-learn, Prophet, SHAP, joblib |
| Frontend | Streamlit, Plotly, Folium |
| Orchestration | APScheduler |
| Testing | pytest, FastAPI TestClient |

## Local Setup

### 1. Prerequisites

- Python 3.11+
- MySQL 8+
- Git

### 2. Clone and Environment

```bash
git clone https://github.com/deepbendale231/Pollution-Analytics.git
cd Pollution-Analytics
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Create `.env` (or adapt `.env.example`) with database and API settings.

```bash
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=air_quality_db
API_BASE_URL=http://127.0.0.1:8000
```

### 5. Start Services

Backend:

```bash
.venv/bin/python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Frontend:

```bash
.venv/bin/python -m streamlit run frontend/streamlit_app.py --server.port 8501 --server.headless true
```

Scheduler (optional):

```bash
.venv/bin/python -m scheduler.pipeline
```

### 6. Open Dashboard

- Streamlit: http://127.0.0.1:8501
- API Health: http://127.0.0.1:8000/health
- OpenAPI Docs: http://127.0.0.1:8000/docs

## API Surface

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Service and model readiness |
| `POST` | `/predict` | AQI prediction with confidence bounds |
| `GET` | `/forecast/{city}` | 7-day AQI forecast |
| `GET` | `/analytics/city/{city}/stats` | city trend and summary KPIs |
| `GET` | `/analytics/city/{city}/pollutants` | pollutant-wise averages |
| `GET` | `/analytics/ranking` | cross-city ranking |
| `GET` | `/analytics/compare` | city-vs-city comparison |

## Example Requests

Predict AQI:

```bash
curl -X POST "http://127.0.0.1:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "city": "Delhi",
    "pm25": 82.5,
    "pm10": 145.2,
    "no2": 38.1,
    "so2": 13.4,
    "temperature": 30.0,
    "humidity": 58.0,
    "wind_speed": 7.2
  }'
```

City stats:

```bash
curl "http://127.0.0.1:8000/analytics/city/Mumbai/stats?days=30"
```

Forecast:

```bash
curl "http://127.0.0.1:8000/forecast/Delhi"
```

## Operational Validation Checklist

Run this after setup or deployment:

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS "http://127.0.0.1:8000/analytics/ranking" | head -c 400
curl -sS "http://127.0.0.1:8000/analytics/city/Delhi/stats?days=30"
curl -sS "http://127.0.0.1:8000/analytics/city/Delhi/pollutants"
curl -sS "http://127.0.0.1:8000/forecast/Delhi" | head -c 400
```

## Testing

Run test suite:

```bash
pytest -q
```

Run a single file:

```bash
pytest -q tests/test_api.py
```

## Data and Standards

- Primary source: OpenAQ (ingested and normalized).
- AQI interpretation aligned to CPCB/Indian AQI bands in analytics and UI.
- Health advisory logic is deterministic and traceable in frontend components.

## Troubleshooting

### API not reachable

- Verify backend process is listening on `:8000`.
- Check `.env` for `API_BASE_URL` mismatch.

### Dashboard shows stale data

- Hard refresh the browser.
- Restart backend and frontend processes.

### MySQL connection errors

- Confirm credentials in `.env`.
- Ensure database `air_quality_db` exists and is reachable.

### Forecast unavailable for a city

- Ensure sufficient recent city history exists in `measurements`.
- Validate city spelling/alias handling.

## Security and Production Notes

- Never commit real credentials in `.env`.
- Restrict DB user permissions for least privilege.
- Add a reverse proxy and TLS for internet-facing deployments.
- Add CI checks for tests, linting, and dependency vulnerabilities.

## License

MIT
