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
    component_type_fa: "Belt",
    name_fa: "Rotary dryer drive belt",
    equipment_id: "DRY-001",
    equipment_name: "Rotary dryer",
    line_id: "L1",
    rul_days: 4.2,
    failure_mode_fa: "Belt wear / slip",
    recommended_action_fa: "Inspect belt tension; replace if cracked or glazed",
  },
  {
    component_id: "CMP-BELT-GRN",
    component_type: "belt",
    component_type_fa: "Belt",
    name_fa: "Pelletizer transmission belt",
    equipment_id: "GRN-001",
    equipment_name: "Pelletizer",
    line_id: "L1",
    rul_days: 38,
    failure_mode_fa: "Belt tear or loosening",
    recommended_action_fa: "Adjust tension and replace with a spare belt",
  },
  {
    component_id: "CMP-OIL-FEED",
    component_type: "oil",
    component_type_fa: "Oil / lubrication",
    name_fa: "Feeder gearbox oil",
    equipment_id: "OIL-001",
    equipment_name: "Lubrication system",
    line_id: "L1",
    rul_days: 6.5,
    failure_mode_fa: "Pressure drop / oil contamination",
    recommended_action_fa: "Replace oil and filter; check for leaks",
  },
  {
    component_id: "CMP-AIR-BLOW",
    component_type: "air",
    component_type_fa: "Air / air system",
    name_fa: "Process air blower",
    equipment_id: "FAN-001",
    equipment_name: "Process fan",
    line_id: "L1",
    rul_days: 9.1,
    failure_mode_fa: "Reduced air flow / blockage",
    recommended_action_fa: "Inspect the air filter and adjust the damper",
  },
  {
    component_id: "CMP-FLT-BAG",
    component_type: "filter",
    component_type_fa: "Filter",
    name_fa: "Baghouse filter bag",
    equipment_id: "BAG-001",
    equipment_name: "Baghouse",
    line_id: "L1",
    rul_days: 3.8,
    failure_mode_fa: "Blockage / bag tear",
    recommended_action_fa: "Pulse cleaning and replacement of damaged bags",
  },
  {
    component_id: "CMP-BRG-FAN",
    component_type: "bearing",
    component_type_fa: "Bearing",
    name_fa: "Main fan bearing",
    equipment_id: "FAN-001",
    equipment_name: "Process fan",
    line_id: "L1",
    rul_days: 11.2,
    failure_mode_fa: "Bearing wear / vibration",
    recommended_action_fa: "Lubrication and bearing replacement in a planned shutdown",
  },
  {
    component_id: "CMP-SEAL-PMP",
    component_type: "seal",
    component_type_fa: "Seal",
    name_fa: "Pump mechanical seal",
    equipment_id: "PMP-001",
    equipment_name: "Process pump",
    line_id: "L2",
    rul_days: 52,
    failure_mode_fa: "Seal leak",
    recommended_action_fa: "Leak inspection and seal replacement",
  },
  {
    component_id: "CMP-MTR-CMP",
    component_type: "motor",
    component_type_fa: "Electric motor",
    name_fa: "Air compressor motor",
    equipment_id: "CMP-001",
    equipment_name: "Air compressor",
    line_id: "UTIL",
    rul_days: 95,
    failure_mode_fa: "Winding overheating",
    recommended_action_fa: "Check the motor current and ventilation",
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
    message: `RUL ${c.component_type_fa} — ${c.name_fa}: ${c.rul_days} days remaining. ${c.recommended_action_fa}`,
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
    source: "Component RUL (offline) — belt · oil · air · bearing · filter · motor",
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
      types_fa: ["Belt", "Oil / lubrication", "Air / air system", "Bearing", "Filter", "Seal", "Electric motor"],
    },
  };
}

export function severityLabelFa(severity: string): string {
  if (severity === "critical") return "Critical";
  if (severity === "warning") return "Warning";
  return "Info";
}
