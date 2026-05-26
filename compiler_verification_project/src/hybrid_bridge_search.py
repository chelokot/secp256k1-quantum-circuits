#!/usr/bin/env python3

from __future__ import annotations

from math import ceil, floor
from typing import Any, Dict, Mapping

from common import SECP_B, SECP_G, SECP_N, SECP_P, affine_to_proj, complete_projective_add_a0, mul_affine


HYBRID_BRIDGE_SEARCH_SCHEMA = 'compiler-project-hybrid-bridge-search-v1'


def _secp_denominator_witnesses() -> list[Dict[str, Any]]:
    rows = []
    for accumulator_scalar, lookup_scalar in ((1, 2), (3, 5), (7, 11), (13, 17)):
        accumulator = mul_affine(accumulator_scalar, SECP_G, SECP_P, SECP_B, order=SECP_N)
        lookup = mul_affine(lookup_scalar, SECP_G, SECP_P, SECP_B, order=SECP_N)
        projective = complete_projective_add_a0(affine_to_proj(accumulator, SECP_P), affine_to_proj(lookup, SECP_P), SECP_P, SECP_B)
        rows.append({
            'accumulator_scalar': accumulator_scalar,
            'lookup_scalar': lookup_scalar,
            'z3_hex': f'{projective[2] % SECP_P:064x}',
            'z3_is_one': projective[2] % SECP_P == 1,
            'z3_is_zero': projective[2] % SECP_P == 0,
        })
    inverse_lookup = mul_affine(SECP_N - 1, SECP_G, SECP_P, SECP_B, order=SECP_N)
    inverse_projective = complete_projective_add_a0(affine_to_proj(SECP_G, SECP_P), affine_to_proj(inverse_lookup, SECP_P), SECP_P, SECP_B)
    rows.append({
        'accumulator_scalar': 1,
        'lookup_scalar': SECP_N - 1,
        'case': 'inverse_pair',
        'z3_hex': f'{inverse_projective[2] % SECP_P:064x}',
        'z3_is_one': inverse_projective[2] % SECP_P == 1,
        'z3_is_zero': inverse_projective[2] % SECP_P == 0,
    })
    return rows


def build_hybrid_bridge_search(
    *,
    strict_replayed_tail_headline: Mapping[str, Any],
    reusable_chunk_lowering: Mapping[str, Any],
    non_clifford_limit_exclusive: int = 40_000_000,
    logical_qubit_limit_exclusive: int = 1_600,
) -> Dict[str, Any]:
    selected = strict_replayed_tail_headline['selected_result']
    formula = strict_replayed_tail_headline['logical_qubit_formula']
    non_clifford_formula = strict_replayed_tail_headline['non_clifford_formula']
    qubit_derivation = reusable_chunk_lowering['qubit_derivation']
    stream_plan = reusable_chunk_lowering['stream_plan']

    field_bits = int(formula['field_bits'])
    lookup_workspace_qubits = int(formula['lookup_workspace_qubits'])
    non_field_qubits = int(formula['lookup_workspace_qubits']) + int(formula['control_qubits']) + int(formula['phase_qubits'])
    max_field_slots_with_current_lookup = floor((logical_qubit_limit_exclusive - 1 - non_field_qubits) / field_bits)

    six_slot_non_field_budget = logical_qubit_limit_exclusive - 1 - 6 * field_bits
    six_slot_lookup_workspace_budget = six_slot_non_field_budget - int(formula['control_qubits']) - int(formula['phase_qubits'])
    chunk_bits_for_six_slot_budget = max(1, six_slot_lookup_workspace_budget - int(qubit_derivation['folded_control_workspace_qubits']))
    chunks_per_coordinate_for_six_slot_budget = ceil(field_bits / chunk_bits_for_six_slot_budget)
    coordinate_table_count = int(stream_plan['coordinate_table_count'])
    leaf_call_count_total = int(stream_plan['leaf_call_count_total'])
    qroam_streams_for_six_slot_budget = coordinate_table_count * chunks_per_coordinate_for_six_slot_budget * leaf_call_count_total
    qroam_non_clifford_for_six_slot_budget = qroam_streams_for_six_slot_budget * int(non_clifford_formula['per_chunk_stream_non_clifford'])
    six_slot_with_reduced_lookup_non_clifford = int(non_clifford_formula['base_non_clifford_without_streamed_qroam']) + qroam_non_clifford_for_six_slot_budget

    corrected_public_envelope = {
        'source': 'downloaded supporting_data.zip low_qubit_circuit.json arithmetic check',
        'claimed_point_add_logical_qubits': 1175,
        'listed_register_qubits': 1431,
        'missing_field_lane_qubits': 256,
        'corrected_ecdlp_logical_qubits_with_window_key': 1447,
        'claimed_ecdlp_non_clifford': 81105024,
        'fits_logical_qubit_limit': 1447 < logical_qubit_limit_exclusive,
        'fits_non_clifford_limit': 81105024 < non_clifford_limit_exclusive,
    }

    z_witnesses = _secp_denominator_witnesses()
    denominator_varies = len({row['z3_hex'] for row in z_witnesses}) > 1
    inverse_pair_reaches_infinity = any(row.get('case') == 'inverse_pair' and row['z3_is_zero'] for row in z_witnesses)

    candidates = [
        {
            'name': 'current_strict_projective_seven_slot',
            'logical_qubits': int(selected['logical_qubits']),
            'non_clifford': int(selected['non_clifford']),
            'field_slots': int(selected['tail_field_slots']),
            'status': 'proven_current_strict_baseline',
            'fits_logical_qubit_limit': int(selected['logical_qubits']) < logical_qubit_limit_exclusive,
            'fits_non_clifford_limit': int(selected['non_clifford']) < non_clifford_limit_exclusive,
            'blocker': 'qubit_count_above_target',
        },
        {
            'name': 'projective_six_slot_with_current_lookup_workspace',
            'logical_qubits': 6 * field_bits + non_field_qubits,
            'non_clifford': int(selected['non_clifford']),
            'field_slots': 6,
            'status': 'numeric_projection_only_not_lowered',
            'fits_logical_qubit_limit': 6 * field_bits + non_field_qubits < logical_qubit_limit_exclusive,
            'fits_non_clifford_limit': int(selected['non_clifford']) < non_clifford_limit_exclusive,
            'blocker': 'six field slots still exceed the qubit target with the strict reusable QROAM workspace',
        },
        {
            'name': 'projective_six_slot_with_lookup_workspace_reduced_to_fit',
            'logical_qubits': 6 * field_bits + six_slot_lookup_workspace_budget + int(formula['control_qubits']) + int(formula['phase_qubits']),
            'non_clifford': six_slot_with_reduced_lookup_non_clifford,
            'field_slots': 6,
            'status': 'derived_lower_bound_fails_gate_budget',
            'fits_logical_qubit_limit': True,
            'fits_non_clifford_limit': six_slot_with_reduced_lookup_non_clifford < non_clifford_limit_exclusive,
            'blocker': 'forcing lookup workspace below the six-slot qubit budget requires enough QROAM chunk streams to exceed the non-Clifford target',
        },
        {
            'name': 'projective_five_slot_no_inverse_core',
            'logical_qubits': 5 * field_bits + non_field_qubits,
            'non_clifford': int(selected['non_clifford']),
            'field_slots': 5,
            'status': 'only_numeric_target_that_would_fit_current_lookup_and_gate_budget',
            'fits_logical_qubit_limit': 5 * field_bits + non_field_qubits < logical_qubit_limit_exclusive,
            'fits_non_clifford_limit': int(selected['non_clifford']) < non_clifford_limit_exclusive,
            'blocker': 'no executable five-field-slot no-inverse projective schedule or primitive lowering is known',
        },
        {
            'name': 'corrected_affine_inversion_public_envelope',
            'logical_qubits': corrected_public_envelope['corrected_ecdlp_logical_qubits_with_window_key'],
            'non_clifford': corrected_public_envelope['claimed_ecdlp_non_clifford'],
            'status': 'corrected_external_envelope_not_primitive_proven',
            'fits_logical_qubit_limit': corrected_public_envelope['fits_logical_qubit_limit'],
            'fits_non_clifford_limit': corrected_public_envelope['fits_non_clifford_limit'],
            'blocker': 'normalizing the accumulator to affine after every dependent point addition pays an inverse-heavy gate budget',
        },
    ]
    periodic_normalization_rows = [
        {
            'normalization_period_retained_additions': 1,
            'logical_qubits_lower_bound': corrected_public_envelope['corrected_ecdlp_logical_qubits_with_window_key'],
            'non_clifford_reference': corrected_public_envelope['claimed_ecdlp_non_clifford'],
            'status': 'affine_every_step_fits_qubits_not_gates',
            'fits_logical_qubit_limit': corrected_public_envelope['fits_logical_qubit_limit'],
            'fits_non_clifford_limit': corrected_public_envelope['fits_non_clifford_limit'],
            'blocker': 'one field inverse per dependent retained addition keeps the non-Clifford count above the target',
        },
    ]
    for normalization_period in (2, 4, 7, 14, 28):
        periodic_normalization_rows.append({
            'normalization_period_retained_additions': normalization_period,
            'logical_qubits_lower_bound': int(selected['logical_qubits']),
            'non_clifford_reference': int(selected['non_clifford']),
            'status': 'projective_state_required_between_normalizations',
            'fits_logical_qubit_limit': int(selected['logical_qubits']) < logical_qubit_limit_exclusive,
            'fits_non_clifford_limit': int(selected['non_clifford']) < non_clifford_limit_exclusive,
            'blocker': 'any period greater than one must carry projective X/Y/Z state across at least one dependent addition before normalization, so the peak inherits the strict projective register footprint before inverse workspace is added',
        })

    checks = {
        'current_strict_baseline_fits_gate_not_qubits': int(selected['non_clifford']) < non_clifford_limit_exclusive and int(selected['logical_qubits']) >= logical_qubit_limit_exclusive,
        'current_lookup_workspace_allows_at_most_five_field_slots_under_target': max_field_slots_with_current_lookup == 5,
        'six_slot_current_lookup_fails_qubit_target': 6 * field_bits + non_field_qubits >= logical_qubit_limit_exclusive,
        'six_slot_reduced_lookup_fails_non_clifford_target': six_slot_with_reduced_lookup_non_clifford >= non_clifford_limit_exclusive,
        'corrected_affine_line_fits_qubits_not_gates': corrected_public_envelope['fits_logical_qubit_limit'] is True and corrected_public_envelope['fits_non_clifford_limit'] is False,
        'periodic_normalization_has_no_target_fitting_row': not any(
            row['fits_logical_qubit_limit'] and row['fits_non_clifford_limit']
            for row in periodic_normalization_rows
        ),
        'affine_projective_denominator_is_not_constant': denominator_varies,
        'affine_inverse_pair_denominator_reaches_zero': inverse_pair_reaches_infinity,
        'only_numeric_survivor_requires_unproven_five_slot_no_inverse_core': all(
            row['fits_logical_qubit_limit'] and row['fits_non_clifford_limit']
            for row in candidates
            if row['name'] == 'projective_five_slot_no_inverse_core'
        ),
    }
    return {
        'schema': HYBRID_BRIDGE_SEARCH_SCHEMA,
        'status': 'blocked_no_promotable_hybrid_found',
        'target': {
            'logical_qubits_exclusive': logical_qubit_limit_exclusive,
            'non_clifford_exclusive': non_clifford_limit_exclusive,
        },
        'source_strict_result': {
            'name': selected['name'],
            'logical_qubits': int(selected['logical_qubits']),
            'non_clifford': int(selected['non_clifford']),
            'field_slots': int(selected['tail_field_slots']),
        },
        'strict_qubit_budget_analysis': {
            'field_bits': field_bits,
            'lookup_workspace_qubits': lookup_workspace_qubits,
            'non_field_qubits': non_field_qubits,
            'max_field_slots_with_current_lookup_workspace': max_field_slots_with_current_lookup,
            'six_slot_lookup_workspace_budget': six_slot_lookup_workspace_budget,
            'six_slot_required_lookup_workspace_reduction': lookup_workspace_qubits - six_slot_lookup_workspace_budget,
        },
        'strict_lookup_chunk_tradeoff_for_six_slots': {
            'chunk_bits_budget': chunk_bits_for_six_slot_budget,
            'chunks_per_coordinate': chunks_per_coordinate_for_six_slot_budget,
            'coordinate_table_count': coordinate_table_count,
            'leaf_call_count_total': leaf_call_count_total,
            'qroam_streams': qroam_streams_for_six_slot_budget,
            'qroam_non_clifford': qroam_non_clifford_for_six_slot_budget,
            'base_non_clifford_without_streamed_qroam': int(non_clifford_formula['base_non_clifford_without_streamed_qroam']),
            'total_non_clifford_lower_bound': six_slot_with_reduced_lookup_non_clifford,
        },
        'affine_boundary_obstruction': {
            'claim': 'A low-qubit affine boundary can drop the carried Z lane only by normalizing each dependent point-add result or by reintroducing projective state across calls.',
            'secp256k1_denominator_witnesses': z_witnesses,
            'denominator_varies': denominator_varies,
            'inverse_pair_reaches_infinity': inverse_pair_reaches_infinity,
            'sequential_dependency': 'Batch inversion across retained point additions requires carrying projective X/Y/Z state between additions; otherwise the next affine add has no normalized accumulator input.',
        },
        'periodic_normalization_search': {
            'retained_addition_count': leaf_call_count_total,
            'rows': periodic_normalization_rows,
            'result': 'no row fits both the logical-qubit and non-Clifford target under the current proven primitive inventory',
        },
        'corrected_public_envelope': corrected_public_envelope,
        'candidate_rows': candidates,
        'next_required_breakthrough': {
            'primary': 'executable five-field-slot no-inverse projective core under the strict lookup workspace',
            'secondary': 'new standard-QROM lookup/workspace construction that keeps six projective slots under the qubit target without pushing non-Clifford above the gate target',
            'not_enough': 'affine boundary alone; it fits qubits only by paying inverse-heavy non-Clifford cost',
        },
        'checks': checks,
        'pass': all(checks.values()),
    }


__all__ = ['HYBRID_BRIDGE_SEARCH_SCHEMA', 'build_hybrid_bridge_search']
