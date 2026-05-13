#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / 'compiler_verification_project' / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from project import build_all_artifacts, write_cain_transfer  # noqa: E402
from zkp_attestation import write_zkp_attestation_inputs  # noqa: E402


def main() -> None:
    payload = build_all_artifacts()
    payload['cain_transfer'] = write_cain_transfer()
    payload['zkp_attestation'] = write_zkp_attestation_inputs()
    print(json.dumps({
        'build_summary': payload['frontier']['best_gate_family'],
        'zkp_attestation_input': 'compiler_verification_project/artifacts/zkp_attestation_input.json',
        'artifact_dir': 'compiler_verification_project/artifacts',
    }, indent=2))


if __name__ == '__main__':
    main()
