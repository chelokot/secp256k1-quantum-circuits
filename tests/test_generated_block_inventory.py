from __future__ import annotations

import json
from pathlib import Path

from support import ensure_compiler_project_build_summary, ensure_compiler_project_verification_summary

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_generated_block_inventories() -> dict:
    ensure_compiler_project_build_summary()
    ensure_compiler_project_verification_summary()
    path = REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'generated_block_inventories.json'
    return json.loads(path.read_text())


def test_generated_block_inventory_reconstructs_family_totals() -> None:
    inventories = _load_generated_block_inventories()
    for family in inventories['families']:
        primitive_ccx = sum(block['primitive_counts_total']['ccx'] for block in family['non_clifford_blocks'])
        qubits = sum(block['logical_qubits'] for block in family['qubit_blocks'])
        phase_measurements = sum(block['count'] for block in family['phase_count_blocks'] if block['category'] == 'phase_measurements')
        phase_rotations = sum(block['count'] for block in family['phase_count_blocks'] if block['category'] == 'phase_rotations')
        assert family['reconstruction']['full_oracle_non_clifford'] == primitive_ccx
        assert family['reconstruction']['total_logical_qubits'] == qubits
        assert family['reconstruction']['phase_shell_measurements'] == phase_measurements
        assert family['reconstruction']['phase_shell_rotations'] == phase_rotations


def test_generated_block_inventory_best_families_are_minima() -> None:
    inventories = _load_generated_block_inventories()
    best_gate = min(
        inventories['families'],
        key=lambda row: (
            row['reconstruction']['full_oracle_non_clifford'],
            row['reconstruction']['total_logical_qubits'],
        ),
    )
    best_qubit = min(
        inventories['families'],
        key=lambda row: (
            row['reconstruction']['total_logical_qubits'],
            row['reconstruction']['full_oracle_non_clifford'],
        ),
    )
    assert inventories['best_gate_family']['name'] == best_gate['name']
    assert inventories['best_qubit_family']['name'] == best_qubit['name']
