"""Re-seed sales CRM customers with UTF-8 Persian labels."""

from __future__ import annotations

import json
import os

from sqlalchemy import create_engine, text

from shared.sales_pipeline import ACTIVE_CUSTOMERS, POTENTIAL_CUSTOMERS, QUEUE_SEED

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
        for c in (*ACTIVE_CUSTOMERS, *POTENTIAL_CUSTOMERS):
            conn.execute(
                text(
                    """
                    INSERT INTO sales.customers (
                        id, name, segment, industry, annual_consumption_kg, region, status,
                        monthly_tonnage_kg, contact_person, notes
                    ) VALUES (
                        :id, :name, :segment, :industry, :annual, :region, :status,
                        :monthly, :contact, :notes
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        segment = EXCLUDED.segment,
                        industry = COALESCE(EXCLUDED.industry, sales.customers.industry),
                        annual_consumption_kg = EXCLUDED.annual_consumption_kg,
                        region = EXCLUDED.region,
                        status = EXCLUDED.status,
                        monthly_tonnage_kg = EXCLUDED.monthly_tonnage_kg,
                        contact_person = EXCLUDED.contact_person,
                        notes = COALESCE(EXCLUDED.notes, sales.customers.notes)
                    """
                ),
                {
                    "id": c["id"],
                    "name": c["name"],
                    "segment": c.get("segment"),
                    "industry": c.get("segment"),
                    "annual": c.get("annual_consumption_kg"),
                    "region": c.get("region"),
                    "status": c.get("status", "active"),
                    "monthly": c.get("monthly_tonnage_kg"),
                    "contact": c.get("contact_person"),
                    "notes": c.get("notes"),
                },
            )
            conn.execute(
                text(
                    """
                    INSERT INTO sales.customer_profiles (customer_id, preferred_grades, churn_risk, lifetime_value_irr, needs)
                    VALUES (:id, CAST(:grades AS jsonb), :churn, :ltv, CAST(:needs AS jsonb))
                    ON CONFLICT (customer_id) DO UPDATE SET
                        preferred_grades = EXCLUDED.preferred_grades,
                        needs = COALESCE(EXCLUDED.needs, sales.customer_profiles.needs)
                    """
                ),
                {
                    "id": c["id"],
                    "grades": json.dumps(c.get("preferred_grades") or []),
                    "churn": 0.12 if c.get("status") == "active" else 0.35,
                    "ltv": float(c.get("annual_consumption_kg") or 0) * 180000 * 0.4,
                    "needs": json.dumps({"stage": c.get("pipeline_stage")} if c.get("pipeline_stage") else {}),
                },
            )

        # Refresh purchase queue names via customer join is enough; still re-insert seed rows if empty
        n = conn.execute(text("SELECT COUNT(*) FROM sales.purchase_queue")).scalar() or 0
        if int(n) == 0:
            for item in QUEUE_SEED:
                conn.execute(
                    text(
                        """
                        INSERT INTO sales.purchase_queue (
                            customer_id, grade, requested_tonnage_kg, priority, status, probability, unit_price_irr
                        ) VALUES (
                            :customer_id, :grade, :ton, :priority, :status, :prob, :price
                        )
                        """
                    ),
                    {
                        "customer_id": item["customer_id"],
                        "grade": item["grade"],
                        "ton": item["requested_tonnage_kg"],
                        "priority": item["priority"],
                        "status": item["status"],
                        "prob": item["probability"],
                        "price": item["unit_price_irr"],
                    },
                )

    print("sales pipeline UTF-8 reseed OK")


if __name__ == "__main__":
    main()
