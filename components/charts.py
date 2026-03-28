from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns


def plot_distribution(df: pd.DataFrame, feature: str):
    fig, ax = plt.subplots()
    sns.histplot(df[feature], kde=True, ax=ax)
    return fig


def plot_correlation_heatmap(
    df: pd.DataFrame,
    numeric_cols: list[str],
    figsize: tuple[int, int] = (10, 6),
    cmap: str = "coolwarm",
):
    corr = df[numeric_cols].corr()
    fig, ax = plt.subplots(figsize=figsize)
    sns.heatmap(corr, cmap=cmap, annot=True, fmt=".2f", ax=ax)
    return fig


def create_scatter_plot(
    df: pd.DataFrame,
    x_axis: str,
    y_axis: str,
    color_col: str | None = None,
    title: str | None = None,
):
    return px.scatter(df, x=x_axis, y=y_axis, color=color_col, title=title)


def create_pca_scatter(
    df: pd.DataFrame,
    color_col: str,
    title: str = "PCA Visualization",
):
    return px.scatter(df, x="PCA1", y="PCA2", color=color_col, title=title)


def create_cluster_scatter(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    cluster_col: str = "Cluster",
    title: str = "K-Means Clustering",
):
    color_series = df[cluster_col].astype(str)
    return px.scatter(df, x=x_col, y=y_col, color=color_series, title=title)


def create_feature_importance_bar(
    importance_df: pd.DataFrame,
    x_col: str = "Feature",
    y_col: str = "Coefficient",
    title: str = "Feature Importance",
):
    return px.bar(importance_df, x=x_col, y=y_col, title=title)


def visualize_feature_importance(model, feature_names: list[str]):
    if not hasattr(model, "feature_importances_"):
        raise ValueError(
            "The provided model does not expose feature_importances_. "
            "Use a trained RandomForest or XGBoost model."
        )

    importances = list(model.feature_importances_)
    if len(importances) != len(feature_names):
        raise ValueError(
            "feature_names length must match model.feature_importances_ length."
        )

    importance_df = pd.DataFrame(
        {
            "feature": feature_names,
            "importance": importances,
        }
    ).sort_values("importance", ascending=False)

    top_df = importance_df.head(15).copy()
    total_importance = top_df["importance"].sum()
    if total_importance > 0:
        top_df["importance_pct"] = (top_df["importance"] / total_importance) * 100
    else:
        top_df["importance_pct"] = 0.0

    # Reverse so the highest-ranked feature appears at the top of the horizontal bar chart.
    top_df = top_df.sort_values("importance", ascending=True)
    top_df["label"] = top_df["importance_pct"].map(lambda v: f"{v:.2f}%")

    fig = px.bar(
        top_df,
        x="importance",
        y="feature",
        orientation="h",
        color="importance",
        color_continuous_scale=[(0.0, "#add8e6"), (1.0, "#8b0000")],
        text="label",
        title="Top 15 Feature Importances",
    )

    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        xaxis_title="Importance",
        yaxis_title="Feature",
        coloraxis_colorbar_title="Importance",
    )

    return fig


def explain_prediction(model, X_train, single_sample):
    import shap

    if isinstance(X_train, pd.DataFrame):
        X_train_df = X_train.copy()
        feature_names = X_train_df.columns.tolist()
    else:
        X_train_df = pd.DataFrame(X_train)
        feature_names = [f"feature_{i}" for i in range(X_train_df.shape[1])]
        X_train_df.columns = feature_names

    if isinstance(single_sample, pd.Series):
        single_sample_df = single_sample.to_frame().T
    elif isinstance(single_sample, pd.DataFrame):
        single_sample_df = single_sample.iloc[[0]].copy()
    else:
        single_sample_df = pd.DataFrame([single_sample], columns=feature_names)

    single_sample_df = single_sample_df.reindex(columns=feature_names)

    tree_model = model
    preprocessor = None
    if hasattr(model, "named_steps") and "model" in model.named_steps:
        tree_model = model.named_steps["model"]
        if len(model.steps) > 1:
            preprocessor = model[:-1]

    X_train_for_shap = X_train_df
    single_for_shap = single_sample_df
    if preprocessor is not None:
        X_train_for_shap = preprocessor.transform(X_train_df)
        single_for_shap = preprocessor.transform(single_sample_df)

    explainer = shap.TreeExplainer(tree_model)
    shap_values_single = explainer.shap_values(single_for_shap)
    shap_values_full = explainer.shap_values(X_train_for_shap)

    if isinstance(shap_values_single, list):
        shap_values_single = shap_values_single[0]
    if isinstance(shap_values_full, list):
        shap_values_full = shap_values_full[0]

    base_value = explainer.expected_value
    if isinstance(base_value, (list, np.ndarray)):
        base_value = np.asarray(base_value).flatten()[0]

    single_values = np.asarray(shap_values_single)[0]
    single_data = np.asarray(single_for_shap)[0]

    explanation = shap.Explanation(
        values=single_values,
        base_values=base_value,
        data=single_data,
        feature_names=feature_names,
    )

    fig_waterfall = plt.figure(figsize=(10, 6))
    shap.plots.waterfall(explanation, show=False)
    plt.tight_layout()

    fig_summary = plt.figure(figsize=(10, 6))
    shap.summary_plot(
        shap_values_full,
        np.asarray(X_train_for_shap),
        feature_names=feature_names,
        show=False,
    )
    plt.tight_layout()

    return fig_waterfall, fig_summary


def plot_prediction_confidence_ribbon(
    time_values,
    prediction_result: dict,
    title: str = "AQI Prediction with 90% Confidence Interval",
):
    prediction = np.asarray(prediction_result["prediction"])
    lower_bound = np.asarray(prediction_result["lower_bound"])
    upper_bound = np.asarray(prediction_result["upper_bound"])

    if len(time_values) != len(prediction):
        raise ValueError("time_values length must match prediction length.")

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=time_values,
            y=lower_bound,
            mode="lines",
            line=dict(width=0),
            hoverinfo="skip",
            showlegend=False,
            name="Lower Bound (5th)",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=time_values,
            y=upper_bound,
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(135, 206, 250, 0.35)",
            name="90% Confidence Interval",
            hovertemplate="Upper: %{y:.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=time_values,
            y=prediction,
            mode="lines+markers",
            line=dict(color="#8b0000", width=2.5),
            marker=dict(size=5),
            name="Mean Prediction",
            hovertemplate="Prediction: %{y:.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title="Predicted AQI",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )

    return fig
