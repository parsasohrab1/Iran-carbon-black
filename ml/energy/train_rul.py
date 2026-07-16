"""Phase 1 RUL model: train GradientBoosting on synthetic run-to-failure trajectories."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURE_NAMES = [
    "vibration_x",
    "vibration_y",
    "vibration_z",
    "temperature",
    "pressure",
    "current_draw",
    "oil_pressure",
    "coolant_temp",
    "vib_rms",
    "thermal_stress",
]

MODEL_VERSION = "rul-gbr-v1"
ALERT_RUL_DAYS = 3.0


def _simulate_run_to_failure(n_cycles: int = 200, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    rows: list[list[float]] = []
    targets: list[float] = []

    for _ in range(n_cycles):
        life = int(rng.integers(50, 140))
        base_temp = rng.uniform(65, 78)
        base_vib = rng.uniform(1.2, 2.2)
        for t in range(life):
            progress = t / max(life - 1, 1)
            # Stronger monotonic degradation → learnable RUL signal
            degradation = progress**1.35
            noise = 0.03
            vibration_x = base_vib + degradation * 4.0 + rng.normal(0, noise)
            vibration_y = base_vib * 0.85 + degradation * 3.2 + rng.normal(0, noise)
            vibration_z = base_vib * 1.2 + degradation * 5.0 + rng.normal(0, noise)
            temperature = base_temp + degradation * 40 + rng.normal(0, 0.35)
            pressure = 11.5 + degradation * 3.0 + rng.normal(0, 0.08)
            current_draw = 130 + degradation * 55 + rng.normal(0, 0.8)
            oil_pressure = 5.2 - degradation * 2.2 + rng.normal(0, 0.03)
            coolant_temp = 58 + degradation * 25 + rng.normal(0, 0.3)
            vib_rms = float(np.sqrt((vibration_x**2 + vibration_y**2 + vibration_z**2) / 3))
            thermal_stress = temperature / max(coolant_temp, 1.0)
            rows.append(
                [
                    vibration_x,
                    vibration_y,
                    vibration_z,
                    temperature,
                    pressure,
                    current_draw,
                    oil_pressure,
                    coolant_temp,
                    vib_rms,
                    thermal_stress,
                ]
            )
            targets.append(float(life - t))

    return np.asarray(rows, dtype=np.float64), np.asarray(targets, dtype=np.float64)


def extract_features(sensors: dict[str, float]) -> np.ndarray:
    vx = float(sensors.get("vibration_x", 0.0))
    vy = float(sensors.get("vibration_y", 0.0))
    vz = float(sensors.get("vibration_z", 0.0))
    temperature = float(sensors.get("temperature", 0.0))
    pressure = float(sensors.get("pressure", 0.0))
    current_draw = float(sensors.get("current_draw", 0.0))
    oil_pressure = float(sensors.get("oil_pressure", 0.0))
    coolant_temp = float(sensors.get("coolant_temp", 1.0))
    vib_rms = float(np.sqrt((vx**2 + vy**2 + vz**2) / 3))
    thermal_stress = temperature / max(coolant_temp, 1.0)
    return np.asarray(
        [[vx, vy, vz, temperature, pressure, current_draw, oil_pressure, coolant_temp, vib_rms, thermal_stress]],
        dtype=np.float64,
    )


def failure_probability_from_rul(rul_days: float) -> float:
    return float(1.0 / (1.0 + np.exp((rul_days - ALERT_RUL_DAYS) / 2.5)))


def train(output_dir: Path | None = None) -> dict:
    output_dir = output_dir or Path(__file__).resolve().parents[2] / "models" / "energy"
    output_dir.mkdir(parents=True, exist_ok=True)

    x, y = _simulate_run_to_failure()
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)

    model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "gbr",
                GradientBoostingRegressor(
                    n_estimators=250,
                    learning_rate=0.05,
                    max_depth=4,
                    subsample=0.9,
                    random_state=42,
                ),
            ),
        ]
    )
    model.fit(x_train, y_train)
    preds = model.predict(x_test)
    mae = float(mean_absolute_error(y_test, preds))
    r2 = float(r2_score(y_test, preds))

    # Operational KPI (PM-02/PM-03): correct detection of RUL <= 3 day alert window
    true_alert = y_test <= ALERT_RUL_DAYS
    pred_alert = preds <= ALERT_RUL_DAYS
    alert_accuracy = float(np.mean(true_alert == pred_alert))
    within_15pct = float(np.mean(np.abs(preds - y_test) <= np.maximum(y_test * 0.15, 2.0)))

    artifact = {
        "model": model,
        "feature_names": FEATURE_NAMES,
        "model_version": MODEL_VERSION,
        "alert_rul_days": ALERT_RUL_DAYS,
        "metrics": {
            "mae_days": mae,
            "r2": r2,
            "alert_accuracy": alert_accuracy,
            "within_15pct": within_15pct,
        },
    }
    model_path = output_dir / "rul_v1.joblib"
    metrics_path = output_dir / "rul_v1_metrics.json"
    joblib.dump(artifact, model_path)
    metrics_path.write_text(
        json.dumps(artifact["metrics"] | {"model_version": MODEL_VERSION}, indent=2),
        encoding="utf-8",
    )
    return {"model_path": str(model_path), **artifact["metrics"], "model_version": MODEL_VERSION}


if __name__ == "__main__":
    result = train()
    print(json.dumps(result, indent=2))
