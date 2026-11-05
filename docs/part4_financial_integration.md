# Part 4 — Audited POS Financial Integration

This release adds independently audited **pre-tax item-sales** figures alongside the existing sales-only pricing research. It never guesses which item or date a standalone refund belongs to.

## 1. Upload and configure

In **Data Setup**, upload a supported POS CSV and map unit price, quantity, item, date, category, optional unit cost, transaction status, and signed line amount. Set price basis to `listed` or `realized` according to the POS provider's documented convention.

In **Data Quality → Advanced POS discount & sales reconciliation**:

1. Map per-unit/order discount and order ID columns when present. Select the documented stacking rule; do not infer it.
2. Confirm the provider's price/status/discount conventions with the checkbox.
3. Check **Compare with an independent POS settlement summary**.
4. Map a unique **transaction event ID** (not merely a repeated order ID).
5. Choose `separate_signed_events` only when refunds are distinct negative entries, and `pre_tax_sales` only when signed amounts exclude tax, tip, service fees and tenders.
6. Enter an independently produced **pre-tax net item-sales summary for the full uploaded export**. The audited integration unlocks only when signed sale amounts, distinct negative refunds, row classifications and the independently entered total agree **to the cent**.

The included example `data/synthetic/part4_audited_demo.csv` uses expected net `15.00`. It has two eligible sale rows ($25), a $10 negative refund event, and one cancelled event. The example demonstrates the calculation but cannot establish the convention of any real provider.

## 2. Analytics

When matched, the top-level dashboard shows **full-export audited net item sales**, **filtered eligible sales**, and an eligible-sales contribution estimate. Under **Audited POS Financials**, review eligible revenue and contribution by item, category, day and hour, and popularity/margin quadrants.

**Crucial scope:**

- Full-export audited net sales includes signed refund events and always covers the **whole** uploaded file. It does not change when category/date filters change.
- Filtered item, category, day and hour values represent **eligible sales before refunds**. Refunds are not assigned to dates, items or costs. Filtered eligible sales must **never** be described as filtered net sales.
- Unit cost and contribution profit are derived from supplied costs or explicit cost assumptions; the POS settlement does **not** independently validate costs. No total net contribution profit is claimed.
- Eligibility is joined by original unique CSV row indices after validation and filtering. Missing, duplicated or changed row identities block integration.
- Existing historical pricing, elasticity and model evaluation remain clearly labeled as **legacy sales-only research**. A reconciliation of observed revenue does not establish regular menu-list prices or causal price elasticity, so coupon-adjusted prices are not fed into price-move simulations automatically.
- Without an independently matched audit, the old dashboard remains in place and audited financial sections stay locked.

## 3. Reports

The **Reports** tab offers separately downloadable deterministic audited financial appendices (`.txt` and `.pdf`) only for a matched audit. It explicitly separates full-export net sales from filtered eligible-sales analytics and labels cost assumptions and missing refund attribution. The existing AI memo and original PDF still use historical sales-only pricing data and are **not** certified by the POS financial audit.

## 4. Validation

Run:

```bash
python3 -m ruff check src tests scripts
PYTHONPATH=src python3 -m pytest -q
python3 -m compileall -q src
PYTHONPATH=src python3 -m streamlit run src/app.py
```

The full suite should increase by 23 tests from 468 to 491 when this patch is applied to that verified baseline. Real-provider validation still requires real anonymized exports with separately generated POS sales reports.
