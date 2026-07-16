"""MLOps helpers — train domain models and publish versioned artifacts to MinIO."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from shared.config import Settings, get_settings
from shared.storage import get_minio_client, put_stream

TRAINERS: dict[str, Callable[[], dict]] = {}


def _load_trainers() -> dict[str, Callable[[], dict]]:
    if TRAINERS:
        return TRAINERS
    from ml.demand.train_forecast import train as train_demand
    from ml.energy.train_rul import train as train_energy
    from ml.finance.train_cashflow import train as train_finance
    from ml.quality.train_anomaly import train as train_quality
    from ml.sales.train_forecast import train as train_sales
    from ml.supply.train_price import train as train_supply

    TRAINERS.update(
        {
            "energy": train_energy,
            "quality": train_quality,
            "demand": train_demand,
            "supply": train_supply,
            "sales": train_sales,
            "finance": train_finance,
        }
    )
    return TRAINERS


DOMAIN_ARTIFACTS = {
    "energy": ("rul", "models/energy/rul_v1.joblib"),
    "quality": ("anomaly", "models/quality/anomaly_v1.joblib"),
    "demand": ("forecast", "models/demand/forecast_v1.joblib"),
    "supply": ("price", "models/supply/price_v1.joblib"),
    "sales": ("forecast", "models/sales/forecast_v1.joblib"),
    "finance": ("cashflow", "models/finance/cashflow_v1.joblib"),
}


def retrain_domain(domain: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    trainers = _load_trainers()
    if domain not in trainers:
        raise ValueError(f"Unsupported domain: {domain}")

    result = trainers[domain]()
    model_name, local_rel = DOMAIN_ARTIFACTS[domain]
    local_path = Path(local_rel)
    if not local_path.exists():
        # trainers write under repo models/; resolve from cwd/app
        candidates = [
            Path("/app") / local_rel,
            Path(__file__).resolve().parents[1] / local_rel,
            local_path,
        ]
        local_path = next((p for p in candidates if p.exists()), local_path)

    version = result.get("model_version") or f"{domain}-v{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
    object_name = f"{domain}/{model_name}/{version}.joblib"
    uri = None
    try:
        with local_path.open("rb") as fh:
            data = fh.read()
        from io import BytesIO

        uri = put_stream(
            settings.minio_bucket_models,
            object_name,
            BytesIO(data),
            length=len(data),
            content_type="application/octet-stream",
            settings=settings,
        )
        # also publish metrics sidecar
        metrics = {k: v for k, v in result.items() if k not in {"model_path"}}
        get_minio_client(settings).put_object(
            settings.minio_bucket_models,
            f"{domain}/{model_name}/{version}.metrics.json",
            BytesIO(json.dumps(metrics, default=str).encode()),
            length=len(json.dumps(metrics, default=str).encode()),
            content_type="application/json",
        )
    except Exception as exc:  # noqa: BLE001
        uri = f"local://{local_path}"
        result["minio_warning"] = str(exc)

    result.update(
        {
            "domain": domain,
            "model_name": model_name,
            "version": version,
            "artifact_uri": uri,
            "local_path": str(local_path),
        }
    )
    return result


def list_minio_models(settings: Settings | None = None) -> list[dict]:
    settings = settings or get_settings()
    client = get_minio_client(settings)
    items = []
    try:
        for obj in client.list_objects(settings.minio_bucket_models, recursive=True):
            items.append({"object": obj.object_name, "size": obj.size, "last_modified": str(obj.last_modified)})
    except Exception as exc:  # noqa: BLE001
        return [{"error": str(exc)}]
    return items
