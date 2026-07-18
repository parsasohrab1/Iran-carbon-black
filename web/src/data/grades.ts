/** Current production grades + ASTM quality sheet (mirrors shared/product_catalog.py). */

export type GradeSpec = {
  id: string;
  label_en: string;
  label_fa: string;
  unit: string;
  astm: string;
  spec: string;
  min?: number;
  max?: number;
  value?: number;
  tolerance?: number;
};

export type ProductGrade = {
  code: string;
  astm_code: string;
  trade_name: string;
  variant: string | null;
  classification: string;
  status: string;
  label_fa: string;
  description_fa: string;
  quality_specs: GradeSpec[];
};

export type CatalogResponse = {
  source?: string;
  count: number;
  products: ProductGrade[];
  comparison: Array<{
    id: string;
    label_fa: string;
    label_en: string;
    unit: string;
    astm: string;
    by_grade: Record<string, string>;
  }>;
  grade_codes: string[];
  classifications?: string[];
};

const PRODUCTS_META = [
  {
    code: "N-326",
    astm_code: "N326",
    trade_name: "HAF-LS",
    variant: "V-7",
    classification: "HAF",
    status: "in_production",
    label_fa: "دوده N-326 — HAF-LS (V-7)",
    description_fa: "گرید تقویت‌کننده با ساختار پایین (Low Structure) در خانواده HAF",
  },
  {
    code: "N-234",
    astm_code: "N234",
    trade_name: "ISAF-HM-HS",
    variant: "V-6",
    classification: "ISAF",
    status: "in_production",
    label_fa: "دوده N-234 — ISAF-HM-HS (V-6)",
    description_fa: "گرید ISAF با ساختار بالا / مدول بالا برای کاربردهای تقویتی سخت",
  },
  {
    code: "N-220",
    astm_code: "N220",
    trade_name: "ISAF-HM",
    variant: null,
    classification: "ISAF",
    status: "in_production",
    label_fa: "دوده N-220 — ISAF-HM",
    description_fa: "گرید ISAF استاندارد با مدول بالا؛ محصول اصلی تقویت تایر",
  },
  {
    code: "P-8201",
    astm_code: "P8201",
    trade_name: "ICJ I.C.C",
    variant: "V3",
    classification: "Specialty",
    status: "in_production",
    label_fa: "دوده ICJ P-8201 — I.C.C (V3)",
    description_fa: "گرید تخصصی ICJ / I.C.C برای کاربردهای ویژه صنعتی",
  },
  {
    code: "N-330-SV",
    astm_code: "N330",
    trade_name: "S-V",
    variant: "S-V",
    classification: "HAF",
    status: "in_production",
    label_fa: "دوده N-330 — S-V",
    description_fa: "گرید N-330 با مشخصات واریانت S-V",
  },
  {
    code: "N-660",
    astm_code: "N660",
    trade_name: "GPF S-SO",
    variant: "S-SO",
    classification: "GPF",
    status: "in_production",
    label_fa: "دوده N-660 — GPF (S-SO)",
    description_fa: "گرید GPF برای کاربردهای عمومی و پرکننده",
  },
  {
    code: "N-550-ICC",
    astm_code: "N550",
    trade_name: "FEF I.C.C S-SO",
    variant: "S-SO",
    classification: "FEF",
    status: "in_production",
    label_fa: "دوده N-550 — FEF I.C.C (S-SO)",
    description_fa: "گرید FEF با مشخصات I.C.C / S-SO",
  },
  {
    code: "N-550-VJ",
    astm_code: "N550",
    trade_name: "V-J",
    variant: "V-J",
    classification: "FEF",
    status: "in_production",
    label_fa: "دوده N-550 — V-J",
    description_fa: "گرید N-550 با واریانت V-J",
  },
  {
    code: "N-375",
    astm_code: "N375",
    trade_name: "HAF-HS",
    variant: "V-M",
    classification: "HAF",
    status: "in_production",
    label_fa: "دوده N-375 — HAF-HS (V-M)",
    description_fa: "گرید HAF با ساختار بالا (High Structure)",
  },
  {
    code: "N-339",
    astm_code: "N339",
    trade_name: "HAF-HS",
    variant: "V-3",
    classification: "HAF",
    status: "in_production",
    label_fa: "دوده N-339 — HAF-HS (V-3)",
    description_fa: "گرید HAF-HS استاندارد برای تایر و قطعات لاستیکی",
  },
  {
    code: "N-330",
    astm_code: "N330",
    trade_name: "HAF",
    variant: null,
    classification: "HAF",
    status: "in_production",
    label_fa: "دوده N-330 — HAF",
    description_fa: "گرید HAF کلاسیک N-330؛ پرکاربرد در صنعت تایر",
  },
] as const;

const SPEC_ROWS: Array<{
  id: string;
  label_en: string;
  label_fa: string;
  unit: string;
  astm: string;
  values: string[];
}> = [
  {
    id: "iodine_no",
    label_en: "Iodine No.",
    label_fa: "عدد ید",
    unit: "mg/g",
    astm: "D-1510",
    values: [
      "77 / 87",
      "115 / 125",
      "116 / 126",
      "25 / 35",
      "75 / 90",
      "31 / 41",
      "38 / 48",
      "40 / 50",
      "85 / 95",
      "85 / 95",
      "77 / 87",
    ],
  },
  {
    id: "oil_absorption_dbp",
    label_en: "Oil Absorption Number (DBP)",
    label_fa: "جذب روغن (DBP)",
    unit: "ml/100g",
    astm: "D-2414",
    values: [
      "67 / 77",
      "120 / 130",
      "109 / 119",
      "95.0 / 110.0",
      "95 / 110",
      "85 / 95",
      "116 / 126",
      "110 / 125",
      "109 / 119",
      "115 / 125",
      "97 / 107",
    ],
  },
  {
    id: "tint_strength",
    label_en: "Tint Strength",
    label_fa: "قدرت رنگ‌دهی",
    unit: "%IRB#3",
    astm: "D-3265",
    values: [
      "106 / 116",
      "118 / 128",
      "111 / 121",
      "99.0 / 109.0",
      "99 / 109",
      "52 / 65",
      "58 / 68",
      "58 / 68",
      "109 / 119",
      "106 / 116",
      "99 / 109",
    ],
  },
  {
    id: "pour_density",
    label_en: "Pour Density",
    label_fa: "چگالی ریزشی",
    unit: "Kg/m³",
    astm: "D-1513",
    values: [
      "455 ± 20",
      "320 ± 20",
      "355 ± 20",
      "350 / 375",
      "350 / 375",
      "440 ± 20",
      "360 ± 20",
      "330 / 355",
      "345 ± 20",
      "345 ± 20",
      "380 ± 20",
    ],
  },
  {
    id: "toluene_discoloration",
    label_en: "Toluene Solvent Discoloration",
    label_fa: "تغییر رنگ حلال تولوئن",
    unit: "T%",
    astm: "D-1618",
    values: [
      "MIN 85",
      "MIN 85",
      "MIN 85",
      "MIN 90",
      "MIN 90",
      "MIN 75",
      "MIN 75",
      "MIN 80",
      "MIN 85",
      "MIN 85",
      "MIN 85",
    ],
  },
  {
    id: "ph",
    label_en: "pH",
    label_fa: "pH",
    unit: "—",
    astm: "D-1512",
    values: [
      "7.5 – 9",
      "7.5 – 9",
      "7.5 – 9",
      "6.0 – 10.0",
      "6.0 – 10.0",
      "7.5 – 9",
      "7.5 – 9",
      "6.0 – 10.0",
      "7.5 – 9",
      "7.5 – 9",
      "7.5 – 9",
    ],
  },
  {
    id: "fines_content",
    label_en: "Fines Content",
    label_fa: "محتوای ذرات ریز",
    unit: "%",
    astm: "D-1508",
    values: [
      "MAX 10",
      "MAX 10",
      "MAX 10",
      "MAX 10",
      "MAX 15.0",
      "MAX 10",
      "MAX 10",
      "MAX 15.0",
      "MAX 10",
      "MAX 10",
      "MAX 10",
    ],
  },
  {
    id: "heating_loss",
    label_en: "Heating Loss",
    label_fa: "افت حرارتی",
    unit: "%",
    astm: "D-1509",
    values: [
      "MAX 1",
      "MAX 1",
      "MAX 1",
      "MAX 0.5",
      "MAX 0.5",
      "MAX 1",
      "MAX 1",
      "MAX 0.5",
      "MAX 1",
      "MAX 1",
      "MAX 1",
    ],
  },
  {
    id: "sieve_residue_325",
    label_en: "Sieve Residue 325 Mesh",
    label_fa: "باقیمانده الک ۳۲۵ مش",
    unit: "ppm",
    astm: "D-1514",
    values: [
      "MAX 1000",
      "MAX 1000",
      "MAX 1000",
      "MAX 150",
      "MAX 200",
      "MAX 1000",
      "MAX 1000",
      "MAX 150",
      "MAX 1000",
      "MAX 1000",
      "MAX 1000",
    ],
  },
  {
    id: "ash",
    label_en: "Ash",
    label_fa: "خاکستر",
    unit: "%",
    astm: "D-1506",
    values: [
      "MAX 0.75",
      "MAX 0.75",
      "MAX 0.75",
      "MAX 0.15",
      "MAX 0.30",
      "MAX 0.75",
      "MAX 0.75",
      "MAX 0.30",
      "MAX 0.75",
      "MAX 0.75",
      "MAX 0.75",
    ],
  },
  {
    id: "sulfur",
    label_en: "Sulfur",
    label_fa: "گوگرد",
    unit: "%",
    astm: "D-1619",
    values: [
      "MAX 2.0",
      "MAX 2.0",
      "MAX 2.0",
      "MAX 0.15",
      "MAX 1.0",
      "MAX 2.0",
      "MAX 2.0",
      "MAX 1.0",
      "MAX 2.0",
      "MAX 2.0",
      "MAX 2.0",
    ],
  },
  {
    id: "n2_surface_area",
    label_en: "N₂ Surface Area",
    label_fa: "سطح ویژه نیتروژن",
    unit: "m²/g",
    astm: "D-6556",
    values: [
      "73 / 83",
      "114 / 124",
      "109 / 119",
      "73.0 / 85.0",
      "71 / 86",
      "30 / 40",
      "35 / 45",
      "37 / 47",
      "88 / 98",
      "86 / 96",
      "73 / 83",
    ],
  },
  {
    id: "pellet_hardness_avg",
    label_en: "Individual Pellet Hardness — Average (20 pellets)",
    label_fa: "سختی پلت — میانگین (۲۰ پلت)",
    unit: "gf",
    astm: "D-3313",
    values: [
      "10 / 40",
      "10 / 40",
      "10 / 40",
      "10 / 50",
      "10 / 40",
      "10 / 40",
      "10 / 40",
      "10 / 40",
      "10 / 40",
      "10 / 40",
      "10 / 40",
    ],
  },
  {
    id: "pellet_hardness_max",
    label_en: "Individual Pellet Hardness — Maximum (20 pellets)",
    label_fa: "سختی پلت — حداکثر (۲۰ پلت)",
    unit: "gf",
    astm: "D-3313",
    values: Array(11).fill("50"),
  },
];

export function buildLocalCatalog(): CatalogResponse {
  const products: ProductGrade[] = PRODUCTS_META.map((product, idx) => ({
    ...product,
    quality_specs: SPEC_ROWS.map((row) => ({
      id: row.id,
      label_en: row.label_en,
      label_fa: row.label_fa,
      unit: row.unit,
      astm: row.astm,
      spec: row.values[idx],
    })),
  }));

  return {
    source: "Shokrban current production quality specification sheets",
    count: products.length,
    products,
    comparison: SPEC_ROWS.map((row) => ({
      id: row.id,
      label_fa: row.label_fa,
      label_en: row.label_en,
      unit: row.unit,
      astm: row.astm,
      by_grade: Object.fromEntries(PRODUCTS_META.map((p, i) => [p.code, row.values[i]])),
    })),
    grade_codes: PRODUCTS_META.map((p) => p.code),
    classifications: [...new Set(PRODUCTS_META.map((p) => p.classification))].sort(),
  };
}
