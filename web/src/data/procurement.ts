/** Offline fallback for procurement price board (mirrors shared/procurement_sources.py). */

export type SupplierQuote = {
  supplier_id: string;
  supplier_name: string;
  city: string;
  price_irr: number;
  lead_time_days?: number | null;
  rating?: number | null;
  quoted_at?: string | null;
};

export type ProcurementMaterial = {
  id: string;
  name_fa: string;
  name_en: string;
  unit: string;
  category: string;
  criticality: string;
  typical_share_pct: number;
  db_name?: string;
  latest_price_irr?: number | null;
  avg_market_irr?: number | null;
  best_supplier?: SupplierQuote | null;
  change_pct_7d?: number | null;
  trend?: string;
  quotes: SupplierQuote[];
  price_source?: string;
  market_as_of?: string | null;
  forecast?: {
    predicted_price_irr: number;
    trend: string;
    recommendation: string;
    confidence?: number | null;
  };
};

export type ProcurementSupplier = {
  id: string;
  name: string;
  city: string;
  province: string;
  type: string;
  rating: number;
  delivery_reliability: number;
  quality_rating: number;
  lead_time_days: number;
  payment_terms: string;
  materials: string[];
  quotes_irr: Record<string, number>;
  notes_fa: string;
};

export type ProcurementBoard = {
  source?: string;
  updated_label?: string;
  generated_at?: string;
  materials: ProcurementMaterial[];
  suppliers: ProcurementSupplier[];
  summary?: {
    supplier_count: number;
    material_count: number;
    critical_materials: number;
    best_cbfs?: SupplierQuote | null;
  };
};

const SUPPLIERS: ProcurementSupplier[] = [
  {
    id: "SUP-0012",
    name: "پتروشیمی تبریز",
    city: "تبریز",
    province: "آذربایجان شرقی",
    type: "پتروشیمی داخلی",
    rating: 4.2,
    delivery_reliability: 0.92,
    quality_rating: 4.5,
    lead_time_days: 7,
    payment_terms: "۳۰ روزه",
    materials: ["cbfs", "naphtha", "ethylene_tar"],
    quotes_irr: { cbfs: 42800, naphtha: 61200, ethylene_tar: 39500 },
    notes_fa: "تأمین‌کننده اصلی CBFS با پایداری تحویل بالا",
  },
  {
    id: "SUP-0003",
    name: "پالایشگاه اصفهان",
    city: "اصفهان",
    province: "اصفهان",
    type: "پالایشگاه",
    rating: 4.0,
    delivery_reliability: 0.88,
    quality_rating: 4.1,
    lead_time_days: 10,
    payment_terms: "۴۵ روزه",
    materials: ["cbfs", "naphtha", "anthracene_oil"],
    quotes_irr: { cbfs: 42100, naphtha: 59800, anthracene_oil: 45200 },
    notes_fa: "گزینه رقابتی قیمت برای نفتا و روغن آنتراسن",
  },
  {
    id: "SUP-0008",
    name: "پتروشیمی بندر امام",
    city: "ماهشهر",
    province: "خوزستان",
    type: "پتروشیمی داخلی",
    rating: 3.8,
    delivery_reliability: 0.85,
    quality_rating: 4.0,
    lead_time_days: 12,
    payment_terms: "۳۰ روزه",
    materials: ["cbfs", "ethylene_tar", "naphtha"],
    quotes_irr: { cbfs: 43500, ethylene_tar: 38800, naphtha: 60500 },
    notes_fa: "ظرفیت بالا؛ مناسب سفارش‌های حجیم",
  },
  {
    id: "SUP-0015",
    name: "پالایشگاه آبادان",
    city: "آبادان",
    province: "خوزستان",
    type: "پالایشگاه",
    rating: 3.9,
    delivery_reliability: 0.83,
    quality_rating: 3.9,
    lead_time_days: 14,
    payment_terms: "۶۰ روزه",
    materials: ["cbfs", "anthracene_oil"],
    quotes_irr: { cbfs: 41900, anthracene_oil: 44800 },
    notes_fa: "قیمت رقابتی CBFS؛ زمان تحویل طولانی‌تر",
  },
  {
    id: "SUP-0021",
    name: "پتروشیمی شازند اراک",
    city: "اراک",
    province: "مرکزی",
    type: "پتروشیمی داخلی",
    rating: 4.1,
    delivery_reliability: 0.9,
    quality_rating: 4.3,
    lead_time_days: 8,
    payment_terms: "۳۰ روزه",
    materials: ["ethylene_tar", "naphtha"],
    quotes_irr: { ethylene_tar: 40200, naphtha: 59100 },
    notes_fa: "منبع پایدار تار اتیلن و نفتا",
  },
  {
    id: "SUP-0030",
    name: "شرکت ملی گاز — منطقه ۳",
    city: "اهواز",
    province: "خوزستان",
    type: "انرژی / گاز",
    rating: 4.4,
    delivery_reliability: 0.96,
    quality_rating: 4.6,
    lead_time_days: 1,
    payment_terms: "قرارداد سالانه",
    materials: ["natural_gas"],
    quotes_irr: { natural_gas: 18500 },
    notes_fa: "سوخت فرآیند کوره؛ قرارداد بلندمدت",
  },
  {
    id: "SUP-0042",
    name: "بازرگانی انرژی خلیج فارس",
    city: "تهران",
    province: "تهران",
    type: "بازرگان / واردات",
    rating: 3.6,
    delivery_reliability: 0.78,
    quality_rating: 3.7,
    lead_time_days: 21,
    payment_terms: "نقدی / ال‌سی",
    materials: ["cbfs", "anthracene_oil"],
    quotes_irr: { cbfs: 44500, anthracene_oil: 46800 },
    notes_fa: "پشتیبان اضطراری؛ حساس به نرخ ارز",
  },
];

const MATERIAL_META = [
  {
    id: "cbfs",
    name_fa: "قطران (فورفورال اکسترکت / CBFS)",
    name_en: "Carbon Black Feedstock Oil (CBFS)",
    unit: "ریال / کیلوگرم",
    category: "خوراک اصلی",
    criticality: "critical",
    typical_share_pct: 62,
  },
  {
    id: "naphtha",
    name_fa: "نفتا",
    name_en: "Naphtha",
    unit: "ریال / کیلوگرم",
    category: "خوراک مکمل",
    criticality: "high",
    typical_share_pct: 18,
  },
  {
    id: "ethylene_tar",
    name_fa: "تار اتیلن",
    name_en: "Ethylene Tar",
    unit: "ریال / کیلوگرم",
    category: "خوراک جایگزین",
    criticality: "medium",
    typical_share_pct: 8,
  },
  {
    id: "anthracene_oil",
    name_fa: "روغن آنتراسن",
    name_en: "Anthracene Oil",
    unit: "ریال / کیلوگرم",
    category: "خوراک جایگزین",
    criticality: "medium",
    typical_share_pct: 5,
  },
  {
    id: "natural_gas",
    name_fa: "گاز طبیعی (سوخت فرآیند)",
    name_en: "Natural Gas",
    unit: "ریال / مترمکعب",
    category: "انرژی",
    criticality: "high",
    typical_share_pct: 7,
  },
];

export function buildLocalProcurementBoard(): ProcurementBoard {
  const materials: ProcurementMaterial[] = MATERIAL_META.map((mat) => {
    const quotes: SupplierQuote[] = SUPPLIERS.filter((s) => mat.id in s.quotes_irr)
      .map((s) => ({
        supplier_id: s.id,
        supplier_name: s.name,
        city: s.city,
        price_irr: s.quotes_irr[mat.id],
        lead_time_days: s.lead_time_days,
        rating: s.rating,
      }))
      .sort((a, b) => a.price_irr - b.price_irr);
    const best = quotes[0] ?? null;
    const avg = quotes.length
      ? Math.round(quotes.reduce((sum, q) => sum + q.price_irr, 0) / quotes.length)
      : null;
    return {
      ...mat,
      latest_price_irr: best?.price_irr ?? null,
      avg_market_irr: avg,
      best_supplier: best,
      change_pct_7d: null,
      trend: "stable",
      quotes,
      price_source: "catalog",
    };
  });

  return {
    source: "Shokrban procurement catalog + supplier quotes",
    updated_label: "نرخ‌های مرجع تأمین (کاتالوگ آفلاین)",
    materials,
    suppliers: SUPPLIERS,
    summary: {
      supplier_count: SUPPLIERS.length,
      material_count: materials.length,
      critical_materials: materials.filter((m) => m.criticality === "critical").length,
      best_cbfs: materials.find((m) => m.id === "cbfs")?.best_supplier ?? null,
    },
  };
}

/** Encoding-safe FA labels (Unicode escapes) — never trust DB/API/Windows pipes for these. */
const SUPPLIER_FA: Record<string, { name: string; city: string }> = {
  "SUP-0012": { name: "\u067E\u062A\u0631\u0648\u0634\u06CC\u0645\u06CC\u0020\u062A\u0628\u0631\u06CC\u0632", city: "\u062A\u0628\u0631\u06CC\u0632" },
  "SUP-0003": { name: "\u067E\u0627\u0644\u0627\u06CC\u0634\u06AF\u0627\u0647\u0020\u0627\u0635\u0641\u0647\u0627\u0646", city: "\u0627\u0635\u0641\u0647\u0627\u0646" },
  "SUP-0008": { name: "\u067E\u062A\u0631\u0648\u0634\u06CC\u0645\u06CC\u0020\u0628\u0646\u062F\u0631\u0020\u0627\u0645\u0627\u0645", city: "\u0645\u0627\u0647\u0634\u0647\u0631" },
  "SUP-0015": { name: "\u067E\u0627\u0644\u0627\u06CC\u0634\u06AF\u0627\u0647\u0020\u0622\u0628\u0627\u062F\u0627\u0646", city: "\u0622\u0628\u0627\u062F\u0627\u0646" },
  "SUP-0021": { name: "\u067E\u062A\u0631\u0648\u0634\u06CC\u0645\u06CC\u0020\u0634\u0627\u0632\u0646\u062F\u0020\u0627\u0631\u0627\u06A9", city: "\u0627\u0631\u0627\u06A9" },
  "SUP-0030": { name: "\u0634\u0631\u06A9\u062A\u0020\u0645\u0644\u06CC\u0020\u06AF\u0627\u0632\u0020\u2014\u0020\u0645\u0646\u0637\u0642\u0647\u0020\u06F3", city: "\u0627\u0647\u0648\u0627\u0632" },
  "SUP-0042": { name: "\u0628\u0627\u0632\u0631\u06AF\u0627\u0646\u06CC\u0020\u0627\u0646\u0631\u0698\u06CC\u0020\u062E\u0644\u06CC\u062C\u0020\u0641\u0627\u0631\u0633", city: "\u062A\u0647\u0631\u0627\u0646" },
};

/** Overlay Persian labels from offline catalog so ??? never reaches the UI. */
export function sanitizeProcurementBoard(board: ProcurementBoard): ProcurementBoard {
  const local = buildLocalProcurementBoard();
  const localSup = new Map(local.suppliers.map((s) => [s.id, s]));
  const localMat = new Map(local.materials.map((m) => [m.id, m]));

  const fixQuote = (q: SupplierQuote | null | undefined) => {
    if (!q) return q ?? null;
    const fa = SUPPLIER_FA[q.supplier_id];
    return {
      ...q,
      supplier_name: fa?.name ?? resolveSupplierName(q.supplier_id, q.supplier_name),
      city: fa?.city ?? resolveSupplierCity(q.supplier_id, q.city),
    };
  };

  const suppliers = board.suppliers.map((s) => {
    const fa = SUPPLIER_FA[s.id];
    const fallback = localSup.get(s.id);
    return {
      ...s,
      name: fa?.name ?? fallback?.name ?? s.name,
      city: fa?.city ?? fallback?.city ?? s.city,
      province: fallback?.province ?? s.province,
      type: fallback?.type ?? s.type,
      payment_terms: fallback?.payment_terms ?? s.payment_terms,
      notes_fa: fallback?.notes_fa ?? s.notes_fa,
    };
  });

  const materials = board.materials.map((m) => {
    const fallback = localMat.get(m.id);
    const quotes = (m.quotes ?? []).map((q) => fixQuote(q)!);
    return {
      ...m,
      name_fa: fallback?.name_fa ?? m.name_fa,
      unit: fallback?.unit ?? m.unit,
      category: fallback?.category ?? m.category,
      quotes,
      best_supplier: fixQuote(m.best_supplier),
    };
  });

  const bestCbfs =
    fixQuote(materials.find((m) => m.id === "cbfs")?.best_supplier) ??
    fixQuote(board.summary?.best_cbfs) ??
    local.summary?.best_cbfs ??
    null;

  return {
    ...board,
    updated_label: local.updated_label,
    source: board.source && !board.source.includes("?") ? board.source : local.source,
    suppliers,
    materials,
    summary: {
      ...board.summary,
      supplier_count: board.summary?.supplier_count ?? suppliers.length,
      material_count: board.summary?.material_count ?? materials.length,
      critical_materials:
        board.summary?.critical_materials ??
        materials.filter((m) => m.criticality === "critical").length,
      best_cbfs: bestCbfs,
    },
  };
}

/** Always resolve supplier display name from catalog by id (ignores garbled API text). */
export function resolveSupplierName(
  supplierId?: string | null,
  fallback?: string | null,
  _board?: ProcurementBoard | null,
): string {
  if (supplierId && SUPPLIER_FA[supplierId]) return SUPPLIER_FA[supplierId].name;
  if (supplierId) {
    const fromCatalog = SUPPLIERS.find((s) => s.id === supplierId)?.name;
    if (fromCatalog && !/[?]/.test(fromCatalog)) return fromCatalog;
  }
  if (fallback && !/[?]/.test(fallback)) return fallback;
  if (supplierId) return supplierId;
  return "\u2014";
}

export function resolveSupplierCity(
  supplierId?: string | null,
  fallback?: string | null,
  _board?: ProcurementBoard | null,
): string {
  if (supplierId && SUPPLIER_FA[supplierId]) return SUPPLIER_FA[supplierId].city;
  if (supplierId) {
    const fromCatalog = SUPPLIERS.find((s) => s.id === supplierId)?.city;
    if (fromCatalog && !/[?]/.test(fromCatalog)) return fromCatalog;
  }
  if (fallback && !/[?]/.test(fallback)) return fallback;
  return "\u2014";
}

export type MaterialWarehouseRisk = {
  material_id: string;
  name_fa: string;
  category: string;
  severity: "critical" | "high" | "medium" | "low";
  severity_fa: string;
  score: number;
  reason_fa: string;
  share_pct: number;
  lead_time_days: number | null;
  trend?: string;
};

const CRIT_SCORE: Record<string, number> = {
  critical: 55,
  high: 38,
  medium: 22,
  low: 10,
};

/** Rank raw-material warehouse / purchase risks by severity (highest first). */
export function rankMaterialWarehouseRisks(
  materials: ProcurementMaterial[],
  opts?: { feedstockPressure?: number },
): MaterialWarehouseRisk[] {
  const pressure = opts?.feedstockPressure ?? 1;
  return materials
    .map((m) => {
      const crit = CRIT_SCORE[m.criticality] ?? 18;
      const share = Number(m.typical_share_pct ?? 0);
      const lead = Number(m.best_supplier?.lead_time_days ?? 10);
      const change = Number(m.change_pct_7d ?? 0);
      const trendBoost =
        m.trend === "up" ? 18 : m.trend === "down" ? -4 : change > 3 ? 12 : change < -3 ? -3 : 0;
      const leadBoost = lead >= 18 ? 14 : lead >= 12 ? 8 : lead >= 7 ? 3 : 0;
      const shareBoost = share >= 50 ? 16 : share >= 15 ? 8 : share >= 7 ? 4 : 0;
      const pressureBoost = pressure > 1.15 ? 12 : pressure > 1.08 ? 6 : 0;
      const score = Math.max(5, Math.min(100, crit + shareBoost + leadBoost + trendBoost + pressureBoost));
      const severity: MaterialWarehouseRisk["severity"] =
        score >= 75 ? "critical" : score >= 55 ? "high" : score >= 35 ? "medium" : "low";
      const severity_fa =
        severity === "critical" ? "بحرانی" : severity === "high" ? "بالا" : severity === "medium" ? "متوسط" : "کم";
      const bits: string[] = [];
      if (m.criticality === "critical" || m.criticality === "high") bits.push("حیاتی برای خط");
      if (share >= 15) bits.push(`سهم ${Math.round(share)}٪ سبد`);
      if (lead >= 12) bits.push(`تحویل ${lead} روز`);
      if (m.trend === "up" || change > 3) bits.push("قیمت صعودی — ریسک انباشت/زمان خرید");
      if (pressure > 1.08) bits.push("فشار خوراک بازار");
      if (!bits.length) bits.push("پوشش عادی انبار");
      return {
        material_id: m.id,
        name_fa: m.name_fa,
        category: m.category,
        severity,
        severity_fa,
        score: Math.round(score),
        reason_fa: bits.join(" · "),
        share_pct: share,
        lead_time_days: m.best_supplier?.lead_time_days ?? null,
        trend: m.trend,
      };
    })
    .sort((a, b) => b.score - a.score || a.name_fa.localeCompare(b.name_fa, "fa"));
}

export function warehouseRiskTone(severity: string): "danger" | "warn" | "ok" | "neutral" {
  if (severity === "critical" || severity === "بحرانی") return "danger";
  if (severity === "high" || severity === "بالا") return "warn";
  if (severity === "medium" || severity === "متوسط") return "warn";
  if (severity === "low" || severity === "کم") return "ok";
  return "neutral";
}

