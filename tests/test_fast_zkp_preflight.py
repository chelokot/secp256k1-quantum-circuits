from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / 'compiler_verification_project' / 'scripts' / 'fast_zkp_preflight.py'
SPEC = importlib.util.spec_from_file_location('fast_zkp_preflight', SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_fast_zkp_preflight_plan_has_no_prover_commands() -> None:
    commands = MODULE.command_plan(skip_cargo=False)
    MODULE.assert_no_heavy_prover_commands(commands)
    rendered = '\n'.join(' '.join(step['command']) for step in commands)
    assert '--prove' not in rendered
    assert 'run_zkp_attestation_guarded.py' not in rendered


def test_fast_zkp_preflight_skip_cargo_removes_rust_step() -> None:
    commands = MODULE.command_plan(skip_cargo=True)
    assert all(step['name'] != 'attestation_lib_cargo_test' for step in commands)


def test_fast_zkp_preflight_parse_args_supports_dry_run() -> None:
    original_argv = sys.argv
    try:
        sys.argv = ['fast_zkp_preflight.py', '--skip-cargo', '--dry-run-json']
        args = MODULE.parse_args()
    finally:
        sys.argv = original_argv
    assert args.skip_cargo is True
    assert args.dry_run_json is True
