"""Grid vs generator source selection (PM-04)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Tariff:
    source: str
    price_irr_per_kwh: float
    peak_multiplier: float
    peak_hours_start: int
    peak_hours_end: int


def effective_price(tariff: Tariff, at: datetime) -> tuple[float, bool]:
    hour = at.hour
    in_peak = False
    if tariff.peak_hours_start != tariff.peak_hours_end:
        if tariff.peak_hours_start < tariff.peak_hours_end:
            in_peak = tariff.peak_hours_start <= hour < tariff.peak_hours_end
        else:
            in_peak = hour >= tariff.peak_hours_start or hour < tariff.peak_hours_end
    multiplier = tariff.peak_multiplier if in_peak else 1.0
    return tariff.price_irr_per_kwh * multiplier, in_peak


def choose_energy_source(
    tariffs: list[Tariff],
    *,
    expected_kwh: float,
    at: datetime | None = None,
) -> dict:
    at = at or datetime.now()
    priced: dict[str, tuple[float, bool]] = {}
    for tariff in tariffs:
        priced[tariff.source] = effective_price(tariff, at)

    if "grid" not in priced or "generator" not in priced:
        raise ValueError("Both grid and generator tariffs are required")

    grid_price, is_peak = priced["grid"]
    gen_price, _ = priced["generator"]
    recommended = "grid" if grid_price <= gen_price else "generator"
    alt = "generator" if recommended == "grid" else "grid"
    saving = abs(priced[alt][0] - priced[recommended][0]) * expected_kwh

    if recommended == "generator":
        reason = (
            f"Peak-hour grid tariff ({grid_price:.0f} IRR/kWh) exceeds generator "
            f"({gen_price:.0f}); prefer generator."
        )
    else:
        reason = (
            f"Grid ({grid_price:.0f} IRR/kWh) is cheaper than generator "
            f"({gen_price:.0f}); prefer grid."
        )

    return {
        "recommended_source": recommended,
        "grid_cost_irr_per_kwh": round(grid_price, 2),
        "generator_cost_irr_per_kwh": round(gen_price, 2),
        "expected_kwh": expected_kwh,
        "estimated_saving_irr": round(saving, 2),
        "is_peak": is_peak,
        "reason": reason,
        "decided_at": at.isoformat(),
    }
