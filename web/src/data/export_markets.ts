/** Offline/static fallback for carbon black export markets board. */

export type IranianSource = {
  id: string;
  name_fa: string;
  url: string;
  role: string;
};

export type ExportMarket = {
  id: string;
  country_fa: string;
  country_en?: string;
  status: "actual" | "potential" | string;
  region?: string;
  annual_tonnage_kg: number;
  ytd_tonnage_kg: number;
  share_pct?: number;
  main_grades?: string[];
  avg_fob_usd?: number;
  growth_yoy_pct?: number;
  buyers?: string;
  logistics?: string;
  risk?: string;
  pipeline_stage?: string;
  probability?: number;
  source_refs?: string[];
};

export type ExportForecastRow = {
  month: string;
  baseline_tonnage_kg: number;
  pipeline_uplift_kg: number;
  forecast_tonnage_kg: number;
  forecast_revenue_usd: number;
  forecast_revenue_irr: number;
  avg_fob_usd: number;
  confidence: number;
  model_version?: string;
};

export type ExportBoard = {
  source?: string;
  hs_code?: string;
  product?: string;
  company?: string;
  iranian_sources: IranianSource[];
  actual_markets: ExportMarket[];
  potential_markets: ExportMarket[];
  export_forecast: ExportForecastRow[];
  summary: {
    actual_markets_count: number;
    potential_markets_count: number;
    ytd_export_tonnage_kg: number;
    annual_actual_tonnage_kg: number;
    potential_weighted_tonnage_kg: number;
    next_month_forecast_kg: number;
    six_month_forecast_kg: number;
    six_month_revenue_usd: number;
    top_market: string;
    avg_growth_yoy_pct: number;
  };
};

const SOURCES: IranianSource[] = [
  { id: "codal", name_fa: "سامانه کدال", url: "https://codal.ir", role: "گزارش ماهانه فروش و صادرات شکربن" },
  { id: "irica", name_fa: "گمرک جمهوری اسلامی ایران (EPL)", url: "https://epl.irica.ir", role: "آمار صادرات HS 280300" },
  { id: "tpo", name_fa: "سازمان توسعه تجارت ایران", url: "https://tpo.ir", role: "بازارهای هدف صادراتی" },
  { id: "ntsw", name_fa: "سامانه جامع تجارت", url: "https://www.ntsw.ir", role: "اظهارنامه‌های صادراتی" },
  { id: "enigma", name_fa: "تحلیل بنیادی انیگما", url: "https://enigma.ir", role: "ترکیب فروش داخلی/صادراتی" },
];

export function buildLocalExportBoard(): ExportBoard {
  const actual: ExportMarket[] = [
    {
      id: "IN",
      country_fa: "هند",
      country_en: "India",
      status: "actual",
      region: "South Asia",
      annual_tonnage_kg: 4200000,
      ytd_tonnage_kg: 2081000,
      share_pct: 28,
      main_grades: ["N-330", "N-220", "N-550"],
      avg_fob_usd: 980,
      growth_yoy_pct: 6.5,
      buyers: "تایرسازان و کامپاوندرهای هند",
      logistics: "بندرعباس → Mundra / Nhava Sheva",
      risk: "متوسط — رقابت چین و نوسان روپیه",
    },
    {
      id: "PK",
      country_fa: "پاکستان",
      country_en: "Pakistan",
      status: "actual",
      region: "South Asia",
      annual_tonnage_kg: 2100000,
      ytd_tonnage_kg: 1180000,
      share_pct: 14,
      main_grades: ["N-330", "N-660"],
      avg_fob_usd: 920,
      growth_yoy_pct: 4.2,
      buyers: "صنعت تایر و لاستیک بازسازی",
      logistics: "زمینی / بندر کراچی",
      risk: "متوسط — مسائل بانکی و تسویه",
    },
    {
      id: "TR",
      country_fa: "ترکیه",
      country_en: "Turkey",
      status: "actual",
      region: "Europe / West Asia",
      annual_tonnage_kg: 1800000,
      ytd_tonnage_kg: 980000,
      share_pct: 12,
      main_grades: ["N-550", "N-660", "N-330"],
      avg_fob_usd: 1050,
      growth_yoy_pct: 8,
      buyers: "کامپاوندر و قطعه‌سازان لاستیکی",
      logistics: "زمینی / بندر مرسین",
      risk: "کم — مسیر پایدار تجاری",
    },
    {
      id: "AE",
      country_fa: "امارات متحده عربی",
      country_en: "UAE",
      status: "actual",
      region: "GCC",
      annual_tonnage_kg: 1500000,
      ytd_tonnage_kg: 820000,
      share_pct: 10,
      main_grades: ["N-550", "N-220"],
      avg_fob_usd: 1020,
      growth_yoy_pct: 5.5,
      buyers: "توزیع‌کنندگان منطقه‌ای خلیج فارس",
      logistics: "بندرعباس → جبل علی (هاب ری‌اکسپورت)",
      risk: "کم — هاب توزیع",
    },
    {
      id: "CN",
      country_fa: "چین",
      country_en: "China",
      status: "actual",
      region: "East Asia",
      annual_tonnage_kg: 1200000,
      ytd_tonnage_kg: 640000,
      share_pct: 8,
      main_grades: ["N-220", "N-234", "P-8201"],
      avg_fob_usd: 890,
      growth_yoy_pct: -2,
      buyers: "مستربچ و تایرسازان منطقه‌ای",
      logistics: "دریایی شرق آسیا",
      risk: "بالا — رقابت قیمتی تولیدکنندگان چینی",
    },
    {
      id: "ID",
      country_fa: "اندونزی",
      country_en: "Indonesia",
      status: "actual",
      region: "SE Asia",
      annual_tonnage_kg: 900000,
      ytd_tonnage_kg: 480000,
      share_pct: 6,
      main_grades: ["N-330", "N-550"],
      avg_fob_usd: 960,
      growth_yoy_pct: 9.5,
      buyers: "تایرسازان ASEAN",
      logistics: "بندرعباس → Jakarta / Surabaya",
      risk: "متوسط — رشد تقاضا، فاصله لجستیکی",
    },
  ];

  const potential: ExportMarket[] = [
    {
      id: "VN",
      country_fa: "ویتنام",
      status: "potential",
      annual_tonnage_kg: 750000,
      ytd_tonnage_kg: 40000,
      main_grades: ["N-330", "N-550"],
      avg_fob_usd: 970,
      growth_yoy_pct: 15,
      probability: 0.55,
      pipeline_stage: "negotiation",
      risk: "متوسط — نیاز به نماینده محلی",
      buyers: "رشد سریع صنعت تایر",
    },
    {
      id: "RU",
      country_fa: "روسیه / CIS",
      status: "potential",
      annual_tonnage_kg: 850000,
      ytd_tonnage_kg: 120000,
      main_grades: ["N-220", "N-330", "N-550"],
      avg_fob_usd: 1010,
      growth_yoy_pct: 11,
      probability: 0.5,
      pipeline_stage: "negotiation",
      risk: "متوسط — فرصت جایگزینی واردات غربی",
      buyers: "تایرسازان و صنایع لاستیک",
    },
    {
      id: "DE",
      country_fa: "آلمان",
      status: "potential",
      annual_tonnage_kg: 600000,
      ytd_tonnage_kg: 0,
      main_grades: ["N-220", "N-234", "N-375"],
      avg_fob_usd: 1180,
      growth_yoy_pct: 12,
      probability: 0.35,
      pipeline_stage: "technical_eval",
      risk: "بالا — استاندارد REACH و محدودیت تحریم",
      buyers: "قطعات خودرو و تایر پرمیوم",
    },
    {
      id: "IQ",
      country_fa: "عراق",
      status: "potential",
      annual_tonnage_kg: 500000,
      ytd_tonnage_kg: 80000,
      main_grades: ["N-330", "N-660"],
      avg_fob_usd: 940,
      growth_yoy_pct: 10,
      probability: 0.45,
      pipeline_stage: "lead",
      risk: "متوسط — تسویه و امنیت مسیر",
      buyers: "بازسازی و لاستیک خودروهای سنگین",
    },
    {
      id: "EG",
      country_fa: "مصر",
      status: "potential",
      annual_tonnage_kg: 400000,
      ytd_tonnage_kg: 0,
      main_grades: ["N-550", "N-660"],
      avg_fob_usd: 990,
      growth_yoy_pct: 8,
      probability: 0.3,
      pipeline_stage: "market_study",
      risk: "متوسط — رقابت ترکیه",
      buyers: "تایر و کامپاند منطقه‌ای",
    },
    {
      id: "BD",
      country_fa: "بنگلادش",
      status: "potential",
      annual_tonnage_kg: 350000,
      ytd_tonnage_kg: 0,
      main_grades: ["N-330", "N-660"],
      avg_fob_usd: 910,
      growth_yoy_pct: 14,
      probability: 0.4,
      pipeline_stage: "lead",
      risk: "کم تا متوسط — بازار در حال رشد",
      buyers: "صنعت تایر نوپا و لاستیک دوچرخه/موتور",
    },
  ];

  const baseMonthly = actual.reduce((s, m) => s + m.annual_tonnage_kg, 0) / 12;
  const potMonthly =
    potential.reduce((s, m) => s + m.annual_tonnage_kg * (m.probability ?? 0.4), 0) / 12;
  const now = new Date();
  const forecast: ExportForecastRow[] = Array.from({ length: 6 }, (_, i) => {
    const d = new Date(now.getFullYear(), now.getMonth() + i, 1);
    const month = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    const season = 1 + 0.04 * ((i % 3) - 1);
    const baseline = baseMonthly * season * (1 + 0.008 * i);
    const uplift = potMonthly * (0.15 + 0.12 * i);
    const total = baseline + uplift;
    const fob = 980 + i * 5;
    const usd = (total / 1000) * fob;
    return {
      month,
      baseline_tonnage_kg: Math.round(baseline),
      pipeline_uplift_kg: Math.round(uplift),
      forecast_tonnage_kg: Math.round(total),
      forecast_revenue_usd: Math.round(usd),
      forecast_revenue_irr: Math.round(usd * 620000),
      avg_fob_usd: fob,
      confidence: Number((0.82 - i * 0.04).toFixed(2)),
      model_version: "export-forecast-v1",
    };
  });

  const ytd = actual.reduce((s, m) => s + m.ytd_tonnage_kg, 0);
  const annual = actual.reduce((s, m) => s + m.annual_tonnage_kg, 0);
  const potW = potential.reduce((s, m) => s + m.annual_tonnage_kg * (m.probability ?? 0.4), 0);

  return {
    source: "static export board — کدال / گمرک / سازمان توسعه تجارت",
    hs_code: "280300",
    product: "دوده صنعتی (Carbon Black)",
    company: "شرکت کربن ایران (شکربن)",
    iranian_sources: SOURCES,
    actual_markets: actual,
    potential_markets: potential,
    export_forecast: forecast,
    summary: {
      actual_markets_count: actual.length,
      potential_markets_count: potential.length,
      ytd_export_tonnage_kg: ytd,
      annual_actual_tonnage_kg: annual,
      potential_weighted_tonnage_kg: Math.round(potW),
      next_month_forecast_kg: forecast[0]?.forecast_tonnage_kg ?? 0,
      six_month_forecast_kg: Math.round(forecast.reduce((s, f) => s + f.forecast_tonnage_kg, 0)),
      six_month_revenue_usd: Math.round(forecast.reduce((s, f) => s + f.forecast_revenue_usd, 0)),
      top_market: actual[0]?.country_fa ?? "—",
      avg_growth_yoy_pct: Number(
        (actual.reduce((s, m) => s + (m.growth_yoy_pct ?? 0), 0) / Math.max(actual.length, 1)).toFixed(1),
      ),
    },
  };
}

function fixMarket(m: ExportMarket, fallback?: ExportMarket): ExportMarket {
  if (!fallback) return m;
  // Always prefer catalog Persian labels — DB/API encoding on Windows often corrupts FA text.
  return {
    ...m,
    country_fa: fallback.country_fa,
    country_en: fallback.country_en ?? m.country_en,
    buyers: fallback.buyers ?? m.buyers,
    logistics: fallback.logistics ?? m.logistics,
    risk: fallback.risk ?? m.risk,
    region: fallback.region ?? m.region,
  };
}

/** Overlay Persian labels from offline catalog so ??? never reaches the UI. */
export function sanitizeExportBoard(board: ExportBoard): ExportBoard {
  const local = buildLocalExportBoard();
  const byId = new Map(
    [...local.actual_markets, ...local.potential_markets].map((m) => [m.id, m]),
  );
  const actual_markets = board.actual_markets.map((m) => fixMarket(m, byId.get(m.id)));
  const potential_markets = board.potential_markets.map((m) => fixMarket(m, byId.get(m.id)));
  return {
    ...board,
    source: local.source,
    product: local.product ?? board.product,
    company: local.company ?? board.company,
    iranian_sources: local.iranian_sources,
    actual_markets,
    potential_markets,
    summary: {
      ...board.summary,
      top_market: actual_markets[0]?.country_fa ?? board.summary.top_market,
    },
  };
}
