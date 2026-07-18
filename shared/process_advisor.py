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
                "action_fa": "کاهش دبی روغن خوراک ۳–۵٪ و/یا افزایش آب کوئنچ",
                "mode": "auto_eligible",
                "setpoint_hint": {"oil_feed_rate_delta_pct": -4, "quench_water_flow_delta_pct": 6},
                "expected_effect_fa": "کاهش دمای ناحیه واکنش به داخل باند عملیاتی",
                "risk_fa": "کاهش بیش از حد روغن ممکن است کیفیت ساختار را تغییر دهد",
            },
            {
                "action_id": "verify_thermocouple",
                "action_fa": "بازرسی دستی ترموکوپل / کالیبراسیون",
                "mode": "manual_only",
                "expected_effect_fa": "حذف هشدار کاذب ناشی از سنسور معیوب",
                "risk_fa": "نیاز به توقف کوتاه اندازه‌گیری",
            },
        ],
        "low": [
            {
                "action_id": "increase_oil_or_air",
                "action_fa": "افزایش کنترل‌شده دبی روغن یا هوا برای بازیابی دما",
                "mode": "auto_eligible",
                "setpoint_hint": {"oil_feed_rate_delta_pct": 3, "air_flow_delta_pct": 2},
                "expected_effect_fa": "بازگشت دما به محدوده عملیاتی",
                "risk_fa": "افزایش ناگهانی ممکن است فشار را بالا ببرد",
            },
        ],
    },
    "oil_feed_rate": {
        "high": [
            {
                "action_id": "trim_oil_feed",
                "action_fa": "کاهش ست‌پوینت دبی روغن به لبه بالای مجاز",
                "mode": "auto_eligible",
                "setpoint_hint": {"oil_feed_rate_target": "max_op"},
                "expected_effect_fa": "بازگشت دبی به رنج و کاهش بار حرارتی",
                "risk_fa": "کاهش تولید لحظه‌ای",
            },
        ],
        "low": [
            {
                "action_id": "raise_oil_feed",
                "action_fa": "افزایش تدریجی دبی روغن تا حداقل عملیاتی +۲٪",
                "mode": "auto_eligible",
                "setpoint_hint": {"oil_feed_rate_delta_pct": 2},
                "expected_effect_fa": "پایداری شعله و کیفیت گرید",
                "risk_fa": "نوسان کوتاه‌مدت فشار",
            },
        ],
    },
    "air_flow": {
        "high": [
            {
                "action_id": "reduce_air_damper",
                "action_fa": "بستن جزئی دمپر هوا / کاهش ست‌پوینت دبی هوا",
                "mode": "auto_eligible",
                "setpoint_hint": {"air_flow_delta_pct": -5},
                "expected_effect_fa": "نسبت سوخت-هوا به محدوده بازمی‌گردد",
                "risk_fa": "دود ناقص در صورت کاهش بیش از حد",
            },
        ],
        "low": [
            {
                "action_id": "open_air_damper",
                "action_fa": "باز کردن دمپر هوا برای افزایش دبی",
                "mode": "auto_eligible",
                "setpoint_hint": {"air_flow_delta_pct": 5},
                "expected_effect_fa": "احتراق کامل‌تر و کنترل دوده",
                "risk_fa": "خنک‌شدن بیش از حد ناحیه واکنش",
            },
        ],
    },
    "pressure": {
        "high": [
            {
                "action_id": "relieve_bag_or_fan",
                "action_fa": "پالس پاکسازی فیلتر / افزایش دور فن القایی",
                "mode": "auto_eligible",
                "setpoint_hint": {"fan_speed_delta_pct": 4, "bag_pulse": True},
                "expected_effect_fa": "افت فشار دیفرانسیلی به محدوده برمی‌گردد",
                "risk_fa": "سایش کیسه فیلتر در پالس مکرر",
            },
            {
                "action_id": "inspect_duct_blockage",
                "action_fa": "بازرسی دستی مسیر گاز و گرفتگی داکت",
                "mode": "manual_only",
                "expected_effect_fa": "رفع گرفتگی فیزیکی",
                "risk_fa": "نیاز به دسترسی ایمن به خط",
            },
        ],
        "low": [
            {
                "action_id": "check_leak_seal",
                "action_fa": "بررسی نشتی فلنج / آب‌بند و تنظیم فن",
                "mode": "manual_only",
                "expected_effect_fa": "بازیابی فشار خط",
                "risk_fa": "ورود هوای اضافی ناخواسته",
            },
        ],
    },
    "vibration_x": {
        "high": [
            {
                "action_id": "reduce_fan_speed",
                "action_fa": "کاهش دور فن و ثبت طیف ارتعاش",
                "mode": "auto_eligible",
                "setpoint_hint": {"fan_speed_delta_pct": -8},
                "expected_effect_fa": "کاهش دامنه ارتعاش تا زیر حد",
                "risk_fa": "کاهش مکش گاز",
            },
            {
                "action_id": "mechanical_balance_check",
                "action_fa": "بازرسی یاتاقان / بالانس مکانیکی (دستی)",
                "mode": "manual_only",
                "expected_effect_fa": "رفع ریشه ارتعاش",
                "risk_fa": "توقف برنامه‌ریزی‌شده",
            },
        ],
        "low": [],
    },
    "moisture": {
        "high": [
            {
                "action_id": "raise_dryer_temp",
                "action_fa": "افزایش دمای خشک‌کن ۲–۴٪",
                "mode": "auto_eligible",
                "setpoint_hint": {"dryer_temp_delta_pct": 3},
                "expected_effect_fa": "کاهش رطوبت محصول به مشخصات",
                "risk_fa": "مصرف انرژی بالاتر",
            },
        ],
        "low": [
            {
                "action_id": "trim_dryer_temp",
                "action_fa": "کاهش ملایم دمای خشک‌کن برای جلوگیری از overdry",
                "mode": "auto_eligible",
                "setpoint_hint": {"dryer_temp_delta_pct": -2},
                "expected_effect_fa": "پایداری کیفیت و صرفه‌جویی انرژی",
                "risk_fa": "رطوبت ممکن است دوباره بالا برود",
            },
        ],
    },
    "quench_water_flow": {
        "high": [
            {
                "action_id": "trim_quench",
                "action_fa": "کاهش دبی آب کوئنچ به باند مجاز",
                "mode": "auto_eligible",
                "setpoint_hint": {"quench_water_flow_delta_pct": -5},
                "expected_effect_fa": "کنترل دمای دود و مصرف آب",
                "risk_fa": "دمای گاز خروجی ممکن است بالا برود",
            },
        ],
        "low": [
            {
                "action_id": "boost_quench",
                "action_fa": "افزایش دبی آب کوئنچ",
                "mode": "auto_eligible",
                "setpoint_hint": {"quench_water_flow_delta_pct": 6},
                "expected_effect_fa": "محافظت حرارتی پایین‌دست",
                "risk_fa": "بار پمپ و مصرف آب",
            },
        ],
    },
    "current_draw": {
        "high": [
            {
                "action_id": "shed_motor_load",
                "action_fa": "کاهش بار موتور / بررسی overload",
                "mode": "auto_eligible",
                "setpoint_hint": {"motor_load_delta_pct": -5},
                "expected_effect_fa": "جریان به محدوده ایمن برمی‌گردد",
                "risk_fa": "کاهش ظرفیت انتقال",
            },
            {
                "action_id": "electrician_inspection",
                "action_fa": "بازرسی الکتریکی توسط اپراتور ارشد (دستی)",
                "mode": "manual_only",
                "expected_effect_fa": "تشخیص اتصال کوتاه / یاتاقان گیر",
                "risk_fa": "نیاز به LOTO",
            },
        ],
        "low": [],
    },
    "oil_pressure": {
        "low": [
            {
                "action_id": "protect_lubrication",
                "action_fa": "هشدار حفاظت روغن — کاهش دور و آلارم اتاق کنترل",
                "mode": "auto_eligible",
                "setpoint_hint": {"fan_speed_delta_pct": -10, "interlock": "lube_low"},
                "expected_effect_fa": "جلوگیری از آسیب یاتاقان",
                "risk_fa": "کاهش ظرفیت خط",
            },
            {
                "action_id": "check_lube_pump",
                "action_fa": "بازرسی پمپ روغن و فیلتر (دستی)",
                "mode": "manual_only",
                "expected_effect_fa": "رفع علت فشار پایین",
                "risk_fa": "توقف جزئی",
            },
        ],
        "high": [
            {
                "action_id": "relieve_lube_pressure",
                "action_fa": "بررسی رگلاتور فشار روغن",
                "mode": "manual_only",
                "expected_effect_fa": "فشار به باند مجاز",
                "risk_fa": "نشتی احتمالی",
            },
        ],
    },
}


def _generic_actions(direction: str, severity: str) -> list[dict[str, Any]]:
    if direction == "high":
        return [
            {
                "action_id": "nudge_setpoint_down",
                "action_fa": "کاهش تدریجی ست‌پوینت مرتبط تا بازگشت به رنج",
                "mode": "auto_eligible" if severity == "critical" else "manual_only",
                "setpoint_hint": {"generic_delta_pct": -4},
                "expected_effect_fa": "بازگشت مقدار اندازه‌گیری به باند عملیاتی",
                "risk_fa": "اثر جانبی روی کیفیت بچ",
            },
            {
                "action_id": "operator_verify",
                "action_fa": "تأیید میدانی توسط اپراتور و ثبت در لاگ شیفت",
                "mode": "manual_only",
                "expected_effect_fa": "اعتبارسنجی هشدار",
                "risk_fa": "تأخیر واکنش",
            },
        ]
    if direction == "low":
        return [
            {
                "action_id": "nudge_setpoint_up",
                "action_fa": "افزایش تدریجی ست‌پوینت مرتبط تا حداقل عملیاتی",
                "mode": "auto_eligible" if severity == "critical" else "manual_only",
                "setpoint_hint": {"generic_delta_pct": 4},
                "expected_effect_fa": "بازگشت به باند عملیاتی",
                "risk_fa": "نوسان کوتاه‌مدت فرآیند",
            },
            {
                "action_id": "operator_verify",
                "action_fa": "تأیید میدانی توسط اپراتور و ثبت در لاگ شیفت",
                "mode": "manual_only",
                "expected_effect_fa": "اعتبارسنجی هشدار",
                "risk_fa": "تأخیر واکنش",
            },
        ]
    return [
        {
            "action_id": "monitor",
            "action_fa": "پایش مداوم — اقدام فوری لازم نیست",
            "mode": "manual_only",
            "expected_effect_fa": "جلوگیری از اقدام نادرست",
            "risk_fa": "کم",
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
        return {"status": "rejected", "reason_fa": "پیشنهادی موجود نیست"}

    if mode == "auto" and not chosen.get("auto_eligible"):
        return {
            "status": "skipped",
            "reason_fa": "این اقدام فقط دستی است — Auto Pilot اجرا نکرد",
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
            "message_fa": "Auto Pilot خاموش است — فقط پیشنهاد نمایش داده می‌شود",
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
        "message_fa": f"Auto Pilot: {len(applied)} اقدام خودکار · {skipped} رد/معوق",
    }
