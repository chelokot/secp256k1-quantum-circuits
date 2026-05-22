#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from proof_environment import build_report as build_environment_report  # noqa: E402


def build_report() -> dict[str, Any]:
    return build_environment_report(REPO_ROOT)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Report local tool readiness for checked SP1 proof workflows.')
    parser.add_argument('--require-ready', action='store_true', help='Exit nonzero if a required tool is missing.')
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    report = build_report()
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.require_ready and not report['ready_for_checked_proof_rebuild']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
