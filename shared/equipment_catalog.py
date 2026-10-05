"""Carbon black production-line equipment, sensors, and operational ranges (Shekarbon)."""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

# Sensor channel → energy.sensor_readings column (when applicable)
CHANNEL_COLUMNS = {
    "vibration_x",
    "vibration_y",
    "vibration_z",
    "temperature",
    "pressure",
    "current_draw",
    "oil_pressure",
    "coolant_temp",
}

# Plant data acquisition layer: Data Logger may be PLC or SCADA gateway
DATA_LOGGERS: list[dict[str, Any]] = [
    {
        "id": "SCADA-01",
        "name_fa": "Central production-line SCADA",
        "name_en": "Central Production SCADA",
        "kind": "scada",  # scada | plc | data_logger
        "protocol": "OPC UA / MQTT",
        "vendor": "Wonderware / Ignition-class",
        "host": "10.10.1.10",
        "poll_interval_s": 2,
        "areas": ["Reaction", "Separation", "Heat recovery"],
        "status": "online",
    },
    {
        "id": "PLC-S7-01",
        "name_fa": "Siemens S7 PLC — Line 1",
        "name_en": "Siemens S7 PLC Line 1",
        "kind": "plc",
        "protocol": "S7 / Modbus TCP",
        "vendor": "Siemens S7-1500",
        "host": "10.10.2.21",
        "poll_interval_s": 1,
        "areas": ["Reaction", "Feed", "Cooling"],
        "status": "online",
    },
    {
        "id": "PLC-S7-02",
        "name_fa": "Siemens S7 PLC — Line 2",
        "name_en": "Siemens S7 PLC Line 2",
        "kind": "plc",
        "protocol": "S7 / Modbus TCP",
        "vendor": "Siemens S7-1500",
        "host": "10.10.2.22",
        "poll_interval_s": 1,
        "areas": ["Reaction"],
        "status": "online",
    },
    {
        "id": "PLC-UTIL",
        "name_fa": "Utility and compressor PLC",
        "name_en": "Utilities PLC",
        "kind": "plc",
        "protocol": "Modbus TCP",
        "vendor": "Allen-Bradley / CompactLogix",
        "host": "10.10.3.15",
        "poll_interval_s": 2,
        "areas": ["Utility"],
        "status": "online",
    },
    {
        "id": "DL-EDGE-01",
        "name_fa": "Edge OT Data Logger (MQTT)",
        "name_en": "OT Edge Data Logger",
        "kind": "data_logger",
        "protocol": "MQTT / REST",
        "vendor": "ICB Edge Gateway",
        "host": "10.10.4.50",
        "poll_interval_s": 5,
        "areas": ["Product", "Transfer", "Packaging"],
        "status": "online",
    },
    {
        "id": "DL-VIB-01",
        "name_fa": "Vibration and machine condition Data Logger",
        "name_en": "Vibration Condition Logger",
        "kind": "data_logger",
        "protocol": "Modbus RTU / MQTT",
        "vendor": "Condition Monitoring Logger",
        "host": "10.10.4.61",
        "poll_interval_s": 3,
        "areas": ["Separation", "Utility"],
        "status": "online",
    },
]

_LOGGER_BY_AREA: dict[str, str] = {
    "Reaction": "PLC-S7-01",
    "Feed": "PLC-S7-01",
    "Heat recovery": "SCADA-01",
    "Separation": "SCADA-01",
    "Cooling": "PLC-S7-01",
    "Transfer": "DL-EDGE-01",
    "Product": "DL-EDGE-01",
    "Utility": "PLC-UTIL",
}


def _logger_for_area(area: str, line_id: str = "Line_1") -> str:
    if area == "Reaction" and line_id == "Line_2":
        return "PLC-S7-02"
    if area in ("Separation", "Heat recovery"):
        return "SCADA-01"
    return _LOGGER_BY_AREA.get(area, "DL-EDGE-01")


def _s(
    key: str,
    name_fa: str,
    unit: str,
    min_op: float,
    max_op: float,
    channel: str | None = None,
    criticality: str = "high",
    logger_id: str | None = None,
    tag: str | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "name_fa": name_fa,
        "unit": unit,
        "min_op": min_op,
        "max_op": max_op,
        "channel": channel or key if (channel or key) in CHANNEL_COLUMNS else None,
        "criticality": criticality,  # critical | high | medium
        "logger_id": logger_id,
        "tag": tag or key.upper(),
    }


EQUIPMENT: list[dict[str, Any]] = [
    {
        "id": "FUR-001",
        "name_fa": "Line 1 reaction furnace",
        "name_en": "Reactor Furnace Line 1",
        "equipment_type": "furnace",
        "location": "Reactor hall",
        "line_id": "Line_1",
        "area": "Reaction",
        "sensors": [
            _s("temperature", "Flame temperature / reaction zone", "°C", 1450, 1850, "temperature", "critical"),
            _s("pressure", "Air inlet pressure", "kPa", 8, 25, "pressure", "high"),
            _s("oil_feed_rate", "Oil feed flow", "kg/h", 1800, 4200, None, "critical"),
            _s("air_flow", "Combustion air flow", "Nm³/h", 12000, 28000, None, "critical"),
            _s("gas_flow", "Fuel gas flow", "Nm³/h", 400, 1200, None, "high"),
            _s("current_draw", "Burner / control current", "A", 15, 55, "current_draw", "medium"),
        ],
    },
    {
        "id": "FUR-002",
        "name_fa": "Line 2 reaction furnace",
        "name_en": "Reactor Furnace Line 2",
        "equipment_type": "furnace",
        "location": "Reactor hall",
        "line_id": "Line_2",
        "area": "Reaction",
        "sensors": [
            _s("temperature", "Flame temperature / reaction zone", "°C", 1450, 1850, "temperature", "critical"),
            _s("pressure", "Air inlet pressure", "kPa", 8, 25, "pressure", "high"),
            _s("oil_feed_rate", "Oil feed flow", "kg/h", 1600, 4000, None, "critical"),
            _s("air_flow", "Combustion air flow", "Nm³/h", 11000, 26000, None, "critical"),
            _s("gas_flow", "Fuel gas flow", "Nm³/h", 350, 1100, None, "high"),
            _s("current_draw", "Burner / control current", "A", 15, 55, "current_draw", "medium"),
        ],
    },
    {
        "id": "AIR-001",
        "name_fa": "Combustion air blower and preheater",
        "name_en": "Combustion Air Blower & Preheater",
        "equipment_type": "blower",
        "location": "Air utility",
        "line_id": "Line_1",
        "area": "Feed",
        "sensors": [
            _s("air_flow", "Air flow", "Nm³/h", 10000, 30000, None, "critical"),
            _s("temperature", "Preheated air temperature", "°C", 450, 750, "temperature", "high"),
            _s("pressure", "Discharge pressure", "kPa", 10, 35, "pressure", "high"),
            _s("vibration_x", "Bearing vibration", "mm/s", 0.5, 7.5, "vibration_x", "high"),
            _s("current_draw", "Motor current", "A", 80, 220, "current_draw", "medium"),
        ],
    },
    {
        "id": "OIL-001",
        "name_fa": "Feed oil (CBFS) pump and preheater",
        "name_en": "Feedstock Oil Pump & Preheater",
        "equipment_type": "pump",
        "location": "Feed station",
        "line_id": "Line_1",
        "area": "Feed",
        "sensors": [
            _s("oil_feed_rate", "Oil flow", "kg/h", 1500, 4500, None, "critical"),
            _s("temperature", "Preheated oil temperature", "°C", 180, 280, "temperature", "high"),
            _s("pressure", "Pump pressure", "kPa", 200, 800, "pressure", "high"),
            _s("oil_pressure", "Lubricating oil pressure", "bar", 1.5, 4.5, "oil_pressure", "medium"),
            _s("current_draw", "Pump current", "A", 20, 90, "current_draw", "medium"),
        ],
    },
    {
        "id": "GAS-001",
        "name_fa": "Fuel natural gas station",
        "name_en": "Natural Gas Fuel Station",
        "equipment_type": "gas_station",
        "location": "Fuel utility",
        "line_id": "UTIL",
        "area": "Feed",
        "sensors": [
            _s("gas_flow", "Gas flow", "Nm³/h", 300, 1500, None, "critical"),
            _s("pressure", "Gas line pressure", "kPa", 150, 400, "pressure", "critical"),
            _s("temperature", "Gas temperature", "°C", 5, 45, "temperature", "medium"),
        ],
    },
    {
        "id": "QNZ-001",
        "name_fa": "Reactor quench system",
        "name_en": "Reactor Quench System",
        "equipment_type": "quench",
        "location": "Reactor hall",
        "line_id": "Line_1",
        "area": "Reaction",
        "sensors": [
            _s("temperature", "Smoke temperature after quench", "°C", 700, 1100, "temperature", "critical"),
            _s("quench_water_flow", "Quench water flow", "m³/h", 8, 35, None, "critical"),
            _s("pressure", "Quench nozzle pressure", "kPa", 300, 900, "pressure", "high"),
            _s("coolant_temp", "Quench water temperature", "°C", 25, 55, "coolant_temp", "medium"),
        ],
    },
    {
        "id": "PMP-001",
        "name_fa": "Quench and cooling water pump",
        "name_en": "Quench / Cooling Water Pump",
        "equipment_type": "pump",
        "location": "Pump station",
        "line_id": "UTIL",
        "area": "Utility",
        "sensors": [
            _s("quench_water_flow", "Water flow", "m³/h", 10, 50, None, "high"),
            _s("pressure", "Discharge pressure", "kPa", 250, 700, "pressure", "high"),
            _s("vibration_x", "Vibration", "mm/s", 0.4, 6.5, "vibration_x", "medium"),
            _s("current_draw", "Motor current", "A", 25, 110, "current_draw", "medium"),
            _s("coolant_temp", "Water temperature", "°C", 20, 50, "coolant_temp", "medium"),
        ],
    },
    {
        "id": "APH-001",
        "name_fa": "Air preheater exchanger",
        "name_en": "Air Preheater Exchanger",
        "equipment_type": "heat_exchanger",
        "location": "Flue / air path",
        "line_id": "Line_1",
        "area": "Heat recovery",
        "sensors": [
            _s("temperature", "Outlet air temperature", "°C", 400, 780, "temperature", "high"),
            _s("flue_temp", "Inlet flue temperature", "°C", 600, 1000, None, "high"),
            _s("pressure", "Air-side pressure drop", "kPa", 1, 12, "pressure", "medium"),
        ],
    },
    {
        "id": "OPH-001",
        "name_fa": "Oil preheater exchanger",
        "name_en": "Oil Preheater Exchanger",
        "equipment_type": "heat_exchanger",
        "location": "Flue / oil path",
        "line_id": "Line_1",
        "area": "Heat recovery",
        "sensors": [
            _s("temperature", "Outlet oil temperature", "°C", 160, 290, "temperature", "high"),
            _s("flue_temp", "Flue temperature", "°C", 350, 700, None, "medium"),
            _s("pressure", "Oil pressure drop", "kPa", 20, 120, "pressure", "medium"),
        ],
    },
    {
        "id": "CYC-001",
        "name_fa": "Primary separation cyclone",
        "name_en": "Primary Cyclone",
        "equipment_type": "cyclone",
        "location": "Separation",
        "line_id": "Line_1",
        "area": "Separation",
        "sensors": [
            _s("pressure", "Cyclone pressure drop", "kPa", 0.5, 8, "pressure", "high"),
            _s("temperature", "Inlet gas temperature", "°C", 250, 550, "temperature", "medium"),
            _s("dp_inlet", "Inlet pressure", "kPa", -5, 15, None, "medium"),
        ],
    },
    {
        "id": "BAG-001",
        "name_fa": "Bag Filter",
        "name_en": "Baghouse Filter",
        "equipment_type": "bag_filter",
        "location": "Separation",
        "line_id": "Line_1",
        "area": "Separation",
        "sensors": [
            _s("pressure", "Filter pressure drop", "kPa", 0.8, 6, "pressure", "critical"),
            _s("temperature", "Gas temperature", "°C", 180, 280, "temperature", "high"),
            _s("dust_outlet", "Outlet dust", "mg/Nm³", 5, 50, None, "high"),
            _s("pulse_pressure", "Cleaning pulse pressure", "kPa", 400, 700, None, "medium"),
        ],
    },
    {
        "id": "FAN-001",
        "name_fa": "Stack induced-draft fan (ID Fan)",
        "name_en": "Induced Draft Fan",
        "equipment_type": "fan",
        "location": "Stack",
        "line_id": "Line_1",
        "area": "Separation",
        "sensors": [
            _s("vibration_x", "Horizontal vibration", "mm/s", 0.5, 8, "vibration_x", "critical"),
            _s("vibration_y", "Vertical vibration", "mm/s", 0.5, 8, "vibration_y", "high"),
            _s("current_draw", "Motor current", "A", 90, 280, "current_draw", "high"),
            _s("pressure", "Suction pressure", "kPa", -15, -2, "pressure", "high"),
            _s("temperature", "Bearing temperature", "°C", 35, 85, "temperature", "medium"),
        ],
    },
    {
        "id": "CLR-001",
        "name_fa": "38-meter vertical cooler",
        "name_en": "Vertical Cooler 38m",
        "equipment_type": "cooler",
        "location": "Cooling tower",
        "line_id": "Line_1",
        "area": "Cooling",
        "sensors": [
            _s("temperature", "Gas outlet temperature", "°C", 180, 280, "temperature", "high"),
            _s("coolant_temp", "Cooling water temperature", "°C", 25, 45, "coolant_temp", "high"),
            _s("pressure", "Cooler pressure drop", "kPa", 0.5, 5, "pressure", "medium"),
            _s("vibration_x", "Structure vibration", "mm/s", 0.3, 5, "vibration_x", "medium"),
        ],
    },
    {
        "id": "PNE-001",
        "name_fa": "Carbon black pneumatic conveying system",
        "name_en": "Pneumatic Conveying",
        "equipment_type": "conveyor",
        "location": "Conveying path",
        "line_id": "Line_1",
        "area": "Transfer",
        "sensors": [
            _s("pressure", "Conveying line pressure", "kPa", 20, 80, "pressure", "high"),
            _s("air_flow", "Conveying air flow", "Nm³/h", 500, 2500, None, "high"),
            _s("current_draw", "Blower current", "A", 30, 120, "current_draw", "medium"),
            _s("temperature", "Line temperature", "°C", 40, 120, "temperature", "medium"),
        ],
    },
    {
        "id": "GRN-001",
        "name_fa": "Wet pelletizer",
        "name_en": "Wet Granulator",
        "equipment_type": "granulator",
        "location": "Pelletizing unit",
        "line_id": "Line_1",
        "area": "Product",
        "sensors": [
            _s("current_draw", "Motor current", "A", 40, 160, "current_draw", "high"),
            _s("vibration_x", "Vibration", "mm/s", 0.5, 9, "vibration_x", "high"),
            _s("binder_flow", "Binder flow", "L/h", 50, 400, None, "high"),
            _s("temperature", "Chamber temperature", "°C", 30, 70, "temperature", "medium"),
        ],
    },
    {
        "id": "DRY-001",
        "name_fa": "Rotary product dryer",
        "name_en": "Rotary Dryer",
        "equipment_type": "dryer",
        "location": "Dryer unit",
        "line_id": "Line_1",
        "area": "Product",
        "sensors": [
            _s("temperature", "Dryer gas temperature", "°C", 180, 320, "temperature", "critical"),
            _s("moisture", "Outlet product moisture", "%", 0.2, 1.2, None, "critical"),
            _s("current_draw", "Drive current", "A", 50, 180, "current_draw", "medium"),
            _s("pressure", "Chamber pressure", "kPa", -2, 5, "pressure", "medium"),
        ],
    },
    {
        "id": "SCR-001",
        "name_fa": "Product screen and grading",
        "name_en": "Product Screen",
        "equipment_type": "screen",
        "location": "Packaging unit",
        "line_id": "Line_1",
        "area": "Product",
        "sensors": [
            _s("vibration_x", "Screen vibration", "mm/s", 2, 18, "vibration_x", "medium"),
            _s("current_draw", "Motor current", "A", 8, 40, "current_draw", "medium"),
            _s("throughput", "Throughput", "t/h", 2, 12, None, "high"),
        ],
    },
    {
        "id": "PKG-001",
        "name_fa": "Packaging and weighing line",
        "name_en": "Packaging & Weighing",
        "equipment_type": "packaging",
        "location": "Product warehouse hall",
        "line_id": "Line_1",
        "area": "Product",
        "sensors": [
            _s("throughput", "Packaging rate", "bag/h", 40, 180, None, "high"),
            _s("current_draw", "Line current", "A", 10, 55, "current_draw", "medium"),
            _s("weight_error", "Weighing error", "%", -1.5, 1.5, None, "critical"),
        ],
    },
    {
        "id": "CMP-001",
        "name_fa": "Instrument air compressor A",
        "name_en": "Instrument Air Compressor A",
        "equipment_type": "compressor",
        "location": "Utility",
        "line_id": "UTIL",
        "area": "Utility",
        "sensors": [
            _s("pressure", "Compressed air pressure", "kPa", 550, 850, "pressure", "critical"),
            _s("temperature", "Discharge temperature", "°C", 60, 120, "temperature", "high"),
            _s("vibration_x", "Vibration", "mm/s", 0.4, 7, "vibration_x", "high"),
            _s("oil_pressure", "Oil pressure", "bar", 2, 5, "oil_pressure", "high"),
            _s("current_draw", "Motor current", "A", 60, 200, "current_draw", "medium"),
            _s("coolant_temp", "Coolant temperature", "°C", 25, 55, "coolant_temp", "medium"),
        ],
    },
    {
        "id": "GEN-001",
        "name_fa": "Unit 1 emergency generator",
        "name_en": "Emergency Generator Unit 1",
        "equipment_type": "generator",
        "location": "Internal power plant",
        "line_id": "UTIL",
        "area": "Utility",
        "sensors": [
            _s("current_draw", "Output current", "A", 50, 400, "current_draw", "critical"),
            _s("temperature", "Generator temperature", "°C", 50, 95, "temperature", "high"),
            _s("vibration_x", "Vibration", "mm/s", 0.5, 8, "vibration_x", "high"),
            _s("oil_pressure", "Engine oil pressure", "bar", 2.5, 5.5, "oil_pressure", "critical"),
            _s("coolant_temp", "Radiator water temperature", "°C", 70, 95, "coolant_temp", "high"),
            _s("pressure", "Fuel pressure", "kPa", 150, 350, "pressure", "medium"),
        ],
    },
]


def _attach_loggers() -> None:
    """Bind each sensor to PLC / SCADA / Data Logger for OT acquisition path."""
    by_id = {d["id"]: d for d in DATA_LOGGERS}
    for eq in EQUIPMENT:
        lid = _logger_for_area(eq["area"], eq.get("line_id", "Line_1"))
        # Vibration-heavy assets also mirror to vibration logger
        eq["data_logger_id"] = lid
        logger = by_id.get(lid, {})
        eq["data_logger"] = {
            "id": lid,
            "name_fa": logger.get("name_fa"),
            "kind": logger.get("kind"),
            "protocol": logger.get("protocol"),
            "host": logger.get("host"),
        }
        for s in eq["sensors"]:
            sensor_logger = lid
            if s["key"].startswith("vibration"):
                sensor_logger = "DL-VIB-01"
            s["logger_id"] = s.get("logger_id") or sensor_logger
            lg = by_id.get(s["logger_id"], {})
            s["logger_kind"] = lg.get("kind", "data_logger")
            s["logger_name_fa"] = lg.get("name_fa", s["logger_id"])
            s["protocol"] = lg.get("protocol", "MQTT")
            s["tag"] = f"{eq['id']}.{s['key'].upper()}"


_attach_loggers()


def _nominal(sensor: dict[str, Any]) -> float:
    lo, hi = float(sensor["min_op"]), float(sensor["max_op"])
    return lo + (hi - lo) * 0.55


def simulate_reading(equipment: dict[str, Any], *, spike: bool = False) -> dict[str, float]:
    """Simulate live sensor values; optionally push one sensor out of range."""
    values: dict[str, float] = {}
    sensors = equipment["sensors"]
    spike_idx = random.randrange(len(sensors)) if spike and sensors else -1
    for i, s in enumerate(sensors):
        lo, hi = float(s["min_op"]), float(s["max_op"])
        mid = _nominal(s)
        span = max(hi - lo, 1e-6)
        if i == spike_idx:
            # 70% high breach, 30% low
            values[s["key"]] = round(hi + span * random.uniform(0.05, 0.25), 2) if random.random() > 0.3 else round(lo - span * random.uniform(0.05, 0.2), 2)
        else:
            values[s["key"]] = round(mid + span * random.gauss(0, 0.08), 2)
            values[s["key"]] = max(lo - span * 0.02, min(hi + span * 0.02, values[s["key"]]))
    return values


def evaluate_equipment(equipment: dict[str, Any], readings: dict[str, float]) -> dict[str, Any]:
    sensors_out = []
    breaches = []
    for s in equipment["sensors"]:
        key = s["key"]
        val = readings.get(key)
        lo, hi = float(s["min_op"]), float(s["max_op"])
        span = max(hi - lo, 1e-9)
        soft = span * 0.1  # yellow band near operational edges
        status = "ok"
        if val is None:
            status = "nodata"
        elif val < lo or val > hi:
            # outside the hard range → red light
            status = "critical"
            breaches.append(
                {
                    "equipment_id": equipment["id"],
                    "equipment_name": equipment["name_fa"],
                    "sensor_key": key,
                    "sensor_name": s["name_fa"],
                    "value": val,
                    "min_op": lo,
                    "max_op": hi,
                    "unit": s["unit"],
                    "severity": "critical" if s.get("criticality") == "critical" else "warning",
                    "message": (
                        f"{equipment['name_fa']}: {s['name_fa']} outside the range "
                        f"({val} {s['unit']}; allowed {lo}–{hi})"
                    ),
                }
            )
        elif val < lo + soft or val > hi - soft:
            status = "warning"
        sensors_out.append({**s, "value": val, "status": status})

    if any(x["status"] == "critical" for x in sensors_out):
        op_status = "critical"
    elif any(x["status"] == "warning" for x in sensors_out):
        op_status = "warning"
    elif any(x["status"] == "nodata" for x in sensors_out):
        op_status = "nodata"
    else:
        op_status = "normal"

    return {
        "id": equipment["id"],
        "name_fa": equipment["name_fa"],
        "name_en": equipment.get("name_en"),
        "equipment_type": equipment["equipment_type"],
        "location": equipment["location"],
        "line_id": equipment["line_id"],
        "area": equipment["area"],
        "data_logger_id": equipment.get("data_logger_id"),
        "data_logger": equipment.get("data_logger"),
        "op_status": op_status,
        "sensors": sensors_out,
        "breach_count": len(breaches),
        "breaches": breaches,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


def build_static_equipment_board(*, with_spikes: bool = True) -> dict[str, Any]:
    units = []
    all_alerts = []
    # Deterministic-ish: spike a few units for demo visibility
    spike_ids = {"BAG-001", "FAN-001", "DRY-001"} if with_spikes else set()
    for eq in EQUIPMENT:
        readings = simulate_reading(eq, spike=eq["id"] in spike_ids)
        # map primary channels for RUL-compatible fields
        evaluated = evaluate_equipment(eq, readings)
        units.append(evaluated)
        all_alerts.extend(evaluated["breaches"])

    normal = sum(1 for u in units if u["op_status"] == "normal")
    warn = sum(1 for u in units if u["op_status"] == "warning")
    crit = sum(1 for u in units if u["op_status"] == "critical")
    sensor_count = sum(len(e["sensors"]) for e in EQUIPMENT)

    return {
        "source": "Production line catalog + PLC/SCADA/Data Logger + operational range assessment",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "equipment": units,
        "data_loggers": DATA_LOGGERS,
        "process_alerts": all_alerts,
        "summary": {
            "equipment_count": len(units),
            "sensor_count": sensor_count,
            "normal_count": normal,
            "warning_count": warn,
            "critical_count": crit,
            "open_process_alerts": len(all_alerts),
            "lines": sorted({e["line_id"] for e in EQUIPMENT}),
            "logger_count": len(DATA_LOGGERS),
            "plc_count": sum(1 for d in DATA_LOGGERS if d["kind"] == "plc"),
            "scada_count": sum(1 for d in DATA_LOGGERS if d["kind"] == "scada"),
            "data_logger_count": sum(1 for d in DATA_LOGGERS if d["kind"] == "data_logger"),
        },
    }


def equipment_by_id() -> dict[str, dict[str, Any]]:
    return {e["id"]: e for e in EQUIPMENT}
