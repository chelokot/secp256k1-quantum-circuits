from __future__ import annotations

import json
from pathlib import Path

from support import ensure_compiler_project_build_summary, ensure_compiler_project_verification_summary

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_compiler_project_frontier_and_schedule() -> None:
    build_path = ensure_compiler_project_build_summary()
    summary = json.loads(build_path.read_text())
    frontier_path = REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'family_frontier.json'
    frontier = json.loads(frontier_path.read_text())
    assert summary['headline']['best_gate_family'] == frontier['best_gate_family']
    assert summary['headline']['best_qubit_family'] == frontier['best_qubit_family']
    assert frontier['best_gate_family']['phase_shell'] == 'semiclassical_qft_v1'
    assert frontier['best_qubit_family']['phase_shell'] == 'semiclassical_qft_v1'


def test_compiler_project_verification_summary() -> None:
    verify_path = ensure_compiler_project_verification_summary()
    summary = json.loads(verify_path.read_text())
    assert summary['summary']['pass'] == summary['summary']['total']
    assert summary['slot_allocation_checks']['pass'] == 1
    assert summary['slot_allocation_checks']['observed_arithmetic_slots'] == 9
    assert summary['primitive_multiplier_checks']['pass'] == 1
    assert summary['primitive_multiplier_checks']['observed_instance_count'] == 341
    assert summary['qubit_frontier_checks']['pass'] == 1
