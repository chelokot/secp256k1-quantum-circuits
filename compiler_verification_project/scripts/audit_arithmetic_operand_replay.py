#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROOT_SRC = PROJECT_ROOT / 'src'
SRC = PROJECT_ROOT / 'compiler_verification_project' / 'src'
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from materialized_circuit import build_arithmetic_operand_replay_audit  # noqa: E402


ARTIFACT_ROOT = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'


def load_artifact(name: str) -> dict:
    return json.loads((ARTIFACT_ROOT / name).read_text())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Audit arithmetic flat-netlist operand replay against generated primitive operation operands.')
    parser.add_argument('--output', type=Path, default=None, help='Optional JSON output path.')
    parser.add_argument('--allow-failures', action='store_true', help='Exit 0 even when replay mismatches are found.')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_arithmetic_operand_replay_audit(
        public_candidate_materialized_circuit_manifest=load_artifact('public_candidate_materialized_circuit_manifest.json'),
        arithmetic_lowerings=load_artifact('arithmetic_lowerings.json'),
        arithmetic_operation_ir=load_artifact('arithmetic_operation_ir.json'),
    )
    encoded = json.dumps(report, indent=2, sort_keys=True) + '\n'
    if args.output is not None:
        output_path = args.output if args.output.is_absolute() else PROJECT_ROOT / args.output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(encoded)
    print(encoded, end='')
    if report['pass'] is not True and not args.allow_failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
