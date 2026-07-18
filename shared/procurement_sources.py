"""Procurement sources and feedstock price board for Shokrban / Iran Carbon Black."""

from __future__ import annotations

from typing import Any

# Primary feedstocks used in furnace carbon black production
MATERIALS: list[dict[str, Any]] = [
    {
        "id": "cbfs",
        "name_fa": "قطران (فورفورال اکسترکت / CBFS)",
        "name_en": "Carbon Black Feedstock Oil (CBFS)",
        "unit": "ریال / کیلوگرم",
        "category": "خوراک اصلی",
        "criticality": "critical",
        "typical_share_pct": 62,
    },
    {
        "id": "naphtha",
        "name_fa": "نفتا",
        "name_en": "Naphtha",
        "unit": "ریال / کیلوگرم",
        "category": "خوراک مکمل",
        "criticality": "high",
        "typical_share_pct": 18,
    },
    {
        "id": "ethylene_tar",
        "name_fa": "تار اتیلن",
        "name_en": "Ethylene Tar",
        "unit": "ریال / کیلوگرم",
        "category": "خوراک جایگزین",
        "criticality": "medium",
        "typical_share_pct": 8,
    },
    {
        "id": "anthracene_oil",
        "name_fa": "روغن آنتراسن",
        "name_en": "Anthracene Oil",
        "unit": "ریال / کیلوگرم",
        "category": "خوراک جایگزین",
        "criticality": "medium",
        "typical_share_pct": 5,
    },
    {
        "id": "natural_gas",
        "name_fa": "گاز طبیعی (سوخت فرآیند)",
        "name_en": "Natural Gas",
        "unit": "ریال / مترمکعب",
        "category": "انرژی",
        "criticality": "high",
        "typical_share_pct": 7,
    },
]

# Purchase sources (suppliers) with offered materials and reference quotes (IRR)
SUPPLIERS: list[dict[str, Any]] = [
    {
        "id": "SUP-0012",
        "name": "پتروشیمی تبریز",
        "city": "تبریز",
        "province": "آذربایجان شرقی",
        "type": "پتروشیمی داخلی",
        "rating": 4.2,
        "delivery_reliability": 0.92,
        "quality_rating": 4.5,
        "lead_time_days": 7,
        "payment_terms": "۳۰ روزه",
        "materials": ["cbfs", "naphtha", "ethylene_tar"],
        "quotes_irr": {"cbfs": 42800, "naphtha": 61200, "ethylene_tar": 39500},
        "notes_fa": "تأمین‌کننده اصلی CBFS با پایداری تحویل بالا",
    },
    {
        "id": "SUP-0003",
        "name": "پالایشگاه اصفهان",
        "city": "اصفهان",
        "province": "اصفهان",
        "type": "پالایشگاه",
        "rating": 4.0,
        "delivery_reliability": 0.88,
        "quality_rating": 4.1,
        "lead_time_days": 10,
        "payment_terms": "۴۵ روزه",
        "materials": ["cbfs", "naphtha", "anthracene_oil"],
        "quotes_irr": {"cbfs": 42100, "naphtha": 59800, "anthracene_oil": 45200},
        "notes_fa": "گزینه رقابتی قیمت برای نفتا و روغن آنتراسن",
    },
    {
        "id": "SUP-0008",
        "name": "پتروشیمی بندر امام",
        "city": "ماهشهر",
        "province": "خوزستان",
        "type": "پتروشیمی داخلی",
        "rating": 3.8,
        "delivery_reliability": 0.85,
        "quality_rating": 4.0,
        "lead_time_days": 12,
        "payment_terms": "۳۰ روزه",
        "materials": ["cbfs", "ethylene_tar", "naphtha"],
        "quotes_irr": {"cbfs": 43500, "ethylene_tar": 38800, "naphtha": 60500},
        "notes_fa": "ظرفیت بالا؛ مناسب سفارش‌های حجیم",
    },
    {
        "id": "SUP-0015",
        "name": "پالایشگاه آبادان",
        "city": "آبادان",
        "province": "خوزستان",
        "type": "پالایشگاه",
        "rating": 3.9,
        "delivery_reliability": 0.83,
        "quality_rating": 3.9,
        "lead_time_days": 14,
        "payment_terms": "۶۰ روزه",
        "materials": ["cbfs", "anthracene_oil"],
        "quotes_irr": {"cbfs": 41900, "anthracene_oil": 44800},
        "notes_fa": "قیمت رقابتی CBFS؛ زمان تحویل طولانی‌تر",
    },
    {
        "id": "SUP-0021",
        "name": "پتروشیمی شازند اراک",
        "city": "اراک",
        "province": "مرکزی",
        "type": "پتروشیمی داخلی",
        "rating": 4.1,
        "delivery_reliability": 0.90,
        "quality_rating": 4.3,
        "lead_time_days": 8,
        "payment_terms": "۳۰ روزه",
        "materials": ["ethylene_tar", "naphtha"],
        "quotes_irr": {"ethylene_tar": 40200, "naphtha": 59100},
        "notes_fa": "منبع پایدار تار اتیلن و نفتا",
    },
    {
        "id": "SUP-0030",
        "name": "شرکت ملی گاز — منطقه ۳",
        "city": "اهواز",
        "province": "خوزستان",
        "type": "انرژی / گاز",
        "rating": 4.4,
        "delivery_reliability": 0.96,
        "quality_rating": 4.6,
        "lead_time_days": 1,
        "payment_terms": "قرارداد سالانه",
        "materials": ["natural_gas"],
        "quotes_irr": {"natural_gas": 18500},
        "notes_fa": "سوخت فرآیند کوره؛ قرارداد بلندمدت",
    },
    {
        "id": "SUP-0042",
        "name": "بازرگانی انرژی خلیج فارس",
        "city": "تهران",
        "province": "تهران",
        "type": "بازرگان / واردات",
        "rating": 3.6,
        "delivery_reliability": 0.78,
        "quality_rating": 3.7,
        "lead_time_days": 21,
        "payment_terms": "نقدی / ال‌سی",
        "materials": ["cbfs", "anthracene_oil"],
        "quotes_irr": {"cbfs": 44500, "anthracene_oil": 46800},
        "notes_fa": "پشتیبان اضطراری؛ حساس به نرخ ارز",
    },
]

# Map material display names used in DB price_history to catalog ids
MATERIAL_DB_NAMES: dict[str, str] = {
    "cbfs": "قطران (فورفورال اکسترکت)",
    "naphtha": "نفتا",
    "ethylene_tar": "تار اتیلن",
    "anthracene_oil": "روغن آنتراسن",
    "natural_gas": "گاز طبیعی (سوخت فرآیند)",
}


def build_static_price_board() -> dict[str, Any]:
    """Offline/fallback board when DB is empty."""
    materials = []
    for mat in MATERIALS:
        quotes = []
        for sup in SUPPLIERS:
            if mat["id"] in sup["quotes_irr"]:
                quotes.append(
                    {
                        "supplier_id": sup["id"],
                        "supplier_name": sup["name"],
                        "city": sup["city"],
                        "price_irr": sup["quotes_irr"][mat["id"]],
                        "lead_time_days": sup["lead_time_days"],
                        "rating": sup["rating"],
                    }
                )
        quotes.sort(key=lambda q: q["price_irr"])
        best = quotes[0] if quotes else None
        avg = round(sum(q["price_irr"] for q in quotes) / len(quotes), 0) if quotes else None
        materials.append(
            {
                **mat,
                "db_name": MATERIAL_DB_NAMES.get(mat["id"], mat["name_fa"]),
                "latest_price_irr": best["price_irr"] if best else None,
                "avg_market_irr": avg,
                "best_supplier": best,
                "change_pct_7d": None,
                "trend": "stable",
                "quotes": quotes,
                "price_source": "catalog",
            }
        )

    return {
        "source": "Shokrban procurement catalog + supplier quotes",
        "updated_label": "نرخ‌های مرجع تأمین (کاتالوگ)",
        "materials": materials,
        "suppliers": SUPPLIERS,
        "summary": {
            "supplier_count": len(SUPPLIERS),
            "material_count": len(MATERIALS),
            "critical_materials": sum(1 for m in MATERIALS if m["criticality"] == "critical"),
        },
    }
