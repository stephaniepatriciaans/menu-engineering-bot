"""Conservative, review-only labels for unusual POS item names/prices.

These rules never remove transactions or change monetary calculations.
"""

from __future__ import annotations

import math
import re

# A review threshold, not a statistical confidence limit. A 5.0 relative
# range means max price > 6x min price (more than 500% variation).
MAX_HIGH_CONFIDENCE_RELATIVE_PRICE_RANGE = 5.0

# These are review hints, not proof that a line is not merchandise.
_OPERATIONAL_LABELS = frozenset({
    "postage", "dotcom postage", "carriage", "manual", "discount",
    "adjust bad debt", "bank charges", "amazon fee", "shipping",
    "delivery charge", "service charge", "handling charge",
})


def possible_operational_charge(item_name: object) -> bool:
    """Flag specific known charge-like descriptions for human review."""
    normalized = re.sub(r"\s+", " ", str(item_name).casefold()).strip()
    return normalized in _OPERATIONAL_LABELS


def review_item_reliability(
    item_name: object,
    elasticity_source: object,
    elasticity_confidence: object,
    price_variation_pct: object,
) -> tuple[str, str, bool]:
    """Return display confidence, review reason, and charge-review flag.

    Only downgrades an *estimated* estimate. Existing priors remain Priors.
    No numerical elasticity, revenue, or demand fields are modified.
    """
    operational = possible_operational_charge(item_name)
    reasons: list[str] = []
    if operational:
        reasons.append("Charge-like description; verify whether this is merchandise")

    confidence = str(elasticity_confidence)
    if str(elasticity_source).casefold() == "estimated":
        try:
            variation = float(price_variation_pct)
        except (TypeError, ValueError):
            variation = math.nan
        if not math.isfinite(variation):
            reasons.append("Invalid price-variation evidence")
        elif variation > 100 * MAX_HIGH_CONFIDENCE_RELATIVE_PRICE_RANGE:
            reasons.append("Extreme historical price range (>500% variation)")
        if reasons:
            confidence = "Low"

    return confidence, "; ".join(reasons), operational
