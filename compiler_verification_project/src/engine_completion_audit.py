#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping


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
    reusable_chunk_lowering: Mapping[str, Any],
    arithmetic_operation_ir: Mapping[str, Any],
    lookup_lowerings: Mapping[str, Any],
    qroam_primitive_certificate: Mapping[str, Any],
    phase_shell_lowerings: Mapping[str, Any],
    release_corpus_preflight: Mapping[str, Any],
    streamed_lookup_tail_leaf_equivalence: Mapping[str, Any],
    modular_arithmetic_certificate: Mapping[str, Any],
    tail_macro_engine: Mapping[str, Any],
    tail_macro_liveness: Mapping[str, Any],
    tail_macro_reversibility: Mapping[str, Any],
    tail_macro_schedule_search: Mapping[str, Any],
    compiler_parameters: Mapping[str, Any],
) -> Dict[str, Any]:
    selected_family_name = str(compiler_parameters['public_headline_policy']['selected_public_family_name'])
    materialized_flat = public_candidate_materialized_circuit_manifest['materialized_flat_netlist']
    strict_completeness = public_candidate_materialized_circuit_manifest['strict_primitive_completeness']
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
        'non_clifford': int(materialized_flat['non_clifford_count']),
        'logical_qubits': int(materialized_flat['peak_live_qubits']),
        'operation_count': int(materialized_flat['operation_count']),
        'source': 'public_candidate_materialized_circuit_manifest.materialized_flat_netlist',
    }
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
        'public_totals_derive_from_materialized_flat_netlist': (
            public_engine_manifest['public_totals']['source'] == public_totals['source']
            and int(public_engine_manifest['public_totals']['non_clifford']) == public_totals['non_clifford']
            and int(public_engine_manifest['public_totals']['logical_qubits']) == public_totals['logical_qubits']
            and public_candidate_materialized_circuit_manifest['public_totals']['non_clifford'] == public_totals['non_clifford']
            and public_candidate_materialized_circuit_manifest['public_totals']['logical_qubits'] == public_totals['logical_qubits']
        ),
        'materialized_flat_stream_is_exact_and_counted': (
            materialized_flat['exact_operation_stream_materialized'] is True
            and public_candidate_materialized_circuit_manifest['checks']['materialized_flat_netlist_stream_is_exact'] is True
            and public_candidate_materialized_circuit_manifest['checks']['materialized_flat_netlist_counts_match_index_netlist'] is True
            and public_candidate_materialized_circuit_manifest['checks']['flat_netlist_non_clifford_matches_public_candidate'] is True
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
            and arithmetic_operation_ir['checks']['modular_kernels_derive_from_executable_modular_circuit_ir'] is True
            and arithmetic_operation_ir['checks']['tail_macro_kernel_derives_from_tail_macro_engine'] is True
            and int(arithmetic_leaf_summary['non_clifford_total']) == sum(
                int(row['kernel_non_clifford_per_instance']) * int(row['leaf_instance_count'])
                for row in arithmetic_leaf_summary['rows']
            )
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
            and tail_macro_engine['completion_status'] == 'tail_cost_bound_to_expanded_field_operation_stream_but_in_place_schedule_unproven'
            and tail_macro_engine['checks']['counted_slots_cover_expanded_single_assignment_peak'] is False
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
        'remaining_macro_boundaries_are_explicit': True,
        'public_claim_not_marked_full_clifford_complete_until_macro_boundaries_flattened': True,
    }
    covered_boundaries = [
        {
            'name': 'public_totals',
            'status': 'derived_from_materialized_flat_netlist',
            'evidence': 'public_engine_manifest.public_totals + public_candidate_materialized_circuit_manifest.materialized_flat_netlist',
        },
        {
            'name': 'flat_primitive_stream_counts',
            'status': 'materialized_and_counted',
            'evidence': 'materialized_flat_netlist.operation_stream_sha256',
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
            'name': 'standard_qroam_primitive_costs',
            'status': 'qroamclean_k1_bound',
            'evidence': 'qroam_primitive_certificate.qroamclean_cost_model',
        },
        {
            'name': 'modular_arithmetic_kernel_generation',
            'status': 'generated_from_executable_modular_circuit_ir',
            'evidence': 'arithmetic_lowerings.executable_modular_circuit_ir + arithmetic_operation_ir.executable_modular_circuit_ir + modular_arithmetic_certificate',
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
            'status': 'reordered_eight_slot_local_inverse_schedule_generated_not_full_circuit_proof',
            'evidence': 'tail_macro_engine.reordered_local_inverse_schedule + tail_macro_engine.operand_overwrite_screen',
        },
        {
            'name': 'point_add_semantic_boundary',
            'status': 'release_corpus_and_equivalence_checked',
            'evidence': 'streamed_lookup_tail_leaf_equivalence + release_corpus_preflight',
        },
    ]
    remaining_macro_boundaries = [
        {
            'name': 'tail_macro_schedule_and_reversibility',
            'status': 'in_place_three_slot_schedule_boundary_not_eliminated',
            'required_to_close': 'Promote an executable reversible/permutation-extension tail schedule into the counted resource contract, or promote a generated expanded/reordered slot schedule into the public qubit budget.',
            'current_evidence': 'tail_macro_engine + tail_macro_liveness + tail_macro_reversibility + tail_macro_schedule_search + arithmetic_operation_ir',
        },
        {
            'name': 'single_engine_zkp_input_derivation',
            'status': 'public_totals_engine_bound_but_zkp_bundle_still_document_bundle_oriented',
            'required_to_close': 'Have ZKP input bind the canonical engine artifact as the only authoritative resource document.',
            'current_evidence': 'public_engine_manifest + checked attestation input bundle',
        },
    ]
    return {
        'schema': ENGINE_COMPLETION_AUDIT_SCHEMA,
        'selected_family_name': selected_family_name,
        'overall_status': 'materialized_flat_public_claim_with_explicit_remaining_macro_boundaries',
        'clifford_complete_goal_achieved': False,
        'public_totals': public_totals,
        'source_digests': _source_digests({
            'public_engine_manifest': public_engine_manifest,
            'public_candidate_materialized_circuit_manifest': public_candidate_materialized_circuit_manifest,
            'reusable_chunk_lowering': reusable_chunk_lowering,
            'arithmetic_operation_ir': arithmetic_operation_ir,
            'lookup_lowerings': lookup_lowerings,
            'qroam_primitive_certificate': qroam_primitive_certificate,
            'phase_shell_lowerings': phase_shell_lowerings,
            'release_corpus_preflight': release_corpus_preflight,
            'streamed_lookup_tail_leaf_equivalence': streamed_lookup_tail_leaf_equivalence,
            'modular_arithmetic_certificate': modular_arithmetic_certificate,
            'tail_macro_engine': tail_macro_engine,
            'tail_macro_liveness': tail_macro_liveness,
            'tail_macro_reversibility': tail_macro_reversibility,
            'tail_macro_schedule_search': tail_macro_schedule_search,
            'compiler_parameters': compiler_parameters,
        }),
        'source_binding_summary': {
            'rows_checked': int(source_binding['rows_checked']),
            'rows_by_source_kind': rows_by_source_kind,
            'failure_count': int(source_binding['failure_count']),
        },
        'materialized_flat_netlist': {
            'operation_count': public_totals['operation_count'],
            'non_clifford_count': public_totals['non_clifford'],
            'peak_live_qubits': public_totals['logical_qubits'],
            'operation_stream_sha256': materialized_flat['operation_stream_sha256'],
            'segment_merkle_root_sha256': materialized_flat['segment_merkle_root_sha256'],
            'exact_operation_stream_materialized': bool(materialized_flat['exact_operation_stream_materialized']),
        },
        'covered_boundaries': covered_boundaries,
        'remaining_macro_boundaries': remaining_macro_boundaries,
        'checks': checks,
        'pass': all(checks.values()) and len(remaining_macro_boundaries) > 0,
        'notes': [
            'This audit passing means the current public claim is internally source-bound and the remaining macro boundaries are explicit.',
            'It does not mean the full thread goal is complete; clifford_complete_goal_achieved remains false until the remaining macro boundaries are eliminated.',
        ],
    }


__all__ = ['ENGINE_COMPLETION_AUDIT_SCHEMA', 'build_engine_completion_audit']
