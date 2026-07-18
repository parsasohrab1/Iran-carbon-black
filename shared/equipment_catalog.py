"""Carbon black production-line equipment, sensors, and operational ranges (شکربن)."""

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
        "name_fa": "SCADA مرکزی خط تولید",
        "name_en": "Central Production SCADA",
        "kind": "scada",  # scada | plc | data_logger
        "protocol": "OPC UA / MQTT",
        "vendor": "Wonderware / Ignition-class",
        "host": "10.10.1.10",
        "poll_interval_s": 2,
        "areas": ["واکنش", "جداسازی", "بازیابی حرارت"],
        "status": "online",
    },
    {
        "id": "PLC-S7-01",
        "name_fa": "PLC زیمنس S7 — خط ۱",
        "name_en": "Siemens S7 PLC Line 1",
        "kind": "plc",
        "protocol": "S7 / Modbus TCP",
        "vendor": "Siemens S7-1500",
        "host": "10.10.2.21",
        "poll_interval_s": 1,
        "areas": ["واکنش", "تغذیه", "خنک‌کاری"],
        "status": "online",
    },
    {
        "id": "PLC-S7-02",
        "name_fa": "PLC زیمنس S7 — خط ۲",
        "name_en": "Siemens S7 PLC Line 2",
        "kind": "plc",
        "protocol": "S7 / Modbus TCP",
        "vendor": "Siemens S7-1500",
        "host": "10.10.2.22",
        "poll_interval_s": 1,
        "areas": ["واکنش"],
        "status": "online",
    },
    {
        "id": "PLC-UTIL",
        "name_fa": "PLC یوتیلیتی و کمپرسور",
        "name_en": "Utilities PLC",
        "kind": "plc",
        "protocol": "Modbus TCP",
        "vendor": "Allen-Bradley / CompactLogix",
        "host": "10.10.3.15",
        "poll_interval_s": 2,
        "areas": ["یوتیلیتی"],
        "status": "online",
    },
    {
        "id": "DL-EDGE-01",
        "name_fa": "Data Logger لبه OT (MQTT)",
        "name_en": "OT Edge Data Logger",
        "kind": "data_logger",
        "protocol": "MQTT / REST",
        "vendor": "ICB Edge Gateway",
        "host": "10.10.4.50",
        "poll_interval_s": 5,
        "areas": ["محصول", "انتقال", "بسته‌بندی"],
        "status": "online",
    },
    {
        "id": "DL-VIB-01",
        "name_fa": "Data Logger ارتعاش و وضعیت ماشین",
        "name_en": "Vibration Condition Logger",
        "kind": "data_logger",
        "protocol": "Modbus RTU / MQTT",
        "vendor": "Condition Monitoring Logger",
        "host": "10.10.4.61",
        "poll_interval_s": 3,
        "areas": ["جداسازی", "یوتیلیتی"],
        "status": "online",
    },
]

_LOGGER_BY_AREA: dict[str, str] = {
    "واکنش": "PLC-S7-01",
    "تغذیه": "PLC-S7-01",
    "بازیابی حرارت": "SCADA-01",
    "جداسازی": "SCADA-01",
    "خنک‌کاری": "PLC-S7-01",
    "انتقال": "DL-EDGE-01",
    "محصول": "DL-EDGE-01",
    "یوتیلیتی": "PLC-UTIL",
}


def _logger_for_area(area: str, line_id: str = "Line_1") -> str:
    if area == "واکنش" and line_id == "Line_2":
        return "PLC-S7-02"
    if area in ("جداسازی", "بازیابی حرارت"):
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
        "name_fa": "کوره واکنش خط ۱",
        "name_en": "Reactor Furnace Line 1",
        "equipment_type": "furnace",
        "location": "سالن راکتور",
        "line_id": "Line_1",
        "area": "واکنش",
        "sensors": [
            _s("temperature", "دمای شعله / ناحیه واکنش", "°C", 1450, 1850, "temperature", "critical"),
            _s("pressure", "فشار ورودی هوا", "kPa", 8, 25, "pressure", "high"),
            _s("oil_feed_rate", "دبی خوراک روغن", "kg/h", 1800, 4200, None, "critical"),
            _s("air_flow", "دبی هوای احتراق", "Nm³/h", 12000, 28000, None, "critical"),
            _s("gas_flow", "دبی گاز سوخت", "Nm³/h", 400, 1200, None, "high"),
            _s("current_draw", "جریان مشعل / کنترل", "A", 15, 55, "current_draw", "medium"),
        ],
    },
    {
        "id": "FUR-002",
        "name_fa": "کوره واکنش خط ۲",
        "name_en": "Reactor Furnace Line 2",
        "equipment_type": "furnace",
        "location": "سالن راکتور",
        "line_id": "Line_2",
        "area": "واکنش",
        "sensors": [
            _s("temperature", "دمای شعله / ناحیه واکنش", "°C", 1450, 1850, "temperature", "critical"),
            _s("pressure", "فشار ورودی هوا", "kPa", 8, 25, "pressure", "high"),
            _s("oil_feed_rate", "دبی خوراک روغن", "kg/h", 1600, 4000, None, "critical"),
            _s("air_flow", "دبی هوای احتراق", "Nm³/h", 11000, 26000, None, "critical"),
            _s("gas_flow", "دبی گاز سوخت", "Nm³/h", 350, 1100, None, "high"),
            _s("current_draw", "جریان مشعل / کنترل", "A", 15, 55, "current_draw", "medium"),
        ],
    },
    {
        "id": "AIR-001",
        "name_fa": "دمنده و پیش‌گرم هوای احتراق",
        "name_en": "Combustion Air Blower & Preheater",
        "equipment_type": "blower",
        "location": "یوتیلیتی هوا",
        "line_id": "Line_1",
        "area": "تغذیه",
        "sensors": [
            _s("air_flow", "دبی هوا", "Nm³/h", 10000, 30000, None, "critical"),
            _s("temperature", "دمای هوای پیش‌گرم", "°C", 450, 750, "temperature", "high"),
            _s("pressure", "فشار دیسشارژ", "kPa", 10, 35, "pressure", "high"),
            _s("vibration_x", "ارتعاش یاتاقان", "mm/s", 0.5, 7.5, "vibration_x", "high"),
            _s("current_draw", "جریان موتور", "A", 80, 220, "current_draw", "medium"),
        ],
    },
    {
        "id": "OIL-001",
        "name_fa": "پمپ و پیش‌گرم‌کن خوراک روغن (CBFS)",
        "name_en": "Feedstock Oil Pump & Preheater",
        "equipment_type": "pump",
        "location": "ایستگاه خوراک",
        "line_id": "Line_1",
        "area": "تغذیه",
        "sensors": [
            _s("oil_feed_rate", "دبی روغن", "kg/h", 1500, 4500, None, "critical"),
            _s("temperature", "دمای روغن پیش‌گرم", "°C", 180, 280, "temperature", "high"),
            _s("pressure", "فشار پمپ", "kPa", 200, 800, "pressure", "high"),
            _s("oil_pressure", "فشار روغن روانکار", "bar", 1.5, 4.5, "oil_pressure", "medium"),
            _s("current_draw", "جریان پمپ", "A", 20, 90, "current_draw", "medium"),
        ],
    },
    {
        "id": "GAS-001",
        "name_fa": "ایستگاه گاز طبیعی سوخت",
        "name_en": "Natural Gas Fuel Station",
        "equipment_type": "gas_station",
        "location": "یوتیلیتی سوخت",
        "line_id": "UTIL",
        "area": "تغذیه",
        "sensors": [
            _s("gas_flow", "دبی گاز", "Nm³/h", 300, 1500, None, "critical"),
            _s("pressure", "فشار خط گاز", "kPa", 150, 400, "pressure", "critical"),
            _s("temperature", "دمای گاز", "°C", 5, 45, "temperature", "medium"),
        ],
    },
    {
        "id": "QNZ-001",
        "name_fa": "سیستم کوئنچ راکتور",
        "name_en": "Reactor Quench System",
        "equipment_type": "quench",
        "location": "سالن راکتور",
        "line_id": "Line_1",
        "area": "واکنش",
        "sensors": [
            _s("temperature", "دمای دود پس از کوئنچ", "°C", 700, 1100, "temperature", "critical"),
            _s("quench_water_flow", "دبی آب کوئنچ", "m³/h", 8, 35, None, "critical"),
            _s("pressure", "فشار نازل کوئنچ", "kPa", 300, 900, "pressure", "high"),
            _s("coolant_temp", "دمای آب کوئنچ", "°C", 25, 55, "coolant_temp", "medium"),
        ],
    },
    {
        "id": "PMP-001",
        "name_fa": "پمپ آب کوئنچ و خنک‌کاری",
        "name_en": "Quench / Cooling Water Pump",
        "equipment_type": "pump",
        "location": "ایستگاه پمپ",
        "line_id": "UTIL",
        "area": "یوتیلیتی",
        "sensors": [
            _s("quench_water_flow", "دبی آب", "m³/h", 10, 50, None, "high"),
            _s("pressure", "فشار دیسشارژ", "kPa", 250, 700, "pressure", "high"),
            _s("vibration_x", "ارتعاش", "mm/s", 0.4, 6.5, "vibration_x", "medium"),
            _s("current_draw", "جریان موتور", "A", 25, 110, "current_draw", "medium"),
            _s("coolant_temp", "دمای آب", "°C", 20, 50, "coolant_temp", "medium"),
        ],
    },
    {
        "id": "APH-001",
        "name_fa": "مبدل پیش‌گرم هوا",
        "name_en": "Air Preheater Exchanger",
        "equipment_type": "heat_exchanger",
        "location": "مسیر دود / هوا",
        "line_id": "Line_1",
        "area": "بازیابی حرارت",
        "sensors": [
            _s("temperature", "دمای هوای خروجی", "°C", 400, 780, "temperature", "high"),
            _s("flue_temp", "دمای دود ورودی", "°C", 600, 1000, None, "high"),
            _s("pressure", "افت فشار سمت هوا", "kPa", 1, 12, "pressure", "medium"),
        ],
    },
    {
        "id": "OPH-001",
        "name_fa": "مبدل پیش‌گرم روغن",
        "name_en": "Oil Preheater Exchanger",
        "equipment_type": "heat_exchanger",
        "location": "مسیر دود / روغن",
        "line_id": "Line_1",
        "area": "بازیابی حرارت",
        "sensors": [
            _s("temperature", "دمای روغن خروجی", "°C", 160, 290, "temperature", "high"),
            _s("flue_temp", "دمای دود", "°C", 350, 700, None, "medium"),
            _s("pressure", "افت فشار روغن", "kPa", 20, 120, "pressure", "medium"),
        ],
    },
    {
        "id": "CYC-001",
        "name_fa": "سیکلون جداسازی اولیه",
        "name_en": "Primary Cyclone",
        "equipment_type": "cyclone",
        "location": "جداسازی",
        "line_id": "Line_1",
        "area": "جداسازی",
        "sensors": [
            _s("pressure", "افت فشار سیکلون", "kPa", 0.5, 8, "pressure", "high"),
            _s("temperature", "دمای گاز ورودی", "°C", 250, 550, "temperature", "medium"),
            _s("dp_inlet", "فشار ورودی", "kPa", -5, 15, None, "medium"),
        ],
    },
    {
        "id": "BAG-001",
        "name_fa": "فیلتر کیسه‌ای (Bag Filter)",
        "name_en": "Baghouse Filter",
        "equipment_type": "bag_filter",
        "location": "جداسازی",
        "line_id": "Line_1",
        "area": "جداسازی",
        "sensors": [
            _s("pressure", "افت فشار فیلتر", "kPa", 0.8, 6, "pressure", "critical"),
            _s("temperature", "دمای گاز", "°C", 180, 280, "temperature", "high"),
            _s("dust_outlet", "غبار خروجی", "mg/Nm³", 5, 50, None, "high"),
            _s("pulse_pressure", "فشار پالس تمیزکاری", "kPa", 400, 700, None, "medium"),
        ],
    },
    {
        "id": "FAN-001",
        "name_fa": "فن مکش دودکش (ID Fan)",
        "name_en": "Induced Draft Fan",
        "equipment_type": "fan",
        "location": "دودکش",
        "line_id": "Line_1",
        "area": "جداسازی",
        "sensors": [
            _s("vibration_x", "ارتعاش افقی", "mm/s", 0.5, 8, "vibration_x", "critical"),
            _s("vibration_y", "ارتعاش عمودی", "mm/s", 0.5, 8, "vibration_y", "high"),
            _s("current_draw", "جریان موتور", "A", 90, 280, "current_draw", "high"),
            _s("pressure", "فشار مکش", "kPa", -15, -2, "pressure", "high"),
            _s("temperature", "دمای یاتاقان", "°C", 35, 85, "temperature", "medium"),
        ],
    },
    {
        "id": "CLR-001",
        "name_fa": "کولر عمودی ۳۸ متری",
        "name_en": "Vertical Cooler 38m",
        "equipment_type": "cooler",
        "location": "برج خنک‌کننده",
        "line_id": "Line_1",
        "area": "خنک‌کاری",
        "sensors": [
            _s("temperature", "دمای خروجی گاز", "°C", 180, 280, "temperature", "high"),
            _s("coolant_temp", "دمای آب خنک‌کننده", "°C", 25, 45, "coolant_temp", "high"),
            _s("pressure", "افت فشار کولر", "kPa", 0.5, 5, "pressure", "medium"),
            _s("vibration_x", "ارتعاش سازه", "mm/s", 0.3, 5, "vibration_x", "medium"),
        ],
    },
    {
        "id": "PNE-001",
        "name_fa": "سیستم انتقال پنوماتیک دوده",
        "name_en": "Pneumatic Conveying",
        "equipment_type": "conveyor",
        "location": "مسیر انتقال",
        "line_id": "Line_1",
        "area": "انتقال",
        "sensors": [
            _s("pressure", "فشار خط انتقال", "kPa", 20, 80, "pressure", "high"),
            _s("air_flow", "دبی هوای انتقال", "Nm³/h", 500, 2500, None, "high"),
            _s("current_draw", "جریان بلوور", "A", 30, 120, "current_draw", "medium"),
            _s("temperature", "دمای خط", "°C", 40, 120, "temperature", "medium"),
        ],
    },
    {
        "id": "GRN-001",
        "name_fa": "گرانولاتور مرطوب",
        "name_en": "Wet Granulator",
        "equipment_type": "granulator",
        "location": "واحد گرانول",
        "line_id": "Line_1",
        "area": "محصول",
        "sensors": [
            _s("current_draw", "جریان موتور", "A", 40, 160, "current_draw", "high"),
            _s("vibration_x", "ارتعاش", "mm/s", 0.5, 9, "vibration_x", "high"),
            _s("binder_flow", "دبی بایندر", "L/h", 50, 400, None, "high"),
            _s("temperature", "دمای محفظه", "°C", 30, 70, "temperature", "medium"),
        ],
    },
    {
        "id": "DRY-001",
        "name_fa": "خشک‌کن دوار محصول",
        "name_en": "Rotary Dryer",
        "equipment_type": "dryer",
        "location": "واحد خشک‌کن",
        "line_id": "Line_1",
        "area": "محصول",
        "sensors": [
            _s("temperature", "دمای گاز خشک‌کن", "°C", 180, 320, "temperature", "critical"),
            _s("moisture", "رطوبت محصول خروجی", "%", 0.2, 1.2, None, "critical"),
            _s("current_draw", "جریان درایو", "A", 50, 180, "current_draw", "medium"),
            _s("pressure", "فشار محفظه", "kPa", -2, 5, "pressure", "medium"),
        ],
    },
    {
        "id": "SCR-001",
        "name_fa": "سرند و درجه‌بندی محصول",
        "name_en": "Product Screen",
        "equipment_type": "screen",
        "location": "واحد بسته‌بندی",
        "line_id": "Line_1",
        "area": "محصول",
        "sensors": [
            _s("vibration_x", "ارتعاش سرند", "mm/s", 2, 18, "vibration_x", "medium"),
            _s("current_draw", "جریان موتور", "A", 8, 40, "current_draw", "medium"),
            _s("throughput", "نرخ عبور", "t/h", 2, 12, None, "high"),
        ],
    },
    {
        "id": "PKG-001",
        "name_fa": "خط بسته‌بندی و توزین",
        "name_en": "Packaging & Weighing",
        "equipment_type": "packaging",
        "location": "سالن انبار محصول",
        "line_id": "Line_1",
        "area": "محصول",
        "sensors": [
            _s("throughput", "نرخ بسته‌بندی", "bag/h", 40, 180, None, "high"),
            _s("current_draw", "جریان خط", "A", 10, 55, "current_draw", "medium"),
            _s("weight_error", "خطای توزین", "%", -1.5, 1.5, None, "critical"),
        ],
    },
    {
        "id": "CMP-001",
        "name_fa": "کمپرسور هوای ابزار دقیق A",
        "name_en": "Instrument Air Compressor A",
        "equipment_type": "compressor",
        "location": "یوتیلیتی",
        "line_id": "UTIL",
        "area": "یوتیلیتی",
        "sensors": [
            _s("pressure", "فشار هوای فشرده", "kPa", 550, 850, "pressure", "critical"),
            _s("temperature", "دمای دیسشارژ", "°C", 60, 120, "temperature", "high"),
            _s("vibration_x", "ارتعاش", "mm/s", 0.4, 7, "vibration_x", "high"),
            _s("oil_pressure", "فشار روغن", "bar", 2, 5, "oil_pressure", "high"),
            _s("current_draw", "جریان موتور", "A", 60, 200, "current_draw", "medium"),
            _s("coolant_temp", "دمای خنک‌کننده", "°C", 25, 55, "coolant_temp", "medium"),
        ],
    },
    {
        "id": "GEN-001",
        "name_fa": "ژنراتور اضطراری واحد ۱",
        "name_en": "Emergency Generator Unit 1",
        "equipment_type": "generator",
        "location": "نیروگاه داخلی",
        "line_id": "UTIL",
        "area": "یوتیلیتی",
        "sensors": [
            _s("current_draw", "جریان خروجی", "A", 50, 400, "current_draw", "critical"),
            _s("temperature", "دمای ژنراتور", "°C", 50, 95, "temperature", "high"),
            _s("vibration_x", "ارتعاش", "mm/s", 0.5, 8, "vibration_x", "high"),
            _s("oil_pressure", "فشار روغن موتور", "bar", 2.5, 5.5, "oil_pressure", "critical"),
            _s("coolant_temp", "دمای آب رادیاتور", "°C", 70, 95, "coolant_temp", "high"),
            _s("pressure", "فشار سوخت", "kPa", 150, 350, "pressure", "medium"),
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
            # خارج از محدوده سخت → چراغ قرمز
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
                        f"{equipment['name_fa']}: {s['name_fa']} خارج از محدوده "
                        f"({val} {s['unit']}; مجاز {lo}–{hi})"
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
        "source": "کاتالوگ خط تولید + PLC/SCADA/Data Logger + ارزیابی رنج عملیاتی",
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
