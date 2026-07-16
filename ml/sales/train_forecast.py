"""Phase 3 sales quantity/revenue forecasting model."""

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

MODEL_VERSION = "sales-gbr-v1"

GRADES = ["N110", "N115", "N220", "N234", "N330", "N339", "N347", "N550", "N660", "N762", "N774", "N990"]

BASE_QTY = {
    "N110": 9000,
    "N115": 8500,
    "N220": 18000,
    "N234": 12000,
    "N330": 22000,
    "N339": 14000,
    "N347": 11000,
    "N550": 16000,
    "N660": 9500,
    "N762": 7000,
    "N774": 8000,
    "N990": 4000,
}

BASE_PRICE = {
    "N110": 210000,
    "N115": 205000,
    "N220": 195000,
    "N234": 200000,
    "N330": 185000,
    "N339": 190000,
    "N347": 188000,
    "N550": 160000,
    "N660": 150000,
    "N762": 145000,
    "N774": 148000,
    "N990": 135000,
}


def _dataset(rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x, y_qty, y_rev = [], [], []
    for gi, grade in enumerate(GRADES):
        base_q = BASE_QTY[grade]
        base_p = BASE_PRICE[grade]
        for month in range(1, 37):
            seasonal = 1 + 0.05 * np.sin(2 * np.pi * month / 12)
            tire_idx = 100 + month * 0.4 + rng.normal(0, 1)
            fx = 220 + month * 0.5 + rng.normal(0, 2)
            oil = 70 + 10 * np.sin(month / 6) + rng.normal(0, 1)
            lag_q = base_q * seasonal * (1 + rng.normal(0, 0.03))
            price = base_p * (1 + 0.002 * month) * (1 + 0.01 * (fx - 220) / 20)
            qty = base_q * seasonal * (1 + 0.01 * (tire_idx - 100) / 10) * (1 + rng.normal(0, 0.04))
            # mild price elasticity
            qty *= max(0.7, 1 - 0.15 * ((price / base_p) - 1))
            x.append([gi, month % 12, tire_idx, fx, oil, lag_q, price, (lag_q + qty) / 2])
            y_qty.append(qty)
            y_rev.append(qty * price)
    return (
        np.asarray(x, dtype=np.float64),
        np.asarray(y_qty, dtype=np.float64),
        np.asarray(y_rev, dtype=np.float64),
    )


def train(output_dir: Path | None = None) -> dict:
    output_dir = output_dir or Path(__file__).resolve().parents[2] / "models" / "sales"
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(21)
    x, y_qty, y_rev = _dataset(rng)
    x_train, x_test, yq_train, yq_test, yr_train, yr_test = train_test_split(
        x, y_qty, y_rev, test_size=0.2, random_state=42
    )

    def _fit(y_train, y_test):
        model = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("gbr", GradientBoostingRegressor(n_estimators=200, learning_rate=0.06, max_depth=3, random_state=42)),
            ]
        )
        model.fit(x_train, y_train)
        preds = model.predict(x_test)
        mape = float(mean_absolute_percentage_error(y_test, preds))
        return model, {
            "mape": mape,
            "accuracy": float(max(0.0, 1.0 - mape)),
            "r2": float(r2_score(y_test, preds)),
        }

    qty_model, qty_metrics = _fit(yq_train, yq_test)
    rev_model, rev_metrics = _fit(yr_train, yr_test)
    artifact = {
        "qty_model": qty_model,
        "rev_model": rev_model,
        "model_version": MODEL_VERSION,
        "grades": GRADES,
        "base_price": BASE_PRICE,
        "metrics": {"quantity": qty_metrics, "revenue": rev_metrics},
    }
    path = output_dir / "forecast_v1.joblib"
    joblib.dump(artifact, path)
    (output_dir / "forecast_v1_metrics.json").write_text(
        json.dumps({"model_version": MODEL_VERSION, **artifact["metrics"]}, indent=2),
        encoding="utf-8",
    )
    return {"model_path": str(path), "model_version": MODEL_VERSION, **artifact["metrics"]}


def forecast_sales(
    artifact: dict,
    *,
    grade: str | None,
    months_ahead: int,
    history_qty: list[float],
    recent_price: float | None = None,
    tire_production_index: float = 112.0,
    usd_irr_rate: float = 245000.0,
    crude_oil_price_usd: float = 78.0,
) -> dict:
    grades = artifact["grades"]
    if grade and grade in grades:
        gi = grades.index(grade)
        base_price = artifact["base_price"][grade]
    else:
        gi = -1
        base_price = float(np.mean(list(artifact["base_price"].values())))
        grade = "all"

    lag_q = float(np.mean(history_qty[-3:])) if history_qty else 15000.0
    price = recent_price or base_price
    features = np.asarray(
        [[gi if gi >= 0 else 4, 7, tire_production_index, usd_irr_rate / 1000, crude_oil_price_usd, lag_q, price, lag_q]],
        dtype=np.float64,
    )
    monthly_qty = float(max(0.0, artifact["qty_model"].predict(features)[0]))
    monthly_rev = float(max(0.0, artifact["rev_model"].predict(features)[0]))
    # Pricing suggestion: nudge toward elasticity-aware optimum (~2% up if demand strong)
    demand_pressure = monthly_qty / max(lag_q, 1.0)
    if demand_pressure > 1.05:
        recommended_price = price * 1.02
        rationale = "Demand above recent run-rate; room for modest price increase."
    elif demand_pressure < 0.95:
        recommended_price = price * 0.98
        rationale = "Soft demand; slight price relief may protect volume."
    else:
        recommended_price = price
        rationale = "Balanced demand; hold current pricing."

    conf = float(artifact["metrics"]["quantity"]["accuracy"])
    return {
        "grade": grade,
        "months_ahead": months_ahead,
        "forecast_quantity_kg": round(monthly_qty * months_ahead, 2),
        "forecast_revenue_irr": round(monthly_rev * months_ahead, 2),
        "recommended_unit_price_irr": round(recommended_price, 2),
        "pricing_rationale": rationale,
        "confidence": round(conf, 3),
        "model_version": artifact["model_version"],
    }


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
