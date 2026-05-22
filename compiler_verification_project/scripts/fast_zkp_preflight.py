#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
VERIFY_GROUPS = (
    'public_headline_result_checks',
    'proof_environment_contract_checks',
    'compiler_parameter_checks',
    'release_corpus_preflight_checks',
    'reusable_chunk_lowering_checks',
    'qroam_reference_crosscheck_checks',
)
PYTEST_TARGETS = (
    'tests/test_zkp_attestation_runner.py',
    'tests/test_release_inventory.py',
    'tests/test_zkp_proof_status.py',
    'tests/test_proof_environment_contract.py',
    'tests/test_release_corpus_preflight.py',
    'tests/test_zkp_attestation_input.py::test_reusable_chunk_zkp_attestation_input_binds_candidate_contract',
    'tests/test_public_headline_verifier.py',
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run the fast ZKP/resource preflight without invoking provers.')
    parser.add_argument('--skip-cargo', action='store_true', help='Skip Rust unit tests for the SP1 attestation library.')
    parser.add_argument('--require-current-proofs', action='store_true', help='Fail the preflight unless checked core/compressed/Groth16 fixtures bind the current input.')
    parser.add_argument('--dry-run-json', action='store_true', help='Print the command plan as JSON instead of running it.')
    return parser.parse_args()


def command_plan(skip_cargo: bool, *, require_current_proofs: bool = False) -> list[dict[str, Any]]:
    proof_status_command = [
        sys.executable,
        'compiler_verification_project/scripts/proof_status.py',
    ]
    if require_current_proofs:
        proof_status_command.append('--require-all-current')
    commands = [
        {
            'name': 'proof_environment_report',
            'command': [
                sys.executable,
                'compiler_verification_project/scripts/proof_environment_report.py',
            ],
        },
        {
            'name': 'proof_status',
            'command': proof_status_command,
        },
        {
            'name': 'integrity_groups',
            'command': [
                sys.executable,
                'compiler_verification_project/scripts/verify.py',
                '--summary',
                '--groups',
                *VERIFY_GROUPS,
            ],
        },
        {
            'name': 'targeted_pytest',
            'command': [
                sys.executable,
                '-m',
                'pytest',
                '-q',
                *PYTEST_TARGETS,
            ],
        },
    ]
    if not skip_cargo:
        commands.append(
            {
                'name': 'attestation_lib_cargo_test',
                'command': [
                    'cargo',
                    'test',
                    '-p',
                    'secp256k1-zkp-attestation-lib',
                ],
                'cwd': 'compiler_verification_project/zkp_attestation',
            }
        )
    return commands


def assert_no_heavy_prover_commands(commands: list[dict[str, Any]]) -> None:
    for step in commands:
        command = step['command']
        rendered = ' '.join(command)
        if '--prove' in command or 'run_zkp_attestation_guarded.py' in rendered:
            raise SystemExit(f'fast preflight must not invoke a prover: {rendered}')


def main() -> None:
    args = parse_args()
    commands = command_plan(args.skip_cargo, require_current_proofs=args.require_current_proofs)
    assert_no_heavy_prover_commands(commands)
    if args.dry_run_json:
        print(json.dumps({'schema': 'compiler-project-fast-zkp-preflight-v1', 'commands': commands}, indent=2))
        return
    for step in commands:
        print(f"[fast-zkp-preflight] {step['name']}", flush=True)
        subprocess.run(step['command'], cwd=REPO_ROOT / step.get('cwd', ''), check=True)


if __name__ == '__main__':
    main()
