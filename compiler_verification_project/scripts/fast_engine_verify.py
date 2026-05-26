#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]


VERIFY_GROUPS = [
    'arithmetic_operand_replay_audit_checks',
    'reusable_chunk_lowering_checks',
    'public_engine_manifest_checks',
    'engine_completion_audit_checks',
    'headline_resource_manifest_checks',
    'strict_replayed_tail_headline_checks',
    'primary_strict_result_checks',
    'reusable_chunk_tail_candidate_checks',
    'release_corpus_preflight_checks',
]

REFRESH_TARGETS = [
    'arithmetic-operand-replay-audit',
    'public-engine-manifest',
    'engine-completion-audit',
    'strict-replayed-tail-headline',
    'primary-strict-result',
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
    'tests/test_strict_replayed_tail_headline.py',
    'tests/test_primary_strict_result.py',
]

BROAD_BUILD_TARGETS = {
    'all',
    'candidate-zkp',
    'public-headline',
    'release-candidate-zkp',
    'resource-zkp-and-public',
    'zkp-and-public',
}


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


def command_plan(*, skip_build: bool, skip_pytest: bool, include_rust: bool) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []
    if not skip_build:
        commands.extend(
            {
                'name': f'refresh_{target.replace("-", "_")}',
                'command': [
                    sys.executable,
                    'compiler_verification_project/scripts/build.py',
                    '--target',
                    target,
                ],
            }
            for target in REFRESH_TARGETS
        )
    commands.append(
        {
            'name': 'engine_integrity_groups',
            'command': [
                sys.executable,
                'compiler_verification_project/scripts/verify.py',
                '--summary',
                '--groups',
                *VERIFY_GROUPS,
            ],
        }
    )
    if not skip_pytest:
        commands.append(
            {
                'name': 'engine_pytest',
                'command': [*_pytest_command(), '-q', *PYTEST_TARGETS],
            }
        )
    if include_rust:
        commands.append(
            {
                'name': 'attestation_lib_reusable_chunk_tests',
                'command': ['cargo', 'test', '-p', 'secp256k1-zkp-attestation-lib', 'reusable_chunk'],
                'cwd': 'compiler_verification_project/zkp_attestation',
            }
        )
    return commands


def assert_no_broad_rebuild_or_prover_commands(commands: list[dict[str, Any]]) -> None:
    for step in commands:
        command = step['command']
        rendered = ' '.join(command)
        if '--prove' in command or 'run_zkp_attestation_guarded.py' in rendered:
            raise SystemExit(f'fast engine verification must not invoke a prover: {rendered}')
        if 'compiler_verification_project/scripts/build.py' in command:
            for index, part in enumerate(command[:-1]):
                if part == '--target' and command[index + 1] in BROAD_BUILD_TARGETS:
                    raise SystemExit(f'fast engine verification must not invoke broad build target: {rendered}')


def main() -> None:
    parser = argparse.ArgumentParser(description='Run the focused no-ZKP public-engine verification loop.')
    parser.add_argument('--skip-build', action='store_true', help='Skip focused no-ZKP artifact refresh targets.')
    parser.add_argument('--skip-pytest', action='store_true', help='Skip focused Python tests.')
    parser.add_argument('--include-rust', action='store_true', help='Also run reusable-chunk Rust unit tests.')
    parser.add_argument('--dry-run-json', action='store_true', help='Print the command plan as JSON instead of running it.')
    args = parser.parse_args()

    commands = command_plan(skip_build=args.skip_build, skip_pytest=args.skip_pytest, include_rust=args.include_rust)
    assert_no_broad_rebuild_or_prover_commands(commands)
    if args.dry_run_json:
        print(json.dumps({'schema': 'compiler-project-fast-engine-verify-v1', 'commands': commands}, indent=2))
        return
    for step in commands:
        _run(step['command'], cwd=PROJECT_ROOT / step.get('cwd', ''))


if __name__ == '__main__':
    main()
