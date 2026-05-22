#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_TOOLS = (
    {
        'name': 'python',
        'command': ['python3.12', '--version'],
        'required_for': 'artifact generation and fast integrity checks',
    },
    {
        'name': 'cargo',
        'command': ['cargo', '--version'],
        'required_for': 'SP1 attestation Rust workspace builds',
    },
    {
        'name': 'rustc',
        'command': ['rustc', '--version'],
        'required_for': 'SP1 attestation Rust workspace builds',
    },
    {
        'name': 'protoc',
        'command': ['protoc', '--version'],
        'fallback_executable': '/tmp/protoc-34.1/bin/protoc',
        'env_var': 'PROTOC',
        'required_for': 'SP1 prover-types protobuf build scripts',
    },
    {
        'name': 'clang',
        'command': ['clang', '--version'],
        'required_for': 'bindgen/libclang-backed SP1 dependencies',
    },
    {
        'name': 'go',
        'command': ['go', 'version'],
        'required_for': 'vendored gnark Groth16 wrapper build path',
    },
)

OPTIONAL_TOOLS = (
    {
        'name': 'cargo-prove',
        'command': ['cargo-prove', '--version'],
        'required_for': 'native SP1 prove/verify command convenience',
    },
    {
        'name': 'sp1up',
        'command': ['sp1up', '--version'],
        'required_for': 'SP1 toolchain installation convenience',
    },
)


def _resolve_executable(tool: dict[str, Any]) -> str | None:
    env_var = tool.get('env_var')
    if env_var is not None:
        configured = os.environ.get(str(env_var))
        if configured and Path(configured).exists():
            return configured
    fallback = tool.get('fallback_executable')
    if fallback is not None and Path(str(fallback)).exists():
        return str(fallback)
    return shutil.which(tool['command'][0])


def _probe(tool: dict[str, Any], *, required: bool) -> dict[str, Any]:
    executable = _resolve_executable(tool)
    if executable is None:
        return {
            'name': tool['name'],
            'command': tool['command'],
            'required': required,
            'required_for': tool['required_for'],
            'available': False,
            'executable': None,
            'version': None,
            'error': 'not found on PATH',
        }
    try:
        command = [executable, *tool['command'][1:]]
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        return {
            'name': tool['name'],
            'command': tool['command'],
            'required': required,
            'required_for': tool['required_for'],
            'available': False,
            'executable': executable,
            'version': None,
            'error': 'version command timed out',
        }
    output = result.stdout.strip().splitlines()
    return {
        'name': tool['name'],
        'command': tool['command'],
        'required': required,
        'required_for': tool['required_for'],
        'available': result.returncode == 0,
        'executable': executable,
        'version': output[0] if output else '',
        'error': None if result.returncode == 0 else result.stdout.strip(),
    }


def build_report() -> dict[str, Any]:
    required = [_probe(tool, required=True) for tool in REQUIRED_TOOLS]
    optional = [_probe(tool, required=False) for tool in OPTIONAL_TOOLS]
    missing_required = [tool['name'] for tool in required if not tool['available']]
    return {
        'schema': 'compiler-project-proof-environment-report-v1',
        'scope': 'fast local readiness check for SP1 compressed/Groth16 proof verification and rebuild tooling',
        'required_tools': required,
        'optional_tools': optional,
        'missing_required_tools': missing_required,
        'ready_for_checked_proof_rebuild': not missing_required,
        'notes': [
            'This is an environment preflight, not a proof verifier.',
            'Use proof_status.py to decide whether checked proof artifacts are current.',
        ],
    }


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
