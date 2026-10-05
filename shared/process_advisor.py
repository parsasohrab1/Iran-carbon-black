"""Smart operational recommendations for out-of-range process sensors.

Provides auto-eligible and manual-only corrective actions for furnace CB plant.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from shared.equipment_catalog import equipment_by_id

# In-process autopilot state (per service instance)
_AUTOPILOT_ON = False
_ACTION_LOG: list[dict[str, Any]] = []


def get_autopilot() -> bool:
    return _AUTOPILOT_ON


def set_autopilot(enabled: bool) -> bool:
    global _AUTOPILOT_ON
    _AUTOPILOT_ON = bool(enabled)
    return _AUTOPILOT_ON


def recent_actions(limit: int = 20) -> list[dict[str, Any]]:
    return list(_ACTION_LOG[:limit])


def _direction(value: float | None, min_op: float, max_op: float) -> str:
    if value is None:
        return "unknown"
    if value > max_op:
        return "high"
    if value < min_op:
        return "low"
    return "in_range"


def _pct_overshoot(value: float | None, min_op: float, max_op: float) -> float:
    if value is None:
        return 0.0
    span = max(max_op - min_op, 1e-9)
    if value > max_op:
        return round((value - max_op) / span * 100, 1)
    if value < min_op:
        return round((min_op - value) / span * 100, 1)
    return 0.0


# Sensor-key → corrective playbook (high / low)
_PLAYBOOK: dict[str, dict[str, list[dict[str, Any]]]] = {
    "temperature": {
        "high": [
            {
                "action_id": "increase_quench_or_reduce_oil",
                "action_fa": "Reduce feed oil flow by 3–5% and/or increase quench water",
                "mode": "auto_eligible",
                "setpoint_hint": {"oil_feed_rate_delta_pct": -4, "quench_water_flow_delta_pct": 6},
                "expected_effect_fa": "Reduce the reaction zone temperature into the operating band",
                "risk_fa": "Reducing oil too much may change the structure quality",
            },
            {
                "action_id": "verify_thermocouple",
                "action_fa": "Manual thermocouple inspection / calibration",
                "mode": "manual_only",
                "expected_effect_fa": "Eliminate a false alarm caused by a faulty sensor",
                "risk_fa": "Requires a short interruption of measurement",
            },
        ],
        "low": [
            {
                "action_id": "increase_oil_or_air",
                "action_fa": "Controlled increase of oil or air flow to recover temperature",
                "mode": "auto_eligible",
                "setpoint_hint": {"oil_feed_rate_delta_pct": 3, "air_flow_delta_pct": 2},
                "expected_effect_fa": "Temperature returns to the operating range",
                "risk_fa": "A sudden increase may raise the pressure",
            },
        ],
    },
    "oil_feed_rate": {
        "high": [
            {
                "action_id": "trim_oil_feed",
                "action_fa": "Reduce the oil flow setpoint to the upper allowed edge",
                "mode": "auto_eligible",
                "setpoint_hint": {"oil_feed_rate_target": "max_op"},
                "expected_effect_fa": "Flow returns to range and thermal load decreases",
                "risk_fa": "Momentary production reduction",
            },
        ],
        "low": [
            {
                "action_id": "raise_oil_feed",
                "action_fa": "Gradually increase oil flow to the operating minimum +2%",
                "mode": "auto_eligible",
                "setpoint_hint": {"oil_feed_rate_delta_pct": 2},
                "expected_effect_fa": "Flame stability and grade quality",
                "risk_fa": "Short-term pressure fluctuation",
            },
        ],
    },
    "air_flow": {
        "high": [
            {
                "action_id": "reduce_air_damper",
                "action_fa": "Partially close the air damper / reduce the air flow setpoint",
                "mode": "auto_eligible",
                "setpoint_hint": {"air_flow_delta_pct": -5},
                "expected_effect_fa": "The fuel-air ratio returns to range",
                "risk_fa": "Incomplete smoke if reduced too much",
            },
        ],
        "low": [
            {
                "action_id": "open_air_damper",
                "action_fa": "Open the air damper to increase flow",
                "mode": "auto_eligible",
                "setpoint_hint": {"air_flow_delta_pct": 5},
                "expected_effect_fa": "More complete combustion and soot control",
                "risk_fa": "Excessive cooling of the reaction zone",
            },
        ],
    },
    "pressure": {
        "high": [
            {
                "action_id": "relieve_bag_or_fan",
                "action_fa": "Filter cleaning pulse / increase induced fan speed",
                "mode": "auto_eligible",
                "setpoint_hint": {"fan_speed_delta_pct": 4, "bag_pulse": True},
                "expected_effect_fa": "Differential pressure drop returns to range",
                "risk_fa": "Filter bag wear from repeated pulses",
            },
            {
                "action_id": "inspect_duct_blockage",
                "action_fa": "Manual inspection of the gas path and duct blockage",
                "mode": "manual_only",
                "expected_effect_fa": "Remove the physical blockage",
                "risk_fa": "Requires safe access to the line",
            },
        ],
        "low": [
            {
                "action_id": "check_leak_seal",
                "action_fa": "Check flange leaks / seals and adjust the fan",
                "mode": "manual_only",
                "expected_effect_fa": "Restore line pressure",
                "risk_fa": "Unwanted entry of excess air",
            },
        ],
    },
    "vibration_x": {
        "high": [
            {
                "action_id": "reduce_fan_speed",
                "action_fa": "Reduce fan speed and record the vibration spectrum",
                "mode": "auto_eligible",
                "setpoint_hint": {"fan_speed_delta_pct": -8},
                "expected_effect_fa": "Vibration amplitude reduced below the limit",
                "risk_fa": "Reduced gas suction",
            },
            {
                "action_id": "mechanical_balance_check",
                "action_fa": "Bearing inspection / mechanical balancing (manual)",
                "mode": "manual_only",
                "expected_effect_fa": "Eliminate the root of the vibration",
                "risk_fa": "Planned shutdown",
            },
        ],
        "low": [],
    },
    "moisture": {
        "high": [
            {
                "action_id": "raise_dryer_temp",
                "action_fa": "Increase the dryer temperature by 2–4%",
                "mode": "auto_eligible",
                "setpoint_hint": {"dryer_temp_delta_pct": 3},
                "expected_effect_fa": "Reduce product moisture to specification",
                "risk_fa": "Higher energy consumption",
            },
        ],
        "low": [
            {
                "action_id": "trim_dryer_temp",
                "action_fa": "Gently reduce the dryer temperature to prevent overdrying",
                "mode": "auto_eligible",
                "setpoint_hint": {"dryer_temp_delta_pct": -2},
                "expected_effect_fa": "Quality stability and energy saving",
                "risk_fa": "Moisture may rise again",
            },
        ],
    },
    "quench_water_flow": {
        "high": [
            {
                "action_id": "trim_quench",
                "action_fa": "Reduce quench water flow to the allowed band",
                "mode": "auto_eligible",
                "setpoint_hint": {"quench_water_flow_delta_pct": -5},
                "expected_effect_fa": "Control of smoke temperature and water consumption",
                "risk_fa": "Outlet gas temperature may rise",
            },
        ],
        "low": [
            {
                "action_id": "boost_quench",
                "action_fa": "Increase quench water flow",
                "mode": "auto_eligible",
                "setpoint_hint": {"quench_water_flow_delta_pct": 6},
                "expected_effect_fa": "Downstream thermal protection",
                "risk_fa": "Pump load and water consumption",
            },
        ],
    },
    "current_draw": {
        "high": [
            {
                "action_id": "shed_motor_load",
                "action_fa": "Reduce motor load / check overload",
                "mode": "auto_eligible",
                "setpoint_hint": {"motor_load_delta_pct": -5},
                "expected_effect_fa": "Current returns to the safe range",
                "risk_fa": "Reduced conveying capacity",
            },
            {
                "action_id": "electrician_inspection",
                "action_fa": "Electrical inspection by the senior operator (manual)",
                "mode": "manual_only",
                "expected_effect_fa": "Diagnose a short circuit / seized bearing",
                "risk_fa": "LOTO required",
            },
        ],
        "low": [],
    },
    "oil_pressure": {
        "low": [
            {
                "action_id": "protect_lubrication",
                "action_fa": "Oil protection alarm — reduce speed and control room alarm",
                "mode": "auto_eligible",
                "setpoint_hint": {"fan_speed_delta_pct": -10, "interlock": "lube_low"},
                "expected_effect_fa": "Prevent bearing damage",
                "risk_fa": "Reduced line capacity",
            },
            {
                "action_id": "check_lube_pump",
                "action_fa": "Inspect the oil pump and filter (manual)",
                "mode": "manual_only",
                "expected_effect_fa": "Eliminate the cause of low pressure",
                "risk_fa": "Partial shutdown",
            },
        ],
        "high": [
            {
                "action_id": "relieve_lube_pressure",
                "action_fa": "Check the oil pressure regulator",
                "mode": "manual_only",
                "expected_effect_fa": "Pressure to the allowed band",
                "risk_fa": "Possible leak",
            },
        ],
    },
}


def _generic_actions(direction: str, severity: str) -> list[dict[str, Any]]:
    if direction == "high":
        return [
            {
                "action_id": "nudge_setpoint_down",
                "action_fa": "Gradually reduce the related setpoint until it returns to range",
                "mode": "auto_eligible" if severity == "critical" else "manual_only",
                "setpoint_hint": {"generic_delta_pct": -4},
                "expected_effect_fa": "The measured value returns to the operating band",
                "risk_fa": "Side effect on batch quality",
            },
            {
                "action_id": "operator_verify",
                "action_fa": "Field confirmation by the operator and logging in the shift log",
                "mode": "manual_only",
                "expected_effect_fa": "Alert validation",
                "risk_fa": "Delayed response",
            },
        ]
    if direction == "low":
        return [
            {
                "action_id": "nudge_setpoint_up",
                "action_fa": "Gradually increase the related setpoint to the operating minimum",
                "mode": "auto_eligible" if severity == "critical" else "manual_only",
                "setpoint_hint": {"generic_delta_pct": 4},
                "expected_effect_fa": "Return to the operating band",
                "risk_fa": "Short-term process fluctuation",
            },
            {
                "action_id": "operator_verify",
                "action_fa": "Field confirmation by the operator and logging in the shift log",
                "mode": "manual_only",
                "expected_effect_fa": "Alert validation",
                "risk_fa": "Delayed response",
            },
        ]
    return [
        {
            "action_id": "monitor",
            "action_fa": "Continuous monitoring — no immediate action needed",
            "mode": "manual_only",
            "expected_effect_fa": "Prevent incorrect action",
            "risk_fa": "Low",
        }
    ]


def recommend_for_alert(alert: dict[str, Any]) -> dict[str, Any]:
    """Attach ranked smart recommendations to a process alert."""
    key = str(alert.get("sensor_key") or "")
    # strip equipment prefix if tag-like
    base_key = key.split(".")[-1].lower() if "." in key else key.lower()
    # map vibration_y etc.
    if base_key.startswith("vibration"):
        play_key = "vibration_x"
    else:
        play_key = base_key

    val = alert.get("measured_value", alert.get("value"))
    try:
        val_f = float(val) if val is not None else None
    except (TypeError, ValueError):
        val_f = None
    lo = float(alert.get("min_op") or 0)
    hi = float(alert.get("max_op") or 0)
    direction = _direction(val_f, lo, hi)
    severity = str(alert.get("severity") or "warning")
    overshoot = _pct_overshoot(val_f, lo, hi)

    book = _PLAYBOOK.get(play_key, {})
    actions = list(book.get(direction) or [])
    if not actions:
        actions = _generic_actions(direction, severity)

    # Enrich names from catalog
    eid = str(alert.get("equipment_id") or "")
    eq = equipment_by_id().get(eid, {})
    sensor_name = alert.get("sensor_name")
    if not sensor_name:
        for s in eq.get("sensors") or []:
            if s.get("key") == key or s.get("key") == base_key:
                sensor_name = s.get("name_fa")
                break

    enriched = []
    for i, a in enumerate(actions):
        enriched.append(
            {
                **a,
                "rank": i + 1,
                "auto_eligible": a.get("mode") == "auto_eligible",
                "confidence": round(0.92 - i * 0.08 - min(overshoot, 40) * 0.002, 2),
            }
        )

    primary = enriched[0] if enriched else None
    return {
        **alert,
        "equipment_name": alert.get("equipment_name") or eq.get("name_fa") or eid,
        "sensor_name": sensor_name or key,
        "breach_direction": direction,
        "overshoot_pct": overshoot,
        "recommendations": enriched,
        "primary_recommendation": primary,
        "advisor_version": "process-advisor-v1",
    }


def enrich_alerts(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [recommend_for_alert(a) for a in alerts]


def apply_recommendation(
    alert: dict[str, Any],
    *,
    action_id: str | None = None,
    mode: str = "manual",
    operator: str = "operator",
) -> dict[str, Any]:
    """Simulate applying a corrective action (SCADA writeback stub)."""
    enriched = recommend_for_alert(alert)
    recs = enriched.get("recommendations") or []
    chosen = None
    if action_id:
        chosen = next((r for r in recs if r.get("action_id") == action_id), None)
    if chosen is None and recs:
        # autopilot picks first auto_eligible
        if mode == "auto":
            chosen = next((r for r in recs if r.get("auto_eligible")), recs[0])
        else:
            chosen = recs[0]

    if chosen is None:
        return {"status": "rejected", "reason_fa": "No suggestion available"}

    if mode == "auto" and not chosen.get("auto_eligible"):
        return {
            "status": "skipped",
            "reason_fa": "This action is manual only — Auto Pilot did not execute it",
            "recommendation": chosen,
        }

    entry = {
        "id": str(uuid4())[:8],
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "operator": operator if mode == "manual" else "autopilot",
        "equipment_id": enriched.get("equipment_id"),
        "equipment_name": enriched.get("equipment_name"),
        "sensor_key": enriched.get("sensor_key"),
        "sensor_name": enriched.get("sensor_name"),
        "severity": enriched.get("severity"),
        "action_id": chosen.get("action_id"),
        "action_fa": chosen.get("action_fa"),
        "setpoint_hint": chosen.get("setpoint_hint"),
        "expected_effect_fa": chosen.get("expected_effect_fa"),
        "status": "applied",
        "scada_writeback": "simulated",
    }
    _ACTION_LOG.insert(0, entry)
    del _ACTION_LOG[100:]
    return {"status": "applied", "action": entry, "alert": enriched}


def run_autopilot_pass(alerts: list[dict[str, Any]]) -> dict[str, Any]:
    """If autopilot ON, auto-apply primary auto_eligible action for critical alerts."""
    if not _AUTOPILOT_ON:
        return {
            "autopilot": False,
            "applied": [],
            "skipped": len(alerts),
            "message_fa": "Auto Pilot is off — only suggestions are shown",
        }
    applied = []
    skipped = 0
    recent_keys = {
        (a.get("equipment_id"), a.get("sensor_key"), a.get("action_id"))
        for a in _ACTION_LOG[:40]
        if a.get("mode") == "auto"
    }
    for a in alerts:
        sev = str(a.get("severity") or "")
        enriched = recommend_for_alert(a)
        primary = enriched.get("primary_recommendation") or {}
        # Auto: all critical; also warning if action is auto_eligible
        if sev != "critical" and not (
            sev == "warning" and primary.get("auto_eligible")
        ):
            skipped += 1
            continue
        key = (enriched.get("equipment_id"), enriched.get("sensor_key"), primary.get("action_id"))
        if key in recent_keys:
            skipped += 1
            continue
        result = apply_recommendation(a, mode="auto", operator="autopilot")
        if result.get("status") == "applied":
            applied.append(result["action"])
            recent_keys.add(key)
        else:
            skipped += 1
    return {
        "autopilot": True,
        "applied": applied,
        "skipped": skipped,
        "message_fa": f"Auto Pilot: {len(applied)} automatic actions · {skipped} rejected/deferred",
    }
