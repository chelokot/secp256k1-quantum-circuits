#!/usr/bin/env python3
"""Run the extended research pass and rebuild derived research artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from research_extensions import run_research_pass  # noqa: E402


def main() -> None:
    summary = run_research_pass(REPO_ROOT)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
