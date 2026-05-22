#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / 'compiler_verification_project' / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
ROOT_SRC = PROJECT_ROOT / 'src'
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))

from proof_status_report import build_proof_status_report  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Fast checked-artifact freshness report for reusable-chunk ZKP proofs.',
    )
    parser.add_argument(
        '--require-all-current',
        action='store_true',
        help='Exit nonzero if any checked proof fixture is stale against the current input/public values.',
    )
    return parser.parse_args()

def build_report() -> dict[str, Any]:
    return build_proof_status_report(PROJECT_ROOT)


def main() -> None:
    args = parse_args()
    report = build_report()
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.require_all_current and not report['all_current']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
