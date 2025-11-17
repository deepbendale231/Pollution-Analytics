🌍 Pollution Data Analytics
End-to-end SQL + Python + Machine Learning analysis of Indian air quality data.

📌 Overview

This project analyzes air pollution across Indian cities using:
SQL → Core KPIs, trends, exceedance analysis
Python (Pandas, Seaborn, Plotly) → EDA, visualization
Machine Learning (Scikit-learn) → Pollution prediction
Streamlit → Interactive dashboards
PDF report → Full written analysis
Dataset contains 3,425+ pollution records from 50+ Indian cities (data.gov.in).

🧪 What This Project Does
✔ 1. SQL Analysis
Includes scripts for:
Total cities, stations
Avg pollution by pollutant
Most polluted stations
Daily & monthly trends
Threshold exceedance (>WHO limits)
Correlation & volatility metrics

✔ 2. Python EDA (Notebooks)
air_quality_analysis.ipynb:
Missing value checks
Pollution distribution
City-wise pollution ranking
Heatmaps, trendlines
Feature correlation
clustering_cities.ipynb:
K-Means clustering of Indian cities
Visualization of cluster groups
PCA analysis

✔ 3. ML Model (Prediction)
Final ML workflow inside:
pollution_ml_report.py
Comprehensive Air Pollution Analysis and Prediction Across Indian Cities.pdf
Key points:
Algorithm: Random Forest Regressor
R² score: 0.91
Predicts PM2.5 pollution per city
Features: Lag values, rolling mean, seasonal indicators

▶ pollution_report.py
PCA
Clustering
Variance importance
CSV upload

▶ pollution_ml_report.py
Full ML workflow (EDA → Train → Metrics → Feature importance)

📊 Highlights & Insights
From your PDF + CSV outputs:
PM2.5 & PM10 exceed WHO limits by 300–400%
NCR & Gujarat industrial zones are the most polluted
70% of monitored days are unsafe
High correlation (~0.89) between PM2.5 & PM10
Winter months show the highest spikes
ML model predicts pollution with 91% accuracy

🧰 Tech Stack
Python (Pandas, NumPy, Matplotlib, Seaborn, Plotly)
SQL (MySQL)
Scikit-learn (PCA, KMeans, Regression)
Streamlit (for dashboards)
Jupyter Notebook

PDF reporting 
