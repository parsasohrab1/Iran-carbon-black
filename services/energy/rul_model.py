"""RUL model loader / predictor for energy service."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import structlog

from ml.energy.train_rul import (
    ALERT_RUL_DAYS,
    MODEL_VERSION,
    extract_features,
    failure_probability_from_rul,
    train,
)

log = structlog.get_logger()

DEFAULT_MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "energy" / "rul_v1.joblib"


@lru_cache
def load_rul_artifact(model_path: str | None = None) -> dict[str, Any]:
    path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
    if not path.exists():
        log.warning("rul_model_missing_training", path=str(path))
        train(path.parent)
    artifact = joblib.load(path)
    log.info("rul_model_loaded", version=artifact.get("model_version"), path=str(path))
    return artifact


def predict_rul_from_sensors(sensors: dict[str, float], model_path: str | None = None) -> dict[str, Any]:
    artifact = load_rul_artifact(model_path)
    model = artifact["model"]
    features = extract_features(sensors)
    rul_days = float(max(0.1, model.predict(features)[0]))
    failure_probability = failure_probability_from_rul(rul_days)
    alert_threshold = float(artifact.get("alert_rul_days", ALERT_RUL_DAYS))
    return {
        "remaining_useful_life_days": round(rul_days, 2),
        "failure_probability": round(failure_probability, 4),
        "alert": rul_days <= alert_threshold,
        "alert_threshold_days": alert_threshold,
        "model_version": artifact.get("model_version", MODEL_VERSION),
    }
