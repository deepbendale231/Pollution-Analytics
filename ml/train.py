from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error, r2_score
from sklearn.model_selection import RandomizedSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
DEFAULT_DATA_PATH = PROJECT_ROOT / "DATA" / "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69.csv"
MODELS_DIR = PROJECT_ROOT / "models"
MODEL_PATH = MODELS_DIR / "aqi_model.pkl"
METADATA_PATH = MODELS_DIR / "metadata.json"


def _prepare_dataset(data_path: Path, target_col: str) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    if not data_path.exists():
        raise FileNotFoundError(f"Training data not found: {data_path}")

    df = pd.read_csv(data_path)
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in data.")

    X = df.drop(columns=[target_col]).select_dtypes(include=["number"]).copy()
    y = pd.to_numeric(df[target_col], errors="coerce")

    merged = X.assign(__target=y).dropna()
    if merged.empty:
        raise ValueError("No valid rows available for training after dropping missing values.")

    X_clean = merged.drop(columns=["__target"])
    y_clean = merged["__target"]

    if X_clean.empty:
        raise ValueError("No numeric feature columns found for training.")

    return X_clean, y_clean, X_clean.columns.tolist()


def train_and_save(
    data_path: Path | str = DEFAULT_DATA_PATH,
    target_col: str = "pollutant_avg",
) -> dict:
    data_path = Path(data_path)

    X, y, feature_names = _prepare_dataset(data_path, target_col)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
    )

    pipeline = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("model", RandomForestRegressor(n_estimators=200, random_state=42)),
        ]
    )

    param_distributions = {
        "model__n_estimators": [100, 200, 300],
        "model__max_depth": [None, 10, 20, 30],
        "model__min_samples_split": [2, 5, 10],
        "model__max_features": ["sqrt", "log2"],
    }

    search = RandomizedSearchCV(
        estimator=pipeline,
        param_distributions=param_distributions,
        n_iter=20,
        cv=5,
        scoring="r2",
        random_state=42,
        n_jobs=-1,
    )
    search.fit(X_train, y_train)

    best_model = search.best_estimator_
    y_pred = best_model.predict(X_test)

    r2 = float(r2_score(y_test, y_pred))
    mae = float(mean_absolute_error(y_test, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    mape = float(mean_absolute_percentage_error(y_test, y_pred))

    print("Model Performance")
    print(f"R2:   {r2:.4f}")
    print(f"MAE:  {mae:.4f}")
    print(f"RMSE: {rmse:.4f}")
    print(f"MAPE: {mape:.4f}")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model, MODEL_PATH)

    metadata = {
        "model_type": "RandomForestRegressor",
        "r2": r2,
        "mae": mae,
        "rmse": rmse,
        "feature_names": feature_names,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_samples": int(len(X)),
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return metadata


if __name__ == "__main__":
    result = train_and_save()
    print("Saved model to:", MODEL_PATH)
    print("Saved metadata to:", METADATA_PATH)
    print(json.dumps(result, indent=2))
