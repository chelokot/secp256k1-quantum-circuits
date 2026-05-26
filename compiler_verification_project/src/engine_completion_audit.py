#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping

from public_engine_contract import (
    CANONICAL_MATERIALIZED_FLAT_NETLIST,
    LEGACY_WRAPPER_MATERIALIZED_FLAT_NETLIST,
    PUBLIC_ENGINE_CANONICAL_TOTALS_SOURCE,
    PUBLIC_TOTALS_DERIVE_FROM_CANONICAL_CHECK,
    STRICT_REPLAYED_TAIL_MATERIALIZED_FLAT_NETLIST,
)
from modular_accumulator_full_adder_contract import FULL_ADDER_CONTRACT_UNPROMOTED_STATUS
from modular_accumulator_full_adder_stream import FULL_ADDER_STREAM_UNPROMOTED_STATUS


ENGINE_COMPLETION_AUDIT_SCHEMA = 'compiler-project-engine-completion-audit-v1'


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def _source_digests(sources: Mapping[str, Mapping[str, Any]]) -> Dict[str, str]:
    return {
        f'{name}_sha256': _sha256_payload(payload)
        for name, payload in sorted(sources.items())
    }


def build_engine_completion_audit(
    *,
    public_engine_manifest: Mapping[str, Any],
    public_candidate_materialized_circuit_manifest: Mapping[str, Any],
    arithmetic_operand_replay_audit: Mapping[str, Any],
    reusable_chunk_lowering: Mapping[str, Any],
    arithmetic_operation_ir: Mapping[str, Any],
    lookup_lowerings: Mapping[str, Any],
    qroam_primitive_certificate: Mapping[str, Any],
    qroam_table_cnot_materialization: Mapping[str, Any],
    phase_shell_lowerings: Mapping[str, Any],
    release_corpus_preflight: Mapping[str, Any],
    streamed_lookup_tail_leaf_equivalence: Mapping[str, Any],
    modular_arithmetic_certificate: Mapping[str, Any],
    modular_execution_trace: Mapping[str, Any],
    scheduled_modular_primitive_netlist: Mapping[str, Any],
    modular_primitive_wire_audit: Mapping[str, Any],
    modular_multiplier_lifecycle: Mapping[str, Any],
    modular_accumulator_lowering: Mapping[str, Any],
    modular_accumulator_row_stream: Mapping[str, Any],
    modular_accumulator_capacity_certificate: Mapping[str, Any],
    modular_accumulator_scratch_schedule: Mapping[str, Any],
    modular_accumulator_semantic_obligations: Mapping[str, Any],
    modular_accumulator_carry_obligations: Mapping[str, Any],
    modular_accumulator_carry_save_candidate: Mapping[str, Any],
    modular_accumulator_full_adder_contract: Mapping[str, Any],
    modular_accumulator_full_adder_stream: Mapping[str, Any],
    tail_macro_engine: Mapping[str, Any],
    tail_macro_liveness: Mapping[str, Any],
    tail_macro_reversibility: Mapping[str, Any],
    tail_macro_schedule_search: Mapping[str, Any],
    compiler_parameters: Mapping[str, Any],
    zkp_attestation_input: Mapping[str, Any],
) -> Dict[str, Any]:
    selected_family_name = str(compiler_parameters['public_headline_policy']['selected_public_family_name'])
    materialized_flat = public_candidate_materialized_circuit_manifest[LEGACY_WRAPPER_MATERIALIZED_FLAT_NETLIST]
    canonical_materialized_flat = public_candidate_materialized_circuit_manifest[CANONICAL_MATERIALIZED_FLAT_NETLIST]
    canonical_physical_flat = public_candidate_materialized_circuit_manifest['canonical_physical_flat_netlist']
    strict_materialized_flat = public_candidate_materialized_circuit_manifest[STRICT_REPLAYED_TAIL_MATERIALIZED_FLAT_NETLIST]
    strict_completeness = public_candidate_materialized_circuit_manifest['strict_primitive_completeness']
    modular_engine_integration = public_candidate_materialized_circuit_manifest['modular_arithmetic_engine_integration']
    source_binding = public_candidate_materialized_circuit_manifest['operand_source_binding']
    parent_binding = public_candidate_materialized_circuit_manifest['operand_parent_binding']
    rows_by_source_kind = {
        str(name): int(count)
        for name, count in source_binding['rows_by_source_kind'].items()
    }
    expected_source_kinds = {
        'arithmetic_operation_ir',
        'lookup_lowering_block',
        'phase_shell_lowering',
        'qroam_primitive_certificate',
    }
    public_totals = {
        'non_clifford': int(canonical_materialized_flat['non_clifford_count']),
        'logical_qubits': int(canonical_materialized_flat['peak_live_qubits']),
        'operation_count': int(canonical_materialized_flat['operation_count']),
        'source': PUBLIC_ENGINE_CANONICAL_TOTALS_SOURCE,
    }
    zkp_claim_summary = zkp_attestation_input['claim_summary']
    zkp_public_engine_document = zkp_attestation_input['public_engine_manifest_document']
    zkp_physical_boundary = zkp_claim_summary['physical_boundary_summary']
    public_engine_physical_manifest = public_engine_manifest['primitive_operation_evidence']['public_candidate_materialized_circuit_manifest']
    scheduled_modular_splice = public_engine_physical_manifest['scheduled_modular_global_splice']
    scheduled_modular_leaf = public_engine_physical_manifest['scheduled_modular_primitive_netlist']
    arithmetic_leaf_summary = arithmetic_operation_ir['leaf_arithmetic_summary']
    qroam_counts = qroam_primitive_certificate['traversed_counts']
    qroam_cost = qroam_primitive_certificate['qroamclean_cost_model']
    release_categories = {
        str(category): int(count)
        for category, count in release_corpus_preflight['category_counts'].items()
    }
    required_semantic_categories = [
        'random',
        'doubling',
        'inverse',
        'accumulator_infinity',
        'lookup_infinity',
    ]
    checks = {
        PUBLIC_TOTALS_DERIVE_FROM_CANONICAL_CHECK: (
            public_engine_manifest['public_totals']['source'] == public_totals['source']
            and int(public_engine_manifest['public_totals']['non_clifford']) == public_totals['non_clifford']
            and int(public_engine_manifest['public_totals']['logical_qubits']) == public_totals['logical_qubits']
            and public_candidate_materialized_circuit_manifest['public_totals']['non_clifford'] == public_totals['non_clifford']
            and public_candidate_materialized_circuit_manifest['public_totals']['logical_qubits'] == public_totals['logical_qubits']
            and public_candidate_materialized_circuit_manifest['checks'][PUBLIC_TOTALS_DERIVE_FROM_CANONICAL_CHECK] is True
        ),
        'legacy_materialized_flat_stream_is_exact_and_counted': (
            materialized_flat['exact_operation_stream_materialized'] is True
            and public_candidate_materialized_circuit_manifest['checks']['materialized_flat_netlist_stream_is_exact'] is True
            and public_candidate_materialized_circuit_manifest['checks']['materialized_flat_netlist_counts_match_index_netlist'] is True
            and public_candidate_materialized_circuit_manifest['checks']['flat_netlist_non_clifford_matches_public_candidate'] is True
        ),
        'strict_materialized_flat_stream_is_exact_and_counted': (
            strict_materialized_flat['exact_operation_stream_materialized'] is True
            and public_candidate_materialized_circuit_manifest['checks']['strict_replayed_tail_materialized_flat_netlist_is_bound'] is True
            and public_candidate_materialized_circuit_manifest['checks']['strict_replayed_tail_materialized_flat_netlist_segments_cover_stream'] is True
            and public_candidate_materialized_circuit_manifest['checks']['strict_replayed_tail_materialized_flat_netlist_preview_rows_are_concrete'] is True
            and int(strict_materialized_flat['operation_count']) == int(materialized_flat['operation_count'])
            and int(strict_materialized_flat['non_clifford_count']) == int(materialized_flat['non_clifford_count'])
        ),
        'run_length_rows_are_primitive_complete': (
            strict_completeness['clifford_complete'] is True
            and int(strict_completeness['rows_checked']) == int(public_candidate_materialized_circuit_manifest['run_length_row_count'])
            and int(strict_completeness['incomplete_row_count']) == 0
        ),
        'operand_domains_bind_counted_live_wires': (
            parent_binding['pass'] is True
            and public_candidate_materialized_circuit_manifest['checks']['primitive_operand_domains_bind_counted_live_parent_wires'] is True
            and public_candidate_materialized_circuit_manifest['checks']['primitive_operand_contract_owners_are_known_and_live'] is True
            and public_candidate_materialized_circuit_manifest['checks']['flat_execution_probe_operand_owners_are_live_and_within_capacity'] is True
        ),
        'source_binding_covers_every_run_length_row': (
            source_binding['pass'] is True
            and int(source_binding['rows_checked']) == int(public_candidate_materialized_circuit_manifest['run_length_row_count'])
            and sum(rows_by_source_kind.values()) == int(source_binding['rows_checked'])
            and set(rows_by_source_kind) == expected_source_kinds
            and all(rows_by_source_kind[name] > 0 for name in expected_source_kinds)
        ),
        'qroam_rows_bind_standard_qroam_primitive_costs': (
            qroam_primitive_certificate['pass'] is True
            and rows_by_source_kind['qroam_primitive_certificate'] == int(public_engine_manifest['primitive_operation_evidence']['public_candidate_materialized_circuit_manifest']['qroam_segment_row_count'])
            and int(qroam_counts['per_stream_non_clifford']) == int(qroam_cost['per_stream_non_clifford'])
            and int(qroam_counts['target_plus_junk_qubits']) == int(qroam_cost['target_plus_junk_qubits'])
            and int(qroam_cost['domain_size']) == int(qroam_primitive_certificate['parameters']['domain_size'])
            and int(qroam_cost['block_size']) == int(compiler_parameters['lookup_policy']['standard_qroamclean_block_size'])
        ),
        'qroam_table_cnot_extension_binds_counted_liveness': (
            public_candidate_materialized_circuit_manifest['qroam_table_cnot_flat_extension']['pass'] is True
            and public_candidate_materialized_circuit_manifest['checks']['qroam_table_cnot_flat_extension_is_bound'] is True
            and int(public_candidate_materialized_circuit_manifest['qroam_table_cnot_flat_extension']['segment_count']) == int(qroam_table_cnot_materialization['totals']['segment_count'])
            and int(public_candidate_materialized_circuit_manifest['qroam_table_cnot_flat_extension']['operation_count']) == int(qroam_table_cnot_materialization['totals']['full_oracle_emitted_clifford_cx'])
            and int(public_candidate_materialized_circuit_manifest['qroam_table_cnot_flat_extension']['non_clifford_count']) == 0
            and qroam_table_cnot_materialization['checks']['rank_checkpoints_cover_every_segment'] is True
            and qroam_table_cnot_materialization['checks']['row_index_contract_domains_match_ranges'] is True
            and qroam_table_cnot_materialization['checks']['row_decoder_samples_are_exact_table_cnot_rows'] is True
            and public_candidate_materialized_circuit_manifest['qroam_table_cnot_flat_extension']['checks']['table_cnot_row_index_contract_matches_artifact'] is True
            and public_candidate_materialized_circuit_manifest['checks']['canonical_physical_flat_netlist_splices_qroam_table_cnot_rows'] is True
            and canonical_physical_flat['pass'] is True
            and int(canonical_physical_flat['qroam_table_cnot_operation_count']) == int(qroam_table_cnot_materialization['totals']['full_oracle_emitted_clifford_cx'])
            and int(canonical_physical_flat['gate_totals']['cx']) == int(qroam_table_cnot_materialization['totals']['full_oracle_emitted_clifford_cx'])
        ),
        'lookup_rows_are_per_block_source_bound': (
            rows_by_source_kind['lookup_lowering_block'] > 0
            and lookup_lowerings['schema'].startswith('compiler-project-lookup-lowerings-')
            and all(
                'stages' in family
                and sum(len(stage['blocks']) for stage in family['stages']) > 0
                and all(
                    block['primitive_operation_stream']['operation_count'] == sum(int(value) for value in block['primitive_counts_total'].values())
                    for stage in family['stages']
                    for block in stage['blocks']
                )
                for family in lookup_lowerings['families']
            )
        ),
        'arithmetic_rows_are_operation_ir_bound': (
            rows_by_source_kind['arithmetic_operation_ir'] > 0
            and arithmetic_operation_ir['pass'] is True
            and arithmetic_operand_replay_audit['pass'] is True
            and int(arithmetic_operand_replay_audit['arithmetic_run_length_rows_checked']) == rows_by_source_kind['arithmetic_operation_ir']
            and int(arithmetic_operand_replay_audit['rows_with_failures']) == 0
            and int(arithmetic_operand_replay_audit['unique_block_gate_failures']) == 0
            and arithmetic_operation_ir['checks']['modular_kernels_derive_from_executable_modular_circuit_ir'] is True
            and modular_engine_integration['pass'] is True
            and public_candidate_materialized_circuit_manifest['checks']['modular_arithmetic_engine_integration_is_bound'] is True
            and arithmetic_operation_ir['checks']['tail_macro_kernel_derives_from_tail_macro_engine'] is True
            and int(arithmetic_leaf_summary['non_clifford_total']) == sum(
                int(row['kernel_non_clifford_per_instance']) * int(row['leaf_instance_count'])
                for row in arithmetic_leaf_summary['rows']
            )
        ),
        'modular_execution_trace_binds_scheduled_tail': (
            modular_execution_trace['pass'] is True
            and int(modular_execution_trace['reconstructed_non_clifford']) == int(tail_macro_engine['selected_tail_kernel_non_clifford'])
            and int(modular_execution_trace['tail_schedule_row_count']) == len(tail_macro_engine['fused_output_reordered_schedule']['rows'])
            and modular_execution_trace['source_digests']['modular_arithmetic_certificate_sha256'] == _sha256_payload(modular_arithmetic_certificate)
            and public_engine_manifest['checks']['modular_execution_trace_is_bound'] is True
        ),
        'scheduled_modular_primitive_netlist_binds_trace': (
            scheduled_modular_primitive_netlist['pass'] is True
            and scheduled_modular_primitive_netlist['source_digests']['modular_execution_trace_sha256'] == _sha256_payload(modular_execution_trace)
            and int(scheduled_modular_primitive_netlist['trace_lookup_interface_non_clifford_replaced']) >= 0
            and int(scheduled_modular_primitive_netlist['strict_public_leaf_non_clifford']) == int(scheduled_modular_primitive_netlist['non_clifford_count'])
            and public_engine_manifest['checks']['scheduled_modular_primitive_netlist_is_bound'] is True
            and public_engine_manifest['checks']['scheduled_modular_primitive_netlist_splices_global_public_rows'] is True
        ),
        'modular_primitive_wire_audit_records_remaining_scratch_gap': (
            modular_primitive_wire_audit['pass'] is False
            and modular_primitive_wire_audit['checks']['scheduled_modular_primitive_netlist_passes'] is True
            and modular_primitive_wire_audit['checks']['scanned_operation_count_matches_scheduled_netlist'] is True
            and modular_primitive_wire_audit['checks']['scanned_gate_counts_match_scheduled_netlist'] is True
            and modular_primitive_wire_audit['checks']['raw_field_operand_liveness_is_not_claimed_complete'] is True
            and modular_primitive_wire_audit['checks']['field_operand_wires_are_live_or_classified'] is True
            and modular_primitive_wire_audit['checks']['no_blocking_field_liveness_gaps'] is True
            and modular_primitive_wire_audit['checks']['lookup_virtual_field_operands_are_classified'] is True
            and modular_primitive_wire_audit['checks']['no_unresolved_virtual_field_operands'] is True
            and modular_primitive_wire_audit['checks']['synthetic_scratch_wires_are_single_use_ccx_targets'] is True
            and modular_primitive_wire_audit['checks']['synthetic_scratch_wires_have_cleanup_or_counted_capacity'] is False
            and modular_primitive_wire_audit['checks']['no_synthetic_arithmetic_scratch_wires_without_owner_capacity'] is False
            and modular_multiplier_lifecycle['pass'] is True
            and modular_accumulator_lowering['pass'] is True
            and modular_accumulator_row_stream['pass'] is True
            and modular_accumulator_capacity_certificate['pass'] is True
            and modular_accumulator_scratch_schedule['pass'] is True
            and modular_accumulator_semantic_obligations['pass'] is True
            and modular_accumulator_carry_obligations['pass'] is True
            and modular_accumulator_carry_save_candidate['pass'] is True
            and modular_accumulator_full_adder_contract['pass'] is True
            and modular_accumulator_full_adder_stream['pass'] is True
            and modular_accumulator_lowering['promotion_status']['status'] == 'lowering_plan_not_promoted_to_scheduled_primitive_netlist'
            and modular_accumulator_row_stream['promotion_status']['status'] == 'row_stream_obligations_not_promoted_to_scheduled_primitive_netlist'
            and modular_accumulator_capacity_certificate['promotion_status']['status'] == 'capacity_certificate_not_promoted_to_public_resource_contract'
            and modular_accumulator_scratch_schedule['promotion_status']['status'] == 'scratch_schedule_not_promoted_to_public_resource_contract'
            and modular_accumulator_semantic_obligations['promotion_status']['status'] == 'semantic_obligations_not_promoted_to_public_resource_contract'
            and modular_accumulator_carry_obligations['promotion_status']['status'] == 'carry_obligations_not_promoted_to_public_resource_contract'
            and modular_accumulator_carry_save_candidate['promotion_status']['status'] == 'carry_save_candidate_not_promoted_to_public_resource_contract'
            and modular_accumulator_full_adder_contract['promotion_status']['status'] == FULL_ADDER_CONTRACT_UNPROMOTED_STATUS
            and modular_accumulator_full_adder_stream['promotion_status']['status'] == FULL_ADDER_STREAM_UNPROMOTED_STATUS
            and modular_accumulator_lowering['checks']['materialized_product_accumulator_shortcut_is_rejected'] is True
            and modular_accumulator_row_stream['checks']['row_stream_rejects_hidden_512_bit_field_slot'] is True
            and modular_accumulator_capacity_certificate['checks']['product_column_owner_includes_final_carry_bit_and_exceeds_single_field_slot'] is True
            and modular_accumulator_scratch_schedule['checks']['serialized_temporary_peak_matches_capacity_certificate'] is True
            and modular_accumulator_semantic_obligations['checks']['consume_events_cover_product_and_guard_rows'] is True
            and modular_accumulator_semantic_obligations['checks']['obligation_classes_cover_every_row_stream_row'] is True
            and modular_accumulator_semantic_obligations['obligation_summary']['semantic_gate_lowering_proven'] is False
            and modular_accumulator_carry_obligations['checks']['reduced_width_parity_only_is_rejected'] is True
            and modular_accumulator_carry_obligations['checks']['carry_obligation_exceeds_parity_only_rows'] is True
            and modular_accumulator_carry_save_candidate['checks']['reduced_width_semantic_replay_passes'] is True
            and modular_accumulator_carry_save_candidate['checks']['candidate_touch_count_below_naive_carry_obligations'] is True
            and modular_accumulator_full_adder_contract['checks']['truth_table_passes'] is True
            and modular_accumulator_full_adder_contract['checks']['irreversible_three_to_two_compression_is_rejected'] is True
            and modular_accumulator_full_adder_stream['checks']['streamed_cell_count_matches_contract'] is True
            and modular_accumulator_full_adder_stream['checks']['retained_input_obligations_remain_explicit'] is True
            and modular_multiplier_lifecycle['current_stream']['physical_lifecycle_status'] == 'invalid_abandoned_temporary_and_targets'
            and int(modular_multiplier_lifecycle['current_stream']['scratch_abandoned_garbage_count']) == int(modular_primitive_wire_audit['arithmetic_scratch_abandoned_garbage_count'])
            and int(modular_primitive_wire_audit['field_wire_missing_liveness_count']) > 0
            and int(modular_primitive_wire_audit['unresolved_virtual_field_observation_count']) == 0
            and int(modular_primitive_wire_audit['arithmetic_scratch_wire_observation_count']) > 0
        ),
        'phase_rows_are_lowering_bound': (
            rows_by_source_kind['phase_shell_lowering'] > 0
            and phase_shell_lowerings['schema'].startswith('compiler-project-phase-shell-lowerings-')
            and public_engine_manifest['primitive_operation_evidence']['phase_shell']['name'] == compiler_parameters['phase_shell']['selected_public_shell']
        ),
        'semantic_boundary_cases_cover_public_point_add_boundary': (
            streamed_lookup_tail_leaf_equivalence['summary']['pass'] == streamed_lookup_tail_leaf_equivalence['summary']['total']
            and release_corpus_preflight['pass'] is True
            and all(release_categories.get(category, 0) > 0 for category in required_semantic_categories)
        ),
        'tail_macro_auxiliary_artifacts_are_current': (
            tail_macro_engine['pass'] is True
            and tail_macro_engine['completion_status'] == 'tail_cost_bound_to_reversible_seven_slot_field_schedule_contract'
            and tail_macro_engine['checks']['counted_slots_cover_expanded_single_assignment_peak'] is False
            and tail_macro_engine['checks']['fused_output_reversible_schedule_contract_passes'] is True
            and tail_macro_engine['fused_output_reversible_schedule_contract']['pass'] is True
            and tail_macro_engine['fused_output_reversible_schedule_contract']['status'] == 'seven_slot_field_operation_schedule_has_reversible_contract'
            and int(tail_macro_engine['fused_output_reversible_schedule_contract']['peak_field_slots']) == 7
            and int(tail_macro_engine['fused_output_reversible_schedule_contract']['owner_capacity_total_logical_qubits']) == 7 * int(tail_macro_engine['field_bits'])
            and int(tail_macro_engine['fused_output_reversible_schedule_contract']['operation_count']) == len(tail_macro_engine['fused_output_reordered_schedule']['rows'])
            and int(tail_macro_engine['fused_output_reversible_schedule_contract']['overwritten_row_count']) == int(tail_macro_engine['fused_output_reordered_schedule']['overwritten_row_count'])
            and int(tail_macro_engine['expanded_slot_schedule']['peak_field_slots']) == int(tail_macro_engine['slot_gap']['expanded_single_assignment_peak_field_values'])
            and int(tail_macro_engine['expanded_slot_schedule']['additional_logical_qubits_over_counted_leaf']) == int(tail_macro_engine['slot_gap']['additional_logical_qubits_needed_without_in_place_schedule'])
            and tail_macro_engine['expanded_slot_schedule']['status'] == 'executable_capacity_fallback_not_reversible_cleanup_proof'
            and tail_macro_engine['destructive_candidate_schedule']['status'] == 'optimizer_candidate_not_a_reversible_proof'
            and int(tail_macro_engine['destructive_candidate_schedule']['peak_field_slots']) < int(tail_macro_engine['expanded_slot_schedule']['peak_field_slots'])
            and tail_macro_engine['destructive_candidate_schedule']['local_inverse_certificate']['status'] == 'toy_boundary_local_inverse_check_not_full_reversible_proof'
            and int(tail_macro_engine['destructive_candidate_schedule']['local_inverse_certificate']['failing_row_count']) > 0
            and tail_macro_engine['reordered_local_inverse_schedule']['status'] == 'solution_found_not_full_reversible_circuit_proof'
            and tail_macro_engine['reordered_local_inverse_schedule']['solution_found'] is True
            and int(tail_macro_engine['reordered_local_inverse_schedule']['peak_field_slots']) == 8
            and int(tail_macro_engine['reordered_local_inverse_schedule']['invalid_overwrite_count']) == 0
            and tail_macro_engine['reordered_slot_assignment']['pass'] is True
            and int(tail_macro_engine['reordered_slot_assignment']['peak_field_slots']) == 8
            and tail_macro_engine['reordered_replay_certificate']['pass'] is True
            and tail_macro_engine['reordered_replay_certificate']['owner_capacity_pass'] is True
            and tail_macro_engine['fused_output_reordered_schedule']['status'] == 'solution_found_with_replay_and_reversible_field_schedule_contract'
            and tail_macro_engine['fused_output_replay_certificate']['pass'] is True
            and tail_macro_engine['fused_output_replay_certificate']['owner_capacity_pass'] is True
            and tail_macro_engine['fused_output_slot_assignment']['pass'] is True
            and int(tail_macro_engine['fused_output_slot_assignment']['peak_field_slots']) == 7
            and tail_macro_liveness['pass'] is True
            and tail_macro_reversibility['canonical_subgroup_domain']['all_checked_rows_injective'] is True
            and tail_macro_reversibility['fixed_lookup_reachable_orbit_domain']['all_checked_rows_injective'] is True
            and tail_macro_reversibility['canonical_boundary_translation_domain']['all_checked_rows_semantic'] is True
            and tail_macro_schedule_search['all_checked_curves_exhausted_without_solution'] is True
            and tail_macro_schedule_search['any_checked_curve_has_solution'] is False
            and modular_arithmetic_certificate['pass'] is True
        ),
        'fast_path_is_no_zkp': (
            public_engine_manifest['fast_no_zkp_contract']['prover_required'] is False
            and public_engine_manifest['fast_no_zkp_contract']['verify_group'] == 'public_engine_manifest_checks'
        ),
        'zkp_input_binds_canonical_engine_without_compact_strict_claim': (
            zkp_attestation_input['public_engine_manifest_sha256'] == zkp_public_engine_document['sha256']
            and zkp_public_engine_document['document_type'] == 'public_engine_manifest'
            and zkp_public_engine_document['payload'] == public_engine_manifest
            and zkp_claim_summary['resource_engine_summary']['source'] == 'public_engine_manifest.public_totals'
            and zkp_claim_summary['resource_engine_summary']['source_sha256'] == zkp_attestation_input['public_engine_manifest_sha256']
            and zkp_physical_boundary['source'] == 'public_engine_manifest.scheduled_modular_global_splice'
            and zkp_physical_boundary['source_sha256'] == zkp_attestation_input['public_engine_manifest_sha256']
            and zkp_physical_boundary['canonical_materialized_operation_stream_sha256'] == public_engine_physical_manifest['canonical_materialized_flat_netlist']['operation_stream_sha256']
            and zkp_physical_boundary['canonical_physical_operation_stream_sha256'] == public_engine_physical_manifest['canonical_physical_flat_netlist']['operation_stream_sha256']
            and zkp_physical_boundary['scheduled_modular_leaf_operation_stream_sha256'] == scheduled_modular_leaf['operation_stream_sha256']
            and zkp_physical_boundary['scheduled_modular_global_splice_sha256'] == scheduled_modular_splice['global_splice_sha256']
            and int(zkp_physical_boundary['scheduled_modular_leaf_operation_count']) == int(scheduled_modular_leaf['operation_count'])
            and int(zkp_physical_boundary['scheduled_modular_leaf_non_clifford']) == int(scheduled_modular_leaf['non_clifford_count'])
            and int(zkp_physical_boundary['scheduled_global_operation_count']) == int(scheduled_modular_splice['scheduled_operation_count']) == int(scheduled_modular_splice['grouped_operation_count'])
            and int(zkp_physical_boundary['scheduled_global_non_clifford']) == int(scheduled_modular_splice['scheduled_non_clifford_count']) == int(scheduled_modular_splice['grouped_non_clifford_count'])
            and int(zkp_claim_summary['expected_full_oracle_non_clifford']) == public_totals['non_clifford']
            and int(zkp_claim_summary['expected_total_logical_qubits']) == public_totals['logical_qubits']
            and int(zkp_claim_summary['logical_qubit_formula']['reconstructed_total']) == public_totals['logical_qubits']
            and sum(
                int(row['logical_qubits'])
                for row in public_engine_manifest['strict_public_owner_capacity_stream']['rows']
            ) == public_totals['logical_qubits']
            and 'primary_strict_claim_sha256' not in zkp_attestation_input
            and 'primary_strict_claim_document' not in zkp_attestation_input
            and 'primary_strict_result_sha256' not in zkp_attestation_input
            and 'primary_strict_result_document' not in zkp_attestation_input
        ),
        'remaining_macro_boundaries_are_explicit': True,
        'public_claim_not_marked_full_clifford_complete_until_macro_boundaries_flattened': True,
    }
    covered_boundaries = [
        {
            'name': 'public_totals',
            'status': 'derived_from_canonical_materialized_flat_netlist',
            'evidence': f'public_engine_manifest.public_totals + {PUBLIC_ENGINE_CANONICAL_TOTALS_SOURCE}',
        },
        {
            'name': 'flat_primitive_stream_counts',
            'status': 'materialized_and_counted',
            'evidence': 'strict_replayed_tail_materialized_flat_netlist.operation_stream_sha256',
        },
        {
            'name': 'primitive_operand_wires_and_owner_liveness',
            'status': 'checked_for_emitted_run_length_rows',
            'evidence': 'operand_parent_binding + flat_execution_probe operand checks',
        },
        {
            'name': 'source_operation_binding',
            'status': 'per_row_source_bound',
            'evidence': 'operand_source_binding rows_by_source_kind',
        },
        {
            'name': 'arithmetic_operand_replay',
            'status': 'exact_source_operands_replayed_to_counted_flat_netlist_wires',
            'evidence': 'arithmetic_operand_replay_audit',
        },
        {
            'name': 'standard_qroam_primitive_costs',
            'status': 'qroamclean_k1_bound',
            'evidence': 'qroam_primitive_certificate.qroamclean_cost_model',
        },
        {
            'name': 'qroam_bit_level_netlist_expansion',
            'status': 'indexed_table_cnot_rows_in_canonical_physical_flat_stream_with_iterator_export',
            'evidence': 'canonical_physical_flat_netlist + qroam_table_cnot_flat_extension + qroam_table_cnot_materialization.row_index_contract',
        },
        {
            'name': 'modular_arithmetic_kernel_generation',
            'status': 'generated_from_executable_modular_circuit_ir',
            'evidence': 'arithmetic_lowerings.executable_modular_circuit_ir + arithmetic_operation_ir.executable_modular_circuit_ir + modular_arithmetic_certificate.modular_primitive_stream_certificate',
        },
        {
            'name': 'tail_macro_cost_formula_binding',
            'status': 'expanded_field_operation_stream_bound_to_tail_kernel_cost',
            'evidence': 'tail_macro_engine + arithmetic_operation_ir.tail_macro_engine + arithmetic_lowerings.tail_macro_engine',
        },
        {
            'name': 'tail_macro_strict_capacity_fallback',
            'status': 'expanded_single_assignment_slot_schedule_generated',
            'evidence': 'tail_macro_engine.expanded_slot_schedule',
        },
        {
            'name': 'tail_macro_in_place_optimizer_signal',
            'status': 'reordered_eight_slot_schedule_replayed_diagnostic',
            'evidence': 'tail_macro_engine.reordered_local_inverse_schedule + tail_macro_engine.operand_overwrite_screen + tail_macro_engine.reordered_replay_certificate',
        },
        {
            'name': 'tail_reversible_field_schedule_contract',
            'status': 'seven_slot_field_operation_schedule_bound_to_reversible_contract',
            'evidence': 'tail_macro_engine.fused_output_reversible_schedule_contract + fused_output_replay_certificate + fused_output_slot_assignment',
        },
        {
            'name': 'point_add_semantic_boundary',
            'status': 'release_corpus_and_equivalence_checked',
            'evidence': 'streamed_lookup_tail_leaf_equivalence + release_corpus_preflight',
        },
        {
            'name': 'canonical_engine_zkp_input_authority',
            'status': 'public_engine_manifest_and_scheduled_physical_boundary_bound_by_candidate_input_and_guest',
            'evidence': 'zkp_attestation_reusable_chunk_candidate_input.public_engine_manifest_document + physical_boundary_summary + Rust prepared guest validation',
        },
    ]
    remaining_macro_boundaries = [
        {
            'name': 'modular_arithmetic_clifford_expansion',
            'status': 'scheduled_modular_primitive_stream_bound_to_zkp_physical_boundary_not_full_clifford_decomposition',
            'required_to_close': 'Replace every synthetic arithmetic scratch operand in modular primitive rows with exact counted owner/liveness assignments, then decompose every modular add, subtract, multiply, fold, and reduction primitive into exact concrete Clifford/CCX wire operations inside the same global flat schedule as the point-add leaf.',
            'current_evidence': 'scheduled_modular_primitive_netlist + modular_primitive_wire_audit + modular_accumulator_semantic_obligations + modular_accumulator_carry_obligations + modular_accumulator_carry_save_candidate + modular_accumulator_full_adder_contract + modular_accumulator_full_adder_stream + scheduled_modular_global_splice + physical_boundary_summary + Rust prepared guest validation',
            'evidence_metrics': {
                'source_bound_run_length_rows': rows_by_source_kind['arithmetic_operation_ir'],
                'leaf_arithmetic_non_clifford': int(arithmetic_leaf_summary['non_clifford_total']),
                'selected_leaf_exact_arithmetic_operation_count': int(arithmetic_operation_ir['selected_leaf_exact_operation_stream']['operation_count']),
                'selected_leaf_exact_arithmetic_segment_count': int(arithmetic_operation_ir['selected_leaf_exact_operation_stream']['segment_count']),
                'selected_leaf_exact_arithmetic_stream_pass': bool(arithmetic_operation_ir['selected_leaf_exact_operation_stream']['pass']),
                'arithmetic_operand_replay_pass': bool(arithmetic_operand_replay_audit['pass']),
                'arithmetic_operand_replay_source_operations_checked': int(arithmetic_operand_replay_audit['source_operations_checked']),
                'arithmetic_operand_replay_rows_with_failures': int(arithmetic_operand_replay_audit['rows_with_failures']),
                'local_modular_primitive_stream_pass': bool(modular_arithmetic_certificate['modular_primitive_stream_certificate']['pass']),
                'local_modular_primitive_stream_operation_count': int(modular_arithmetic_certificate['modular_primitive_stream_certificate']['operation_count']),
                'local_modular_primitive_stream_sha256': modular_arithmetic_certificate['modular_primitive_stream_certificate']['operation_stream_sha256'],
                'modular_engine_integration_pass': bool(modular_engine_integration['pass']),
                'modular_engine_integration_public_arithmetic_operation_count': int(modular_engine_integration['public_arithmetic_rows']['operation_count']),
                'modular_engine_integration_strict_liveness_rows_checked': int(modular_engine_integration['strict_liveness_projection']['rows_checked']),
                'modular_execution_trace_pass': bool(modular_execution_trace['pass']),
                'modular_execution_trace_suboperation_count': int(modular_execution_trace['suboperation_count']),
                'modular_execution_trace_sha256': modular_execution_trace['trace_stream_sha256'],
                'scheduled_modular_primitive_netlist_pass': bool(scheduled_modular_primitive_netlist['pass']),
                'scheduled_modular_primitive_netlist_operation_count': int(scheduled_modular_primitive_netlist['operation_count']),
                'scheduled_modular_primitive_netlist_non_clifford': int(scheduled_modular_primitive_netlist['non_clifford_count']),
                'scheduled_modular_primitive_netlist_sha256': scheduled_modular_primitive_netlist['operation_stream_sha256'],
                'scheduled_modular_global_splice_pass': bool(public_engine_manifest['primitive_operation_evidence']['public_candidate_materialized_circuit_manifest']['scheduled_modular_global_splice']['pass']),
                'modular_primitive_wire_audit_pass': bool(modular_primitive_wire_audit['pass']),
                'modular_primitive_wire_audit_sha256': _sha256_payload(modular_primitive_wire_audit),
                'field_operand_wires_missing_liveness': int(modular_primitive_wire_audit['field_wire_missing_liveness_count']),
                'field_operand_wires_classified_missing_liveness': int(modular_primitive_wire_audit['field_wire_classified_missing_liveness_count']),
                'field_operand_wires_blocking_missing_liveness': int(modular_primitive_wire_audit['field_wire_blocking_missing_liveness_count']),
                'overwritten_source_field_operands_counted_by_target_owner': int(modular_primitive_wire_audit['overwritten_source_field_observation_count']),
                'lookup_virtual_field_operands_classified': int(modular_primitive_wire_audit['lookup_virtual_field_observation_count']),
                'unresolved_virtual_field_operands': int(modular_primitive_wire_audit['unresolved_virtual_field_observation_count']),
                'synthetic_arithmetic_scratch_wire_observations': int(modular_primitive_wire_audit['arithmetic_scratch_wire_observation_count']),
                'synthetic_arithmetic_scratch_unique_wires': int(modular_primitive_wire_audit['arithmetic_scratch_unique_wire_count']),
                'synthetic_arithmetic_scratch_single_use_wires': int(modular_primitive_wire_audit['arithmetic_scratch_single_use_wire_count']),
                'synthetic_arithmetic_scratch_ccx_target_observations': int(modular_primitive_wire_audit['arithmetic_scratch_ccx_target_observation_count']),
                'synthetic_arithmetic_scratch_cleanup_observations': int(modular_primitive_wire_audit['arithmetic_scratch_cleanup_observation_count']),
                'synthetic_arithmetic_scratch_abandoned_garbage': int(modular_primitive_wire_audit['arithmetic_scratch_abandoned_garbage_count']),
                'modular_multiplier_lifecycle_pass': bool(modular_multiplier_lifecycle['pass']),
                'modular_multiplier_lifecycle_sha256': _sha256_payload(modular_multiplier_lifecycle),
                'modular_accumulator_lowering_pass': bool(modular_accumulator_lowering['pass']),
                'modular_accumulator_lowering_sha256': _sha256_payload(modular_accumulator_lowering),
                'modular_accumulator_row_stream_pass': bool(modular_accumulator_row_stream['pass']),
                'modular_accumulator_row_stream_sha256': _sha256_payload(modular_accumulator_row_stream),
                'modular_accumulator_capacity_certificate_pass': bool(modular_accumulator_capacity_certificate['pass']),
                'modular_accumulator_capacity_certificate_sha256': _sha256_payload(modular_accumulator_capacity_certificate),
                'modular_accumulator_scratch_schedule_pass': bool(modular_accumulator_scratch_schedule['pass']),
                'modular_accumulator_scratch_schedule_sha256': _sha256_payload(modular_accumulator_scratch_schedule),
                'modular_accumulator_semantic_obligations_pass': bool(modular_accumulator_semantic_obligations['pass']),
                'modular_accumulator_semantic_obligations_sha256': _sha256_payload(modular_accumulator_semantic_obligations),
                'modular_accumulator_carry_obligations_pass': bool(modular_accumulator_carry_obligations['pass']),
                'modular_accumulator_carry_obligations_sha256': _sha256_payload(modular_accumulator_carry_obligations),
                'modular_accumulator_carry_save_candidate_pass': bool(modular_accumulator_carry_save_candidate['pass']),
                'modular_accumulator_carry_save_candidate_sha256': _sha256_payload(modular_accumulator_carry_save_candidate),
                'modular_accumulator_full_adder_contract_pass': bool(modular_accumulator_full_adder_contract['pass']),
                'modular_accumulator_full_adder_contract_sha256': _sha256_payload(modular_accumulator_full_adder_contract),
                'modular_accumulator_full_adder_stream_pass': bool(modular_accumulator_full_adder_stream['pass']),
                'modular_accumulator_full_adder_stream_sha256': _sha256_payload(modular_accumulator_full_adder_stream),
                'modular_accumulator_single_grid_column_count': int(modular_accumulator_lowering['single_schoolbook_grid']['column_count']),
                'modular_accumulator_fold_route_count': int(modular_accumulator_lowering['pseudo_mersenne_fold_routes']['route_count']),
                'modular_accumulator_overflowing_shift_column_count': int(modular_accumulator_lowering['pseudo_mersenne_fold_routes']['overflowing_shift_column_count']),
                'modular_accumulator_promotion_status': str(modular_accumulator_lowering['promotion_status']['status']),
                'modular_accumulator_row_stream_promotion_status': str(modular_accumulator_row_stream['promotion_status']['status']),
                'modular_accumulator_row_stream_operation_sha256': str(modular_accumulator_row_stream['row_stream']['operation_stream_sha256']),
                'modular_accumulator_row_stream_row_count': int(modular_accumulator_row_stream['row_stream']['row_count']),
                'modular_accumulator_row_stream_segment_count': int(modular_accumulator_row_stream['row_stream']['segment_count']),
                'modular_accumulator_row_stream_partial_product_rows': int(modular_accumulator_row_stream['expanded_counts']['partial_product_consume_rows']),
                'modular_accumulator_row_stream_fold_rows': int(modular_accumulator_row_stream['expanded_counts']['pseudo_mersenne_fold_rows']),
                'modular_accumulator_row_stream_cleanup_rows': int(modular_accumulator_row_stream['expanded_counts']['temporary_cleanup_rows']),
                'modular_accumulator_partial_product_column_count': int(modular_accumulator_capacity_certificate['owner_capacity_obligations'][0]['partial_product_column_count']),
                'modular_accumulator_product_column_capacity_bits': int(modular_accumulator_capacity_certificate['owner_capacity_obligations'][0]['logical_qubit_budget_required_by_materialized_columns']),
                'modular_accumulator_fold_overflow_column_count': int(modular_accumulator_capacity_certificate['owner_capacity_obligations'][1]['overflowing_shift_column_count']),
                'modular_accumulator_obligation_order_temporary_peak_qubits': int(modular_accumulator_capacity_certificate['owner_capacity_obligations'][2]['obligation_order_peak_logical_qubits']),
                'modular_accumulator_serialized_candidate_temporary_peak_qubits': int(modular_accumulator_capacity_certificate['owner_capacity_obligations'][2]['serialized_candidate_peak_logical_qubits']),
                'modular_accumulator_scratch_schedule_event_count': int(modular_accumulator_scratch_schedule['schedule_stream']['event_count']),
                'modular_accumulator_scratch_schedule_peak_temporary_qubits': int(modular_accumulator_scratch_schedule['liveness_certificate']['serialized_schedule_temporary_peak_qubits']),
                'modular_accumulator_scratch_schedule_semantic_gate_lowering_proven': bool(modular_accumulator_scratch_schedule['liveness_certificate']['semantic_gate_lowering_proven']),
                'modular_accumulator_semantic_obligation_class_count': len(modular_accumulator_semantic_obligations['obligation_classes']),
                'modular_accumulator_semantic_obligation_row_count': int(modular_accumulator_semantic_obligations['obligation_summary']['row_stream_row_count']),
                'modular_accumulator_semantic_partial_product_rows': int(modular_accumulator_semantic_obligations['obligation_summary']['partial_product_consume_rows']),
                'modular_accumulator_semantic_guard_rows': int(modular_accumulator_semantic_obligations['obligation_summary']['zero_lift_guard_consume_rows']),
                'modular_accumulator_semantic_fold_rows': int(modular_accumulator_semantic_obligations['obligation_summary']['pseudo_mersenne_fold_rows']),
                'modular_accumulator_semantic_temporary_cleanup_rows': int(modular_accumulator_semantic_obligations['obligation_summary']['temporary_cleanup_rows']),
                'modular_accumulator_semantic_gate_lowering_proven': bool(modular_accumulator_semantic_obligations['obligation_summary']['semantic_gate_lowering_proven']),
                'modular_accumulator_carry_obligation_row_count': int(modular_accumulator_carry_obligations['column_carry_obligation_stream']['total_carry_obligation_rows']),
                'modular_accumulator_carry_obligation_column_count': int(modular_accumulator_carry_obligations['column_carry_obligation_stream']['column_count']),
                'modular_accumulator_carry_max_span_bits': int(modular_accumulator_carry_obligations['column_carry_obligation_stream']['max_single_increment_carry_span_bits']),
                'modular_accumulator_carry_reduced_width_case_count': sum(int(row['total_cases']) for row in modular_accumulator_carry_obligations['reduced_width_exhaustive_checks']),
                'modular_accumulator_carry_parity_mismatch_count': sum(int(row['parity_only_mismatch_count']) for row in modular_accumulator_carry_obligations['reduced_width_exhaustive_checks']),
                'modular_accumulator_carry_save_single_grid_full_adders': int(modular_accumulator_carry_save_candidate['single_grid']['full_adder_count']),
                'modular_accumulator_carry_save_single_grid_layer_count': int(modular_accumulator_carry_save_candidate['single_grid']['layer_count']),
                'modular_accumulator_carry_save_all_grid_full_adders': int(modular_accumulator_carry_save_candidate['all_grids']['carry_save_full_adder_count']),
                'modular_accumulator_carry_save_final_carry_bits': int(modular_accumulator_carry_save_candidate['all_grids']['final_carry_propagate_bits']),
                'modular_accumulator_carry_save_candidate_touch_count': int(modular_accumulator_carry_save_candidate['all_grids']['candidate_touch_count']),
                'modular_accumulator_carry_save_reduced_width_case_count': sum(int(row['total_cases']) for row in modular_accumulator_carry_save_candidate['reduced_width_exhaustive_checks']),
                'modular_accumulator_full_adder_cell_count': int(modular_accumulator_full_adder_contract['candidate_totals']['full_adder_cell_count']),
                'modular_accumulator_full_adder_ccx': int(modular_accumulator_full_adder_contract['candidate_totals']['embedded_full_adder_primitive_counts']['ccx']),
                'modular_accumulator_full_adder_cx': int(modular_accumulator_full_adder_contract['candidate_totals']['embedded_full_adder_primitive_counts']['cx']),
                'modular_accumulator_full_adder_retained_input_bits': int(modular_accumulator_full_adder_contract['candidate_totals']['retained_input_obligation_bits']),
                'modular_accumulator_full_adder_output_bits': int(modular_accumulator_full_adder_contract['candidate_totals']['output_obligation_bits']),
                'modular_accumulator_full_adder_stream_operation_count': int(modular_accumulator_full_adder_stream['operation_count']),
                'modular_accumulator_full_adder_stream_non_clifford': int(modular_accumulator_full_adder_stream['non_clifford_count']),
                'modular_accumulator_full_adder_stream_segment_count': int(modular_accumulator_full_adder_stream['segment_count']),
                'modular_accumulator_full_adder_stream_retained_input_bits': int(modular_accumulator_full_adder_stream['retained_input_obligation_bits']),
                'modular_accumulator_full_adder_stream_output_bits': int(modular_accumulator_full_adder_stream['output_obligation_bits']),
                'modular_accumulator_full_adder_stream_operation_sha256': str(modular_accumulator_full_adder_stream['operation_stream_sha256']),
                'streamed_lifecycle_candidate_event_stream_sha256': str(modular_multiplier_lifecycle['candidate_lifecycle_stream']['operation_stream_sha256']),
                'streamed_lifecycle_candidate_event_count': int(modular_multiplier_lifecycle['candidate_lifecycle_stream']['event_count']),
                'streamed_lifecycle_partial_product_routes': int(modular_multiplier_lifecycle['candidate_lifecycle_stream']['route_summary']['partial_product_routes']),
                'streamed_lifecycle_zero_lift_guard_routes': int(modular_multiplier_lifecycle['candidate_lifecycle_stream']['route_summary']['zero_lift_guard_routes']),
                'streamed_lifecycle_unrouted_scratch_targets': int(modular_multiplier_lifecycle['candidate_lifecycle_stream']['route_summary']['unrouted_scratch_targets']),
                'streamed_lifecycle_product_column_max': int(modular_multiplier_lifecycle['candidate_lifecycle_stream']['route_summary']['product_column_max']),
                'streamed_lifecycle_materialized_product_accumulator_bits_required': int(modular_multiplier_lifecycle['candidate_lifecycle_stream']['route_summary']['materialized_product_accumulator_bits_required']),
                'streamed_lifecycle_rejects_materialized_field_slot_shortcut': bool(modular_multiplier_lifecycle['candidate_lifecycle_stream']['route_summary']['materialized_product_accumulator_exceeds_counted_field_slot']),
                'streamed_lifecycle_candidate_required_consume_events': int(modular_multiplier_lifecycle['streamed_lifecycle_candidate']['required_consume_events']),
                'streamed_lifecycle_candidate_required_cleanup_events': int(modular_multiplier_lifecycle['streamed_lifecycle_candidate']['required_cleanup_events']),
                'streamed_lifecycle_candidate_peak_temporary_and_wires': int(modular_multiplier_lifecycle['streamed_lifecycle_candidate']['peak_temporary_and_wires_if_serialized']),
                'field_mul_non_clifford': int(modular_arithmetic_certificate['field_mul_stage_count_certificate']['observed_total_ccx']),
                'field_mul_stage_counts_match': bool(modular_arithmetic_certificate['field_mul_stage_count_certificate']['stage_counts_match']),
                'modular_ir_counts_match_lowerings': bool(modular_arithmetic_certificate['executable_circuit_ir_count_certificate']['counts_match_arithmetic_lowerings']),
            },
        },
    ]
    remaining_boundary_names = {row['name'] for row in remaining_macro_boundaries}
    checks['remaining_macro_boundaries_are_explicit'] = (
        remaining_boundary_names == {'modular_arithmetic_clifford_expansion'}
        and all(
            row['status']
            and row['required_to_close']
            and row['current_evidence']
            for row in remaining_macro_boundaries
        )
    )
    return {
        'schema': ENGINE_COMPLETION_AUDIT_SCHEMA,
        'selected_family_name': selected_family_name,
        'overall_status': 'materialized_flat_public_claim_with_canonical_engine_zkp_authority_and_explicit_remaining_macro_boundaries',
        'clifford_complete_goal_achieved': False,
        'public_totals': public_totals,
        'source_digests': _source_digests({
            'public_engine_manifest': public_engine_manifest,
            'modular_execution_trace': modular_execution_trace,
            'scheduled_modular_primitive_netlist': scheduled_modular_primitive_netlist,
            'modular_primitive_wire_audit': modular_primitive_wire_audit,
            'public_candidate_materialized_circuit_manifest': public_candidate_materialized_circuit_manifest,
            'reusable_chunk_lowering': reusable_chunk_lowering,
            'arithmetic_operation_ir': arithmetic_operation_ir,
            'arithmetic_operand_replay_audit': arithmetic_operand_replay_audit,
            'lookup_lowerings': lookup_lowerings,
            'qroam_primitive_certificate': qroam_primitive_certificate,
            'qroam_table_cnot_materialization': qroam_table_cnot_materialization,
            'phase_shell_lowerings': phase_shell_lowerings,
            'release_corpus_preflight': release_corpus_preflight,
            'streamed_lookup_tail_leaf_equivalence': streamed_lookup_tail_leaf_equivalence,
            'modular_arithmetic_certificate': modular_arithmetic_certificate,
            'modular_accumulator_row_stream': modular_accumulator_row_stream,
            'modular_accumulator_capacity_certificate': modular_accumulator_capacity_certificate,
            'modular_accumulator_scratch_schedule': modular_accumulator_scratch_schedule,
            'modular_accumulator_semantic_obligations': modular_accumulator_semantic_obligations,
            'modular_accumulator_carry_obligations': modular_accumulator_carry_obligations,
            'modular_accumulator_carry_save_candidate': modular_accumulator_carry_save_candidate,
            'modular_accumulator_full_adder_contract': modular_accumulator_full_adder_contract,
            'modular_accumulator_full_adder_stream': modular_accumulator_full_adder_stream,
            'tail_macro_engine': tail_macro_engine,
            'tail_macro_liveness': tail_macro_liveness,
            'tail_macro_reversibility': tail_macro_reversibility,
            'tail_macro_schedule_search': tail_macro_schedule_search,
            'compiler_parameters': compiler_parameters,
            'zkp_attestation_reusable_chunk_candidate_input': zkp_attestation_input,
        }),
        'source_binding_summary': {
            'rows_checked': int(source_binding['rows_checked']),
            'rows_by_source_kind': rows_by_source_kind,
            'failure_count': int(source_binding['failure_count']),
        },
        'legacy_materialized_flat_netlist': {
            'operation_count': int(materialized_flat['operation_count']),
            'non_clifford_count': int(materialized_flat['non_clifford_count']),
            'peak_live_qubits': int(materialized_flat['peak_live_qubits']),
            'operation_stream_sha256': materialized_flat['operation_stream_sha256'],
            'segment_merkle_root_sha256': materialized_flat['segment_merkle_root_sha256'],
            'exact_operation_stream_materialized': bool(materialized_flat['exact_operation_stream_materialized']),
        },
        'materialized_flat_netlist': {
            'operation_count': public_totals['operation_count'],
            'non_clifford_count': public_totals['non_clifford'],
            'peak_live_qubits': public_totals['logical_qubits'],
            'operation_stream_sha256': canonical_materialized_flat['operation_stream_sha256'],
            'segment_merkle_root_sha256': canonical_materialized_flat['segment_merkle_root_sha256'],
            'exact_operation_stream_materialized': bool(canonical_materialized_flat['exact_operation_stream_materialized']),
        },
        'covered_boundaries': covered_boundaries,
        'remaining_macro_boundaries': remaining_macro_boundaries,
        'checks': checks,
        'pass': all(checks.values()) and len(remaining_macro_boundaries) > 0,
        'notes': [
            'This audit passing means the current public claim is internally source-bound and the remaining macro boundary is explicit.',
            'The candidate ZKP input uses public_engine_manifest as the strict resource authority; compact primary_strict_claim is no longer part of the active ZKP authority path.',
            'It does not mean the full thread goal is complete; clifford_complete_goal_achieved remains false until the remaining macro boundary is eliminated.',
        ],
    }


__all__ = ['ENGINE_COMPLETION_AUDIT_SCHEMA', 'build_engine_completion_audit']
