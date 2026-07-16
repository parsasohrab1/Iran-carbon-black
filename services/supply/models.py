"""Supply price model loader."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import structlog

from ml.supply.train_price import forecast_price, train

log = structlog.get_logger()
DEFAULT_PATH = Path(__file__).resolve().parents[2] / "models" / "supply" / "price_v1.joblib"


@lru_cache
def load_price_artifact(model_path: str | None = None) -> dict[str, Any]:
    path = Path(model_path) if model_path else DEFAULT_PATH
    if not path.exists():
        train(path.parent)
    artifact = joblib.load(path)
    log.info("supply_price_model_loaded", version=artifact.get("model_version"))
    return artifact


def run_price_forecast(material: str, history: list[float], horizon_days: int, **kwargs) -> dict:
    return forecast_price(
        load_price_artifact(),
        material=material,
        history=history,
        horizon_days=horizon_days,
        **kwargs,
    )
