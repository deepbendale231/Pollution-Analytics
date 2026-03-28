# Pollution Analytics

An end-to-end air quality intelligence platform for Indian cities, built for practical decision-making and deployment.

- Live frontend: https://deepbendale231-pollution-analytics-frontendstreamlit-app-yx00m4.streamlit.app/
- Backend target: https://pollution-analytics.onrender.com

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-FF4B4B?logo=streamlit&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-Data-4479A1?logo=mysql&logoColor=white)
![Status](https://img.shields.io/badge/Deployment-Active-brightgreen)

## Why This Project Exists

Urban air quality data is often noisy, fragmented, and hard to operationalize. Pollution Analytics turns raw pollutant signals into clear, action-oriented outputs:

- City-level air quality KPIs
- AQI prediction with confidence bounds
- Forecasting for planning windows
- Health-risk interpretation for sensitive groups
- A deployment-ready web dashboard for real users

## Live Product

The Streamlit frontend is deployed and publicly accessible:

https://deepbendale231-pollution-analytics-frontendstreamlit-app-yx00m4.streamlit.app/

The frontend is configured to call:

https://pollution-analytics.onrender.com

## System Architecture

```text
Data Sources -> Ingestion + Normalization -> MySQL -> FastAPI -> Streamlit UI
                                      \-> ML model artifacts (prediction + forecast)
```

Core flow:

1. Data is ingested and transformed into a clean relational schema.
2. API endpoints expose analytics, prediction, forecast, and health insights.
3. Streamlit consumes the API and renders decision dashboards.
4. Model artifacts are versioned and loaded at runtime.

## Key Capabilities

- Real-time style dashboard for city-level AQI monitoring
- AQI prediction endpoint with lower and upper confidence bounds
- Forecast visualization with uncertainty support
- Health-risk cards and activity advisories
- City comparison and deep-dive workflows
- Ranking and pollutant-level analytics endpoints

## Tech Stack

- Backend: FastAPI, Uvicorn, Pydantic
- Frontend: Streamlit, Plotly, Folium
- Data: MySQL, Pandas, NumPy
- ML: scikit-learn, Prophet, SHAP, joblib
- Scheduling: APScheduler
- Testing: pytest

## Repository Layout

- backend: FastAPI app, routers, service logic
- frontend: Streamlit app, pages, api client, components
- models: trained artifacts (model, scaler, metadata)
- scheduler: ingestion and orchestration jobs
- SQL: analysis SQL scripts
- DATA: source datasets and utilities
- outputs: generated analysis artifacts
- tests: automated tests

## API Endpoints

- GET /health
- POST /predict
- GET /forecast/{city}
- GET /analytics/ranking
- GET /analytics/compare
- GET /analytics/city/{city}/stats
- GET /analytics/city/{city}/pollutants

## Local Development

### 1) Environment

```bash
git clone https://github.com/deepbendale231/Pollution-Analytics.git
cd Pollution-Analytics
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Configure environment variables

Create .env file:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=air_quality_db
API_BASE_URL=http://127.0.0.1:8000
```

### 3) Run backend

```bash
.venv/bin/python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

### 4) Run frontend

```bash
.venv/bin/python -m streamlit run frontend/streamlit_app.py --server.port 8501 --server.headless true
```

## Production Deployment

### Frontend (Streamlit Cloud)

Required secret:

```toml
API_BASE_URL = "https://pollution-analytics.onrender.com"
```

### Backend (Render)

Start command:

```bash
python -m uvicorn backend.app:app --host 0.0.0.0 --port $PORT
```

Required environment variables:

```env
DB_HOST=ber1eetclql1cagyfn8o-mysql.services.clever-cloud.com
DB_PORT=3306
DB_USER=ufyuzzgw4yq62pry
DB_PASSWORD=********
DB_NAME=ber1eetclql1cagyfn8o
```

Notes:

- Use a managed MySQL database in production.
- Keep credentials only in Render or Streamlit secret management.
- Do not hardcode secrets in source files.

## Data Restore Procedure

Database import can be done with:

```bash
mysql --host <host> --port 3306 --user <user> --password=<password> <db_name> < pollution_backup_nogtid.sql
```

Validation query:

```bash
mysql --host <host> --port 3306 --user <user> --password=<password> <db_name> -e "SELECT COUNT(*) FROM measurements;"
```

## Model Artifacts

Committed deployment artifacts:

- models/aqi_model.pkl
- models/scaler.pkl
- models/metadata.json

These are required for production prediction behavior to match local runs.

## Quality Gates

Health check:

```bash
curl -sS https://pollution-analytics.onrender.com/health
```

Representative API checks:

```bash
curl -sS "https://pollution-analytics.onrender.com/analytics/ranking" | head -c 500
curl -sS "https://pollution-analytics.onrender.com/forecast/Delhi" | head -c 500
```

Test suite:

```bash
pytest -q
```

## Troubleshooting

### Frontend shows API Offline

- Confirm API_BASE_URL secret in Streamlit points to Render backend URL.
- Confirm Render service is healthy at /health.
- Confirm CORS settings are not blocking frontend domain.

### Render deploy starts but prediction fails

- Ensure model artifacts exist in repository under models.
- Confirm backend has permission and path access to read artifact files.

### MySQL connectivity fails on Render

- Re-check DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME.
- Confirm database allows external connections from Render.

## Security Notes

- Rotate database credentials after sharing in any public context.
- Keep credentials in platform secrets only.
- Use least-privilege database users.

## Roadmap

- Add CI checks for deployment smoke tests
- Add artifact version pinning and model registry
- Add alerting for API downtime and forecast drift
- Add role-based frontend access control

## License

MIT
