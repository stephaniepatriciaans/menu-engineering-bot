import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from pdf_report import generate_memo_pdf


def test_generate_pdf():
    memo = """
## Revenue Overview

**Latte** generated $12,500.00 in revenue.

## Recommendations

1. Review top-selling products.
2. Test prices before implementation.

- Elasticity estimates are uncertain.
"""

    pdf = generate_memo_pdf(
        memo=memo,
        business_name="Test Coffee Shop",
        dataset_name="Sample Sales Data",
    )

    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000