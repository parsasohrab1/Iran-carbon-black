/** Offline/static production-line equipment board for carbon black plant. */

import { buildLocalRulComponentsBoard } from "./rul_components";

export type DataLogger = {
  id: string;
  name_fa: string;
  name_en?: string;
  kind: "scada" | "plc" | "data_logger" | string;
  protocol: string;
  vendor?: string;
  host?: string;
  poll_interval_s?: number;
  areas?: string[];
  status?: string;
};

export type EquipmentSensor = {
  key: string;
  name_fa: string;
  unit: string;
  min_op: number;
  max_op: number;
  channel?: string | null;
  criticality?: string;
  value?: number | null;
  status?: "ok" | "warning" | "critical" | "nodata" | string;
  logger_id?: string;
  logger_kind?: string;
  logger_name_fa?: string;
  protocol?: string;
  tag?: string;
};

export type EquipmentUnit = {
  id: string;
  name_fa: string;
  name_en?: string;
  equipment_type: string;
  location: string;
  line_id: string;
  area: string;
  op_status: "normal" | "warning" | "critical" | "nodata" | string;
  sensors: EquipmentSensor[];
  breach_count: number;
  as_of?: string;
  data_logger_id?: string;
  data_logger?: {
    id?: string;
    name_fa?: string;
    kind?: string;
    protocol?: string;
    host?: string;
  };
};

export type ProcessRecommendation = {
  action_id: string;
  action_fa: string;
  mode: "auto_eligible" | "manual_only" | string;
  auto_eligible?: boolean;
  rank?: number;
  confidence?: number;
  expected_effect_fa?: string;
  risk_fa?: string;
  setpoint_hint?: Record<string, unknown>;
};

export type ProcessAlert = {
  id?: number | string;
  equipment_id: string;
  equipment_name?: string;
  sensor_key: string;
  sensor_name?: string;
  severity: string;
  measured_value?: number;
  value?: number;
  min_op?: number;
  max_op?: number;
  unit?: string;
  message: string;
  created_at?: string;
  breach_direction?: string;
  overshoot_pct?: number;
  recommendations?: ProcessRecommendation[];
  primary_recommendation?: ProcessRecommendation | null;
};

export type ProcessActionLog = {
  id: string;
  applied_at: string;
  mode: string;
  operator: string;
  equipment_id?: string;
  equipment_name?: string;
  sensor_key?: string;
  sensor_name?: string;
  action_id?: string;
  action_fa?: string;
  status?: string;
};

export type ComponentRul = {
  component_id: string;
  component_type: string;
  component_type_fa: string;
  name_fa: string;
  equipment_id: string;
  equipment_name?: string;
  line_id?: string;
  rul_days: number;
  failure_probability: number;
  health_score?: number;
  severity: string;
  alert?: boolean;
  failure_mode_fa?: string;
  recommended_action_fa?: string;
  message?: string;
  alert_type?: string;
};

export type RulComponentsBoard = {
  source?: string;
  alert_threshold_days?: number;
  components: ComponentRul[];
  alerts: ComponentRul[];
  summary: {
    component_count: number;
    alert_count: number;
    critical_count: number;
    warning_count: number;
    by_type: Record<string, number>;
    min_rul_days?: number | null;
    types_fa?: string[];
  };
};

export type EquipmentBoard = {
  source?: string;
  generated_at?: string;
  equipment: EquipmentUnit[];
  data_loggers?: DataLogger[];
  process_alerts: ProcessAlert[];
  autopilot?: {
    enabled?: boolean;
    autopilot?: boolean;
    applied?: ProcessActionLog[];
    skipped?: number;
    message_fa?: string;
  };
  recent_actions?: ProcessActionLog[];
  rul_components?: RulComponentsBoard;
  summary: {
    equipment_count: number;
    sensor_count: number;
    normal_count: number;
    warning_count: number;
    critical_count: number;
    open_process_alerts: number;
    lines: string[];
    logger_count?: number;
    plc_count?: number;
    scada_count?: number;
    data_logger_count?: number;
    auto_applied_count?: number;
  };
};

type Spec = {
  id: string;
  name_fa: string;
  type: string;
  location: string;
  line_id: string;
  area: string;
  sensors: Array<{ key: string; name_fa: string; unit: string; min: number; max: number; crit?: string }>;
};

const SPECS: Spec[] = [
  {
    id: "FUR-001",
    name_fa: "کوره واکنش خط ۱",
    type: "furnace",
    location: "سالن راکتور",
    line_id: "Line_1",
    area: "واکنش",
    sensors: [
      { key: "temperature", name_fa: "دمای واکنش", unit: "°C", min: 1450, max: 1850, crit: "critical" },
      { key: "pressure", name_fa: "فشار هوا", unit: "kPa", min: 8, max: 25 },
      { key: "oil_feed_rate", name_fa: "دبی روغن", unit: "kg/h", min: 1800, max: 4200, crit: "critical" },
      { key: "air_flow", name_fa: "دبی هوا", unit: "Nm³/h", min: 12000, max: 28000, crit: "critical" },
    ],
  },
  {
    id: "FUR-002",
    name_fa: "کوره واکنش خط ۲",
    type: "furnace",
    location: "سالن راکتور",
    line_id: "Line_2",
    area: "واکنش",
    sensors: [
      { key: "temperature", name_fa: "دمای واکنش", unit: "°C", min: 1450, max: 1850, crit: "critical" },
      { key: "oil_feed_rate", name_fa: "دبی روغن", unit: "kg/h", min: 1600, max: 4000, crit: "critical" },
      { key: "air_flow", name_fa: "دبی هوا", unit: "Nm³/h", min: 11000, max: 26000, crit: "critical" },
    ],
  },
  {
    id: "AIR-001",
    name_fa: "دمنده و پیش‌گرم هوا",
    type: "blower",
    location: "یوتیلیتی هوا",
    line_id: "Line_1",
    area: "تغذیه",
    sensors: [
      { key: "air_flow", name_fa: "دبی هوا", unit: "Nm³/h", min: 10000, max: 30000, crit: "critical" },
      { key: "temperature", name_fa: "دمای پیش‌گرم", unit: "°C", min: 450, max: 750 },
      { key: "vibration_x", name_fa: "ارتعاش", unit: "mm/s", min: 0.5, max: 7.5 },
    ],
  },
  {
    id: "OIL-001",
    name_fa: "پمپ و پیش‌گرم خوراک روغن",
    type: "pump",
    location: "ایستگاه خوراک",
    line_id: "Line_1",
    area: "تغذیه",
    sensors: [
      { key: "oil_feed_rate", name_fa: "دبی روغن", unit: "kg/h", min: 1500, max: 4500, crit: "critical" },
      { key: "temperature", name_fa: "دمای روغن", unit: "°C", min: 180, max: 280 },
      { key: "pressure", name_fa: "فشار پمپ", unit: "kPa", min: 200, max: 800 },
    ],
  },
  {
    id: "GAS-001",
    name_fa: "ایستگاه گاز طبیعی سوخت",
    type: "gas_station",
    location: "یوتیلیتی سوخت",
    line_id: "UTIL",
    area: "تغذیه",
    sensors: [
      { key: "gas_flow", name_fa: "دبی گاز", unit: "Nm³/h", min: 300, max: 1500, crit: "critical" },
      { key: "pressure", name_fa: "فشار گاز", unit: "kPa", min: 150, max: 400, crit: "critical" },
    ],
  },
  {
    id: "QNZ-001",
    name_fa: "سیستم کوئنچ راکتور",
    type: "quench",
    location: "سالن راکتور",
    line_id: "Line_1",
    area: "واکنش",
    sensors: [
      { key: "temperature", name_fa: "دمای پس از کوئنچ", unit: "°C", min: 700, max: 1100, crit: "critical" },
      { key: "quench_water_flow", name_fa: "دبی آب کوئنچ", unit: "m³/h", min: 8, max: 35, crit: "critical" },
    ],
  },
  {
    id: "PMP-001",
    name_fa: "پمپ آب کوئنچ",
    type: "pump",
    location: "ایستگاه پمپ",
    line_id: "UTIL",
    area: "یوتیلیتی",
    sensors: [
      { key: "pressure", name_fa: "فشار دیسشارژ", unit: "kPa", min: 250, max: 700 },
      { key: "current_draw", name_fa: "جریان موتور", unit: "A", min: 25, max: 110 },
    ],
  },
  {
    id: "APH-001",
    name_fa: "مبدل پیش‌گرم هوا",
    type: "heat_exchanger",
    location: "مسیر دود / هوا",
    line_id: "Line_1",
    area: "بازیابی حرارت",
    sensors: [
      { key: "temperature", name_fa: "دمای هوای خروجی", unit: "°C", min: 400, max: 780 },
      { key: "pressure", name_fa: "افت فشار", unit: "kPa", min: 1, max: 12 },
    ],
  },
  {
    id: "OPH-001",
    name_fa: "مبدل پیش‌گرم روغن",
    type: "heat_exchanger",
    location: "مسیر دود / روغن",
    line_id: "Line_1",
    area: "بازیابی حرارت",
    sensors: [
      { key: "temperature", name_fa: "دمای روغن خروجی", unit: "°C", min: 160, max: 290 },
    ],
  },
  {
    id: "CYC-001",
    name_fa: "سیکلون جداسازی",
    type: "cyclone",
    location: "جداسازی",
    line_id: "Line_1",
    area: "جداسازی",
    sensors: [
      { key: "pressure", name_fa: "افت فشار", unit: "kPa", min: 0.5, max: 8 },
      { key: "temperature", name_fa: "دمای گاز", unit: "°C", min: 250, max: 550 },
    ],
  },
  {
    id: "BAG-001",
    name_fa: "فیلتر کیسه‌ای",
    type: "bag_filter",
    location: "جداسازی",
    line_id: "Line_1",
    area: "جداسازی",
    sensors: [
      { key: "pressure", name_fa: "افت فشار فیلتر", unit: "kPa", min: 0.8, max: 6, crit: "critical" },
      { key: "dust_outlet", name_fa: "غبار خروجی", unit: "mg/Nm³", min: 5, max: 50 },
    ],
  },
  {
    id: "FAN-001",
    name_fa: "فن مکش دودکش",
    type: "fan",
    location: "دودکش",
    line_id: "Line_1",
    area: "جداسازی",
    sensors: [
      { key: "vibration_x", name_fa: "ارتعاش", unit: "mm/s", min: 0.5, max: 8, crit: "critical" },
      { key: "current_draw", name_fa: "جریان موتور", unit: "A", min: 90, max: 280 },
    ],
  },
  {
    id: "CLR-001",
    name_fa: "کولر عمودی ۳۸ متری",
    type: "cooler",
    location: "برج خنک‌کننده",
    line_id: "Line_1",
    area: "خنک‌کاری",
    sensors: [
      { key: "temperature", name_fa: "دمای خروجی", unit: "°C", min: 180, max: 280 },
      { key: "coolant_temp", name_fa: "دمای آب", unit: "°C", min: 25, max: 45 },
    ],
  },
  {
    id: "PNE-001",
    name_fa: "انتقال پنوماتیک دوده",
    type: "conveyor",
    location: "مسیر انتقال",
    line_id: "Line_1",
    area: "انتقال",
    sensors: [
      { key: "pressure", name_fa: "فشار خط", unit: "kPa", min: 20, max: 80 },
      { key: "air_flow", name_fa: "دبی هوا", unit: "Nm³/h", min: 500, max: 2500 },
    ],
  },
  {
    id: "GRN-001",
    name_fa: "گرانولاتور مرطوب",
    type: "granulator",
    location: "واحد گرانول",
    line_id: "Line_1",
    area: "محصول",
    sensors: [
      { key: "current_draw", name_fa: "جریان موتور", unit: "A", min: 40, max: 160 },
      { key: "vibration_x", name_fa: "ارتعاش", unit: "mm/s", min: 0.5, max: 9 },
    ],
  },
  {
    id: "DRY-001",
    name_fa: "خشک‌کن دوار",
    type: "dryer",
    location: "واحد خشک‌کن",
    line_id: "Line_1",
    area: "محصول",
    sensors: [
      { key: "temperature", name_fa: "دمای گاز", unit: "°C", min: 180, max: 320, crit: "critical" },
      { key: "moisture", name_fa: "رطوبت محصول", unit: "%", min: 0.2, max: 1.2, crit: "critical" },
    ],
  },
  {
    id: "SCR-001",
    name_fa: "سرند محصول",
    type: "screen",
    location: "واحد بسته‌بندی",
    line_id: "Line_1",
    area: "محصول",
    sensors: [
      { key: "vibration_x", name_fa: "ارتعاش سرند", unit: "mm/s", min: 2, max: 18 },
      { key: "throughput", name_fa: "نرخ عبور", unit: "t/h", min: 2, max: 12 },
    ],
  },
  {
    id: "PKG-001",
    name_fa: "بسته‌بندی و توزین",
    type: "packaging",
    location: "سالن انبار",
    line_id: "Line_1",
    area: "محصول",
    sensors: [
      { key: "throughput", name_fa: "نرخ بسته", unit: "bag/h", min: 40, max: 180 },
      { key: "weight_error", name_fa: "خطای توزین", unit: "%", min: -1.5, max: 1.5, crit: "critical" },
    ],
  },
  {
    id: "CMP-001",
    name_fa: "کمپرسور هوای ابزار دقیق",
    type: "compressor",
    location: "یوتیلیتی",
    line_id: "UTIL",
    area: "یوتیلیتی",
    sensors: [
      { key: "pressure", name_fa: "فشار هوا", unit: "kPa", min: 550, max: 850, crit: "critical" },
      { key: "oil_pressure", name_fa: "فشار روغن", unit: "bar", min: 2, max: 5 },
    ],
  },
  {
    id: "GEN-001",
    name_fa: "ژنراتور اضطراری",
    type: "generator",
    location: "نیروگاه داخلی",
    line_id: "UTIL",
    area: "یوتیلیتی",
    sensors: [
      { key: "current_draw", name_fa: "جریان خروجی", unit: "A", min: 50, max: 400, crit: "critical" },
      { key: "oil_pressure", name_fa: "فشار روغن", unit: "bar", min: 2.5, max: 5.5, crit: "critical" },
      { key: "coolant_temp", name_fa: "دمای آب", unit: "°C", min: 70, max: 95 },
    ],
  },
];

const LOCAL_LOGGERS: DataLogger[] = [
  {
    id: "SCADA-01",
    name_fa: "SCADA مرکزی خط تولید",
    kind: "scada",
    protocol: "OPC UA / MQTT",
    vendor: "Wonderware / Ignition-class",
    host: "10.10.1.10",
    poll_interval_s: 2,
    areas: ["واکنش", "جداسازی", "بازیابی حرارت"],
    status: "online",
  },
  {
    id: "PLC-S7-01",
    name_fa: "PLC زیمنس S7 — خط ۱",
    kind: "plc",
    protocol: "S7 / Modbus TCP",
    vendor: "Siemens S7-1500",
    host: "10.10.2.21",
    poll_interval_s: 1,
    areas: ["واکنش", "تغذیه", "خنک‌کاری"],
    status: "online",
  },
  {
    id: "PLC-S7-02",
    name_fa: "PLC زیمنس S7 — خط ۲",
    kind: "plc",
    protocol: "S7 / Modbus TCP",
    host: "10.10.2.22",
    status: "online",
  },
  {
    id: "PLC-UTIL",
    name_fa: "PLC یوتیلیتی و کمپرسور",
    kind: "plc",
    protocol: "Modbus TCP",
    host: "10.10.3.15",
    status: "online",
  },
  {
    id: "DL-EDGE-01",
    name_fa: "Data Logger لبه OT (MQTT)",
    kind: "data_logger",
    protocol: "MQTT / REST",
    host: "10.10.4.50",
    status: "online",
  },
  {
    id: "DL-VIB-01",
    name_fa: "Data Logger ارتعاش و وضعیت ماشین",
    kind: "data_logger",
    protocol: "Modbus RTU / MQTT",
    host: "10.10.4.61",
    status: "online",
  },
];

function loggerForArea(area: string, lineId: string): DataLogger {
  if (area === "واکنش" && lineId === "Line_2") {
    return LOCAL_LOGGERS.find((d) => d.id === "PLC-S7-02") ?? LOCAL_LOGGERS[1];
  }
  if (area === "جداسازی" || area === "بازیابی حرارت") {
    return LOCAL_LOGGERS.find((d) => d.id === "SCADA-01") ?? LOCAL_LOGGERS[0];
  }
  if (area === "یوتیلیتی") return LOCAL_LOGGERS.find((d) => d.id === "PLC-UTIL") ?? LOCAL_LOGGERS[3];
  if (area === "محصول" || area === "انتقال") {
    return LOCAL_LOGGERS.find((d) => d.id === "DL-EDGE-01") ?? LOCAL_LOGGERS[4];
  }
  return LOCAL_LOGGERS.find((d) => d.id === "PLC-S7-01") ?? LOCAL_LOGGERS[1];
}

function evalUnit(spec: Spec, spike = false): EquipmentUnit {
  const primary = loggerForArea(spec.area, spec.line_id);
  const sensors: EquipmentSensor[] = spec.sensors.map((s, i) => {
    const mid = s.min + (s.max - s.min) * 0.55;
    let value = mid * (0.96 + (i % 5) * 0.01);
    if (spike && i === 0) value = s.max * 1.12;
    // Near-edge samples for yellow lamps on some sensors
    if (!spike && i === 1) value = s.min + (s.max - s.min) * 0.04;
    if (!spike && i === 2) value = s.max - (s.max - s.min) * 0.05;
    const status = classifySensorTraffic(value, s.min, s.max, s.crit ?? "high");
    const logger =
      s.key.startsWith("vibration") ? LOCAL_LOGGERS.find((d) => d.id === "DL-VIB-01") ?? primary : primary;
    return {
      key: s.key,
      name_fa: s.name_fa,
      unit: s.unit,
      min_op: s.min,
      max_op: s.max,
      criticality: s.crit ?? "high",
      value: Number(value.toFixed(2)),
      status,
      logger_id: logger.id,
      logger_kind: logger.kind,
      logger_name_fa: logger.name_fa,
      protocol: logger.protocol,
      tag: `${spec.id}.${s.key.toUpperCase()}`,
    };
  });
  const op_status = sensors.some((x) => x.status === "critical")
    ? "critical"
    : sensors.some((x) => x.status === "warning")
      ? "warning"
      : "normal";
  return {
    id: spec.id,
    name_fa: spec.name_fa,
    equipment_type: spec.type,
    location: spec.location,
    line_id: spec.line_id,
    area: spec.area,
    op_status,
    sensors,
    breach_count: sensors.filter((x) => x.value != null && (x.value < x.min_op || x.value > x.max_op))
      .length,
    as_of: new Date().toISOString(),
    data_logger_id: primary.id,
    data_logger: {
      id: primary.id,
      name_fa: primary.name_fa,
      kind: primary.kind,
      protocol: primary.protocol,
      host: primary.host,
    },
  };
}

export function buildLocalAdvice(alert: ProcessAlert): ProcessAlert {
  const val = Number(alert.measured_value ?? alert.value ?? 0);
  const high = val > Number(alert.max_op);
  const primary: ProcessRecommendation = {
    action_id: high ? "nudge_setpoint_down" : "nudge_setpoint_up",
    action_fa: high
      ? "کاهش تدریجی ست‌پوینت مرتبط تا بازگشت به رنج"
      : "افزایش تدریجی ست‌پوینت مرتبط تا حداقل عملیاتی",
    mode: alert.severity === "critical" ? "auto_eligible" : "manual_only",
    auto_eligible: alert.severity === "critical",
    rank: 1,
    confidence: 0.88,
    expected_effect_fa: "بازگشت مقدار به باند عملیاتی",
    risk_fa: "اثر جانبی کوتاه‌مدت روی کیفیت",
  };
  const manual: ProcessRecommendation = {
    action_id: "operator_verify",
    action_fa: "تأیید میدانی توسط اپراتور و ثبت در لاگ شیفت",
    mode: "manual_only",
    auto_eligible: false,
    rank: 2,
    confidence: 0.8,
    expected_effect_fa: "اعتبارسنجی هشدار",
    risk_fa: "تأخیر واکنش",
  };
  return {
    ...alert,
    breach_direction: high ? "high" : "low",
    overshoot_pct: Math.round(
      (Math.abs(val - (high ? Number(alert.max_op) : Number(alert.min_op))) /
        Math.max(Number(alert.max_op) - Number(alert.min_op), 1e-9)) *
        1000,
    ) / 10,
    recommendations: [primary, manual],
    primary_recommendation: primary,
  };
}

export function buildLocalEquipmentBoard(): EquipmentBoard {
  const spikeIds = new Set(["BAG-001", "FAN-001", "DRY-001"]);
  const equipment = SPECS.map((s) => evalUnit(s, spikeIds.has(s.id)));
  const process_alerts: ProcessAlert[] = [];
  for (const u of equipment) {
    for (const s of u.sensors) {
      if (s.status === "ok" || s.status === "nodata" || s.value == null) continue;
      if (!(s.value < s.min_op || s.value > s.max_op)) continue;
      process_alerts.push(
        buildLocalAdvice({
          equipment_id: u.id,
          equipment_name: u.name_fa,
          sensor_key: s.key,
          sensor_name: s.name_fa,
          severity: String(s.status),
          measured_value: s.value,
          min_op: s.min_op,
          max_op: s.max_op,
          unit: s.unit,
          message: `${u.name_fa}: ${s.name_fa} خارج از محدوده (${s.value} ${s.unit}; مجاز ${s.min_op}–${s.max_op})`,
        }),
      );
    }
  }
  const rul_components = buildLocalRulComponentsBoard();
  return {
    source: "کاتالوگ آفلاین خط تولید + PLC/SCADA/Data Logger",
    equipment,
    data_loggers: LOCAL_LOGGERS,
    process_alerts,
    autopilot: { enabled: false, message_fa: "آفلاین — Auto Pilot در سرویس انرژی فعال می‌شود" },
    recent_actions: [],
    rul_components,
    summary: {
      equipment_count: equipment.length,
      sensor_count: equipment.reduce((n, e) => n + e.sensors.length, 0),
      normal_count: equipment.filter((e) => e.op_status === "normal").length,
      warning_count: equipment.filter((e) => e.op_status === "warning").length,
      critical_count: equipment.filter((e) => e.op_status === "critical").length,
      open_process_alerts: process_alerts.length,
      lines: [...new Set(equipment.map((e) => e.line_id))],
      logger_count: LOCAL_LOGGERS.length,
      plc_count: LOCAL_LOGGERS.filter((d) => d.kind === "plc").length,
      scada_count: LOCAL_LOGGERS.filter((d) => d.kind === "scada").length,
      data_logger_count: LOCAL_LOGGERS.filter((d) => d.kind === "data_logger").length,
    },
  };
}

export function opStatusLabel(status: string): string {
  if (status === "normal" || status === "ok") return "در محدوده";
  if (status === "warning") return "هشدار";
  if (status === "critical") return "بحرانی";
  if (status === "nodata") return "بدون داده";
  return status;
}

/** Traffic-light status: green (ok) / yellow (near limit) / red (out of range). */
export function classifySensorTraffic(
  value: number | null | undefined,
  minOp: number,
  maxOp: number,
  _criticality = "high",
): "ok" | "warning" | "critical" | "nodata" {
  if (value == null || Number.isNaN(value)) return "nodata";
  const span = Math.max(maxOp - minOp, 1e-9);
  const soft = span * 0.1;
  if (value < minOp || value > maxOp) {
    return "critical";
  }
  if (value < minOp + soft || value > maxOp - soft) return "warning";
  return "ok";
}

export function sensorTrafficStatus(s: EquipmentSensor): "ok" | "warning" | "critical" | "nodata" {
  return classifySensorTraffic(s.value, s.min_op, s.max_op, s.criticality ?? "high");
}

/** Marker position 0–100 on operational range bar (clamped with small overflow). */
export function sensorRangePct(s: EquipmentSensor): number {
  if (s.value == null) return 50;
  const span = Math.max(s.max_op - s.min_op, 1e-9);
  const raw = ((s.value - s.min_op) / span) * 100;
  return Math.max(-6, Math.min(106, raw));
}

export type FlatSensorRow = EquipmentSensor & {
  equipment_id: string;
  equipment_name: string;
  line_id: string;
  area: string;
};

export function flattenEquipmentSensors(board: EquipmentBoard): FlatSensorRow[] {
  const rows: FlatSensorRow[] = [];
  for (const eq of board.equipment) {
    for (const s of eq.sensors) {
      rows.push({
        ...s,
        equipment_id: eq.id,
        equipment_name: eq.name_fa,
        line_id: eq.line_id,
        area: eq.area,
        status: sensorTrafficStatus(s),
      });
    }
  }
  return rows;
}

export function trafficLabel(status: string): string {
  if (status === "ok") return "سبز — در محدوده";
  if (status === "warning") return "زرد — نزدیک حد / هشدار";
  if (status === "critical") return "قرمز — خارج از محدوده";
  return "بدون داده";
}

export function loggerKindLabel(kind?: string): string {
  if (kind === "plc") return "PLC";
  if (kind === "scada") return "SCADA";
  if (kind === "data_logger") return "Data Logger";
  return kind ?? "—";
}
