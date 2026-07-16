"""Phase 3 finance / cashflow forecasting model."""

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

MODEL_VERSION = "finance-gbr-v1"


def _dataset(rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x, y_in, y_out = [], [], []
    revenue = 38_000_000_000
    opex = 8_000_000_000
    cogs = 30_000_000_000
    for t in range(120):
        util = 0.75 + 0.15 * np.sin(t / 6) + rng.normal(0, 0.02)
        defect = 0.02 + abs(rng.normal(0, 0.005))
        fx = 230 + t * 0.4 + rng.normal(0, 2)
        oil = 70 + 8 * np.sin(t / 5) + rng.normal(0, 1)
        inflow = revenue * util * (1 + rng.normal(0, 0.03))
        outflow = (cogs * util + opex) * (1 + 0.002 * (fx - 230) / 10) * (1 + defect)
        x.append([t % 12, util, defect, fx, oil, revenue / 1e9, cogs / 1e9, opex / 1e9, inflow / 1e9])
        y_in.append(inflow)
        y_out.append(outflow)
        revenue *= 1.002
        cogs *= 1.0025
    return np.asarray(x, np.float64), np.asarray(y_in, np.float64), np.asarray(y_out, np.float64)


def train(output_dir: Path | None = None) -> dict:
    output_dir = output_dir or Path(__file__).resolve().parents[2] / "models" / "finance"
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(33)
    x, y_in, y_out = _dataset(rng)
    x_tr, x_te, yin_tr, yin_te, yout_tr, yout_te = train_test_split(x, y_in, y_out, test_size=0.2, random_state=42)

    def fit(y_tr, y_te):
        model = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("gbr", GradientBoostingRegressor(n_estimators=180, learning_rate=0.06, max_depth=3, random_state=42)),
            ]
        )
        model.fit(x_tr, y_tr)
        preds = model.predict(x_te)
        mape = float(mean_absolute_percentage_error(y_te, preds))
        return model, {"mape": mape, "accuracy": float(max(0.0, 1 - mape)), "r2": float(r2_score(y_te, preds))}

    in_model, in_m = fit(yin_tr, yin_te)
    out_model, out_m = fit(yout_tr, yout_te)
    artifact = {
        "inflow_model": in_model,
        "outflow_model": out_model,
        "model_version": MODEL_VERSION,
        "metrics": {"inflow": in_m, "outflow": out_m},
    }
    path = output_dir / "cashflow_v1.joblib"
    joblib.dump(artifact, path)
    (output_dir / "cashflow_v1_metrics.json").write_text(
        json.dumps({"model_version": MODEL_VERSION, **artifact["metrics"]}, indent=2),
        encoding="utf-8",
    )
    return {"model_path": str(path), "model_version": MODEL_VERSION, **artifact["metrics"]}


def forecast_cashflow(
    artifact: dict,
    *,
    horizon_days: int,
    capacity_utilization: float = 0.85,
    defect_rate: float = 0.023,
    usd_irr_rate: float = 245000.0,
    crude_oil_price_usd: float = 78.0,
    revenue_ytd: float = 245e9,
    cogs: float = 195e9,
    opex: float = 32e9,
) -> dict:
    months = max(1, horizon_days // 30)
    features = np.asarray(
        [
            [
                7,
                capacity_utilization,
                defect_rate,
                usd_irr_rate / 1000,
                crude_oil_price_usd,
                revenue_ytd / 1e9 / 12,
                cogs / 1e9 / 12,
                opex / 1e9 / 12,
                revenue_ytd / 1e9 / 12,
            ]
        ],
        dtype=np.float64,
    )
    monthly_in = float(artifact["inflow_model"].predict(features)[0])
    monthly_out = float(artifact["outflow_model"].predict(features)[0])
    inflow = monthly_in * months
    outflow = monthly_out * months
    net = inflow - outflow
    if net < 0:
        risk = "high"
        recs = ["accelerate receivables", "defer non-critical CAPEX", "review generator fuel cost"]
    elif net < inflow * 0.05:
        risk = "moderate"
        recs = ["tighten working capital", "optimize grade mix toward higher margin"]
    else:
        risk = "low"
        recs = ["maintain production plan", "consider opportunistic feedstock buys"]

    conf = float(
        (
            artifact["metrics"]["inflow"]["accuracy"]
            + artifact["metrics"]["outflow"]["accuracy"]
        )
        / 2
    )
    return {
        "horizon_days": horizon_days,
        "projected_inflow": round(inflow, 2),
        "projected_outflow": round(outflow, 2),
        "net_cashflow": round(net, 2),
        "liquidity_risk": risk,
        "recommendations": recs,
        "confidence": round(conf, 3),
        "model_version": artifact["model_version"],
    }


def analyze_ratios(report: dict) -> dict:
    ratios = {
        "current_ratio": report.get("current_ratio"),
        "debt_to_equity": report.get("debt_to_equity"),
        "inventory_turnover": report.get("inventory_turnover"),
        "profit_margin": report.get("profit_margin"),
        "gross_margin": None,
    }
    if report.get("revenue_ytd") and report.get("gross_profit") is not None:
        ratios["gross_margin"] = round(float(report["gross_profit"]) / max(float(report["revenue_ytd"]), 1), 4)

    improvements = []
    if ratios["current_ratio"] is not None and ratios["current_ratio"] < 1.2:
        improvements.append("Improve current ratio via receivables collection / inventory reduction")
    if ratios["debt_to_equity"] is not None and ratios["debt_to_equity"] > 2.5:
        improvements.append("High leverage — prioritize cash generation and refinance review")
    if ratios["profit_margin"] is not None and ratios["profit_margin"] < 0.08:
        improvements.append("Margin below 8% — push high-margin grades and energy savings")
    if ratios["inventory_turnover"] is not None and ratios["inventory_turnover"] < 4:
        improvements.append("Inventory turns low — align production with demand forecasts")

    return {"ratios": ratios, "improvement_areas": improvements, "model_version": "ratio-rules-v1"}


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
