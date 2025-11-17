import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import plotly.express as px
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# ----------------------------------------------------------
# PAGE CONFIGURATION
# ----------------------------------------------------------
st.set_page_config(page_title="Pollution Data Report", layout="wide")
st.title("🌍 Pollution Data Interactive Report")
st.markdown("An AI-powered report built using **Scikit-learn** and **Streamlit**")

# ----------------------------------------------------------
# LOAD DATA
# ----------------------------------------------------------
file_path = r"C:\Users\deepb\Desktop\Pollution data analytics\DATA\3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69.csv"

@st.cache_data
def load_data(path):
    df = pd.read_csv(path)
    return df

df = load_data(file_path)

st.subheader("📄 Dataset Preview")
st.dataframe(df.head())

# ----------------------------------------------------------
# DATA OVERVIEW
# ----------------------------------------------------------
st.subheader("📊 Dataset Overview")
col1, col2, col3 = st.columns(3)
col1.metric("Rows", df.shape[0])
col2.metric("Columns", df.shape[1])
col3.metric("Missing Values", df.isnull().sum().sum())

st.write("### Data Types")
st.dataframe(df.dtypes)

# ----------------------------------------------------------
# DATA VISUALIZATION
# ----------------------------------------------------------
st.header("📈 Exploratory Data Analysis")

numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
selected_feature = st.selectbox("Select a feature for distribution plot", numeric_cols)

fig, ax = plt.subplots()
sns.histplot(df[selected_feature], kde=True, ax=ax)
st.pyplot(fig)

# Correlation heatmap
st.write("### 🔥 Correlation Heatmap")
corr = df[numeric_cols].corr()
fig_corr, ax_corr = plt.subplots(figsize=(10, 6))
sns.heatmap(corr, cmap="coolwarm", annot=True, fmt=".2f", ax=ax_corr)
st.pyplot(fig_corr)

# ----------------------------------------------------------
# INTERACTIVE SCATTERPLOT
# ----------------------------------------------------------
st.write("### 🌀 Interactive Scatter Plot")
x_axis = st.selectbox("X-axis", numeric_cols, index=0)
y_axis = st.selectbox("Y-axis", numeric_cols, index=1)
fig_px = px.scatter(df, x=x_axis, y=y_axis, color=df.columns[0], title=f"{y_axis} vs {x_axis}")
st.plotly_chart(fig_px, use_container_width=True)

# ----------------------------------------------------------
# SIMPLE REGRESSION MODEL
# ----------------------------------------------------------
st.header("🤖 Predictive Model (Linear Regression)")

target = st.selectbox("Select Target Variable", numeric_cols)
features = [col for col in numeric_cols if col != target]

X = df[features].fillna(df.mean())
y = df[target].fillna(df[target].mean())

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

model = LinearRegression()
model.fit(X_train_scaled, y_train)

y_pred = model.predict(X_test_scaled)

# Model metrics
mae = mean_absolute_error(y_test, y_pred)
mse = mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

col1, col2, col3 = st.columns(3)
col1.metric("MAE", round(mae, 3))
col2.metric("MSE", round(mse, 3))
col3.metric("R² Score", round(r2, 3))

# Feature importance (coefficients)
st.write("### 🔍 Feature Importance")
importance_df = pd.DataFrame({
    "Feature": features,
    "Coefficient": model.coef_
}).sort_values(by="Coefficient", ascending=False)

st.dataframe(importance_df)

fig_imp = px.bar(importance_df, x="Feature", y="Coefficient", title="Feature Importance (Linear Regression)")
st.plotly_chart(fig_imp, use_container_width=True)

# ----------------------------------------------------------
# DOWNLOAD SECTION
# ----------------------------------------------------------
st.write("### 📥 Download Processed Data")
csv_data = df.to_csv(index=False).encode("utf-8")
st.download_button("Download Cleaned Data", csv_data, "cleaned_pollution_data.csv", "text/csv")

st.success("✅ Report generated successfully! Use the sidebar and dropdowns to explore your data interactively.")
