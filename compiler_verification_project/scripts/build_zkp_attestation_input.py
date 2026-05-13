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

from zkp_attestation import DEFAULT_CASE_COUNT, write_zkp_attestation_inputs  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Build the compiler-project ZK attestation input bundle.')
    parser.add_argument('--family', default='best-gate', help='Compiler family name or alias (best-gate, best-qubit).')
    parser.add_argument('--cases', type=int, default=DEFAULT_CASE_COUNT, help='Deterministic point-add case count.')
    parser.add_argument('--case-start', type=int, default=0, help='Starting deterministic case index within the public corpus.')
    parser.add_argument('--output-dir', type=Path, help='Optional output directory for the generated input, claim, and case artifacts.')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = write_zkp_attestation_inputs(
        family_name=args.family,
        case_count=args.cases,
        case_start=args.case_start,
        output_dir=args.output_dir,
    )
    artifact_root = args.output_dir if args.output_dir is not None else PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    print(json.dumps({
        'artifact': str(artifact_root / 'zkp_attestation_input.json'),
        'claim_sha256': payload['claim_sha256'],
        'leaf_sha256': payload['leaf_sha256'],
        'family_sha256': payload['family_sha256'],
        'case_corpus_sha256': payload['case_corpus_sha256'],
        'selected_family_name': payload['selected_family_name'],
        'case_start': args.case_start,
        'case_count': payload['prepared_case_corpus']['case_count'],
    }, indent=2))


if __name__ == '__main__':
    main()
