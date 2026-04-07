from __future__ import annotations

import json
from pathlib import Path

from support import ensure_compiler_project_build_summary, ensure_compiler_project_verification_summary

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_compiler_project_frontier_and_schedule() -> None:
    build_path = ensure_compiler_project_build_summary()
    summary = json.loads(build_path.read_text())
    best_gate = summary['headline']['best_gate_family']
    best_qubit = summary['headline']['best_qubit_family']
    assert best_gate['full_oracle_non_clifford'] < 70_000_000
    assert best_gate['improvement_vs_google_low_gate'] > 1.0
    assert best_qubit['total_logical_qubits'] < 2500
    assert 'semiclassical_qft_v1' in best_qubit['name']


def test_compiler_project_verification_summary() -> None:
    verify_path = ensure_compiler_project_verification_summary()
    summary = json.loads(verify_path.read_text())
    assert summary['summary']['pass'] == summary['summary']['total']
    assert summary['slot_allocation_checks']['observed_arithmetic_slots'] == 9
    assert summary['primitive_multiplier_checks']['observed_instance_count'] == 341
