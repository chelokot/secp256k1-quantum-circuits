#!/usr/bin/env python3

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


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


def _probe(tool: dict[str, Any], *, required: bool, repo_root: Path) -> dict[str, Any]:
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
            cwd=repo_root,
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


def tool_contracts() -> dict[str, Any]:
    return {
        'required_tools': list(REQUIRED_TOOLS),
        'optional_tools': list(OPTIONAL_TOOLS),
        'required_tool_names': [tool['name'] for tool in REQUIRED_TOOLS],
        'optional_tool_names': [tool['name'] for tool in OPTIONAL_TOOLS],
    }


def build_report(repo_root: Path) -> dict[str, Any]:
    required = [_probe(tool, required=True, repo_root=repo_root) for tool in REQUIRED_TOOLS]
    optional = [_probe(tool, required=False, repo_root=repo_root) for tool in OPTIONAL_TOOLS]
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


__all__ = ['REQUIRED_TOOLS', 'OPTIONAL_TOOLS', 'build_report', 'tool_contracts']
