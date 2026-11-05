"""Compare an anonymized POS transaction export with its independent sales summary.

Example:
PYTHONPATH=src python3 scripts/validate_pos_export.py \
  --csv data/private/export.csv --expected-net 123.45 \
  --price-basis listed --refund-convention separate_signed_events \
  --amount-basis pre_tax_sales --event-id event_id \
  --status order_status --amount signed_line_amount --confirm-conventions

Exit codes: 0 matched, 2 review/mismatch, 1 invalid inputs.
"""

from __future__ import annotations

import argparse
import json

import pandas as pd

from pos.export_validation import audit_pos_export


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, help="Path to a local, anonymized transaction CSV")
    parser.add_argument("--expected-net", required=True, help="Independent POS pre-tax net item-sales summary")
    parser.add_argument("--price", default="price", help="Unit price column")
    parser.add_argument("--quantity", default="units_sold", help="Quantity column")
    parser.add_argument("--status", help="Transaction status column")
    parser.add_argument("--amount", required=True, help="Signed pre-tax, post-discount line amount column")
    parser.add_argument("--event-id", required=True, help="Unique transaction event identifier")
    parser.add_argument("--price-basis", choices=("unknown", "listed", "realized"), default="unknown")
    parser.add_argument(
        "--refund-convention",
        choices=("unknown", "separate_signed_events", "status_only_original"),
        default="unknown",
    )
    parser.add_argument("--amount-basis", choices=("unknown", "pre_tax_sales"), default="unknown")
    parser.add_argument("--confirm-conventions", action="store_true")
    parser.add_argument("--line-discount", help="Total fixed discount for this line")
    parser.add_argument("--percent", help="Line percentage discount")
    parser.add_argument("--per-unit-discount", help="Fixed discount per item unit")
    parser.add_argument("--order-id", help="Order ID used for coupon allocation")
    parser.add_argument("--order-discount", help="Total fixed coupon per order")
    parser.add_argument("--order-percent", help="Percentage coupon per order")
    parser.add_argument("--stacking", choices=("exclusive", "sequential"), default="exclusive")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        df = pd.read_csv(args.csv, dtype={args.event_id: "string"})
        if args.price == args.quantity:
            raise ValueError("Price and quantity columns must be distinct")
        for canonical, source in (("price", args.price), ("units_sold", args.quantity)):
            if source not in df.columns:
                raise ValueError(f"Missing column: {source}")
            if source != canonical and canonical in df.columns:
                raise ValueError(f"Cannot rename {source}: {canonical} already exists")
        df = df.rename(columns={args.price: "price", args.quantity: "units_sold"})
        audit = audit_pos_export(
            df,
            price_basis=args.price_basis,
            amount_column=args.amount,
            status_column=args.status,
            event_id_column=args.event_id,
            refund_convention=args.refund_convention,
            source_amount_basis=args.amount_basis,
            expected_net_sales=args.expected_net,
            verified_conventions=args.confirm_conventions,
            line_discount_column=args.line_discount,
            percent_column=args.percent,
            per_unit_discount_column=args.per_unit_discount,
            order_id_column=args.order_id,
            order_discount_column=args.order_discount,
            order_percent_column=args.order_percent,
            stacking=args.stacking,
        )
    except (OSError, ValueError, KeyError) as exc:
        print(f"Invalid export or accounting options: {exc}")
        return 1
    print(json.dumps(audit.as_dict(), indent=2))
    return 0 if audit.outcome == "matched" else 2


if __name__ == "__main__":
    raise SystemExit(main())
