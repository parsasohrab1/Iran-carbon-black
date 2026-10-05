"""Procurement sources and feedstock price board for Shokrban / Iran Carbon Black."""

from __future__ import annotations

from typing import Any

# Primary feedstocks used in furnace carbon black production
MATERIALS: list[dict[str, Any]] = [
    {
        "id": "cbfs",
        "name_fa": "Coal tar (furfural extract / CBFS)",
        "name_en": "Carbon Black Feedstock Oil (CBFS)",
        "unit": "rials / kg",
        "category": "Main feedstock",
        "criticality": "critical",
        "typical_share_pct": 62,
    },
    {
        "id": "naphtha",
        "name_fa": "Naphtha",
        "name_en": "Naphtha",
        "unit": "rials / kg",
        "category": "Supplementary feedstock",
        "criticality": "high",
        "typical_share_pct": 18,
    },
    {
        "id": "ethylene_tar",
        "name_fa": "Ethylene tar",
        "name_en": "Ethylene Tar",
        "unit": "rials / kg",
        "category": "Alternative feedstock",
        "criticality": "medium",
        "typical_share_pct": 8,
    },
    {
        "id": "anthracene_oil",
        "name_fa": "Anthracene oil",
        "name_en": "Anthracene Oil",
        "unit": "rials / kg",
        "category": "Alternative feedstock",
        "criticality": "medium",
        "typical_share_pct": 5,
    },
    {
        "id": "natural_gas",
        "name_fa": "Natural gas (process fuel)",
        "name_en": "Natural Gas",
        "unit": "rials / m³",
        "category": "Energy",
        "criticality": "high",
        "typical_share_pct": 7,
    },
]

# Purchase sources (suppliers) with offered materials and reference quotes (IRR)
SUPPLIERS: list[dict[str, Any]] = [
    {
        "id": "SUP-0012",
        "name": "Tabriz Petrochemical",
        "city": "Tabriz",
        "province": "East Azerbaijan",
        "type": "Domestic petrochemical",
        "rating": 4.2,
        "delivery_reliability": 0.92,
        "quality_rating": 4.5,
        "lead_time_days": 7,
        "payment_terms": "30 days",
        "materials": ["cbfs", "naphtha", "ethylene_tar"],
        "quotes_irr": {"cbfs": 42800, "naphtha": 61200, "ethylene_tar": 39500},
        "notes_fa": "Main CBFS supplier with high delivery reliability",
    },
    {
        "id": "SUP-0003",
        "name": "Isfahan Refinery",
        "city": "Isfahan",
        "province": "Isfahan",
        "type": "Refinery",
        "rating": 4.0,
        "delivery_reliability": 0.88,
        "quality_rating": 4.1,
        "lead_time_days": 10,
        "payment_terms": "45 days",
        "materials": ["cbfs", "naphtha", "anthracene_oil"],
        "quotes_irr": {"cbfs": 42100, "naphtha": 59800, "anthracene_oil": 45200},
        "notes_fa": "Price-competitive option for naphtha and anthracene oil",
    },
    {
        "id": "SUP-0008",
        "name": "Bandar Imam Petrochemical",
        "city": "Mahshahr",
        "province": "Khuzestan",
        "type": "Domestic petrochemical",
        "rating": 3.8,
        "delivery_reliability": 0.85,
        "quality_rating": 4.0,
        "lead_time_days": 12,
        "payment_terms": "30 days",
        "materials": ["cbfs", "ethylene_tar", "naphtha"],
        "quotes_irr": {"cbfs": 43500, "ethylene_tar": 38800, "naphtha": 60500},
        "notes_fa": "High capacity; suitable for bulk orders",
    },
    {
        "id": "SUP-0015",
        "name": "Abadan Refinery",
        "city": "Abadan",
        "province": "Khuzestan",
        "type": "Refinery",
        "rating": 3.9,
        "delivery_reliability": 0.83,
        "quality_rating": 3.9,
        "lead_time_days": 14,
        "payment_terms": "60 days",
        "materials": ["cbfs", "anthracene_oil"],
        "quotes_irr": {"cbfs": 41900, "anthracene_oil": 44800},
        "notes_fa": "Competitive CBFS price; longer delivery time",
    },
    {
        "id": "SUP-0021",
        "name": "Shazand Arak Petrochemical",
        "city": "Arak",
        "province": "Markazi",
        "type": "Domestic petrochemical",
        "rating": 4.1,
        "delivery_reliability": 0.90,
        "quality_rating": 4.3,
        "lead_time_days": 8,
        "payment_terms": "30 days",
        "materials": ["ethylene_tar", "naphtha"],
        "quotes_irr": {"ethylene_tar": 40200, "naphtha": 59100},
        "notes_fa": "Stable source of ethylene tar and naphtha",
    },
    {
        "id": "SUP-0030",
        "name": "National Gas Company — Region 3",
        "city": "Ahvaz",
        "province": "Khuzestan",
        "type": "Energy / Gas",
        "rating": 4.4,
        "delivery_reliability": 0.96,
        "quality_rating": 4.6,
        "lead_time_days": 1,
        "payment_terms": "Annual contract",
        "materials": ["natural_gas"],
        "quotes_irr": {"natural_gas": 18500},
        "notes_fa": "Furnace process fuel; long-term contract",
    },
    {
        "id": "SUP-0042",
        "name": "Persian Gulf Energy Trading",
        "city": "Tehran",
        "province": "Tehran",
        "type": "Trader / Importer",
        "rating": 3.6,
        "delivery_reliability": 0.78,
        "quality_rating": 3.7,
        "lead_time_days": 21,
        "payment_terms": "Cash / LC",
        "materials": ["cbfs", "anthracene_oil"],
        "quotes_irr": {"cbfs": 44500, "anthracene_oil": 46800},
        "notes_fa": "Emergency backup; sensitive to the exchange rate",
    },
]

# Map material display names used in DB price_history to catalog ids
MATERIAL_DB_NAMES: dict[str, str] = {
    "cbfs": "Coal tar (furfural extract)",
    "naphtha": "Naphtha",
    "ethylene_tar": "Ethylene tar",
    "anthracene_oil": "Anthracene oil",
    "natural_gas": "Natural gas (process fuel)",
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
        "updated_label": "Reference supply rates (catalog)",
        "materials": materials,
        "suppliers": SUPPLIERS,
        "summary": {
            "supplier_count": len(SUPPLIERS),
            "material_count": len(MATERIALS),
            "critical_materials": sum(1 for m in MATERIALS if m["criticality"] == "critical"),
        },
    }
