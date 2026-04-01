from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from flask import Flask, jsonify, request
from tensorflow import keras

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from backend.training.train_models import train_models
from backend.utils.ml_utils import (
    AUTOENCODER_PATH,
    RF_MODEL_PATH,
    build_rf_frame,
    ensure_numeric_types,
    load_preprocessor_bundle,
    transform_for_autoencoder,
)


app = Flask(__name__)
queue: list[dict] = []
resolved_patients: list[dict] = []
random_forest = None
autoencoder = None
preprocessor_bundle = None

FIELD_LIMITS = {
    "age": (0, 120),
    "heart_rate": (30, 220),
    "systolic_blood_pressure": (70, 250),
    "oxygen_saturation": (50, 100),
    "body_temperature": (30, 45),
    "pain_level": (0, 10),
    "chronic_disease_count": (0, 10),
}


def allow_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,DELETE,OPTIONS"
    return response


app.after_request(allow_cors)


def load_models():
    global random_forest, autoencoder, preprocessor_bundle

    if random_forest is not None and autoencoder is not None and preprocessor_bundle is not None:
        return

    if not RF_MODEL_PATH.exists() or not AUTOENCODER_PATH.exists():
        train_models()

    random_forest = joblib.load(RF_MODEL_PATH)
    autoencoder = keras.models.load_model(AUTOENCODER_PATH, compile=False)
    preprocessor_bundle = load_preprocessor_bundle()


def compute_scores(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    load_models()

    ae_matrix = transform_for_autoencoder(frame, preprocessor_bundle)
    reconstructed = autoencoder.predict(ae_matrix, verbose=0)
    anomaly_scores = np.mean(np.square(ae_matrix - reconstructed), axis=1)

    rf_frame = build_rf_frame(frame, anomaly_scores, preprocessor_bundle)
    predicted_triage = random_forest.predict(rf_frame)
    priority_scores = predicted_triage + anomaly_scores

    return anomaly_scores, predicted_triage, priority_scores


def triage_to_priority_label(triage_level: int) -> str:
    priority_map = {
        3: "Critical",
        2: "High",
        1: "Medium",
        0: "Low",
    }
    return priority_map.get(int(triage_level), "Low")


def normalize_payload(payload: dict) -> dict:
    return {
        "patient_id": str(payload["patient_id"]).strip().upper(),
        "age": payload["age"],
        "heart_rate": payload["heart_rate"],
        "systolic_blood_pressure": payload["systolic_blood_pressure"],
        "oxygen_saturation": payload["oxygen_saturation"],
        "body_temperature": payload["body_temperature"],
        "pain_level": payload["pain_level"],
        "chronic_disease_count": payload["chronic_disease_count"],
        "previous_er_visits": payload.get("previous_er_visits", 0),
        "arrival_mode": str(payload.get("arrival_mode", "walk_in")).strip(),
        "status": "Waiting",
        "predicted_triage": None,
        "priority_label": None,
        "anomaly_score": None,
        "priority_score": None,
    }


def validate_payload_ranges(payload: dict) -> str | None:
    for field_name, (minimum, maximum) in FIELD_LIMITS.items():
        try:
            value = float(payload[field_name])
        except (TypeError, ValueError, KeyError):
            return f"Invalid value for {field_name}."

        if value < minimum or value > maximum:
            label = field_name.replace("_", " ")
            return f"{label} must be between {minimum} and {maximum}."

    return None


@app.route("/add_patient", methods=["POST", "OPTIONS"])
def add_patient():
    if request.method == "OPTIONS":
        return ("", 204)

    payload = request.get_json(silent=True) or {}
    required_fields = [
        "patient_id",
        "age",
        "heart_rate",
        "systolic_blood_pressure",
        "oxygen_saturation",
        "body_temperature",
        "pain_level",
        "chronic_disease_count",
    ]

    missing = [field for field in required_fields if field not in payload]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    range_error = validate_payload_ranges(payload)
    if range_error:
        return jsonify({"error": range_error}), 400

    patient = normalize_payload(payload)
    queue.append(patient)
    return jsonify({"message": "Patient added to queue.", "patient": patient}), 201


@app.route("/patients", methods=["GET"])
def get_patients():
    return jsonify({"active": queue, "resolved": resolved_patients})


@app.route("/patients/<patient_id>/resolve", methods=["POST", "OPTIONS"])
def resolve_patient(patient_id: str):
    if request.method == "OPTIONS":
        return ("", 204)

    for index, patient in enumerate(queue):
        if patient["patient_id"] == patient_id.upper():
            resolved_patient = {
                **queue.pop(index),
                "status": "Admitted",
            }
            resolved_patients.insert(0, resolved_patient)
            return jsonify({"message": "Patient marked as admitted.", "patient": resolved_patient})

    return jsonify({"error": "Patient not found in active queue."}), 404


@app.route("/patients/<patient_id>", methods=["DELETE", "OPTIONS"])
def delete_patient(patient_id: str):
    if request.method == "OPTIONS":
        return ("", 204)

    normalized_id = patient_id.upper()

    for collection in (queue, resolved_patients):
        for index, patient in enumerate(collection):
            if patient["patient_id"] == normalized_id:
                deleted_patient = collection.pop(index)
                return jsonify({"message": "Patient deleted.", "patient": deleted_patient})

    return jsonify({"error": "Patient not found."}), 404


@app.route("/optimize_queue", methods=["POST", "OPTIONS"])
def optimize_queue():
    if request.method == "OPTIONS":
        return ("", 204)

    if not queue:
        return jsonify({"error": "Queue is empty."}), 400

    frame = pd.DataFrame(queue)
    model_frame = ensure_numeric_types(
        frame[
            [
                "age",
                "heart_rate",
                "systolic_blood_pressure",
                "oxygen_saturation",
                "body_temperature",
                "pain_level",
                "chronic_disease_count",
                "previous_er_visits",
                "arrival_mode",
            ]
        ]
    )

    if model_frame.isna().any().any():
        return jsonify({"error": "Queue contains invalid numeric values."}), 400

    anomaly_scores, predicted_triage, priority_scores = compute_scores(model_frame)

    updated_queue = []
    for patient, anomaly_score, triage_level, priority_score in zip(
        queue,
        anomaly_scores,
        predicted_triage,
        priority_scores,
    ):
        updated_queue.append(
            {
                **patient,
                "predicted_triage": int(triage_level),
                "priority_label": triage_to_priority_label(int(triage_level)),
                "anomaly_score": int(round(float(anomaly_score) * 100)),
                "priority_score": int(round(float(priority_score) * 100)),
            }
        )

    updated_queue.sort(
        key=lambda patient: (patient["predicted_triage"], patient["priority_score"]),
        reverse=True,
    )

    queue.clear()
    queue.extend(updated_queue)
    return jsonify(queue)


@app.route("/train_models", methods=["POST", "OPTIONS"])
def retrain_models():
    if request.method == "OPTIONS":
        return ("", 204)

    global random_forest, autoencoder, preprocessor_bundle
    metrics = train_models()
    random_forest = None
    autoencoder = None
    preprocessor_bundle = None
    return jsonify(metrics)


if __name__ == "__main__":
    app.run(debug=True)
