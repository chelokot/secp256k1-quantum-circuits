from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

from support import ensure_compiler_project_build_summary, ensure_compiler_project_verification_summary

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_SRC = REPO_ROOT / 'src'
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from integrity import evaluate_mutated_verification_groups, load_compiler_artifacts  # noqa: E402


def _load_artifacts() -> dict:
    ensure_compiler_project_build_summary()
    ensure_compiler_project_verification_summary()
    return load_compiler_artifacts(REPO_ROOT)


def test_compiler_project_frontier_and_schedule() -> None:
    build_path = ensure_compiler_project_build_summary()
    summary = json.loads(build_path.read_text())
    frontier_path = REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'family_frontier.json'
    frontier = json.loads(frontier_path.read_text())
    best_gate = min(frontier['families'], key=lambda row: (row['full_oracle_non_clifford'], row['total_logical_qubits']))
    best_qubit = min(frontier['families'], key=lambda row: (row['total_logical_qubits'], row['full_oracle_non_clifford']))
    assert summary['headline']['best_gate_family'] == frontier['best_gate_family'] == best_gate
    assert summary['headline']['best_qubit_family'] == frontier['best_qubit_family'] == best_qubit
    assert frontier['best_gate_family']['phase_shell'] == 'semiclassical_qft_v1'
    assert frontier['best_qubit_family']['phase_shell'] == 'semiclassical_qft_v1'


def test_compiler_project_verification_summary_groups_all_pass() -> None:
    verify_path = ensure_compiler_project_verification_summary()
    summary = json.loads(verify_path.read_text())
    assert summary['summary']['semantic_cases']['pass'] == summary['summary']['semantic_cases']['total']
    assert summary['summary']['invariant_checks']['pass'] == summary['summary']['invariant_checks']['total']
    for group_name, group in summary.items():
        if isinstance(group, dict) and 'checks' in group:
            assert group['pass'] == group['total'], group_name
    semantic = summary['semantic_replay']['summary']
    assert semantic['structured_cases'] > 0
    assert semantic['random_cases'] == 16
    assert semantic['phase_b_zero_cases'] > 0
    assert semantic['phase_b_nonzero_cases'] > 0
    lookup_lowering = summary['lookup_lowering_checks']
    assert lookup_lowering['pass'] == lookup_lowering['total']
    generated_block_inventory = summary['generated_block_inventory_checks']
    assert generated_block_inventory['pass'] == generated_block_inventory['total']


def test_mutated_frontier_family_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['family_frontier']['families'][0]['full_oracle_non_clifford'] += 1
    groups = evaluate_mutated_verification_groups(artifacts, REPO_ROOT)
    assert groups['frontier_checks']['pass'] < groups['frontier_checks']['total']
    assert groups['cain_transfer_checks']['pass'] < groups['cain_transfer_checks']['total']


def test_mutated_slot_assignment_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['exact_leaf_slot_allocation']['versions'][21]['assigned_slot'] = artifacts['exact_leaf_slot_allocation']['versions'][20]['assigned_slot']
    groups = evaluate_mutated_verification_groups(artifacts, REPO_ROOT)
    assert groups['slot_allocation_checks']['pass'] < groups['slot_allocation_checks']['total']


def test_mutated_lookup_lowering_stage_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['lookup_lowerings']['families'][0]['stages'][1]['blocks'][0]['non_clifford_total'] += 1
    groups = evaluate_mutated_verification_groups(artifacts, REPO_ROOT)
    assert groups['lookup_lowering_checks']['pass'] < groups['lookup_lowering_checks']['total']
    assert groups['frontier_checks']['pass'] < groups['frontier_checks']['total']


def test_mutated_generated_block_inventory_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['generated_block_inventories']['families'][0]['non_clifford_blocks'][0]['primitive_counts_total']['ccx'] += 1
    groups = evaluate_mutated_verification_groups(artifacts, REPO_ROOT)
    assert groups['generated_block_inventory_checks']['pass'] < groups['generated_block_inventory_checks']['total']


def test_mutated_full_attack_generated_summary_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['full_attack_inventory']['generated_block_inventory_summary']['family_reconstructed_totals'][0]['full_oracle_non_clifford'] += 1
    groups = evaluate_mutated_verification_groups(artifacts, REPO_ROOT)
    assert groups['full_attack_inventory_checks']['pass'] < groups['full_attack_inventory_checks']['total']


def test_mutated_cain_transfer_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['cain_exact_transfer']['families'][0]['heuristic_time_efficient_days_if_90M_maps_to_10d'] += 1.0
    groups = evaluate_mutated_verification_groups(artifacts, REPO_ROOT)
    assert groups['cain_transfer_checks']['pass'] < groups['cain_transfer_checks']['total']


def test_mutated_azure_seed_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['azure_resource_estimator_logical_counts']['families'][0]['logicalCounts']['numQubits'] += 1
    groups = evaluate_mutated_verification_groups(artifacts, REPO_ROOT)
    assert groups['azure_seed_checks']['pass'] < groups['azure_seed_checks']['total']
