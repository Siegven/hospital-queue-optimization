from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT_DIR = Path(__file__).resolve().parents[2]
DATASET_PATH = ROOT_DIR / "Dataset" / "synthetic_medical_triage.csv"
MODEL_DIR = ROOT_DIR / "models"
RF_MODEL_PATH = MODEL_DIR / "random_forest_model.pkl"
AUTOENCODER_PATH = MODEL_DIR / "autoencoder_model.h5"
SCALER_PATH = MODEL_DIR / "scaler.pkl"

NUMERIC_FEATURES = [
    "age",
    "heart_rate",
    "systolic_blood_pressure",
    "oxygen_saturation",
    "body_temperature",
    "pain_level",
    "chronic_disease_count",
    "previous_er_visits",
]

CATEGORICAL_FEATURES = ["arrival_mode"]

RF_FEATURES = [
    "age",
    "heart_rate",
    "systolic_blood_pressure",
    "oxygen_saturation",
    "body_temperature",
    "pain_level",
    "chronic_disease_count",
    "previous_er_visits",
    "arrival_mode",
    "anomaly_score",
]


def load_dataset() -> pd.DataFrame:
    dataset = pd.read_csv(DATASET_PATH)
    dataset.columns = [column.strip() for column in dataset.columns]
    return dataset


def fit_preprocessors(dataset: pd.DataFrame) -> dict:
    encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    encoded_modes = encoder.fit_transform(dataset[CATEGORICAL_FEATURES])

    base_matrix = np.hstack([dataset[NUMERIC_FEATURES].to_numpy(dtype=float), encoded_modes])

    scaler = StandardScaler()
    scaled_matrix = scaler.fit_transform(base_matrix)

    return {
        "encoder": encoder,
        "scaler": scaler,
        "encoded_feature_names": encoder.get_feature_names_out(CATEGORICAL_FEATURES).tolist(),
        "autoencoder_features": NUMERIC_FEATURES + encoder.get_feature_names_out(CATEGORICAL_FEATURES).tolist(),
    }


def transform_for_autoencoder(frame: pd.DataFrame, bundle: dict) -> np.ndarray:
    encoded_modes = bundle["encoder"].transform(frame[CATEGORICAL_FEATURES])
    base_matrix = np.hstack([frame[NUMERIC_FEATURES].to_numpy(dtype=float), encoded_modes])
    return bundle["scaler"].transform(base_matrix)


def build_rf_frame(frame: pd.DataFrame, anomaly_scores: np.ndarray, bundle: dict) -> pd.DataFrame:
    encoded_modes = bundle["encoder"].transform(frame[CATEGORICAL_FEATURES])
    encoded_columns = bundle["encoded_feature_names"]

    rf_frame = pd.concat(
        [
            frame[NUMERIC_FEATURES].reset_index(drop=True),
            pd.DataFrame(encoded_modes, columns=encoded_columns),
            pd.DataFrame({"anomaly_score": anomaly_scores}),
        ],
        axis=1,
    )
    return rf_frame


def ensure_numeric_types(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    for column in NUMERIC_FEATURES:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
    return normalized


def save_preprocessor_bundle(bundle: dict) -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, SCALER_PATH)


def load_preprocessor_bundle() -> dict:
    return joblib.load(SCALER_PATH)
