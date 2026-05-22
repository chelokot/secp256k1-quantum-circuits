#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / 'compiler_verification_project' / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
ROOT_SRC = PROJECT_ROOT / 'src'
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))

from common import sha256_path  # noqa: E402
from proof_corpus_profiles import resolve_proof_corpus_profile  # noqa: E402

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Build and optionally execute the 9024-case release ZKP input without proving.',
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Run the SP1 guest execute path over the generated release input. This never invokes a prover.',
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        help='Directory for the generated release bundle. Defaults to a temporary directory.',
    )
    parser.add_argument(
        '--keep-output',
        action='store_true',
        help='Keep the temporary output directory and print its path.',
    )
    parser.add_argument(
        '--resource-profile',
        choices=('safe', 'balanced', 'throughput', 'full'),
        default='safe',
        help='Resource profile passed to the execute-only guarded runner.',
    )
    parser.add_argument(
        '--skip-build',
        action='store_true',
        help='Skip rebuilding the Rust host binary before execute-only replay.',
    )
    parser.add_argument(
        '--dry-run-json',
        action='store_true',
        help='Print the planned actions without building or executing.',
    )
    return parser.parse_args()


def build_release_input(output_dir: Path) -> dict[str, Any]:
    profile = resolve_proof_corpus_profile('release')
    command = [
        sys.executable,
        'compiler_verification_project/scripts/build_zkp_attestation_input.py',
        '--family',
        'reusable-chunk',
        '--profile',
        'release',
        '--output-dir',
        str(output_dir),
    ]
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    builder_report = parse_json_object(completed.stdout)
    input_path = output_dir / 'zkp_attestation_input.json'
    payload = json.loads(input_path.read_text())
    return {
        'profile': profile['name'],
        'profile_release_grade': bool(profile['release_grade']),
        'case_start': int(profile['case_start']),
        'case_count': int(builder_report['case_count']),
        'builder_command': command,
        'input_path': str(input_path),
        'input_sha256': sha256_path(input_path),
        'selected_family_name': payload['selected_family_name'],
        'claim_sha256': payload['claim_sha256'],
        'leaf_sha256': payload['leaf_sha256'],
        'family_sha256': payload['family_sha256'],
        'case_corpus_sha256': payload['case_corpus_sha256'],
        'resource_certificate_sha256': payload['resource_certificate_sha256'],
    }


def parse_json_object(stdout: str) -> dict[str, Any]:
    for index, character in enumerate(stdout):
        if character != '{':
            continue
        try:
            payload = json.loads(stdout[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise ValueError('guarded runner output did not contain a JSON object')


def parse_guarded_runner_json(stdout: str) -> dict[str, Any]:
    return parse_json_object(stdout)


def execute_release_input(
    *,
    input_path: Path,
    output_dir: Path,
    resource_profile: str,
    skip_build: bool,
) -> dict[str, Any]:
    execute_dir = output_dir / 'execute'
    command = [
        sys.executable,
        'compiler_verification_project/scripts/run_zkp_attestation_guarded.py',
        '--execute',
        '--system',
        'core',
        '--resource-profile',
        resource_profile,
        '--input',
        str(input_path),
        '--output-dir',
        str(execute_dir),
    ]
    if skip_build:
        command.append('--skip-build')
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    summary = parse_guarded_runner_json(completed.stdout)
    public_values = summary['public_values']
    return {
        'command': command,
        'output_dir': str(execute_dir),
        'case_count': int(public_values['case_count']),
        'passed_case_count': int(public_values['passed_case_count']),
        'expected_full_oracle_non_clifford': int(public_values['expected_full_oracle_non_clifford']),
        'expected_total_logical_qubits': int(public_values['expected_total_logical_qubits']),
        'stage_seconds': summary['stage_seconds'],
        'total_instruction_count': int(summary['total_instruction_count']),
    }


def planned_output_dir(args: argparse.Namespace) -> tuple[Path, tempfile.TemporaryDirectory[str] | None]:
    if args.output_dir is not None:
        return args.output_dir, None
    temporary = tempfile.TemporaryDirectory(prefix='secp-zkp-release-')
    return Path(temporary.name), temporary


def main() -> int:
    args = parse_args()
    if args.dry_run_json:
        output_dir = args.output_dir or Path('<temporary-directory>')
        print(json.dumps({
            'schema': 'compiler-project-release-candidate-preproof-plan-v1',
            'build_release_input': {
                'profile': 'release',
                'family': 'reusable-chunk',
                'output_dir': str(output_dir),
            },
            'execute': bool(args.execute),
            'proof_invoked': False,
        }, indent=2, sort_keys=True))
        return 0

    output_dir, temporary = planned_output_dir(args)
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f'[release-candidate-preproof] building release input in {output_dir}', file=sys.stderr, flush=True)
        input_report = build_release_input(output_dir)
        print('[release-candidate-preproof] finished release input build', file=sys.stderr, flush=True)
        report: dict[str, Any] = {
            'schema': 'compiler-project-release-candidate-preproof-v1',
            'proof_invoked': False,
            'output_dir': str(output_dir),
            'input': input_report,
        }
        if args.execute:
            print('[release-candidate-preproof] starting SP1 execute-only replay', file=sys.stderr, flush=True)
            report['execute'] = execute_release_input(
                input_path=Path(input_report['input_path']),
                output_dir=output_dir,
                resource_profile=args.resource_profile,
                skip_build=args.skip_build,
            )
            print('[release-candidate-preproof] finished SP1 execute-only replay', file=sys.stderr, flush=True)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    finally:
        if temporary is not None and not args.keep_output:
            temporary.cleanup()


if __name__ == '__main__':
    raise SystemExit(main())
