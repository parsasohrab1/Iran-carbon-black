/** Offline fallback for sales CRM pipeline (mirrors shared/sales_pipeline.py). */

export type PipelineCustomer = {
  id: string;
  name: string;
  status: string;
  segment?: string;
  region?: string;
  monthly_tonnage_kg: number;
  annual_consumption_kg?: number;
  preferred_grades?: string[] | unknown;
  contact_person?: string;
  pipeline_stage?: string;
  notes?: string;
};

export type QueueItem = {
  id?: number;
  customer_id: string;
  customer_name?: string;
  customer_status?: string;
  grade: string;
  requested_tonnage_kg: number;
  weighted_tonnage_kg?: number;
  expected_revenue_irr?: number;
  priority: number;
  status: string;
  probability: number;
  unit_price_irr?: number;
  notes?: string;
};

export type PipelineForecast = {
  grade: string;
  base_ml_quantity_kg: number;
  queue_requested_kg: number;
  queue_weighted_kg: number;
  forecast_quantity_kg: number;
  forecast_revenue_irr: number;
  recommended_unit_price?: number;
  pipeline_share_pct?: number;
  queue_items?: number;
  source?: string;
};

export type SalesPipeline = {
  source?: string;
  active_customers: PipelineCustomer[];
  potential_customers: PipelineCustomer[];
  purchase_queue: QueueItem[];
  summary: {
    active_count: number;
    potential_count: number;
    queue_items: number;
    active_monthly_tonnage_kg: number;
    potential_monthly_tonnage_kg: number;
    queue_requested_tonnage_kg: number;
    queue_weighted_tonnage_kg: number;
  };
  sales_forecast_with_queue: PipelineForecast[];
};

export function buildLocalSalesPipeline(): SalesPipeline {
  // Dynamic import avoided — duplicate minimal static from shared catalog via API fallback path
  const active: PipelineCustomer[] = [
    { id: "CUST-0047", name: "Sahand Tire", status: "active", monthly_tonnage_kg: 15000, region: "domestic", preferred_grades: ["N330", "N220"], contact_person: "Eng. Rezaei" },
    { id: "CUST-0012", name: "Barez Rubber", status: "active", monthly_tonnage_kg: 18300, region: "domestic", preferred_grades: ["N220", "N234"], contact_person: "Ms. Karimi" },
    { id: "CUST-0021", name: "Kavir Tire", status: "active", monthly_tonnage_kg: 12500, region: "domestic", preferred_grades: ["N550", "N660"], contact_person: "Mr. Mousavi" },
    { id: "CUST-0033", name: "Iran Tire", status: "active", monthly_tonnage_kg: 16250, region: "domestic", preferred_grades: ["N330", "N339"], contact_person: "Eng. Ahmadi" },
    { id: "CUST-0099", name: "Export Partner UAE", status: "active", monthly_tonnage_kg: 7900, region: "export", preferred_grades: ["N550"], contact_person: "Mr. Al-Farsi" },
    { id: "CUST-0055", name: "RubberTech TR", status: "active", monthly_tonnage_kg: 5000, region: "export", preferred_grades: ["N660"], contact_person: "Ms. Yilmaz" },
    { id: "CUST-0070", name: "Cable Poly Iran", status: "active", monthly_tonnage_kg: 3300, region: "domestic", preferred_grades: ["N550", "N660"], contact_person: "Eng. Nouri" },
  ];
  const potential: PipelineCustomer[] = [
    { id: "CUST-0101", name: "Yazd Tire", status: "potential", monthly_tonnage_kg: 7500, region: "domestic", preferred_grades: ["N330", "N220"], contact_person: "Mr. Hosseini", pipeline_stage: "technical_eval" },
    { id: "CUST-0102", name: "Dena Rubber", status: "potential", monthly_tonnage_kg: 9200, region: "domestic", preferred_grades: ["N330", "N339"], contact_person: "Ms. Moradi", pipeline_stage: "sample" },
    { id: "CUST-0103", name: "Pars Rubber", status: "potential", monthly_tonnage_kg: 3750, region: "domestic", preferred_grades: ["N339", "N375"], contact_person: "Eng. Kazemi", pipeline_stage: "proposal" },
    { id: "CUST-0104", name: "Gulf Tire Co.", status: "potential", monthly_tonnage_kg: 10800, region: "export", preferred_grades: ["N220", "N234"], contact_person: "Mr. Rahman", pipeline_stage: "commercial" },
    { id: "CUST-0105", name: "Arya Wire & Cable", status: "potential", monthly_tonnage_kg: 2300, region: "domestic", preferred_grades: ["N550", "N660"], contact_person: "Ms. Jafari", pipeline_stage: "discovery" },
  ];
  const purchase_queue: QueueItem[] = [
    { customer_id: "CUST-0047", customer_name: "Sahand Tire", grade: "N330", requested_tonnage_kg: 18000, priority: 1, status: "queued", probability: 0.85, unit_price_irr: 188000, weighted_tonnage_kg: 15300 },
    { customer_id: "CUST-0012", customer_name: "Barez Rubber", grade: "N220", requested_tonnage_kg: 22000, priority: 1, status: "queued", probability: 0.9, unit_price_irr: 196000, weighted_tonnage_kg: 19800 },
    { customer_id: "CUST-0012", customer_name: "Barez Rubber", grade: "N234", requested_tonnage_kg: 12000, priority: 2, status: "negotiating", probability: 0.7, unit_price_irr: 205000, weighted_tonnage_kg: 8400 },
    { customer_id: "CUST-0033", customer_name: "Iran Tire", grade: "N330", requested_tonnage_kg: 15000, priority: 2, status: "queued", probability: 0.8, unit_price_irr: 187000, weighted_tonnage_kg: 12000 },
    { customer_id: "CUST-0021", customer_name: "Kavir Tire", grade: "N550", requested_tonnage_kg: 10000, priority: 3, status: "queued", probability: 0.65, unit_price_irr: 165000, weighted_tonnage_kg: 6500 },
    { customer_id: "CUST-0099", customer_name: "Export Partner UAE", grade: "N550", requested_tonnage_kg: 9000, priority: 2, status: "confirmed", probability: 0.95, unit_price_irr: 172000, weighted_tonnage_kg: 8550 },
    { customer_id: "CUST-0055", customer_name: "RubberTech TR", grade: "N660", requested_tonnage_kg: 6000, priority: 3, status: "queued", probability: 0.6, unit_price_irr: 158000, weighted_tonnage_kg: 3600 },
    { customer_id: "CUST-0101", customer_name: "Yazd Tire", grade: "N330", requested_tonnage_kg: 8000, priority: 2, status: "queued", probability: 0.45, unit_price_irr: 185000, weighted_tonnage_kg: 3600 },
    { customer_id: "CUST-0102", customer_name: "Dena Rubber", grade: "N339", requested_tonnage_kg: 7000, priority: 3, status: "negotiating", probability: 0.4, unit_price_irr: 190000, weighted_tonnage_kg: 2800 },
    { customer_id: "CUST-0104", customer_name: "Gulf Tire Co.", grade: "N220", requested_tonnage_kg: 14000, priority: 1, status: "queued", probability: 0.55, unit_price_irr: 210000, weighted_tonnage_kg: 7700 },
    { customer_id: "CUST-0103", customer_name: "Pars Rubber", grade: "N375", requested_tonnage_kg: 4500, priority: 4, status: "queued", probability: 0.35, unit_price_irr: 192000, weighted_tonnage_kg: 1575 },
    { customer_id: "CUST-0105", customer_name: "Arya Wire & Cable", grade: "N550", requested_tonnage_kg: 3000, priority: 4, status: "queued", probability: 0.3, unit_price_irr: 160000, weighted_tonnage_kg: 900 },
  ];

  const byGrade: Record<string, { req: number; w: number; rev: number }> = {};
  for (const q of purchase_queue) {
    const slot = (byGrade[q.grade] ??= { req: 0, w: 0, rev: 0 });
    const w = q.requested_tonnage_kg * q.probability;
    slot.req += q.requested_tonnage_kg;
    slot.w += w;
    slot.rev += w * (q.unit_price_irr ?? 180000);
  }
  const sales_forecast_with_queue: PipelineForecast[] = Object.entries(byGrade).map(([grade, agg]) => ({
    grade,
    base_ml_quantity_kg: Math.round(agg.w * 0.35),
    queue_requested_kg: Math.round(agg.req),
    queue_weighted_kg: Math.round(agg.w),
    forecast_quantity_kg: Math.round(agg.w * 1.35),
    forecast_revenue_irr: Math.round(agg.rev + agg.w * 0.35 * 180000),
    pipeline_share_pct: 74,
    source: "catalog+queue",
  }));

  return {
    source: "static sales pipeline catalog",
    active_customers: active,
    potential_customers: potential,
    purchase_queue,
    summary: {
      active_count: active.length,
      potential_count: potential.length,
      queue_items: purchase_queue.length,
      active_monthly_tonnage_kg: active.reduce((s, c) => s + c.monthly_tonnage_kg, 0),
      potential_monthly_tonnage_kg: potential.reduce((s, c) => s + c.monthly_tonnage_kg, 0),
      queue_requested_tonnage_kg: purchase_queue.reduce((s, q) => s + q.requested_tonnage_kg, 0),
      queue_weighted_tonnage_kg: Math.round(
        purchase_queue.reduce((s, q) => s + q.requested_tonnage_kg * q.probability, 0),
      ),
    },
    sales_forecast_with_queue,
  };
}

function isGarbled(value?: string | null): boolean {
  if (value == null || !String(value).trim()) return true;
  const text = String(value);
  if (text.includes("\uFFFD")) return true;
  const q = (text.match(/\?/g) ?? []).length;
  return q >= Math.max(1, Math.floor(text.length / 3));
}

const REGION_FA: Record<string, string> = {
  domestic: "Domestic",
  export: "Export",
};

const STAGE_FA: Record<string, string> = {
  technical_eval: "Technical evaluation",
  sample: "Sample",
  proposal: "Proposal",
  commercial: "Commercial negotiation",
  discovery: "Opportunity discovery",
};

/** Overlay Persian CRM labels from offline catalog so ??? never reaches the UI. */
export function sanitizeSalesPipeline(board: SalesPipeline): SalesPipeline {
  const local = buildLocalSalesPipeline();
  const byId = new Map(
    [...local.active_customers, ...local.potential_customers].map((c) => [c.id, c]),
  );
  const fixCustomer = (c: PipelineCustomer): PipelineCustomer => {
    const fb = byId.get(c.id);
    if (!fb) {
      return {
        ...c,
        region: REGION_FA[c.region ?? ""] ?? c.region,
        pipeline_stage: STAGE_FA[c.pipeline_stage ?? ""] ?? c.pipeline_stage,
      };
    }
    return {
      ...c,
      name: isGarbled(c.name) ? fb.name : c.name,
      contact_person: isGarbled(c.contact_person) ? fb.contact_person : c.contact_person,
      notes: isGarbled(c.notes) ? fb.notes ?? undefined : c.notes,
      preferred_grades: c.preferred_grades?.length ? c.preferred_grades : fb.preferred_grades,
      region: REGION_FA[c.region ?? fb.region ?? ""] ?? c.region ?? fb.region,
      pipeline_stage:
        STAGE_FA[c.pipeline_stage ?? fb.pipeline_stage ?? ""] ?? c.pipeline_stage ?? fb.pipeline_stage,
    };
  };
  const active_customers = board.active_customers.map(fixCustomer);
  const potential_customers = board.potential_customers.map(fixCustomer);
  const purchase_queue = board.purchase_queue.map((q) => {
    const fb = byId.get(q.customer_id);
    return {
      ...q,
      customer_name: isGarbled(q.customer_name) ? fb?.name ?? q.customer_name : q.customer_name,
    };
  });
  return {
    ...board,
    active_customers,
    potential_customers,
    purchase_queue,
    summary: {
      ...board.summary,
      active_count: active_customers.length,
      potential_count: potential_customers.length,
      queue_items: purchase_queue.length,
    },
  };
}

export function resolveCustomerName(customerId?: string, fallback?: string): string {
  if (!customerId) return fallback ?? "—";
  const local = buildLocalSalesPipeline();
  const hit = [...local.active_customers, ...local.potential_customers].find((c) => c.id === customerId);
  return hit?.name ?? fallback ?? customerId;
}
