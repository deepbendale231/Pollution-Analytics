from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import shap


def _as_dataframe(data: Any, columns: list[str] | None = None) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data.copy()
    if isinstance(data, pd.Series):
        return data.to_frame().T
    return pd.DataFrame(data, columns=columns)


def _unwrap_tree_model(model: Any) -> Any:
    if hasattr(model, "named_steps") and "model" in model.named_steps:
        return model.named_steps["model"]
    return model


def _build_explanation_text(items: list[dict[str, Any]]) -> str:
    if not items:
        return "No clear feature drivers were identified for this prediction."

    positive = [x for x in items if x["shap_value"] > 0]
    negative = [x for x in items if x["shap_value"] < 0]

    pos_part = ""
    neg_part = ""

    if positive:
        top_pos = positive[:2]
        pos_features = " and ".join([f"high {x['feature']}" for x in top_pos])
        pos_part = f"{pos_features} increased the predicted AQI"

    if negative:
        top_neg = negative[:2]
        neg_features = " and ".join([f"low {x['feature']}" for x in top_neg])
        neg_part = f"{neg_features} reduced the predicted AQI"

    if pos_part and neg_part:
        return f"{pos_part}, while {neg_part}."
    if pos_part:
        return f"{pos_part}."
    return f"{neg_part}."


def explain_prediction(model, X_train, single_input_df):
    """Generate SHAP explanation for a single prediction input."""
    X_train_df = _as_dataframe(X_train)
    single_df = _as_dataframe(single_input_df, columns=list(X_train_df.columns))

    tree_model = _unwrap_tree_model(model)
    explainer = shap.TreeExplainer(tree_model)

    shap_values = explainer.shap_values(single_df)
    if isinstance(shap_values, list):
        shap_values = shap_values[0]

    base_value = explainer.expected_value
    if isinstance(base_value, (list, np.ndarray)):
        base_value = float(np.asarray(base_value).flatten()[0])
    else:
        base_value = float(base_value)

    shap_row = np.asarray(shap_values)[0]
    value_row = single_df.iloc[0].to_numpy(dtype=float)
    feature_names = single_df.columns.tolist()

    explanation_items: list[dict[str, Any]] = []
    for feature, value, shap_val in zip(feature_names, value_row, shap_row):
        shap_float = float(shap_val)
        direction = "increase" if shap_float > 0 else "decrease" if shap_float < 0 else "neutral"
        explanation_items.append(
            {
                "feature": str(feature),
                "value": float(value),
                "shap_value": shap_float,
                "direction": direction,
            }
        )

    explanation_items = sorted(explanation_items, key=lambda x: abs(x["shap_value"]), reverse=True)
    top_driver = explanation_items[0]["feature"] if explanation_items else ""
    explanation_text = _build_explanation_text(explanation_items)

    return {
        "base_value": base_value,
        "shap_values": explanation_items,
        "top_driver": top_driver,
        "prediction_explanation": explanation_text,
    }
