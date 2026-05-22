#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Mapping

from proof_corpus_profiles import GOOGLE_COMPARABLE_CASE_COUNT


PUBLIC_ENGINE_MANIFEST_SCHEMA = 'compiler-project-public-engine-manifest-v1'


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def _stream_hash(rows: List[Mapping[str, Any]], columns: List[str]) -> str:
    digest = hashlib.sha256()
    digest.update(('\t'.join(columns) + '\n').encode('ascii'))
    for row in rows:
        digest.update(('\t'.join(_canonical_json(row[column]) for column in columns) + '\n').encode('ascii'))
    return digest.hexdigest()


def _instruction_rows(instructions: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            'row_index': row_index,
            'pc': int(instruction['pc']),
            'op': str(instruction['op']),
            'reads': list(instruction.get('reads', [])),
            'writes': list(instruction.get('writes', [])),
        }
        for row_index, instruction in enumerate(instructions)
    ]


def _wire_rows(wire_catalog: Mapping[str, Mapping[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            'row_index': row_index,
            'wire_id': str(wire_id),
            'owner_id': str(wire['owner_id']),
            'qubits': int(wire['qubits']),
            'role': str(wire['role']),
        }
        for row_index, (wire_id, wire) in enumerate(sorted(wire_catalog.items()))
    ]


def _schedule_rows(events: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            'row_index': row_index,
            'event_id': str(event['event_id']),
            'event_type': str(event['event_type']),
            'pc_range': [int(value) for value in event['pc_range']],
            'source_instruction_pcs': [int(value) for value in event['source_instruction_pcs']],
            'source_instruction_ops': [str(value) for value in event['source_instruction_ops']],
            'live_wire_ids': list(event['live_wire_ids']),
        }
        for row_index, event in enumerate(events)
    ]


def _owner_rows(owner_capacity: Mapping[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            'row_index': row_index,
            'owner_id': str(row['owner_id']),
            'logical_qubits': int(row['logical_qubits']),
            'required_peak_qubits': int(row['required_peak_qubits']),
            'capacity_pass': bool(row['capacity_pass']),
        }
        for row_index, row in enumerate(owner_capacity['rows'])
    ]


def _resource_term_rows(counted_resource_ir: Mapping[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            'row_index': row_index,
            'term_id': str(term['term_id']),
            'category': str(term['category']),
            'instances': int(term['instances']),
            'per_instance_non_clifford': int(term['per_instance_non_clifford']),
            'total_non_clifford': int(term['total_non_clifford']),
            'source': str(term['source']),
        }
        for row_index, term in enumerate(counted_resource_ir['non_clifford_terms'])
    ]


def _case_category_counts(cases: List[Mapping[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for case in cases:
        category = str(case['category'])
        counts[category] = counts.get(category, 0) + 1
    return dict(sorted(counts.items()))


def build_public_engine_manifest(
    *,
    reusable_chunk_lowering: Mapping[str, Any],
    reusable_chunk_tail_candidate: Mapping[str, Any],
    streamed_lookup_tail_leaf_equivalence: Mapping[str, Any],
    release_corpus_preflight: Mapping[str, Any],
    zkp_attestation_input: Mapping[str, Any],
    arithmetic_operation_ir: Mapping[str, Any],
    qroam_primitive_certificate: Mapping[str, Any],
    phase_shell_lowerings: Mapping[str, Any],
    selected_family_name: str,
) -> Dict[str, Any]:
    executable_resource_engine = reusable_chunk_lowering['executable_resource_engine']
    executable_contract = reusable_chunk_lowering['executable_contract']
    executable_liveness = reusable_chunk_lowering['executable_liveness']
    executable_schedule = executable_liveness['executable_schedule_ir']
    counted_resource_ir = reusable_chunk_lowering['counted_resource_ir']
    counted_resource_engine = reusable_chunk_lowering['counted_resource_engine']
    resource_contract_engine = reusable_chunk_lowering['resource_contract_engine']
    owner_capacity = reusable_chunk_lowering['owner_capacity']
    toy_semantics = reusable_chunk_tail_candidate['toy_semantic_equivalence']
    streamed_equivalence_summary = streamed_lookup_tail_leaf_equivalence['summary']
    release_category_counts = {
        str(category): int(count)
        for category, count in sorted(release_corpus_preflight['category_counts'].items())
    }
    smoke_case_category_counts = _case_category_counts(list(zkp_attestation_input['prepared_case_corpus']['cases']))
    compiler_parameters = zkp_attestation_input['compiler_parameters_document']['payload']
    family_payload = zkp_attestation_input['family_document']['payload']
    selected_phase_shell_name = str(compiler_parameters['phase_shell']['selected_public_shell'])
    phase_register_bits = int(compiler_parameters['phase_shell']['full_phase_register_bits'])
    selected_qroam_block_size = int(compiler_parameters['lookup_policy']['standard_qroamclean_block_size'])
    semantic_required_categories = [
        'random',
        'doubling',
        'inverse',
        'accumulator_infinity',
        'lookup_infinity',
    ]
    tail_opcode = str(reusable_chunk_lowering['chunked_multiplier_primitive_contract']['source_arithmetic_kernel'])
    arithmetic_tail_row = next(
        row
        for row in arithmetic_operation_ir['leaf_arithmetic_summary']['rows']
        if row['opcode'] == tail_opcode
    )
    qroam_counts = qroam_primitive_certificate['traversed_counts']
    selected_phase_shell = next(
        row
        for row in phase_shell_lowerings['families']
        if row['name'] == selected_phase_shell_name
    )

    instruction_rows = _instruction_rows(list(executable_contract['instruction_stream']))
    wire_rows = _wire_rows(executable_liveness['wire_catalog'])
    schedule_rows = _schedule_rows(list(executable_schedule['events']))
    owner_rows = _owner_rows(owner_capacity)
    resource_term_rows = _resource_term_rows(counted_resource_ir)

    instruction_columns = ['row_index', 'pc', 'op', 'reads', 'writes']
    wire_columns = ['row_index', 'wire_id', 'owner_id', 'qubits', 'role']
    schedule_columns = ['row_index', 'event_id', 'event_type', 'pc_range', 'source_instruction_pcs', 'source_instruction_ops', 'live_wire_ids']
    owner_columns = ['row_index', 'owner_id', 'logical_qubits', 'required_peak_qubits', 'capacity_pass']
    term_columns = ['row_index', 'term_id', 'category', 'instances', 'per_instance_non_clifford', 'total_non_clifford', 'source']

    public_totals = {
        'non_clifford': int(executable_resource_engine['public_totals']['non_clifford']),
        'logical_qubits': int(executable_resource_engine['public_totals']['logical_qubits']),
    }
    checks = {
        'executable_resource_engine_passes': executable_resource_engine['pass'] is True,
        'counted_resource_engine_passes': counted_resource_engine['pass'] is True,
        'resource_contract_engine_passes': resource_contract_engine['pass'] is True,
        'public_totals_match_counted_resource_engine': (
            public_totals['non_clifford'] == int(counted_resource_engine['non_clifford_total_from_terms'])
            and public_totals['logical_qubits'] == int(counted_resource_engine['peak_live_qubits_from_intervals'])
        ),
        'public_totals_match_resource_contract_engine': (
            public_totals['logical_qubits'] == int(resource_contract_engine['peak_live_qubits'])
        ),
        'engine_digests_match_bound_documents': (
            executable_resource_engine['counted_resource_ir_sha256'] == counted_resource_engine['counted_resource_ir_sha256']
            and executable_resource_engine['executable_liveness_sha256'] == resource_contract_engine['executable_liveness_sha256']
            and executable_resource_engine['owner_capacity_sha256'] == resource_contract_engine['owner_capacity_sha256']
        ),
        'schedule_rows_bind_instruction_stream': all(
            row['source_instruction_ops'] == [
                instruction_rows_by_pc[pc]['op']
                for pc in row['source_instruction_pcs']
            ]
            for instruction_rows_by_pc in [{row['pc']: row for row in instruction_rows}]
            for row in schedule_rows
        ),
        'wire_rows_cover_liveness_catalog': len(wire_rows) == len(executable_liveness['wire_catalog']),
        'owner_rows_cover_capacity_catalog': len(owner_rows) == len(owner_capacity['rows']),
        'resource_terms_sum_to_public_total': sum(row['total_non_clifford'] for row in resource_term_rows) == public_totals['non_clifford'],
        'streamed_tail_equivalence_covers_required_categories': (
            int(streamed_equivalence_summary['pass']) == int(streamed_equivalence_summary['total'])
            and all(
                category in streamed_equivalence_summary['categories']
                and int(streamed_equivalence_summary['categories'][category]['pass']) == int(streamed_equivalence_summary['categories'][category]['total'])
                and int(streamed_equivalence_summary['categories'][category]['total']) > 0
                for category in semantic_required_categories
            )
        ),
        'toy_tail_semantics_cover_required_categories': (
            toy_semantics['all_rows_semantic'] is True
            and toy_semantics['all_rows_executable'] is True
            and toy_semantics['all_rows_scratch_trace'] is True
            and int(toy_semantics['total_boundary_pairs']) == sum(int(value) for value in toy_semantics['category_totals'].values())
            and all(int(toy_semantics['category_totals'][category]) > 0 for category in ('doubling', 'inverse', 'accumulator_infinity', 'lookup_infinity'))
            and int(toy_semantics['category_totals']['ordinary']) > 0
        ),
        'release_corpus_preflight_covers_required_categories': (
            release_corpus_preflight['pass'] is True
            and int(release_corpus_preflight['case_count']) == GOOGLE_COMPARABLE_CASE_COUNT
            and all(release_category_counts.get(category, 0) > 0 for category in semantic_required_categories)
        ),
        'smoke_case_corpus_covers_required_categories': (
            int(zkp_attestation_input['prepared_case_corpus']['case_count']) == len(zkp_attestation_input['prepared_case_corpus']['cases'])
            and all(smoke_case_category_counts.get(category, 0) > 0 for category in semantic_required_categories)
        ),
        'arithmetic_operation_ir_binds_tail_opcode': (
            arithmetic_operation_ir['pass'] is True
            and arithmetic_tail_row['opcode'] == tail_opcode
            and int(reusable_chunk_lowering['chunked_multiplier_primitive_contract']['chunk_bits']) == int(reusable_chunk_lowering['executable_contract']['chunk_contract']['chunk_bits'])
            and int(arithmetic_operation_ir['leaf_arithmetic_summary']['leaf_opcode_histogram'][tail_opcode]) == int(arithmetic_tail_row['leaf_instance_count'])
            and int(arithmetic_tail_row['kernel_operation_count']) == sum(int(value) for value in arithmetic_tail_row['primitive_counts_total'].values())
            and int(arithmetic_tail_row['kernel_non_clifford_per_instance']) == int(arithmetic_tail_row['primitive_counts_total']['ccx'])
            and int(arithmetic_operation_ir['leaf_arithmetic_summary']['non_clifford_total']) == int(arithmetic_tail_row['primitive_counts_total']['ccx'])
        ),
        'qroam_primitive_stream_binds_stream_terms': (
            qroam_primitive_certificate['pass'] is True
            and int(qroam_primitive_certificate['parameters']['block_size']) == selected_qroam_block_size
            and int(qroam_primitive_certificate['qroamclean_cost_model']['block_size']) == selected_qroam_block_size
            and int(qroam_primitive_certificate['parameters']['target_bits']) == int(reusable_chunk_lowering['stream_plan']['chunk_bits'])
            and int(qroam_counts['per_stream_non_clifford']) == int(qroam_primitive_certificate['qroamclean_cost_model']['lookup_compute_non_clifford']) + int(qroam_primitive_certificate['qroamclean_cost_model']['measured_uncompute_non_clifford'])
            and int(qroam_counts['per_stream_non_clifford']) == int(reusable_chunk_lowering['non_clifford_derivation']['per_chunk_stream_non_clifford'])
            and int(qroam_counts['target_register_qubits']) == int(reusable_chunk_lowering['stream_plan']['chunk_bits'])
            and int(qroam_counts['junk_register_qubits']) == int(reusable_chunk_lowering['qubit_derivation']['qroam_clean_junk_register_qubits'])
            and int(qroam_counts['junk_register_qubits']) == int(qroam_primitive_certificate['qroamclean_cost_model']['junk_register_qubits'])
            and int(qroam_counts['per_stream_non_clifford']) * int(reusable_chunk_lowering['stream_plan']['whole_oracle_chunk_streams']) == int(reusable_chunk_lowering['non_clifford_derivation']['qroam_chunk_non_clifford'])
        ),
        'phase_shell_primitive_counts_bind_public_family': (
            selected_phase_shell['name'] == family_payload['phase_shell']
            and selected_phase_shell['name'] in selected_family_name
            and int(phase_shell_lowerings['phase_register_bits']) == phase_register_bits
            and int(selected_phase_shell['live_quantum_bits']) == int(reusable_chunk_lowering['qubit_derivation']['phase_qubits'])
            and int(selected_phase_shell['live_quantum_bits']) == int(family_payload['live_phase_bits'])
            and int(selected_phase_shell['hadamard_count']) == phase_register_bits
            and int(selected_phase_shell['hadamard_count']) == int(family_payload['phase_shell_hadamards'])
            and int(selected_phase_shell['total_measurements']) == phase_register_bits
            and int(selected_phase_shell['total_measurements']) == int(family_payload['phase_shell_measurements'])
            and int(selected_phase_shell['single_qubit_rotation_count']) == phase_register_bits - 1
            and int(selected_phase_shell['single_qubit_rotation_count']) == int(family_payload['phase_shell_rotations'])
            and int(selected_phase_shell['rotation_depth']) == int(family_payload['phase_shell_rotation_depth'])
            and int(selected_phase_shell['controlled_rotation_count']) == int(selected_phase_shell['total_rotations']) - int(selected_phase_shell['single_qubit_rotation_count'])
        ),
    }
    return {
        'schema': PUBLIC_ENGINE_MANIFEST_SCHEMA,
        'scope': 'current public reusable-chunk executable resource engine manifest',
        'selected_family_name': selected_family_name,
        'source_artifact': 'compiler_verification_project/artifacts/reusable_chunk_lowering.json',
        'engine_source_module': executable_resource_engine['engine_source_module'],
        'public_totals': public_totals,
        'source_digests': {
            'executable_resource_engine_sha256': _sha256_payload(executable_resource_engine),
            'counted_resource_ir_sha256': executable_resource_engine['counted_resource_ir_sha256'],
            'executable_liveness_sha256': executable_resource_engine['executable_liveness_sha256'],
            'owner_capacity_sha256': executable_resource_engine['owner_capacity_sha256'],
            'resource_contract_engine_sha256': executable_resource_engine['resource_contract_engine_sha256'],
        },
        'instruction_stream': {
            'encoding': instruction_columns,
            'row_count': len(instruction_rows),
            'sha256': _stream_hash(instruction_rows, instruction_columns),
            'rows': instruction_rows,
        },
        'wire_catalog_stream': {
            'encoding': wire_columns,
            'row_count': len(wire_rows),
            'sha256': _stream_hash(wire_rows, wire_columns),
            'rows': wire_rows,
        },
        'schedule_stream': {
            'encoding': schedule_columns,
            'row_count': len(schedule_rows),
            'sha256': _stream_hash(schedule_rows, schedule_columns),
            'rows': schedule_rows,
        },
        'owner_capacity_stream': {
            'encoding': owner_columns,
            'row_count': len(owner_rows),
            'sha256': _stream_hash(owner_rows, owner_columns),
            'rows': owner_rows,
        },
        'resource_term_stream': {
            'encoding': term_columns,
            'row_count': len(resource_term_rows),
            'expanded_non_clifford_instances': sum(row['instances'] for row in resource_term_rows),
            'sha256': _stream_hash(resource_term_rows, term_columns),
            'rows': resource_term_rows,
        },
        'semantic_boundary_evidence': {
            'required_categories': semantic_required_categories,
            'streamed_lookup_tail_leaf_equivalence': {
                'schema': streamed_lookup_tail_leaf_equivalence['schema'],
                'sha256': _sha256_payload(streamed_lookup_tail_leaf_equivalence),
                'total': int(streamed_equivalence_summary['total']),
                'pass': int(streamed_equivalence_summary['pass']),
                'categories': streamed_equivalence_summary['categories'],
            },
            'reusable_chunk_tail_toy_semantics': {
                'schema': reusable_chunk_tail_candidate['schema'],
                'sha256': _sha256_payload(reusable_chunk_tail_candidate),
                'total_boundary_pairs': int(toy_semantics['total_boundary_pairs']),
                'scratch_trace_checked': int(toy_semantics['scratch_trace_checked']),
                'category_totals': {
                    category: int(count)
                    for category, count in sorted(toy_semantics['category_totals'].items())
                },
                'all_rows_semantic': bool(toy_semantics['all_rows_semantic']),
                'all_rows_executable': bool(toy_semantics['all_rows_executable']),
                'all_rows_scratch_trace': bool(toy_semantics['all_rows_scratch_trace']),
            },
            'release_corpus_preflight': {
                'schema': release_corpus_preflight['schema'],
                'sha256': _sha256_payload(release_corpus_preflight),
                'profile': release_corpus_preflight['profile'],
                'case_count': int(release_corpus_preflight['case_count']),
                'case_stream_sha256': release_corpus_preflight['case_stream_sha256'],
                'category_counts': release_category_counts,
            },
            'smoke_case_corpus': {
                'input_sha256': _sha256_payload(zkp_attestation_input),
                'case_corpus_sha256': zkp_attestation_input['case_corpus_sha256'],
                'case_count': int(zkp_attestation_input['prepared_case_corpus']['case_count']),
                'category_counts': smoke_case_category_counts,
            },
        },
        'primitive_operation_evidence': {
            'arithmetic_operation_ir': {
                'schema': arithmetic_operation_ir['schema'],
                'sha256': _sha256_payload(arithmetic_operation_ir),
                'pass': bool(arithmetic_operation_ir['pass']),
                'tail_opcode': tail_opcode,
                'tail_kernel_stage_digest_sha256': arithmetic_tail_row['kernel_stage_digest_sha256'],
                'tail_kernel_operation_count': int(arithmetic_tail_row['kernel_operation_count']),
                'tail_kernel_non_clifford_per_instance': int(arithmetic_tail_row['kernel_non_clifford_per_instance']),
                'tail_primitive_counts_total': {
                    key: int(value)
                    for key, value in sorted(arithmetic_tail_row['primitive_counts_total'].items())
                },
                'leaf_arithmetic_operation_stream_sha256': arithmetic_operation_ir['leaf_arithmetic_summary']['operation_stream_sha256'],
            },
            'qroam_primitive_certificate': {
                'schema': qroam_primitive_certificate['schema'],
                'sha256': _sha256_payload(qroam_primitive_certificate),
                'pass': bool(qroam_primitive_certificate['pass']),
                'operation_schema': qroam_primitive_certificate['operation_stream']['operation_schema'],
                'segment_count': int(qroam_primitive_certificate['operation_stream']['segment_count']),
                'segment_merkle_root_sha256': qroam_primitive_certificate['operation_stream']['segment_merkle_root_sha256'],
                'block_size': int(qroam_primitive_certificate['parameters']['block_size']),
                'per_stream_non_clifford': int(qroam_counts['per_stream_non_clifford']),
                'target_register_qubits': int(qroam_counts['target_register_qubits']),
                'junk_register_qubits': int(qroam_counts['junk_register_qubits']),
                'whole_oracle_streams': int(reusable_chunk_lowering['stream_plan']['whole_oracle_chunk_streams']),
                'whole_oracle_non_clifford': int(qroam_counts['per_stream_non_clifford']) * int(reusable_chunk_lowering['stream_plan']['whole_oracle_chunk_streams']),
            },
            'phase_shell': {
                'schema': phase_shell_lowerings['schema'],
                'sha256': _sha256_payload(phase_shell_lowerings),
                'name': selected_phase_shell['name'],
                'phase_register_bits': phase_register_bits,
                'live_quantum_bits': int(selected_phase_shell['live_quantum_bits']),
                'hadamard_count': int(selected_phase_shell['hadamard_count']),
                'total_measurements': int(selected_phase_shell['total_measurements']),
                'single_qubit_rotation_count': int(selected_phase_shell['single_qubit_rotation_count']),
                'controlled_rotation_count': int(selected_phase_shell['controlled_rotation_count']),
                'rotation_depth': int(selected_phase_shell['rotation_depth']),
            },
        },
        'fast_no_zkp_contract': {
            'build_target': 'public-engine-manifest',
            'verify_group': 'public_engine_manifest_checks',
            'prover_required': False,
        },
        'checks': checks,
        'pass': all(checks.values()),
    }


__all__ = [
    'PUBLIC_ENGINE_MANIFEST_SCHEMA',
    'build_public_engine_manifest',
]
