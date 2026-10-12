import io
import sys
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ui.data_upload import load_uploaded_sales


def test_load_uploaded_sales():
    csv_content = (
        "item,price,units_sold\n"
        "Latte,5.50,2\n"
        "Mocha,6.00,3\n"
    )

    uploaded = io.BytesIO(csv_content.encode("utf-8"))
    uploaded.seek(5)

    actual_df, messages = load_uploaded_sales(uploaded)

    expected_df = pd.DataFrame({
        "item": ["Latte", "Mocha"],
        "price": [5.5, 6.0],
        "units_sold": [2, 3],
    })

    assert_frame_equal(actual_df, expected_df)
    assert isinstance(messages, list)


def test_upload_reader_resets_file_pointer():
    uploaded = io.BytesIO(
        b"item,price,units_sold\nLatte,5.50,2\n"
    )

    uploaded.seek(10)

    df, _ = load_uploaded_sales(uploaded)

    assert len(df) == 1
    assert df.loc[0, "item"] == "Latte"
