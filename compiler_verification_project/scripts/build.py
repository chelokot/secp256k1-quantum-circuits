#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / 'compiler_verification_project' / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
ROOT_SRC = PROJECT_ROOT / 'src'
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))

from baselines import load_public_google_baseline_lines  # noqa: E402
from project import build_all_artifacts, write_cain_transfer  # noqa: E402
from public_result import write_public_headline_result  # noqa: E402
from zkp_attestation import write_zkp_attestation_inputs  # noqa: E402


def main() -> None:
    payload = build_all_artifacts()
    payload['cain_transfer'] = write_cain_transfer()
    payload['zkp_attestation'] = write_zkp_attestation_inputs()
    candidate_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts' / 'zkp_attestation_reusable_chunk_candidate'
    payload['zkp_attestation_reusable_chunk_candidate'] = write_zkp_attestation_inputs(
        family_name='reusable-chunk',
        output_dir=candidate_dir,
    )
    payload['public_headline_result'] = write_public_headline_result(
        baseline=load_public_google_baseline_lines(),
    )
    print(json.dumps({
        'build_summary': payload['frontier']['best_gate_family'],
        'public_headline_result': 'compiler_verification_project/artifacts/public_headline_result.json',
        'zkp_attestation_input': 'compiler_verification_project/artifacts/zkp_attestation_input.json',
        'zkp_attestation_reusable_chunk_candidate_input': 'compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_input.json',
        'artifact_dir': 'compiler_verification_project/artifacts',
    }, indent=2))


if __name__ == '__main__':
    main()
