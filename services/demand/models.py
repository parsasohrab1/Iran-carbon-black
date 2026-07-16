"""Demand model loader helpers."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import structlog

from ml.demand.train_forecast import forecast_grade, recommend_grade, train

log = structlog.get_logger()
DEFAULT_PATH = Path(__file__).resolve().parents[2] / "models" / "demand" / "forecast_v1.joblib"


@lru_cache
def load_demand_artifact(model_path: str | None = None) -> dict[str, Any]:
    path = Path(model_path) if model_path else DEFAULT_PATH
    if not path.exists():
        train(path.parent)
    artifact = joblib.load(path)
    log.info("demand_model_loaded", version=artifact.get("model_version"))
    return artifact


def run_forecast(grade: str, history: list[float], period: str, **kwargs) -> dict:
    return forecast_grade(load_demand_artifact(), grade=grade, history=history, period=period, **kwargs)


def run_recommend(need: dict) -> dict:
    return recommend_grade(need, load_demand_artifact())
