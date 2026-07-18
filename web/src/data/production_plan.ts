/** Offline/static demand-driven production board (fallback when API is down). */

export type DemandGradeRow = {
  product_grade: string;
  demand_baseline_kg: number;
  demand_sales_queue_kg: number;
  demand_export_kg: number;
  demand_total_kg: number;
  safety_stock_kg: number;
  planned_quantity_kg: number;
  production_line: string;
  margin_score: number;
  horizon_days?: number;
};

export type ScheduleSlot = {
  date: string;
  weekday: string;
  product_grade: string;
  production_line: string;
  quantity_kg: number;
  line_utilization_pct: number;
  demand_source: string;
};

export type ProductionBoard = {
  source?: string;
  horizon_days: number;
  schedule_days: number;
  plan_date: string;
  demand_by_grade: DemandGradeRow[];
  schedule: ScheduleSlot[];
  sales_pipeline_summary?: Record<string, unknown>;
  line_capacity_kg_day?: Record<string, number>;
  summary: {
    grades_count: number;
    total_demand_kg: number;
    total_planned_kg: number;
    total_scheduled_kg: number;
    backlog_kg: number;
    schedule_slots: number;
    lines_used: string[];
    line_load_kg: Record<string, number>;
    coverage_pct: number;
  };
};

const BASE_MONTHLY: Record<string, number> = {
  "N-220": 380_000,
  "N-234": 220_000,
  "N-326": 180_000,
  "N-330": 420_000,
  "N-330-SV": 160_000,
  "N-339": 200_000,
  "N-375": 150_000,
  "N-550-ICC": 280_000,
  "N-550-VJ": 210_000,
  "N-660": 260_000,
  "P-8201": 90_000,
};

const LINE_OF: Record<string, string> = {
  "N-220": "Line_1",
  "N-234": "Line_1",
  "N-326": "Line_1",
  "N-330": "Line_1",
  "N-330-SV": "Line_1",
  "N-339": "Line_1",
  "N-375": "Line_1",
  "N-550-ICC": "Line_2",
  "N-550-VJ": "Line_2",
  "N-660": "Line_2",
  "P-8201": "Line_2",
};

const MARGIN: Record<string, number> = {
  "N-220": 0.12,
  "N-234": 0.13,
  "N-326": 0.1,
  "N-330": 0.11,
  "N-330-SV": 0.11,
  "N-339": 0.12,
  "N-375": 0.12,
  "N-550-ICC": 0.09,
  "N-550-VJ": 0.09,
  "N-660": 0.08,
  "P-8201": 0.14,
};

function isoPlus(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

export function buildLocalProductionBoard(horizonDays = 30, scheduleDays = 14): ProductionBoard {
  const demand_by_grade: DemandGradeRow[] = Object.entries(BASE_MONTHLY)
    .map(([grade, base]) => {
      const hist = base * (horizonDays / 30);
      const q = grade === "N-330" ? 30_900 : grade === "N-220" ? 27_500 : 8_000;
      const ex = hist * 0.18;
      const total = hist * 0.55 + q * 0.3 + ex * 0.15;
      const safety = total * 0.12;
      return {
        product_grade: grade,
        demand_baseline_kg: Math.round(hist),
        demand_sales_queue_kg: Math.round(q),
        demand_export_kg: Math.round(ex),
        demand_total_kg: Math.round(total),
        safety_stock_kg: Math.round(safety),
        planned_quantity_kg: Math.round(total + safety),
        production_line: LINE_OF[grade] ?? "Line_1",
        margin_score: MARGIN[grade] ?? 0.1,
        horizon_days: horizonDays,
      };
    })
    .sort((a, b) => b.planned_quantity_kg - a.planned_quantity_kg);

  const schedule: ScheduleSlot[] = [];
  const remaining = Object.fromEntries(demand_by_grade.map((r) => [r.product_grade, r.planned_quantity_kg]));
  const caps: Record<string, number> = { Line_1: 48_000, Line_2: 42_000 };
  const order = [...demand_by_grade].sort((a, b) => b.margin_score - a.margin_score);

  for (let d = 0; d < scheduleDays; d++) {
    const left = { ...caps };
    for (const row of order) {
      const need = remaining[row.product_grade] ?? 0;
      if (need < 500) continue;
      const avail = left[row.production_line] ?? 0;
      if (avail < 500) continue;
      const qty = Math.min(need, avail);
      remaining[row.product_grade] = need - qty;
      left[row.production_line] -= qty;
      const util = 1 - left[row.production_line] / (caps[row.production_line] || 1);
      schedule.push({
        date: isoPlus(d + 1),
        weekday: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][(new Date(isoPlus(d + 1)).getDay() + 6) % 7],
        product_grade: row.product_grade,
        production_line: row.production_line,
        quantity_kg: Math.round(qty),
        line_utilization_pct: Math.round(util * 1000) / 10,
        demand_source: "forecast+sales+export",
      });
    }
  }

  for (const [grade, left] of Object.entries(remaining)) {
    if (left > 500) {
      schedule.push({
        date: isoPlus(scheduleDays + 1),
        weekday: "backlog",
        product_grade: grade,
        production_line: LINE_OF[grade] ?? "Line_1",
        quantity_kg: Math.round(left),
        line_utilization_pct: 100,
        demand_source: "backlog",
      });
    }
  }

  const total_demand = demand_by_grade.reduce((s, r) => s + r.demand_total_kg, 0);
  const total_planned = demand_by_grade.reduce((s, r) => s + r.planned_quantity_kg, 0);
  const total_scheduled = schedule
    .filter((s) => s.demand_source !== "backlog")
    .reduce((s, r) => s + r.quantity_kg, 0);
  const backlog = schedule.filter((s) => s.demand_source === "backlog").reduce((s, r) => s + r.quantity_kg, 0);
  const line_load_kg: Record<string, number> = {};
  for (const s of schedule) {
    if (s.demand_source === "backlog") continue;
    line_load_kg[s.production_line] = (line_load_kg[s.production_line] ?? 0) + s.quantity_kg;
  }

  return {
    source: "آفلاین — تقاضا (پایه + صف فروش + صادرات) → برنامه تولید",
    horizon_days: horizonDays,
    schedule_days: scheduleDays,
    plan_date: new Date().toISOString().slice(0, 10),
    demand_by_grade,
    schedule,
    line_capacity_kg_day: { Line_1: 48_000, Line_2: 42_000, UTIL: 0 },
    summary: {
      grades_count: demand_by_grade.length,
      total_demand_kg: Math.round(total_demand),
      total_planned_kg: Math.round(total_planned),
      total_scheduled_kg: Math.round(total_scheduled),
      backlog_kg: Math.round(backlog),
      schedule_slots: schedule.filter((s) => s.demand_source !== "backlog").length,
      lines_used: Object.keys(line_load_kg).sort(),
      line_load_kg,
      coverage_pct: total_planned ? Math.round((total_scheduled / total_planned) * 1000) / 10 : 0,
    },
  };
}
