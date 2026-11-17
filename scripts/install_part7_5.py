"""Safely install the Part 7.5 CI workflow and development safeguards.

Run from the repository root: python3 scripts/install_part7_5.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def ensure_requirement() -> None:
    path = ROOT / "requirements-dev.txt"
    if not path.is_file():
        raise FileNotFoundError("requirements-dev.txt not found in project root")
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    if not any(line.strip().lower().startswith("ruff") for line in lines):
        with path.open("a", encoding="utf-8") as handle:
            if content and not content.endswith("\n"):
                handle.write("\n")
            handle.write("ruff>=0.9,<1\n")
        print("requirements-dev.txt: added Ruff")
    else:
        print("requirements-dev.txt: Ruff already specified")


def ensure_gitignore() -> None:
    path = ROOT / ".gitignore"
    if not path.is_file():
        raise FileNotFoundError(".gitignore not found in project root")
    content = path.read_text(encoding="utf-8")
    additions = []
    if "data/Indo_CoffeeShop/" not in content.splitlines():
        additions.append("data/Indo_CoffeeShop/")
    if "*.part7_4.bak" not in content.splitlines():
        additions.append("*.part7_4.bak")
    if additions:
        with path.open("a", encoding="utf-8") as handle:
            if content and not content.endswith("\n"):
                handle.write("\n")
            handle.write("\n# Local datasets and installer backups\n")
            handle.write("\n".join(additions) + "\n")
        print(".gitignore: added", ", ".join(additions))
    else:
        print(".gitignore: dataset and backups already ignored")


def main() -> None:
    workflow = ROOT / ".github/workflows/ci.yml"
    if not workflow.is_file():
        raise FileNotFoundError("Missing .github/workflows/ci.yml; unzip patch at repository root")
    ensure_requirement()
    ensure_gitignore()
    print("Installed Part 7.5 workflow. Run lint, tests, and Git safety checks.")


if __name__ == "__main__":
    main()
