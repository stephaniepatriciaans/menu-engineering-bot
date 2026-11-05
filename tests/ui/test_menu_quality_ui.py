"""Part 5 UI test using Streamlit mocks only."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd

from ui.menu_quality import render_menu_quality


def test_panel_skips_when_item_mapping_is_missing():
    raw = pd.DataFrame({"something": [1, 2]})
    with patch("ui.menu_quality.st") as st:
        render_menu_quality(raw, {"item": None})
        st.info.assert_called_once()
        st.expander.assert_not_called()


def test_panel_does_not_modify_input_and_exports_review():
    raw = pd.DataFrame({"item": [" Tea", "TEA"], "price": [3.0, 3.5]})
    before = raw.copy(deep=True)
    with patch("ui.menu_quality.st") as st:
        st.expander.return_value.__enter__ = MagicMock()
        st.expander.return_value.__exit__ = MagicMock(return_value=False)
        st.selectbox.return_value = None
        st.file_uploader.return_value = None
        st.columns.return_value = [MagicMock() for _ in range(4)]
        render_menu_quality(raw, {"item": "item", "price": "price"})
        st.download_button.assert_called_once()
    pd.testing.assert_frame_equal(raw, before)
