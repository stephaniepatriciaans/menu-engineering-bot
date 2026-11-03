"""Finish the one-time repository cleanup after extracting the refactor ZIP.

Run from the repository root: python3 scripts/finalize_layout.py

Never deletes different/modified test files, datasets, or secrets.
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def clean_old_tests() -> tuple[int, list[str]]:
    """Remove only identical legacy test copies after validating replacements."""
    removed = 0
    conflicts: list[str] = []
    tests = ROOT / "tests"

    for group in ("analytics", "ai", "core", "data_pipeline", "integration", "reporting", "ui"):
        for moved in (tests / group).glob("test_*.py"):
            legacy = tests / moved.name
            if not legacy.exists():
                continue

            existing = legacy.read_text(encoding="utf-8")
            expected = existing.replace(
                "Path(__file__).resolve().parents[1]",
                "Path(__file__).resolve().parents[2]",
            ).replace(
                'os.path.join(os.path.dirname(__file__), "..")',
                'os.path.join(os.path.dirname(__file__), "..", "..")',
            )
            if expected == moved.read_text(encoding="utf-8"):
                legacy.unlink()
                removed += 1
            else:
                conflicts.append(str(legacy.relative_to(ROOT)))

    return removed, conflicts


def organize_screenshots() -> int:
    """Move existing PNG screenshots and update Markdown references safely."""
    assets = ROOT / "assets"
    destination = assets / "screenshots"
    files = sorted(assets.glob("*.png"))
    if not files:
        return 0

    destination.mkdir(parents=True, exist_ok=True)
    for source in files:
        target = destination / source.name
        if target.exists():
            raise FileExistsError(f"Screenshot already exists at {target}")

    for source in files:
        shutil.move(str(source), str(destination / source.name))

    markdown = [ROOT / "README.md", *(ROOT / "docs").glob("*.md")]
    for path in markdown:
        if path.exists():
            content = path.read_text(encoding="utf-8")
            for source in files:
                content = content.replace(
                    f"assets/{source.name}",
                    f"assets/screenshots/{source.name}",
                )
            path.write_text(content, encoding="utf-8")
    return len(files)


def main() -> None:
    removed, conflicts = clean_old_tests()
    moved = organize_screenshots()
    print(f"Removed {removed} verified duplicate legacy test files")
    print(f"Organized {moved} screenshot(s)")
    if conflicts:
        print("Preserved modified legacy tests requiring manual comparison:")
        for path in conflicts:
            print(f"  {path}")
        raise SystemExit(1)
    print("Local layout finalization completed.")


if __name__ == "__main__":
    main()
