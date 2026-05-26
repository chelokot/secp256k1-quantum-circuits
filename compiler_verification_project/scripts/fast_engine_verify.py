#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


VERIFY_GROUPS = [
    'reusable_chunk_lowering_checks',
    'public_engine_manifest_checks',
    'engine_completion_audit_checks',
    'headline_resource_manifest_checks',
    'public_headline_result_checks',
    'strict_replayed_tail_headline_checks',
    'primary_strict_result_checks',
    'reusable_chunk_tail_candidate_checks',
    'release_corpus_preflight_checks',
]

PYTEST_TARGETS = [
    'tests/test_public_engine_manifest.py',
    'tests/test_engine_completion_audit.py',
    'tests/test_materialized_circuit.py',
    'tests/test_release_corpus_preflight.py',
    'tests/test_headline_resource_manifest.py',
    'tests/test_compiler_verification_project.py::test_mutated_public_engine_manifest_is_detected',
    'tests/test_compiler_verification_project.py::test_mutated_public_engine_manifest_semantic_evidence_is_detected',
    'tests/test_compiler_verification_project.py::test_mutated_reusable_chunk_executable_resource_engine_drift_is_detected',
    'tests/test_compiler_verification_project.py::test_mutated_reusable_chunk_schedule_source_instruction_drift_is_detected',
    'tests/test_public_headline_verifier.py',
    'tests/test_strict_replayed_tail_headline.py',
    'tests/test_primary_strict_result.py',
]


def _run(argv: list[str], *, cwd: Path = PROJECT_ROOT) -> None:
    print(f"[fast-engine] {' '.join(argv)}", flush=True)
    subprocess.run(argv, cwd=cwd, check=True)


def _pytest_command() -> list[str]:
    probe = subprocess.run(
        [sys.executable, '-m', 'pytest', '--version'],
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if probe.returncode == 0:
        return [sys.executable, '-m', 'pytest']
    pytest_path = shutil.which('pytest')
    if pytest_path is None:
        raise SystemExit('pytest is not importable by this Python and no pytest executable was found on PATH')
    return [pytest_path]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip-build', action='store_true')
    parser.add_argument('--skip-pytest', action='store_true')
    parser.add_argument('--include-rust', action='store_true')
    args = parser.parse_args()

    if not args.skip_build:
        _run([sys.executable, 'compiler_verification_project/scripts/build.py', '--target', 'resource-zkp-and-public'])
    _run([
        sys.executable,
        'compiler_verification_project/scripts/verify.py',
        '--summary',
        '--groups',
        *VERIFY_GROUPS,
    ])
    if not args.skip_pytest:
        _run([*_pytest_command(), '-q', *PYTEST_TARGETS])
    if args.include_rust:
        _run(
            ['cargo', 'test', '-p', 'secp256k1-zkp-attestation-lib', 'reusable_chunk'],
            cwd=PROJECT_ROOT / 'compiler_verification_project' / 'zkp_attestation',
        )


if __name__ == '__main__':
    main()
