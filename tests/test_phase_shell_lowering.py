from __future__ import annotations

import json
from pathlib import Path

from support import ensure_compiler_project_build_summary, ensure_compiler_project_verification_summary


REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE_BITS = 512


def _load_phase_shell_lowerings() -> dict:
    ensure_compiler_project_build_summary()
    ensure_compiler_project_verification_summary()
    path = REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'phase_shell_lowerings.json'
    return json.loads(path.read_text())


def test_phase_shell_lowerings_match_expected_rotation_formulas() -> None:
    lowerings = _load_phase_shell_lowerings()
    families = {row['name']: row for row in lowerings['families']}
    full_family = families['full_phase_register_v1']
    semiclassical_family = families['semiclassical_qft_v1']
    assert full_family['rotation_count'] == PHASE_BITS * (PHASE_BITS - 1) // 2
    assert full_family['controlled_rotation_count'] == full_family['rotation_count']
    assert full_family['rotation_depth'] == full_family['rotation_count']
    assert semiclassical_family['rotation_count'] == PHASE_BITS - 1
    assert semiclassical_family['single_qubit_rotation_count'] == semiclassical_family['rotation_count']
    assert semiclassical_family['rotation_depth'] == semiclassical_family['rotation_count']


def test_phase_shell_summary_is_derived_from_lowerings() -> None:
    lowerings = _load_phase_shell_lowerings()
    summary = json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'phase_shell_families.json').read_text())
    summary_rows = {row['name']: row for row in summary['families']}
    for family in lowerings['families']:
        summary_row = summary_rows[family['name']]
        assert summary_row['live_quantum_bits'] == family['live_quantum_bits']
        assert summary_row['hadamard_count'] == family['hadamard_count']
        assert summary_row['total_measurements'] == family['measurement_count']
        assert summary_row['total_rotations'] == family['rotation_count']
        assert summary_row['rotation_depth'] == family['rotation_depth']
