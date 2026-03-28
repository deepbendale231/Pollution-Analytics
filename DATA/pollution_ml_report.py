import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import RandomizedSearchCV, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    r2_score,
)

from components.charts import (
    create_feature_importance_bar,
    create_scatter_plot,
    explain_prediction,
    plot_correlation_heatmap,
    plot_distribution,
)
from components.filters import get_filtered_dataframe

# ----------------------------------------------------------
# PAGE CONFIGURATION
# ----------------------------------------------------------
st.set_page_config(page_title="Pollution Data Report", layout="wide")
st.title("🌍 Pollution Data Interactive Report")
st.markdown("An AI-powered report built using **Scikit-learn** and **Streamlit**")

# ----------------------------------------------------------
# LOAD DATA
# ----------------------------------------------------------
CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
FILE_PATH = PROJECT_ROOT / "DATA" / "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69.csv"

@st.cache_data
def load_data(path):
    df = pd.read_csv(path)
    return df

df = load_data(FILE_PATH)
df = get_filtered_dataframe(df)

if df.empty:
    st.warning("No rows match the selected filters. Adjust filters in the sidebar.")
    st.stop()

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
if not numeric_cols:
    st.warning("No numeric columns available after filters.")
    st.stop()

selected_feature = st.selectbox("Select a feature for distribution plot", numeric_cols)

fig = plot_distribution(df, selected_feature)
st.pyplot(fig)

# Correlation heatmap
st.write("### 🔥 Correlation Heatmap")
fig_corr = plot_correlation_heatmap(df, numeric_cols, figsize=(10, 6))
st.pyplot(fig_corr)

# ----------------------------------------------------------
# INTERACTIVE SCATTERPLOT
# ----------------------------------------------------------
st.write("### 🌀 Interactive Scatter Plot")
x_axis = st.selectbox("X-axis", numeric_cols, index=0)
y_axis = st.selectbox("Y-axis", numeric_cols, index=1)
fig_px = create_scatter_plot(
    df,
    x_axis=x_axis,
    y_axis=y_axis,
    color_col=df.columns[0],
    title=f"{y_axis} vs {x_axis}",
)
st.plotly_chart(fig_px, use_container_width=True)

# ----------------------------------------------------------
# RANDOM FOREST PIPELINE MODEL
# ----------------------------------------------------------
st.header("🤖 Predictive Model (Random Forest Pipeline)")

target = st.selectbox("Select Target Variable", numeric_cols)
features = [col for col in numeric_cols if col != target]

if not features:
    st.warning("At least one numeric feature is required to train the model.")
    st.stop()

X = df[features].fillna(df[features].mean())
y = df[target].fillna(df[target].mean())

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

pipeline = Pipeline(
    steps=[
        ("scaler", StandardScaler()),
        ("model", RandomForestRegressor(random_state=42)),
    ]
)

scoring = {
    "r2": "r2",
    "mae": "neg_mean_absolute_error",
    "rmse": "neg_root_mean_squared_error",
    "mape": "neg_mean_absolute_percentage_error",
}

cv_results = cross_validate(
    pipeline,
    X_train,
    y_train,
    cv=5,
    scoring=scoring,
    n_jobs=-1,
)

param_distributions = {
    "model__n_estimators": [100, 200, 300, 500, 800],
    "model__max_depth": [None, 10, 20, 30, 50],
    "model__min_samples_split": [2, 5, 10],
    "model__min_samples_leaf": [1, 2, 4],
    "model__max_features": ["sqrt", "log2", None],
}

random_search = RandomizedSearchCV(
    estimator=pipeline,
    param_distributions=param_distributions,
    n_iter=20,
    cv=5,
    scoring="r2",
    random_state=42,
    n_jobs=-1,
)
random_search.fit(X_train, y_train)

best_pipeline = random_search.best_estimator_
y_pred = best_pipeline.predict(X_test)

test_r2 = r2_score(y_test, y_pred)
test_mae = mean_absolute_error(y_test, y_pred)
test_rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
test_mape = mean_absolute_percentage_error(y_test, y_pred)

summary_df = pd.DataFrame(
    {
        "Metric": [
            "CV R2 (mean)",
            "CV MAE (mean)",
            "CV RMSE (mean)",
            "CV MAPE (mean)",
            "Test R2",
            "Test MAE",
            "Test RMSE",
            "Test MAPE",
        ],
        "Value": [
            float(np.mean(cv_results["test_r2"])),
            float(-np.mean(cv_results["test_mae"])),
            float(-np.mean(cv_results["test_rmse"])),
            float(-np.mean(cv_results["test_mape"])),
            float(test_r2),
            float(test_mae),
            float(test_rmse),
            float(test_mape),
        ],
    }
)

st.write("### 📋 Model Performance Summary")
st.table(summary_df.style.format({"Value": "{:.4f}"}))

print("Random Forest Pipeline - Metrics Summary")
print(summary_df.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

st.write("### 🧪 Best Hyperparameters")
st.json(random_search.best_params_)

col1, col2, col3, col4 = st.columns(4)
col1.metric("R²", round(test_r2, 3))
col2.metric("MAE", round(test_mae, 3))
col3.metric("RMSE", round(test_rmse, 3))
col4.metric("MAPE", round(test_mape, 3))

st.write("### 🔍 Feature Importance")
rf_model = best_pipeline.named_steps["model"]
importance_df = pd.DataFrame(
    {
        "Feature": features,
        "Coefficient": rf_model.feature_importances_,
    }
).sort_values(by="Coefficient", ascending=False)

st.dataframe(importance_df)

fig_imp = create_feature_importance_bar(
    importance_df,
    x_col="Feature",
    y_col="Coefficient",
    title="Feature Importance (Random Forest)",
)
st.plotly_chart(fig_imp, use_container_width=True)

st.write("### 🧠 SHAP Explainability")
sample_idx = st.number_input(
    "Select test sample index",
    min_value=0,
    max_value=max(len(X_test) - 1, 0),
    value=0,
    step=1,
)

if len(X_test) > 0:
    single_sample = X_test.iloc[[int(sample_idx)]]
    shap_waterfall_fig, shap_summary_fig = explain_prediction(best_pipeline, X_train, single_sample)

    st.write("#### Waterfall Plot (Single Prediction)")
    st.pyplot(shap_waterfall_fig, clear_figure=True)

    st.write("#### Summary Plot (Training Data)")
    st.pyplot(shap_summary_fig, clear_figure=True)

# ----------------------------------------------------------
# DOWNLOAD SECTION
# ----------------------------------------------------------
st.write("### 📥 Download Processed Data")
csv_data = df.to_csv(index=False).encode("utf-8")
st.download_button("Download Cleaned Data", csv_data, "cleaned_pollution_data.csv", "text/csv")

st.success("✅ Report generated successfully! Use the sidebar and dropdowns to explore your data interactively.")
