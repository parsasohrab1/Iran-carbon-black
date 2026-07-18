"""Re-seed export markets Persian labels with UTF-8."""

from __future__ import annotations

import os

from sqlalchemy import create_engine, text

from shared.export_markets import ACTUAL_MARKETS, POTENTIAL_MARKETS

DSN = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://icb_admin:change_me_strong_password@postgres:5432/carbon_black",
)


def main() -> None:
    raw = DSN
    if raw.startswith("postgresql://"):
        raw = raw.replace("postgresql://", "postgresql+psycopg2://", 1)
    elif "+psycopg://" in raw:
        raw = raw.replace("+psycopg://", "+psycopg2://", 1)
    engine = create_engine(raw)

    with engine.begin() as conn:
        for m in (*ACTUAL_MARKETS, *POTENTIAL_MARKETS):
            conn.execute(
                text(
                    """
                    INSERT INTO sales.export_markets (
                        id, country_fa, country_en, status, region, annual_tonnage_kg, ytd_tonnage_kg,
                        share_pct, main_grades, avg_fob_usd, growth_yoy_pct, buyers, logistics, risk,
                        pipeline_stage, probability, source_refs, updated_at
                    ) VALUES (
                        :id, :country_fa, :country_en, :status, :region, :annual_tonnage_kg, :ytd_tonnage_kg,
                        :share_pct, :main_grades, :avg_fob_usd, :growth_yoy_pct, :buyers, :logistics, :risk,
                        :pipeline_stage, :probability, :source_refs, NOW()
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        country_fa = EXCLUDED.country_fa,
                        country_en = EXCLUDED.country_en,
                        status = EXCLUDED.status,
                        region = EXCLUDED.region,
                        annual_tonnage_kg = EXCLUDED.annual_tonnage_kg,
                        ytd_tonnage_kg = EXCLUDED.ytd_tonnage_kg,
                        share_pct = EXCLUDED.share_pct,
                        main_grades = EXCLUDED.main_grades,
                        avg_fob_usd = EXCLUDED.avg_fob_usd,
                        growth_yoy_pct = EXCLUDED.growth_yoy_pct,
                        buyers = EXCLUDED.buyers,
                        logistics = EXCLUDED.logistics,
                        risk = EXCLUDED.risk,
                        pipeline_stage = EXCLUDED.pipeline_stage,
                        probability = EXCLUDED.probability,
                        source_refs = EXCLUDED.source_refs,
                        updated_at = NOW()
                    """
                ),
                {
                    "id": m["id"],
                    "country_fa": m["country_fa"],
                    "country_en": m.get("country_en"),
                    "status": m["status"],
                    "region": m.get("region"),
                    "annual_tonnage_kg": m["annual_tonnage_kg"],
                    "ytd_tonnage_kg": m["ytd_tonnage_kg"],
                    "share_pct": m.get("share_pct") or 0,
                    "main_grades": m.get("main_grades") or [],
                    "avg_fob_usd": m.get("avg_fob_usd"),
                    "growth_yoy_pct": m.get("growth_yoy_pct"),
                    "buyers": m.get("buyers"),
                    "logistics": m.get("logistics"),
                    "risk": m.get("risk"),
                    "pipeline_stage": m.get("pipeline_stage"),
                    "probability": m.get("probability"),
                    "source_refs": m.get("source_refs") or [],
                },
            )
    print("export markets UTF-8 reseed OK")


if __name__ == "__main__":
    main()
