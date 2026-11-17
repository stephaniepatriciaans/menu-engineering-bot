"""Deterministic business commentary on monthly aggregated menu sales.

No language model or external API is involved. All metrics come from monthly
report rows, which represent item-level summaries rather than transactions.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class BusinessInsight:
    """A data-grounded observation with its limits and a next check."""

    heading: str
    observation: str
    next_step: str
    kind: str = "observation"


def _idr(value: float) -> str:
    return f"Rp {value:,.0f}"


def _month(value: object, language: str) -> str:
    timestamp = pd.Timestamp(str(value))
    if language == "id":
        names = (
            "Januari", "Februari", "Maret", "April", "Mei", "Juni",
            "Juli", "Agustus", "September", "Oktober", "November", "Desember",
        )
        return f"{names[timestamp.month - 1]} {timestamp.year}"
    return timestamp.strftime("%b %Y")


def build_monthly_business_insights(
    rows: pd.DataFrame,
    *,
    language: str = "en",
    minimum_flagged_units: int = 100,
    near_zero_revenue_idr: float = 1_000,
) -> list[BusinessInsight]:
    """Explain recorded sales, volume and anomalies without inventing causes.

    Item comparisons preserve menu code, name, category and subcategory;
    channel entries may be combined for the exact same identity. 'Regular'
    items are only *candidates* selected by source category (BEVERAGE*, FOOD).
    A reported zero-value entry is never assumed to be a giveaway or fraud.
    """
    if language not in {"en", "id"}:
        raise ValueError("language must be 'en' or 'id'")
    if minimum_flagged_units < 1 or near_zero_revenue_idr < 0:
        raise ValueError("flag thresholds must be nonnegative (units >= 1)")

    needed = {
        "period_start", "Menu Code", "Menu", "Menu Category",
        "Menu Category Detail", "Qty", "Net Sales Total",
    }
    missing = needed.difference(rows.columns)
    if missing:
        raise ValueError(f"Missing monthly report fields: {sorted(missing)}")
    if rows.empty:
        return []

    work = rows.copy()
    work["period"] = pd.to_datetime(work["period_start"].astype(str)).dt.to_period("M")
    work["units"] = pd.to_numeric(work["Qty"], errors="raise")
    work["net_sales"] = pd.to_numeric(work["Net Sales Total"], errors="raise")
    monthly = (
        work.groupby("period", as_index=False)
        .agg(net_sales=("net_sales", "sum"), units=("units", "sum"))
        .sort_values("period")
        .reset_index(drop=True)
    )
    latest = monthly.iloc[-1]
    latest_period = latest["period"]
    latest_label = _month(latest_period.start_time, language)
    earlier = monthly.loc[monthly["period"] == latest_period - 1]
    results: list[BusinessInsight] = []
    id_lang = language == "id"

    if not earlier.empty:
        previous = earlier.iloc[0]
        previous_label = _month(previous["period"].start_time, language)
        prior_sales = float(previous["net_sales"])
        curr_sales = float(latest["net_sales"])
        unit_change = float(latest["units"]) - float(previous["units"])
        if prior_sales > 0:
            change_pct = 100 * (curr_sales - prior_sales) / prior_sales
            direction = ("naik" if change_pct > 0 else "turun" if change_pct < 0 else "tetap") if id_lang else ("increased" if change_pct > 0 else "decreased" if change_pct < 0 else "were unchanged")
            if id_lang:
                message = (
                    f"Penjualan bersih yang dilaporkan pada {latest_label} {direction} "
                    f"{abs(change_pct):.1f}% dibanding {previous_label}, dari "
                    f"{_idr(prior_sales)} menjadi {_idr(curr_sales)}. "
                    f"Perubahan jumlah unit tercatat: {unit_change:+,.0f}."
                )
                action = "Periksa promosi, ketersediaan menu, dan konteks operasional kedua bulan sebelum menyimpulkan penyebabnya."
            else:
                message = (
                    f"Reported net sales {direction} by {abs(change_pct):.1f}% "
                    f"in {latest_label} versus {previous_label}, from "
                    f"{_idr(prior_sales)} to {_idr(curr_sales)}. "
                    f"Change in recorded units: {unit_change:+,.0f}."
                )
                action = "Review promotions, item availability and operating context before attributing a cause."
            results.append(BusinessInsight(
                "Perubahan penjualan bulanan" if id_lang else "Month-over-month sales",
                message, action,
            ))
        else:
            results.append(BusinessInsight(
                "Perbandingan penjualan" if id_lang else "Sales comparison",
                "Persentase pertumbuhan tidak dihitung karena penjualan bersih bulan sebelumnya nol atau negatif." if id_lang else "Percentage growth is unavailable because the preceding month's net sales were zero or negative.",
                "Tinjau nilai laporan sumber." if id_lang else "Review the source-reported values.",
                "caution",
            ))
    else:
        results.append(BusinessInsight(
            "Perbandingan penjualan" if id_lang else "Sales comparison",
            f"Tidak tersedia laporan bulan tepat sebelum {latest_label}; perubahan bulanan tidak dihitung." if id_lang else f"No report for the month immediately before {latest_label}; no month-over-month growth is calculated.",
            "Unggah laporan bulan sebelumnya untuk perbandingan yang tepat." if id_lang else "Upload the immediately preceding month to compare reliably.",
            "caution",
        ))

    categories_upper = work["Menu Category"].fillna("").astype(str).str.strip().str.upper()
    candidate_mask = categories_upper.str.startswith("BEVERAGE") | categories_upper.eq("FOOD")
    candidates = work.loc[candidate_mask]
    dims = ["Menu Code", "Menu", "Menu Category", "Menu Category Detail"]
    if not candidates.empty:
        leaders = (
            candidates.groupby(dims, dropna=False, as_index=False)
            .agg(units=("units", "sum"), net_sales=("net_sales", "sum"))
            .sort_values(["net_sales", "units"], ascending=[False, False])
        )
        leader = leaders.iloc[0]
        product = str(leader["Menu"])
        if id_lang:
            message = (
                f"Di antara entri kategori BEVERAGE dan FOOD, '{product}' "
                f"mencatat penjualan bersih terbesar: {_idr(float(leader['net_sales']))} "
                f"dan {float(leader['units']):,.0f} unit selama periode yang diunggah."
            )
            action = "Pastikan entri tersebut benar-benar produk yang dijual tersendiri; kategori sumber tidak menjamin statusnya sebagai produk reguler."
        else:
            message = (
                f"Among BEVERAGE and FOOD entries, '{product}' has the highest "
                f"reported net sales: {_idr(float(leader['net_sales']))} "
                f"across {float(leader['units']):,.0f} recorded units in the uploaded period."
            )
            action = "Verify that this is a standalone product; source categories do not guarantee regular retail status."
        results.append(BusinessInsight(
            "Pemimpin pendapatan produk" if id_lang else "Product revenue leader",
            message, action,
        ))

    # Use a strict, explainable threshold to flag quantity/revenue mismatches;
    # do not call this a selling price or infer promotion mechanics.
    all_items = (
        work.groupby(dims, dropna=False, as_index=False)
        .agg(units=("units", "sum"), net_sales=("net_sales", "sum"))
    )
    flagged = all_items.loc[
        (all_items["units"] >= minimum_flagged_units)
        & (all_items["net_sales"].abs() <= near_zero_revenue_idr)
    ].sort_values(["units", "Menu"], ascending=[False, True])
    if not flagged.empty:
        names = "; ".join(
            f"{row['Menu']} ({float(row['units']):,.0f} unit)"
            for _, row in flagged.head(3).iterrows()
        )
        if id_lang:
            msg = (
                f"Ditemukan {len(flagged)} identitas menu dengan minimal "
                f"{minimum_flagged_units:,} unit tetapi total penjualan bersih yang "
                f"dilaporkan tidak lebih dari {_idr(near_zero_revenue_idr)} secara absolut. "
                f"Contoh: {names}."
            )
            action = "Periksa pemetaan POS, bundling, promosi, atau entri komponen sebelum menafsirkannya sebagai produk gratis atau terlaris."
        else:
            msg = (
                f"Found {len(flagged)} menu identities with at least "
                f"{minimum_flagged_units:,} recorded units but absolute reported "
                f"net sales no greater than {_idr(near_zero_revenue_idr)}. "
                f"Examples: {names}."
            )
            action = "Investigate POS mapping, bundles, promotions or component entries before interpreting these as free products or retail bestsellers."
        results.append(BusinessInsight(
            "Volume tinggi, pendapatan hampir nol" if id_lang else "High volume, little reported revenue",
            msg, action, "caution",
        ))

    if not earlier.empty:
        cat_month = (
            work.groupby(["period", "Menu Category"], dropna=False)["units"]
            .sum()
            .unstack(fill_value=0)
        )
        current = cat_month.loc[latest_period]
        previous_cat = cat_month.loc[latest_period - 1]
        movements = (current - previous_cat).sort_values(ascending=False)
        if not movements.empty:
            gains = movements[movements > 0]
            losses = movements[movements < 0].sort_values()
            segments = []
            if not gains.empty:
                segments.append(
                    f"{'Kenaikan terbesar' if id_lang else 'Largest increase'}: "
                    f"{gains.index[0]} ({float(gains.iloc[0]):+,.0f} unit)"
                )
            if not losses.empty:
                segments.append(
                    f"{'Penurunan terbesar' if id_lang else 'Largest decrease'}: "
                    f"{losses.index[0]} ({float(losses.iloc[0]):+,.0f} unit)"
                )
            if segments:
                results.append(BusinessInsight(
                    "Perubahan volume kategori" if id_lang else "Category volume changes",
                    "; ".join(segments) + ".",
                    "Perubahan volume dapat dipengaruhi penambahan/penghapusan item dan klasifikasi POS; cocokkan dengan daftar produk dan stok." if id_lang else "Changes may reflect assortment, availability or POS classification; compare against item lists and stock records.",
                ))

    results.append(BusinessInsight(
        "Batasan interpretasi" if id_lang else "Interpretation limits",
        "Laporan ini berisi ringkasan menu bulanan. Jumlah unit bukan jumlah pesanan pelanggan. Data ini tidak cukup untuk menghitung laba, tren harian, efektivitas bundling, atau penyebab perubahan penjualan." if id_lang else "These are monthly menu summaries. Units are not distinct customer orders. The data cannot establish profit, daily patterns, bundle effectiveness or causes of sales changes.",
        "Gunakan data transaksi individual, biaya produk, dan konteks operasional untuk analisis lanjutan." if id_lang else "Use transaction records, product costs and operating context for deeper analysis.",
        "caution",
    ))
    return results
