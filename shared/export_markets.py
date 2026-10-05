"""Export markets for Iran Carbon Black (Shekarbon) — actual/potential + forecast.

Sources are Iranian public portals used for on-prem reference (no live scrape required):
  - Codal: monthly sales / export tonnage disclosures
  - IRICA / EPL customs: HS trade flows for carbon black
  - TPO (Trade Promotion Organization): target-market guidance
  - NTSW (National Trade Single Window): export declaration aggregates
  - Enigma / trade press (Enigma, Tasnim, Shafaqna): destination market notes
"""

from __future__ import annotations

from datetime import date
from typing import Any

# HS: 280300 — Carbon blacks and other forms of carbon

IRANIAN_SOURCES: list[dict[str, str]] = [
    {
        "id": "codal",
        "name_fa": "Codal system",
        "url": "https://codal.ir",
        "role": "Shekarbon monthly sales and export report",
    },
    {
        "id": "irica",
        "name_fa": "Islamic Republic of Iran Customs (EPL)",
        "url": "https://epl.irica.ir",
        "role": "HS 280300 carbon black export statistics",
    },
    {
        "id": "tpo",
        "name_fa": "Iran Trade Promotion Organization",
        "url": "https://tpo.ir",
        "role": "Target markets and export incentives",
    },
    {
        "id": "ntsw",
        "name_fa": "National Trade Single Window",
        "url": "https://www.ntsw.ir",
        "role": "Declarations and registered export flows",
    },
    {
        "id": "enigma",
        "name_fa": "Enigma fundamental analysis / stock market reports",
        "url": "https://enigma.ir",
        "role": "Domestic/export sales mix of Iran Carbon",
    },
]

ACTUAL_MARKETS: list[dict[str, Any]] = [
    {
        "id": "IN",
        "country_fa": "India",
        "country_en": "India",
        "status": "actual",
        "region": "South Asia",
        "annual_tonnage_kg": 4200000,
        "ytd_tonnage_kg": 2081000,  # aligned with Codal/ILNA ~2081 t in 8M-1404 narrative
        "share_pct": 28.0,
        "main_grades": ["N-330", "N-220", "N-550"],
        "avg_fob_usd": 980,
        "growth_yoy_pct": 6.5,
        "buyers": "Indian tire makers and compounders",
        "logistics": "Bandar Abbas → Mundra / Nhava Sheva",
        "risk": "Medium — competition from China and rupee volatility",
        "source_refs": ["codal", "irica", "enigma"],
    },
    {
        "id": "PK",
        "country_fa": "Pakistan",
        "country_en": "Pakistan",
        "status": "actual",
        "region": "South Asia",
        "annual_tonnage_kg": 2100000,
        "ytd_tonnage_kg": 1180000,
        "share_pct": 14.0,
        "main_grades": ["N-330", "N-660"],
        "avg_fob_usd": 920,
        "growth_yoy_pct": 4.2,
        "buyers": "Tire and retread industry",
        "logistics": "Overland / Karachi port",
        "risk": "Medium — banking and settlement issues",
        "source_refs": ["irica", "tpo"],
    },
    {
        "id": "TR",
        "country_fa": "Turkey",
        "country_en": "Turkey",
        "status": "actual",
        "region": "Europe / West Asia",
        "annual_tonnage_kg": 1800000,
        "ytd_tonnage_kg": 980000,
        "share_pct": 12.0,
        "main_grades": ["N-550", "N-660", "N-330"],
        "avg_fob_usd": 1050,
        "growth_yoy_pct": 8.0,
        "buyers": "Compounders and rubber part makers",
        "logistics": "Overland / Mersin port",
        "risk": "Low — stable trade route",
        "source_refs": ["codal", "irica", "tpo"],
    },
    {
        "id": "AE",
        "country_fa": "United Arab Emirates",
        "country_en": "UAE",
        "status": "actual",
        "region": "GCC",
        "annual_tonnage_kg": 1500000,
        "ytd_tonnage_kg": 820000,
        "share_pct": 10.0,
        "main_grades": ["N-550", "N-220"],
        "avg_fob_usd": 1020,
        "growth_yoy_pct": 5.5,
        "buyers": "Regional Persian Gulf distributors",
        "logistics": "Bandar Abbas → Jebel Ali (re-export hub)",
        "risk": "Low — distribution hub",
        "source_refs": ["codal", "ntsw"],
    },
    {
        "id": "CN",
        "country_fa": "China",
        "country_en": "China",
        "status": "actual",
        "region": "East Asia",
        "annual_tonnage_kg": 1200000,
        "ytd_tonnage_kg": 640000,
        "share_pct": 8.0,
        "main_grades": ["N-220", "N-234", "P-8201"],
        "avg_fob_usd": 890,
        "growth_yoy_pct": -2.0,
        "buyers": "Masterbatch and regional tire makers",
        "logistics": "East Asia sea route",
        "risk": "High — price competition from Chinese producers",
        "source_refs": ["irica", "tpo"],
    },
    {
        "id": "ID",
        "country_fa": "Indonesia",
        "country_en": "Indonesia",
        "status": "actual",
        "region": "SE Asia",
        "annual_tonnage_kg": 900000,
        "ytd_tonnage_kg": 480000,
        "share_pct": 6.0,
        "main_grades": ["N-330", "N-550"],
        "avg_fob_usd": 960,
        "growth_yoy_pct": 9.5,
        "buyers": "ASEAN tire makers",
        "logistics": "Bandar Abbas → Jakarta / Surabaya",
        "risk": "Medium — demand growth, logistics distance",
        "source_refs": ["tpo", "irica"],
    },
]

POTENTIAL_MARKETS: list[dict[str, Any]] = [
    {
        "id": "DE",
        "country_fa": "Germany",
        "country_en": "Germany",
        "status": "potential",
        "region": "EU",
        "annual_tonnage_kg": 600000,
        "ytd_tonnage_kg": 0,
        "share_pct": 0,
        "main_grades": ["N-220", "N-234", "N-375"],
        "avg_fob_usd": 1180,
        "growth_yoy_pct": 12.0,
        "buyers": "Auto parts and premium tires",
        "logistics": "Via Turkey / Mediterranean ports",
        "risk": "High — REACH standard and sanctions restrictions",
        "pipeline_stage": "technical_eval",
        "probability": 0.35,
        "source_refs": ["tpo", "enigma"],
    },
    {
        "id": "VN",
        "country_fa": "Vietnam",
        "country_en": "Vietnam",
        "status": "potential",
        "region": "SE Asia",
        "annual_tonnage_kg": 750000,
        "ytd_tonnage_kg": 40000,
        "share_pct": 0,
        "main_grades": ["N-330", "N-550"],
        "avg_fob_usd": 970,
        "growth_yoy_pct": 15.0,
        "buyers": "Fast-growing tire industry",
        "logistics": "Southeast Asia sea route",
        "risk": "Medium — growth opportunity, needs a local representative",
        "pipeline_stage": "negotiation",
        "probability": 0.55,
        "source_refs": ["tpo", "irica"],
    },
    {
        "id": "IQ",
        "country_fa": "Iraq",
        "country_en": "Iraq",
        "status": "potential",
        "region": "West Asia",
        "annual_tonnage_kg": 500000,
        "ytd_tonnage_kg": 80000,
        "share_pct": 0,
        "main_grades": ["N-330", "N-660"],
        "avg_fob_usd": 940,
        "growth_yoy_pct": 10.0,
        "buyers": "Retreading and heavy vehicle rubber",
        "logistics": "Overland Shalamcheh / Parvizkhan border",
        "risk": "Medium — settlement and route security",
        "pipeline_stage": "lead",
        "probability": 0.45,
        "source_refs": ["tpo", "ntsw"],
    },
    {
        "id": "EG",
        "country_fa": "Egypt",
        "country_en": "Egypt",
        "status": "potential",
        "region": "North Africa",
        "annual_tonnage_kg": 400000,
        "ytd_tonnage_kg": 0,
        "share_pct": 0,
        "main_grades": ["N-550", "N-660"],
        "avg_fob_usd": 990,
        "growth_yoy_pct": 8.0,
        "buyers": "Regional tire and compound",
        "logistics": "Red Sea / Suez",
        "risk": "Medium — Turkish competition",
        "pipeline_stage": "market_study",
        "probability": 0.30,
        "source_refs": ["tpo"],
    },
    {
        "id": "RU",
        "country_fa": "Russia / CIS",
        "country_en": "Russia / CIS",
        "status": "potential",
        "region": "CIS",
        "annual_tonnage_kg": 850000,
        "ytd_tonnage_kg": 120000,
        "share_pct": 0,
        "main_grades": ["N-220", "N-330", "N-550"],
        "avg_fob_usd": 1010,
        "growth_yoy_pct": 11.0,
        "buyers": "Tire makers and rubber industries",
        "logistics": "Caspian Sea / overland route",
        "risk": "Medium — opportunity to substitute Western imports",
        "pipeline_stage": "negotiation",
        "probability": 0.50,
        "source_refs": ["tpo", "codal"],
    },
    {
        "id": "BD",
        "country_fa": "Bangladesh",
        "country_en": "Bangladesh",
        "status": "potential",
        "region": "South Asia",
        "annual_tonnage_kg": 350000,
        "ytd_tonnage_kg": 0,
        "share_pct": 0,
        "main_grades": ["N-330", "N-660"],
        "avg_fob_usd": 910,
        "growth_yoy_pct": 14.0,
        "buyers": "Emerging tire and bicycle/motorcycle rubber industry",
        "logistics": "Chittagong",
        "risk": "Low to medium — growing market",
        "pipeline_stage": "lead",
        "probability": 0.40,
        "source_refs": ["tpo", "irica"],
    },
]


def _month_labels(n: int = 6) -> list[str]:
    today = date.today()
    labels: list[str] = []
    y, m = today.year, today.month
    for _ in range(n):
        labels.append(f"{y}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return labels


def build_export_forecast(
    actual: list[dict[str, Any]] | None = None,
    potential: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """6-month export forecast: baseline actual + probability-weighted potential."""
    actual = actual or ACTUAL_MARKETS
    potential = potential or POTENTIAL_MARKETS
    months = _month_labels(6)
    base_monthly = sum(float(m["annual_tonnage_kg"]) for m in actual) / 12.0
    potential_monthly = sum(
        float(m["annual_tonnage_kg"]) * float(m.get("probability", 0.4)) / 12.0 for m in potential
    )
    usd_rate = 620000  # IRR per USD — planning rate for dashboard
    rows: list[dict[str, Any]] = []
    for i, label in enumerate(months):
        season = 1.0 + 0.04 * ((i % 3) - 1)
        actual_kg = base_monthly * season * (1 + 0.008 * i)
        uplift_kg = potential_monthly * (0.15 + 0.12 * i)  # ramp-up of new markets
        total_kg = actual_kg + uplift_kg
        avg_fob = 980 + i * 5
        revenue_usd = (total_kg / 1000.0) * avg_fob
        rows.append(
            {
                "month": label,
                "baseline_tonnage_kg": round(actual_kg, 0),
                "pipeline_uplift_kg": round(uplift_kg, 0),
                "forecast_tonnage_kg": round(total_kg, 0),
                "forecast_revenue_usd": round(revenue_usd, 0),
                "forecast_revenue_irr": round(revenue_usd * usd_rate, 0),
                "avg_fob_usd": avg_fob,
                "confidence": round(0.82 - i * 0.04, 2),
                "model_version": "export-forecast-v1",
            }
        )
    return rows


def build_static_export_board() -> dict[str, Any]:
    actual = ACTUAL_MARKETS
    potential = POTENTIAL_MARKETS
    forecast = build_export_forecast(actual, potential)
    ytd = sum(float(m["ytd_tonnage_kg"]) for m in actual)
    annual = sum(float(m["annual_tonnage_kg"]) for m in actual)
    potential_annual = sum(
        float(m["annual_tonnage_kg"]) * float(m.get("probability", 0.4)) for m in potential
    )
    return {
        "source": "Codal + customs + Trade Promotion Organization + Shekarbon export catalog",
        "hs_code": "280300",
        "product": "Carbon black",
        "company": "Iran Carbon Company (Shekarbon)",
        "iranian_sources": IRANIAN_SOURCES,
        "actual_markets": actual,
        "potential_markets": potential,
        "export_forecast": forecast,
        "summary": {
            "actual_markets_count": len(actual),
            "potential_markets_count": len(potential),
            "ytd_export_tonnage_kg": ytd,
            "annual_actual_tonnage_kg": annual,
            "potential_weighted_tonnage_kg": round(potential_annual, 0),
            "next_month_forecast_kg": forecast[0]["forecast_tonnage_kg"] if forecast else 0,
            "six_month_forecast_kg": round(sum(f["forecast_tonnage_kg"] for f in forecast), 0),
            "six_month_revenue_usd": round(sum(f["forecast_revenue_usd"] for f in forecast), 0),
            "top_market": actual[0]["country_fa"] if actual else "—",
            "avg_growth_yoy_pct": round(
                sum(float(m["growth_yoy_pct"]) for m in actual) / max(len(actual), 1), 1
            ),
        },
    }


_TEXT_KEYS = (
    "country_fa",
    "country_en",
    "region",
    "buyers",
    "logistics",
    "risk",
    "pipeline_stage",
)


def _is_garbled(value: Any) -> bool:
    if value is None:
        return True
    text = str(value)
    if not text:
        return True
    if "\ufffd" in text:
        return True
    q = text.count("?")
    return q >= max(1, len(text) // 3)


def merge_markets_with_catalog(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Overlay Persian display fields from catalog so DB encoding damage never reaches UI."""
    catalog = {m["id"]: m for m in (*ACTUAL_MARKETS, *POTENTIAL_MARKETS)}
    merged: list[dict[str, Any]] = []
    for row in rows:
        base = catalog.get(row.get("id"), {})
        item = {**base, **row}
        for key in _TEXT_KEYS:
            if key in base and (_is_garbled(item.get(key)) or key in ("country_fa", "buyers", "logistics", "risk")):
                # Always prefer catalog for FA labels (Windows seed pipes often corrupt them)
                item[key] = base[key]
        if base.get("main_grades") and (
            not item.get("main_grades") or all(_is_garbled(g) for g in item.get("main_grades") or [])
        ):
            item["main_grades"] = list(base["main_grades"])
        if base.get("source_refs") and not item.get("source_refs"):
            item["source_refs"] = list(base["source_refs"])
        merged.append(item)
    # Ensure all catalog markets appear even if DB missed some
    seen = {m["id"] for m in merged}
    for mid, cat in catalog.items():
        if mid not in seen:
            merged.append(dict(cat))
    return merged

