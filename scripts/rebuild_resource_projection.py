#!/usr/bin/env python3
"""Rebuild the canonical modeled resource projection file."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from resource_projection import write_resource_projection  # noqa: E402


def main() -> None:
    write_resource_projection(REPO_ROOT)
    print(f'Wrote {REPO_ROOT / "artifacts" / "out" / "resource_projection.json"}')


if __name__ == '__main__':
    main()
