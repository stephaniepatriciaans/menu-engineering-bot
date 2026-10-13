"""Reusable dataset capability reporting

This module describes which analyses are available and
how much evidence supports the elasticity estimates.

It does not calculate financial recommendations or
modify the input DataFrame.
"""

import pandas as pd


def capability_line(
    available: bool,
    label: str,
    reason: str = "",
) -> str:
    """Format one dataset capability as a readable status."""

    icon = "✓" if available else "✗"
    suffix = f" — {reason}" if reason else ""

    return f"{icon} {label}{suffix}"


def build_capability_report(
    summary: pd.DataFrame,
    capabilities: dict,
    cost_is_assumption: bool,
) -> list[str]:
    """Build a capability report from calculated analysis results."""

    total_items = len(summary)

    # Use actual summary values rather than hard-coded counts.
    if "elasticity_source" in summary.columns:
        sources = summary["elasticity_source"].fillna("")
    else:
        sources = pd.Series("", index=summary.index)

    estimated = sources.eq("estimated")

    estimated_count = int(estimated.sum())
    category_prior_count = int(
        sources.eq("category_prior").sum()
    )
    default_prior_count = int(
        sources.eq("default_prior").sum()
    )

    if "elasticity_confidence" in summary.columns:
        confidence = (
            summary["elasticity_confidence"]
            .fillna("")
            .astype(str)
            .str.lower()
        )
    else:
        confidence = pd.Series("", index=summary.index)

    low_confidence_count = int(
        (estimated & confidence.eq("low")).sum()
    )

    if estimated_count > 0:
        elasticity_reason = (
            f"{estimated_count} of {total_items} items estimated "
            f"({low_confidence_count} low confidence); "
            f"{category_prior_count} category priors, "
            f"{default_prior_count} default priors"
        )
    else:
        elasticity_reason = (
            f"No historical estimates among {total_items} items; "
            f"{category_prior_count} category priors, "
            f"{default_prior_count} default priors"
        )

    def has_capability(name: str) -> bool:
        """Safely interpret a capability flag."""
        return bool(capabilities.get(name, False))

    def cost_reason(enabled: bool, assumed_text: str) -> str:
        """Explain cost-dependent capabilities."""
        if not enabled:
            return "unit cost missing or incomplete"

        if cost_is_assumption:
            return assumed_text

        return ""

    return [
        capability_line(
            has_capability("revenue_analysis"),
            "Revenue analysis",
        ),
        capability_line(
            has_capability("popularity_analysis"),
            "Popularity analysis",
        ),
        capability_line(
            has_capability("sales_trend_analysis"),
            "Sales trend analysis",
        ),
        capability_line(
            has_capability("price_variation_analysis"),
            "Price variation analysis",
        ),
        capability_line(
            estimated_count > 0,
            "Historical elasticity estimation",
            elasticity_reason,
        ),
        capability_line(
            has_capability("profit_analysis"),
            "Profit analysis",
            cost_reason(
                has_capability("profit_analysis"),
                "cost is a scenario assumption",
            ),
        ),
        capability_line(
            has_capability("menu_engineering_quadrants"),
            "Menu Engineering Quadrants",
            cost_reason(
                has_capability("menu_engineering_quadrants"),
                "based on assumed costs",
            ),
        ),
        capability_line(
            has_capability("price_optimization"),
            "Profit-based price recommendations",
            cost_reason(
                has_capability("price_optimization"),
                "scenario only",
            ),
        ),
    ]
