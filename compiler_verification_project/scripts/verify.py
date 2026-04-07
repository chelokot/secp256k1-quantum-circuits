#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / 'compiler_verification_project' / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from project import write_verification_summary  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run compiler-project semantic verification.')
    parser.add_argument('--cases', type=int, default=32, help='Deterministic case count for the raw-32 semantic replay.')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = write_verification_summary(case_count=args.cases)
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
