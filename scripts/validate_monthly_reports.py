"""Local CLI: validate aggregated monthly reports and save analysis to ignored data/local/."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from data_pipeline.monthly_report import (
    category_performance,
    item_performance,
    load_monthly_reports,
    monthly_overview,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/Indo_CoffeeShop"))
    parser.add_argument("--output", type=Path, default=Path("data/local/monthly_validation"))
    args = parser.parse_args()
    paths = sorted(args.input.glob("*.xlsx"))
    report = load_monthly_reports(paths)
    reports = {
        "audit.csv": report.audit,
        "monthly_overview.csv": monthly_overview(report.rows),
        "item_performance.csv": item_performance(report.rows),
        "category_performance.csv": category_performance(report.rows),
    }
    args.output.mkdir(parents=True, exist_ok=True)
    for name, table in reports.items():
        table.to_csv(args.output / name, index=False)
    print(f"Validated {len(report.rows):,} monthly summary rows across {len(paths)} workbooks")
    print(report.audit.to_string(index=False))
    print(f"Saved local summaries to {args.output} (ensure this path is gitignored)")


if __name__ == "__main__":
    main()
