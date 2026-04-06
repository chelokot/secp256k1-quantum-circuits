#!/usr/bin/env python3
"""Rebuild MANIFEST.sha256 for the repository tree."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from common import relative_file_manifest  # noqa: E402


def main() -> None:
    manifest = relative_file_manifest(REPO_ROOT)
    out_lines = [f"{record['sha256']}  {rel}" for rel, record in manifest.items()]
    path = REPO_ROOT / 'MANIFEST.sha256'
    path.write_text('\n'.join(out_lines) + '\n')
    print(f'Wrote {path}')


if __name__ == '__main__':
    main()
