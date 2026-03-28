from __future__ import annotations

import numpy as np
import pandas as pd


def _resolve_tree_model_and_features(model, X):
    tree_model = model
    X_for_tree = X

    if hasattr(model, "named_steps") and "model" in model.named_steps:
        tree_model = model.named_steps["model"]
        if len(model.steps) > 1:
            preprocessor = model[:-1]
            X_for_tree = preprocessor.transform(X)

    if not hasattr(tree_model, "estimators_"):
        raise ValueError(
            "The provided model does not expose estimators_. "
            "Use a trained RandomForest model (or a Pipeline wrapping one)."
        )

    return tree_model, X_for_tree


def predict_with_confidence(model, X):
    """Backward-compatible wrapper around predict_with_intervals."""
    return predict_with_intervals(model, X)


def predict_with_intervals(model, X):
    """Return prediction mean, interval bounds, interval width, and reliability."""
    if isinstance(X, (pd.Series, dict)):
        X = pd.DataFrame([X])

    tree_model, X_for_tree = _resolve_tree_model_and_features(model, X)

    tree_predictions = np.vstack(
        [estimator.predict(X_for_tree) for estimator in tree_model.estimators_]
    )

    mean_prediction = np.mean(tree_predictions, axis=0)
    lower_bound = np.percentile(tree_predictions, 5, axis=0)
    upper_bound = np.percentile(tree_predictions, 95, axis=0)
    confidence_width = upper_bound - lower_bound

    reliability = np.where(
        confidence_width < 30,
        "high",
        np.where(confidence_width <= 60, "medium", "low"),
    )

    return {
        "prediction": mean_prediction,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
        "confidence_width": confidence_width,
        "reliability": reliability,
    }
