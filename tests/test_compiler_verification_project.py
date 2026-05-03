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


def _evaluate_mutation(artifacts: dict, *group_names: str) -> dict:
    return evaluate_mutated_verification_groups(artifacts, REPO_ROOT, group_names=group_names)


def test_compiler_project_frontier_and_schedule() -> None:
    build_path = ensure_compiler_project_build_summary()
    summary = json.loads(build_path.read_text())
    frontier_path = REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'family_frontier.json'
    frontier = json.loads(frontier_path.read_text())
    best_gate = min(frontier['families'], key=lambda row: (row['full_oracle_non_clifford'], row['total_logical_qubits']))
    best_qubit = min(frontier['families'], key=lambda row: (row['total_logical_qubits'], row['full_oracle_non_clifford']))
    assert summary['headline']['best_gate_family'] == frontier['best_gate_family'] == best_gate
    assert summary['headline']['best_qubit_family'] == frontier['best_qubit_family'] == best_qubit
    assert summary['headline']['best_google_low_gate_qubit_family'] == frontier['best_google_low_gate_qubit_family']
    assert summary['headline']['best_sub30m_qubit_family'] == frontier['best_sub30m_qubit_family']
    assert frontier['best_gate_family']['phase_shell'] == 'semiclassical_qft_v1'
    assert frontier['best_qubit_family']['phase_shell'] == 'semiclassical_qft_v1'
    assert frontier['best_google_low_gate_qubit_family']['full_oracle_non_clifford'] < 70_000_000
    assert frontier['best_sub30m_qubit_family'] is None


def test_qubit_breakthrough_analysis_thresholds_are_self_consistent() -> None:
    build_path = ensure_compiler_project_build_summary()
    assert build_path.exists()
    frontier = json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'family_frontier.json').read_text())
    analysis = json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'qubit_breakthrough_analysis.json').read_text())
    best_qubit = frontier['best_qubit_family']
    fixed_overhead = (
        best_qubit['lookup_workspace_qubits']
        + best_qubit['control_slot_count']
        + best_qubit.get('borrowed_interface_qubits', 0)
        + best_qubit['live_phase_bits']
    )
    assert analysis['best_exact_qubit_family'] == best_qubit
    assert analysis['exact_component_breakdown']['arithmetic_register_file_qubits'] == best_qubit['arithmetic_slot_count'] * 256
    assert analysis['exact_component_breakdown']['fixed_non_arithmetic_overhead_qubits'] == fixed_overhead
    assert analysis['baseline_thresholds']['low_gate']['max_arithmetic_slots_at_current_field_width'] == (1450 - fixed_overhead) // 256
    assert analysis['baseline_thresholds']['low_qubit']['max_arithmetic_slots_at_current_field_width'] == (1200 - fixed_overhead) // 256
    assert analysis['baseline_thresholds']['low_gate']['max_field_slot_logical_qubits_at_current_exact_slot_count'] == (1450 - fixed_overhead) // best_qubit['arithmetic_slot_count']
    assert analysis['baseline_thresholds']['low_qubit']['max_field_slot_logical_qubits_at_current_exact_slot_count'] == (1200 - fixed_overhead) // best_qubit['arithmetic_slot_count']
    assert analysis['modeled_reference_points']['addsub_modmul_named_slots_v2']['logical_qubits_total'] == 592
    assert analysis['modeled_reference_points']['addsub_modmul_liveness_v2']['logical_qubits_total'] == 520


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
    phase_shell_lowering = summary['phase_shell_lowering_checks']
    assert phase_shell_lowering['pass'] == phase_shell_lowering['total']
    cleanup_pair = summary['cleanup_pair_checks']
    assert cleanup_pair['pass'] == cleanup_pair['total']
    generated_block_inventory = summary['generated_block_inventory_checks']
    assert generated_block_inventory['pass'] == generated_block_inventory['total']
    ft_ir = summary['ft_ir_checks']
    assert ft_ir['pass'] == ft_ir['total']
    lookup_fed_slot_allocation = summary['lookup_fed_slot_allocation_checks']
    assert lookup_fed_slot_allocation['pass'] == lookup_fed_slot_allocation['total']
    streamed_lookup_tail_slot_allocation = summary['streamed_lookup_tail_slot_allocation_checks']
    assert streamed_lookup_tail_slot_allocation['pass'] == streamed_lookup_tail_slot_allocation['total']
    streamed_lookup_table_multiplier_resource = summary['streamed_lookup_table_multiplier_resource_checks']
    assert streamed_lookup_table_multiplier_resource['pass'] == streamed_lookup_table_multiplier_resource['total']
    standard_qrom_lookup_assessment = summary['standard_qrom_lookup_assessment_checks']
    assert standard_qrom_lookup_assessment['pass'] == standard_qrom_lookup_assessment['total']
    logical_resource_ledger = summary['logical_resource_ledger_checks']
    assert logical_resource_ledger['pass'] == logical_resource_ledger['total']
    recount = summary['whole_oracle_recount_checks']
    assert recount['pass'] == recount['total']
    subcircuit_equivalence = summary['subcircuit_equivalence_checks']
    assert subcircuit_equivalence['pass'] == subcircuit_equivalence['total']
    physical_estimator_targets = summary['physical_estimator_target_checks']
    assert physical_estimator_targets['pass'] == physical_estimator_targets['total']
    physical_estimator_results = summary['physical_estimator_result_checks']
    assert physical_estimator_results['pass'] == physical_estimator_results['total']


def test_mutated_frontier_family_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['family_frontier']['families'][0]['full_oracle_non_clifford'] += 1
    groups = _evaluate_mutation(artifacts, 'frontier_checks', 'cain_transfer_checks')
    assert groups['frontier_checks']['pass'] < groups['frontier_checks']['total']
    assert groups['cain_transfer_checks']['pass'] < groups['cain_transfer_checks']['total']


def test_mutated_slot_assignment_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['exact_leaf_slot_allocation']['versions'][1]['assigned_slot'] = artifacts['exact_leaf_slot_allocation']['versions'][0]['assigned_slot']
    groups = _evaluate_mutation(artifacts, 'slot_allocation_checks')
    assert groups['slot_allocation_checks']['pass'] < groups['slot_allocation_checks']['total']


def test_mutated_qubit_breakthrough_analysis_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['qubit_breakthrough_analysis']['baseline_thresholds']['low_gate']['max_arithmetic_slots_at_current_field_width'] += 1
    groups = _evaluate_mutation(artifacts, 'qubit_breakthrough_checks')
    assert groups['qubit_breakthrough_checks']['pass'] < groups['qubit_breakthrough_checks']['total']


def test_mutated_lookup_lowering_stage_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['lookup_lowerings']['families'][0]['stages'][1]['blocks'][0]['primitive_operation_generator']['bit_count'] += 1
    groups = _evaluate_mutation(artifacts, 'lookup_lowering_checks')
    assert groups['lookup_lowering_checks']['pass'] < groups['lookup_lowering_checks']['total']


def test_mutated_standard_qrom_assessment_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['standard_qrom_lookup_assessment']['standard_qrom_gap']['standard_qrom_equivalent'] = False
    groups = _evaluate_mutation(artifacts, 'standard_qrom_lookup_assessment_checks')
    assert groups['standard_qrom_lookup_assessment_checks']['pass'] < groups['standard_qrom_lookup_assessment_checks']['total']


def test_mutated_qroam_workspace_capacity_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['streamed_lookup_table_multiplier_resource']['workspace_contract']['qroam_clean_junk_register_qubits'] -= 256
    groups = _evaluate_mutation(artifacts, 'streamed_lookup_table_multiplier_resource_checks', 'logical_resource_ledger_checks')
    assert groups['streamed_lookup_table_multiplier_resource_checks']['pass'] < groups['streamed_lookup_table_multiplier_resource_checks']['total']
    assert groups['logical_resource_ledger_checks']['pass'] < groups['logical_resource_ledger_checks']['total']


def test_mutated_logical_resource_owner_capacity_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['logical_resource_ledger']['peak_live_qubit_owners'][2]['decomposition']['qroam_clean_target_register_qubits'] -= 1
    groups = _evaluate_mutation(artifacts, 'logical_resource_ledger_checks')
    assert groups['logical_resource_ledger_checks']['pass'] < groups['logical_resource_ledger_checks']['total']


def test_mutated_phase_shell_lowering_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['phase_shell_lowerings']['families'][0]['stages'][0]['blocks'][0]['phase_operation_generator']['phase_bits'] -= 1
    groups = _evaluate_mutation(artifacts, 'phase_shell_lowering_checks')
    assert groups['phase_shell_lowering_checks']['pass'] < groups['phase_shell_lowering_checks']['total']


def test_mutated_cleanup_pair_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['module_library']['leaf_opcode_histogram']['select_field_if_flag'] = 1
    groups = _evaluate_mutation(artifacts, 'cleanup_pair_checks')
    assert groups['cleanup_pair_checks']['pass'] < groups['cleanup_pair_checks']['total']


def test_mutated_arithmetic_lowering_stage_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['arithmetic_lowerings']['kernels'][0]['stages'][0]['blocks'][0]['primitive_operations'].append(['ccx', 999999, 999999])
    groups = _evaluate_mutation(artifacts, 'arithmetic_kernel_checks')
    assert groups['arithmetic_kernel_checks']['pass'] < groups['arithmetic_kernel_checks']['total']


def test_mutated_generated_block_inventory_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['generated_block_inventories']['families'][0]['non_clifford_blocks'][0]['primitive_counts_total']['ccx'] += 1
    groups = _evaluate_mutation(artifacts, 'generated_block_inventory_checks')
    assert groups['generated_block_inventory_checks']['pass'] < groups['generated_block_inventory_checks']['total']


def test_mutated_ft_ir_edge_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['ft_ir_compositions']['families'][0]['graph']['edges'][0]['count'] += 1
    groups = _evaluate_mutation(artifacts, 'ft_ir_checks')
    assert groups['ft_ir_checks']['pass'] < groups['ft_ir_checks']['total']


def test_mutated_whole_oracle_recount_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['whole_oracle_recount']['families'][0]['full_oracle_non_clifford'] += 1
    groups = _evaluate_mutation(artifacts, 'whole_oracle_recount_checks')
    assert groups['whole_oracle_recount_checks']['pass'] < groups['whole_oracle_recount_checks']['total']


def test_mutated_full_attack_generated_summary_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['full_attack_inventory']['generated_block_inventory_summary']['family_reconstructed_totals'][0]['full_oracle_non_clifford'] += 1
    groups = _evaluate_mutation(artifacts, 'full_attack_inventory_checks')
    assert groups['full_attack_inventory_checks']['pass'] < groups['full_attack_inventory_checks']['total']


def test_mutated_cain_transfer_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['cain_exact_transfer']['families'][0]['heuristic_time_efficient_days_if_90M_maps_to_10d'] += 1.0
    groups = _evaluate_mutation(artifacts, 'cain_transfer_checks')
    assert groups['cain_transfer_checks']['pass'] < groups['cain_transfer_checks']['total']


def test_mutated_azure_seed_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['azure_resource_estimator_logical_counts']['families'][0]['logicalCounts']['numQubits'] += 1
    groups = _evaluate_mutation(artifacts, 'azure_seed_checks', 'physical_estimator_target_checks')
    assert groups['azure_seed_checks']['pass'] < groups['azure_seed_checks']['total']
    assert groups['physical_estimator_target_checks']['pass'] < groups['physical_estimator_target_checks']['total']


def test_mutated_physical_estimator_target_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['azure_resource_estimator_targets']['targets'][0]['requested_params']['errorBudget'] = 0.01
    groups = _evaluate_mutation(artifacts, 'physical_estimator_target_checks', 'physical_estimator_result_checks')
    assert groups['physical_estimator_target_checks']['pass'] < groups['physical_estimator_target_checks']['total']
    assert groups['physical_estimator_result_checks']['pass'] < groups['physical_estimator_result_checks']['total']


def test_mutated_physical_estimator_result_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['azure_resource_estimator_results']['families'][0]['estimates'][0]['physical_counts']['physicalQubits'] += 1
    groups = _evaluate_mutation(artifacts, 'physical_estimator_result_checks')
    assert groups['physical_estimator_result_checks']['pass'] < groups['physical_estimator_result_checks']['total']


def test_mutated_subcircuit_equivalence_is_detected() -> None:
    artifacts = deepcopy(_load_artifacts())
    artifacts['subcircuit_equivalence']['whole_oracle_composition_equivalence']['families'][0]['frontier_full_oracle_non_clifford'] += 1
    groups = _evaluate_mutation(artifacts, 'subcircuit_equivalence_checks')
    assert groups['subcircuit_equivalence_checks']['pass'] < groups['subcircuit_equivalence_checks']['total']
