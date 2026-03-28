from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json

import joblib
import pandas as pd
import streamlit as st
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
DEFAULT_DATA_PATH = PROJECT_ROOT / "DATA" / "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69.csv"
MODELS_DIR = PROJECT_ROOT / "models"
MODEL_PATH = MODELS_DIR / "aqi_model.pkl"
SCALER_PATH = MODELS_DIR / "scaler.pkl"
METADATA_PATH = MODELS_DIR / "metadata.json"


def _prepare_training_frame(data_path: Path, target_col: str) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    if not data_path.exists():
        raise FileNotFoundError(f"Training data not found: {data_path}")

    df = pd.read_csv(data_path)
    if target_col not in df.columns:
        raise ValueError(
            f"Target column '{target_col}' not found in dataset. "
            f"Available columns: {list(df.columns)}"
        )

    feature_df = df.drop(columns=[target_col])

    # Keep only numeric features for scaler + RandomForest training.
    numeric_feature_df = feature_df.select_dtypes(include=["number"]).copy()
    if numeric_feature_df.empty:
        raise ValueError("No numeric feature columns available for training.")

    cleaned = numeric_feature_df.assign(**{target_col: df[target_col]}).dropna()
    if cleaned.empty:
        raise ValueError("No training rows remain after dropping rows with missing values.")

    X = cleaned.drop(columns=[target_col])
    y = cleaned[target_col]
    return X, y, X.columns.tolist()


def train_and_save(
    data_path: Path | str = DEFAULT_DATA_PATH,
    target_col: str = "pollutant_avg",
    test_size: float = 0.2,
    random_state: int = 42,
) -> dict[str, Any]:
    """Train a RandomForestRegressor and persist model, scaler, and metadata."""
    data_path = Path(data_path)
    X, y, feature_names = _prepare_training_frame(data_path, target_col)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = RandomForestRegressor(n_estimators=300, random_state=random_state)
    model.fit(X_train_scaled, y_train)

    predictions = model.predict(X_test_scaled)
    r2 = r2_score(y_test, predictions)
    mae = mean_absolute_error(y_test, predictions)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)

    metadata = {
        "r2_score": float(r2),
        "mae": float(mae),
        "feature_names": feature_names,
        "training_date": datetime.now(timezone.utc).isoformat(),
        "num_samples": int(len(X)),
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return metadata


@st.cache_resource
def load_model() -> tuple[Any, Any]:
    """Load and return the persisted model and scaler."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model file not found: {MODEL_PATH}. Run train_and_save() first."
        )
    if not SCALER_PATH.exists():
        raise FileNotFoundError(
            f"Scaler file not found: {SCALER_PATH}. Run train_and_save() first."
        )

    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    return model, scaler
