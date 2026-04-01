from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from tensorflow import keras
from tensorflow.keras import layers

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from backend.utils.ml_utils import (
    AUTOENCODER_PATH,
    MODEL_DIR,
    RF_MODEL_PATH,
    build_rf_frame,
    fit_preprocessors,
    load_dataset,
    save_preprocessor_bundle,
    transform_for_autoencoder,
)


SEED = 42
METRICS_PATH = MODEL_DIR / "training_metrics.json"


def set_seeds() -> None:
    random.seed(SEED)
    np.random.seed(SEED)
    keras.utils.set_random_seed(SEED)


def build_autoencoder(input_dim: int) -> keras.Model:
    inputs = keras.Input(shape=(input_dim,))
    encoded = layers.Dense(24, activation="relu")(inputs)
    encoded = layers.Dense(12, activation="relu")(encoded)
    bottleneck = layers.Dense(6, activation="relu")(encoded)
    decoded = layers.Dense(12, activation="relu")(bottleneck)
    decoded = layers.Dense(24, activation="relu")(decoded)
    outputs = layers.Dense(input_dim, activation="linear")(decoded)

    model = keras.Model(inputs=inputs, outputs=outputs)
    model.compile(optimizer="adam", loss="mse")
    return model


def compute_reconstruction_error(model: keras.Model, matrix: np.ndarray) -> np.ndarray:
    reconstructed = model.predict(matrix, verbose=0)
    return np.mean(np.square(matrix - reconstructed), axis=1)


def train_models() -> dict:
    set_seeds()
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    dataset = load_dataset()
    preprocessors = fit_preprocessors(dataset)
    save_preprocessor_bundle(preprocessors)

    normal_cases = dataset[dataset["triage_level"].isin([0, 1])].copy()
    normal_matrix = transform_for_autoencoder(normal_cases, preprocessors)

    train_matrix, validation_matrix = train_test_split(
        normal_matrix,
        test_size=0.2,
        random_state=SEED,
    )

    autoencoder = build_autoencoder(train_matrix.shape[1])
    callbacks = [keras.callbacks.EarlyStopping(monitor="val_loss", patience=8, restore_best_weights=True)]

    history = autoencoder.fit(
        train_matrix,
        train_matrix,
        validation_data=(validation_matrix, validation_matrix),
        epochs=60,
        batch_size=64,
        verbose=0,
        callbacks=callbacks,
    )

    full_matrix = transform_for_autoencoder(dataset, preprocessors)
    anomaly_scores = compute_reconstruction_error(autoencoder, full_matrix)

    rf_input = build_rf_frame(dataset, anomaly_scores, preprocessors)
    x_train, x_test, y_train, y_test = train_test_split(
        rf_input,
        dataset["triage_level"],
        test_size=0.2,
        random_state=SEED,
        stratify=dataset["triage_level"],
    )

    random_forest = RandomForestClassifier(
        n_estimators=300,
        max_depth=16,
        min_samples_leaf=2,
        random_state=SEED,
        class_weight="balanced_subsample",
    )
    random_forest.fit(x_train, y_train)

    predictions = random_forest.predict(x_test)
    accuracy = accuracy_score(y_test, predictions)

    autoencoder.save(AUTOENCODER_PATH)
    joblib.dump(random_forest, RF_MODEL_PATH)

    threshold = float(np.percentile(compute_reconstruction_error(autoencoder, validation_matrix), 95))
    preprocessors["anomaly_threshold"] = threshold
    save_preprocessor_bundle(preprocessors)

    metrics = {
        "dataset_rows": int(len(dataset)),
        "normal_cases": int(len(normal_cases)),
        "autoencoder_best_val_loss": float(min(history.history["val_loss"])),
        "random_forest_accuracy": round(float(accuracy), 4),
        "anomaly_threshold": round(threshold, 6),
        "classification_report": classification_report(y_test, predictions, output_dict=True),
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


if __name__ == "__main__":
    result = train_models()
    print(json.dumps(result, indent=2))
