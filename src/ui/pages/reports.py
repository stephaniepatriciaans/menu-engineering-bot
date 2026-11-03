"""Streamlit workflow module extracted from app.py."""

from __future__ import annotations

import pandas as pd

from reporting.pdf_report import generate_memo_pdf
from ui.pages.data_quality import QualityData
from ui.pages.data_setup import SetupData
from ui.sections.ai_decision_memo import render_ai_decision_memo
from ui.sidebar import SidebarSettings


def render_reports(
    setup: SetupData,
    quality: QualityData,
    settings: SidebarSettings,
    moves: pd.DataFrame,
) -> None:
    summary = quality.summary
    capabilities = quality.capabilities
    cost_basis = quality.cost_basis
    cost_is_assumption = quality.cost_is_assumption
    refund_candidates_df = quality.refund_candidates_df
    business_name = setup.business_name
    dataset_name = setup.dataset_name
    currency = settings.currency

    # 7. Generate AI decision memo
    # ================================================================
    render_ai_decision_memo(
        summary=summary,
        moves=moves,
        business_name=business_name,
        dataset_name=dataset_name,
        currency=currency,
        cost_basis=cost_basis,
        cost_is_assumption=cost_is_assumption,
        capabilities=capabilities,
        generate_memo_pdf=generate_memo_pdf,
        refund_candidate_count=len(refund_candidates_df),
    )
