"""Finance model loader."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import structlog

from ml.finance.train_cashflow import analyze_ratios, forecast_cashflow, train

log = structlog.get_logger()
DEFAULT_PATH = Path(__file__).resolve().parents[2] / "models" / "finance" / "cashflow_v1.joblib"


@lru_cache
def load_finance_artifact(model_path: str | None = None) -> dict[str, Any]:
    path = Path(model_path) if model_path else DEFAULT_PATH
    if not path.exists():
        train(path.parent)
    artifact = joblib.load(path)
    log.info("finance_model_loaded", version=artifact.get("model_version"))
    return artifact


def run_cashflow_forecast(**kwargs) -> dict:
    return forecast_cashflow(load_finance_artifact(), **kwargs)


def run_ratio_analysis(report: dict) -> dict:
    return analyze_ratios(report)
