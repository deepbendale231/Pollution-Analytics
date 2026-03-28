import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

from components.charts import (
    create_cluster_scatter,
    create_pca_scatter,
    plot_correlation_heatmap,
)
from components.filters import get_filtered_dataframe

# ------------------------------------------------------------
# Streamlit Page Setup
# ------------------------------------------------------------
st.set_page_config(page_title="Interactive Scikit-learn Report", layout="wide")
st.title("📊 Interactive Scikit-learn Data Analysis Report")

st.sidebar.header("⚙️ Settings")

# ------------------------------------------------------------
# Dataset Upload or Load
# ------------------------------------------------------------
uploaded_file = st.sidebar.file_uploader("Upload a CSV file", type=["csv"])

CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
DEFAULT_DATASET_PATH = PROJECT_ROOT / "DATA" / "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69.csv"

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
else:
    df = pd.read_csv(DEFAULT_DATASET_PATH)
    st.sidebar.info("Using default dataset.")

df = get_filtered_dataframe(df)

if df.empty:
    st.warning("No rows match the selected filters. Adjust filters in the sidebar.")
    st.stop()

st.subheader("📁 Dataset Overview")
st.dataframe(df.head())

# ------------------------------------------------------------
# Basic Statistics
# ------------------------------------------------------------
st.subheader("📈 Summary Statistics")
st.write(df.describe())

# ------------------------------------------------------------
# Correlation Heatmap
# ------------------------------------------------------------
st.subheader("📊 Correlation Heatmap")
numeric_cols = df.select_dtypes(include=np.number).columns.tolist()

if len(numeric_cols) > 1:
    fig = plot_correlation_heatmap(df, numeric_cols, figsize=(8, 6))
    st.pyplot(fig)
else:
    st.warning("Not enough numeric columns for correlation heatmap.")

# ------------------------------------------------------------
# PCA for Dimensionality Reduction
# ------------------------------------------------------------
st.subheader("🔍 Principal Component Analysis (PCA)")
if len(numeric_cols) > 2:
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(df[numeric_cols])

    pca = PCA(n_components=2)
    pca_result = pca.fit_transform(scaled_data)
    df["PCA1"] = pca_result[:, 0]
    df["PCA2"] = pca_result[:, 1]

    fig = create_pca_scatter(df, color_col=numeric_cols[0], title="PCA Visualization")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Need at least 3 numeric columns for PCA.")

# ------------------------------------------------------------
# K-Means Clustering
# ------------------------------------------------------------
st.subheader("🧠 K-Means Clustering")

if len(numeric_cols) >= 2:
    k = st.slider("Select number of clusters (K)", 2, 10, 3)
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    scaled_data = StandardScaler().fit_transform(df[numeric_cols])
    df["Cluster"] = kmeans.fit_predict(scaled_data)

    fig = create_cluster_scatter(
        df=df,
        x_col="PCA1" if "PCA1" in df else numeric_cols[0],
        y_col="PCA2" if "PCA2" in df else numeric_cols[1],
        cluster_col="Cluster",
        title=f"K-Means Clustering (k={k})",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Not enough numeric columns for clustering.")

# ------------------------------------------------------------
# Feature Importance (Variance)
# ------------------------------------------------------------
st.subheader("📉 Feature Variance (Importance Approximation)")
variance = df[numeric_cols].var().sort_values(ascending=False)
st.bar_chart(variance)

# ------------------------------------------------------------
# Download Processed Data
# ------------------------------------------------------------
st.subheader("⬇️ Download Processed Data")
csv = df.to_csv(index=False).encode("utf-8")
st.download_button("Download CSV", csv, "processed_data.csv", "text/csv")
