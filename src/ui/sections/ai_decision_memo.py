"""AI Decision Memo dashboard section"""

import hashlib
import json
import os
import re
from typing import Callable

import pandas as pd
import streamlit as st


def render_ai_decision_memo(
    summary: pd.DataFrame,
    moves: pd.DataFrame,
    business_name: str,
    dataset_name: str,
    currency: str,
    cost_basis: str,
    cost_is_assumption: bool,
    capabilities: dict,
    generate_memo_pdf: Callable[..., bytes],
) -> None:
    """Render, cache, display, and download the AI decision memo"""

    st.header("AI Decision Memo")

    metadata = {
        "business_name": business_name,
        "dataset_name": dataset_name,
        "currency": currency,
        "cost_basis": cost_basis,
        "cost_is_assumption": cost_is_assumption,
        "available_analysis": [
            name
            for name, available in capabilities.items()
            if available
        ],
    }

    # Create a stable fingerprint of the memo inputs
    # Changing the dataset, settings, or analysis results
    # invalidates the previously generated memo
    memo_context = {
        "metadata": metadata,
        "capabilities": capabilities,
        "summary": summary.to_json(
            orient="records",
            date_format="iso",
        ),
        "moves": moves.to_json(
            orient="records",
            date_format="iso",
        ),
    }

    context_bytes = json.dumps(
        memo_context,
        sort_keys=True,
        default=str,
    ).encode("utf-8")

    context_id = hashlib.sha256(context_bytes).hexdigest()

    # Initialize Streamlit session state
    if "generated_memo" not in st.session_state:
        st.session_state.generated_memo = None

    if "generated_memo_context" not in st.session_state:
        st.session_state.generated_memo_context = None

    # Clear outdated memos when the inputs change
    if st.session_state.generated_memo_context != context_id:
        st.session_state.generated_memo = None
        st.session_state.generated_memo_context = None

    # Check Anthropic API configuration
    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.warning(
            "No ANTHROPIC_API_KEY is configured. "
            "All deterministic analytics still work; "
            "only memo generation is disabled."
        )

    else:
        # Generate or regenerate the memo
        if st.button(
            "Generate decision memo",
            type="primary",
        ):
            try:
                from agent import generate_menu_memo

                with st.spinner(
                    "Generating memo from computed results..."
                ):
                    memo = generate_menu_memo(
                        summary,
                        moves,
                        metadata=metadata,
                        capabilities=capabilities,
                    )

                # Persist the memo across Streamlit reruns
                st.session_state.generated_memo = memo
                st.session_state.generated_memo_context = context_id

                st.success(
                    "AI decision memo generated successfully!"
                )

            except Exception as exc:
                st.error(
                    "Could not generate the AI memo. "
                    "The analytics above are unaffected."
                )
                st.code(str(exc))

    # --------------------------------------------------
    # Display and download the generated memo
    # --------------------------------------------------
    if (
        st.session_state.generated_memo is not None
        and st.session_state.generated_memo_context == context_id
    ):
        memo = st.session_state.generated_memo

        st.markdown("### Decision Memo")

        # Escape dollar signs only for Streamlit display
        # Keep the original memo unchanged for downloads
        display_memo = memo.replace("$", r"**\$**")

        st.markdown(display_memo)

        st.divider()

        st.subheader("Download decision memo")

        # Make a safe filename from the business name
        safe_business_name = re.sub(
            r"[^A-Za-z0-9\_-]+",
            "_",
            business_name.strip(),
        ).strip("_") or "business"

        # Create three download columns
        download_col1, download_col2, download_col3 = (
            st.columns(3)
        )

        # Markdown download
        with download_col1:
            st.download_button(
                label="Download Markdown (.md)",
                data=memo.encode("utf-8"),
                file_name=(
                    f"{safe_business_name}_decision_memo.md"
                ),
                mime="text/markdown",
                width="stretch",
            )

        # Plain text download
        with download_col2:
            st.download_button(
                label="Download Text (.txt)",
                data=memo.encode("utf-8"),
                file_name=(
                    f"{safe_business_name}_decision_memo.txt"
                ),
                mime="text/plain",
                width="stretch",
            )

        # PDF download
        with download_col3:
            try:
                pdf_bytes = generate_memo_pdf(
                    memo=memo,
                    business_name=business_name,
                    dataset_name=dataset_name,
                )

                st.download_button(
                    label="Download PDF (.pdf)",
                    data=pdf_bytes,
                    file_name=(
                        f"{safe_business_name}_decision_memo.pdf"
                    ),
                    mime="application/pdf",
                    width="stretch",
                )

            except Exception as exc:
                st.error(f"Could not generate PDF: {exc}")

        st.caption(
            "This memo is AI-generated from the computed analysis. "
            "Verify all recommendations before making business decisions. "
            "Estimated costs and uncertain price elasticities "
            "should not be treated as confirmed results."
        )
