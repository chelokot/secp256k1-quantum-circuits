from __future__ import annotations

import json
from pathlib import Path

from support import ensure_compiler_project_build_summary, ensure_compiler_project_verification_summary


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_recount() -> dict:
    ensure_compiler_project_build_summary()
    ensure_compiler_project_verification_summary()
    path = REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'whole_oracle_recount.json'
    return json.loads(path.read_text())


def test_whole_oracle_recount_reconstructs_frontier_totals() -> None:
    recount = _load_recount()
    frontier = json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'family_frontier.json').read_text())
    frontier_lookup = {row['name']: row for row in frontier['families']}
    for family in recount['families']:
        frontier_row = frontier_lookup[family['name']]
        assert family['full_oracle_non_clifford'] == frontier_row['full_oracle_non_clifford']
        assert family['total_logical_qubits'] == frontier_row['total_logical_qubits']
        assert family['phase_shell_hadamards'] == frontier_row['phase_shell_hadamards']
        assert family['phase_shell_measurements'] == frontier_row['phase_shell_measurements']
        assert family['phase_shell_rotations'] == frontier_row['phase_shell_rotations']
        assert family['phase_shell_rotation_depth'] == frontier_row['phase_shell_rotation_depth']
        assert family['total_measurements'] == frontier_row['total_measurements']
        assert family['primitive_totals']['ccx'] == family['full_oracle_non_clifford']
    assert recount['best_gate_family']['name'] == frontier['best_gate_family']['name']
    assert recount['best_qubit_family']['name'] == frontier['best_qubit_family']['name']
