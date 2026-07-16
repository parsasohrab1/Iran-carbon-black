"""Sales model loader."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import structlog

from ml.sales.train_forecast import forecast_sales, train

log = structlog.get_logger()
DEFAULT_PATH = Path(__file__).resolve().parents[2] / "models" / "sales" / "forecast_v1.joblib"


@lru_cache
def load_sales_artifact(model_path: str | None = None) -> dict[str, Any]:
    path = Path(model_path) if model_path else DEFAULT_PATH
    if not path.exists():
        train(path.parent)
    artifact = joblib.load(path)
    log.info("sales_model_loaded", version=artifact.get("model_version"))
    return artifact


def run_sales_forecast(**kwargs) -> dict:
    return forecast_sales(load_sales_artifact(), **kwargs)
