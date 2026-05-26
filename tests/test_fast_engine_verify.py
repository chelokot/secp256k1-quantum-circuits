from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / 'compiler_verification_project' / 'scripts' / 'fast_engine_verify.py'
SPEC = importlib.util.spec_from_file_location('fast_engine_verify', SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _render(commands: list[dict]) -> str:
    return '\n'.join(' '.join(step['command']) for step in commands)


def test_fast_engine_verify_plan_has_no_prover_or_broad_rebuild() -> None:
    commands = MODULE.command_plan(skip_build=False, skip_pytest=False, include_rust=False)
    MODULE.assert_no_broad_rebuild_or_prover_commands(commands)
    rendered = _render(commands)
    assert '--prove' not in rendered
    assert 'run_zkp_attestation_guarded.py' not in rendered
    assert 'resource-zkp-and-public' not in rendered
    assert 'zkp-and-public' not in rendered
    assert 'candidate-zkp' not in rendered
    assert 'arithmetic-operand-replay-audit' in rendered
    assert 'engine-completion-audit-current' in rendered
    assert 'strict-replayed-tail-headline' in rendered
    assert 'primary-strict-result' in rendered
    assert 'arithmetic_operand_replay_audit_checks' in rendered
    assert 'public_headline_result_checks' not in rendered


def test_fast_engine_verify_skip_build_keeps_verify_and_pytest_only() -> None:
    commands = MODULE.command_plan(skip_build=True, skip_pytest=False, include_rust=False)
    assert all(step['name'].startswith('refresh_') is False for step in commands)
    assert commands[0]['name'] == 'engine_integrity_groups'
    assert commands[1]['name'] == 'engine_pytest'
    MODULE.assert_no_broad_rebuild_or_prover_commands(commands)


def test_fast_engine_verify_skip_pytest_keeps_integrity_only_after_refresh() -> None:
    commands = MODULE.command_plan(skip_build=False, skip_pytest=True, include_rust=False)
    assert commands[-1]['name'] == 'engine_integrity_groups'
    assert all(step['name'] != 'engine_pytest' for step in commands)
    MODULE.assert_no_broad_rebuild_or_prover_commands(commands)


def test_fast_engine_verify_include_rust_adds_reusable_chunk_test() -> None:
    commands = MODULE.command_plan(skip_build=True, skip_pytest=True, include_rust=True)
    assert commands[-1]['name'] == 'attestation_lib_reusable_chunk_tests'
    assert commands[-1]['cwd'] == 'compiler_verification_project/zkp_attestation'
    MODULE.assert_no_broad_rebuild_or_prover_commands(commands)
