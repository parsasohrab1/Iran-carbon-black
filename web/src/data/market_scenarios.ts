/** Offline market-shock production scenarios (USD · gold · oil · feedstock). */

export type ScenarioMacros = {
  usd_irr: number;
  gold_irr_g: number;
  oil_usd: number;
  feedstock_basket_irr: number;
};

export type ScenarioGradeRow = {
  product_grade: string;
  production_line: string;
  sales_queue_kg: number;
  sales_queue_items: number;
  confirmed_queue_kg: number;
  inventory_on_hand_kg: number;
  inventory_cover_days: number;
  effective_demand_kg: number;
  excess_inventory_kg: number;
  planned_produce_kg: number;
  safety_stock_kg: number;
  adjusted_margin: number;
  base_margin: number;
  feedstock_intensity: number;
  feedstock_need_kg: number;
  feedstock_buy_advice: string;
  action: string;
  reason_fa: string;
  priority_score: number;
};

export type ScenarioComparison = {
  id: string;
  name_fa: string;
  description_fa: string;
  macros: ScenarioMacros;
  deltas_pct: Record<string, number>;
  indices: Record<string, number>;
  summary: ScenarioSummary;
  top_grades: string[];
  recommended?: boolean;
};

export type ScenarioSummary = {
  total_produce_kg: number;
  total_sales_queue_kg: number;
  total_excess_inventory_kg: number;
  total_feedstock_need_kg: number;
  uncovered_sales_queue_kg: number;
  warehouse_risk: string;
  sales_queue_risk: string;
  purchase_queue_risk: string;
  balance_score: number;
  policy_fa: string;
};

export type MarketScenarioBoard = {
  source?: string;
  plan_date: string;
  horizon_days: number;
  selected_scenario: { id: string; name_fa: string; description_fa: string };
  macros: {
    baseline: ScenarioMacros;
    current: ScenarioMacros;
    deltas_pct: Record<string, number>;
    indices: Record<string, number>;
  };
  presets: Array<{
    id: string;
    name_fa: string;
    description_fa: string;
    usd_irr_delta_pct: number;
    gold_delta_pct: number;
    oil_delta_pct: number;
    feedstock_delta_pct: number;
  }>;
  grades: ScenarioGradeRow[];
  summary: ScenarioSummary;
  comparisons: ScenarioComparison[];
  feedstock_actions: Array<{
    product_grade: string;
    advice: string;
    feedstock_need_kg: number;
    note_fa: string;
  }>;
  objectives_fa: string[];
};

const PRESETS = [
  {
    id: "baseline",
    name_fa: "پایه (بازار جاری)",
    description_fa: "نرخ ارز، طلا، نفت و خوراک در سطح مرجع.",
    usd_irr_delta_pct: 0,
    gold_delta_pct: 0,
    oil_delta_pct: 0,
    feedstock_delta_pct: 0,
  },
  {
    id: "usd_shock",
    name_fa: "شوک دلار (ارز↑)",
    description_fa: "ضعف ریال → اولویت صادرات و گریدهای ارزی.",
    usd_irr_delta_pct: 18,
    gold_delta_pct: 8,
    oil_delta_pct: 4,
    feedstock_delta_pct: 6,
  },
  {
    id: "gold_oil_up",
    name_fa: "طلا و نفت صعودی",
    description_fa: "فشار تورم خوراک؛ تولید سبک‌تر و صف فروش اول.",
    usd_irr_delta_pct: 5,
    gold_delta_pct: 15,
    oil_delta_pct: 20,
    feedstock_delta_pct: 14,
  },
  {
    id: "feedstock_spike",
    name_fa: "جهش قیمت مواد خام",
    description_fa: "توقف انبار؛ تمرکز پرمارژین و تخلیه موجودی نرم.",
    usd_irr_delta_pct: 3,
    gold_delta_pct: 5,
    oil_delta_pct: 12,
    feedstock_delta_pct: 28,
  },
  {
    id: "soft_landing",
    name_fa: "فرود نرم (کالا↓)",
    description_fa: "پیش‌خرید مواد بدون صف خرید؛ پوشش صف فروش.",
    usd_irr_delta_pct: -6,
    gold_delta_pct: -4,
    oil_delta_pct: -10,
    feedstock_delta_pct: -12,
  },
] as const;

export function actionLabelFa(action: string): string {
  const map: Record<string, string> = {
    produce_for_sales_queue: "تولید برای صف فروش",
    drawdown_inventory: "تخلیه انبار",
    hold_low_margin: "توقف کم‌مارژین",
    produce_queue_only: "فقط صف فروش",
    produce_and_prebuy_feed: "تولید + پیش‌خرید مواد",
    boost_export_grade: "افزایش صادراتی",
    trim_to_demand: "کاهش تا تقاضا",
    balanced_produce: "تولید متوازن",
  };
  return map[action] ?? action;
}

export function buyAdviceLabelFa(advice: string): string {
  const map: Record<string, string> = {
    hold: "نگهداری",
    prebuy_window: "پنجره پیش‌خرید",
    delay_noncritical: "تأخیر خرید",
    buy_for_queue: "خرید برای صف فروش",
  };
  return map[advice] ?? advice;
}

export function riskTone(risk: string): "ok" | "warn" | "danger" {
  if (risk === "کم") return "ok";
  if (risk === "متوسط") return "warn";
  return "danger";
}

/** Lightweight offline board mirroring backend scenario engine. */
export function buildLocalMarketScenarioBoard(scenarioId = "baseline"): MarketScenarioBoard {
  const preset = PRESETS.find((p) => p.id === scenarioId) ?? PRESETS[0];
  const base: ScenarioMacros = {
    usd_irr: 620_000,
    gold_irr_g: 4_850_000,
    oil_usd: 78,
    feedstock_basket_irr: 43_200,
  };
  const current: ScenarioMacros = {
    usd_irr: Math.round(base.usd_irr * (1 + preset.usd_irr_delta_pct / 100)),
    gold_irr_g: Math.round(base.gold_irr_g * (1 + preset.gold_delta_pct / 100)),
    oil_usd: Math.round(base.oil_usd * (1 + preset.oil_delta_pct / 100) * 100) / 100,
    feedstock_basket_irr: Math.round(base.feedstock_basket_irr * (1 + preset.feedstock_delta_pct / 100)),
  };
  const cost =
    0.45 * (current.feedstock_basket_irr / base.feedstock_basket_irr) +
    0.25 * (current.oil_usd / base.oil_usd) +
    0.2 * (current.gold_irr_g / base.gold_irr_g) +
    0.1 * (current.usd_irr / base.usd_irr);

  const seed = [
    { g: "N-330", q: 30900, inv: 180000, m: 0.11, inten: 1 },
    { g: "N-220", q: 27500, inv: 95000, m: 0.12, inten: 1.12 },
    { g: "N-550-ICC", q: 18000, inv: 140000, m: 0.09, inten: 0.92 },
    { g: "N-660", q: 3600, inv: 160000, m: 0.08, inten: 0.85 },
    { g: "N-234", q: 8400, inv: 40000, m: 0.13, inten: 1.15 },
    { g: "P-8201", q: 0, inv: 18000, m: 0.14, inten: 1.18 },
    { g: "N-326", q: 0, inv: 120000, m: 0.1, inten: 1.05 },
    { g: "N-339", q: 2800, inv: 70000, m: 0.12, inten: 1.08 },
  ];

  const grades: ScenarioGradeRow[] = seed.map((s, i) => {
    const fx = current.usd_irr / base.usd_irr;
    const margin = Math.max(0.02, s.m - (cost - 1) * 0.07 * s.inten + (fx - 1) * 0.05);
    const demand = 120000 + i * 8000;
    const daily = demand / 30;
    const excess = Math.max(0, s.inv - daily * 20);
    const produce = Math.max(s.q * 1.05, demand - excess * 0.85);
    let action = "balanced_produce";
    let reason = "تولید متوازن با پوشش صف فروش و کنترل موجودی";
    if (s.q > 5000 && s.inv < s.q * 0.5) {
      action = "produce_for_sales_queue";
      reason = "اولویت صف فروش — موجودی ناکافی";
    } else if (s.inv / daily > 45 && s.q < 3000) {
      action = "drawdown_inventory";
      reason = "انبار بالا — جلوگیری از انبارداری";
    } else if (cost > 1.15 && margin < 0.09) {
      action = "hold_low_margin";
      reason = "خوراک گران و حاشیه پایین";
    } else if (fx > 1.1 && margin >= 0.12) {
      action = "boost_export_grade";
      reason = "دلار↑ — افزایش سهم صادراتی";
    }
    const buy =
      current.feedstock_basket_irr / base.feedstock_basket_irr < 0.95
        ? "prebuy_window"
        : current.feedstock_basket_irr / base.feedstock_basket_irr > 1.2
          ? "delay_noncritical"
          : s.q > s.inv
            ? "buy_for_queue"
            : "hold";
    return {
      product_grade: s.g,
      production_line: s.g.startsWith("N-5") || s.g.startsWith("N-6") || s.g.startsWith("P") ? "Line_2" : "Line_1",
      sales_queue_kg: s.q,
      sales_queue_items: s.q > 0 ? 2 : 0,
      confirmed_queue_kg: Math.round(s.q * 0.4),
      inventory_on_hand_kg: s.inv,
      inventory_cover_days: Math.round((s.inv / daily) * 10) / 10,
      effective_demand_kg: Math.round(demand),
      excess_inventory_kg: Math.round(excess),
      planned_produce_kg: Math.round(produce),
      safety_stock_kg: Math.round(produce * 0.08),
      adjusted_margin: Math.round(margin * 10000) / 10000,
      base_margin: s.m,
      feedstock_intensity: s.inten,
      feedstock_need_kg: Math.round(produce * s.inten * 1.35),
      feedstock_buy_advice: buy,
      action,
      reason_fa: reason,
      priority_score: Math.round(s.q / 1000 + margin * 100 - excess / 5000),
    };
  });
  grades.sort((a, b) => b.priority_score - a.priority_score);

  const total_produce = grades.reduce((s, g) => s + g.planned_produce_kg, 0);
  const total_queue = grades.reduce((s, g) => s + g.sales_queue_kg, 0);
  const total_excess = grades.reduce((s, g) => s + g.excess_inventory_kg, 0);
  const total_feed = grades.reduce((s, g) => s + g.feedstock_need_kg, 0);
  const warehouse_risk = total_excess > 250000 ? "بالا" : total_excess > 100000 ? "متوسط" : "کم";
  const sales_queue_risk = total_queue > 80000 ? "متوسط" : "کم";
  const purchase_queue_risk = cost > 1.15 ? "متوسط" : "کم";
  const summary: ScenarioSummary = {
    total_produce_kg: total_produce,
    total_sales_queue_kg: total_queue,
    total_excess_inventory_kg: total_excess,
    total_feedstock_need_kg: total_feed,
    uncovered_sales_queue_kg: Math.max(0, total_queue - total_produce * 0.2),
    warehouse_risk,
    sales_queue_risk,
    purchase_queue_risk,
    balance_score: 100 - (warehouse_risk === "بالا" ? 10 : 5) - (sales_queue_risk === "متوسط" ? 6 : 0),
    policy_fa: "اولویت ۱: پوشش صف فروش · اولویت ۲: عدم انبار · اولویت ۳: خرید مواد فقط برای برنامه",
  };

  const comparisons: ScenarioComparison[] = PRESETS.map((p) => {
    const scoreAdj = Math.abs(p.feedstock_delta_pct) / 4 + Math.abs(p.usd_irr_delta_pct) / 8;
    return {
      id: p.id,
      name_fa: p.name_fa,
      description_fa: p.description_fa,
      macros: {
        usd_irr: Math.round(base.usd_irr * (1 + p.usd_irr_delta_pct / 100)),
        gold_irr_g: Math.round(base.gold_irr_g * (1 + p.gold_delta_pct / 100)),
        oil_usd: Math.round(base.oil_usd * (1 + p.oil_delta_pct / 100) * 100) / 100,
        feedstock_basket_irr: Math.round(base.feedstock_basket_irr * (1 + p.feedstock_delta_pct / 100)),
      },
      deltas_pct: {
        usd_irr: p.usd_irr_delta_pct,
        gold_irr_g: p.gold_delta_pct,
        oil_usd: p.oil_delta_pct,
        feedstock_basket_irr: p.feedstock_delta_pct,
      },
      indices: {
        cost_pressure: Math.round(cost * 1000) / 1000,
        fx_tailwind: Math.round((current.usd_irr / base.usd_irr) * 1000) / 1000,
      },
      summary: {
        ...summary,
        balance_score: Math.max(60, Math.round(summary.balance_score - (p.id === scenarioId ? 0 : scoreAdj))),
      },
      top_grades: grades.slice(0, 3).map((g) => g.product_grade),
      recommended: p.id === "soft_landing" || p.id === "baseline",
    };
  });

  return {
    source: "آفلاین — نوسان دلار/طلا/نفت/مواد خام → سناریوی تولید",
    plan_date: new Date().toISOString().slice(0, 10),
    horizon_days: 30,
    selected_scenario: {
      id: preset.id,
      name_fa: preset.name_fa,
      description_fa: preset.description_fa,
    },
    macros: {
      baseline: base,
      current,
      deltas_pct: {
        usd_irr: preset.usd_irr_delta_pct,
        gold_irr_g: preset.gold_delta_pct,
        oil_usd: preset.oil_delta_pct,
        feedstock_basket_irr: preset.feedstock_delta_pct,
      },
      indices: {
        cost_pressure: Math.round(cost * 1000) / 1000,
        fx_tailwind: Math.round((current.usd_irr / base.usd_irr) * 1000) / 1000,
        feed_idx: Math.round((current.feedstock_basket_irr / base.feedstock_basket_irr) * 1000) / 1000,
      },
    },
    presets: [...PRESETS],
    grades,
    summary,
    comparisons: comparisons.sort((a, b) => b.summary.balance_score - a.summary.balance_score),
    feedstock_actions: grades
      .filter((g) => g.feedstock_buy_advice !== "hold")
      .slice(0, 8)
      .map((g) => ({
        product_grade: g.product_grade,
        advice: g.feedstock_buy_advice,
        feedstock_need_kg: g.feedstock_need_kg,
        note_fa: buyAdviceLabelFa(g.feedstock_buy_advice),
      })),
    objectives_fa: [
      "جلوگیری از انبارداری محصول نهایی",
      "جلوگیری از صف خرید مواد خام",
      "جلوگیری از صف فروش / سفارش مشتری پاسخ‌نداده",
    ],
  };
}
