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
    assert checked['non_clifford_total'] == 1126332
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
    assert checked['fused_output_lowering_contract']['rows'][1]['schedule_overwritten_source'] == 'N'
    assert checked['fused_output_lowering_contract']['rows'][1]['overwrite_contract']['domain_rows_checked'] == 110082
    assert checked['slot_gap']['fused_output_reordered_solution_found'] is True
    assert checked['slot_gap']['fused_output_reordered_peak_field_values'] == 7
    assert checked['slot_gap']['fused_output_slot_assignment_peak_field_values'] == 7
    assert checked['slot_gap']['fused_output_replay_pass'] is True
    assert checked['slot_gap']['destructive_candidate_peak_field_values'] == 8
    assert checked['completion_status'] == 'tail_cost_bound_to_expanded_field_operation_stream_but_in_place_schedule_unproven'


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
