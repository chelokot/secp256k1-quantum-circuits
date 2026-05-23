from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_SRC = REPO_ROOT / 'src'
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from integrity import build_tail_macro_engine_checks  # noqa: E402
from project import FIELD_BITS, build_streamed_lookup_tail_leaf  # noqa: E402
from tail_macro_engine import build_tail_macro_engine  # noqa: E402


def _load(name: str) -> dict:
    return json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / name).read_text())


def _kernel_costs() -> dict[str, int]:
    return {
        kernel['opcode']: int(kernel['exact_non_clifford_per_kernel'])
        for kernel in _load('arithmetic_lowerings.json')['kernels']
    }


def test_tail_macro_engine_reconstructs_checked_artifact() -> None:
    checked = _load('tail_macro_engine.json')
    costs = _kernel_costs()
    observed = build_tail_macro_engine(
        field_bits=FIELD_BITS,
        counted_arithmetic_slots=len(build_streamed_lookup_tail_leaf()['arithmetic_slots']),
        kernel_non_clifford_by_opcode=costs,
        selected_tail_kernel_non_clifford=costs[checked['opcode']],
    )
    assert observed == checked
    assert checked['pass'] is True
    assert checked['non_clifford_total'] == 1126842
    assert checked['opcode_histogram'] == {
        'field_add': 6,
        'field_mul': 6,
        'field_mul_lookup_sum': 1,
        'field_mul_lookup_x': 2,
        'field_mul_lookup_y': 2,
        'field_sub': 2,
        'field_sub_sum': 1,
        'field_triple': 1,
        'mul_const': 2,
    }


def test_tail_macro_engine_exposes_unclosed_three_slot_gap() -> None:
    checked = _load('tail_macro_engine.json')
    assert checked['checks']['counted_slots_cover_expanded_single_assignment_peak'] is False
    assert checked['slot_gap']['expanded_live_after_peak_field_values'] == 8
    assert checked['slot_gap']['expanded_single_assignment_peak_field_values'] == 9
    assert checked['slot_gap']['counted_arithmetic_slots'] == 3
    assert checked['slot_gap']['additional_logical_qubits_needed_without_in_place_schedule'] == 1536
    assert checked['expanded_slot_schedule']['peak_field_slots'] == 9
    assert sorted(checked['expanded_slot_schedule']['final_live_values']) == ['X3', 'Y3', 'Z3']
    assert checked['destructive_candidate_schedule']['status'] == 'optimizer_candidate_not_a_reversible_proof'
    assert checked['destructive_candidate_schedule']['peak_field_slots'] == 8
    assert checked['destructive_candidate_schedule']['proxy_metrics']['field_slot_improvement_vs_strict_single_assignment'] == 1
    assert checked['destructive_candidate_schedule']['local_inverse_certificate']['passing_row_count'] == 10
    assert checked['destructive_candidate_schedule']['local_inverse_certificate']['failing_row_count'] == 5
    assert checked['destructive_candidate_schedule']['overwrite_choice_screen']['choice_count'] == 23
    assert checked['destructive_candidate_schedule']['overwrite_choice_screen']['passing_choice_count'] == 16
    assert checked['destructive_candidate_schedule']['overwrite_choice_screen']['failing_choice_count'] == 7
    assert checked['destructive_candidate_schedule']['overwrite_choice_screen']['failing_row_indices'] == [1, 16, 17, 18, 19]
    assert checked['operand_overwrite_screen']['choice_count'] == 39
    assert checked['operand_overwrite_screen']['passing_choice_count'] == 26
    assert checked['operand_overwrite_screen']['failing_choice_count'] == 13
    assert checked['operand_overwrite_screen']['failing_row_indices'] == [1, 14, 15, 16, 17, 18, 19]
    assert checked['slot_gap']['destructive_candidate_overwrite_rows_locally_invertible'] is False
    assert checked['slot_gap']['overwrite_choice_screen_pass'] is False
    assert checked['slot_gap']['operand_overwrite_screen_pass'] is False
    assert checked['local_inverse_pass_only_schedule']['peak_field_slots'] == 9
    assert checked['slot_gap']['local_inverse_pass_only_peak_field_values'] == 9
    assert checked['reordered_local_inverse_schedule']['solution_found'] is True
    assert checked['reordered_local_inverse_schedule']['peak_field_slots'] == 8
    assert checked['reordered_local_inverse_schedule']['overwritten_row_count'] == 10
    assert checked['reordered_local_inverse_schedule']['invalid_overwrite_count'] == 0
    assert checked['reordered_local_inverse_schedule']['terminal_live_values'] == ['X3', 'Y3', 'Z3']
    assert checked['reordered_slot_assignment']['pass'] is True
    assert checked['reordered_slot_assignment']['peak_field_slots'] == 8
    assert checked['reordered_replay_certificate']['pass'] is True
    assert checked['reordered_replay_certificate']['owner_capacity_pass'] is True
    assert checked['reordered_replay_certificate']['checked_non_infinity_pairs'] == 110082
    assert checked['reordered_replay_certificate']['checked_lookup_infinity_pairs'] == 610
    assert checked['slot_gap']['reordered_local_inverse_solution_found'] is True
    assert checked['slot_gap']['reordered_local_inverse_peak_field_values'] == 8
    assert checked['slot_gap']['reordered_slot_assignment_peak_field_values'] == 8
    assert checked['slot_gap']['reordered_replay_pass'] is True
    assert checked['checks']['fused_output_stream_cost_matches_expanded_stream'] is True
    assert checked['checks']['fused_output_replay_passes'] is True
    assert checked['checks']['fused_output_schedule_reaches_seven_slots'] is True
    assert checked['checks']['fused_output_lowering_contract_passes'] is True
    assert checked['fused_output_reordered_schedule']['solution_found'] is True
    assert checked['fused_output_reordered_schedule']['peak_field_slots'] == 7
    assert checked['fused_output_slot_assignment']['pass'] is True
    assert checked['fused_output_slot_assignment']['peak_field_slots'] == 7
    assert checked['fused_output_replay_certificate']['pass'] is True
    assert checked['fused_output_replay_certificate']['owner_capacity_pass'] is True
    assert checked['fused_output_replay_certificate']['checked_non_infinity_pairs'] == 110082
    assert checked['fused_output_replay_certificate']['checked_lookup_infinity_pairs'] == 610
    assert checked['fused_output_lowering_contract']['overwritten_output_row_count'] == 1
    assert checked['fused_output_lowering_contract']['cost_matches_rows'] is True
    assert checked['fused_output_lowering_contract']['all_output_overwrites_have_boundary_permutation_contract'] is True
    assert checked['fused_output_lowering_contract']['rows'][1]['target'] == 'Y3'
    assert checked['fused_output_lowering_contract']['rows'][1]['schedule_overwritten_source'] == 'C'
    assert checked['fused_output_lowering_contract']['rows'][1]['overwrite_contract']['kind'] == 'secp256k1_zero_lifted_in_place_field_permutation'
    assert checked['fused_output_lowering_contract']['rows'][1]['overwrite_contract']['domain_rows_checked'] == 110082
    assert checked['fused_output_in_place_permutation_certificate']['pass'] is True
    assert checked['fused_output_in_place_permutation_certificate']['checks']['three_is_invertible_mod_secp256k1_p'] is True
    assert checked['fused_output_in_place_permutation_certificate']['checks']['l_zero_implies_accumulator_infinity_on_valid_non_infinity_lookup_domain'] is True
    assert checked['fused_output_in_place_permutation_certificate']['l_zero_domain_proof']['pass'] is True
    assert checked['fused_output_in_place_permutation_certificate']['guard']['logical_qubits'] == 1
    assert checked['fused_output_in_place_permutation_certificate']['guard']['non_clifford'] == 510
    assert checked['fused_output_in_place_permutation_certificate']['rejected_unguarded_output_reuse_counterexample']['m_value'] == 0
    assert checked['slot_gap']['fused_output_reordered_solution_found'] is True
    assert checked['slot_gap']['fused_output_reordered_peak_field_values'] == 7
    assert checked['slot_gap']['fused_output_slot_assignment_peak_field_values'] == 7
    assert checked['slot_gap']['fused_output_replay_pass'] is True
    assert checked['slot_gap']['destructive_candidate_peak_field_values'] == 8
    assert checked['completion_status'] == 'tail_cost_bound_to_expanded_field_operation_stream_but_in_place_schedule_unproven'
    assert checked['six_slot_pair_output_candidate']['pass'] is True
    assert checked['six_slot_pair_output_candidate']['peak_field_slots'] == 6
    assert checked['six_slot_pair_output_candidate']['status'] == 'semantic_candidate_not_promoted_to_public_headline'
    assert checked['six_slot_pair_output_candidate']['promotion_blocker']
    assert checked['pair_output_determinant_certificate']['pass'] is True
    assert checked['pair_output_determinant_certificate']['checks']['secp256k1_has_no_affine_y_zero_point'] is True
    assert checked['pair_output_determinant_certificate']['matrix']['determinant_equals'] == '-Y3'
    assert checked['six_slot_pair_output_candidate']['replay_certificate']['checked_non_infinity_pairs'] == 110082
    assert checked['six_slot_pair_output_candidate']['replay_certificate']['checked_lookup_infinity_pairs'] == 610


def test_tail_macro_engine_integrity_group_rejects_forged_cost() -> None:
    artifacts = {
        'tail_macro_engine': _load('tail_macro_engine.json'),
        'arithmetic_lowerings': _load('arithmetic_lowerings.json'),
        'streamed_lookup_tail_leaf': _load('streamed_lookup_tail_leaf.json'),
    }
    artifacts['tail_macro_engine']['non_clifford_total'] -= 1
    report = build_tail_macro_engine_checks(artifacts)
    assert report['pass'] < report['total']
    failed = {row['name'] for row in report['checks'] if row['pass'] == 0}
    assert 'tail_macro_engine_matches_generator' in failed
    assert 'tail_macro_engine_cost_binds_selected_tail_kernel' in failed


def test_tail_macro_engine_rejects_old_unguarded_y3_over_n() -> None:
    checked = _load('tail_macro_engine.json')
    counterexample = checked['fused_output_in_place_permutation_certificate']['rejected_unguarded_output_reuse_counterexample']
    y3_over_n = next(
        choice
        for choice in checked['fused_output_operand_screen']['choices']
        if choice['index'] == 15 and choice['overwritten_source'] == 'N'
    )

    assert counterexample['old_y3_over_n_coefficient'] == 'M'
    assert counterexample['m_value'] == 0
    assert y3_over_n['pass'] is False
    assert y3_over_n['failure_examples'][0]['m_value'] == 0


def test_tail_macro_engine_proves_lookup_infinity_is_bypassed() -> None:
    checked = _load('tail_macro_engine.json')
    replay = checked['fused_output_replay_certificate']
    proof = checked['fused_output_in_place_permutation_certificate']['l_zero_domain_proof']

    assert replay['checked_lookup_infinity_pairs'] > 0
    assert any('Lookup-infinity cases are checked as the external boundary no-op' in note for note in replay['notes'])
    assert any('bypassed for lookup-infinity rows' in premise for premise in proof['premises'])


def test_tail_macro_engine_six_slot_candidate_uses_pair_permutations() -> None:
    checked = _load('tail_macro_engine.json')
    candidate = checked['six_slot_pair_output_candidate']
    kinds = [row['kind'] for row in candidate['rows']]

    assert candidate['pass'] is True
    assert candidate['terminal_live_values'] == ['X3', 'Y3', 'Z3']
    assert 'in_place_mn_sum_difference_pair' in kinds
    assert 'in_place_xz_pair_output_matrix' in kinds
    assert max(row['live_field_value_count_during_step'] for row in candidate['rows']) == 6
    assert candidate['determinant_certificate']['matrix']['input_registers'] == ['E', 'K']
    assert candidate['determinant_certificate']['matrix']['output_registers'] == ['X3', 'Z3']


def test_tail_macro_engine_blocks_six_slot_promotion_without_variable_scale() -> None:
    checked = _load('tail_macro_engine.json')
    lowering = checked['six_slot_pair_output_lowering_search']

    assert lowering['pass'] is True
    assert lowering['promotion_ready'] is False
    assert lowering['status'] == 'blocked_on_variable_in_place_scale_lowering'
    assert lowering['checks']['shear_only_lowering_rejected_because_target_determinant_is_variable'] is True
    assert lowering['checks']['all_symbolic_lu_pivots_require_quantum_inverse_or_variable_scale'] is True
    assert lowering['checks']['current_kernel_inventory_lacks_required_variable_scale_primitive'] is True
    assert lowering['current_kernel_inventory']['has_variable_in_place_field_scale_without_extra_field_lane'] is False
    assert any(blocker['id'] == 'variable_scale_not_in_kernel_inventory' for blocker in lowering['blockers'])
