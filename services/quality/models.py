"""Quality anomaly model loader."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import structlog

from ml.quality.train_anomaly import extract_features, recommend_process_params, train

log = structlog.get_logger()
DEFAULT_PATH = Path(__file__).resolve().parents[2] / "models" / "quality" / "anomaly_v1.joblib"


@lru_cache
def load_anomaly_artifact(model_path: str | None = None) -> dict[str, Any]:
    path = Path(model_path) if model_path else DEFAULT_PATH
    if not path.exists():
        train(path.parent)
    artifact = joblib.load(path)
    log.info("quality_anomaly_model_loaded", version=artifact.get("model_version"))
    return artifact


def predict_anomaly(process: dict, quality: dict, model_path: str | None = None) -> dict:
    artifact = load_anomaly_artifact(model_path)
    features = extract_features(process, quality)
    model = artifact["model"]
    proba = float(model.predict_proba(features)[0][1])
    is_anomaly = bool(model.predict(features)[0] == 1 or proba >= 0.55)
    return {
        "is_anomaly": is_anomaly,
        "anomaly_score": round(proba, 4),
        "model_version": artifact["model_version"],
        "metrics": artifact.get("metrics"),
    }


def optimize_process(process: dict, grade: str) -> dict:
    return recommend_process_params(process, grade)
