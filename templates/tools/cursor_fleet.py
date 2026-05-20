#!/usr/bin/env python3
"""Project-local cursor-fleet launcher.

This file is copied to .codex/tools/cursor_fleet.py by scripts/install_project.py.
It runs the vendored source under .cursor-fleet/vendor/cursor-fleet/src so a target
project does not need a global Python package install.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main() -> None:
    project = Path(__file__).resolve().parents[2]
    src = project / ".cursor-fleet" / "vendor" / "cursor-fleet" / "src"
    if not src.exists():
        raise SystemExit(
            "cursor-fleet vendor source not found. Re-run scripts/install_project.py from the cursor-fleet repository."
        )
    sys.path.insert(0, str(src))
    runpy.run_module("cursor_fleet", run_name="__main__")


if __name__ == "__main__":
    main()
