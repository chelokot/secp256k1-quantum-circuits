from __future__ import annotations

import json
import sys
from pathlib import Path

from support import ensure_compiler_project_build_summary, ensure_compiler_project_verification_summary


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from phase_shell_lowering import materialize_phase_operations  # noqa: E402

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


def test_phase_shell_operation_inventory_reconstructs_family_totals() -> None:
    lowerings = _load_phase_shell_lowerings()
    for family in lowerings['families']:
        reconstructed_family_counts = {
            'hadamard': 0,
            'measurement': 0,
            'single_qubit_rotation': 0,
            'controlled_rotation': 0,
            'rotation_depth': 0,
        }
        for stage in family['stages']:
            reconstructed_stage_counts = {
                'hadamard': 0,
                'measurement': 0,
                'single_qubit_rotation': 0,
                'controlled_rotation': 0,
                'rotation_depth': 0,
            }
            for block in stage['blocks']:
                reconstructed_block_counts = {
                    'hadamard': 0,
                    'measurement': 0,
                    'single_qubit_rotation': 0,
                    'controlled_rotation': 0,
                    'rotation_depth': 0,
                }
                for operation in materialize_phase_operations(block['phase_operation_generator']):
                    reconstructed_block_counts[operation[0]] += 1
                    if operation[0] in ('single_qubit_rotation', 'controlled_rotation'):
                        reconstructed_block_counts['rotation_depth'] += 1
                assert reconstructed_block_counts == block['count_profile_total']
                for key in reconstructed_stage_counts:
                    reconstructed_stage_counts[key] += reconstructed_block_counts[key]
            assert reconstructed_stage_counts == stage['count_profile_total']
            for key in reconstructed_family_counts:
                reconstructed_family_counts[key] += reconstructed_stage_counts[key]
        assert reconstructed_family_counts['hadamard'] == family['hadamard_count']
        assert reconstructed_family_counts['measurement'] == family['measurement_count']
        assert reconstructed_family_counts['single_qubit_rotation'] == family['single_qubit_rotation_count']
        assert reconstructed_family_counts['controlled_rotation'] == family['controlled_rotation_count']
        assert reconstructed_family_counts['rotation_depth'] == family['rotation_depth']


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
