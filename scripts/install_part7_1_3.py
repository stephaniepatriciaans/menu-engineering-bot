"""Idempotent Part 7.1+7.3 installer, applying only validated source anchors.

Copy the patch into the Menu Engineering Bot repository and run once.
The installer checks ALL anchors and syntax before writing ANY existing files.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def once(source: str, old: str, new: str, label: str) -> str:
    if new in source:
        return source
    if source.count(old) != 1:
        raise RuntimeError(f"Expected exactly one {label} anchor, found {source.count(old)}")
    return source.replace(old, new, 1)


def patch_app(source: str) -> str:
    source = once(
        source,
        "from ui.pages.analytics import render_analytics\n",
        "from core.performance import PerformanceProfiler\n"
        "from ui.pages.analytics import render_analytics\n",
        "app imports",
    )
    source = once(
        source,
        "from ui.pages.reports import render_reports\n",
        "from ui.pages.reports import render_reports\n"
        "from ui.performance_dashboard import render_performance_summary\n",
        "app performance UI import",
    )
    source = once(
        source,
        "    settings = render_sidebar()\n",
        "    profiler = PerformanceProfiler()\n"
        "    settings = render_sidebar()\n",
        "app profiler",
    )
    for name, code, label in (
        ("setup", "render_data_setup(settings)", "Data Setup"),
        ("quality", "render_data_quality(setup)", "Data Quality"),
        ("moves", "render_analytics(setup, quality, settings)", "Analytics"),
    ):
        old = f"        {name} = {code}\n"
        new = f"        with profiler.measure({label!r}):\n            {name} = {code}\n"
        source = once(source, old, new, label)
    source = once(
        source,
        "        render_reports(setup, quality, settings, moves)\n",
        "        with profiler.measure('Reports'):\n"
        "            render_reports(setup, quality, settings, moves)\n"
        "    render_performance_summary(profiler)\n",
        "Reports timing",
    )
    return source


def patch_upload(source: str) -> str:
    # Function rename maintains the source parser unchanged; the public wrapper
    # uses a bounded cache only for Streamlit UploadedFile-like objects.
    if "def _load_uploaded_sales_uncached(" not in source:
        source = once(
            source,
            "def load_uploaded_sales(\n",
            "def _load_uploaded_sales_uncached(\n",
            "uploaded sales loader",
        )
    wrapper = '''\n\ndef load_uploaded_sales(
    uploaded,
    encoding: str = "utf-8-sig",
) -> tuple[pd.DataFrame, list[str]]:
    """Read unchanged uploads once per cache entry; preserve parser semantics.

    Non-Streamlit test objects and streams without a reliable filename use
    the established uncached reader. Streamlit UploadedFile includes both
    name and getvalue(). A content-based key prevents stale filename hits.
    """
    filename = getattr(uploaded, "name", None)
    getvalue = getattr(uploaded, "getvalue", None)
    if isinstance(filename, str) and filename and callable(getvalue):
        from ui.cached_upload import cached_uploaded_sales

        return cached_uploaded_sales(filename, getvalue(), encoding)
    return _load_uploaded_sales_uncached(uploaded, encoding=encoding)
'''
    if "def load_uploaded_sales(\n" not in source:
        source += wrapper
    return source


def patch_model_ui(source: str) -> str:
    source = once(
        source,
        "    evaluate_historical_average,\n)\n\nREQUIRED_COLUMNS =",
        "    evaluate_historical_average,\n)\n"
        "from ui.evaluation_reliability import render_paired_model_reliability\n\n"
        "REQUIRED_COLUMNS =",
        "model UI import",
    )
    marker = "    # ITEM-LEVEL RESULTS\n"
    if "    render_paired_model_reliability(item_df)\n" not in source:
        if source.count(marker) != 1:
            raise RuntimeError("Model evaluation item-level anchor not found")
        source = source.replace(
            marker,
            "    # Report paired out-of-sample reliability; no forecast recalculation.\n"
            "    render_paired_model_reliability(item_df)\n\n"
            + marker,
            1,
        )
    return source


def install(root: Path) -> list[str]:
    transforms = {
        "src/app.py": patch_app,
        "src/ui/data_upload.py": patch_upload,
        "src/ui/sections/model_evaluation.py": patch_model_ui,
    }
    updated: dict[Path, str] = {}
    for relpath, transform in transforms.items():
        target = root / relpath
        original = target.read_text(encoding="utf-8")
        result = transform(original)
        ast.parse(result, filename=relpath)
        if result != original:
            updated[target] = result
    for target, result in updated.items():
        target.write_text(result, encoding="utf-8")
    return [str(target.relative_to(root)) for target in updated]


def main() -> None:
    changed = install(ROOT)
    if changed:
        for name in changed:
            print(f"Updated {name}")
    else:
        print("Already installed; no files changed.")


if __name__ == "__main__":
    main()
