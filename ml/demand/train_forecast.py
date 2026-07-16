"""Phase 2 demand forecasting for 12 carbon black grades."""

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

MODEL_VERSION = "demand-gbr-v1"

GRADES = [
    "N110",
    "N115",
    "N220",
    "N234",
    "N330",
    "N339",
    "N347",
    "N550",
    "N660",
    "N762",
    "N774",
    "N990",
]

GRADE_BASE = {
    "N110": 95000,
    "N115": 88000,
    "N220": 170000,
    "N234": 125000,
    "N330": 215000,
    "N339": 140000,
    "N347": 110000,
    "N550": 160000,
    "N660": 98000,
    "N762": 72000,
    "N774": 85000,
    "N990": 45000,
}

GRADE_PROPERTIES = {
    "N110": {"conductivity": "very_high", "dispersion": "low", "tint_strength": "very_high", "margin": 0.12},
    "N115": {"conductivity": "high", "dispersion": "low", "tint_strength": "high", "margin": 0.11},
    "N220": {"conductivity": "high", "dispersion": "medium", "tint_strength": "high", "margin": 0.10},
    "N234": {"conductivity": "high", "dispersion": "medium", "tint_strength": "high", "margin": 0.105},
    "N330": {"conductivity": "medium", "dispersion": "high", "tint_strength": "medium", "margin": 0.09},
    "N339": {"conductivity": "medium", "dispersion": "high", "tint_strength": "medium", "margin": 0.095},
    "N347": {"conductivity": "medium", "dispersion": "high", "tint_strength": "medium", "margin": 0.092},
    "N550": {"conductivity": "low", "dispersion": "high", "tint_strength": "low", "margin": 0.08},
    "N660": {"conductivity": "low", "dispersion": "very_high", "tint_strength": "low", "margin": 0.075},
    "N762": {"conductivity": "low", "dispersion": "very_high", "tint_strength": "low", "margin": 0.07},
    "N774": {"conductivity": "low", "dispersion": "very_high", "tint_strength": "low", "margin": 0.072},
    "N990": {"conductivity": "very_low", "dispersion": "very_high", "tint_strength": "very_low", "margin": 0.06},
}

PERIOD_MONTHS = {"1_month": 1, "3_months": 3, "6_months": 6}


def _build_dataset(rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    rows, targets = [], []
    for gi, grade in enumerate(GRADES):
        base = GRADE_BASE[grade]
        for month in range(1, 37):
            seasonal = 1 + 0.04 * np.sin(2 * np.pi * month / 12)
            tire_growth = 0.02 + 0.03 * (month / 36)
            fx_vol = rng.uniform(0.05, 0.18)
            oil = 70 + 15 * np.sin(month / 5) + rng.normal(0, 1)
            lag1 = base * seasonal * (1 + tire_growth) * (1 + rng.normal(0, 0.02))
            lag2 = lag1 * (1 + rng.normal(0, 0.02))
            lag3 = lag2 * (1 + rng.normal(0, 0.02))
            # Next-month demand
            y = base * seasonal * (1 + tire_growth) * (1 + 0.02 * (oil - 70) / 70) * (1 + rng.normal(0, 0.025))
            rows.append([gi, month % 12, tire_growth, fx_vol, oil, lag1, lag2, lag3, (lag1 + lag2 + lag3) / 3])
            targets.append(y)
    return np.asarray(rows, dtype=np.float64), np.asarray(targets, dtype=np.float64)


def train(output_dir: Path | None = None) -> dict:
    output_dir = output_dir or Path(__file__).resolve().parents[2] / "models" / "demand"
    output_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(7)
    x, y = _build_dataset(rng)
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)

    model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "gbr",
                GradientBoostingRegressor(
                    n_estimators=220,
                    learning_rate=0.06,
                    max_depth=3,
                    random_state=42,
                ),
            ),
        ]
    )
    model.fit(x_train, y_train)
    preds = model.predict(x_test)
    mape = float(mean_absolute_percentage_error(y_test, preds))
    accuracy = float(max(0.0, 1.0 - mape))
    r2 = float(r2_score(y_test, preds))

    artifact = {
        "model": model,
        "model_version": MODEL_VERSION,
        "grades": GRADES,
        "grade_base": GRADE_BASE,
        "grade_properties": GRADE_PROPERTIES,
        "metrics": {"mape": mape, "accuracy": accuracy, "r2": r2},
    }
    path = output_dir / "forecast_v1.joblib"
    joblib.dump(artifact, path)
    (output_dir / "forecast_v1_metrics.json").write_text(
        json.dumps(artifact["metrics"] | {"model_version": MODEL_VERSION}, indent=2),
        encoding="utf-8",
    )
    return {"model_path": str(path), **artifact["metrics"], "model_version": MODEL_VERSION}


def forecast_grade(
    artifact: dict,
    *,
    grade: str,
    history: list[float],
    period: str,
    tire_industry_growth: float = 0.04,
    exchange_rate_volatility: float = 0.1,
    crude_oil_price_usd: float = 78.0,
    month_index: int | None = None,
) -> dict:
    if grade not in GRADES:
        raise ValueError(f"Unsupported grade: {grade}")
    months = PERIOD_MONTHS[period]
    gi = GRADES.index(grade)
    base = artifact["grade_base"][grade]
    hist = list(history[-3:]) if history else [base, base, base]
    while len(hist) < 3:
        hist.insert(0, base)
    lag1, lag2, lag3 = hist[-1], hist[-2], hist[-3]
    month = month_index if month_index is not None else 7
    features = np.asarray(
        [
            [
                gi,
                month % 12,
                tire_industry_growth,
                exchange_rate_volatility,
                crude_oil_price_usd,
                lag1,
                lag2,
                lag3,
                (lag1 + lag2 + lag3) / 3,
            ]
        ],
        dtype=np.float64,
    )
    monthly = float(max(0.0, artifact["model"].predict(features)[0]))
    total = monthly * months
    lower = total * 0.9
    upper = total * 1.1
    safety = monthly * 0.12
    margin = artifact["grade_properties"][grade]["margin"]
    line = "Line_1" if gi < 4 else "Line_2" if gi < 8 else "Line_3"
    return {
        "product_grade": grade,
        "forecast_period": period,
        "forecast_quantity_kg": round(total, 2),
        "monthly_run_rate_kg": round(monthly, 2),
        "confidence_interval": {"lower": round(lower, 2), "upper": round(upper, 2), "confidence_level": 0.9},
        "recommended_production": {
            "quantity_kg": round(total * 0.98, 2),
            "safety_stock_kg": round(safety, 2),
            "production_line": line,
            "margin_score": margin,
        },
        "model_version": artifact["model_version"],
    }


def recommend_grade(need: dict, artifact: dict | None = None) -> dict:
    props = (artifact or {}).get("grade_properties") or GRADE_PROPERTIES
    scored = []
    for grade, p in props.items():
        score = 0.0
        for key in ("conductivity", "dispersion", "tint_strength"):
            if need.get(key) and p.get(key) == need[key]:
                score += 2.0
            elif need.get(key) and need[key] in str(p.get(key)):
                score += 1.0
        score += float(p.get("margin", 0)) * 10
        scored.append({"grade": grade, "score": round(score, 3), "properties": p})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return {
        "recommendation": scored[0]["grade"],
        "alternatives": scored[1:4],
        "ranked": scored[:6],
        "model_version": "grade-match-v1",
    }


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
