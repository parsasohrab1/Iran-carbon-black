"""Re-seed procurement Persian labels with UTF-8 (fixes ??? from Windows pipe encoding)."""

from __future__ import annotations

import json
import os

from sqlalchemy import create_engine, text

from shared.procurement_sources import MATERIAL_DB_NAMES, SUPPLIERS

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
        for s in SUPPLIERS:
            meta = {
                "city": s["city"],
                "province": s["province"],
                "type": s["type"],
                "materials": s["materials"],
                "payment_terms": s["payment_terms"],
                "notes_fa": s["notes_fa"],
            }
            conn.execute(
                text(
                    """
                    INSERT INTO supply.suppliers (id, name, rating, delivery_reliability, quality_rating, metadata)
                    VALUES (:id, :name, :rating, :rel, :qual, CAST(:meta AS jsonb))
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        rating = EXCLUDED.rating,
                        delivery_reliability = EXCLUDED.delivery_reliability,
                        quality_rating = EXCLUDED.quality_rating,
                        metadata = EXCLUDED.metadata
                    """
                ),
                {
                    "id": s["id"],
                    "name": s["name"],
                    "rating": s["rating"],
                    "rel": s["delivery_reliability"],
                    "qual": s["quality_rating"],
                    "meta": json.dumps(meta, ensure_ascii=False),
                },
            )

        # Remove garbled material labels (ASCII '?' heavy) then reinsert quotes
        conn.execute(
            text(
                """
                DELETE FROM supply.price_history
                WHERE material !~ '[آ-ی]'
                   OR material LIKE '%?%'
                """
            )
        )

        for mid, db_name in MATERIAL_DB_NAMES.items():
            # market series ~8 weeks
            for w in range(0, 9):
                base = {
                    "cbfs": (41000, 220),
                    "naphtha": (58000, 280),
                    "ethylene_tar": (37500, 180),
                    "anthracene_oil": (43000, 200),
                    "natural_gas": (17200, 90),
                }[mid]
                price = base[0] + w * base[1]
                conn.execute(
                    text(
                        """
                        INSERT INTO supply.price_history (time, material, price_irr, source)
                        VALUES (NOW() - ((:w)::text || ' weeks')::interval, :mat, :price, 'market')
                        """
                    ),
                    {"w": 8 - w, "mat": db_name, "price": price},
                )

        for s in SUPPLIERS:
            for mid, price in s["quotes_irr"].items():
                conn.execute(
                    text(
                        """
                        INSERT INTO supply.price_history (time, material, price_irr, source)
                        VALUES (NOW() - INTERVAL '1 day', :mat, :price, :sid)
                        """
                    ),
                    {"mat": MATERIAL_DB_NAMES[mid], "price": price, "sid": s["id"]},
                )

    print("procurement UTF-8 reseed OK")


if __name__ == "__main__":
    main()
