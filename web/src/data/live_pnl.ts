/** Live P&L / operations snapshot for overview dashboard. */

import type { MarketScenarioBoard } from "./market_scenarios";
import type { ProcurementBoard } from "./procurement";
import type { SalesPipeline } from "./sales_pipeline";

export type ScenarioProfitRow = {
  id: string;
  name_fa: string;
  estimated_profit_irr: number;
  estimated_gross_profit_irr: number;
  delta_vs_baseline_irr: number;
  recommended?: boolean;
};

export type LivePnlSnapshot = {
  as_of_label: string;
  horizon_days: number;
  net_profit_irr: number;
  gross_profit_irr: number;
  material_purchase_irr: number;
  sales_irr: number;
  purchase_queue_irr: number;
  inbound_freight_irr: number;
  outbound_distribution_irr: number;
  scenario_profits: ScenarioProfitRow[];
  source?: string;
};

const AVG_SELL_IRR = 185_000;
const INBOUND_FREIGHT_PCT = 0.045;
const OUTBOUND_DIST_PCT = 0.035;
/** Monthly feedstock proxy when scenario feed not available (kg). */
const MONTHLY_FEED_KG = 1_250_000;

function num(v: unknown, fallback = 0): number {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function queueValueIrr(pipeline: SalesPipeline): number {
  return pipeline.purchase_queue.reduce((sum, q) => {
    if (q.expected_revenue_irr != null) return sum + num(q.expected_revenue_irr);
    const price = num(q.unit_price_irr, AVG_SELL_IRR);
    const w = num(q.weighted_tonnage_kg, num(q.requested_tonnage_kg) * num(q.probability, 1));
    return sum + w * price;
  }, 0);
}

function materialPurchaseIrr(
  procurement: ProcurementBoard,
  scenarios: MarketScenarioBoard,
): number {
  const feedNeed = num(scenarios.summary?.total_feedstock_need_kg);
  const basket = num(scenarios.macros?.current?.feedstock_basket_irr, 42_000);
  if (feedNeed > 0 && basket > 0) return feedNeed * basket;

  // Fallback: weighted basket from live quotes × typical shares
  const mats = procurement.materials ?? [];
  if (!mats.length) return MONTHLY_FEED_KG * basket;
  const shareSum = mats.reduce((s, m) => s + num(m.typical_share_pct), 0) || 100;
  return mats.reduce((s, m) => {
    const price = num(m.latest_price_irr, num(m.avg_market_irr, basket));
    const share = num(m.typical_share_pct) / shareSum;
    return s + MONTHLY_FEED_KG * share * price;
  }, 0);
}

function salesIrr(
  finance: Record<string, unknown> | null | undefined,
  salesMtd: { month_revenue?: number } | null | undefined,
  pipeline: SalesPipeline,
  scenarios: MarketScenarioBoard,
): number {
  const mtd = num(salesMtd?.month_revenue);
  if (mtd > 0) return mtd;
  const finRev = num((finance as { revenue_ytd?: number } | null)?.revenue_ytd);
  if (finRev > 0) return finRev / 12; // monthly proxy from YTD
  const fc = (pipeline.sales_forecast_with_queue ?? []).reduce(
    (s, f) => s + num(f.forecast_revenue_irr),
    0,
  );
  if (fc > 0) return fc;
  const produce = num(scenarios.summary?.total_produce_kg);
  return produce * AVG_SELL_IRR;
}

function scenarioProfitRows(board: MarketScenarioBoard): ScenarioProfitRow[] {
  const comps = board.comparisons ?? [];
  const baseline =
    comps.find((c) => c.id === "baseline") ??
    comps.find((c) => c.id === board.selected_scenario?.id) ??
    comps[0];
  const baseProfit = num(
    baseline?.summary?.estimated_profit_irr,
    estimateFromSummary(baseline?.summary, baseline?.macros?.feedstock_basket_irr),
  );

  const rows = (comps.length ? comps : [{ id: board.selected_scenario.id, name_fa: board.selected_scenario.name_fa, summary: board.summary, macros: board.macros.current, recommended: true }]).map(
    (c) => {
      const profit = num(
        c.summary?.estimated_profit_irr,
        estimateFromSummary(c.summary, c.macros?.feedstock_basket_irr),
      );
      const gross = num(
        c.summary?.estimated_gross_profit_irr,
        profit * 1.15,
      );
      return {
        id: c.id,
        name_fa: c.name_fa,
        estimated_profit_irr: Math.round(profit),
        estimated_gross_profit_irr: Math.round(gross),
        delta_vs_baseline_irr: Math.round(profit - baseProfit),
        recommended: c.recommended,
      };
    },
  );
  return rows.sort((a, b) => b.estimated_profit_irr - a.estimated_profit_irr).slice(0, 5);
}

function estimateFromSummary(
  summary: { total_produce_kg?: number; total_feedstock_need_kg?: number; estimated_profit_irr?: number } | undefined,
  feedPrice?: number,
): number {
  if (!summary) return 0;
  if (summary.estimated_profit_irr != null) return num(summary.estimated_profit_irr);
  const produce = num(summary.total_produce_kg);
  const feed = num(summary.total_feedstock_need_kg);
  const rev = produce * AVG_SELL_IRR;
  const feedCost = feed * num(feedPrice, 42_000);
  const gross = rev * 0.12;
  return gross - feedCost * INBOUND_FREIGHT_PCT - rev * OUTBOUND_DIST_PCT;
}

export function buildLivePnlSnapshot(args: {
  finance?: Record<string, unknown> | null;
  salesMtd?: { month_revenue?: number; month_qty?: number } | null;
  procurement: ProcurementBoard;
  salesPipeline: SalesPipeline;
  marketScenarios: MarketScenarioBoard;
}): LivePnlSnapshot {
  const { finance, salesMtd, procurement, salesPipeline, marketScenarios } = args;
  const horizon = num(marketScenarios.horizon_days, 30);
  const sales = salesIrr(finance, salesMtd, salesPipeline, marketScenarios);
  const material = materialPurchaseIrr(procurement, marketScenarios);
  const inbound = material * INBOUND_FREIGHT_PCT;
  const outbound = sales * OUTBOUND_DIST_PCT;

  const finGross = num((finance as { gross_profit?: number } | null)?.gross_profit);
  const finNet = num((finance as { net_profit?: number } | null)?.net_profit);
  // Prefer live ops-derived when finance report is empty/stale zeros
  const grossFromOps = Math.max(0, sales - material);
  const gross = finGross > 0 ? finGross / (finGross > sales * 2 ? 12 : 1) : grossFromOps;
  // If finance YTD-scale, divide already handled for sales; for profit use monthly share when huge
  let grossMonthly = gross;
  if (finGross > 0 && finGross > sales * 3) grossMonthly = finGross / 12;

  const opexProxy = num((finance as { operating_expenses?: number } | null)?.operating_expenses);
  const opexMonthly = opexProxy > sales * 2 ? opexProxy / 12 : opexProxy > 0 ? opexProxy : sales * 0.04;
  const netFromOps = grossMonthly - inbound - outbound - opexMonthly * 0.25;
  let net = finNet > 0 ? (finNet > sales * 3 ? finNet / 12 : finNet) : netFromOps;
  if (finNet === 0 && finGross === 0) net = netFromOps;

  const purchaseQueue = queueValueIrr(salesPipeline);
  const scenario_profits = scenarioProfitRows(marketScenarios);

  return {
    as_of_label: "Instantaneous · horizon " + horizon + " days",
    horizon_days: horizon,
    net_profit_irr: Math.round(net),
    gross_profit_irr: Math.round(grossMonthly),
    material_purchase_irr: Math.round(material),
    sales_irr: Math.round(sales),
    purchase_queue_irr: Math.round(purchaseQueue),
    inbound_freight_irr: Math.round(inbound),
    outbound_distribution_irr: Math.round(outbound),
    scenario_profits,
    source: "MTD sales · material basket · purchase queue · market scenarios",
  };
}
