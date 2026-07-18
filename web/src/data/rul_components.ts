/** Offline fallback for component-level predictive maintenance (RUL). */

import type { ComponentRul, RulComponentsBoard } from "./equipment";

const ALERT_THRESHOLD_DAYS = 14;

type LocalCompDef = {
  component_id: string;
  component_type: string;
  component_type_fa: string;
  name_fa: string;
  equipment_id: string;
  equipment_name: string;
  line_id: string;
  rul_days: number;
  failure_mode_fa: string;
  recommended_action_fa: string;
};

const LOCAL_COMPONENTS: LocalCompDef[] = [
  {
    component_id: "CMP-BELT-DRY",
    component_type: "belt",
    component_type_fa: "تسمه",
    name_fa: "تسمه درایو خشک‌کن دوار",
    equipment_id: "DRY-001",
    equipment_name: "خشک‌کن دوار",
    line_id: "L1",
    rul_days: 4.2,
    failure_mode_fa: "سایش / لغزش تسمه",
    recommended_action_fa: "بازرسی کشش تسمه، تعویض در صورت ترک یا براق‌شدگی",
  },
  {
    component_id: "CMP-BELT-GRN",
    component_type: "belt",
    component_type_fa: "تسمه",
    name_fa: "تسمه انتقال گرانولاتور",
    equipment_id: "GRN-001",
    equipment_name: "گرانولاتور",
    line_id: "L1",
    rul_days: 38,
    failure_mode_fa: "پارگی یا شل‌شدن تسمه",
    recommended_action_fa: "تنظیم کشش و تعویض تسمه یدکی",
  },
  {
    component_id: "CMP-OIL-FEED",
    component_type: "oil",
    component_type_fa: "روغن / روانکاری",
    name_fa: "روغن گیربکس خوراک‌دهنده",
    equipment_id: "OIL-001",
    equipment_name: "سیستم روغن‌کاری",
    line_id: "L1",
    rul_days: 6.5,
    failure_mode_fa: "افت فشار / آلودگی روغن",
    recommended_action_fa: "تعویض روغن و فیلتر؛ بررسی نشتی",
  },
  {
    component_id: "CMP-AIR-BLOW",
    component_type: "air",
    component_type_fa: "هوا / سیستم هوا",
    name_fa: "دمنده هوای فرآیند",
    equipment_id: "FAN-001",
    equipment_name: "فن فرآیند",
    line_id: "L1",
    rul_days: 9.1,
    failure_mode_fa: "کاهش دبی هوا / گرفتگی",
    recommended_action_fa: "بازرسی فیلتر هوا و تنظیم دمپر",
  },
  {
    component_id: "CMP-FLT-BAG",
    component_type: "filter",
    component_type_fa: "فیلتر",
    name_fa: "کیسه فیلتر بگ‌هاوس",
    equipment_id: "BAG-001",
    equipment_name: "بگ‌هاوس",
    line_id: "L1",
    rul_days: 3.8,
    failure_mode_fa: "گرفتگی / پارگی کیسه",
    recommended_action_fa: "پالس‌شویی و تعویض کیسه‌های آسیب‌دیده",
  },
  {
    component_id: "CMP-BRG-FAN",
    component_type: "bearing",
    component_type_fa: "یاتاقان",
    name_fa: "یاتاقان فن اصلی",
    equipment_id: "FAN-001",
    equipment_name: "فن فرآیند",
    line_id: "L1",
    rul_days: 11.2,
    failure_mode_fa: "سایش یاتاقان / لرزش",
    recommended_action_fa: "روانکاری و تعویض یاتاقان در توقف برنامه‌ریزی‌شده",
  },
  {
    component_id: "CMP-SEAL-PMP",
    component_type: "seal",
    component_type_fa: "آب‌بند / سیل",
    name_fa: "مکانیکال سیل پمپ",
    equipment_id: "PMP-001",
    equipment_name: "پمپ فرآیند",
    line_id: "L2",
    rul_days: 52,
    failure_mode_fa: "نشتی سیل",
    recommended_action_fa: "بازرسی نشتی و تعویض سیل",
  },
  {
    component_id: "CMP-MTR-CMP",
    component_type: "motor",
    component_type_fa: "موتور الکتریکی",
    name_fa: "موتور کمپرسور هوا",
    equipment_id: "CMP-001",
    equipment_name: "کمپرسور هوا",
    line_id: "UTIL",
    rul_days: 95,
    failure_mode_fa: "گرم‌شدن سیم‌پیچ",
    recommended_action_fa: "بررسی جریان و تهویه موتور",
  },
];

function toRow(c: LocalCompDef): ComponentRul {
  const failP = Math.max(0.05, Math.min(0.9, 1 - c.rul_days / 90));
  const severity = c.rul_days <= 5 ? "critical" : c.rul_days <= ALERT_THRESHOLD_DAYS ? "warning" : "info";
  const alert = c.rul_days <= ALERT_THRESHOLD_DAYS;
  return {
    ...c,
    failure_probability: Math.round(failP * 1000) / 1000,
    health_score: Math.round(Math.min(1, c.rul_days / 90) * 1000) / 1000,
    severity,
    alert,
    alert_type: `rul_${c.component_type}`,
    message: `RUL ${c.component_type_fa} — ${c.name_fa}: ${c.rul_days} روز باقی‌مانده. ${c.recommended_action_fa}`,
  };
}

export function buildLocalRulComponentsBoard(): RulComponentsBoard {
  const components = LOCAL_COMPONENTS.map(toRow).sort((a, b) => a.rul_days - b.rul_days);
  const alerts = components.filter((c) => c.alert);
  const by_type: Record<string, number> = {};
  for (const c of components) {
    by_type[c.component_type] = (by_type[c.component_type] ?? 0) + 1;
  }
  return {
    source: "RUL اجزا (آفلاین) — تسمه · روغن · هوا · یاتاقان · فیلتر · موتور",
    alert_threshold_days: ALERT_THRESHOLD_DAYS,
    components,
    alerts,
    summary: {
      component_count: components.length,
      alert_count: alerts.length,
      critical_count: alerts.filter((a) => a.severity === "critical").length,
      warning_count: alerts.filter((a) => a.severity === "warning").length,
      by_type,
      min_rul_days: components[0]?.rul_days ?? null,
      types_fa: ["تسمه", "روغن / روانکاری", "هوا / سیستم هوا", "یاتاقان", "فیلتر", "آب‌بند / سیل", "موتور الکتریکی"],
    },
  };
}

export function severityLabelFa(severity: string): string {
  if (severity === "critical") return "بحرانی";
  if (severity === "warning") return "هشدار";
  return "اطلاع";
}
