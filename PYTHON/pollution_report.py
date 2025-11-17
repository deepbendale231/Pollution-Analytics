import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

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

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
else:
    default_path = r"C:\Users\deepb\Desktop\Pollution data analytics\DATA\3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69.csv"
    df = pd.read_csv(default_path)
    st.sidebar.info("Using default dataset.")

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
    corr = df[numeric_cols].corr()
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f", ax=ax)
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

    fig = px.scatter(df, x="PCA1", y="PCA2", title="PCA Visualization", color=df[numeric_cols[0]])
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

    fig = px.scatter(
        df,
        x="PCA1" if "PCA1" in df else numeric_cols[0],
        y="PCA2" if "PCA2" in df else numeric_cols[1],
        color=df["Cluster"].astype(str),
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
