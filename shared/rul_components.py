"""Component-level predictive maintenance (RUL) for belts, oil, air, bearings, filters, etc.

Generates Persian maintenance alerts with remaining useful life estimates from
process sensors (vibration, oil pressure, air flow, current, temperature).
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from shared.equipment_catalog import EQUIPMENT, simulate_reading

# Nominal baseline RUL (days) when healthy
BASE_RUL_DAYS: dict[str, float] = {
    "belt": 90,
    "oil": 45,
    "air": 60,
    "bearing": 120,
    "filter": 30,
    "seal": 75,
    "motor": 180,
    "coupling": 100,
}

COMPONENT_LABEL_FA: dict[str, str] = {
    "belt": "تسمه",
    "oil": "روغن / روانکاری",
    "air": "هوا / سیستم هوا",
    "bearing": "یاتاقان",
    "filter": "فیلتر",
    "seal": "آب‌بند / سیل",
    "motor": "موتور الکتریکی",
    "coupling": "کوپلینگ",
}

ALERT_THRESHOLD_DAYS = 14.0  # raise maintenance alert when RUL <= this


def _component_defs() -> list[dict[str, Any]]:
    """Wear components linked to plant equipment."""
    return [
        # —— تسمه‌ها ——
        {
            "id": "CMP-BELT-DRY",
            "component_type": "belt",
            "name_fa": "تسمه درایو خشک‌کن دوار",
            "equipment_id": "DRY-001",
            "sensors": ["vibration_x", "current_draw", "temperature"],
            "failure_mode_fa": "سایش / لغزش تسمه",
            "action_fa": "بازرسی کشش تسمه، تعویض در صورت ترک یا براق‌شدگی",
        },
        {
            "id": "CMP-BELT-GRN",
            "component_type": "belt",
            "name_fa": "تسمه انتقال گرانولاتور",
            "equipment_id": "GRN-001",
            "sensors": ["vibration_x", "current_draw"],
            "failure_mode_fa": "پارگی یا شل‌شدن تسمه",
            "action_fa": "تنظیم کشش و تعویض تسمه یدکی",
        },
        {
            "id": "CMP-BELT-SCR",
            "component_type": "belt",
            "name_fa": "تسمه سرند محصول",
            "equipment_id": "SCR-001",
            "sensors": ["vibration_x", "current_draw", "throughput"],
            "failure_mode_fa": "فرسودگی تسمه ویبره",
            "action_fa": "تعویض تسمه سرند و بالانس دینامیکی",
        },
        {
            "id": "CMP-BELT-PKG",
            "component_type": "belt",
            "name_fa": "تسمه نقاله بسته‌بندی",
            "equipment_id": "PKG-001",
            "sensors": ["current_draw", "throughput"],
            "failure_mode_fa": "لغزش تسمه نقاله",
            "action_fa": "تمیزکاری غلطک و تعویض تسمه در صورت سایش",
        },
        # —— روغن ——
        {
            "id": "CMP-OIL-FEED",
            "component_type": "oil",
            "name_fa": "روغن روانکار پمپ خوراک CBFS",
            "equipment_id": "OIL-001",
            "sensors": ["oil_pressure", "temperature", "current_draw"],
            "failure_mode_fa": "افت فشار / آلودگی روغن",
            "action_fa": "آنالیز روغن، تعویض فیلتر و تکمیل سطح",
        },
        {
            "id": "CMP-OIL-FAN",
            "component_type": "oil",
            "name_fa": "روغن یاتاقان فن مکش",
            "equipment_id": "FAN-001",
            "sensors": ["oil_pressure", "temperature", "vibration_x"],
            "failure_mode_fa": "کاهش روانکاری یاتاقان",
            "action_fa": "کنترل سطح روغن و تعویض طبق برنامه PM",
        },
        {
            "id": "CMP-OIL-CMP",
            "component_type": "oil",
            "name_fa": "روغن کمپرسور هوای ابزار دقیق",
            "equipment_id": "CMP-001",
            "sensors": ["oil_pressure", "temperature", "current_draw"],
            "failure_mode_fa": "اکسیداسیون / افت ویسکوزیته",
            "action_fa": "تعویض روغن کمپرسور و فیلتر سپراتور",
        },
        {
            "id": "CMP-OIL-GEN",
            "component_type": "oil",
            "name_fa": "روغن موتور ژنراتور اضطراری",
            "equipment_id": "GEN-001",
            "sensors": ["oil_pressure", "temperature", "current_draw"],
            "failure_mode_fa": "فشار پایین روغن موتور",
            "action_fa": "تست استندبای، تعویض روغن و فیلتر",
        },
        # —— هوا ——
        {
            "id": "CMP-AIR-BLOW",
            "component_type": "air",
            "name_fa": "سیستم هوای احتراق (دمنده)",
            "equipment_id": "AIR-001",
            "sensors": ["air_flow", "pressure", "vibration_x", "current_draw"],
            "failure_mode_fa": "کاهش ظرفیت هوا / گرفتگی",
            "action_fa": "بازرسی فیلتر ورودی هوا و بالانس دمپر",
        },
        {
            "id": "CMP-AIR-PNE",
            "component_type": "air",
            "name_fa": "هوای انتقال پنوماتیک دوده",
            "equipment_id": "PNE-001",
            "sensors": ["air_flow", "pressure", "current_draw"],
            "failure_mode_fa": "نشتی خط یا افت فشار انتقال",
            "action_fa": "نشتی‌یابی فلنج‌ها و تنظیم بلوور",
        },
        {
            "id": "CMP-AIR-CMP",
            "component_type": "air",
            "name_fa": "هوای فشرده ابزار دقیق",
            "equipment_id": "CMP-001",
            "sensors": ["pressure", "current_draw", "temperature"],
            "failure_mode_fa": "افت فشار هوای ابزار",
            "action_fa": "بازرسی درایر و تله آب؛ سرویس کمپرسور",
        },
        {
            "id": "CMP-AIR-FUR1",
            "component_type": "air",
            "name_fa": "هوای احتراق کوره خط ۱",
            "equipment_id": "FUR-001",
            "sensors": ["air_flow", "pressure", "temperature"],
            "failure_mode_fa": "نسبت هوا-سوخت نامناسب",
            "action_fa": "کالیبراسیون فلومتر هوا و بازرسی مسیر",
        },
        # —— یاتاقان ——
        {
            "id": "CMP-BRG-FAN",
            "component_type": "bearing",
            "name_fa": "یاتاقان فن ID",
            "equipment_id": "FAN-001",
            "sensors": ["vibration_x", "vibration_y", "temperature"],
            "failure_mode_fa": "خستگی یاتاقان / ارتعاش بالا",
            "action_fa": "آنالیز ارتعاش و برنامه‌ریزی تعویض یاتاقان",
        },
        {
            "id": "CMP-BRG-AIR",
            "component_type": "bearing",
            "name_fa": "یاتاقان دمنده هوا",
            "equipment_id": "AIR-001",
            "sensors": ["vibration_x", "current_draw", "temperature"],
            "failure_mode_fa": "سایش یاتاقان",
            "action_fa": "گریس‌کاری / تعویض یاتاقان",
        },
        {
            "id": "CMP-BRG-PMP",
            "component_type": "bearing",
            "name_fa": "یاتاقان پمپ آب کوئنچ",
            "equipment_id": "PMP-001",
            "sensors": ["vibration_x", "current_draw", "pressure"],
            "failure_mode_fa": "کاویتاسیون و آسیب یاتاقان",
            "action_fa": "کنترل NPSH و وضعیت یاتاقان",
        },
        # —— فیلتر ——
        {
            "id": "CMP-FLT-BAG",
            "component_type": "filter",
            "name_fa": "کیسه فیلتر بگ‌هاوس",
            "equipment_id": "BAG-001",
            "sensors": ["pressure", "pulse_pressure", "dust_outlet"],
            "failure_mode_fa": "گرفتگی / پارگی کیسه",
            "action_fa": "پالس تمیزکاری و تعویض کیسه‌های معیوب",
        },
        {
            "id": "CMP-FLT-AIR",
            "component_type": "filter",
            "name_fa": "فیلتر ورودی هوای احتراق",
            "equipment_id": "AIR-001",
            "sensors": ["air_flow", "pressure", "current_draw"],
            "failure_mode_fa": "گرفتگی فیلتر هوا",
            "action_fa": "تعویض/شستشوی فیلتر ورودی",
        },
        # —— سیل / کوپلینگ / موتور ——
        {
            "id": "CMP-SEAL-OIL",
            "component_type": "seal",
            "name_fa": "آب‌بند مکانیکی پمپ روغن",
            "equipment_id": "OIL-001",
            "sensors": ["oil_pressure", "pressure", "temperature"],
            "failure_mode_fa": "نشتی سیل",
            "action_fa": "بازرسی نشتی و تعویض سیل",
        },
        {
            "id": "CMP-CPL-FAN",
            "component_type": "coupling",
            "name_fa": "کوپلینگ فن مکش",
            "equipment_id": "FAN-001",
            "sensors": ["vibration_x", "current_draw"],
            "failure_mode_fa": "عدم هم‌محوری کوپلینگ",
            "action_fa": "آلینمنت لیزری و تعویض الاستومر",
        },
        {
            "id": "CMP-MTR-FAN",
            "component_type": "motor",
            "name_fa": "موتور فن مکش",
            "equipment_id": "FAN-001",
            "sensors": ["current_draw", "vibration_x", "temperature"],
            "failure_mode_fa": "اضافه‌بار / گرم‌شدن موتور",
            "action_fa": "ترموگرافی و تست عایق سیم‌پیچ",
        },
        {
            "id": "CMP-MTR-AIR",
            "component_type": "motor",
            "name_fa": "موتور دمنده هوا",
            "equipment_id": "AIR-001",
            "sensors": ["current_draw", "vibration_x"],
            "failure_mode_fa": "فرسودگی موتور",
            "action_fa": "بازرسی بلبرینگ موتور و جریان",
        },
    ]


def _eq_map() -> dict[str, dict[str, Any]]:
    return {e["id"]: e for e in EQUIPMENT}


def _sensor_band(equipment: dict[str, Any], key: str) -> tuple[float, float] | None:
    for s in equipment.get("sensors") or []:
        if s["key"] == key:
            return float(s["min_op"]), float(s["max_op"])
    return None


def _health_score(component: dict[str, Any], readings: dict[str, float], equipment: dict[str, Any]) -> float:
    """0 = failed, 1 = healthy. Aggregates normalized sensor stress."""
    scores: list[float] = []
    for key in component.get("sensors") or []:
        band = _sensor_band(equipment, key)
        if band is None or key not in readings:
            continue
        lo, hi = band
        val = float(readings[key])
        span = max(hi - lo, 1e-9)
        mid = (lo + hi) / 2
        # distance from center relative to half-span; clip
        dist = abs(val - mid) / (span / 2)
        # high vibration / current near max is worse
        if key.startswith("vibration") or key in ("current_draw", "dust_outlet", "pulse_pressure"):
            # closer to max_op = worse
            stress = max(0.0, (val - lo) / span)
            scores.append(1.0 - min(1.2, stress) * 0.85)
        elif key in ("oil_pressure",) and val < mid:
            stress = (mid - val) / (span / 2)
            scores.append(1.0 - min(1.2, stress) * 0.9)
        elif key in ("air_flow",) and (val < lo + span * 0.15 or val > hi - span * 0.1):
            scores.append(0.55)
        elif val < lo or val > hi:
            scores.append(0.25)
        else:
            scores.append(max(0.35, 1.0 - dist * 0.35))
    if not scores:
        # deterministic mild wear from component id hash for demo diversity
        h = int(hashlib.md5(component["id"].encode()).hexdigest()[:6], 16)
        return 0.55 + (h % 40) / 100.0
    return max(0.05, min(1.0, sum(scores) / len(scores)))


def estimate_component_rul(
    component: dict[str, Any],
    readings: dict[str, float] | None = None,
) -> dict[str, Any]:
    eq = _eq_map().get(component["equipment_id"], {})
    if readings is None:
        readings = simulate_reading(eq, spike=False) if eq else {}
        # Bias a few components toward alert for demo visibility
        demo_stress = {"CMP-BELT-DRY", "CMP-OIL-FEED", "CMP-AIR-BLOW", "CMP-FLT-BAG", "CMP-BRG-FAN"}
        if component["id"] in demo_stress and readings:
            # push wear sensors toward failure so demo alerts are visible
            for key in component.get("sensors") or []:
                band = _sensor_band(eq, key)
                if not band:
                    continue
                lo, hi = band
                if key.startswith("vibration") or key == "current_draw":
                    readings[key] = hi * 0.98
                elif key == "oil_pressure":
                    readings[key] = lo * 0.92
                elif key in ("air_flow",):
                    readings[key] = lo + (hi - lo) * 0.05
                elif key == "pressure" and component["component_type"] == "filter":
                    readings[key] = hi * 1.12
                elif key in ("dust_outlet", "pulse_pressure", "temperature"):
                    readings[key] = hi * 0.97
            # extra deterministic wear so RUL stays under alert threshold
            health_override = 0.22 + (int(hashlib.md5(component["id"].encode()).hexdigest()[:4], 16) % 12) / 100.0
            base = BASE_RUL_DAYS.get(component["component_type"], 60)
            rul = max(1.5, min(ALERT_THRESHOLD_DAYS - 0.5, base * (health_override**1.6)))
            fail_p = max(0.35, min(0.92, 1.0 - health_override * 0.9))
            severity = "critical" if rul <= 5 else "warning"
            ctype = component["component_type"]
            return {
                "component_id": component["id"],
                "component_type": ctype,
                "component_type_fa": COMPONENT_LABEL_FA.get(ctype, ctype),
                "name_fa": component["name_fa"],
                "equipment_id": component["equipment_id"],
                "equipment_name": eq.get("name_fa") or component["equipment_id"],
                "line_id": eq.get("line_id"),
                "area": eq.get("area"),
                "rul_days": round(rul, 1),
                "failure_probability": round(fail_p, 3),
                "health_score": round(health_override, 3),
                "severity": severity,
                "alert": True,
                "alert_threshold_days": ALERT_THRESHOLD_DAYS,
                "failure_mode_fa": component.get("failure_mode_fa"),
                "recommended_action_fa": component.get("action_fa"),
                "sensors_used": component.get("sensors") or [],
                "readings_snapshot": {k: readings.get(k) for k in (component.get("sensors") or []) if k in readings},
                "message": (
                    f"RUL {COMPONENT_LABEL_FA.get(ctype, ctype)} — {component['name_fa']}: "
                    f"{round(rul, 1)} روز باقی‌مانده "
                    f"(احتمال خرابی {round(fail_p * 100, 1)}٪). {component.get('action_fa', '')}"
                ),
                "alert_type": f"rul_{ctype}",
                "as_of": datetime.now(timezone.utc).isoformat(),
                "model_version": "component-rul-v1",
            }

    health = _health_score(component, readings, eq)
    base = BASE_RUL_DAYS.get(component["component_type"], 60)
    # Nonlinear: low health collapses RUL
    rul = base * (health**1.6)
    # floor / ceiling
    rul = max(0.5, min(base * 1.1, rul))
    fail_p = max(0.02, min(0.95, 1.0 - health * 0.9))
    severity = "critical" if rul <= 5 else ("warning" if rul <= ALERT_THRESHOLD_DAYS else "info")
    ctype = component["component_type"]
    return {
        "component_id": component["id"],
        "component_type": ctype,
        "component_type_fa": COMPONENT_LABEL_FA.get(ctype, ctype),
        "name_fa": component["name_fa"],
        "equipment_id": component["equipment_id"],
        "equipment_name": eq.get("name_fa") or component["equipment_id"],
        "line_id": eq.get("line_id"),
        "area": eq.get("area"),
        "rul_days": round(rul, 1),
        "failure_probability": round(fail_p, 3),
        "health_score": round(health, 3),
        "severity": severity,
        "alert": rul <= ALERT_THRESHOLD_DAYS,
        "alert_threshold_days": ALERT_THRESHOLD_DAYS,
        "failure_mode_fa": component.get("failure_mode_fa"),
        "recommended_action_fa": component.get("action_fa"),
        "sensors_used": component.get("sensors") or [],
        "readings_snapshot": {k: readings.get(k) for k in (component.get("sensors") or []) if k in readings},
        "message": (
            f"RUL {COMPONENT_LABEL_FA.get(ctype, ctype)} — {component['name_fa']}: "
            f"{round(rul, 1)} روز باقی‌مانده "
            f"(احتمال خرابی {round(fail_p * 100, 1)}٪). {component.get('action_fa', '')}"
        ),
        "alert_type": f"rul_{ctype}",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "model_version": "component-rul-v1",
    }


def build_component_rul_board(
    *,
    readings_by_equipment: dict[str, dict[str, float]] | None = None,
    alert_only: bool = False,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for comp in _component_defs():
        eid = comp["equipment_id"]
        readings = (readings_by_equipment or {}).get(eid)
        row = estimate_component_rul(comp, readings=readings)
        rows.append(row)

    rows.sort(key=lambda r: (r["rul_days"], -r["failure_probability"]))
    alerts = [r for r in rows if r["alert"]]
    by_type: dict[str, int] = {}
    for r in rows:
        by_type[r["component_type"]] = by_type.get(r["component_type"], 0) + 1

    return {
        "source": "RUL اجزا — تسمه · روغن · هوا · یاتاقان · فیلتر · موتور",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "alert_threshold_days": ALERT_THRESHOLD_DAYS,
        "components": alerts if alert_only else rows,
        "alerts": alerts,
        "summary": {
            "component_count": len(rows),
            "alert_count": len(alerts),
            "critical_count": sum(1 for r in alerts if r["severity"] == "critical"),
            "warning_count": sum(1 for r in alerts if r["severity"] == "warning"),
            "by_type": by_type,
            "min_rul_days": rows[0]["rul_days"] if rows else None,
            "types_fa": [COMPONENT_LABEL_FA[t] for t in sorted(by_type.keys()) if t in COMPONENT_LABEL_FA],
        },
    }


def maintenance_alert_rows(board: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Flatten component alerts into maintenance_alerts-compatible dicts."""
    board = board or build_component_rul_board()
    out = []
    for a in board.get("alerts") or []:
        out.append(
            {
                "equipment_id": a["equipment_id"],
                "equipment_name": a.get("equipment_name"),
                "component_id": a["component_id"],
                "component_type": a["component_type"],
                "component_type_fa": a["component_type_fa"],
                "component_name_fa": a["name_fa"],
                "alert_type": a["alert_type"],
                "severity": a["severity"],
                "rul_days": a["rul_days"],
                "failure_probability": a["failure_probability"],
                "message": a["message"],
                "recommended_action_fa": a.get("recommended_action_fa"),
                "failure_mode_fa": a.get("failure_mode_fa"),
            }
        )
    return out
