"""Phase 2 supply feedstock price forecasting."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_percentage_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

MODEL_VERSION = "supply-price-gbr-v1"

MATERIALS = ["Coal tar (furfural extract)", "Naphtha"]


def _dataset(rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    rows, targets = [], []
    for mi, _material in enumerate(MATERIALS):
        price = 36000 + mi * 15000
        for t in range(120):
            oil = 70 + 12 * np.sin(t / 8) + rng.normal(0, 1.2)
            fx = 220000 + t * 400 + rng.normal(0, 1500)
            inflation = 0.30 + 0.02 * np.sin(t / 10)
            lag1 = price
            lag2 = price * (1 + rng.normal(0, 0.01))
            lag3 = price * (1 + rng.normal(0, 0.015))
            next_price = price * (1 + 0.004 + 0.0015 * (oil - 70) / 10 + rng.normal(0, 0.008))
            rows.append([mi, t % 12, oil, fx / 1000, inflation, lag1, lag2, lag3, (lag1 - lag3) / max(lag3, 1)])
            targets.append(next_price)
            price = next_price
    return np.asarray(rows, dtype=np.float64), np.asarray(targets, dtype=np.float64)


def train(output_dir: Path | None = None) -> dict:
    output_dir = output_dir or Path(__file__).resolve().parents[2] / "models" / "supply"
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(11)
    x, y = _dataset(rng)
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)
    model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("gbr", GradientBoostingRegressor(n_estimators=180, learning_rate=0.06, max_depth=3, random_state=42)),
        ]
    )
    model.fit(x_train, y_train)
    preds = model.predict(x_test)
    mape = float(mean_absolute_percentage_error(y_test, preds))
    accuracy = float(max(0.0, 1.0 - mape))
    artifact = {
        "model": model,
        "model_version": MODEL_VERSION,
        "materials": MATERIALS,
        "metrics": {"mape": mape, "accuracy": accuracy, "r2": float(r2_score(y_test, preds))},
    }
    path = output_dir / "price_v1.joblib"
    joblib.dump(artifact, path)
    (output_dir / "price_v1_metrics.json").write_text(
        json.dumps(artifact["metrics"] | {"model_version": MODEL_VERSION}, indent=2),
        encoding="utf-8",
    )
    return {"model_path": str(path), **artifact["metrics"], "model_version": MODEL_VERSION}


def forecast_price(
    artifact: dict,
    *,
    material: str,
    history: list[float],
    horizon_days: int = 90,
    crude_oil_price_usd: float = 78.0,
    usd_irr_rate: float = 245000.0,
    inflation_rate: float = 0.35,
) -> dict:
    materials = artifact["materials"]
    if material not in materials:
        # fuzzy: use first material model index 0
        mi = 0
    else:
        mi = materials.index(material)
    hist = list(history[-3:]) if history else [40000, 41000, 42000]
    while len(hist) < 3:
        hist.insert(0, hist[0])
    lag1, lag2, lag3 = hist[-1], hist[-2], hist[-3]
    features = np.asarray(
        [
            [
                mi,
                6,
                crude_oil_price_usd,
                usd_irr_rate / 1000,
                inflation_rate,
                lag1,
                lag2,
                lag3,
                (lag1 - lag3) / max(lag3, 1),
            ]
        ],
        dtype=np.float64,
    )
    next_month = float(artifact["model"].predict(features)[0])
    # Extrapolate horizon with damped drift
    months = max(1, horizon_days // 30)
    drift = (next_month - lag1) / max(lag1, 1)
    predicted = lag1 * ((1 + drift) ** months)
    trend = "increasing" if predicted > lag1 * 1.01 else "decreasing" if predicted < lag1 * 0.99 else "stable"
    if trend == "increasing":
        recommendation = "buy_sooner"
        reason = "Model expects feedstock prices to rise; accelerate procurement."
    elif trend == "decreasing":
        recommendation = "wait"
        reason = "Model expects prices to ease; delay non-critical buys."
    else:
        recommendation = "hold"
        reason = "Stable outlook; buy to reorder point."

    return {
        "material": material,
        "horizon_days": horizon_days,
        "latest_price_irr": round(lag1, 2),
        "predicted_price_irr": round(predicted, 2),
        "trend": trend,
        "recommendation": recommendation,
        "reason": reason,
        "confidence": round(float(artifact["metrics"].get("accuracy", 0.85)), 3),
        "model_version": artifact["model_version"],
    }


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
