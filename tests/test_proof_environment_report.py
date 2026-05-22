#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / 'compiler_verification_project' / 'scripts' / 'proof_environment_report.py'
SPEC = importlib.util.spec_from_file_location('proof_environment_report', SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_proof_environment_report_schema_and_required_tools() -> None:
    report = MODULE.build_report()
    assert report['schema'] == 'compiler-project-proof-environment-report-v1'
    required_names = {tool['name'] for tool in report['required_tools']}
    assert {'python', 'cargo', 'rustc', 'protoc', 'clang', 'go'}.issubset(required_names)
    assert report['missing_required_tools'] == [
        tool['name'] for tool in report['required_tools'] if not tool['available']
    ]
    assert report['ready_for_checked_proof_rebuild'] == (not report['missing_required_tools'])


def test_proof_environment_report_require_ready_flag_is_parsed() -> None:
    args = MODULE.parse_args([])
    assert args.require_ready is False
    args = MODULE.parse_args(['--require-ready'])
    assert args.require_ready is True


def test_proof_environment_report_resolves_env_configured_protoc(tmp_path, monkeypatch) -> None:
    protoc = tmp_path / 'protoc'
    protoc.write_text('#!/bin/sh\n')
    monkeypatch.setenv('PROTOC', str(protoc))
    assert MODULE._resolve_executable({'name': 'protoc', 'command': ['protoc', '--version'], 'env_var': 'PROTOC'}) == str(protoc)
