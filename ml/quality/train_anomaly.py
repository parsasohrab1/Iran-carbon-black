"""Phase 2 quality anomaly detector — RandomForest on process + quality features."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

MODEL_VERSION = "quality-anomaly-rf-v1"

FEATURE_NAMES = [
    "reactor_temp",
    "feed_rate",
    "air_flow",
    "residence_time",
    "pressure",
    "oil_to_air_ratio",
    "iodine_absorption",
    "dbp_absorption",
    "surface_area",
    "particle_size",
    "tint_strength",
]

# Spec centers used to label synthetic anomalies
GRADE_CENTERS = {
    "N220": {"iodine_absorption": 82.5, "dbp_absorption": 115, "surface_area": 78.5},
    "N330": {"iodine_absorption": 81.0, "dbp_absorption": 106, "surface_area": 76.0},
    "N550": {"iodine_absorption": 44.0, "dbp_absorption": 122, "surface_area": 42.0},
}


def _sample_row(rng: np.random.Generator, anomalous: bool) -> tuple[list[float], int]:
    # Nominal process window
    reactor_temp = rng.normal(1420, 8)
    feed_rate = rng.normal(2.4, 0.08)
    air_flow = rng.normal(18.5, 0.4)
    residence_time = rng.normal(2.3, 0.08)
    pressure = rng.normal(1.4, 0.05)
    oil_to_air = rng.normal(0.78, 0.03)

    iodine = rng.normal(82.5, 1.0)
    dbp = rng.normal(115, 2.0)
    surface = rng.normal(78.5, 1.2)
    particle = rng.normal(22.5, 0.8)
    tint = rng.normal(118, 2.5)

    if anomalous:
        # Push either process or quality outside healthy band
        if rng.random() < 0.5:
            reactor_temp += rng.choice([-1, 1]) * rng.uniform(35, 55)
            oil_to_air += rng.choice([-1, 1]) * rng.uniform(0.15, 0.28)
        else:
            iodine += rng.choice([-1, 1]) * rng.uniform(8, 14)
            dbp += rng.choice([-1, 1]) * rng.uniform(12, 20)
            surface += rng.choice([-1, 1]) * rng.uniform(8, 14)

    features = [
        reactor_temp,
        feed_rate,
        air_flow,
        residence_time,
        pressure,
        oil_to_air,
        iodine,
        dbp,
        surface,
        particle,
        tint,
    ]
    return features, int(anomalous)


def extract_features(process: dict, quality: dict) -> np.ndarray:
    values = [
        float(process.get("reactor_temp", 0)),
        float(process.get("feed_rate", 0)),
        float(process.get("air_flow", 0)),
        float(process.get("residence_time", 0)),
        float(process.get("pressure", 0)),
        float(process.get("oil_to_air_ratio", 0)),
        float(quality.get("iodine_absorption", 0)),
        float(quality.get("dbp_absorption") or quality.get("DBP_absorption") or 0),
        float(quality.get("surface_area", 0)),
        float(quality.get("particle_size", 0)),
        float(quality.get("tint_strength", 0)),
    ]
    return np.asarray([values], dtype=np.float64)


def train(output_dir: Path | None = None) -> dict:
    output_dir = output_dir or Path(__file__).resolve().parents[2] / "models" / "quality"
    output_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(42)
    x, y = [], []
    for _ in range(4000):
        anomalous = rng.random() < 0.25
        row, label = _sample_row(rng, anomalous)
        x.append(row)
        y.append(label)

    x_arr = np.asarray(x, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.int64)
    x_train, x_test, y_train, y_test = train_test_split(x_arr, y_arr, test_size=0.2, random_state=42, stratify=y_arr)

    model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "rf",
                RandomForestClassifier(
                    n_estimators=200,
                    max_depth=10,
                    min_samples_leaf=2,
                    class_weight="balanced",
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    model.fit(x_train, y_train)
    preds = model.predict(x_test)
    accuracy = float(accuracy_score(y_test, preds))
    f1 = float(f1_score(y_test, preds))

    artifact = {
        "model": model,
        "feature_names": FEATURE_NAMES,
        "model_version": MODEL_VERSION,
        "metrics": {"accuracy": accuracy, "f1": f1},
        "grade_centers": GRADE_CENTERS,
    }
    path = output_dir / "anomaly_v1.joblib"
    joblib.dump(artifact, path)
    (output_dir / "anomaly_v1_metrics.json").write_text(
        json.dumps(artifact["metrics"] | {"model_version": MODEL_VERSION}, indent=2),
        encoding="utf-8",
    )
    return {"model_path": str(path), **artifact["metrics"], "model_version": MODEL_VERSION}


def recommend_process_params(process: dict, grade: str = "N220") -> dict:
    """Heuristic MPC-style nudge toward grade-healthy process window."""
    target = {
        "reactor_temp": 1425.0,
        "feed_rate": 2.45,
        "air_flow": 18.7,
        "residence_time": 2.3,
        "pressure": 1.45,
        "oil_to_air_ratio": 0.78,
    }
    recommended = {}
    deltas = {}
    for key, goal in target.items():
        current = float(process.get(key, goal))
        # Move 40% of the way toward target each recommendation cycle
        new_val = current + 0.4 * (goal - current)
        recommended[key] = round(new_val, 3)
        deltas[key] = round(new_val - current, 3)

    drift = sum(abs(v) for v in deltas.values())
    expected_defect_reduction = float(min(0.35, drift / 50.0))
    return {
        "grade": grade,
        "recommended_params": recommended,
        "deltas": deltas,
        "expected_defect_reduction": round(expected_defect_reduction, 4),
        "rationale": "Nudge reactor/air/oil ratio toward grade setpoint to reduce off-spec probability.",
        "model_version": "process-mpc-v1",
    }


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
