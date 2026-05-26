#!/usr/bin/env python3

from __future__ import annotations

import csv
import json
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from common import (
    SECP_B,
    SECP_G,
    SECP_N,
    SECP_P,
    deterministic_scalars,
    dump_json,
    load_json,
    mul_fixed_window,
    precompute_window_tables,
    sha256_bytes,
    sha256_path,
)
from artifact_digest_tree import ARTIFACT_DIGEST_TREE_SCHEMA, build_artifact_digest_tree
from artifact_registry import BUILD_SUMMARY_ARTIFACT_PATHS, BUILD_SUMMARY_SCHEMA
from arithmetic_lowering import arithmetic_kernel_summary, arithmetic_lowering_library, materialize_arithmetic_primitive_operations
from arithmetic_operation_ir import ARITHMETIC_OPERATION_IR_SCHEMA, build_arithmetic_operation_ir
from compiler_parameters import COMPILER_PARAMETERS_SCHEMA, build_compiler_parameters
from constant_provenance import CONSTANT_PROVENANCE_SCHEMA, build_constant_provenance
from engine_completion_audit import ENGINE_COMPLETION_AUDIT_SCHEMA, build_engine_completion_audit
from fallback_frontier_stress import build_fallback_frontier_stress
from lookup_lowering import lookup_lowering_library, lowered_lookup_semantic_summary, materialize_lookup_primitive_operations
from materialized_circuit import PUBLIC_CANDIDATE_MATERIALIZED_CIRCUIT_MANIFEST_SCHEMA, build_arithmetic_operand_replay_audit, build_public_candidate_materialized_circuit_manifest
from modular_arithmetic_certificate import build_modular_arithmetic_certificate
from phase_shell_lowering import materialize_phase_operations, phase_shell_family_summary, phase_shell_lowering_library
from physical_estimator import (
    build_azure_estimator_target_payload,
    build_or_load_azure_estimator_results_payload,
)
from proof_corpus_profiles import GOOGLE_COMPARABLE_CASE_COUNT, GOOGLE_COMPARABLE_PROFILE, SMOKE_PUBLIC_PROFILE, build_proof_corpus_profiles
from proof_environment_contract import PROOF_ENVIRONMENT_CONTRACT_SCHEMA, build_proof_environment_contract
from proof_publication_status import PROOF_PUBLICATION_STATUS_SCHEMA, build_proof_publication_status
from primary_strict_result import PRIMARY_STRICT_RESULT_SCHEMA, build_primary_strict_result, write_primary_strict_result
from public_engine_contract import (
    CANONICAL_MATERIALIZED_FLAT_NETLIST,
    PUBLIC_ENGINE_CANONICAL_TOTALS_SOURCE,
    PUBLIC_TOTALS_MATCH_CANONICAL_ENGINE_CHECK,
    STRICT_RESOURCE_CLAIM_NOT_YET_ACHIEVED,
)
from public_engine_manifest import PUBLIC_ENGINE_MANIFEST_SCHEMA, build_public_engine_manifest
from public_result import build_public_headline_result, write_public_headline_result
from qroam_primitive import build_qroam_k1_primitive_certificate
from qroam_reference_crosscheck import QROAM_REFERENCE_CROSSCHECK_SCHEMA, build_qroam_reference_crosscheck
from qroam_table_cnot_materialization import QROAM_TABLE_CNOT_MATERIALIZATION_SCHEMA, build_qroam_table_cnot_materialization
from release_corpus_preflight import build_release_corpus_preflight
from reusable_chunk_lowering import build_reusable_chunk_lowering
from reusable_chunk_tail_candidate import build_reusable_chunk_tail_candidate
from resource_ledger import build_logical_resource_ledger, qroam_clean_stream_cost
from resource_certificate import build_resource_liveness_certificate
from resource_ir_engine import (
    RESOURCE_CONTRACT_ENGINE_SCHEMA,
    RESOURCE_IR_ENGINE_SCHEMA,
    evaluate_counted_resource_ir,
    evaluate_resource_contract,
)
from strict_replayed_tail_result import STRICT_REPLAYED_TAIL_HEADLINE_SCHEMA, build_strict_replayed_tail_headline_result
from tail_macro_engine import build_tail_macro_engine
from tail_macro_liveness import build_tail_macro_liveness
from tail_macro_reversibility import build_tail_macro_reversibility
from tail_macro_schedule_search import build_tail_macro_schedule_search
from headline_opcode_coverage import build_headline_opcode_coverage
from headline_resource_manifest import HEADLINE_RESOURCE_MANIFEST_SCHEMA, build_headline_resource_manifest
from hybrid_bridge_search import HYBRID_BRIDGE_SEARCH_SCHEMA, build_hybrid_bridge_search
from project import (
    FIELD_BITS,
    FOLDED_MAG_BITS,
    FOLDED_MAG_DOMAIN,
    FULL_PHASE_REGISTER_BITS,
    PROJECT_ROOT,
    PUBLIC_GOOGLE_BASELINE,
    RAW_WINDOW_BITS,
    _leaf,
    build_azure_logical_counts_payload,
    build_cain_transfer_payload,
    build_ft_ir_compositions_payload,
    build_generated_block_inventories_payload,
    build_qubit_breakthrough_analysis,
    central_executable_leaf,
    exact_leaf_slot_allocation,
    full_attack_inventory,
    leaf_opcode_histogram,
    lookup_fed_leaf_slot_allocation,
    phase_shell_families,
    primitive_multiplier_library,
    raw32_schedule,
    slot_allocation_families,
    standard_qrom_lookup_assessment,
    streamed_lookup_tail_leaf_slot_allocation,
    streamed_lookup_table_multiplier_resource,
    run_full_raw32_semantic_check,
    arithmetic_kernel_library,
    lookup_families,
    structured_raw32_cases,
    table_manifests,
    build_whole_oracle_recount_payload,
)
from subcircuit_equivalence import build_subcircuit_equivalence_artifact


def _check(name: str, passed: bool, expected: Any, observed: Any) -> Dict[str, Any]:
    def _compact_payload(payload: Any) -> Any:
        serialized = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        if len(serialized) <= 4096:
            return payload
        return {
            'summary': 'payload omitted from verification summary because it exceeds the inline size limit',
            'sha256': sha256_bytes(serialized.encode()),
            'size_bytes': len(serialized.encode()),
        }

    return {
        'name': name,
        'pass': int(passed),
        'expected': _compact_payload(expected),
        'observed': _compact_payload(observed),
    }


def _summarize_checks(checks: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        'pass': sum(check['pass'] for check in checks),
        'total': len(checks),
        'checks': checks,
    }


def _canonical_payload_sha256(payload: Any) -> str:
    return sha256_bytes(json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii'))


def _load_artifact(path: Path) -> Dict[str, Any]:
    return load_json(path)


def _primitive_counts_from_operations(primitive_operations: List[List[Any]]) -> Dict[str, int]:
    counts = {'ccx': 0, 'cx': 0, 'x': 0, 'measurement': 0}
    for operation in primitive_operations:
        counts[str(operation[0])] += 1
    return counts


def _phase_counts_from_operations(phase_operations: List[List[Any]]) -> Dict[str, int]:
    counts = {
        'hadamard': 0,
        'measurement': 0,
        'single_qubit_rotation': 0,
        'controlled_rotation': 0,
        'rotation_depth': 0,
    }
    for operation in phase_operations:
        gate = str(operation[0])
        counts[gate] += 1
        if gate in ('single_qubit_rotation', 'controlled_rotation'):
            counts['rotation_depth'] += 1
    return counts


def load_compiler_artifacts(repo_root: Path) -> Dict[str, Any]:
    artifact_root = repo_root / 'compiler_verification_project' / 'artifacts'
    required = {
        'canonical_public_point': artifact_root / 'canonical_public_point.json',
        'compiler_parameters': artifact_root / 'compiler_parameters.json',
        'public_google_baseline_source': artifact_root / 'public_google_baseline_source.json',
        'proof_corpus_profiles': artifact_root / 'proof_corpus_profiles.json',
        'full_raw32_oracle': artifact_root / 'full_raw32_oracle.json',
        'exact_leaf_slot_allocation': artifact_root / 'exact_leaf_slot_allocation.json',
        'lookup_fed_leaf': artifact_root / 'lookup_fed_leaf.json',
        'lookup_fed_leaf_equivalence': artifact_root / 'lookup_fed_leaf_equivalence.json',
        'lookup_fed_leaf_slot_allocation': artifact_root / 'lookup_fed_leaf_slot_allocation.json',
        'streamed_lookup_tail_leaf': artifact_root / 'streamed_lookup_tail_leaf.json',
        'streamed_lookup_tail_leaf_equivalence': artifact_root / 'streamed_lookup_tail_leaf_equivalence.json',
        'streamed_lookup_tail_leaf_slot_allocation': artifact_root / 'streamed_lookup_tail_leaf_slot_allocation.json',
        'arithmetic_lowerings': artifact_root / 'arithmetic_lowerings.json',
        'tail_macro_engine': artifact_root / 'tail_macro_engine.json',
        'arithmetic_operation_ir': artifact_root / 'arithmetic_operation_ir.json',
        'modular_arithmetic_certificate': artifact_root / 'modular_arithmetic_certificate.json',
        'tail_macro_liveness': artifact_root / 'tail_macro_liveness.json',
        'tail_macro_reversibility': artifact_root / 'tail_macro_reversibility.json',
        'tail_macro_schedule_search': artifact_root / 'tail_macro_schedule_search.json',
        'streamed_lookup_table_multiplier_resource': artifact_root / 'streamed_lookup_table_multiplier_resource.json',
        'module_library': artifact_root / 'module_library.json',
        'primitive_multiplier_library': artifact_root / 'primitive_multiplier_library.json',
        'phase_shell_lowerings': artifact_root / 'phase_shell_lowerings.json',
        'phase_shell_families': artifact_root / 'phase_shell_families.json',
        'table_manifests': artifact_root / 'table_manifests.json',
        'lookup_lowerings': artifact_root / 'lookup_lowerings.json',
        'generated_block_inventories': artifact_root / 'generated_block_inventories.json',
        'family_frontier': artifact_root / 'family_frontier.json',
        'standard_qrom_lookup_assessment': artifact_root / 'standard_qrom_lookup_assessment.json',
        'logical_resource_ledger': artifact_root / 'logical_resource_ledger.json',
        'fallback_frontier_stress': artifact_root / 'fallback_frontier_stress.json',
        'reusable_chunk_tail_candidate': artifact_root / 'reusable_chunk_tail_candidate.json',
        'qroam_primitive_certificate': artifact_root / 'qroam_primitive_certificate.json',
        'qroam_reference_crosscheck': artifact_root / 'qroam_reference_crosscheck.json',
        'qroam_table_cnot_materialization': artifact_root / 'qroam_table_cnot_materialization.json',
        'reusable_chunk_lowering': artifact_root / 'reusable_chunk_lowering.json',
        'resource_liveness_certificate': artifact_root / 'resource_liveness_certificate.json',
        'materialized_circuit_manifest': artifact_root / 'materialized_circuit_manifest.json',
        'public_candidate_materialized_circuit_manifest': artifact_root / 'public_candidate_materialized_circuit_manifest.json',
        'arithmetic_operand_replay_audit': artifact_root / 'arithmetic_operand_replay_audit.json',
        'headline_resource_manifest': artifact_root / 'headline_resource_manifest.json',
        'public_engine_manifest': artifact_root / 'public_engine_manifest.json',
        'engine_completion_audit': artifact_root / 'engine_completion_audit.json',
        'qubit_breakthrough_analysis': artifact_root / 'qubit_breakthrough_analysis.json',
        'full_attack_inventory': artifact_root / 'full_attack_inventory.json',
        'ft_ir_compositions': artifact_root / 'ft_ir_compositions.json',
        'whole_oracle_recount': artifact_root / 'whole_oracle_recount.json',
        'release_corpus_preflight': artifact_root / 'release_corpus_preflight.json',
        'subcircuit_equivalence': artifact_root / 'subcircuit_equivalence.json',
        'headline_opcode_coverage': artifact_root / 'headline_opcode_coverage.json',
        'public_headline_result': artifact_root / 'public_headline_result.json',
        'strict_replayed_tail_headline': artifact_root / 'strict_replayed_tail_headline.json',
        'primary_strict_result': artifact_root / 'primary_strict_result.json',
        'hybrid_bridge_search': artifact_root / 'hybrid_bridge_search.json',
        'zkp_attestation_reusable_chunk_candidate_input': artifact_root / 'zkp_attestation_reusable_chunk_candidate' / 'zkp_attestation_input.json',
        'zkp_attestation_reusable_chunk_candidate_public_values': artifact_root / 'zkp_attestation_reusable_chunk_candidate' / 'zkp_attestation_public_values.json',
        'build_summary': artifact_root / 'build_summary.json',
        'cain_exact_transfer': artifact_root / 'cain_exact_transfer.json',
        'azure_resource_estimator_logical_counts': artifact_root / 'azure_resource_estimator_logical_counts.json',
        'azure_resource_estimator_targets': artifact_root / 'azure_resource_estimator_targets.json',
        'azure_resource_estimator_results': artifact_root / 'azure_resource_estimator_results.json',
        'artifact_digest_tree': artifact_root / 'artifact_digest_tree.json',
        'proof_environment_contract': artifact_root / 'proof_environment_contract.json',
        'proof_publication_status': artifact_root / 'proof_publication_status.json',
        'constant_provenance': artifact_root / 'constant_provenance.json',
    }
    if not all(path.exists() for path in required.values()):
        from project import build_all_artifacts, write_cain_transfer

        build_all_artifacts()
        write_cain_transfer()
        write_public_headline_result(baseline=PUBLIC_GOOGLE_BASELINE)
        from strict_replayed_tail_result import write_strict_replayed_tail_headline_result

        write_strict_replayed_tail_headline_result(baseline=PUBLIC_GOOGLE_BASELINE)
        dump_json(
            artifact_root / 'hybrid_bridge_search.json',
            build_hybrid_bridge_search(
                strict_replayed_tail_headline=load_json(artifact_root / 'strict_replayed_tail_headline.json'),
                reusable_chunk_lowering=load_json(artifact_root / 'reusable_chunk_lowering.json'),
            ),
        )
        write_primary_strict_result()
        dump_json(
            artifact_root / 'proof_environment_contract.json',
            build_proof_environment_contract(repo_root=repo_root),
        )
        dump_json(
            artifact_root / 'proof_publication_status.json',
            build_proof_publication_status(repo_root=repo_root),
        )
        dump_json(
            artifact_root / 'constant_provenance.json',
            build_constant_provenance(
                repo_root=repo_root,
                compiler_parameters=load_json(artifact_root / 'compiler_parameters.json'),
                phase_shell_lowerings=load_json(artifact_root / 'phase_shell_lowerings.json'),
                reusable_chunk_lowering=load_json(artifact_root / 'reusable_chunk_lowering.json'),
                zkp_attestation_input=load_json(artifact_root / 'zkp_attestation_reusable_chunk_candidate' / 'zkp_attestation_input.json'),
                public_headline_result=load_json(artifact_root / 'public_headline_result.json'),
                headline_resource_manifest=load_json(artifact_root / 'headline_resource_manifest.json'),
            ),
        )
        dump_json(
            artifact_root / 'public_candidate_materialized_circuit_manifest.json',
            build_public_candidate_materialized_circuit_manifest(
                reusable_chunk_lowering=load_json(artifact_root / 'reusable_chunk_lowering.json'),
                arithmetic_operation_ir=load_json(artifact_root / 'arithmetic_operation_ir.json'),
                lookup_lowerings=load_json(artifact_root / 'lookup_lowerings.json'),
                qroam_primitive_certificate=load_json(artifact_root / 'qroam_primitive_certificate.json'),
                qroam_table_cnot_materialization=load_json(artifact_root / 'qroam_table_cnot_materialization.json'),
                phase_shell_lowerings=load_json(artifact_root / 'phase_shell_lowerings.json'),
                compiler_parameters=load_json(artifact_root / 'compiler_parameters.json'),
                selected_family_name=load_json(artifact_root / 'compiler_parameters.json')['public_headline_policy']['selected_public_family_name'],
                strict_replayed_tail_headline=load_json(artifact_root / 'strict_replayed_tail_headline.json'),
                tail_macro_engine=load_json(artifact_root / 'tail_macro_engine.json'),
            ),
        )
        dump_json(
            artifact_root / 'public_engine_manifest.json',
            build_public_engine_manifest(
                reusable_chunk_lowering=load_json(artifact_root / 'reusable_chunk_lowering.json'),
                reusable_chunk_tail_candidate=load_json(artifact_root / 'reusable_chunk_tail_candidate.json'),
                streamed_lookup_tail_leaf_equivalence=load_json(artifact_root / 'streamed_lookup_tail_leaf_equivalence.json'),
                release_corpus_preflight=load_json(artifact_root / 'release_corpus_preflight.json'),
                compiler_parameters=load_json(artifact_root / 'compiler_parameters.json'),
                arithmetic_operation_ir=load_json(artifact_root / 'arithmetic_operation_ir.json'),
                qroam_primitive_certificate=load_json(artifact_root / 'qroam_primitive_certificate.json'),
                qroam_table_cnot_materialization=load_json(artifact_root / 'qroam_table_cnot_materialization.json'),
                phase_shell_lowerings=load_json(artifact_root / 'phase_shell_lowerings.json'),
                public_candidate_materialized_circuit_manifest=load_json(artifact_root / 'public_candidate_materialized_circuit_manifest.json'),
                selected_family_name=load_json(artifact_root / 'compiler_parameters.json')['public_headline_policy']['selected_public_family_name'],
            ),
        )
        dump_json(
            artifact_root / 'arithmetic_operand_replay_audit.json',
            build_arithmetic_operand_replay_audit(
                public_candidate_materialized_circuit_manifest=load_json(artifact_root / 'public_candidate_materialized_circuit_manifest.json'),
                arithmetic_lowerings=load_json(artifact_root / 'arithmetic_lowerings.json'),
                arithmetic_operation_ir=load_json(artifact_root / 'arithmetic_operation_ir.json'),
            ),
        )
        dump_json(
            artifact_root / 'engine_completion_audit.json',
            build_engine_completion_audit(
                public_engine_manifest=load_json(artifact_root / 'public_engine_manifest.json'),
                public_candidate_materialized_circuit_manifest=load_json(artifact_root / 'public_candidate_materialized_circuit_manifest.json'),
                arithmetic_operand_replay_audit=load_json(artifact_root / 'arithmetic_operand_replay_audit.json'),
                reusable_chunk_lowering=load_json(artifact_root / 'reusable_chunk_lowering.json'),
                arithmetic_operation_ir=load_json(artifact_root / 'arithmetic_operation_ir.json'),
                lookup_lowerings=load_json(artifact_root / 'lookup_lowerings.json'),
                qroam_primitive_certificate=load_json(artifact_root / 'qroam_primitive_certificate.json'),
                qroam_table_cnot_materialization=load_json(artifact_root / 'qroam_table_cnot_materialization.json'),
                phase_shell_lowerings=load_json(artifact_root / 'phase_shell_lowerings.json'),
                release_corpus_preflight=load_json(artifact_root / 'release_corpus_preflight.json'),
                streamed_lookup_tail_leaf_equivalence=load_json(artifact_root / 'streamed_lookup_tail_leaf_equivalence.json'),
                modular_arithmetic_certificate=load_json(artifact_root / 'modular_arithmetic_certificate.json'),
                tail_macro_engine=load_json(artifact_root / 'tail_macro_engine.json'),
                tail_macro_liveness=load_json(artifact_root / 'tail_macro_liveness.json'),
                tail_macro_reversibility=load_json(artifact_root / 'tail_macro_reversibility.json'),
                tail_macro_schedule_search=load_json(artifact_root / 'tail_macro_schedule_search.json'),
                compiler_parameters=load_json(artifact_root / 'compiler_parameters.json'),
                zkp_attestation_input=load_json(artifact_root / 'zkp_attestation_reusable_chunk_candidate' / 'zkp_attestation_input.json'),
            ),
        )
    return {name: _load_artifact(path) for name, path in required.items()}


def _recomputed_canonical_public_point() -> Dict[str, Any]:
    leaf_path = PROJECT_ROOT / 'artifacts' / 'circuits' / 'optimized_pointadd_secp256k1.json'
    scaffold_path = PROJECT_ROOT / 'artifacts' / 'circuits' / 'ecdlp_scaffold_optimized.json'
    leaf_sha = sha256_path(leaf_path)
    scaffold_sha = sha256_path(scaffold_path)
    seed = bytes.fromhex(sha256_bytes(bytes.fromhex(leaf_sha) + bytes.fromhex(scaffold_sha)))
    h_scalar = deterministic_scalars(seed + b'compiler-project-public-point', 1, SECP_N)[0]
    tables = precompute_window_tables(SECP_G, SECP_P, SECP_B, width=8, bits=256)
    point = mul_fixed_window(h_scalar, tables, SECP_P, SECP_B, width=8, order=SECP_N)
    assert point is not None
    return {
        'derivation': 'first deterministic public-point base from the checked-in leaf/scaffold hash stream',
        'leaf_sha256': leaf_sha,
        'scaffold_sha256': scaffold_sha,
        'h_scalar_hex': format(h_scalar, '064x'),
        'point': {
            'x_hex': format(point[0], '064x'),
            'y_hex': format(point[1], '064x'),
        },
    }


def build_canonical_public_point_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    expected = _recomputed_canonical_public_point()
    checks = [
        _check('canonical_public_point_matches_hash_derivation', artifacts['canonical_public_point'] == expected, expected, artifacts['canonical_public_point']),
        _check(
            'table_manifests_share_canonical_public_point',
            artifacts['table_manifests']['canonical_public_point'] == artifacts['canonical_public_point'],
            artifacts['canonical_public_point'],
            artifacts['table_manifests']['canonical_public_point'],
        ),
    ]
    return _summarize_checks(checks)


def build_compiler_parameter_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    parameters = artifacts['compiler_parameters']
    expected = build_compiler_parameters()
    field = parameters['field']
    windowing = parameters['windowing']
    lookup_policy = parameters['lookup_policy']
    reusable_chunk_policy = parameters['reusable_chunk_policy']
    public_headline_policy = parameters['public_headline_policy']
    primary_strict_headline_policy = parameters['primary_strict_headline_policy']
    schedule = artifacts['full_raw32_oracle']
    selected_family = artifacts['logical_resource_ledger']['selected_family_summary']
    headline_family = artifacts['build_summary']['headline']['best_gate_family']
    reusable_chunk = artifacts['reusable_chunk_lowering']
    public_headline = artifacts['public_headline_result']
    checks = [
        _check('compiler_parameters_match_generator', parameters == expected, expected, parameters),
        _check('compiler_parameters_schema_is_current', parameters['schema'] == COMPILER_PARAMETERS_SCHEMA, COMPILER_PARAMETERS_SCHEMA, parameters['schema']),
        _check('compiler_parameters_pass_internal_checks', parameters['pass'] is True and all(parameters['checks'].values()), True, parameters['checks']),
        _check('compiler_parameters_bind_project_field_and_window_constants', field['field_bits'] == FIELD_BITS and windowing['raw_window_bits'] == RAW_WINDOW_BITS and windowing['folded_magnitude_bits'] == FOLDED_MAG_BITS and windowing['folded_magnitude_domain'] == FOLDED_MAG_DOMAIN and windowing['full_raw_windows'] == schedule['raw_window_count'], {'field_bits': FIELD_BITS, 'raw_window_bits': RAW_WINDOW_BITS, 'folded_magnitude_domain': FOLDED_MAG_DOMAIN, 'full_raw_windows': schedule['raw_window_count']}, {'field': field, 'windowing': windowing}),
        _check('compiler_parameters_bind_lookup_resource_policy', lookup_policy['standard_qroamclean_block_size'] == selected_family['qroam_clean_block_size'] and lookup_policy['selected_public_lookup_family'] == headline_family['lookup_family'], {'selected_family_summary': selected_family, 'headline_family': headline_family}, lookup_policy),
        _check('compiler_parameters_bind_reusable_chunk_policy', reusable_chunk_policy['chunk_bits'] == reusable_chunk['stream_plan']['chunk_bits'] and reusable_chunk_policy['chunk_count'] == reusable_chunk['stream_plan']['chunk_count'] and reusable_chunk_policy['scratch_slot'] in reusable_chunk['executable_contract']['arithmetic_slots'], reusable_chunk['stream_plan'], reusable_chunk_policy),
        _check('compiler_parameters_bind_public_headline_policy', reusable_chunk['non_clifford_derivation']['candidate_total_non_clifford'] < public_headline_policy['non_clifford_limit_exclusive'] and reusable_chunk['qubit_derivation']['candidate_total_logical_qubits'] < public_headline_policy['logical_qubit_limit_exclusive'], public_headline_policy, reusable_chunk['qubit_derivation']),
        _check('compiler_parameters_bind_primary_strict_headline_policy', public_headline['selection_policy']['limits'] == primary_strict_headline_policy and public_headline['selected_result']['non_clifford'] < primary_strict_headline_policy['non_clifford_limit_exclusive'] and public_headline['selected_result']['logical_qubits'] < primary_strict_headline_policy['logical_qubit_limit_exclusive'], primary_strict_headline_policy, public_headline['selection_policy']),
        _check('compiler_parameters_digest_is_stable_sha256', isinstance(parameters['parameter_digest_sha256'], str) and len(parameters['parameter_digest_sha256']) == 64, '64 hex chars', parameters['parameter_digest_sha256']),
    ]
    return _summarize_checks(checks)


def build_schedule_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    schedule = artifacts['full_raw32_oracle']
    calls = schedule['leaf_calls']
    phase_a_windows = [schedule['direct_seed']['window_index_within_register']] + [row['window_index_within_register'] for row in calls if row['phase_register'] == 'phase_a']
    phase_b_windows = [row['window_index_within_register'] for row in calls if row['phase_register'] == 'phase_b']
    checks = [
        _check('schedule_matches_generator', schedule == raw32_schedule(), raw32_schedule(), schedule),
        _check('raw_window_count_matches_completed_schedule', schedule['raw_window_count'] == 1 + len(calls), 1 + len(calls), schedule['raw_window_count']),
        _check('phase_a_windows_cover_0_through_15_once', sorted(phase_a_windows) == list(range(16)), list(range(16)), sorted(phase_a_windows)),
        _check('phase_b_windows_cover_0_through_15_once', sorted(phase_b_windows) == list(range(16)), list(range(16)), sorted(phase_b_windows)),
        _check(
            'leaf_call_indexes_are_consecutive',
            [row['call_index'] for row in calls] == list(range(len(calls))),
            list(range(len(calls))),
            [row['call_index'] for row in calls],
        ),
        _check(
            'bit_starts_match_window_indexes',
            all(row['bit_start'] == RAW_WINDOW_BITS * row['window_index_within_register'] and row['bit_width'] == RAW_WINDOW_BITS for row in calls),
            'bit_start == 16 * window_index and bit_width == 16 for every leaf call',
            [{'call_index': row['call_index'], 'bit_start': row['bit_start'], 'window_index_within_register': row['window_index_within_register'], 'bit_width': row['bit_width']} for row in calls],
        ),
        _check(
            'summary_lookup_invocations_match_schedule',
            schedule['summary']['lookup_invocations_total'] == 1 + len(calls),
            1 + len(calls),
            schedule['summary']['lookup_invocations_total'],
        ),
        _check(
            'phase_register_bits_match_two_raw_registers',
            schedule['phase_register_bits_total'] == 2 * FIELD_BITS,
            2 * FIELD_BITS,
            schedule['phase_register_bits_total'],
        ),
        _check(
            'full_phase_register_constant_matches_schedule',
            schedule['phase_register_bits_total'] == FULL_PHASE_REGISTER_BITS,
            FULL_PHASE_REGISTER_BITS,
            schedule['phase_register_bits_total'],
        ),
    ]
    return _summarize_checks(checks)


def build_table_manifest_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    manifests = artifacts['table_manifests']
    checks = [
        _check('table_manifests_match_generator', manifests == table_manifests(), table_manifests(), manifests),
        _check('phase_a_table_count_is_16', len(manifests['phase_a_bases']) == 16, 16, len(manifests['phase_a_bases'])),
        _check('phase_b_table_count_is_16', len(manifests['phase_b_bases']) == 16, 16, len(manifests['phase_b_bases'])),
        _check(
            'folded_contract_matches_compiler_constants',
            manifests['folded_contract'] == {
                'word_bits': RAW_WINDOW_BITS,
                'magnitude_bits': FOLDED_MAG_BITS,
                'positive_domain_size': FOLDED_MAG_DOMAIN,
                'coordinate_bits_per_record': 2 * FIELD_BITS,
            },
            {
                'word_bits': RAW_WINDOW_BITS,
                'magnitude_bits': FOLDED_MAG_BITS,
                'positive_domain_size': FOLDED_MAG_DOMAIN,
                'coordinate_bits_per_record': 2 * FIELD_BITS,
            },
            manifests['folded_contract'],
        ),
    ]
    return _summarize_checks(checks)


def build_arithmetic_kernel_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    kernel = artifacts['module_library']
    arithmetic_lowerings = artifacts['arithmetic_lowerings']
    expected_lowerings = arithmetic_lowering_library(
        field_bits=FIELD_BITS,
        leaf_opcode_histogram=leaf_opcode_histogram(),
        qroam_domain_size=FOLDED_MAG_DOMAIN,
    )
    expected_kernel = arithmetic_kernel_summary(expected_lowerings)
    kernel_lookup = {row['opcode']: row for row in arithmetic_lowerings['kernels']}
    reconstruction = arithmetic_lowerings['leaf_reconstruction']
    expected_leaf_non_clifford = sum(
        leaf_opcode_histogram().get(opcode, 0) * kernel_lookup[opcode]['exact_non_clifford_per_kernel']
        for opcode in leaf_opcode_histogram()
        if opcode in kernel_lookup
    )
    block_operation_reconstruction = []
    stage_operation_reconstruction = []
    kernel_operation_reconstruction = []
    for lowering_kernel in arithmetic_lowerings['kernels']:
        for stage in lowering_kernel['stages']:
            stage_counts = {'ccx': 0, 'cx': 0, 'x': 0, 'measurement': 0}
            for block in stage['blocks']:
                block_counts = _primitive_counts_from_operations(materialize_arithmetic_primitive_operations(block))
                block_operation_reconstruction.append({
                    'kernel': lowering_kernel['opcode'],
                    'stage': stage['name'],
                    'block': block['name'],
                    'expected': block['primitive_counts_total'],
                    'reconstructed': block_counts,
                })
                for key in stage_counts:
                    stage_counts[key] += int(block_counts[key])
            stage_operation_reconstruction.append({
                'kernel': lowering_kernel['opcode'],
                'stage': stage['name'],
                'expected': stage['primitive_counts_total'],
                'reconstructed': stage_counts,
            })
            kernel_operation_reconstruction.append({
                'kernel': lowering_kernel['opcode'],
                'stage': stage['name'],
                'primitive_counts_total': stage_counts,
            })
    kernel_totals_from_stages: Dict[str, Dict[str, int]] = defaultdict(lambda: {'ccx': 0, 'cx': 0, 'x': 0, 'measurement': 0})
    for row in kernel_operation_reconstruction:
        for key in kernel_totals_from_stages[row['kernel']]:
            kernel_totals_from_stages[row['kernel']][key] += int(row['primitive_counts_total'][key])
    checks = [
        _check('arithmetic_lowerings_match_generator', arithmetic_lowerings == expected_lowerings, expected_lowerings, arithmetic_lowerings),
        _check('module_library_matches_lowering_summary', kernel == expected_kernel, expected_kernel, kernel),
        _check('module_library_matches_project_summary', kernel == arithmetic_kernel_library(), arithmetic_kernel_library(), kernel),
        _check(
            'arithmetic_block_totals_reconstruct_from_generated_operations',
            all(row['expected'] == row['reconstructed'] for row in block_operation_reconstruction),
            [row['expected'] for row in block_operation_reconstruction],
            [row['reconstructed'] for row in block_operation_reconstruction],
        ),
        _check(
            'arithmetic_stage_totals_reconstruct_from_block_operations',
            all(row['expected'] == row['reconstructed'] for row in stage_operation_reconstruction),
            [row['expected'] for row in stage_operation_reconstruction],
            [row['reconstructed'] for row in stage_operation_reconstruction],
        ),
        _check(
            'arithmetic_kernel_totals_reconstruct_from_stage_operations',
            all(kernel_lookup[opcode]['primitive_counts_total'] == totals for opcode, totals in kernel_totals_from_stages.items()),
            {opcode: kernel_lookup[opcode]['primitive_counts_total'] for opcode in kernel_totals_from_stages},
            dict(kernel_totals_from_stages),
        ),
        _check('field_add_cost_matches_lowering_kernel', kernel['field_add_non_clifford'] == kernel_lookup['field_add']['exact_non_clifford_per_kernel'], kernel_lookup['field_add']['exact_non_clifford_per_kernel'], kernel['field_add_non_clifford']),
        _check('field_mul_cost_matches_lowering_kernel', kernel['field_mul_non_clifford'] == kernel_lookup['field_mul']['exact_non_clifford_per_kernel'], kernel_lookup['field_mul']['exact_non_clifford_per_kernel'], kernel['field_mul_non_clifford']),
        _check('mul_const_cost_matches_lowering_kernel', kernel['mul_const_non_clifford'] == kernel_lookup['mul_const']['exact_non_clifford_per_kernel'], kernel_lookup['mul_const']['exact_non_clifford_per_kernel'], kernel['mul_const_non_clifford']),
        _check('leaf_opcode_histogram_matches_lowering_reconstruction', kernel['leaf_opcode_histogram'] == reconstruction['leaf_opcode_histogram'], reconstruction['leaf_opcode_histogram'], kernel['leaf_opcode_histogram']),
        _check(
            'arithmetic_leaf_non_clifford_matches_lowering_reconstruction',
            kernel['arithmetic_leaf_non_clifford'] == reconstruction['arithmetic_leaf_non_clifford'] == expected_leaf_non_clifford,
            expected_leaf_non_clifford,
            kernel['arithmetic_leaf_non_clifford'],
        ),
    ]
    return _summarize_checks(checks)


def build_modular_arithmetic_certificate_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    certificate = artifacts['modular_arithmetic_certificate']
    expected = build_modular_arithmetic_certificate(
        arithmetic_lowerings=artifacts['arithmetic_lowerings'],
        field_bits=FIELD_BITS,
    )
    stage_certificate = certificate['field_mul_stage_count_certificate']
    opcode_certificate = certificate['opcode_count_certificate']
    circuit_ir_certificate = certificate.get('executable_circuit_ir_count_certificate', {})
    reduced_cases = certificate['reduced_width_exhaustive_cases']
    checks = [
        _check('modular_arithmetic_certificate_matches_generator', certificate == expected, expected, certificate),
        _check('modular_arithmetic_certificate_schema_is_current', certificate['schema'] == 'compiler-project-modular-arithmetic-certificate-v1', 'compiler-project-modular-arithmetic-certificate-v1', certificate['schema']),
        _check('modular_arithmetic_certificate_passes_internal_checks', certificate['pass'] is True and all(certificate['checks'].values()), True, certificate['checks']),
        _check('modular_arithmetic_certificate_binds_secp256k1_modulus_shape', certificate['secp256k1_parameters']['field_bits'] == FIELD_BITS and certificate['secp256k1_parameters']['shift'] == 32 and certificate['secp256k1_parameters']['low_term'] == 977 and certificate['secp256k1_parameters']['canonical_subtract_passes'] == 2, {'field_bits': FIELD_BITS, 'shift': 32, 'low_term': 977, 'canonical_subtract_passes': 2}, certificate['secp256k1_parameters']),
        _check('modular_arithmetic_certificate_executable_ir_counts_match_lowering', circuit_ir_certificate.get('counts_match_arithmetic_lowerings') is True and circuit_ir_certificate.get('observed_non_clifford_per_opcode') == circuit_ir_certificate.get('expected_non_clifford_per_opcode'), circuit_ir_certificate.get('expected_non_clifford_per_opcode'), circuit_ir_certificate),
        _check('modular_arithmetic_certificate_opcode_counts_match_modular_contracts', opcode_certificate['opcode_counts_match'] is True and opcode_certificate['observed_non_clifford_per_opcode'] == opcode_certificate['expected_non_clifford_per_opcode'] and opcode_certificate['expected_non_clifford_per_opcode']['field_add'] == 2 * (FIELD_BITS - 1) and opcode_certificate['expected_non_clifford_per_opcode']['mul_const'] == 6 * 2 * (FIELD_BITS - 1), {'field_add': 2 * (FIELD_BITS - 1), 'mul_const': 6 * 2 * (FIELD_BITS - 1)}, opcode_certificate),
        _check('modular_arithmetic_certificate_field_mul_stage_counts_match_lowering', stage_certificate['stage_counts_match'] is True and stage_certificate['observed_stage_ccx'] == stage_certificate['expected_stage_ccx'] and stage_certificate['observed_total_ccx'] == stage_certificate['expected_total_ccx'], stage_certificate['expected_stage_ccx'], stage_certificate),
        _check('modular_arithmetic_certificate_reduced_width_cases_are_exhaustive', all(row['pass'] is True and row['rows_checked'] == row['modulus'] * row['modulus'] and row['circuit_ir']['schema'] == 'compiler-project-executable-modular-circuit-ir-v1' for row in reduced_cases), 'all reduced-width rows pass exhaustive p^2 testing through executable modular circuit IR', reduced_cases),
    ]
    return _summarize_checks(checks)


def build_arithmetic_operation_ir_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    arithmetic_ir = artifacts['arithmetic_operation_ir']
    expected = build_arithmetic_operation_ir(
        arithmetic_lowerings=artifacts['arithmetic_lowerings'],
        leaf_opcode_histogram=leaf_opcode_histogram(),
    )
    leaf_summary = arithmetic_ir['leaf_arithmetic_summary']
    exact_stream = arithmetic_ir['selected_leaf_exact_operation_stream']
    kernel_rows = arithmetic_ir['kernels']
    block_rows = [
        block
        for kernel in kernel_rows
        for stage in kernel['stages']
        for block in stage['blocks']
    ]
    checks = [
        _check('arithmetic_operation_ir_matches_generator', arithmetic_ir == expected, expected, arithmetic_ir),
        _check('arithmetic_operation_ir_schema_is_current', arithmetic_ir['schema'] == ARITHMETIC_OPERATION_IR_SCHEMA, ARITHMETIC_OPERATION_IR_SCHEMA, arithmetic_ir['schema']),
        _check('arithmetic_operation_ir_passes_internal_checks', arithmetic_ir['pass'] is True and all(arithmetic_ir['checks'].values()), True, arithmetic_ir['checks']),
        _check('arithmetic_operation_ir_leaf_total_matches_arithmetic_lowering', leaf_summary['primitive_counts_total'] == artifacts['arithmetic_lowerings']['leaf_reconstruction']['primitive_totals'] and leaf_summary['non_clifford_total'] == artifacts['arithmetic_lowerings']['leaf_reconstruction']['arithmetic_leaf_non_clifford'], artifacts['arithmetic_lowerings']['leaf_reconstruction'], leaf_summary),
        _check('arithmetic_operation_ir_selected_leaf_exact_stream_matches_leaf_summary', exact_stream['pass'] is True and exact_stream['gate_totals'] == leaf_summary['primitive_counts_total'] and exact_stream['non_clifford_count'] == leaf_summary['non_clifford_total'] and len(exact_stream['segment_merkle_root_sha256']) == 64, leaf_summary['primitive_counts_total'], exact_stream),
        _check('arithmetic_operation_ir_block_stream_digests_are_present', all(len(block['operation_stream_sha256']) == 64 for block in block_rows), '64 hex chars per block digest', [block['operation_stream_sha256'] for block in block_rows[:8]]),
        _check('arithmetic_operation_ir_tracks_operand_capacity', arithmetic_ir['summary']['max_block_operand_slots_required'] >= FIELD_BITS and all(block['operand_profile']['negative_operand_count'] == 0 for block in block_rows), {'min_operand_slots_required': FIELD_BITS, 'negative_operands': 0}, arithmetic_ir['summary']),
        _check('arithmetic_operation_ir_generator_operand_contracts_pass', arithmetic_ir['checks']['generator_operand_contracts_pass'] is True and arithmetic_ir['checks']['repeated_ladder_generators_use_bit_index_operands'] is True and arithmetic_ir['checks']['non_qroam_generated_ladders_use_typed_ladder_generator'] is True, True, arithmetic_ir['checks']),
        _check('arithmetic_operation_ir_ladder_operands_are_bit_indices_not_operation_ordinals', arithmetic_ir['summary']['generated_ladder_max_operand_slots_required'] <= FIELD_BITS + 32, {'max_expected_ladder_operand_slots': FIELD_BITS + 32}, arithmetic_ir['summary']),
    ]
    return _summarize_checks(checks)


def build_tail_macro_engine_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    engine = artifacts['tail_macro_engine']
    destructive_schedule = engine['destructive_candidate_schedule']
    local_inverse_certificate = destructive_schedule['local_inverse_certificate']
    overwrite_choice_screen = destructive_schedule['overwrite_choice_screen']
    pass_only_schedule = engine['local_inverse_pass_only_schedule']
    operand_screen = engine['operand_overwrite_screen']
    reordered_schedule = engine['reordered_local_inverse_schedule']
    reordered_slot_assignment = engine['reordered_slot_assignment']
    reordered_replay = engine['reordered_replay_certificate']
    fused_output_schedule = engine['fused_output_reordered_schedule']
    fused_output_slot_assignment = engine['fused_output_slot_assignment']
    fused_output_replay = engine['fused_output_replay_certificate']
    fused_output_lowering_contract = engine['fused_output_lowering_contract']
    fused_output_permutation = engine['fused_output_in_place_permutation_certificate']
    six_slot_candidate = engine['six_slot_pair_output_candidate']
    pair_output_determinant = engine['pair_output_determinant_certificate']
    six_slot_lowering_search = engine['six_slot_pair_output_lowering_search']
    slot_gap = engine['slot_gap']
    kernel_lookup = {
        kernel['opcode']: int(kernel['exact_non_clifford_per_kernel'])
        for kernel in artifacts['arithmetic_lowerings']['kernels']
    }
    expected = build_tail_macro_engine(
        field_bits=FIELD_BITS,
        counted_arithmetic_slots=len(artifacts['streamed_lookup_tail_leaf']['arithmetic_slots']),
        kernel_non_clifford_by_opcode=kernel_lookup,
        selected_tail_kernel_non_clifford=kernel_lookup[engine['opcode']],
    )
    checks = [
        _check('tail_macro_engine_matches_generator', engine == expected, expected, engine),
        _check('tail_macro_engine_schema_is_current', engine['schema'] == 'compiler-project-tail-macro-engine-v1', 'compiler-project-tail-macro-engine-v1', engine['schema']),
        _check(
            'tail_macro_engine_cost_binds_selected_tail_kernel',
            engine['pass'] is True
            and engine['checks']['non_clifford_total_matches_selected_tail_kernel'] is True
            and int(engine['non_clifford_total']) == kernel_lookup[engine['opcode']],
            kernel_lookup[engine['opcode']],
            {
                'non_clifford_total': engine['non_clifford_total'],
                'checks': engine['checks'],
            },
        ),
        _check('tail_macro_engine_expands_every_formula_target', engine['checks']['expanded_operation_stream_covers_formula_targets'] is True and engine['expanded_field_operation_stream'][-3:][0]['target'] == 'X3' and engine['expanded_field_operation_stream'][-1]['target'] == 'Z3', 'expanded stream covers all formula targets through X3/Y3/Z3', engine['expanded_field_operation_stream'][-4:]),
        _check('tail_macro_engine_exposes_unproven_three_slot_gap', engine['checks']['counted_slots_cover_expanded_single_assignment_peak'] is False and engine['slot_gap']['additional_field_slots_needed_without_in_place_schedule'] > 0, 'three counted slots do not cover expanded single-assignment peak', engine['slot_gap']),
        _check('tail_macro_engine_generates_strict_capacity_fallback_schedule', engine['expanded_slot_schedule']['peak_field_slots'] == engine['slot_gap']['expanded_single_assignment_peak_field_values'] and engine['expanded_slot_schedule']['additional_logical_qubits_over_counted_leaf'] == engine['slot_gap']['additional_logical_qubits_needed_without_in_place_schedule'] and sorted(engine['expanded_slot_schedule']['final_live_values']) == ['X3', 'Y3', 'Z3'], 'expanded fallback schedule peaks at the slot gap and finishes with only X3/Y3/Z3 live', engine['expanded_slot_schedule']),
        _check('tail_macro_engine_generates_eight_slot_destructive_candidate', destructive_schedule['status'] == 'optimizer_candidate_not_a_reversible_proof' and destructive_schedule['peak_field_slots'] == 8 and destructive_schedule['proxy_metrics']['field_slot_improvement_vs_strict_single_assignment'] == 1 and sorted(destructive_schedule['final_live_values']) == ['X3', 'Y3', 'Z3'], 'unproven optimizer candidate reaches eight field slots without being promoted to public contract', destructive_schedule),
        _check(
            'tail_macro_engine_screens_overwrite_local_inverses',
            local_inverse_certificate['status'] == 'toy_boundary_local_inverse_check_not_full_reversible_proof'
            and local_inverse_certificate['overwrite_row_count'] == 15
            and local_inverse_certificate['passing_row_count'] == 10
            and local_inverse_certificate['failing_row_count'] == 5
            and overwrite_choice_screen['choice_count'] == 23
            and overwrite_choice_screen['passing_choice_count'] == 16
            and overwrite_choice_screen['failing_choice_count'] == 7
            and overwrite_choice_screen['failing_row_indices'] == [1, 16, 17, 18, 19]
            and operand_screen['choice_count'] == 39
            and operand_screen['passing_choice_count'] == 26
            and operand_screen['failing_choice_count'] == 13
            and operand_screen['failing_row_indices'] == [1, 14, 15, 16, 17, 18, 19]
            and slot_gap['destructive_candidate_overwrite_rows_locally_invertible'] is False
            and slot_gap['overwrite_choice_screen_pass'] is False
            and slot_gap['operand_overwrite_screen_pass'] is False
            and pass_only_schedule['peak_field_slots'] == 9
            and slot_gap['local_inverse_pass_only_peak_field_values'] == 9,
            '10 overwrite rows pass local inverse screen, 5 fixed-order rows remain concrete blockers, all expiring-source and operand choices are screened, and the pass-only schedule still peaks at 9 slots',
            {
                'certificate': local_inverse_certificate,
                'choice_screen': overwrite_choice_screen,
                'operand_screen': operand_screen,
                'pass_only_schedule': pass_only_schedule,
            },
        ),
        _check(
            'tail_macro_engine_finds_reordered_eight_slot_local_inverse_schedule',
            reordered_schedule['status'] == 'solution_found_not_full_reversible_circuit_proof'
            and reordered_schedule['solution_found'] is True
            and reordered_schedule['peak_field_slots'] == 8
            and reordered_schedule['overwritten_row_count'] == 10
            and reordered_schedule['invalid_overwrite_count'] == 0
            and reordered_schedule['terminal_live_values'] == ['X3', 'Y3', 'Z3']
            and reordered_slot_assignment['pass'] is True
            and reordered_slot_assignment['peak_field_slots'] == 8
            and reordered_replay['pass'] is True
            and reordered_replay['owner_capacity_pass'] is True
            and reordered_replay['checked_non_infinity_pairs'] == 110082
            and reordered_replay['checked_lookup_infinity_pairs'] == 610
            and slot_gap['reordered_local_inverse_solution_found'] is True
            and slot_gap['reordered_local_inverse_peak_field_values'] == 8,
            'reordered tail DAG reaches eight slots using only overwrite choices that passed the local inverse screen, and the generated replay/owner-capacity certificates pass',
            {
                'schedule': reordered_schedule,
                'slot_assignment': reordered_slot_assignment,
                'replay': reordered_replay,
            },
        ),
        _check(
            'tail_macro_engine_fused_output_stream_is_cost_equivalent_to_expanded_stream',
            engine['checks']['fused_output_stream_cost_matches_expanded_stream'] is True
            and engine['checks']['fused_output_lowering_contract_passes'] is True
            and engine['fused_output_non_clifford_total'] == engine['non_clifford_total']
            and [row['target'] for row in engine['fused_output_field_operation_stream'][-3:]] == ['X3', 'Y3', 'Z3'],
            'fused output stream finishes with X3/Y3/Z3 and preserves expanded non-Clifford total',
            {
                'expanded_non_clifford_total': engine['non_clifford_total'],
                'fused_output_non_clifford_total': engine['fused_output_non_clifford_total'],
                'fused_tail_rows': engine['fused_output_field_operation_stream'][-3:],
                'lowering_contract': fused_output_lowering_contract,
            },
        ),
        _check(
            'tail_macro_engine_finds_fused_output_seven_slot_schedule',
            engine['checks']['fused_output_schedule_reaches_seven_slots'] is True
            and fused_output_schedule['status'] == 'solution_found_with_boundary_replay_and_fused_output_lowering_contract'
            and fused_output_schedule['solution_found'] is True
            and fused_output_schedule['peak_field_slots'] == 7
            and fused_output_schedule['overwritten_row_count'] == 10
            and fused_output_schedule['invalid_overwrite_count'] == 0
            and fused_output_schedule['terminal_live_values'] == ['X3', 'Y3', 'Z3']
            and fused_output_slot_assignment['pass'] is True
            and fused_output_slot_assignment['peak_field_slots'] == 7
            and slot_gap['fused_output_reordered_solution_found'] is True
            and slot_gap['fused_output_reordered_peak_field_values'] == 7
            and slot_gap['fused_output_slot_assignment_peak_field_values'] == 7,
            'fused-output tail DAG reaches seven field slots and the generated owner assignment has seven field-sized owners',
            {
                'schedule': fused_output_schedule,
                'slot_assignment': fused_output_slot_assignment,
                'slot_gap': slot_gap,
            },
        ),
        _check(
            'tail_macro_engine_fused_output_replay_and_owner_capacity_pass',
            engine['checks']['fused_output_replay_passes'] is True
            and fused_output_replay['pass'] is True
            and fused_output_replay['owner_capacity_pass'] is True
            and fused_output_replay['checked_non_infinity_pairs'] == 110082
            and fused_output_replay['checked_lookup_infinity_pairs'] == 610
            and slot_gap['fused_output_replay_pass'] is True,
            'fused-output seven-slot schedule replays across the toy point-add boundary and every counted owner has numeric field capacity',
            fused_output_replay,
        ),
        _check(
            'tail_macro_engine_names_required_fused_output_overwrite_contract',
            fused_output_lowering_contract['status'] == 'fused_output_rows_decomposed_to_counted_field_multiply_accumulate_steps'
            and fused_output_lowering_contract['cost_matches_rows'] is True
            and fused_output_lowering_contract['all_output_overwrites_have_boundary_permutation_contract'] is True
            and fused_output_lowering_contract['overwritten_output_row_count'] == 1
            and fused_output_lowering_contract['rows'][1]['target'] == 'Y3'
            and fused_output_lowering_contract['rows'][1]['schedule_overwritten_source'] == 'C'
            and fused_output_lowering_contract['rows'][1]['overwrite_contract']['kind'] == 'secp256k1_zero_lifted_in_place_field_permutation'
            and fused_output_lowering_contract['rows'][1]['overwrite_contract']['domain_rows_checked'] == 110082,
            'the seven-slot schedule explicitly records its one required zero-lifted in-place output permutation instead of treating it as a free output lane',
            fused_output_lowering_contract,
        ),
        _check(
            'tail_macro_engine_rejects_unguarded_y3_over_n_with_secp256k1_counterexample',
            fused_output_permutation['pass'] is True
            and fused_output_permutation['rejected_unguarded_output_reuse_counterexample']['old_y3_over_n_coefficient'] == 'M'
            and fused_output_permutation['rejected_unguarded_output_reuse_counterexample']['m_value'] == 0
            and fused_output_permutation['selected_output_reuse']['overwritten_source'] == 'C'
            and fused_output_permutation['guard']['logical_qubits'] == 1
            and fused_output_permutation['guard']['non_clifford'] == 510,
            'old Y3-over-N is rejected by an explicit secp256k1 M == 0 witness; selected Y3-over-C uses a counted zero-lift guard',
            fused_output_permutation,
        ),
        _check(
            'tail_macro_engine_proves_y3_over_c_l_zero_domain_and_lookup_infinity_bypass',
            fused_output_permutation['checks']['three_is_invertible_mod_secp256k1_p'] is True
            and fused_output_permutation['checks']['all_checked_lookup_x_coordinates_nonzero'] is True
            and fused_output_permutation['checks']['secp256k1_prime_has_no_affine_x_zero_point'] is True
            and fused_output_permutation['checks']['l_zero_implies_accumulator_infinity_on_valid_non_infinity_lookup_domain'] is True
            and fused_output_permutation['l_zero_domain_proof']['pass'] is True
            and fused_output_replay['checked_lookup_infinity_pairs'] > 0,
            'Y3-over-C zero-lift branch is backed by a secp256k1 L == 0 domain proof and lookup-infinity rows are replayed as bypasses',
            {'permutation': fused_output_permutation, 'replay': fused_output_replay},
        ),
        _check(
            'tail_macro_engine_finds_unpromoted_six_slot_pair_output_candidate',
            six_slot_candidate['pass'] is True
            and six_slot_candidate['status'] == 'semantic_candidate_not_promoted_to_public_headline'
            and six_slot_candidate['peak_field_slots'] == 6
            and six_slot_candidate['terminal_live_values'] == ['X3', 'Y3', 'Z3']
            and six_slot_candidate['replay_certificate']['checked_non_infinity_pairs'] == 110082
            and six_slot_candidate['replay_certificate']['checked_lookup_infinity_pairs'] == 610
            and pair_output_determinant['pass'] is True
            and pair_output_determinant['matrix']['determinant_equals'] == '-Y3'
            and pair_output_determinant['checks']['secp256k1_has_no_affine_y_zero_point'] is True,
            'six-slot candidate uses (I,F)->(M,N) and (E,K)->(X3,Z3) pair permutations but is not promoted until the 2x2 primitive lowering is finalized',
            six_slot_candidate,
        ),
        _check(
            'tail_macro_engine_blocks_six_slot_promotion_without_variable_scale_lowering',
            six_slot_lowering_search['pass'] is True
            and six_slot_lowering_search['promotion_ready'] is False
            and six_slot_lowering_search['status'] == 'blocked_on_variable_in_place_scale_lowering'
            and six_slot_lowering_search['checks']['shear_only_lowering_rejected_because_target_determinant_is_variable'] is True
            and six_slot_lowering_search['checks']['current_kernel_inventory_lacks_required_variable_scale_primitive'] is True
            and six_slot_lowering_search['current_kernel_inventory']['has_variable_in_place_field_scale_without_extra_field_lane'] is False,
            'six-slot semantic candidate is not promoted because current kernels lack a counted no-extra-field-lane variable in-place scale primitive',
            six_slot_lowering_search,
        ),
    ]
    return _summarize_checks(checks)


def build_cleanup_pair_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    leaf = central_executable_leaf()
    hist = artifacts['module_library']['leaf_opcode_histogram']
    extract_ops = [ins for ins in leaf['instructions'] if ins['op'] == 'bool_from_flag']
    cleanup_ops = [ins for ins in leaf['instructions'] if ins['op'] == 'clear_bool_from_flag']
    select_ops = [ins for ins in leaf['instructions'] if ins['op'] == 'select_field_if_flag' and ins.get('flag') == 'f_lookup_inf']
    extract = extract_ops[0] if extract_ops else None
    observed_select_pcs = [ins['pc'] for ins in select_ops]
    checks = [
        _check('single_flag_extract_exists', len(extract_ops) == 1, 1, len(extract_ops)),
        _check(
            'boundary_noop_policy_is_explicit',
            leaf.get('lookup_infinity_policy') == 'boundary_noop',
            'boundary_noop',
            leaf.get('lookup_infinity_policy'),
        ),
        _check('boundary_noop_leaf_has_no_xyz_select_window', observed_select_pcs == [], [], observed_select_pcs),
        _check(
            'boundary_noop_leaf_has_no_cleanup_opcode',
            cleanup_ops == [],
            [],
            [ins['pc'] for ins in cleanup_ops],
        ),
        _check('leaf_histogram_has_no_internal_select_cost', hist.get('select_field_if_flag', 0) == 0, 0, hist.get('select_field_if_flag', 0)),
        _check('leaf_histogram_has_no_cleanup_opcode', hist.get('clear_bool_from_flag', 0) == 0, 0, hist.get('clear_bool_from_flag', 0)),
        _check('legacy_cleanup_opcode_is_absent', 'mbuc_clear_bool' not in hist, False, 'mbuc_clear_bool' in hist),
    ]
    return _summarize_checks(checks)


def build_lookup_lowering_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    lowering = artifacts['lookup_lowerings']
    expected = lookup_lowering_library()
    semantic = lowered_lookup_semantic_summary()
    contract_summary = lowering['lookup_contract_summary']
    families = lowering['families']
    family_lookup = {family['name']: family for family in families}
    reconstructed_family_totals = []
    reconstructed_family_workspace = []
    semantic_pairs = []
    block_operation_reconstruction = []
    stage_operation_reconstruction = []
    for family in families:
        stages = family['stages']
        persistent_total = sum(int(entry['qubits']) for entry in family['persistent_workspace'])
        family_primitive_totals = {'ccx': 0, 'cx': 0, 'x': 0, 'measurement': 0}
        for stage in stages:
            stage_counts = {'ccx': 0, 'cx': 0, 'x': 0, 'measurement': 0}
            for block in stage['blocks']:
                block_counts = _primitive_counts_from_operations(materialize_lookup_primitive_operations(block['primitive_operation_generator']))
                block_operation_reconstruction.append({
                    'family': family['name'],
                    'stage': stage['name'],
                    'block': block['name'],
                    'expected': block['primitive_counts_total'],
                    'reconstructed': block_counts,
                })
                for key in stage_counts:
                    stage_counts[key] += int(block_counts[key])
            stage_operation_reconstruction.append({
                'family': family['name'],
                'stage': stage['name'],
                'expected': stage['primitive_counts_total'],
                'reconstructed': stage_counts,
            })
            for key in family_primitive_totals:
                family_primitive_totals[key] += int(stage_counts[key])
        reconstructed_non_clifford = family_primitive_totals['ccx']
        reconstructed_workspace = max(int(stage['total_workspace_qubits']) for stage in stages)
        reconstructed_family_totals.append({
            'name': family['name'],
            'direct_lookup_non_clifford': reconstructed_non_clifford,
            'per_leaf_lookup_non_clifford': reconstructed_non_clifford,
            'primitive_counts_total': family_primitive_totals,
        })
        reconstructed_family_workspace.append({
            'name': family['name'],
            'persistent_workspace_qubits': persistent_total,
            'peak_total_workspace_qubits': reconstructed_workspace,
        })
        semantic_row = next(row for row in semantic['families'] if row['name'] == family['name'])
        semantic_pairs.append({
            'name': family['name'],
            'canonical_full_exhaustive_pass': semantic_row['canonical_full_exhaustive_pass'],
            'canonical_full_exhaustive_total': semantic_row['canonical_full_exhaustive_total'],
            'multibase_edge_pass': semantic_row['multibase_edge_pass'],
            'multibase_edge_total': semantic_row['multibase_edge_total'],
        })
    checks = [
        _check('lookup_lowering_library_matches_generator', lowering == expected, expected, lowering),
        _check(
            'lookup_block_totals_reconstruct_from_generated_operations',
            all(row['expected'] == row['reconstructed'] for row in block_operation_reconstruction),
            [row['expected'] for row in block_operation_reconstruction],
            [row['reconstructed'] for row in block_operation_reconstruction],
        ),
        _check(
            'lookup_stage_totals_reconstruct_from_block_operations',
            all(row['expected'] == row['reconstructed'] for row in stage_operation_reconstruction),
            [row['expected'] for row in stage_operation_reconstruction],
            [row['reconstructed'] for row in stage_operation_reconstruction],
        ),
        _check(
            'lookup_lowering_contract_summary_matches_constants',
            contract_summary == {
                'word_bits': RAW_WINDOW_BITS,
                'magnitude_bits': FOLDED_MAG_BITS,
                'positive_domain_size': FOLDED_MAG_DOMAIN,
                'coordinate_bits': FIELD_BITS,
            },
            {
                'word_bits': RAW_WINDOW_BITS,
                'magnitude_bits': FOLDED_MAG_BITS,
                'positive_domain_size': FOLDED_MAG_DOMAIN,
                'coordinate_bits': FIELD_BITS,
            },
            contract_summary,
        ),
        _check(
            'lookup_lowering_contract_hash_matches_main_lookup_contract',
            lowering['lookup_contract_sha256'] == sha256_path(PROJECT_ROOT / 'artifacts' / 'lookup' / 'lookup_signed_fold_contract.json'),
            sha256_path(PROJECT_ROOT / 'artifacts' / 'lookup' / 'lookup_signed_fold_contract.json'),
            lowering['lookup_contract_sha256'],
        ),
        _check(
            'lookup_lowering_totals_reconstruct_from_stage_inventory',
            all(
                family_lookup[row['name']]['direct_lookup_non_clifford'] == row['direct_lookup_non_clifford']
                and family_lookup[row['name']]['per_leaf_lookup_non_clifford'] == row['per_leaf_lookup_non_clifford']
                and family_lookup[row['name']]['primitive_counts_total'] == row['primitive_counts_total']
                for row in reconstructed_family_totals
            ),
            reconstructed_family_totals,
            [
                {
                    'name': family['name'],
                    'direct_lookup_non_clifford': family['direct_lookup_non_clifford'],
                    'per_leaf_lookup_non_clifford': family['per_leaf_lookup_non_clifford'],
                    'primitive_counts_total': family['primitive_counts_total'],
                }
                for family in families
            ],
        ),
        _check(
            'lookup_lowering_workspace_reconstructs_from_persistent_plus_peak_stage',
            all(
                family_lookup[row['name']]['workspace_reconstruction']['persistent_workspace_qubits'] == row['persistent_workspace_qubits']
                and family_lookup[row['name']]['workspace_reconstruction']['peak_total_workspace_qubits'] == row['peak_total_workspace_qubits']
                and family_lookup[row['name']]['extra_lookup_workspace_qubits'] == row['peak_total_workspace_qubits']
                for row in reconstructed_family_workspace
            ),
            reconstructed_family_workspace,
            [
                {
                    'name': family['name'],
                    'persistent_workspace_qubits': family['workspace_reconstruction']['persistent_workspace_qubits'],
                    'peak_total_workspace_qubits': family['workspace_reconstruction']['peak_total_workspace_qubits'],
                }
                for family in families
            ],
        ),
        _check(
            'lookup_lowering_semantics_match_contract',
            all(
                row['canonical_full_exhaustive_pass'] == row['canonical_full_exhaustive_total']
                and row['multibase_edge_pass'] == row['multibase_edge_total']
                for row in semantic_pairs
            ),
            [
                {
                    'name': row['name'],
                    'canonical_full_exhaustive': row['canonical_full_exhaustive_total'],
                    'multibase_edge': row['multibase_edge_total'],
                }
                for row in semantic_pairs
            ],
            semantic_pairs,
        ),
    ]
    return _summarize_checks(checks)


def build_phase_shell_lowering_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    lowerings = artifacts['phase_shell_lowerings']
    summary = artifacts['phase_shell_families']
    expected_lowerings = phase_shell_lowering_library(FULL_PHASE_REGISTER_BITS)
    expected_summary = phase_shell_family_summary(expected_lowerings)
    families = {row['name']: row for row in lowerings['families']}
    full_family = families['full_phase_register_v1']
    semiclassical_family = families['semiclassical_qft_v1']
    expected_full_rotations = FULL_PHASE_REGISTER_BITS * (FULL_PHASE_REGISTER_BITS - 1) // 2
    expected_semiclassical_rotations = FULL_PHASE_REGISTER_BITS - 1
    block_operation_reconstruction = []
    stage_operation_reconstruction = []
    family_operation_reconstruction = []
    for family in lowerings['families']:
        family_counts = {
            'hadamard': 0,
            'measurement': 0,
            'single_qubit_rotation': 0,
            'controlled_rotation': 0,
            'rotation_depth': 0,
        }
        for stage in family['stages']:
            stage_counts = {
                'hadamard': 0,
                'measurement': 0,
                'single_qubit_rotation': 0,
                'controlled_rotation': 0,
                'rotation_depth': 0,
            }
            for block in stage['blocks']:
                block_counts = _phase_counts_from_operations(materialize_phase_operations(block['phase_operation_generator']))
                block_operation_reconstruction.append({
                    'family': family['name'],
                    'stage': stage['name'],
                    'block': block['name'],
                    'expected': block['count_profile_total'],
                    'reconstructed': block_counts,
                })
                for key in stage_counts:
                    stage_counts[key] += int(block_counts[key])
            stage_operation_reconstruction.append({
                'family': family['name'],
                'stage': stage['name'],
                'expected': stage['count_profile_total'],
                'reconstructed': stage_counts,
            })
            for key in family_counts:
                family_counts[key] += int(stage_counts[key])
        family_operation_reconstruction.append({
            'name': family['name'],
            'hadamard_count': family_counts['hadamard'],
            'measurement_count': family_counts['measurement'],
            'rotation_count': family_counts['single_qubit_rotation'] + family_counts['controlled_rotation'],
            'rotation_depth': family_counts['rotation_depth'],
            'single_qubit_rotation_count': family_counts['single_qubit_rotation'],
            'controlled_rotation_count': family_counts['controlled_rotation'],
        })
    checks = [
        _check('phase_shell_lowerings_match_generator', lowerings == expected_lowerings, expected_lowerings, lowerings),
        _check('phase_shell_family_summary_matches_lowerings', summary == expected_summary, expected_summary, summary),
        _check(
            'phase_shell_block_totals_reconstruct_from_generated_operations',
            all(row['expected'] == row['reconstructed'] for row in block_operation_reconstruction),
            [row['expected'] for row in block_operation_reconstruction],
            [row['reconstructed'] for row in block_operation_reconstruction],
        ),
        _check(
            'phase_shell_stage_totals_reconstruct_from_block_operations',
            all(row['expected'] == row['reconstructed'] for row in stage_operation_reconstruction),
            [row['expected'] for row in stage_operation_reconstruction],
            [row['reconstructed'] for row in stage_operation_reconstruction],
        ),
        _check(
            'phase_shell_family_totals_reconstruct_from_generated_operations',
            all(
                families[row['name']]['hadamard_count'] == row['hadamard_count']
                and families[row['name']]['measurement_count'] == row['measurement_count']
                and families[row['name']]['rotation_count'] == row['rotation_count']
                and families[row['name']]['rotation_depth'] == row['rotation_depth']
                and families[row['name']]['single_qubit_rotation_count'] == row['single_qubit_rotation_count']
                and families[row['name']]['controlled_rotation_count'] == row['controlled_rotation_count']
                for row in family_operation_reconstruction
            ),
            family_operation_reconstruction,
            [
                {
                    'name': family['name'],
                    'hadamard_count': family['hadamard_count'],
                    'measurement_count': family['measurement_count'],
                    'rotation_count': family['rotation_count'],
                    'rotation_depth': family['rotation_depth'],
                    'single_qubit_rotation_count': family['single_qubit_rotation_count'],
                    'controlled_rotation_count': family['controlled_rotation_count'],
                }
                for family in lowerings['families']
            ],
        ),
        _check(
            'full_phase_register_rotation_ladder_matches_bit_pair_count',
            full_family['rotation_count'] == expected_full_rotations and full_family['controlled_rotation_count'] == expected_full_rotations,
            expected_full_rotations,
            {
                'rotation_count': full_family['rotation_count'],
                'controlled_rotation_count': full_family['controlled_rotation_count'],
            },
        ),
        _check(
            'semiclassical_phase_updates_match_noninitial_bit_count',
            semiclassical_family['rotation_count'] == expected_semiclassical_rotations and semiclassical_family['single_qubit_rotation_count'] == expected_semiclassical_rotations,
            expected_semiclassical_rotations,
            {
                'rotation_count': semiclassical_family['rotation_count'],
                'single_qubit_rotation_count': semiclassical_family['single_qubit_rotation_count'],
            },
        ),
        _check(
            'phase_shell_hadamards_and_measurements_match_phase_bits',
            all(
                family['hadamard_count'] == FULL_PHASE_REGISTER_BITS
                and family['measurement_count'] == FULL_PHASE_REGISTER_BITS
                for family in lowerings['families']
            ),
            FULL_PHASE_REGISTER_BITS,
            [
                {
                    'name': family['name'],
                    'hadamard_count': family['hadamard_count'],
                    'measurement_count': family['measurement_count'],
                }
                for family in lowerings['families']
            ],
        ),
        _check(
            'semiclassical_phase_shell_uses_strictly_fewer_live_qubits_and_rotations',
            semiclassical_family['live_quantum_bits'] < full_family['live_quantum_bits']
            and semiclassical_family['rotation_count'] < full_family['rotation_count'],
            {
                'live_quantum_bits': full_family['live_quantum_bits'],
                'rotation_count': full_family['rotation_count'],
            },
            {
                'live_quantum_bits': semiclassical_family['live_quantum_bits'],
                'rotation_count': semiclassical_family['rotation_count'],
            },
        ),
    ]
    return _summarize_checks(checks)


def build_generated_block_inventory_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    generated = artifacts['generated_block_inventories']
    expected = build_generated_block_inventories_payload(
        schedule=artifacts['full_raw32_oracle'],
        kernel=artifacts['module_library'],
        arithmetic_lowerings=artifacts['arithmetic_lowerings'],
        lookup_lowerings=artifacts['lookup_lowerings'],
        phase_shells=artifacts['phase_shell_lowerings']['families'],
        field_bits=FIELD_BITS,
        public_google_baseline=artifacts['family_frontier']['public_google_baseline'],
    )
    families = generated['families']
    frontier_lookup = {row['name']: row for row in artifacts['family_frontier']['families']}
    reconstruction_rows = []
    arithmetic_whole_oracle_non_clifford = sum(
        int(block['primitive_counts_total']['ccx'])
        for block in generated['shared_arithmetic_blocks']
    )
    for family in families:
        primitive_totals = {
            key: sum(int(block['primitive_counts_total'][key]) for block in family['non_clifford_blocks'])
            for key in ('ccx', 'cx', 'x', 'measurement')
        }
        qubit_total = sum(int(block['logical_qubits']) for block in family['qubit_blocks'])
        phase_hadamards = sum(int(block['count']) for block in family['phase_count_blocks'] if block['category'] == 'phase_hadamards')
        phase_measurements = sum(int(block['count']) for block in family['phase_count_blocks'] if block['category'] == 'phase_measurements')
        phase_rotations = sum(
            int(block['count'])
            for block in family['phase_count_blocks']
            if block['category'] in ('phase_single_qubit_rotations', 'phase_controlled_rotations')
        )
        phase_rotation_depth = sum(int(block['count']) for block in family['phase_count_blocks'] if block['category'] == 'phase_rotation_depth')
        direct_seed_non_clifford = sum(
            int(block['primitive_counts_total']['ccx'])
            for block in family['non_clifford_blocks']
            if block['metadata'].get('invocation_scope') == 'direct_seed'
        )
        repeated_leaf_lookup_non_clifford = sum(
            int(block['primitive_counts_total']['ccx'])
            for block in family['non_clifford_blocks']
            if block['metadata'].get('invocation_scope') == 'repeated_leaf_calls'
            and block['category'] == 'lookup_non_clifford'
        )
        reconstruction_rows.append(
            {
                'name': family['name'],
                'full_oracle_non_clifford': primitive_totals['ccx'],
                'total_logical_qubits': qubit_total,
                'direct_seed_non_clifford': direct_seed_non_clifford,
                'per_leaf_lookup_non_clifford': repeated_leaf_lookup_non_clifford // artifacts['full_raw32_oracle']['summary']['leaf_call_count_total'],
                'phase_shell_hadamards': phase_hadamards,
                'phase_shell_measurements': phase_measurements,
                'phase_shell_rotations': phase_rotations,
                'phase_shell_rotation_depth': phase_rotation_depth,
            }
        )
    checks = [
        _check('generated_block_inventories_match_generator', generated == expected, expected, generated),
        _check(
            'generated_block_inventory_schema_matches_current_version',
            generated['schema'] == 'compiler-project-generated-block-inventories-v2',
            'compiler-project-generated-block-inventories-v2',
            generated['schema'],
        ),
        _check(
            'generated_block_inventory_source_paths_match_expected',
            generated['source_artifacts'] == {
                'full_raw32_oracle': 'compiler_verification_project/artifacts/full_raw32_oracle.json',
                'slot_allocations': [row.source_artifact for row in slot_allocation_families()],
                'arithmetic_lowerings': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
                'lookup_lowerings': 'compiler_verification_project/artifacts/lookup_lowerings.json',
                'phase_shell_lowerings': 'compiler_verification_project/artifacts/phase_shell_lowerings.json',
            },
            {
                'full_raw32_oracle': 'compiler_verification_project/artifacts/full_raw32_oracle.json',
                'slot_allocations': [row.source_artifact for row in slot_allocation_families()],
                'arithmetic_lowerings': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
                'lookup_lowerings': 'compiler_verification_project/artifacts/lookup_lowerings.json',
                'phase_shell_lowerings': 'compiler_verification_project/artifacts/phase_shell_lowerings.json',
            },
            generated['source_artifacts'],
        ),
        _check(
            'generated_block_inventory_arithmetic_family_matches_arithmetic_lowerings',
            generated['arithmetic_lowering_family'] == artifacts['arithmetic_lowerings']['family'],
            artifacts['arithmetic_lowerings']['family'],
            generated['arithmetic_lowering_family'],
        ),
        _check(
            'shared_arithmetic_blocks_match_leaf_reconstruction_times_schedule',
            arithmetic_whole_oracle_non_clifford
            == artifacts['arithmetic_lowerings']['leaf_reconstruction']['arithmetic_leaf_non_clifford']
            * artifacts['full_raw32_oracle']['summary']['leaf_call_count_total'],
            artifacts['arithmetic_lowerings']['leaf_reconstruction']['arithmetic_leaf_non_clifford']
            * artifacts['full_raw32_oracle']['summary']['leaf_call_count_total'],
            arithmetic_whole_oracle_non_clifford,
        ),
        _check(
            'generated_block_inventory_family_reconstruction_matches_blocks',
            all(
                next(row for row in reconstruction_rows if row['name'] == family['name'])['full_oracle_non_clifford'] == family['reconstruction']['full_oracle_non_clifford']
                and next(row for row in reconstruction_rows if row['name'] == family['name'])['total_logical_qubits'] == family['reconstruction']['total_logical_qubits']
                and next(row for row in reconstruction_rows if row['name'] == family['name'])['direct_seed_non_clifford'] == family['reconstruction']['direct_seed_non_clifford']
                and next(row for row in reconstruction_rows if row['name'] == family['name'])['per_leaf_lookup_non_clifford'] == family['reconstruction']['per_leaf_lookup_non_clifford']
                and next(row for row in reconstruction_rows if row['name'] == family['name'])['phase_shell_hadamards'] == family['reconstruction']['phase_shell_hadamards']
                and next(row for row in reconstruction_rows if row['name'] == family['name'])['phase_shell_measurements'] == family['reconstruction']['phase_shell_measurements']
                and next(row for row in reconstruction_rows if row['name'] == family['name'])['phase_shell_rotations'] == family['reconstruction']['phase_shell_rotations']
                and next(row for row in reconstruction_rows if row['name'] == family['name'])['phase_shell_rotation_depth'] == family['reconstruction']['phase_shell_rotation_depth']
                for family in families
            ),
            reconstruction_rows,
            [family['reconstruction'] for family in families],
        ),
        _check(
            'frontier_family_totals_match_generated_block_reconstruction',
            all(
                frontier_lookup[family['name']]['full_oracle_non_clifford'] == family['reconstruction']['full_oracle_non_clifford']
                and frontier_lookup[family['name']]['total_logical_qubits'] == family['reconstruction']['total_logical_qubits']
                for family in families
            ),
            [family['reconstruction'] for family in families],
            [
                {
                    'name': family['name'],
                    'full_oracle_non_clifford': frontier_lookup[family['name']]['full_oracle_non_clifford'],
                    'total_logical_qubits': frontier_lookup[family['name']]['total_logical_qubits'],
                }
                for family in families
            ],
        ),
        _check(
            'generated_block_inventory_best_families_match_frontier',
            generated['best_gate_family']['name'] == artifacts['family_frontier']['best_gate_family']['name']
            and generated['best_qubit_family']['name'] == artifacts['family_frontier']['best_qubit_family']['name'],
            {
                'best_gate_family': artifacts['family_frontier']['best_gate_family']['name'],
                'best_qubit_family': artifacts['family_frontier']['best_qubit_family']['name'],
            },
            generated['best_gate_family'] | {'best_qubit_family': generated['best_qubit_family']['name']},
        ),
    ]
    return _summarize_checks(checks)


def _versions_during_write(slot_alloc: Mapping[str, Any], pc: int) -> Tuple[set[Tuple[str, int]], set[Tuple[str, int]]]:
    before = set()
    during = set()
    for entry in slot_alloc['versions']:
        slot = (entry['reg_type'], entry['assigned_slot'])
        if entry['def_pc'] < pc <= entry['last_use_pc'] or (entry['def_pc'] < pc and entry['last_use_pc'] == pc):
            before.add(slot)
        if entry['def_pc'] < pc <= entry['last_use_pc'] or entry['def_pc'] == pc:
            during.add(slot)
    return before, during


def _build_slot_allocation_checks(
    slot_alloc: Mapping[str, Any],
    expected_slot_alloc: Mapping[str, Any],
    leaf: Mapping[str, Any],
    arithmetic_registers: List[str],
    control_registers: List[str],
) -> Dict[str, Any]:
    overlap_violations: List[Dict[str, Any]] = []
    slot_buckets: Dict[Tuple[str, int], List[Dict[str, Any]]] = defaultdict(list)
    for entry in slot_alloc['versions']:
        slot_buckets[(entry['reg_type'], entry['assigned_slot'])].append(entry)
    for (reg_type, assigned_slot), entries in slot_buckets.items():
        ordered = sorted(entries, key=lambda row: (row['def_pc'], row['last_use_pc'], row['version_id']))
        for left, right in zip(ordered, ordered[1:]):
            if right['def_pc'] < left['last_use_pc']:
                overlap_violations.append({
                    'reg_type': reg_type,
                    'assigned_slot': assigned_slot,
                    'left_version_id': left['version_id'],
                    'right_version_id': right['version_id'],
                    'left_interval': [left['def_pc'], left['last_use_pc']],
                    'right_interval': [right['def_pc'], right['last_use_pc']],
                })
    reconstructed = []
    for row in slot_alloc['per_pc']:
        before, during = _versions_during_write(slot_alloc, row['pc'])
        reconstructed.append({
            'pc': row['pc'],
            'opcode': row['opcode'],
            'arithmetic_slots_live_before_write': sum(1 for reg_type, _ in before if reg_type == 'arithmetic'),
            'control_slots_live_before_write': sum(1 for reg_type, _ in before if reg_type == 'control'),
            'arithmetic_slots_needed_during_write': sum(1 for reg_type, _ in during if reg_type == 'arithmetic'),
            'control_slots_needed_during_write': sum(1 for reg_type, _ in during if reg_type == 'control'),
            'dst': row['dst'],
            'reuses_existing_slot': row['reuses_existing_slot'],
        })
    reconstructed_peak_arithmetic = max(entry['arithmetic_slots_needed_during_write'] for entry in reconstructed)
    reconstructed_peak_control = max(entry['control_slots_needed_during_write'] for entry in reconstructed)
    reconstructed_peak_total = max(entry['arithmetic_slots_needed_during_write'] + entry['control_slots_needed_during_write'] for entry in reconstructed)
    assigned_arithmetic_span = 1 + max(entry['assigned_slot'] for entry in slot_alloc['versions'] if entry['reg_type'] == 'arithmetic')
    assigned_control_span = 1 + max(entry['assigned_slot'] for entry in slot_alloc['versions'] if entry['reg_type'] == 'control')
    checks = [
        _check('slot_allocation_matches_generator', slot_alloc == expected_slot_alloc, expected_slot_alloc, slot_alloc),
        _check('tracked_arithmetic_registers_match_register_map', slot_alloc['tracked_arithmetic_registers'] == arithmetic_registers, arithmetic_registers, slot_alloc['tracked_arithmetic_registers']),
        _check('tracked_control_registers_match_register_map', slot_alloc['tracked_control_registers'] == control_registers, control_registers, slot_alloc['tracked_control_registers']),
        _check('version_intervals_do_not_overlap_on_same_slot', len(overlap_violations) == 0, [], overlap_violations),
        _check(
            'per_pc_live_counts_match_assigned_intervals',
            slot_alloc['per_pc'] == reconstructed,
            reconstructed,
            slot_alloc['per_pc'],
        ),
        _check(
            'peak_arithmetic_slots_match_reconstructed_live_set',
            slot_alloc['peak_arithmetic_slots']['count'] == reconstructed_peak_arithmetic,
            reconstructed_peak_arithmetic,
            slot_alloc['peak_arithmetic_slots']['count'],
        ),
        _check(
            'allocator_summary_arithmetic_slot_span_matches_assigned_versions',
            slot_alloc['allocator_summary']['exact_arithmetic_slot_count'] == assigned_arithmetic_span,
            assigned_arithmetic_span,
            slot_alloc['allocator_summary']['exact_arithmetic_slot_count'],
        ),
        _check(
            'peak_control_slots_match_reconstructed_live_set',
            slot_alloc['peak_control_slots']['count'] == reconstructed_peak_control,
            reconstructed_peak_control,
            slot_alloc['peak_control_slots']['count'],
        ),
        _check(
            'allocator_summary_control_slot_span_matches_assigned_versions',
            slot_alloc['allocator_summary']['exact_control_slot_count'] == assigned_control_span,
            assigned_control_span,
            slot_alloc['allocator_summary']['exact_control_slot_count'],
        ),
        _check(
            'peak_total_matches_reconstructed_live_set',
            slot_alloc['peak_total_slots']['count'] == reconstructed_peak_total,
            reconstructed_peak_total,
            slot_alloc['peak_total_slots']['count'],
        ),
        _check(
            'per_pc_rows_cover_leaf_instruction_count',
            len(slot_alloc['per_pc']) == len(leaf['instructions']),
            len(leaf['instructions']),
            len(slot_alloc['per_pc']),
        ),
    ]
    return _summarize_checks(checks)


def build_slot_allocation_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    return _build_slot_allocation_checks(
        slot_alloc=artifacts['exact_leaf_slot_allocation'],
        expected_slot_alloc=exact_leaf_slot_allocation(),
        leaf=central_executable_leaf(),
        arithmetic_registers=sorted(artifacts['exact_leaf_slot_allocation']['tracked_arithmetic_registers']),
        control_registers=sorted(artifacts['exact_leaf_slot_allocation']['tracked_control_registers']),
    )


def build_lookup_fed_slot_allocation_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    slot_alloc = artifacts['lookup_fed_leaf_slot_allocation']
    return _build_slot_allocation_checks(
        slot_alloc=slot_alloc,
        expected_slot_alloc=lookup_fed_leaf_slot_allocation(),
        leaf=artifacts['lookup_fed_leaf'],
        arithmetic_registers=sorted(slot_alloc['tracked_arithmetic_registers']),
        control_registers=sorted(slot_alloc['tracked_control_registers']),
    )


def build_streamed_lookup_tail_slot_allocation_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    slot_alloc = artifacts['streamed_lookup_tail_leaf_slot_allocation']
    base_checks = _build_slot_allocation_checks(
        slot_alloc=slot_alloc,
        expected_slot_alloc=streamed_lookup_tail_leaf_slot_allocation(),
        leaf=artifacts['streamed_lookup_tail_leaf'],
        arithmetic_registers=sorted(slot_alloc['tracked_arithmetic_registers']),
        control_registers=sorted(slot_alloc['tracked_control_registers']),
    )
    ownership = slot_alloc['resource_ownership']
    owner_failures = [
        owner['owner']
        for owner in ownership['owners']
        if int(owner['logical_qubit_budget']) < int(owner['required_logical_qubits'])
    ]
    extra_checks = [
        _check(
            'streamed_lookup_tail_peak_arithmetic_slots_is_three',
            slot_alloc['allocator_summary']['exact_arithmetic_slot_count'] == 3
            and slot_alloc['peak_arithmetic_slots']['count'] == 3,
            {'exact_arithmetic_slot_count': 3, 'peak_arithmetic_slots': 3},
            {
                'exact_arithmetic_slot_count': slot_alloc['allocator_summary']['exact_arithmetic_slot_count'],
                'peak_arithmetic_slots': slot_alloc['peak_arithmetic_slots']['count'],
            },
        ),
        _check(
            'streamed_lookup_tail_has_no_borrowed_lookup_field_lanes',
            slot_alloc['allocator_summary']['exact_borrowed_field_slot_count'] == 0
            and ownership['lookup_interface_policy']['coordinate_field_lanes_materialized_by_leaf'] == 0,
            0,
            {
                'borrowed_field_slot_count': slot_alloc['allocator_summary']['exact_borrowed_field_slot_count'],
                'coordinate_field_lanes_materialized_by_leaf': ownership['lookup_interface_policy']['coordinate_field_lanes_materialized_by_leaf'],
            },
        ),
        _check(
            'resource_owner_capacity_covers_peak_live_wires',
            ownership['no_free_quantum_wire_invariant']['passes'] and not owner_failures,
            [],
            owner_failures,
        ),
    ]
    return {
        'pass': base_checks['pass'] + sum(check['pass'] for check in extra_checks),
        'total': base_checks['total'] + len(extra_checks),
        'checks': [*base_checks['checks'], *extra_checks],
    }


def build_streamed_lookup_table_multiplier_resource_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    resource = artifacts['streamed_lookup_table_multiplier_resource']
    expected_resource = streamed_lookup_table_multiplier_resource(
        arithmetic_lowerings=artifacts['arithmetic_lowerings'],
        lookup_lowerings=artifacts['lookup_lowerings'],
    )
    model = resource['streamed_data_selection_model']
    workspace = resource['workspace_contract']
    lookup_family = next(row for row in artifacts['lookup_lowerings']['families'] if row['name'] == resource['selected_lookup_family'])
    expected_folded_workspace = int(lookup_family['workspace_reconstruction']['persistent_workspace_qubits'])
    qroam_block_size = int(model['qroam_block_size'])
    qroam_target_bitsize = int(model['qroam_target_bitsize'])
    qroam_domain_size = int(model['folded_coordinate_domain_size'])
    qroam_cost = qroam_clean_stream_cost(qroam_domain_size, qroam_target_bitsize, qroam_block_size)
    qroam_expected_compute = int(qroam_cost['lookup_compute_non_clifford'])
    qroam_expected_uncompute = int(qroam_cost['measured_uncompute_non_clifford'])
    qroam_expected_per_kernel = int(qroam_cost['per_stream_non_clifford'])
    qroam_expected_local_workspace = int(qroam_cost['target_plus_junk_qubits'])
    qroam_expected_junk_workspace = int(qroam_cost['junk_register_qubits'])
    source_failures = [
        row
        for row in resource['coordinate_bit_sources']
        if any(int(cost) != int(model['per_kernel_non_clifford']) for cost in row['data_select_non_clifford_per_stream'])
        or not row['stage_names']
    ]
    arithmetic_lookup = {kernel['opcode']: kernel for kernel in artifacts['arithmetic_lowerings']['kernels']}
    table_kernel_failures = [
        opcode
        for opcode in ('field_mul_lookup_x', 'field_mul_lookup_y', 'field_mul_lookup_sum')
        if not any(stage['category'] == 'streamed_lookup_data_select' for stage in arithmetic_lookup[opcode]['stages'])
    ]
    complete_tail = arithmetic_lookup['complete_a0_all_streamed_tail']
    checks = [
        _check('streamed_lookup_table_multiplier_resource_matches_generator', resource == expected_resource, expected_resource, resource),
        _check('streamed_lookup_table_multiplier_schema_is_current', resource['schema'] == 'compiler-project-standard-qroam-streamed-lookup-table-resource-v1', 'compiler-project-standard-qroam-streamed-lookup-table-resource-v1', resource['schema']),
        _check('streamed_lookup_table_multiplier_uses_15_bit_folded_path', model['folded_magnitude_bits'] == 15, 15, model['folded_magnitude_bits']),
        _check('streamed_lookup_table_multiplier_is_standard_qroam', model['standard_qrom_equivalent'] is True and model['primitive'] == 'standard_qroam_clean_full_coordinate_stream', {'standard_qrom_equivalent': True, 'primitive': 'standard_qroam_clean_full_coordinate_stream'}, {'standard_qrom_equivalent': model['standard_qrom_equivalent'], 'primitive': model['primitive']}),
        _check('streamed_lookup_table_multiplier_counts_qroam_coordinate_stream', model['per_kernel_non_clifford'] == qroam_expected_per_kernel and model['decomposition']['lookup_compute_non_clifford'] == qroam_expected_compute and model['decomposition']['measured_uncompute_non_clifford'] == qroam_expected_uncompute, {'per_kernel_non_clifford': qroam_expected_per_kernel, 'lookup_compute_non_clifford': qroam_expected_compute, 'measured_uncompute_non_clifford': qroam_expected_uncompute}, model),
        _check('streamed_lookup_table_multiplier_counts_five_leaf_kernels', model['per_leaf_streamed_kernel_count'] == 5, 5, model['per_leaf_streamed_kernel_count']),
        _check('streamed_lookup_table_multiplier_per_leaf_cost_is_explicit', model['per_leaf_data_select_non_clifford'] == 5 * qroam_expected_per_kernel, 5 * qroam_expected_per_kernel, model['per_leaf_data_select_non_clifford']),
        _check('streamed_lookup_table_multiplier_source_rows_have_data_select_stages', not source_failures, [], source_failures),
        _check('streamed_lookup_table_multiplier_top_level_kernels_have_data_select_stage', not table_kernel_failures, [], table_kernel_failures),
        _check(
            'streamed_lookup_table_multiplier_complete_tail_internal_xy_has_data_select_stage',
            any(stage['category'] == 'streamed_lookup_data_select' for stage in complete_tail['stages']),
            True,
            [stage['category'] for stage in complete_tail['stages']],
        ),
        _check('streamed_lookup_table_multiplier_workspace_contract_passes', workspace['passes'], True, workspace),
        _check('streamed_lookup_table_multiplier_counts_qroam_workspace', workspace['lookup_workspace_qubits'] == expected_folded_workspace + qroam_expected_local_workspace and workspace['folded_control_workspace_qubits'] == expected_folded_workspace and workspace['standard_qroam_local_workspace_qubits'] == qroam_expected_local_workspace and workspace['qroam_clean_target_register_qubits'] == qroam_target_bitsize and workspace['qroam_clean_junk_register_qubits'] == qroam_expected_junk_workspace, {'lookup_workspace_qubits': expected_folded_workspace + qroam_expected_local_workspace, 'folded_control_workspace_qubits': expected_folded_workspace, 'standard_qroam_local_workspace_qubits': qroam_expected_local_workspace, 'qroam_clean_target_register_qubits': qroam_target_bitsize, 'qroam_clean_junk_register_qubits': qroam_expected_junk_workspace}, workspace),
        _check('streamed_lookup_table_multiplier_materializes_no_coordinate_field_lanes', workspace['coordinate_field_lanes_materialized'] == 0 and workspace['coordinate_field_lane_qubits_materialized'] == 0, 0, workspace),
        _check('streamed_lookup_table_multiplier_all_streams_use_standard_qroam_cost', resource['capacity_check']['all_coordinate_streams_use_standard_qroam_cost'], True, resource['capacity_check']),
        _check('streamed_lookup_table_multiplier_qroam_capacity_matches_cost_model', resource['capacity_check']['qroam_clean_capacity_matches_cost_model'], True, resource['capacity_check']),
    ]
    return _summarize_checks(checks)


def build_tail_macro_liveness_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    artifact = artifacts['tail_macro_liveness']
    expected = build_tail_macro_liveness(
        field_bits=FIELD_BITS,
        counted_arithmetic_slots=len(artifacts['streamed_lookup_tail_leaf']['arithmetic_slots']),
    )
    gap = artifact['gap_analysis']
    checks = [
        _check('tail_macro_liveness_matches_generator', artifact == expected, expected, artifact),
        _check('tail_macro_liveness_schema_is_current', artifact['schema'] == 'compiler-project-tail-macro-liveness-v1', 'compiler-project-tail-macro-liveness-v1', artifact['schema']),
        _check('tail_macro_liveness_tracks_current_macro_opcode', artifact['opcode'] == 'complete_a0_all_streamed_tail', 'complete_a0_all_streamed_tail', artifact['opcode']),
        _check('tail_macro_liveness_uses_streamed_leaf_slot_budget', artifact['counted_arithmetic_slots'] == len(artifacts['streamed_lookup_tail_leaf']['arithmetic_slots']), len(artifacts['streamed_lookup_tail_leaf']['arithmetic_slots']), artifact['counted_arithmetic_slots']),
        _check('tail_macro_liveness_exposes_no_recompute_gap',
               gap['one_compute_peak_field_values'] > gap['counted_arithmetic_slots']
               and gap['non_destructive_recompute_minimum_peak_field_values'] > gap['counted_arithmetic_slots']
               and gap['additional_field_slots_needed_without_recompute_or_destructive_schedule'] == gap['one_compute_peak_field_values'] - gap['counted_arithmetic_slots'],
               {
                   'one_compute_peak_field_values': '> counted_arithmetic_slots',
                   'non_destructive_recompute_minimum_peak_field_values': '> counted_arithmetic_slots',
                   'additional_field_slots_needed_without_recompute_or_destructive_schedule': 'difference',
               },
               gap),
    ]
    return _summarize_checks(checks)


def build_tail_macro_reversibility_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    artifact = artifacts['tail_macro_reversibility']
    expected = build_tail_macro_reversibility()
    full_domain = artifact['full_raw_field_domain']
    canonical_domain = artifact['canonical_subgroup_domain']
    projective_domain = artifact['all_projective_representatives_domain']
    reachable_domain = artifact['fixed_lookup_reachable_orbit_domain']
    boundary_domain = artifact['canonical_boundary_translation_domain']
    expected_boundary_categories = ('ordinary', 'doubling', 'inverse', 'accumulator_infinity', 'lookup_infinity')
    checks = [
        _check('tail_macro_reversibility_matches_generator', artifact == expected, expected, artifact),
        _check('tail_macro_reversibility_schema_is_current', artifact['schema'] == 'compiler-project-tail-macro-reversibility-v1', 'compiler-project-tail-macro-reversibility-v1', artifact['schema']),
        _check('tail_macro_reversibility_tracks_current_macro_opcode', artifact['opcode'] == 'complete_a0_all_streamed_tail', 'complete_a0_all_streamed_tail', artifact['opcode']),
        _check('tail_macro_full_raw_domain_is_not_injective', full_domain['injective'] is False and full_domain['collision'] is not None, {'injective': False, 'collision': 'present'}, full_domain),
        _check('tail_macro_canonical_subgroup_rows_are_injective', canonical_domain['all_checked_rows_injective'] is True and all(row['injective'] is True for row in canonical_domain['rows']), 'all rows injective', canonical_domain),
        _check('tail_macro_all_projective_representatives_are_not_injective', projective_domain['all_checked_rows_injective'] is False and all(row['injective'] is False and row['collision'] is not None for row in projective_domain['rows']), 'all rows non-injective with collision', projective_domain),
        _check('tail_macro_fixed_lookup_reachable_orbits_are_injective', reachable_domain['all_checked_rows_injective'] is True and reachable_domain['all_checked_rows_return_to_projective_infinity'] is True, {'injective': True, 'returns_to_projective_infinity': True}, reachable_domain),
        _check('tail_macro_canonical_boundary_translation_is_semantic', boundary_domain['all_checked_rows_semantic'] is True and all(row['semantic_pass'] is True for row in boundary_domain['rows']), 'all rows semantic', boundary_domain),
        _check('tail_macro_canonical_boundary_translation_is_injective_per_lookup', boundary_domain['all_checked_rows_injective_for_each_lookup'] is True and all(row['injective_for_each_lookup'] is True for row in boundary_domain['rows']), 'all fixed lookup translations injective', boundary_domain),
        _check('tail_macro_canonical_boundary_translation_covers_edge_cases', all(boundary_domain['category_totals'][category] > 0 for category in expected_boundary_categories), {category: '> 0' for category in expected_boundary_categories}, boundary_domain['category_totals']),
    ]
    return _summarize_checks(checks)


def build_tail_macro_schedule_search_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    artifact = artifacts['tail_macro_schedule_search']
    expected = build_tail_macro_schedule_search(
        counted_arithmetic_slots=len(artifacts['streamed_lookup_tail_leaf']['arithmetic_slots']),
    )
    checks = [
        _check('tail_macro_schedule_search_matches_generator', artifact == expected, expected, artifact),
        _check('tail_macro_schedule_search_schema_is_current', artifact['schema'] == 'compiler-project-tail-macro-schedule-search-v1', 'compiler-project-tail-macro-schedule-search-v1', artifact['schema']),
        _check('tail_macro_schedule_search_tracks_current_macro_opcode', artifact['opcode'] == 'complete_a0_all_streamed_tail', 'complete_a0_all_streamed_tail', artifact['opcode']),
        _check('tail_macro_schedule_search_uses_streamed_leaf_slot_budget', artifact['field_value_budget'] == len(artifacts['streamed_lookup_tail_leaf']['arithmetic_slots']), len(artifacts['streamed_lookup_tail_leaf']['arithmetic_slots']), artifact['field_value_budget']),
        _check('tail_macro_schedule_search_exhausts_three_slot_formula_dag_without_solution', artifact['all_checked_curves_exhausted_without_solution'] is True and artifact['any_checked_curve_has_solution'] is False and all(row['solution_found'] is False for row in artifact['rows']), {'all_checked_curves_exhausted_without_solution': True, 'any_checked_curve_has_solution': False}, artifact),
    ]
    return _summarize_checks(checks)


def build_standard_qrom_lookup_assessment_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    assessment = artifacts['standard_qrom_lookup_assessment']
    expected = standard_qrom_lookup_assessment(
        frontier=artifacts['family_frontier'],
        lookup_lowerings=artifacts['lookup_lowerings'],
        streamed_resource=artifacts['streamed_lookup_table_multiplier_resource'],
    )
    gap = assessment['standard_qrom_gap']
    current = assessment['current_boundary_lookup_model']
    implications = assessment['conservative_implications']
    expected_full_table_qrom_compute = int(current['positive_domain_size']) - 1
    checks = [
        _check('standard_qrom_lookup_assessment_matches_generator', assessment == expected, expected, assessment),
        _check('standard_qrom_lookup_assessment_schema_is_current', assessment['schema'] == 'compiler-project-standard-qrom-lookup-assessment-v2', 'compiler-project-standard-qrom-lookup-assessment-v2', assessment['schema']),
        _check('standard_qrom_lookup_assessment_status_is_proven', assessment['status'] == 'standard_qrom_primitive_circuit_proven_for_counted_family_with_counted_workspace', 'standard_qrom_primitive_circuit_proven_for_counted_family_with_counted_workspace', assessment['status']),
        _check('standard_qrom_lookup_assessment_uses_full_selection_space', gap['standard_unary_qrom_compute_toffoli_for_full_table'] == expected_full_table_qrom_compute, expected_full_table_qrom_compute, gap['standard_unary_qrom_compute_toffoli_for_full_table']),
        _check('standard_qrom_lookup_assessment_accepts_standard_qroam_stream', gap['standard_qrom_equivalent'] is True and gap['standard_qroam_coordinate_stream_toffoli'] == current['standard_qroam_coordinate_stream_non_clifford'] and gap['standard_qroam_coordinate_stream_target_plus_junk_qubits'] == current['standard_qroam_target_plus_junk_qubits'], {'standard_qrom_equivalent': True, 'standard_qroam_coordinate_stream_toffoli': current['standard_qroam_coordinate_stream_non_clifford'], 'standard_qroam_coordinate_stream_target_plus_junk_qubits': current['standard_qroam_target_plus_junk_qubits']}, {'standard_qrom_equivalent': gap['standard_qrom_equivalent'], 'standard_qroam_coordinate_stream_toffoli': gap['standard_qroam_coordinate_stream_toffoli'], 'standard_qroam_coordinate_stream_target_plus_junk_qubits': gap['standard_qroam_coordinate_stream_target_plus_junk_qubits']}),
        _check('standard_qrom_lookup_assessment_has_no_streaming_gap', gap['current_streamed_bit_toffoli_shortfall'] == 0 and gap['current_compute_toffoli_shortfall'] == 0 and gap['current_qroam_workspace_shortfall'] == 0, {'current_streamed_bit_toffoli_shortfall': 0, 'current_compute_toffoli_shortfall': 0, 'current_qroam_workspace_shortfall': 0}, {'current_streamed_bit_toffoli_shortfall': gap['current_streamed_bit_toffoli_shortfall'], 'current_compute_toffoli_shortfall': gap['current_compute_toffoli_shortfall'], 'current_qroam_workspace_shortfall': gap['current_qroam_workspace_shortfall']}),
        _check('standard_qrom_lookup_assessment_boundary_under_1600', implications['boundary_model_logical_qubits'] < 1600, '< 1600', implications['boundary_model_logical_qubits']),
    ]
    return _summarize_checks(checks)


def build_logical_resource_ledger_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    ledger = artifacts['logical_resource_ledger']
    expected = build_logical_resource_ledger(
        frontier=artifacts['family_frontier'],
        generated_block_inventories=artifacts['generated_block_inventories'],
        streamed_lookup_resource=artifacts['streamed_lookup_table_multiplier_resource'],
        field_bits=FIELD_BITS,
        public_google_baseline=PUBLIC_GOOGLE_BASELINE,
    )
    selected = artifacts['family_frontier']['best_qubit_family']
    model = artifacts['streamed_lookup_table_multiplier_resource']['streamed_data_selection_model']
    workspace = artifacts['streamed_lookup_table_multiplier_resource']['workspace_contract']
    qroam_cost = qroam_clean_stream_cost(
        int(model['folded_coordinate_domain_size']),
        int(model['qroam_target_bitsize']),
        int(model['qroam_block_size']),
    )
    owner_total = sum(int(owner['logical_qubits']) for owner in ledger['peak_live_qubit_owners'])
    owner_capacity_failures = [
        owner for owner in ledger['peak_live_qubit_owners']
        if int(owner['logical_qubits']) != int(owner['decomposition_total'])
    ]
    selected_row = ledger['qroam_clean_tradeoff_sweep']['selected_row']
    rows = ledger['qroam_clean_tradeoff_sweep']['rows']
    rows_under_24m_and_1700 = [
        row for row in rows
        if bool(row['under_24m_non_clifford']) and bool(row['under_1700_logical_qubits'])
    ]
    checks = [
        _check('logical_resource_ledger_matches_generator', ledger == expected, expected, ledger),
        _check('logical_resource_ledger_schema_is_current', ledger['schema'] == 'compiler-project-logical-resource-ledger-v1', 'compiler-project-logical-resource-ledger-v1', ledger['schema']),
        _check('logical_resource_ledger_passes_internal_checks', ledger['pass'] is True and all(ledger['checks'].values()), True, ledger['checks']),
        _check('logical_resource_ledger_owner_sum_matches_frontier', owner_total == int(selected['total_logical_qubits']) == int(ledger['peak_live_qubit_total_from_owners']), int(selected['total_logical_qubits']), {'owner_total': owner_total, 'ledger_total': ledger['peak_live_qubit_total_from_owners']}),
        _check('logical_resource_ledger_owner_capacity_is_numeric', not owner_capacity_failures, [], owner_capacity_failures),
        _check('logical_resource_ledger_selected_qroam_cost_matches_streamed_resource', int(qroam_cost['per_stream_non_clifford']) == int(model['per_kernel_non_clifford']) and int(qroam_cost['target_plus_junk_qubits']) == int(workspace['qroam_clean_target_plus_junk_qubits']), {'per_stream_non_clifford': model['per_kernel_non_clifford'], 'target_plus_junk_qubits': workspace['qroam_clean_target_plus_junk_qubits']}, qroam_cost),
        _check('logical_resource_ledger_selected_tradeoff_matches_frontier', int(selected_row['full_oracle_non_clifford']) == int(selected['full_oracle_non_clifford']) and int(selected_row['total_logical_qubits']) == int(selected['total_logical_qubits']), selected, selected_row),
        _check('logical_resource_ledger_current_standard_qroam_is_low_workspace_k1', int(selected_row['block_size']) == 1 and int(selected_row['target_plus_junk_qubits']) == FIELD_BITS, {'block_size': 1, 'target_plus_junk_qubits': FIELD_BITS}, selected_row),
        _check('logical_resource_ledger_proves_no_24m_1700_tradeoff_in_current_qroamclean_sweep', not rows_under_24m_and_1700 and not ledger['qroam_clean_tradeoff_sweep']['rows_under_24m_and_1700'], [], rows_under_24m_and_1700),
    ]
    return _summarize_checks(checks)


def build_fallback_frontier_stress_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    stress = artifacts['fallback_frontier_stress']
    public_policy = artifacts['compiler_parameters']['public_headline_policy']
    non_clifford_limit = int(public_policy['non_clifford_limit_exclusive'])
    qubit_limit = int(public_policy['logical_qubit_limit_exclusive'])
    expected = build_fallback_frontier_stress(
        frontier=artifacts['family_frontier'],
        logical_resource_ledger=artifacts['logical_resource_ledger'],
        field_bits=FIELD_BITS,
    )
    chunked = stress['chunked_coordinate_qroam_counterfactual']
    reusable = stress['reusable_chunked_coordinate_candidate']
    pressure = stress['four_slot_pressure']
    checks = [
        _check('fallback_frontier_stress_matches_generator', stress == expected, expected, stress),
        _check('fallback_frontier_stress_schema_is_current', stress['schema'] == 'compiler-project-fallback-frontier-stress-v1', 'compiler-project-fallback-frontier-stress-v1', stress['schema']),
        _check('fallback_frontier_stress_uses_compiler_parameter_limits', stress['limits'] == {'non_clifford_limit': non_clifford_limit, 'logical_qubit_limit_exclusive': qubit_limit}, public_policy, stress['limits']),
        _check('fallback_frontier_stress_shows_four_full_coordinate_slots_miss_qubit_limit', pressure['current_four_slot_total_with_full_coordinate_qroam'] >= qubit_limit and pressure['lookup_workspace_reduction_needed_from_current'] > 0, {'four_slot_total': f'>= {qubit_limit}', 'workspace_reduction_needed': '> 0'}, pressure),
        _check('fallback_frontier_stress_chunked_four_slot_counterfactual_misses_40m', chunked['chunked_total_logical_qubits'] < qubit_limit and chunked['chunked_total_non_clifford'] >= non_clifford_limit and chunked['required_non_qroam_base_reduction_to_fit_limit'] > 0, {'chunked_total_logical_qubits': f'< {qubit_limit}', 'chunked_total_non_clifford': f'>= {non_clifford_limit}', 'required_non_qroam_base_reduction_to_fit_limit': '> 0'}, chunked),
        _check('fallback_frontier_stress_reusable_chunk_headline_fits_limits', reusable['status'] == 'proven_public_headline' and reusable['beats_requested_non_clifford_limit'] is True and reusable['beats_requested_logical_qubit_limit'] is True and reusable['candidate_total_non_clifford'] < non_clifford_limit and reusable['candidate_total_logical_qubits'] < qubit_limit and len(reusable['public_claim_evidence']) >= 4, {'status': 'proven_public_headline', 'candidate_total_non_clifford': f'< {non_clifford_limit}', 'candidate_total_logical_qubits': f'< {qubit_limit}', 'public_claim_evidence': '>= 4'}, reusable),
        _check('fallback_frontier_stress_conclusion_has_no_current_four_slot_fallback', stress['conclusion']['current_models_have_no_four_slot_fallback_under_limits'] is True, True, stress['conclusion']),
    ]
    return _summarize_checks(checks)


def build_reusable_chunk_tail_candidate_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    candidate = artifacts['reusable_chunk_tail_candidate']
    expected = build_reusable_chunk_tail_candidate(
        fallback_frontier_stress=artifacts['fallback_frontier_stress'],
    )
    semantic = candidate['toy_semantic_equivalence']
    production = candidate['production_resource_candidate']
    public_policy = artifacts['compiler_parameters']['public_headline_policy']
    checks = [
        _check('reusable_chunk_tail_candidate_matches_generator', candidate == expected, expected, candidate),
        _check('reusable_chunk_tail_candidate_schema_is_current', candidate['schema'] == 'compiler-project-reusable-chunk-tail-candidate-v1', 'compiler-project-reusable-chunk-tail-candidate-v1', candidate['schema']),
        _check('reusable_chunk_tail_candidate_is_public_headline', candidate['status'] == 'proven_public_headline', 'proven_public_headline', candidate['status']),
        _check('reusable_chunk_tail_candidate_toy_semantics_pass_all_boundary_pairs', semantic['all_rows_semantic'] is True and semantic['all_rows_executable'] is True and semantic['total_boundary_pairs'] == 110692 and all(row['semantic_pass'] is True and row['executable_pass'] is True for row in semantic['rows']), {'all_rows_semantic': True, 'all_rows_executable': True, 'total_boundary_pairs': 110692}, semantic),
        _check('reusable_chunk_tail_candidate_executes_qchunk_scratch_contract', semantic['all_rows_scratch_trace'] is True and semantic['scratch_trace_checked'] == semantic['total_boundary_pairs'] - semantic['category_totals']['lookup_infinity'] and candidate['scratch_execution_contract']['scratch_register'] == 'qchunk' and candidate['scratch_execution_contract']['final_scratch_value'] == 0 and all(row['scratch_trace_pass'] is True and row['scratch_trace_checked'] == row['total_boundary_pairs'] - row['category_totals']['lookup_infinity'] for row in semantic['rows']), {'all_rows_scratch_trace': True, 'scratch_trace_checked': semantic['total_boundary_pairs'] - semantic['category_totals']['lookup_infinity'], 'scratch_register': 'qchunk', 'final_scratch_value': 0}, {'scratch_execution_contract': candidate['scratch_execution_contract'], 'scratch_trace_checked': semantic['scratch_trace_checked'], 'row_passes': [row['scratch_trace_pass'] for row in semantic['rows']]}),
        _check('reusable_chunk_tail_candidate_covers_edge_categories', all(semantic['category_totals'][category] > 0 for category in ('ordinary', 'doubling', 'inverse', 'accumulator_infinity', 'lookup_infinity')), 'all edge categories > 0', semantic['category_totals']),
        _check('reusable_chunk_tail_candidate_resource_numbers_match_stress_candidate', production['candidate_total_non_clifford'] == artifacts['fallback_frontier_stress']['reusable_chunked_coordinate_candidate']['candidate_total_non_clifford'] and production['candidate_total_logical_qubits'] == artifacts['fallback_frontier_stress']['reusable_chunked_coordinate_candidate']['candidate_total_logical_qubits'], artifacts['fallback_frontier_stress']['reusable_chunked_coordinate_candidate'], production),
        _check('reusable_chunk_tail_candidate_fits_requested_limits_if_proven', production['beats_requested_non_clifford_limit'] is True and production['beats_requested_logical_qubit_limit'] is True and production['candidate_total_non_clifford'] < public_policy['non_clifford_limit_exclusive'] and production['candidate_total_logical_qubits'] < public_policy['logical_qubit_limit_exclusive'], public_policy, production),
        _check('reusable_chunk_tail_candidate_records_public_claim_evidence', len(candidate['public_claim_evidence']) >= 4, '>= 4', candidate['public_claim_evidence']),
    ]
    return _summarize_checks(checks)


def build_qroam_primitive_certificate_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    certificate = artifacts['qroam_primitive_certificate']
    selected_row = artifacts['logical_resource_ledger']['qroam_clean_tradeoff_sweep']['selected_row']
    target_bits = int(
        artifacts['fallback_frontier_stress']['chunked_coordinate_qroam_counterfactual'][
            'max_qroam_target_bits_per_live_chunk'
        ]
    )
    expected = build_qroam_k1_primitive_certificate(
        domain_size=int(selected_row['domain_size']),
        target_bits=target_bits,
        block_size=1,
    )
    parameters = certificate['parameters']
    traversed = certificate['traversed_counts']
    qroam_cost = qroam_clean_stream_cost(
        int(parameters['domain_size']),
        int(parameters['target_bits']),
        int(parameters['block_size']),
    )
    segments = certificate['operation_stream']['segments']
    compute_segments = [row for row in segments if row['phase'] == 'compute']
    cleanup_segments = [row for row in segments if row['phase'] == 'measured_uncompute']
    compute_ccx = sum(int(row['ccx']) for row in compute_segments)
    cleanup_ccx = sum(int(row['ccx']) for row in cleanup_segments)
    operation_stream = certificate['operation_stream']
    target_bit_load_site_stream = certificate['target_bit_load_site_stream']
    preview_rows = operation_stream['preview_head'] + operation_stream['preview_tail']
    target_bit_preview_rows = target_bit_load_site_stream['preview_head'] + target_bit_load_site_stream['preview_tail']
    expected_selection_bits = int(certificate['wire_catalog']['selection_register']['qubits'])
    stream_binds_word_level_contract = (
        operation_stream['operation_schema'] == 'qroamclean-k1-unary-iteration-word-step-v1'
        and operation_stream['operation_level'] == 'word_level_unary_iteration_rows'
        and int(operation_stream['selection_bit_count']) == expected_selection_bits
        and int(operation_stream['target_register_qubits']) == target_bits
        and all(
            int(row['selection_bit_count']) == expected_selection_bits
            and int(row['target_register_qubits']) == target_bits
            for row in segments
        )
    )
    preview_rows_bind_word_sources = (
        len(preview_rows) >= 4
        and all(
            len(row['selection_control_wires']) == expected_selection_bits
            and len(row['selection_control_pattern_lsb_first']) == expected_selection_bits
            and row['target_register']['bit_count'] == target_bits
            and row['loaded_word_source']['bit_range'] == [0, target_bits]
            and row['loaded_word_source']['table_address'] == row['address']
            for row in preview_rows
        )
    )
    target_bit_load_sites_bind_target_width = (
        target_bit_load_site_stream['operation_schema'] == 'qroamclean-k1-target-bit-load-site-v1'
        and target_bit_load_site_stream['operation_level'] == 'target_bit_clifford_load_sites'
        and int(target_bit_load_site_stream['target_register_qubits']) == target_bits
        and int(target_bit_load_site_stream['potential_cnot_site_count']) == (compute_ccx + cleanup_ccx) * target_bits
        and all(
            int(row['target_bit_count']) == target_bits
            and int(row['potential_cnot_site_count']) == (
                int(row['end_address_exclusive']) - int(row['start_address'])
            ) * target_bits
            for row in target_bit_load_site_stream['segments']
        )
    )
    target_bit_preview_rows_bind_sources = (
        len(target_bit_preview_rows) >= 6
        and all(
            row['target_wire'] == f"qroam_target.bit[{int(row['target_bit_index'])}]"
            and row['loaded_bit_source']['table_address'] == row['address']
            and row['loaded_bit_source']['bit_index'] == row['target_bit_index']
            and 0 <= int(row['target_bit_index']) < target_bits
            for row in target_bit_preview_rows
        )
    )
    checks = [
        _check('qroam_primitive_certificate_matches_generator', certificate == expected, expected, certificate),
        _check('qroam_primitive_certificate_schema_is_current', certificate['schema'] == 'compiler-project-qroam-k1-primitive-certificate-v1', 'compiler-project-qroam-k1-primitive-certificate-v1', certificate['schema']),
        _check('qroam_primitive_certificate_passes_internal_checks', certificate['pass'] is True and all(certificate['checks'].values()), True, certificate['checks']),
        _check('qroam_primitive_certificate_uses_public_k1_stream_parameters', int(parameters['domain_size']) == int(selected_row['domain_size']) and int(parameters['target_bits']) == target_bits and int(parameters['block_size']) == 1, {'domain_size': selected_row['domain_size'], 'target_bits': target_bits, 'block_size': 1}, parameters),
        _check('qroam_primitive_certificate_traverses_compute_and_cleanup_domains', compute_ccx == cleanup_ccx == int(parameters['domain_size']) and len(compute_segments) == len(cleanup_segments) and len(segments) == int(certificate['operation_stream']['segment_count']), {'compute_ccx': parameters['domain_size'], 'cleanup_ccx': parameters['domain_size']}, {'compute_ccx': compute_ccx, 'cleanup_ccx': cleanup_ccx, 'segment_count': len(segments)}),
        _check('qroam_primitive_certificate_segments_bind_word_level_wire_contract', stream_binds_word_level_contract, {'operation_schema': 'qroamclean-k1-unary-iteration-word-step-v1', 'selection_bit_count': expected_selection_bits, 'target_register_qubits': target_bits}, operation_stream),
        _check('qroam_primitive_certificate_preview_rows_bind_selection_patterns_and_target_range', preview_rows_bind_word_sources, 'preview rows bind selection controls, address patterns, target width, and loaded word range', preview_rows),
        _check('qroam_primitive_certificate_target_bit_load_sites_bind_target_width', target_bit_load_sites_bind_target_width, {'operation_schema': 'qroamclean-k1-target-bit-load-site-v1', 'potential_cnot_site_count': (compute_ccx + cleanup_ccx) * target_bits}, target_bit_load_site_stream),
        _check('qroam_primitive_certificate_target_bit_preview_rows_bind_sources', target_bit_preview_rows_bind_sources, 'target-bit preview rows bind target wire and loaded bit source', target_bit_preview_rows),
        _check('qroam_primitive_certificate_counts_match_qroamclean_cost_model', int(traversed['lookup_compute_non_clifford']) == int(qroam_cost['lookup_compute_non_clifford']) and int(traversed['measured_uncompute_non_clifford']) == int(qroam_cost['measured_uncompute_non_clifford']) and int(traversed['per_stream_non_clifford']) == int(qroam_cost['per_stream_non_clifford']) and int(traversed['target_plus_junk_qubits']) == int(qroam_cost['target_plus_junk_qubits']), qroam_cost, traversed),
        _check('qroam_primitive_certificate_workspace_decomposes_target_and_junk', int(certificate['wire_catalog']['target_register']['qubits']) == int(parameters['target_bits']) and int(certificate['wire_catalog']['junk_registers']['qubits']) == 0 and int(traversed['target_plus_junk_qubits']) == int(parameters['target_bits']), {'target_register_qubits': parameters['target_bits'], 'junk_register_qubits': 0}, certificate['wire_catalog']),
    ]
    return _summarize_checks(checks)


def build_qroam_reference_crosscheck_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    crosscheck = artifacts['qroam_reference_crosscheck']
    expected = build_qroam_reference_crosscheck(
        qroam_primitive_certificate=artifacts['qroam_primitive_certificate'],
        logical_resource_ledger=artifacts['logical_resource_ledger'],
    )
    selected = crosscheck['selected_reference']
    ledger_selected = crosscheck['ledger_selected_reference']
    primitive = artifacts['qroam_primitive_certificate']['traversed_counts']
    selected_row = artifacts['logical_resource_ledger']['qroam_clean_tradeoff_sweep']['selected_row']
    checks = [
        _check('qroam_reference_crosscheck_matches_generator', crosscheck == expected, expected, crosscheck),
        _check('qroam_reference_crosscheck_schema_is_current', crosscheck['schema'] == QROAM_REFERENCE_CROSSCHECK_SCHEMA, QROAM_REFERENCE_CROSSCHECK_SCHEMA, crosscheck['schema']),
        _check('qroam_reference_crosscheck_passes_internal_checks', crosscheck['pass'] is True and all(crosscheck['checks'].values()), True, crosscheck['checks']),
        _check('qroam_reference_crosscheck_selected_matches_primitive_certificate', selected['per_stream_non_clifford'] == primitive['per_stream_non_clifford'] and selected['target_plus_junk_qubits'] == primitive['target_plus_junk_qubits'], primitive, selected),
        _check('qroam_reference_crosscheck_ledger_selected_matches_resource_ledger', ledger_selected['block_size'] == selected_row['block_size'] and ledger_selected['per_stream_non_clifford'] == selected_row['per_stream_non_clifford'] and ledger_selected['target_plus_junk_qubits'] == selected_row['target_plus_junk_qubits'], selected_row, ledger_selected),
        _check('qroam_reference_crosscheck_chunk_reference_keeps_width_boundary_explicit', selected['block_size'] == selected_row['block_size'] and selected['domain_size'] == selected_row['domain_size'] and selected['per_stream_non_clifford'] == selected_row['per_stream_non_clifford'] and selected['target_bits'] <= selected_row['target_register_qubits'], selected_row, selected),
        _check('qroam_reference_crosscheck_toy_semantics_are_exhaustive', all(row['pass'] is True and len(row['rows']) == row['domain_size'] for row in crosscheck['toy_semantics']), 'all toy selections pass', crosscheck['toy_semantics']),
    ]
    return _summarize_checks(checks)


def build_qroam_table_cnot_materialization_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    materialization = artifacts['qroam_table_cnot_materialization']
    expected = build_qroam_table_cnot_materialization(
        table_manifests=artifacts['table_manifests'],
        raw32_schedule=raw32_schedule(),
        reusable_chunk_lowering=artifacts['reusable_chunk_lowering'],
        qroam_primitive_certificate=artifacts['qroam_primitive_certificate'],
        field_bits=FIELD_BITS,
    )
    stream_plan = artifacts['reusable_chunk_lowering']['stream_plan']
    qroam_site_stream = artifacts['qroam_primitive_certificate']['target_bit_load_site_stream']
    totals = materialization['totals']
    parameters = materialization['parameters']
    checks = [
        _check('qroam_table_cnot_materialization_matches_generator', materialization == expected, expected, materialization),
        _check('qroam_table_cnot_materialization_schema_is_current', materialization['schema'] == QROAM_TABLE_CNOT_MATERIALIZATION_SCHEMA, QROAM_TABLE_CNOT_MATERIALIZATION_SCHEMA, materialization['schema']),
        _check('qroam_table_cnot_materialization_passes_internal_checks', materialization['pass'] is True and all(materialization['checks'].values()), True, materialization['checks']),
        _check('qroam_table_cnot_materialization_uses_checked_raw32_shape', int(parameters['leaf_call_count']) == int(stream_plan['leaf_call_count_total']) and int(totals['chunk_stream_count']) == int(stream_plan['whole_oracle_chunk_streams']), {'leaf_call_count': stream_plan['leaf_call_count_total'], 'chunk_stream_count': stream_plan['whole_oracle_chunk_streams']}, {'parameters': parameters, 'totals': totals}),
        _check('qroam_table_cnot_materialization_covers_target_bit_site_stream', int(totals['full_oracle_potential_target_bit_sites']) == int(stream_plan['whole_oracle_chunk_streams']) * int(qroam_site_stream['potential_cnot_site_count']), 'every potential target-bit site across every stream is classified', totals),
        _check('qroam_table_cnot_materialization_emits_only_effective_nonzero_table_bits', 0 <= int(totals['full_oracle_emitted_clifford_cx']) <= int(totals['full_oracle_effective_target_bit_sites']) <= int(totals['full_oracle_potential_target_bit_sites']), 'emitted CNOTs are a subset of effective non-padding target-bit sites', totals),
        _check('qroam_table_cnot_materialization_segments_have_merkle_root', len(materialization['segment_merkle_root_sha256']) == 64 and int(totals['segment_count']) == len(materialization['segments']), 'segment merkle root binds all concrete table chunks', {'segment_count': len(materialization['segments']), 'root': materialization['segment_merkle_root_sha256']}),
        _check('qroam_table_cnot_materialization_ranges_cover_emitted_cx_stream', materialization['checks']['emitted_cx_operation_ranges_cover_total'] is True and materialization['segments'][0]['emitted_cx_operation_start'] == 0 and materialization['segments'][-1]['emitted_cx_operation_end_exclusive'] == totals['full_oracle_emitted_clifford_cx'], 'global emitted-CNOT ranges cover the full emitted stream', {'first': materialization['segments'][0], 'last': materialization['segments'][-1]}),
        _check('qroam_table_cnot_materialization_probes_bind_set_target_bits', materialization['checks']['emitted_cx_probes_are_within_effective_target_bits'] is True and any(segment['first_emitted_cx'] is not None for segment in materialization['segments']), 'first/last emitted-CNOT probes are set target bits inside each segment range', materialization['segments'][:4]),
        _check('qroam_table_cnot_materialization_has_rank_checkpoint_index', materialization['checks']['rank_checkpoints_cover_every_segment'] is True and int(totals['rank_checkpoint_count']) > int(totals['segment_count']) and len(materialization['row_index_contract_merkle_root_sha256']) == 64, 'rank checkpoints index the emitted-CNOT stream for every segment', {'rank_checkpoint_count': totals['rank_checkpoint_count'], 'root': materialization['row_index_contract_merkle_root_sha256']}),
        _check('qroam_table_cnot_materialization_has_executable_row_decoder_samples', materialization['checks']['row_decoder_samples_are_exact_table_cnot_rows'] is True and int(totals['row_decoder_sample_count']) > 0 and len(materialization['row_decoder_sample_merkle_root_sha256']) == 64, 'decoder samples bind concrete per-CNOT row reconstruction', {'row_decoder_sample_count': totals['row_decoder_sample_count'], 'root': materialization['row_decoder_sample_merkle_root_sha256']}),
    ]
    return _summarize_checks(checks)


def build_reusable_chunk_lowering_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    lowering = artifacts['reusable_chunk_lowering']
    expected = build_reusable_chunk_lowering(
        reusable_chunk_tail_candidate=artifacts['reusable_chunk_tail_candidate'],
        fallback_frontier_stress=artifacts['fallback_frontier_stress'],
        logical_resource_ledger=artifacts['logical_resource_ledger'],
        arithmetic_lowerings=artifacts['arithmetic_lowerings'],
        qroam_primitive_certificate=artifacts['qroam_primitive_certificate'],
        qroam_reference_crosscheck=artifacts['qroam_reference_crosscheck'],
        modular_arithmetic_certificate=artifacts['modular_arithmetic_certificate'],
        field_bits=FIELD_BITS,
    )
    stream_plan = lowering['stream_plan']
    qubits = lowering['qubit_derivation']
    non_clifford = lowering['non_clifford_derivation']
    owners = lowering['owner_capacity']
    executable_liveness = lowering['executable_liveness']
    executable_schedule = executable_liveness['executable_schedule_ir']
    executable_contract = lowering['executable_contract']
    counted_resource_ir = lowering['counted_resource_ir']
    counted_resource_engine = lowering['counted_resource_engine']
    resource_contract_engine = lowering['resource_contract_engine']
    executable_resource_engine = lowering['executable_resource_engine']
    source_instruction_ops = {
        int(instruction['pc']): str(instruction['op'])
        for instruction in executable_contract['instruction_stream']
    }
    qroam_model = lowering['standard_qroamclean_k1_model']
    primitive_contract = lowering['chunked_multiplier_primitive_contract']
    expected_stream_count = (
        stream_plan['leaf_call_count_total']
        * stream_plan['coordinate_table_count']
        * stream_plan['chunk_count']
    )
    expected_chunk_effective_bits = [
        max(0, min(stream_plan['chunk_bits'], FIELD_BITS - stream_plan['chunk_bits'] * index))
        for index in range(stream_plan['chunk_count'])
    ]
    expected_qroam_non_clifford = (
        non_clifford['qroam_chunk_streams']
        * non_clifford['per_chunk_stream_non_clifford']
    )
    expected_arithmetic_qubits = qubits['arithmetic_slot_count'] * qubits['field_bits']
    expected_lookup_workspace_qubits = (
        qubits['folded_control_workspace_qubits']
        + qubits['qroam_clean_chunk_target_qubits']
        + qubits['qroam_clean_junk_register_qubits']
    )
    checks = [
        _check('reusable_chunk_lowering_matches_generator', lowering == expected, expected, lowering),
        _check('reusable_chunk_lowering_schema_is_current', lowering['schema'] == 'compiler-project-reusable-chunk-lowering-v2', 'compiler-project-reusable-chunk-lowering-v2', lowering['schema']),
        _check('reusable_chunk_lowering_is_public_headline', lowering['status'] == 'proven_public_headline', 'proven_public_headline', lowering['status']),
        _check('reusable_chunk_lowering_passes_internal_checks', lowering['pass'] is True and all(lowering['checks'].values()), True, lowering['checks']),
        _check('reusable_chunk_lowering_derives_stream_count_from_contract', stream_plan['coordinate_table_count'] == len(stream_plan['coordinate_tables']) and stream_plan['chunk_streams_per_leaf'] == stream_plan['coordinate_table_count'] * stream_plan['chunk_count'] and stream_plan['whole_oracle_chunk_streams'] == expected_stream_count, {'whole_oracle_chunk_streams': expected_stream_count}, stream_plan),
        _check('reusable_chunk_lowering_uses_standard_qroamclean_k1_consistently', qroam_model['block_size'] == 1 and qroam_model['target_register_qubits'] == stream_plan['chunk_bits'] and qroam_model['junk_register_qubits'] == 0 and qroam_model['per_stream_non_clifford'] == qroam_model['lookup_compute_non_clifford'] + qroam_model['measured_uncompute_non_clifford'], {'target_register_qubits': stream_plan['chunk_bits'], 'junk_register_qubits': 0, 'per_stream_non_clifford': qroam_model['lookup_compute_non_clifford'] + qroam_model['measured_uncompute_non_clifford']}, qroam_model),
        _check('reusable_chunk_lowering_binds_generated_qroam_primitive_certificate', lowering['qroam_primitive_certificate'] == artifacts['qroam_primitive_certificate'] and lowering['checks']['per_stream_cost_matches_generated_qroam_primitive'] is True, artifacts['qroam_primitive_certificate'], lowering['qroam_primitive_certificate']),
        _check('reusable_chunk_lowering_binds_independent_qroam_reference_crosscheck', lowering['qroam_reference_crosscheck'] == artifacts['qroam_reference_crosscheck'] and lowering['checks']['per_stream_cost_matches_independent_qroam_reference_crosscheck'] is True, artifacts['qroam_reference_crosscheck'], lowering['qroam_reference_crosscheck']),
        _check('reusable_chunk_lowering_binds_modular_arithmetic_certificate', lowering['modular_arithmetic_certificate'] == artifacts['modular_arithmetic_certificate'] and lowering['checks']['modular_arithmetic_certificate_binds_counted_field_mul'] is True, artifacts['modular_arithmetic_certificate'], lowering['modular_arithmetic_certificate']),
        _check('reusable_chunk_lowering_materializes_no_full_coordinate_lane', all(row['full_coordinate_lane_materialized'] == 0 and row['live_target_qubits'] == qroam_model['target_register_qubits'] for row in stream_plan['rows']) and lowering['executable_contract']['chunk_contract']['full_coordinate_lanes_materialized'] == 0, 0, stream_plan['rows']),
        _check('reusable_chunk_lowering_binds_scratch_execution_contract', executable_contract['scratch_execution_contract'] == artifacts['reusable_chunk_tail_candidate']['scratch_execution_contract'] and lowering['checks']['executable_leaf_executes_reusable_chunk_scratch_contract'] is True, artifacts['reusable_chunk_tail_candidate']['scratch_execution_contract'], executable_contract['scratch_execution_contract']),
        _check('reusable_chunk_lowering_proves_table_multiplier_base_conservative', primitive_contract['arithmetic_base_conservatism']['inherited_base_without_streamed_qroam_is_valid_for_chunked_contract'] is True and primitive_contract['table_multiplier_partial_products_per_leaf'] == primitive_contract['inherited_table_multiplier_partial_products_per_leaf'] == sum(row['inherited_full_width_partial_product_non_clifford'] for row in primitive_contract['table_multiplier_rows']), {'table_multiplier_partial_products_per_leaf': primitive_contract['inherited_table_multiplier_partial_products_per_leaf']}, primitive_contract),
        _check('reusable_chunk_lowering_high_chunk_effective_bits_are_explicit', primitive_contract['chunk_effective_bits'] == expected_chunk_effective_bits and all([chunk['effective_constant_bits'] for chunk in row['chunk_rows']] == expected_chunk_effective_bits for row in primitive_contract['table_multiplier_rows']), {'chunk_effective_bits': expected_chunk_effective_bits}, primitive_contract),
        _check('reusable_chunk_lowering_reconstructs_non_clifford_candidate', non_clifford['qroam_chunk_streams'] == expected_stream_count and non_clifford['qroam_chunk_non_clifford'] == expected_qroam_non_clifford and non_clifford['candidate_total_non_clifford'] == artifacts['reusable_chunk_tail_candidate']['production_resource_candidate']['candidate_total_non_clifford'], {'qroam_chunk_streams': expected_stream_count, 'candidate_total_non_clifford': artifacts['reusable_chunk_tail_candidate']['production_resource_candidate']['candidate_total_non_clifford']}, non_clifford),
        _check('reusable_chunk_lowering_reconstructs_qubit_candidate', qubits['arithmetic_slot_qubits'] == expected_arithmetic_qubits and qubits['lookup_workspace_qubits'] == expected_lookup_workspace_qubits and qubits['candidate_total_logical_qubits'] == artifacts['reusable_chunk_tail_candidate']['production_resource_candidate']['candidate_total_logical_qubits'], {'arithmetic_slot_qubits': expected_arithmetic_qubits, 'lookup_workspace_qubits': expected_lookup_workspace_qubits, 'candidate_total_logical_qubits': artifacts['reusable_chunk_tail_candidate']['production_resource_candidate']['candidate_total_logical_qubits']}, qubits),
        _check('reusable_chunk_lowering_owner_capacity_is_numeric', owners['required_global_peak_qubits'] == owners['capacity_global_peak_qubits'] == qubits['candidate_total_logical_qubits'] and all(row['capacity_pass'] is True and row['logical_qubits'] >= row['required_peak_qubits'] for row in owners['rows']), {'required_global_peak_qubits': qubits['candidate_total_logical_qubits'], 'capacity_global_peak_qubits': qubits['candidate_total_logical_qubits']}, owners),
        _check('reusable_chunk_lowering_executable_schedule_ir_is_liveness_source', executable_schedule['schema'] == 'compiler-project-reusable-chunk-executable-schedule-ir-v1' and executable_schedule['pass'] is True and executable_liveness['source_schedule_schema'] == executable_schedule['schema'] and executable_liveness['source_schedule_event_count'] == executable_schedule['event_count'] == len(executable_liveness['intervals']) and executable_schedule['wire_catalog'] == executable_liveness['wire_catalog'], {'schema': 'compiler-project-reusable-chunk-executable-schedule-ir-v1', 'event_count': len(executable_liveness['intervals'])}, {'schema': executable_schedule['schema'], 'event_count': executable_schedule['event_count'], 'source_event_count': executable_liveness['source_schedule_event_count']}),
        _check('reusable_chunk_lowering_schedule_events_bind_leaf_instruction_stream', executable_schedule['source_leaf_instruction_stream'] == executable_contract['instruction_stream'] and executable_schedule['checks']['source_instruction_ops_match_leaf'] is True and all([source_instruction_ops[int(pc)] for pc in event['source_instruction_pcs']] == event['source_instruction_ops'] for event in executable_schedule['events']), 'schedule source instructions match executable contract instruction stream', {'source_leaf_instruction_stream': executable_schedule['source_leaf_instruction_stream'], 'events': executable_schedule['events']}),
        _check('reusable_chunk_lowering_liveness_intervals_derive_from_schedule_events', all(event['event_id'] == interval['interval_id'] and event['live_wire_ids'] == interval['live_wire_ids'] for event, interval in zip(executable_schedule['events'], executable_liveness['intervals'])), 'schedule event live wires equal liveness interval live wires', {'events': executable_schedule['events'], 'intervals': executable_liveness['intervals']}),
        _check('reusable_chunk_lowering_schedule_qroam_events_match_stream_rows', [(event['stream_table'], event['stream_chunk_index']) for event in executable_schedule['events'] if event['event_type'] == 'qroam_chunk_load_consume_uncompute'] == [(row['table'], row['chunk_index']) for row in stream_plan['rows']] and executable_schedule['checks']['qchunk_live_during_each_qroam_stream_event'] is True, [(row['table'], row['chunk_index']) for row in stream_plan['rows']], [(event.get('stream_table'), event.get('stream_chunk_index')) for event in executable_schedule['events'] if event['event_type'] == 'qroam_chunk_load_consume_uncompute']),
        _check('reusable_chunk_lowering_executable_liveness_reconstructs_peak', executable_liveness['pass'] is True and executable_liveness['global_peak_live_qubits'] == qubits['candidate_total_logical_qubits'] and executable_liveness['owner_peak_live_qubits'] == executable_liveness['owner_capacity_qubits'], {'global_peak_live_qubits': qubits['candidate_total_logical_qubits'], 'owner_peaks_equal_capacity': True}, executable_liveness),
        _check('reusable_chunk_lowering_executable_liveness_counts_qchunk_and_qroam_target_concurrently', executable_liveness['checks']['qroam_target_and_qchunk_are_concurrently_live'] is True and executable_liveness['checks']['no_full_coordinate_lane_wire_is_live'] is True, {'qchunk_and_qroam_target_concurrent': True, 'full_coordinate_lane_live': False}, executable_liveness['checks']),
        _check('reusable_chunk_lowering_counted_resource_ir_recomputes_public_totals', counted_resource_ir['pass'] is True and counted_resource_ir['recomputed_total_non_clifford'] == non_clifford['candidate_total_non_clifford'] and counted_resource_ir['recomputed_peak_live_qubits'] == qubits['candidate_total_logical_qubits'] and len([term for term in counted_resource_ir['non_clifford_terms'] if term['category'] == 'qroam_chunk_stream']) == len(stream_plan['rows']), {'non_clifford': non_clifford['candidate_total_non_clifford'], 'peak_live_qubits': qubits['candidate_total_logical_qubits'], 'qroam_terms': len(stream_plan['rows'])}, counted_resource_ir),
        _check('reusable_chunk_lowering_counted_resource_engine_matches_generator', counted_resource_engine == evaluate_counted_resource_ir(counted_resource_ir), evaluate_counted_resource_ir(counted_resource_ir), counted_resource_engine),
        _check('reusable_chunk_lowering_counted_resource_engine_recomputes_public_totals', counted_resource_engine['schema'] == RESOURCE_IR_ENGINE_SCHEMA and counted_resource_engine['pass'] is True and counted_resource_engine['non_clifford_total_from_terms'] == non_clifford['candidate_total_non_clifford'] and counted_resource_engine['peak_live_qubits_from_intervals'] == qubits['candidate_total_logical_qubits'], {'schema': RESOURCE_IR_ENGINE_SCHEMA, 'non_clifford': non_clifford['candidate_total_non_clifford'], 'peak_live_qubits': qubits['candidate_total_logical_qubits']}, counted_resource_engine),
        _check('reusable_chunk_lowering_resource_contract_engine_matches_generator', resource_contract_engine == evaluate_resource_contract(counted_resource_ir=counted_resource_ir, counted_resource_engine=counted_resource_engine, executable_liveness=executable_liveness, owner_capacity=owners), evaluate_resource_contract(counted_resource_ir=counted_resource_ir, counted_resource_engine=counted_resource_engine, executable_liveness=executable_liveness, owner_capacity=owners), resource_contract_engine),
        _check('reusable_chunk_lowering_resource_contract_engine_unifies_counted_and_executable_liveness', resource_contract_engine['schema'] == RESOURCE_CONTRACT_ENGINE_SCHEMA and resource_contract_engine['pass'] is True and resource_contract_engine['peak_live_qubits'] == qubits['candidate_total_logical_qubits'] and resource_contract_engine['owner_peak_live_qubits'] == resource_contract_engine['owner_capacity_qubits'], {'schema': RESOURCE_CONTRACT_ENGINE_SCHEMA, 'peak_live_qubits': qubits['candidate_total_logical_qubits'], 'owner_peaks_equal_capacity': True}, resource_contract_engine),
        _check('reusable_chunk_lowering_executable_resource_engine_is_single_entrypoint', executable_resource_engine['schema'] == 'compiler-project-executable-resource-engine-v1' and executable_resource_engine['pass'] is True and executable_resource_engine['public_totals']['non_clifford'] == non_clifford['candidate_total_non_clifford'] and executable_resource_engine['public_totals']['logical_qubits'] == qubits['candidate_total_logical_qubits'] and executable_resource_engine['counted_resource_ir_sha256'] == counted_resource_engine['counted_resource_ir_sha256'] and executable_resource_engine['executable_liveness_sha256'] == resource_contract_engine['executable_liveness_sha256'] and executable_resource_engine['owner_capacity_sha256'] == resource_contract_engine['owner_capacity_sha256'], 'single executable resource engine summary binds public totals and resource digests', executable_resource_engine),
        _check('reusable_chunk_lowering_records_zkp_and_release_evidence', len(lowering['public_claim_evidence']) >= 2, '>= 2', lowering['public_claim_evidence']),
    ]
    return _summarize_checks(checks)


def build_resource_liveness_certificate_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    certificate = artifacts['resource_liveness_certificate']
    expected = build_resource_liveness_certificate(
        frontier=artifacts['family_frontier'],
        streamed_lookup_tail_slot_allocation=artifacts['streamed_lookup_tail_leaf_slot_allocation'],
        arithmetic_lowerings=artifacts['arithmetic_lowerings'],
        arithmetic_operation_ir=artifacts['arithmetic_operation_ir'],
        streamed_lookup_resource=artifacts['streamed_lookup_table_multiplier_resource'],
        logical_resource_ledger=artifacts['logical_resource_ledger'],
        ft_ir_compositions=artifacts['ft_ir_compositions'],
        phase_shell_lowerings=artifacts['phase_shell_lowerings'],
        materialized_circuit_manifest=artifacts['materialized_circuit_manifest'],
        field_bits=FIELD_BITS,
    )
    selected = artifacts['family_frontier']['best_qubit_family']
    primitive_ir = certificate['primitive_oracle_ir']
    owner_capacity = certificate['derived_owner_capacity']
    arithmetic_operation_ir = certificate['arithmetic_operation_ir']
    checks = [
        _check('resource_liveness_certificate_matches_generator', certificate == expected, expected, certificate),
        _check('resource_liveness_certificate_schema_is_current', certificate['schema'] == 'compiler-project-resource-liveness-certificate-v3', 'compiler-project-resource-liveness-certificate-v3', certificate['schema']),
        _check('resource_liveness_certificate_passes_internal_checks', certificate['pass'] is True and all(certificate['checks'].values()), True, certificate['checks']),
        _check('resource_liveness_certificate_binds_selected_headline', certificate['selected_family'] == selected['name'] and certificate['headline_totals']['full_oracle_non_clifford'] == selected['full_oracle_non_clifford'] and certificate['headline_totals']['total_logical_qubits'] == selected['total_logical_qubits'], selected, certificate['headline_totals']),
        _check('resource_liveness_certificate_uses_versioned_materialized_manifest', artifacts['materialized_circuit_manifest']['schema'] == 'compiler-project-materialized-circuit-manifest-v1', 'compiler-project-materialized-circuit-manifest-v1', artifacts['materialized_circuit_manifest'].get('schema')),
        _check('resource_liveness_certificate_derives_peak_from_schedule_and_owners', certificate['flat_leaf_liveness']['arithmetic_slots_from_schedule'] == selected['arithmetic_slot_count'] and certificate['global_peak_live_qubits'] == selected['total_logical_qubits'], {'arithmetic_slot_count': selected['arithmetic_slot_count'], 'total_logical_qubits': selected['total_logical_qubits']}, {'arithmetic_slots_from_schedule': certificate['flat_leaf_liveness']['arithmetic_slots_from_schedule'], 'global_peak_live_qubits': certificate['global_peak_live_qubits']}),
        _check('resource_liveness_certificate_owner_capacity_rows_cover_required_peak',
               owner_capacity['required_global_peak_qubits'] == selected['total_logical_qubits']
               and owner_capacity['capacity_global_peak_qubits'] == selected['total_logical_qubits']
               and all(row['capacity_qubits'] >= row['required_peak_qubits'] for row in owner_capacity['rows']),
               {'required_global_peak_qubits': selected['total_logical_qubits'], 'capacity_global_peak_qubits': selected['total_logical_qubits']},
               owner_capacity),
        _check('resource_liveness_certificate_embeds_selected_ft_ir_leaf_sigma', primitive_ir['selected_family'] == selected['name'] and primitive_ir['source_schema'] == artifacts['ft_ir_compositions']['schema'] and primitive_ir['leaf_sigma_count'] == len(primitive_ir['leaf_sigma']), {'selected_family': selected['name'], 'source_schema': artifacts['ft_ir_compositions']['schema']}, {'selected_family': primitive_ir['selected_family'], 'source_schema': primitive_ir['source_schema'], 'leaf_sigma_count': primitive_ir['leaf_sigma_count']}),
        _check('resource_liveness_certificate_leaf_sigma_reconstructs_headline', primitive_ir['reconstruction_from_leaf_sigma']['full_oracle_non_clifford'] == selected['full_oracle_non_clifford'] and primitive_ir['reconstruction_from_leaf_sigma']['total_logical_qubits'] == selected['total_logical_qubits'], selected, primitive_ir['reconstruction_from_leaf_sigma']),
        _check('resource_liveness_certificate_binds_materialized_stream_manifest', certificate['materialized_operation_stream']['operation_stream_sha256'] == artifacts['materialized_circuit_manifest']['operation_stream_sha256'] and certificate['materialized_operation_stream']['gate_totals']['ccx'] == selected['full_oracle_non_clifford'], artifacts['materialized_circuit_manifest'], certificate['materialized_operation_stream']),
        _check('resource_liveness_certificate_binds_arithmetic_operation_ir', {key: value for key, value in arithmetic_operation_ir.items() if key != 'binding_note'} == artifacts['arithmetic_operation_ir'] and arithmetic_operation_ir['leaf_arithmetic_summary']['non_clifford_total'] == selected['arithmetic_leaf_non_clifford'], artifacts['arithmetic_operation_ir'], arithmetic_operation_ir),
        _check('resource_liveness_certificate_tail_macro_expands_into_rows', primitive_ir['tail_macro_rows']['row_count'] > 0 and primitive_ir['tail_macro_rows']['whole_oracle_non_clifford'] == primitive_ir['tail_macro_rows']['per_leaf_non_clifford'] * primitive_ir['tail_macro_rows']['leaf_call_count_total'], True, primitive_ir['tail_macro_rows']),
        _check('resource_liveness_certificate_binds_materialized_segment_tree', certificate['materialized_operation_stream']['segment_merkle_root_sha256'] == artifacts['materialized_circuit_manifest']['segment_merkle_root_sha256'] and certificate['checks']['materialized_operation_stream_segments_cover_stream'] is True, artifacts['materialized_circuit_manifest']['segment_merkle_root_sha256'], certificate['materialized_operation_stream']),
    ]
    return _summarize_checks(checks)


def build_qubit_breakthrough_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    analysis = artifacts['qubit_breakthrough_analysis']
    best_qubit = artifacts['family_frontier']['best_qubit_family']
    fixed_non_arithmetic_overhead = (
        int(best_qubit['lookup_workspace_qubits'])
        + int(best_qubit['control_slot_count'])
        + int(best_qubit.get('borrowed_interface_qubits', 0))
        + int(best_qubit['live_phase_bits'])
    )
    slot_family_name = best_qubit['slot_allocation_family']
    slot_alloc = next(
        row['slot_allocation']
        for row in artifacts['family_frontier']['slot_allocation_families']
        if row['name'] == slot_family_name
    )
    expected = build_qubit_breakthrough_analysis(
        frontier=artifacts['family_frontier'],
        slot_allocation=slot_alloc,
    )
    checks = [
        _check(
            'qubit_breakthrough_analysis_matches_generator',
            analysis == expected,
            expected,
            analysis,
        ),
        _check(
            'qubit_breakthrough_exact_breakdown_matches_frontier_best_qubit_family',
            analysis['exact_component_breakdown']['arithmetic_register_file_qubits']
            == int(best_qubit['arithmetic_slot_count']) * FIELD_BITS
            and analysis['exact_component_breakdown']['fixed_non_arithmetic_overhead_qubits'] == fixed_non_arithmetic_overhead,
            {
                'arithmetic_register_file_qubits': int(best_qubit['arithmetic_slot_count']) * FIELD_BITS,
                'fixed_non_arithmetic_overhead_qubits': fixed_non_arithmetic_overhead,
            },
            {
                'arithmetic_register_file_qubits': analysis['exact_component_breakdown']['arithmetic_register_file_qubits'],
                'fixed_non_arithmetic_overhead_qubits': analysis['exact_component_breakdown']['fixed_non_arithmetic_overhead_qubits'],
            },
        ),
        _check(
            'qubit_breakthrough_google_thresholds_match_exact_frontier_math',
            analysis['baseline_thresholds'] == {
                name: {
                    'baseline_logical_qubits': int(row['logical_qubits']),
                    'max_arithmetic_slots_at_current_field_width': (int(row['logical_qubits']) - fixed_non_arithmetic_overhead) // FIELD_BITS,
                    'max_field_slot_logical_qubits_at_current_exact_slot_count': (int(row['logical_qubits']) - fixed_non_arithmetic_overhead) // int(best_qubit['arithmetic_slot_count']),
                }
                for name, row in artifacts['family_frontier']['public_google_baseline'].items()
            },
            {
                name: {
                    'baseline_logical_qubits': int(row['logical_qubits']),
                    'max_arithmetic_slots_at_current_field_width': (int(row['logical_qubits']) - fixed_non_arithmetic_overhead) // FIELD_BITS,
                    'max_field_slot_logical_qubits_at_current_exact_slot_count': (int(row['logical_qubits']) - fixed_non_arithmetic_overhead) // int(best_qubit['arithmetic_slot_count']),
                }
                for name, row in artifacts['family_frontier']['public_google_baseline'].items()
            },
            analysis['baseline_thresholds'],
        ),
    ]
    return _summarize_checks(checks)


def build_full_attack_inventory_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    inventory = artifacts['full_attack_inventory']
    schedule = artifacts['full_raw32_oracle']
    hist = artifacts['module_library']['leaf_opcode_histogram']
    leaf_calls = schedule['summary']['leaf_call_count_total']
    expected_inventory = {
        'direct_seed_count': 1,
        'phase_a_leaf_calls': schedule['summary']['phase_a_leaf_calls'],
        'phase_b_leaf_calls': schedule['summary']['phase_b_leaf_calls'],
        'total_leaf_calls': leaf_calls,
        'classical_tail_elisions_removed': schedule['summary']['classical_tail_elisions_removed'],
        'whole_oracle_field_mul_count': leaf_calls * hist.get('field_mul', 0),
        'whole_oracle_field_add_count': leaf_calls * hist.get('field_add', 0),
        'whole_oracle_field_sub_count': leaf_calls * hist.get('field_sub', 0),
        'whole_oracle_field_sub_sum_count': leaf_calls * hist.get('field_sub_sum', 0),
        'whole_oracle_field_triple_count': leaf_calls * hist.get('field_triple', 0),
        'whole_oracle_field_mul_lookup_x_count': leaf_calls * hist.get('field_mul_lookup_x', 0),
        'whole_oracle_field_mul_lookup_y_count': leaf_calls * hist.get('field_mul_lookup_y', 0),
        'whole_oracle_field_mul_lookup_sum_count': leaf_calls * hist.get('field_mul_lookup_sum', 0),
        'whole_oracle_complete_a0_streamed_tail_count': leaf_calls * hist.get('complete_a0_streamed_tail', 0),
        'whole_oracle_complete_a0_fully_streamed_tail_count': leaf_calls * hist.get('complete_a0_fully_streamed_tail', 0),
        'whole_oracle_complete_a0_all_streamed_tail_count': leaf_calls * hist.get('complete_a0_all_streamed_tail', 0),
        'whole_oracle_mul_const_count': leaf_calls * hist.get('mul_const', 0),
        'whole_oracle_select_count': leaf_calls * hist.get('select_field_if_flag', 0),
        'whole_oracle_lookup_count': schedule['summary']['lookup_invocations_total'],
    }
    checks = [
        _check('full_attack_inventory_matches_generator', inventory == full_attack_inventory(), full_attack_inventory(), inventory),
        _check('inventory_counts_match_schedule_and_histogram', inventory['inventory'] == expected_inventory, expected_inventory, inventory['inventory']),
        _check(
            'full_attack_inventory_phase_shell_lowering_path_matches_expected',
            inventory['phase_shell_lowering_artifact'] == 'compiler_verification_project/artifacts/phase_shell_lowerings.json',
            'compiler_verification_project/artifacts/phase_shell_lowerings.json',
            inventory['phase_shell_lowering_artifact'],
        ),
        _check(
            'full_attack_inventory_generated_block_summary_matches_generated_block_inventory',
            inventory['generated_block_inventory_summary'] == {
                'best_gate_family': artifacts['generated_block_inventories']['best_gate_family'],
                'best_qubit_family': artifacts['generated_block_inventories']['best_qubit_family'],
                'family_reconstructed_totals': [
                    {
                        'name': row['name'],
                        'full_oracle_non_clifford': row['reconstruction']['full_oracle_non_clifford'],
                        'total_logical_qubits': row['reconstruction']['total_logical_qubits'],
                    }
                    for row in artifacts['generated_block_inventories']['families']
                ],
            },
            {
                'best_gate_family': artifacts['generated_block_inventories']['best_gate_family'],
                'best_qubit_family': artifacts['generated_block_inventories']['best_qubit_family'],
                'family_reconstructed_totals': [
                    {
                        'name': row['name'],
                        'full_oracle_non_clifford': row['reconstruction']['full_oracle_non_clifford'],
                        'total_logical_qubits': row['reconstruction']['total_logical_qubits'],
                    }
                    for row in artifacts['generated_block_inventories']['families']
                ],
            },
            inventory['generated_block_inventory_summary'],
        ),
        _check(
            'full_attack_inventory_recount_summary_matches_frontier',
            inventory['whole_oracle_recount_summary'] == {
                'best_gate_family': artifacts['family_frontier']['best_gate_family'],
                'best_qubit_family': artifacts['family_frontier']['best_qubit_family'],
                'family_recount_totals': [
                    {
                        'name': row['name'],
                        'full_oracle_non_clifford': row['full_oracle_non_clifford'],
                        'total_logical_qubits': row['total_logical_qubits'],
                    }
                    for row in artifacts['family_frontier']['families']
                ],
            },
            {
                'best_gate_family': artifacts['family_frontier']['best_gate_family'],
                'best_qubit_family': artifacts['family_frontier']['best_qubit_family'],
                'family_recount_totals': [
                    {
                        'name': row['name'],
                        'full_oracle_non_clifford': row['full_oracle_non_clifford'],
                        'total_logical_qubits': row['total_logical_qubits'],
                    }
                    for row in artifacts['family_frontier']['families']
                ],
            },
            inventory['whole_oracle_recount_summary'],
        ),
        _check('inventory_best_gate_family_matches_frontier', inventory['best_gate_family'] == artifacts['family_frontier']['best_gate_family'], artifacts['family_frontier']['best_gate_family'], inventory['best_gate_family']),
        _check('inventory_best_qubit_family_matches_frontier', inventory['best_qubit_family'] == artifacts['family_frontier']['best_qubit_family'], artifacts['family_frontier']['best_qubit_family'], inventory['best_qubit_family']),
    ]
    return _summarize_checks(checks)


def build_ft_ir_checks(artifacts: Mapping[str, Any], repo_root: Path) -> Dict[str, Any]:
    ft_ir = artifacts['ft_ir_compositions']
    expected = build_ft_ir_compositions_payload(
        schedule=artifacts['full_raw32_oracle'],
        arithmetic_lowerings=artifacts['arithmetic_lowerings'],
        lookup_lowerings=artifacts['lookup_lowerings'],
        phase_shells=artifacts['phase_shell_lowerings']['families'],
        generated_block_inventories=artifacts['generated_block_inventories'],
        frontier=artifacts['family_frontier'],
        field_bits=FIELD_BITS,
    )
    family_failures = []
    root_failures = []
    source_path_failures = []
    for path in ft_ir['source_artifacts'].values():
        path_rows = path if isinstance(path, list) else [path]
        for path_row in path_rows:
            if not (repo_root / path_row).exists():
                source_path_failures.append(path_row)
    for family in ft_ir['families']:
        graph = family['graph']
        summary = graph['summary']
        leaf_sigma = family['leaf_sigma']
        if not (
            graph['root'] == 'full_oracle'
            and summary['root_in_degree'] == 0
            and summary['reachable_node_count'] == summary['node_count']
        ):
            root_failures.append(family['name'])
        primitive_from_sigma = {'ccx': 0, 'cx': 0, 'x': 0, 'measurement': 0}
        logical_qubits_from_sigma = 0
        phase_hadamards_from_sigma = 0
        phase_measurements_from_sigma = 0
        phase_rotations_from_sigma = 0
        phase_rotation_depth_from_sigma = 0
        for entry in leaf_sigma:
            semantics = entry['resource_profile']['resource_semantics']
            if semantics == 'additive_primitive':
                for key in primitive_from_sigma:
                    primitive_from_sigma[key] += int(entry['primitive_counts_total'][key])
            elif semantics == 'peak_live_qubits':
                logical_qubits_from_sigma += int(entry['logical_qubits_total'])
            elif semantics == 'additive_phase_hadamards':
                phase_hadamards_from_sigma += int(entry['count_total'])
            elif semantics == 'additive_phase_measurements':
                phase_measurements_from_sigma += int(entry['count_total'])
            elif semantics == 'additive_phase_rotations':
                phase_rotations_from_sigma += int(entry['count_total'])
            elif semantics == 'additive_phase_rotation_depth':
                phase_rotation_depth_from_sigma += int(entry['count_total'])
        reconstruction = family['reconstruction']
        if not (
            primitive_from_sigma == reconstruction['primitive_totals']
            and primitive_from_sigma['ccx'] == reconstruction['full_oracle_non_clifford']
            and logical_qubits_from_sigma == reconstruction['total_logical_qubits']
            and phase_hadamards_from_sigma == reconstruction['phase_shell_hadamards']
            and phase_measurements_from_sigma == reconstruction['phase_shell_measurements']
            and phase_rotations_from_sigma == reconstruction['phase_shell_rotations']
            and phase_rotation_depth_from_sigma == reconstruction['phase_shell_rotation_depth']
            and reconstruction == family['generated_block_inventory_reconstruction']
            and reconstruction['full_oracle_non_clifford'] == family['frontier_reconstruction']['full_oracle_non_clifford']
            and reconstruction['total_logical_qubits'] == family['frontier_reconstruction']['total_logical_qubits']
        ):
            family_failures.append(family['name'])
    checks = [
        _check('ft_ir_compositions_match_generator', ft_ir == expected, expected, ft_ir),
        _check(
            'ft_ir_schema_matches_current_version',
            ft_ir['schema'] == 'compiler-project-ft-ir-v2',
            'compiler-project-ft-ir-v2',
            ft_ir['schema'],
        ),
        _check(
            'ft_ir_source_paths_match_expected',
            ft_ir['source_artifacts'] == {
                'full_raw32_oracle': 'compiler_verification_project/artifacts/full_raw32_oracle.json',
                'slot_allocations': [row.source_artifact for row in slot_allocation_families()],
                'arithmetic_lowerings': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
                'lookup_lowerings': 'compiler_verification_project/artifacts/lookup_lowerings.json',
                'phase_shell_lowerings': 'compiler_verification_project/artifacts/phase_shell_lowerings.json',
                'generated_block_inventories': 'compiler_verification_project/artifacts/generated_block_inventories.json',
                'family_frontier': 'compiler_verification_project/artifacts/family_frontier.json',
            },
            {
                'full_raw32_oracle': 'compiler_verification_project/artifacts/full_raw32_oracle.json',
                'slot_allocations': [row.source_artifact for row in slot_allocation_families()],
                'arithmetic_lowerings': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
                'lookup_lowerings': 'compiler_verification_project/artifacts/lookup_lowerings.json',
                'phase_shell_lowerings': 'compiler_verification_project/artifacts/phase_shell_lowerings.json',
                'generated_block_inventories': 'compiler_verification_project/artifacts/generated_block_inventories.json',
                'family_frontier': 'compiler_verification_project/artifacts/family_frontier.json',
            },
            ft_ir['source_artifacts'],
        ),
        _check('ft_ir_source_paths_exist_on_disk', len(source_path_failures) == 0, [], source_path_failures),
        _check('ft_ir_family_graphs_are_rooted_and_reachable', len(root_failures) == 0, [], root_failures),
        _check('ft_ir_leaf_sigma_reconstructs_generated_totals', len(family_failures) == 0, [], family_failures),
        _check(
            'ft_ir_best_families_match_generated_inventory',
            ft_ir['best_gate_family']['name'] == artifacts['generated_block_inventories']['best_gate_family']['name']
            and ft_ir['best_qubit_family']['name'] == artifacts['generated_block_inventories']['best_qubit_family']['name']
            and ft_ir['best_gate_family']['reconstruction']['full_oracle_non_clifford']
            == artifacts['generated_block_inventories']['best_gate_family']['reconstruction']['full_oracle_non_clifford']
            and ft_ir['best_qubit_family']['reconstruction']['total_logical_qubits']
            == artifacts['generated_block_inventories']['best_qubit_family']['reconstruction']['total_logical_qubits'],
            {
                'best_gate_family': artifacts['generated_block_inventories']['best_gate_family'],
                'best_qubit_family': artifacts['generated_block_inventories']['best_qubit_family'],
            },
            {
                'best_gate_family': ft_ir['best_gate_family'],
                'best_qubit_family': ft_ir['best_qubit_family'],
            },
        ),
    ]
    return _summarize_checks(checks)


def build_whole_oracle_recount_checks(artifacts: Mapping[str, Any], repo_root: Path) -> Dict[str, Any]:
    recount = artifacts['whole_oracle_recount']
    expected = build_whole_oracle_recount_payload(
        ft_ir_compositions=artifacts['ft_ir_compositions'],
        public_google_baseline=artifacts['family_frontier']['public_google_baseline'],
    )
    source_path_failures = [
        path
        for path in recount['source_artifacts'].values()
        if not (repo_root / path).exists()
    ]
    ft_ir_lookup = {row['name']: row for row in artifacts['ft_ir_compositions']['families']}
    frontier_lookup = {row['name']: row for row in artifacts['family_frontier']['families']}
    family_failures = []
    for family in recount['families']:
        ft_ir_row = ft_ir_lookup[family['name']]
        frontier_row = frontier_lookup[family['name']]
        if not (
            family['primitive_totals'] == ft_ir_row['reconstruction']['primitive_totals']
            and family['full_oracle_non_clifford'] == ft_ir_row['reconstruction']['full_oracle_non_clifford'] == frontier_row['full_oracle_non_clifford']
            and family['total_logical_qubits'] == ft_ir_row['reconstruction']['total_logical_qubits'] == frontier_row['total_logical_qubits']
            and family['phase_shell_hadamards'] == ft_ir_row['reconstruction']['phase_shell_hadamards'] == frontier_row['phase_shell_hadamards']
            and family['total_measurements'] == frontier_row['total_measurements']
            and family['phase_shell_measurements'] == ft_ir_row['reconstruction']['phase_shell_measurements']
            and family['phase_shell_rotations'] == ft_ir_row['reconstruction']['phase_shell_rotations']
            and family['phase_shell_rotation_depth'] == ft_ir_row['reconstruction']['phase_shell_rotation_depth'] == frontier_row['phase_shell_rotation_depth']
        ):
            family_failures.append(family['name'])
    checks = [
        _check('whole_oracle_recount_matches_generator', recount == expected, expected, recount),
        _check(
            'whole_oracle_recount_schema_matches_current_version',
            recount['schema'] == 'compiler-project-whole-oracle-recount-v2',
            'compiler-project-whole-oracle-recount-v2',
            recount['schema'],
        ),
        _check(
            'whole_oracle_recount_source_paths_match_expected',
            recount['source_artifacts'] == {
                'ft_ir_compositions': 'compiler_verification_project/artifacts/ft_ir_compositions.json',
                'family_frontier': 'compiler_verification_project/artifacts/family_frontier.json',
            },
            {
                'ft_ir_compositions': 'compiler_verification_project/artifacts/ft_ir_compositions.json',
                'family_frontier': 'compiler_verification_project/artifacts/family_frontier.json',
            },
            recount['source_artifacts'],
        ),
        _check('whole_oracle_recount_source_paths_exist_on_disk', len(source_path_failures) == 0, [], source_path_failures),
        _check('whole_oracle_recount_rows_match_ft_ir_and_frontier', len(family_failures) == 0, [], family_failures),
        _check(
            'whole_oracle_recount_best_families_match_frontier',
            recount['best_gate_family']['name'] == artifacts['family_frontier']['best_gate_family']['name']
            and recount['best_qubit_family']['name'] == artifacts['family_frontier']['best_qubit_family']['name'],
            {
                'best_gate_family': artifacts['family_frontier']['best_gate_family']['name'],
                'best_qubit_family': artifacts['family_frontier']['best_qubit_family']['name'],
            },
            {
                'best_gate_family': recount['best_gate_family']['name'],
                'best_qubit_family': recount['best_qubit_family']['name'],
            },
        ),
    ]
    return _summarize_checks(checks)


def build_subcircuit_equivalence_checks(artifacts: Mapping[str, Any], repo_root: Path) -> Dict[str, Any]:
    equivalence = artifacts['subcircuit_equivalence']
    expected = build_subcircuit_equivalence_artifact(
        arithmetic_lowerings=artifacts['arithmetic_lowerings'],
        lookup_lowerings=artifacts['lookup_lowerings'],
        generated_block_inventories=artifacts['generated_block_inventories'],
        frontier=artifacts['family_frontier'],
        full_attack_inventory=artifacts['full_attack_inventory'],
    )
    arithmetic = equivalence['arithmetic_opcode_equivalence']
    boundary_noop = equivalence['boundary_noop_equivalence']
    lookup = equivalence['lookup_family_equivalence']
    composition = equivalence['whole_oracle_composition_equivalence']
    reduced_width_failures = []
    for width_row in arithmetic['reduced_width_family_shape_witnesses']['widths']:
        for opcode in ('field_add', 'field_sub', 'field_mul', 'mul_const', 'select_field_if_flag'):
            if width_row[opcode]['pass'] != width_row[opcode]['total']:
                reduced_width_failures.append({'field_bits': width_row['field_bits'], 'opcode': opcode})
    composition_failures = []
    for family in composition['families']:
        if not (
            family['generated_full_oracle_non_clifford'] == family['frontier_full_oracle_non_clifford'] == family['inventory_full_oracle_non_clifford']
            and family['generated_total_logical_qubits'] == family['frontier_total_logical_qubits'] == family['inventory_total_logical_qubits']
        ):
            composition_failures.append(family['name'])
    lookup_failures = [
        row['name']
        for row in lookup['families']
        if not (
            row['direct_lookup_non_clifford'] == row['stage_reconstructed_non_clifford']
            and row['workspace_qubits'] == row['stage_reconstructed_workspace_qubits']
            and row['canonical_full_exhaustive_pass'] == row['canonical_full_exhaustive_total']
            and row['multibase_edge_pass'] == row['multibase_edge_total']
        )
    ]
    arithmetic_per_pc_failures = [row['pc'] for row in arithmetic['per_pc'] if row['pass'] != row['total']]
    arithmetic_per_opcode_failures = [row['opcode'] for row in arithmetic['per_opcode'] if row['pass'] != row['total']]
    expected_source_artifacts = {
        'leaf': 'compiler_verification_project/artifacts/streamed_lookup_tail_leaf.json',
        'lookup_fed_leaf_equivalence': 'compiler_verification_project/artifacts/lookup_fed_leaf_equivalence.json',
        'streamed_lookup_tail_leaf_equivalence': 'compiler_verification_project/artifacts/streamed_lookup_tail_leaf_equivalence.json',
        'arithmetic_lowerings': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
        'lookup_lowerings': 'compiler_verification_project/artifacts/lookup_lowerings.json',
        'generated_block_inventories': 'compiler_verification_project/artifacts/generated_block_inventories.json',
        'family_frontier': 'compiler_verification_project/artifacts/family_frontier.json',
        'full_attack_inventory': 'compiler_verification_project/artifacts/full_attack_inventory.json',
    }
    checks = [
        _check('subcircuit_equivalence_artifact_matches_generator', equivalence == expected, expected, equivalence),
        _check(
            'subcircuit_equivalence_source_paths_match_expected',
            equivalence['source_artifacts'] == expected_source_artifacts,
            expected_source_artifacts,
            equivalence['source_artifacts'],
        ),
        _check(
            'subcircuit_equivalence_source_paths_exist_on_disk',
            all((repo_root / path).exists() for path in equivalence['source_artifacts'].values()),
            sorted(equivalence['source_artifacts'].values()),
            sorted(path for path in equivalence['source_artifacts'].values() if (repo_root / path).exists()),
        ),
        _check('arithmetic_opcode_trace_equivalence_passes_all_traced_pcs', len(arithmetic_per_pc_failures) == 0, [], arithmetic_per_pc_failures),
        _check('arithmetic_opcode_trace_equivalence_passes_all_opcodes', len(arithmetic_per_opcode_failures) == 0, [], arithmetic_per_opcode_failures),
        _check(
            'boundary_noop_policy_traces_flag_partition',
            boundary_noop['policy'] == 'boundary_noop'
            and boundary_noop['no_leaf_select_or_cleanup_pcs']
            and boundary_noop['lookup_infinity_cases_seen'] > 0
            and boundary_noop['ordinary_cases_seen'] > 0,
            {
                'policy': 'boundary_noop',
                'no_leaf_select_or_cleanup_pcs': True,
                'lookup_infinity_cases_seen': '> 0',
                'ordinary_cases_seen': '> 0',
            },
            {
                'policy': boundary_noop['policy'],
                'no_leaf_select_or_cleanup_pcs': boundary_noop['no_leaf_select_or_cleanup_pcs'],
                'lookup_infinity_cases_seen': boundary_noop['lookup_infinity_cases_seen'],
                'ordinary_cases_seen': boundary_noop['ordinary_cases_seen'],
            },
        ),
        _check(
            'streamed_leaf_interface_equivalence_passes_edge_cases',
            equivalence['leaf_interface_equivalence']['streamed_lookup_tail_leaf']['summary']['pass']
            == equivalence['leaf_interface_equivalence']['streamed_lookup_tail_leaf']['summary']['total'],
            equivalence['leaf_interface_equivalence']['streamed_lookup_tail_leaf']['summary']['total'],
            equivalence['leaf_interface_equivalence']['streamed_lookup_tail_leaf']['summary']['pass'],
        ),
        _check('lookup_family_equivalence_passes_all_semantic_witnesses', len(lookup_failures) == 0, [], lookup_failures),
        _check('reduced_width_family_shape_witnesses_pass', len(reduced_width_failures) == 0, [], reduced_width_failures),
        _check('whole_oracle_composition_equivalence_rows_match_all_layers', len(composition_failures) == 0, [], composition_failures),
        _check(
            'whole_oracle_best_families_match_generated_inventory',
            composition['best_gate_family'] == artifacts['generated_block_inventories']['best_gate_family']
            and composition['best_qubit_family'] == artifacts['generated_block_inventories']['best_qubit_family'],
            {
                'best_gate_family': artifacts['generated_block_inventories']['best_gate_family'],
                'best_qubit_family': artifacts['generated_block_inventories']['best_qubit_family'],
            },
            {
                'best_gate_family': composition['best_gate_family'],
                'best_qubit_family': composition['best_qubit_family'],
            },
        ),
    ]
    return _summarize_checks(checks)


def build_headline_opcode_coverage_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    coverage = artifacts['headline_opcode_coverage']
    expected = build_headline_opcode_coverage(
        leaf=artifacts['streamed_lookup_tail_leaf'],
        streamed_lookup_tail_leaf_equivalence=artifacts['streamed_lookup_tail_leaf_equivalence'],
        subcircuit_equivalence=artifacts['subcircuit_equivalence'],
        arithmetic_lowerings=artifacts['arithmetic_lowerings'],
        resource_liveness_certificate=artifacts['resource_liveness_certificate'],
    )
    rows_by_opcode = {row['opcode']: row for row in coverage['rows']}
    tail_row = rows_by_opcode['complete_a0_all_streamed_tail']
    checks = [
        _check('headline_opcode_coverage_matches_generator', coverage == expected, expected, coverage),
        _check('headline_opcode_coverage_schema_is_current', coverage['schema'] == 'compiler-project-headline-opcode-coverage-v1', 'compiler-project-headline-opcode-coverage-v1', coverage['schema']),
        _check('headline_opcode_coverage_matches_leaf_histogram', coverage['headline_opcode_histogram'] == leaf_opcode_histogram(), leaf_opcode_histogram(), coverage['headline_opcode_histogram']),
        _check('headline_opcode_coverage_has_policy_for_every_opcode', coverage['all_headline_opcodes_have_policy'] is True, True, coverage['rows']),
        _check('headline_opcode_coverage_has_zkp_prepared_kind_for_every_opcode', coverage['all_headline_opcodes_have_zkp_prepared_kind'] is True, True, coverage['rows']),
        _check('headline_opcode_coverage_has_liveness_rows_for_every_pc', coverage['all_headline_opcode_pcs_have_liveness_rows'] is True, True, coverage['rows']),
        _check('headline_opcode_coverage_all_required_layers_pass', coverage['all_required_opcode_coverage_passes'] is True and all(row['passes_required_coverage'] is True for row in coverage['rows']), True, coverage['rows']),
        _check('headline_opcode_coverage_tail_opcode_has_counted_lowering_and_sigma_rows', tail_row['arithmetic_lowering_non_clifford_per_kernel'] == artifacts['resource_liveness_certificate']['macro_lowering_inventory']['exact_non_clifford_per_kernel'] and tail_row['macro_leaf_sigma']['row_count'] > 0 and tail_row['macro_leaf_sigma']['whole_oracle_non_clifford'] > 0, {'non_clifford': artifacts['resource_liveness_certificate']['macro_lowering_inventory']['exact_non_clifford_per_kernel'], 'sigma_rows': '> 0'}, tail_row),
    ]
    return _summarize_checks(checks)


def build_headline_resource_manifest_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    manifest = artifacts['headline_resource_manifest']
    lowering = artifacts['reusable_chunk_lowering']
    selected_family_name = artifacts['compiler_parameters']['public_headline_policy']['selected_public_family_name']
    expected = build_headline_resource_manifest(
        reusable_chunk_lowering=lowering,
        selected_family_name=selected_family_name,
    )
    checks = [
        _check('headline_resource_manifest_matches_generator', manifest == expected, expected, manifest),
        _check('headline_resource_manifest_schema_is_current', manifest['schema'] == HEADLINE_RESOURCE_MANIFEST_SCHEMA, HEADLINE_RESOURCE_MANIFEST_SCHEMA, manifest['schema']),
        _check('headline_resource_manifest_family_matches_compiler_parameters', manifest['selected_family_name'] == selected_family_name, selected_family_name, manifest['selected_family_name']),
        _check('headline_resource_manifest_binds_reusable_chunk_counted_ir', manifest['source_counted_resource_ir_sha256'] == lowering['resource_contract_engine']['counted_resource_ir_sha256'], lowering['resource_contract_engine']['counted_resource_ir_sha256'], manifest['source_counted_resource_ir_sha256']),
        _check('headline_resource_manifest_reconstructs_public_non_clifford', manifest['public_totals']['non_clifford'] == lowering['non_clifford_derivation']['candidate_total_non_clifford'], lowering['non_clifford_derivation']['candidate_total_non_clifford'], manifest['public_totals']['non_clifford']),
        _check('headline_resource_manifest_reconstructs_public_qubits', manifest['public_totals']['logical_qubits'] == lowering['qubit_derivation']['candidate_total_logical_qubits'], lowering['qubit_derivation']['candidate_total_logical_qubits'], manifest['public_totals']['logical_qubits']),
        _check('headline_resource_manifest_expands_qroam_stream_instances', manifest['checks']['qroam_rows_expand_stream_plan_instances'] is True and manifest['term_row_count'] > len(lowering['counted_resource_ir']['non_clifford_terms']), {'qroam_rows_expand_stream_plan_instances': True}, manifest),
    ]
    return _summarize_checks(checks)


def build_public_engine_manifest_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    manifest = artifacts['public_engine_manifest']
    lowering = artifacts['reusable_chunk_lowering']
    compiler_parameters = artifacts['compiler_parameters']
    selected_family_name = compiler_parameters['public_headline_policy']['selected_public_family_name']
    expected = build_public_engine_manifest(
        reusable_chunk_lowering=lowering,
        reusable_chunk_tail_candidate=artifacts['reusable_chunk_tail_candidate'],
        streamed_lookup_tail_leaf_equivalence=artifacts['streamed_lookup_tail_leaf_equivalence'],
        release_corpus_preflight=artifacts['release_corpus_preflight'],
        compiler_parameters=compiler_parameters,
        arithmetic_operation_ir=artifacts['arithmetic_operation_ir'],
        qroam_primitive_certificate=artifacts['qroam_primitive_certificate'],
        qroam_table_cnot_materialization=artifacts['qroam_table_cnot_materialization'],
        phase_shell_lowerings=artifacts['phase_shell_lowerings'],
        public_candidate_materialized_circuit_manifest=artifacts['public_candidate_materialized_circuit_manifest'],
        selected_family_name=selected_family_name,
    )
    executable_resource_engine = lowering['executable_resource_engine']
    resource_contract_engine = lowering['resource_contract_engine']
    qroam_table_cnot = artifacts['qroam_table_cnot_materialization']
    checks = [
        _check('public_engine_manifest_matches_generator', manifest == expected, expected, manifest),
        _check('public_engine_manifest_schema_is_current', manifest['schema'] == PUBLIC_ENGINE_MANIFEST_SCHEMA, PUBLIC_ENGINE_MANIFEST_SCHEMA, manifest['schema']),
        _check('public_engine_manifest_binds_selected_family', manifest['selected_family_name'] == selected_family_name, selected_family_name, manifest['selected_family_name']),
        _check(
            'public_engine_manifest_derives_public_totals_from_materialized_flat_engine',
            manifest['public_totals']['source'] == PUBLIC_ENGINE_CANONICAL_TOTALS_SOURCE
            and manifest['public_totals']['non_clifford'] == artifacts['public_candidate_materialized_circuit_manifest'][CANONICAL_MATERIALIZED_FLAT_NETLIST]['non_clifford_count']
            and manifest['public_totals']['logical_qubits'] == artifacts['public_candidate_materialized_circuit_manifest'][CANONICAL_MATERIALIZED_FLAT_NETLIST]['peak_live_qubits']
            and artifacts['public_candidate_materialized_circuit_manifest'][CANONICAL_MATERIALIZED_FLAT_NETLIST]['exact_operation_stream_materialized'] is True
            and manifest['checks'][PUBLIC_TOTALS_MATCH_CANONICAL_ENGINE_CHECK] is True,
            {
                'source': PUBLIC_ENGINE_CANONICAL_TOTALS_SOURCE,
                'non_clifford': artifacts['public_candidate_materialized_circuit_manifest'][CANONICAL_MATERIALIZED_FLAT_NETLIST]['non_clifford_count'],
                'logical_qubits': artifacts['public_candidate_materialized_circuit_manifest'][CANONICAL_MATERIALIZED_FLAT_NETLIST]['peak_live_qubits'],
            },
            manifest['public_totals'],
        ),
        _check('public_engine_manifest_binds_counted_ir_digest', manifest['source_digests']['counted_resource_ir_sha256'] == executable_resource_engine['counted_resource_ir_sha256'], executable_resource_engine['counted_resource_ir_sha256'], manifest['source_digests']['counted_resource_ir_sha256']),
        _check('public_engine_manifest_binds_liveness_and_owner_digests', manifest['source_digests']['executable_liveness_sha256'] == resource_contract_engine['executable_liveness_sha256'] and manifest['source_digests']['owner_capacity_sha256'] == resource_contract_engine['owner_capacity_sha256'], {'executable_liveness_sha256': resource_contract_engine['executable_liveness_sha256'], 'owner_capacity_sha256': resource_contract_engine['owner_capacity_sha256']}, manifest['source_digests']),
        _check('public_engine_manifest_binds_qroam_table_cnot_digest', manifest['source_digests']['qroam_table_cnot_materialization_sha256'] == _canonical_payload_sha256(qroam_table_cnot), _canonical_payload_sha256(qroam_table_cnot), manifest['source_digests']['qroam_table_cnot_materialization_sha256']),
        _check('public_engine_manifest_instruction_schedule_and_wire_streams_are_nonempty', manifest['instruction_stream']['row_count'] > 0 and manifest['schedule_stream']['row_count'] > 0 and manifest['wire_catalog_stream']['row_count'] > 0, '> 0 rows', {'instruction_rows': manifest['instruction_stream']['row_count'], 'schedule_rows': manifest['schedule_stream']['row_count'], 'wire_rows': manifest['wire_catalog_stream']['row_count']}),
        _check('public_engine_manifest_fast_contract_is_no_zkp', manifest['fast_no_zkp_contract']['prover_required'] is False and manifest['fast_no_zkp_contract']['verify_group'] == 'public_engine_manifest_checks', {'prover_required': False, 'verify_group': 'public_engine_manifest_checks'}, manifest['fast_no_zkp_contract']),
        _check('public_engine_manifest_binds_semantic_boundary_evidence', manifest['semantic_boundary_evidence']['streamed_lookup_tail_leaf_equivalence']['pass'] == manifest['semantic_boundary_evidence']['streamed_lookup_tail_leaf_equivalence']['total'] and manifest['semantic_boundary_evidence']['release_corpus_preflight']['case_count'] == GOOGLE_COMPARABLE_CASE_COUNT and all(manifest['semantic_boundary_evidence']['release_corpus_preflight']['category_counts'].get(category, 0) > 0 for category in manifest['semantic_boundary_evidence']['required_categories']) and manifest['semantic_boundary_evidence']['compiler_parameters']['selected_public_family_name'] == selected_family_name, 'semantic boundary evidence covers required categories in release corpus and binds compiler parameters', manifest['semantic_boundary_evidence']),
        _check('public_engine_manifest_binds_primitive_operation_evidence', manifest['primitive_operation_evidence']['arithmetic_operation_ir']['pass'] is True and manifest['primitive_operation_evidence']['qroam_primitive_certificate']['pass'] is True and manifest['primitive_operation_evidence']['qroam_table_cnot_materialization']['pass'] is True and manifest['primitive_operation_evidence']['public_candidate_materialized_circuit_manifest']['pass'] is True and manifest['primitive_operation_evidence']['qroam_primitive_certificate']['whole_oracle_non_clifford'] == lowering['non_clifford_derivation']['qroam_chunk_non_clifford'] and manifest['primitive_operation_evidence']['qroam_table_cnot_materialization']['full_oracle_emitted_clifford_cx'] == qroam_table_cnot['totals']['full_oracle_emitted_clifford_cx'] and manifest['primitive_operation_evidence']['phase_shell']['name'] in selected_family_name, 'primitive operation evidence binds materialized public candidate, arithmetic, qroam, table-CNOT, and phase shell sources', manifest['primitive_operation_evidence']),
        _check('public_engine_manifest_passes_internal_checks', manifest['pass'] is True and all(manifest['checks'].values()), True, manifest['checks']),
    ]
    return _summarize_checks(checks)


def build_engine_completion_audit_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    audit = artifacts['engine_completion_audit']
    expected = build_engine_completion_audit(
        public_engine_manifest=artifacts['public_engine_manifest'],
        public_candidate_materialized_circuit_manifest=artifacts['public_candidate_materialized_circuit_manifest'],
        arithmetic_operand_replay_audit=artifacts['arithmetic_operand_replay_audit'],
        reusable_chunk_lowering=artifacts['reusable_chunk_lowering'],
        arithmetic_operation_ir=artifacts['arithmetic_operation_ir'],
        lookup_lowerings=artifacts['lookup_lowerings'],
        qroam_primitive_certificate=artifacts['qroam_primitive_certificate'],
        qroam_table_cnot_materialization=artifacts['qroam_table_cnot_materialization'],
        phase_shell_lowerings=artifacts['phase_shell_lowerings'],
        release_corpus_preflight=artifacts['release_corpus_preflight'],
        streamed_lookup_tail_leaf_equivalence=artifacts['streamed_lookup_tail_leaf_equivalence'],
        modular_arithmetic_certificate=artifacts['modular_arithmetic_certificate'],
        tail_macro_engine=artifacts['tail_macro_engine'],
        tail_macro_liveness=artifacts['tail_macro_liveness'],
        tail_macro_reversibility=artifacts['tail_macro_reversibility'],
        tail_macro_schedule_search=artifacts['tail_macro_schedule_search'],
        compiler_parameters=artifacts['compiler_parameters'],
        zkp_attestation_input=artifacts['zkp_attestation_reusable_chunk_candidate_input'],
    )
    materialized_flat = artifacts['public_candidate_materialized_circuit_manifest'][CANONICAL_MATERIALIZED_FLAT_NETLIST]
    checks = [
        _check('engine_completion_audit_matches_generator', audit == expected, expected, audit),
        _check('engine_completion_audit_schema_is_current', audit['schema'] == ENGINE_COMPLETION_AUDIT_SCHEMA, ENGINE_COMPLETION_AUDIT_SCHEMA, audit['schema']),
        _check('engine_completion_audit_derives_headline_from_canonical_materialized_flat_netlist', audit['public_totals']['source'] == PUBLIC_ENGINE_CANONICAL_TOTALS_SOURCE and audit['public_totals']['non_clifford'] == materialized_flat['non_clifford_count'] and audit['public_totals']['logical_qubits'] == materialized_flat['peak_live_qubits'] and audit['public_totals']['operation_count'] == materialized_flat['operation_count'], materialized_flat, audit['public_totals']),
        _check(
            'engine_completion_audit_requires_explicit_remaining_macro_boundaries',
            audit['clifford_complete_goal_achieved'] is False
            and {
                'modular_arithmetic_clifford_expansion',
                'tail_macro_schedule_and_reversibility',
            }.issubset({row['name'] for row in audit['remaining_macro_boundaries']})
            and 'single_engine_zkp_input_derivation' not in {row['name'] for row in audit['remaining_macro_boundaries']}
            and 'qroam_bit_level_netlist_expansion' in {row['name'] for row in audit['covered_boundaries']}
            and 'arithmetic_operand_replay' in {row['name'] for row in audit['covered_boundaries']}
            and 'canonical_engine_zkp_input_authority' in {row['name'] for row in audit['covered_boundaries']}
            and audit['checks']['remaining_macro_boundaries_are_explicit'] is True
            and audit['checks']['public_claim_not_marked_full_clifford_complete_until_macro_boundaries_flattened'] is True,
            'explicit arithmetic and tail boundaries remain; qroam, arithmetic operand replay, and canonical engine ZKP authority are covered without a full-completion claim',
            {'clifford_complete_goal_achieved': audit['clifford_complete_goal_achieved'], 'covered_boundaries': audit['covered_boundaries'], 'remaining_macro_boundaries': audit['remaining_macro_boundaries'], 'checks': audit['checks']},
        ),
        _check('engine_completion_audit_source_binding_covers_all_run_length_rows', audit['checks']['source_binding_covers_every_run_length_row'] is True and audit['source_binding_summary']['rows_checked'] == artifacts['public_candidate_materialized_circuit_manifest']['run_length_row_count'] and sum(audit['source_binding_summary']['rows_by_source_kind'].values()) == audit['source_binding_summary']['rows_checked'], 'all run-length rows source-bound', audit['source_binding_summary']),
        _check('engine_completion_audit_passes_internal_checks', audit['pass'] is True and all(audit['checks'].values()), True, audit['checks']),
    ]
    return _summarize_checks(checks)


def build_arithmetic_operand_replay_audit_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    audit = artifacts['arithmetic_operand_replay_audit']
    expected = build_arithmetic_operand_replay_audit(
        public_candidate_materialized_circuit_manifest=artifacts['public_candidate_materialized_circuit_manifest'],
        arithmetic_lowerings=artifacts['arithmetic_lowerings'],
        arithmetic_operation_ir=artifacts['arithmetic_operation_ir'],
    )
    checks = [
        _check('arithmetic_operand_replay_audit_matches_generator', audit == expected, expected, audit),
        _check('arithmetic_operand_replay_audit_passes', audit['pass'] is True, True, audit),
        _check(
            'arithmetic_operand_replay_audit_checks_all_arithmetic_rows',
            audit['arithmetic_run_length_rows_checked'] == artifacts['public_candidate_materialized_circuit_manifest']['arithmetic_leaf_block_row_count']
            and audit['source_operations_checked'] > artifacts['arithmetic_operation_ir']['selected_leaf_exact_operation_stream']['operation_count']
            and audit['rows_with_failures'] == 0
            and audit['unique_block_gate_failures'] == 0,
            {
                'arithmetic_rows': artifacts['public_candidate_materialized_circuit_manifest']['arithmetic_leaf_block_row_count'],
                'minimum_source_operations': artifacts['arithmetic_operation_ir']['selected_leaf_exact_operation_stream']['operation_count'],
                'failures': 0,
            },
            audit,
        ),
    ]
    return _summarize_checks(checks)


def build_constant_provenance_checks(artifacts: Mapping[str, Any], repo_root: Path) -> Dict[str, Any]:
    provenance = artifacts['constant_provenance']
    expected = build_constant_provenance(
        repo_root=repo_root,
        compiler_parameters=artifacts['compiler_parameters'],
        phase_shell_lowerings=artifacts['phase_shell_lowerings'],
        reusable_chunk_lowering=artifacts['reusable_chunk_lowering'],
        zkp_attestation_input=artifacts['zkp_attestation_reusable_chunk_candidate_input'],
        public_headline_result=artifacts['public_headline_result'],
        headline_resource_manifest=artifacts['headline_resource_manifest'],
    )
    checks = [
        _check('constant_provenance_matches_generator', provenance == expected, expected, provenance),
        _check('constant_provenance_schema_is_current', provenance['schema'] == CONSTANT_PROVENANCE_SCHEMA, CONSTANT_PROVENANCE_SCHEMA, provenance['schema']),
        _check('constant_provenance_source_rows_pass', all(row['pass'] for row in provenance['source_rows']), True, provenance['source_rows']),
        _check('constant_provenance_forbidden_literals_absent', provenance['checks']['forbidden_historic_literals_absent'] is True, True, provenance['forbidden_literal_scan']),
        _check('constant_provenance_zkp_resource_fields_are_derived', provenance['checks']['tracked_zkp_family_resource_fields_are_not_integer_literals'] is True, True, provenance['ast_literal_audits']),
        _check('constant_provenance_candidate_beats_limits', provenance['checks']['candidate_beats_public_limits'] is True, True, provenance['checks']),
        _check('constant_provenance_passes_internal_checks', provenance['pass'] is True and all(provenance['checks'].values()), True, provenance['checks']),
    ]
    return _summarize_checks(checks)


def build_primitive_multiplier_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    primitive = artifacts['primitive_multiplier_library']
    schedule = artifacts['full_raw32_oracle']
    kernel = artifacts['module_library']
    field_mul_kernel = next(row for row in artifacts['arithmetic_lowerings']['kernels'] if row['opcode'] == 'field_mul')
    expected_per_leaf = []
    for instruction in central_executable_leaf()['instructions']:
        opcode = str(instruction['op'])
        if opcode in {'field_mul', 'field_mul_lookup_x', 'field_mul_lookup_y', 'field_mul_lookup_sum'}:
            expected_per_leaf.append({
                'leaf_multiplier_index': len(expected_per_leaf),
                'leaf_pc': int(instruction['pc']),
                'opcode': opcode,
                'family': kernel['name'],
                'field_bits': FIELD_BITS,
                'exact_non_clifford': field_mul_kernel['exact_non_clifford_per_kernel'],
                'gate_set': kernel['gate_set'],
                'arithmetic_lowering_artifact': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
            })
        elif opcode in {'complete_a0_streamed_tail', 'complete_a0_fully_streamed_tail', 'complete_a0_all_streamed_tail'}:
            for tail_product in ('KN', 'EC', 'NM', 'CL', 'ME', 'LK'):
                expected_per_leaf.append({
                    'leaf_multiplier_index': len(expected_per_leaf),
                    'leaf_pc': int(instruction['pc']),
                    'opcode': opcode,
                    'tail_product': tail_product,
                    'family': kernel['name'],
                    'field_bits': FIELD_BITS,
                    'exact_non_clifford': field_mul_kernel['exact_non_clifford_per_kernel'],
                    'gate_set': kernel['gate_set'],
                    'arithmetic_lowering_artifact': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
                })
    expected_examples = []
    for call in schedule['leaf_calls']:
        for entry in expected_per_leaf:
            expected_examples.append({
                'call_index': call['call_index'],
                'phase_register': call['phase_register'],
                'window_index_within_register': call['window_index_within_register'],
                **entry,
            })
    checks = [
        _check('primitive_multiplier_library_matches_generator', primitive == primitive_multiplier_library(), primitive_multiplier_library(), primitive),
        _check('per_leaf_multiplier_instances_match_leaf_field_mul_pcs', primitive['per_leaf_multiplier_instances'] == expected_per_leaf, expected_per_leaf, primitive['per_leaf_multiplier_instances']),
        _check(
            'whole_oracle_multiplier_instance_count_matches_schedule_times_leaf_multipliers',
            primitive['whole_oracle_multiplier_instance_count'] == schedule['summary']['leaf_call_count_total'] * len(expected_per_leaf),
            schedule['summary']['leaf_call_count_total'] * len(expected_per_leaf),
            primitive['whole_oracle_multiplier_instance_count'],
        ),
        _check(
            'whole_oracle_multiplier_total_matches_instance_count',
            primitive['whole_oracle_multiplier_non_clifford_total'] == primitive['whole_oracle_multiplier_instance_count'] * field_mul_kernel['exact_non_clifford_per_kernel'],
            primitive['whole_oracle_multiplier_instance_count'] * field_mul_kernel['exact_non_clifford_per_kernel'],
            primitive['whole_oracle_multiplier_non_clifford_total'],
        ),
        _check('example_instances_match_cross_product_prefix', primitive['example_instances'] == expected_examples[:8], expected_examples[:8], primitive['example_instances']),
    ]
    return _summarize_checks(checks)


def build_frontier_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    frontier = artifacts['family_frontier']
    schedule = artifacts['full_raw32_oracle']
    slot_alloc = artifacts['exact_leaf_slot_allocation']
    kernel = artifacts['module_library']
    expected_lookup_families = [row.__dict__ for row in lookup_families()]
    expected_phase_shells = [row.__dict__ for row in phase_shell_families()]
    expected_slot_families = [
        {
            'name': row.name,
            'summary': row.summary,
            'source_artifact': row.source_artifact,
            'leaf_source_artifact': row.leaf_source_artifact,
            'slot_allocation': row.slot_allocation,
            'notes': row.notes,
        }
        for row in slot_allocation_families()
    ]
    families = frontier['families']
    recount_lookup = {row['name']: row for row in artifacts['whole_oracle_recount']['families']}
    expected_families = []
    for slot_family in expected_slot_families:
        for lookup in frontier['lookup_families']:
            for phase_shell in frontier['phase_shell_families']:
                family_name = f"{lookup['name']}__{slot_family['name']}__{phase_shell['name']}"
                inventory = next(
                    row['reconstruction']
                    for row in artifacts['generated_block_inventories']['families']
                    if row['name'] == family_name
                )
                recount = recount_lookup[family_name]
                expected_families.append({
                    'name': family_name,
                    'summary': f"{lookup['summary']} / {phase_shell['summary']} / {slot_family['summary']}",
                    'gate_set': f"{lookup['gate_set']}; {phase_shell['gate_set']}",
                    'phase_shell': phase_shell['name'],
                    'slot_allocation_family': slot_family['name'],
                    'arithmetic_kernel_family': kernel['name'],
                    'lookup_family': lookup['name'],
                    'arithmetic_leaf_non_clifford': inventory['arithmetic_leaf_non_clifford'],
                    'direct_seed_non_clifford': inventory['direct_seed_non_clifford'],
                    'per_leaf_lookup_non_clifford': inventory['per_leaf_lookup_non_clifford'],
                    'full_oracle_non_clifford': recount['full_oracle_non_clifford'],
                    'arithmetic_slot_count': inventory['arithmetic_slot_count'],
                    'control_slot_count': inventory['control_slot_count'],
                    'borrowed_interface_qubits': inventory.get('borrowed_interface_qubits', 0),
                    'lookup_workspace_qubits': inventory['lookup_workspace_qubits'],
                    'live_phase_bits': inventory['live_phase_bits'],
                    'total_logical_qubits': recount['total_logical_qubits'],
                    'phase_shell_hadamards': recount['phase_shell_hadamards'],
                    'phase_shell_measurements': recount['phase_shell_measurements'],
                    'phase_shell_rotations': recount['phase_shell_rotations'],
                    'phase_shell_rotation_depth': recount['phase_shell_rotation_depth'],
                    'total_measurements': recount['total_measurements'],
                    'improvement_vs_google_low_qubit': recount['improvement_vs_google_low_qubit'],
                    'improvement_vs_google_low_gate': recount['improvement_vs_google_low_gate'],
                    'qubit_ratio_vs_google_low_qubit': recount['qubit_ratio_vs_google_low_qubit'],
                    'qubit_ratio_vs_google_low_gate': recount['qubit_ratio_vs_google_low_gate'],
                    'notes': [*lookup['notes'], *phase_shell['notes']],
                })
    expected_best_gate = min(expected_families, key=lambda row: (row['full_oracle_non_clifford'], row['total_logical_qubits']))
    expected_best_qubit = min(expected_families, key=lambda row: (row['total_logical_qubits'], row['full_oracle_non_clifford']))
    expected_sub30m_rows = [row for row in expected_families if row['full_oracle_non_clifford'] < 30_000_000]
    expected_best_sub30m_qubit = None if not expected_sub30m_rows else min(
        expected_sub30m_rows,
        key=lambda row: (row['total_logical_qubits'], row['full_oracle_non_clifford']),
    )
    expected_best_google_low_gate_qubit = min(
        (
            row for row in expected_families
            if row['full_oracle_non_clifford'] < PUBLIC_GOOGLE_BASELINE['low_gate']['non_clifford']
        ),
        key=lambda row: (row['total_logical_qubits'], row['full_oracle_non_clifford']),
    )
    checks = [
        _check('public_google_baseline_matches_source_artifact', frontier['public_google_baseline'] == artifacts['public_google_baseline_source']['lines'] == PUBLIC_GOOGLE_BASELINE, artifacts['public_google_baseline_source']['lines'], frontier['public_google_baseline']),
        _check('frontier_schema_matches_current_version', frontier['schema'] == 'compiler-project-frontier-v11', 'compiler-project-frontier-v11', frontier['schema']),
        _check('frontier_schedule_matches_standalone_schedule', frontier['schedule'] == schedule, schedule, frontier['schedule']),
        _check('frontier_slot_allocation_matches_standalone_slot_allocation', frontier['slot_allocation'] == slot_alloc, slot_alloc, frontier['slot_allocation']),
        _check('frontier_slot_allocation_families_match_expected', frontier['slot_allocation_families'] == expected_slot_families, expected_slot_families, frontier['slot_allocation_families']),
        _check('frontier_arithmetic_kernel_matches_module_library', frontier['arithmetic_kernel_family'] == kernel, kernel, frontier['arithmetic_kernel_family']),
        _check(
            'frontier_arithmetic_lowering_artifact_path_matches_expected',
            frontier['arithmetic_lowering_artifact'] == 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
            'compiler_verification_project/artifacts/arithmetic_lowerings.json',
            frontier['arithmetic_lowering_artifact'],
        ),
        _check(
            'frontier_lookup_lowering_artifact_path_matches_expected',
            frontier['lookup_lowering_artifact'] == 'compiler_verification_project/artifacts/lookup_lowerings.json',
            'compiler_verification_project/artifacts/lookup_lowerings.json',
            frontier['lookup_lowering_artifact'],
        ),
        _check(
            'frontier_phase_shell_lowering_artifact_path_matches_expected',
            frontier['phase_shell_lowering_artifact'] == 'compiler_verification_project/artifacts/phase_shell_lowerings.json',
            'compiler_verification_project/artifacts/phase_shell_lowerings.json',
            frontier['phase_shell_lowering_artifact'],
        ),
        _check(
            'frontier_generated_block_inventory_path_matches_expected',
            frontier['generated_block_inventory_artifact'] == 'compiler_verification_project/artifacts/generated_block_inventories.json',
            'compiler_verification_project/artifacts/generated_block_inventories.json',
            frontier['generated_block_inventory_artifact'],
        ),
        _check(
            'frontier_whole_oracle_recount_path_matches_expected',
            frontier['whole_oracle_recount_artifact'] == 'compiler_verification_project/artifacts/whole_oracle_recount.json',
            'compiler_verification_project/artifacts/whole_oracle_recount.json',
            frontier['whole_oracle_recount_artifact'],
        ),
        _check('lookup_family_library_matches_named_lookup_families', frontier['lookup_families'] == expected_lookup_families, expected_lookup_families, frontier['lookup_families']),
        _check('phase_shell_library_matches_named_phase_shells', frontier['phase_shell_families'] == expected_phase_shells, expected_phase_shells, frontier['phase_shell_families']),
        _check('frontier_family_rows_reconstruct_from_components', families == expected_families, expected_families, families),
        _check('best_gate_family_is_minimum_over_family_rows', frontier['best_gate_family'] == expected_best_gate, expected_best_gate, frontier['best_gate_family']),
        _check('best_qubit_family_is_minimum_over_family_rows', frontier['best_qubit_family'] == expected_best_qubit, expected_best_qubit, frontier['best_qubit_family']),
        _check(
            'best_google_low_gate_qubit_family_is_minimum_over_google_gate_rows',
            frontier['best_google_low_gate_qubit_family'] == expected_best_google_low_gate_qubit,
            expected_best_google_low_gate_qubit,
            frontier['best_google_low_gate_qubit_family'],
        ),
        _check(
            'best_sub30m_qubit_family_is_minimum_over_sub30m_rows',
            frontier['best_sub30m_qubit_family'] == expected_best_sub30m_qubit,
            expected_best_sub30m_qubit,
            frontier['best_sub30m_qubit_family'],
        ),
    ]
    return _summarize_checks(checks)


def build_build_summary_checks(artifacts: Mapping[str, Any], repo_root: Path) -> Dict[str, Any]:
    build_summary = artifacts['build_summary']
    expected_paths = dict(BUILD_SUMMARY_ARTIFACT_PATHS)
    checks = [
        _check('build_summary_schema_matches_current_version', build_summary['schema'] == BUILD_SUMMARY_SCHEMA, BUILD_SUMMARY_SCHEMA, build_summary['schema']),
        _check('build_summary_artifact_paths_match_expected_set', build_summary['artifacts'] == expected_paths, expected_paths, build_summary['artifacts']),
        _check(
            'build_summary_paths_exist_on_disk',
            all((repo_root / path).exists() for path in build_summary['artifacts'].values()),
            sorted(build_summary['artifacts'].values()),
            sorted(path for path in build_summary['artifacts'].values() if (repo_root / path).exists()),
        ),
        _check('build_summary_best_gate_matches_frontier', build_summary['headline']['best_gate_family'] == artifacts['family_frontier']['best_gate_family'], artifacts['family_frontier']['best_gate_family'], build_summary['headline']['best_gate_family']),
        _check('build_summary_best_qubit_matches_frontier', build_summary['headline']['best_qubit_family'] == artifacts['family_frontier']['best_qubit_family'], artifacts['family_frontier']['best_qubit_family'], build_summary['headline']['best_qubit_family']),
        _check('build_summary_best_google_low_gate_qubit_matches_frontier', build_summary['headline']['best_google_low_gate_qubit_family'] == artifacts['family_frontier']['best_google_low_gate_qubit_family'], artifacts['family_frontier']['best_google_low_gate_qubit_family'], build_summary['headline']['best_google_low_gate_qubit_family']),
        _check(
            'build_summary_best_sub30m_qubit_matches_frontier',
            build_summary['headline']['best_sub30m_qubit_family'] == artifacts['family_frontier']['best_sub30m_qubit_family'],
            artifacts['family_frontier']['best_sub30m_qubit_family'],
            build_summary['headline']['best_sub30m_qubit_family'],
        ),
        _check(
            'build_summary_names_public_headline_result_artifact',
            build_summary['headline']['public_headline_result_artifact'] == BUILD_SUMMARY_ARTIFACT_PATHS['public_headline_result'],
            BUILD_SUMMARY_ARTIFACT_PATHS['public_headline_result'],
            build_summary['headline'].get('public_headline_result_artifact'),
        ),
        _check(
            'build_summary_names_strict_replayed_tail_headline_artifact',
            build_summary['headline']['strict_replayed_tail_headline_artifact'] == BUILD_SUMMARY_ARTIFACT_PATHS['strict_replayed_tail_headline'],
            BUILD_SUMMARY_ARTIFACT_PATHS['strict_replayed_tail_headline'],
            build_summary['headline'].get('strict_replayed_tail_headline_artifact'),
        ),
        _check(
            'build_summary_names_primary_strict_result_artifact',
            build_summary['headline']['primary_strict_result_artifact'] == BUILD_SUMMARY_ARTIFACT_PATHS['primary_strict_result'],
            BUILD_SUMMARY_ARTIFACT_PATHS['primary_strict_result'],
            build_summary['headline'].get('primary_strict_result_artifact'),
        ),
    ]
    return _summarize_checks(checks)


def build_artifact_digest_tree_checks(artifacts: Mapping[str, Any], repo_root: Path) -> Dict[str, Any]:
    digest_tree = artifacts['artifact_digest_tree']
    expected = build_artifact_digest_tree(
        repo_root=repo_root,
        size_threshold_bytes=int(digest_tree['size_threshold_bytes']),
        chunk_size_bytes=int(digest_tree['chunk_size_bytes']),
    )
    checks = [
        _check('artifact_digest_tree_matches_generator', digest_tree == expected, expected, digest_tree),
        _check('artifact_digest_tree_schema_is_current', digest_tree['schema'] == ARTIFACT_DIGEST_TREE_SCHEMA, ARTIFACT_DIGEST_TREE_SCHEMA, digest_tree['schema']),
        _check('artifact_digest_tree_passes_internal_checks', digest_tree['pass'] is True and all(digest_tree['checks'].values()), True, digest_tree['checks']),
        _check('artifact_digest_tree_contains_only_large_tracked_files', all(row['bytes'] >= digest_tree['size_threshold_bytes'] and (repo_root / row['path']).exists() for row in digest_tree['files']), 'tracked files above threshold', digest_tree['files']),
        _check('artifact_digest_tree_chunks_reconstruct_file_sizes', all(sum(chunk['bytes'] for chunk in row['chunks']) == row['bytes'] for row in digest_tree['files']), 'chunk byte sums equal file bytes', digest_tree['files']),
    ]
    return _summarize_checks(checks)


def build_proof_environment_contract_checks(artifacts: Mapping[str, Any], repo_root: Path) -> Dict[str, Any]:
    contract = artifacts['proof_environment_contract']
    expected = build_proof_environment_contract(repo_root=repo_root)
    checked_artifacts = contract['checked_artifacts']
    command_by_name = {command['name']: command for command in contract['command_contracts']}
    checks = [
        _check('proof_environment_contract_matches_generator', contract == expected, expected, contract),
        _check('proof_environment_contract_schema_is_current', contract['schema'] == PROOF_ENVIRONMENT_CONTRACT_SCHEMA, PROOF_ENVIRONMENT_CONTRACT_SCHEMA, contract['schema']),
        _check('proof_environment_contract_passes_internal_checks', contract['pass'] is True and all(contract['checks'].values()), True, contract['checks']),
        _check('proof_environment_contract_binds_public_headline_result', contract['public_headline_result']['sha256'] == sha256_path(repo_root / contract['public_headline_result']['path']), contract['public_headline_result'], contract['public_headline_result']),
        _check('proof_environment_contract_references_curated_proof_manifest_without_digest_cycle', (repo_root / contract['proof_manifest']['path']).exists() and 'sha256' not in contract['proof_manifest'] and contract['proof_manifest']['file_count'] > 0, 'existing proof manifest path without self-referential sha256 binding', contract['proof_manifest']),
        _check('proof_environment_contract_manifest_covers_checked_artifacts', all(row['manifest_record_present'] and row['manifest_sha256_matches_checked_record'] for row in checked_artifacts.values()), 'all checked artifacts in proof manifest with matching digest and size', checked_artifacts),
        _check('proof_environment_contract_has_no_prover_command_in_fast_gates', all(command['invokes_prover'] is False and '--prove' not in command.get('argv', []) and ' --prove' not in command.get('shell_command', '') for command in contract['command_contracts']), 'no --prove in contract commands', contract['command_contracts']),
        _check('proof_environment_contract_has_publication_freshness_gate', command_by_name['proof_status_publication_gate']['publication_gate'] is True and '--require-all-current' in command_by_name['proof_status_publication_gate']['argv'], 'proof_status.py --require-all-current', command_by_name['proof_status_publication_gate']),
        _check('proof_environment_contract_has_checked_compressed_and_groth16_verifiers', command_by_name['direct_compressed_verify']['publication_gate'] is True and command_by_name['direct_groth16_verify']['publication_gate'] is True and contract['checks']['direct_verify_commands_bind_checked_input_and_proofs'] is True, 'direct checked compressed and Groth16 verify commands', {'compressed': command_by_name['direct_compressed_verify'], 'groth16': command_by_name['direct_groth16_verify']}),
        _check('proof_environment_contract_lists_required_tool_stack', set(contract['tool_contract']['required_tool_names']) == {'python', 'cargo', 'rustc', 'protoc', 'clang', 'go'}, ['cargo', 'clang', 'go', 'protoc', 'python', 'rustc'], sorted(contract['tool_contract']['required_tool_names'])),
    ]
    return _summarize_checks(checks)


def build_proof_publication_status_checks(artifacts: Mapping[str, Any], repo_root: Path) -> Dict[str, Any]:
    status = artifacts['proof_publication_status']
    expected = build_proof_publication_status(repo_root=repo_root)
    proof_status = status['proof_status']
    checks = [
        _check('proof_publication_status_matches_generator', status == expected, expected, status),
        _check('proof_publication_status_schema_is_current', status['schema'] == PROOF_PUBLICATION_STATUS_SCHEMA, PROOF_PUBLICATION_STATUS_SCHEMA, status['schema']),
        _check('proof_publication_status_passes_internal_checks', status['pass'] is True and all(status['checks'].values()), True, status['checks']),
        _check('proof_publication_status_ready_matches_proof_status', status['publication_ready'] == proof_status['all_current'], proof_status['all_current'], status['publication_ready']),
        _check('proof_publication_status_has_blockers_when_stale', status['publication_ready'] or len(status['publication_blockers']) > 0, 'blockers exist when publication_ready is false', status['publication_blockers']),
        _check('proof_publication_status_public_headline_pass_matches_ready', artifacts['public_headline_result']['pass'] == status['publication_ready'], status['publication_ready'], artifacts['public_headline_result']['pass']),
        _check('proof_publication_status_records_compressed_and_groth16_gates', {'public_headline_compressed_verify', 'public_headline_groth16_verify', 'direct_compressed_verify', 'direct_groth16_verify'}.issubset({command['name'] for command in status['publication_gate_commands']}), 'compressed and Groth16 publication gates', [command['name'] for command in status['publication_gate_commands']]),
        _check('proof_publication_status_binds_environment_contract', status['source_artifacts']['proof_environment_contract']['sha256'] == sha256_path(repo_root / status['source_artifacts']['proof_environment_contract']['path']), status['source_artifacts']['proof_environment_contract'], status['source_artifacts']['proof_environment_contract']),
        _check('proof_publication_status_binds_public_headline_result', status['source_artifacts']['public_headline_result']['sha256'] == sha256_path(repo_root / status['source_artifacts']['public_headline_result']['path']), status['source_artifacts']['public_headline_result'], status['source_artifacts']['public_headline_result']),
    ]
    return _summarize_checks(checks)


def build_proof_corpus_profile_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    profiles = artifacts['proof_corpus_profiles']
    expected = build_proof_corpus_profiles()
    selected = profiles['profiles'][profiles['selected_public_profile']]
    release = profiles['profiles'][profiles['release_profile']]
    reusable_public_values = artifacts['zkp_attestation_reusable_chunk_candidate_public_values']
    checks = [
        _check('proof_corpus_profiles_match_generator', profiles == expected, expected, profiles),
        _check('proof_corpus_profiles_schema_is_current', profiles['schema'] == 'compiler-project-proof-corpus-profiles-v1', 'compiler-project-proof-corpus-profiles-v1', profiles['schema']),
        _check('proof_corpus_profiles_pass_internal_checks', profiles['pass'] is True and all(profiles['checks'].values()), True, profiles['checks']),
        _check('proof_corpus_profiles_select_explicit_public_smoke_profile', profiles['selected_public_profile'] == SMOKE_PUBLIC_PROFILE and selected['release_grade'] is False, SMOKE_PUBLIC_PROFILE, {'selected_public_profile': profiles['selected_public_profile'], 'selected': selected}),
        _check('proof_corpus_profiles_track_google_comparable_release_target', profiles['release_profile'] == GOOGLE_COMPARABLE_PROFILE and release['release_grade'] is True and release['case_count'] > selected['case_count'], GOOGLE_COMPARABLE_PROFILE, {'release_profile': profiles['release_profile'], 'release': release}),
        _check('proof_corpus_profiles_match_current_public_candidate_case_count', reusable_public_values['case_count'] == reusable_public_values['passed_case_count'] == selected['case_count'], selected['case_count'], reusable_public_values),
    ]
    return _summarize_checks(checks)


def build_release_corpus_preflight_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    preflight = artifacts['release_corpus_preflight']
    expected = build_release_corpus_preflight(
        leaf=artifacts['streamed_lookup_tail_leaf'],
        proof_corpus_profiles=artifacts['proof_corpus_profiles'],
    )
    release = artifacts['proof_corpus_profiles']['profiles'][artifacts['proof_corpus_profiles']['release_profile']]
    checks = [
        _check('release_corpus_preflight_matches_generator', preflight == expected, expected, preflight),
        _check('release_corpus_preflight_schema_is_current', preflight['schema'] == 'compiler-project-release-corpus-preflight-v1', 'compiler-project-release-corpus-preflight-v1', preflight['schema']),
        _check('release_corpus_preflight_passes_internal_checks', preflight['pass'] is True and all(preflight['checks'].values()), True, preflight['checks']),
        _check('release_corpus_preflight_runs_google_comparable_case_count', preflight['case_count'] == release['case_count'] == GOOGLE_COMPARABLE_CASE_COUNT and preflight['release_grade'] is True, release, {'case_count': preflight['case_count'], 'release_grade': preflight['release_grade']}),
        _check('release_corpus_preflight_covers_forced_edge_categories', set(preflight['category_counts']) == {'accumulator_infinity', 'doubling', 'inverse', 'lookup_infinity', 'random', 'zero_zero'}, 'all forced edge categories plus random', preflight['category_counts']),
        _check('release_corpus_preflight_has_stable_stream_digest', isinstance(preflight['case_stream_sha256'], str) and len(preflight['case_stream_sha256']) == 64, '64 hex chars', preflight['case_stream_sha256']),
    ]
    return _summarize_checks(checks)


def build_public_headline_result_checks(artifacts: Mapping[str, Any], repo_root: Path) -> Dict[str, Any]:
    public_result = artifacts['public_headline_result']
    expected = build_public_headline_result(baseline=PUBLIC_GOOGLE_BASELINE)
    selected = public_result['selected_result']
    checked = public_result['checked_artifacts']
    public_policy = artifacts['compiler_parameters']['primary_strict_headline_policy']
    candidate_input = artifacts['zkp_attestation_reusable_chunk_candidate_input']
    candidate_values = {
        'selected_family_name': candidate_input['selected_family_name'],
        'expected_full_oracle_non_clifford': int(candidate_input['claim_summary']['expected_full_oracle_non_clifford']),
        'expected_total_logical_qubits': int(candidate_input['claim_summary']['expected_total_logical_qubits']),
    }
    checks = [
        _check('public_headline_result_matches_generator', public_result == expected, expected, public_result),
        _check('public_headline_result_schema_is_current', public_result['schema'] == 'compiler-project-public-headline-result-v1', 'compiler-project-public-headline-result-v1', public_result['schema']),
        _check('public_headline_result_pass_flag_matches_internal_checks', public_result['pass'] == all(public_result['checks'].values()), all(public_result['checks'].values()), {'pass': public_result['pass'], 'checks': public_result['checks']}),
        _check('public_headline_result_limits_match_compiler_parameters', public_result['selection_policy']['limits'] == public_policy, public_policy, public_result['selection_policy']['limits']),
        _check('public_headline_result_current_strict_headline_fits_recorded_policy_limits', selected['non_clifford'] < public_policy['non_clifford_limit_exclusive'] and selected['logical_qubits'] < public_policy['logical_qubit_limit_exclusive'], {'strict_limits': public_policy}, selected),
        _check('public_headline_result_records_stale_proof_public_values_mismatch', public_result['pass'] is False and public_result['checks']['public_values_match_input_claim'] is False and selected['non_clifford'] == candidate_values['expected_full_oracle_non_clifford'] and selected['logical_qubits'] == candidate_values['expected_total_logical_qubits'], 'current strict headline records stale checked proof public values', {'candidate_values': candidate_values, 'selected': selected, 'public_values_match_input_claim': public_result['checks']['public_values_match_input_claim']}),
        _check('public_headline_result_compressed_proof_hash_matches_file', checked['compressed_proof']['sha256'] == sha256_path(repo_root / checked['compressed_proof']['path']) and checked['compressed_proof']['bytes'] == (repo_root / checked['compressed_proof']['path']).stat().st_size, checked['compressed_proof'], checked['compressed_proof']),
        _check('public_headline_result_groth16_proof_hash_matches_file', checked['groth16_proof']['sha256'] == sha256_path(repo_root / checked['groth16_proof']['path']) and checked['groth16_proof']['bytes'] == (repo_root / checked['groth16_proof']['path']).stat().st_size, checked['groth16_proof'], checked['groth16_proof']),
        _check('public_headline_result_groth16_vk_hash_matches_file', checked['groth16_verifier_key']['sha256'] == sha256_path(repo_root / checked['groth16_verifier_key']['path']) and checked['groth16_verifier_key']['bytes'] == (repo_root / checked['groth16_verifier_key']['path']).stat().st_size, checked['groth16_verifier_key'], checked['groth16_verifier_key']),
        _check('public_headline_result_is_current_primary_strict_resource_headline', public_result['selection_policy']['role'] == 'current primary strict resource headline', 'current primary strict resource headline', public_result['selection_policy']['role']),
        _check('public_headline_result_binds_verified_reusable_chunk_lowering_status', artifacts['reusable_chunk_lowering']['status'] == 'proven_public_headline', 'proven_public_headline', artifacts['reusable_chunk_lowering']['status']),
    ]
    return _summarize_checks(checks)


def build_strict_replayed_tail_headline_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    observed = artifacts['strict_replayed_tail_headline']
    expected = build_strict_replayed_tail_headline_result(
        tail_macro_engine=artifacts['tail_macro_engine'],
        reusable_chunk_lowering=artifacts['reusable_chunk_lowering'],
        public_headline_result=artifacts['public_headline_result'],
        baseline=PUBLIC_GOOGLE_BASELINE,
    )
    selected = observed['selected_result']
    formula = observed['logical_qubit_formula']
    replay = artifacts['tail_macro_engine']['fused_output_replay_certificate']
    checks = [
        _check('strict_replayed_tail_headline_matches_generator', observed == expected, expected, observed),
        _check('strict_replayed_tail_headline_schema_is_current', observed['schema'] == STRICT_REPLAYED_TAIL_HEADLINE_SCHEMA, STRICT_REPLAYED_TAIL_HEADLINE_SCHEMA, observed['schema']),
        _check('strict_replayed_tail_headline_pass_flag_matches_internal_checks', observed['pass'] == all(observed['checks'].values()), all(observed['checks'].values()), {'pass': observed['pass'], 'checks': observed['checks']}),
        _check('strict_replayed_tail_headline_uses_fused_output_seven_slot_tail', selected['tail_field_slots'] == artifacts['tail_macro_engine']['fused_output_slot_assignment']['peak_field_slots'] == 7 and replay['pass'] is True and replay['owner_capacity_pass'] is True, 'fused-output seven-slot tail with owner capacity pass', {'selected': selected, 'replay': replay}),
        _check('strict_replayed_tail_headline_counts_fused_output_guard_qubit', selected['fused_output_guard_qubits'] == formula['fused_output_guard_qubits'] == artifacts['tail_macro_engine']['fused_output_lowering_contract']['guard_owner_capacity']['logical_qubits'] == 1 and formula['control_qubits'] == artifacts['reusable_chunk_lowering']['qubit_derivation']['control_qubits'] + 1, 'one extra fused-output guard qubit counted in control term', {'selected': selected, 'formula': formula}),
        _check('strict_replayed_tail_headline_total_is_formula_derived', selected['logical_qubits'] == formula['reconstructed_total'] == formula['tail_field_slots'] * formula['field_bits'] + formula['lookup_workspace_qubits'] + formula['control_qubits'] + formula['phase_qubits'], formula['reconstructed_total'], selected['logical_qubits']),
        _check('strict_replayed_tail_headline_demotes_macro_contract', selected['logical_qubits'] > artifacts['public_headline_result']['legacy_wrapper_reference']['selected_result']['logical_qubits'] and observed['macro_contract_reference']['status'] == 'not_primary_strict_headline', 'strict headline exceeds and demotes macro contract', observed['macro_contract_reference']),
    ]
    return _summarize_checks(checks)


def build_primary_strict_result_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    observed = artifacts['primary_strict_result']
    expected = build_primary_strict_result(
        strict_replayed_tail_headline=artifacts['strict_replayed_tail_headline'],
        public_headline_result=artifacts['public_headline_result'],
        engine_completion_audit=artifacts['engine_completion_audit'],
        public_candidate_materialized_circuit_manifest=artifacts['public_candidate_materialized_circuit_manifest'],
        hybrid_bridge_search=artifacts['hybrid_bridge_search'],
    )
    selected = observed['selected_result']
    flat_status = observed['flat_netlist_status']
    checks = [
        _check('primary_strict_result_matches_generator', observed == expected, expected, observed),
        _check('primary_strict_result_schema_is_current', observed['schema'] == PRIMARY_STRICT_RESULT_SCHEMA, PRIMARY_STRICT_RESULT_SCHEMA, observed['schema']),
        _check('primary_strict_result_pass_flag_matches_internal_checks', observed['pass'] == all(observed['checks'].values()), all(observed['checks'].values()), {'pass': observed['pass'], 'checks': observed['checks']}),
        _check('primary_strict_result_selects_strict_replayed_tail_headline', selected == artifacts['strict_replayed_tail_headline']['selected_result'], artifacts['strict_replayed_tail_headline']['selected_result'], selected),
        _check('primary_strict_result_demotes_legacy_macro_wrapper', observed['legacy_wrapper_reference']['status'] == 'legacy_macro_zkp_wrapper_not_primary_resource_headline' and observed['legacy_wrapper_reference']['selected_result'] == artifacts['public_headline_result']['legacy_wrapper_reference']['selected_result'], 'legacy macro wrapper demoted', observed['legacy_wrapper_reference']),
        _check('primary_strict_result_keeps_unclosed_boundaries_explicit', observed['resource_claim_level']['clifford_complete_flat_netlist'] == STRICT_RESOURCE_CLAIM_NOT_YET_ACHIEVED and observed['resource_claim_level']['zkp_binds_this_strict_result'] == STRICT_RESOURCE_CLAIM_NOT_YET_ACHIEVED, 'strict result is not marked fully flattened or ZKP-bound', observed['resource_claim_level']),
        _check('primary_strict_result_flat_netlist_status_binds_strict_not_legacy_totals', flat_status['current_materialized_flat_netlist_binds_selected_strict_result'] is True and flat_status['current_materialized_flat_netlist_binds_legacy_wrapper'] is False and flat_status['peak_live_qubits'] == selected['logical_qubits'] and flat_status['legacy_materialized_flat_netlist_peak_live_qubits'] == artifacts['public_headline_result']['legacy_wrapper_reference']['selected_result']['logical_qubits'], 'flat netlist binds strict totals while legacy wrapper remains separate', flat_status),
        _check('primary_strict_result_binds_strict_capacity_overlay', flat_status['strict_capacity_overlay_binds_selected_result'] is True and flat_status['strict_capacity_peak_qubits'] == selected['logical_qubits'] and flat_status['strict_capacity_overlay_is_full_liveness_rewrite'] is False, 'strict capacity overlay bound but not full liveness rewrite', flat_status),
        _check('primary_strict_result_binds_strict_liveness_projection', flat_status['strict_liveness_projection_binds_selected_result'] is True and flat_status['strict_liveness_projection_peak_qubits'] == selected['logical_qubits'] and flat_status['strict_liveness_projection_is_segment_hashed_flat_netlist'] is True, 'strict liveness projection is bound and segment-hashed', flat_status),
        _check('primary_strict_result_binds_strict_materialized_flat_netlist', flat_status['strict_materialized_flat_netlist_binds_selected_strict_result'] is True and flat_status['strict_materialized_flat_netlist_peak_live_qubits'] == selected['logical_qubits'] and len(flat_status['strict_materialized_flat_netlist_operation_stream_sha256']) == 64 and len(flat_status['strict_materialized_flat_netlist_segment_merkle_root_sha256']) == 64, 'strict materialized flat netlist binds selected strict result', flat_status),
    ]
    return _summarize_checks(checks)


def build_hybrid_bridge_search_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    observed = artifacts['hybrid_bridge_search']
    expected = build_hybrid_bridge_search(
        strict_replayed_tail_headline=artifacts['strict_replayed_tail_headline'],
        reusable_chunk_lowering=artifacts['reusable_chunk_lowering'],
    )
    corrected_affine = observed['corrected_public_envelope']
    strict_budget = observed['strict_qubit_budget_analysis']
    lookup_tradeoff = observed['strict_lookup_chunk_tradeoff_for_six_slots']
    periodic_rows = observed['periodic_normalization_search']['rows']
    five_slot = next(row for row in observed['candidate_rows'] if row['name'] == 'projective_five_slot_no_inverse_core')
    checks = [
        _check('hybrid_bridge_search_matches_generator', observed == expected, expected, observed),
        _check('hybrid_bridge_search_schema_is_current', observed['schema'] == HYBRID_BRIDGE_SEARCH_SCHEMA, HYBRID_BRIDGE_SEARCH_SCHEMA, observed['schema']),
        _check('hybrid_bridge_search_pass_flag_matches_internal_checks', observed['pass'] == all(observed['checks'].values()), all(observed['checks'].values()), {'pass': observed['pass'], 'checks': observed['checks']}),
        _check('hybrid_bridge_search_corrects_public_envelope_free_lane', corrected_affine['listed_register_qubits'] - corrected_affine['claimed_point_add_logical_qubits'] == corrected_affine['missing_field_lane_qubits'] == 256 and corrected_affine['corrected_ecdlp_logical_qubits_with_window_key'] == 1447, 'one 256-bit lane must be counted', corrected_affine),
        _check('hybrid_bridge_search_shows_current_lookup_budget_allows_only_five_slots', strict_budget['max_field_slots_with_current_lookup_workspace'] == 5 and strict_budget['six_slot_required_lookup_workspace_reduction'] > 0, 'strict lookup workspace leaves room for at most five field slots under 1600', strict_budget),
        _check('hybrid_bridge_search_reduced_lookup_six_slot_fails_gate_target', lookup_tradeoff['total_non_clifford_lower_bound'] >= observed['target']['non_clifford_exclusive'] and observed['checks']['six_slot_reduced_lookup_fails_non_clifford_target'] is True, 'six-slot lookup squeeze exceeds non-Clifford target', lookup_tradeoff),
        _check('hybrid_bridge_search_periodic_normalization_has_no_survivor', not any(row['fits_logical_qubit_limit'] and row['fits_non_clifford_limit'] for row in periodic_rows) and observed['checks']['periodic_normalization_has_no_target_fitting_row'] is True, 'no periodic normalization row fits both targets', periodic_rows),
        _check('hybrid_bridge_search_only_survivor_is_unproven_five_slot_core', five_slot['fits_logical_qubit_limit'] is True and five_slot['fits_non_clifford_limit'] is True and five_slot['status'] == 'only_numeric_target_that_would_fit_current_lookup_and_gate_budget', 'five-slot no-inverse projective core remains the required breakthrough', five_slot),
    ]
    return _summarize_checks(checks)


def build_cain_transfer_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    expected = build_cain_transfer_payload(artifacts['family_frontier'])
    checks = [
        _check('cain_transfer_matches_frontier_projection', artifacts['cain_exact_transfer'] == expected, expected, artifacts['cain_exact_transfer']),
    ]
    return _summarize_checks(checks)


def build_azure_seed_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    expected = build_azure_logical_counts_payload(artifacts['family_frontier'])
    observed = artifacts['azure_resource_estimator_logical_counts']
    observed_family_names = [row['family'] for row in observed['families']]
    expected_family_names = [row['family'] for row in expected['families']]
    filtered_runtime_note = 'When qsharp/qdk is unavailable, this artifact is filtered to the subset of families that have checked recorded estimator outputs in the repository.'
    if observed_family_names != expected_family_names or filtered_runtime_note in observed.get('notes', []):
        observed_name_set = set(observed_family_names)
        expected = {
            **expected,
            'families': [row for row in expected['families'] if row['family'] in observed_name_set],
            'notes': [
                *expected['notes'],
                filtered_runtime_note,
            ],
        }
    checks = [
        _check(
            'azure_seed_family_names_are_frontier_subset',
            set(observed_family_names).issubset(set(expected_family_names)),
            sorted(expected_family_names),
            sorted(observed_family_names),
        ),
        _check('azure_seed_matches_frontier_projection', observed == expected, expected, observed),
    ]
    return _summarize_checks(checks)


def build_physical_estimator_target_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    expected = build_azure_estimator_target_payload(artifacts['azure_resource_estimator_logical_counts'])
    checks = [
        _check(
            'physical_estimator_targets_match_expected_profiles',
            artifacts['azure_resource_estimator_targets'] == expected,
            expected,
            artifacts['azure_resource_estimator_targets'],
        ),
    ]
    return _summarize_checks(checks)


def build_physical_estimator_result_checks(artifacts: Mapping[str, Any], repo_root: Path) -> Dict[str, Any]:
    expected = build_or_load_azure_estimator_results_payload(
        logical_counts_payload=artifacts['azure_resource_estimator_logical_counts'],
        target_payload=artifacts['azure_resource_estimator_targets'],
        artifact_path=repo_root / 'compiler_verification_project' / 'artifacts' / 'azure_resource_estimator_results.json',
    )
    results = artifacts['azure_resource_estimator_results']
    target_names = [target['name'] for target in artifacts['azure_resource_estimator_targets']['targets']]
    family_rows = results['families']
    logical_count_family_names = [row['family'] for row in artifacts['azure_resource_estimator_logical_counts']['families']]
    checks = [
        _check(
            'physical_estimator_results_match_recorded_projection',
            results == expected,
            expected,
            results,
        ),
        _check(
            'physical_estimator_result_family_count_matches_logical_counts',
            (
                set(row['family'] for row in family_rows).issubset(set(logical_count_family_names))
                if logical_count_family_names
                else len(family_rows) == len(expected['families'])
            ),
            sorted(logical_count_family_names) if logical_count_family_names else len(expected['families']),
            sorted(row['family'] for row in family_rows) if logical_count_family_names else len(family_rows),
        ),
        _check(
            'physical_estimator_result_target_summary_count_matches_target_profiles',
            len(results['target_summaries']) == len(target_names),
            len(target_names),
            len(results['target_summaries']),
        ),
        _check(
            'physical_estimator_source_bindings_match_input_hashes',
            results['source_bindings'] == expected['source_bindings'],
            expected['source_bindings'],
            results['source_bindings'],
        ),
    ]
    for family in family_rows:
        estimate_targets = [estimate['target'] for estimate in family['estimates']]
        checks.append(
            _check(
                f"physical_estimator_{family['family']}_covers_every_target_exactly_once",
                estimate_targets == target_names,
                target_names,
                estimate_targets,
            )
        )
        best_space = min(
            family['estimates'],
            key=lambda row: (
                row['physical_counts']['physicalQubits'],
                row['physical_counts']['runtime'],
                row['physical_counts']['rqops'],
            ),
        )
        best_runtime = min(
            family['estimates'],
            key=lambda row: (
                row['physical_counts']['runtime'],
                row['physical_counts']['physicalQubits'],
                -row['physical_counts']['rqops'],
            ),
        )
        checks.extend([
            _check(
                f"physical_estimator_{family['family']}_summary_best_space_matches_estimates",
                family['summary']['lowest_physical_qubits_target'] == {
                    'target': best_space['target'],
                    'physical_qubits': best_space['physical_counts']['physicalQubits'],
                    'runtime': best_space['physical_counts']['runtime'],
                },
                {
                    'target': best_space['target'],
                    'physical_qubits': best_space['physical_counts']['physicalQubits'],
                    'runtime': best_space['physical_counts']['runtime'],
                },
                family['summary']['lowest_physical_qubits_target'],
            ),
            _check(
                f"physical_estimator_{family['family']}_summary_best_runtime_matches_estimates",
                family['summary']['fastest_runtime_target'] == {
                    'target': best_runtime['target'],
                    'runtime': best_runtime['physical_counts']['runtime'],
                    'physical_qubits': best_runtime['physical_counts']['physicalQubits'],
                },
                {
                    'target': best_runtime['target'],
                    'runtime': best_runtime['physical_counts']['runtime'],
                    'physical_qubits': best_runtime['physical_counts']['physicalQubits'],
                },
                family['summary']['fastest_runtime_target'],
            ),
        ])
        for estimate in family['estimates']:
            target = next(row for row in artifacts['azure_resource_estimator_targets']['targets'] if row['name'] == estimate['target'])
            checks.extend([
                _check(
                    f"physical_estimator_{family['family']}_{estimate['target']}_requested_params_match_target_profile",
                    estimate['requested_params'] == target['requested_params'],
                    target['requested_params'],
                    estimate['requested_params'],
                ),
                _check(
                    f"physical_estimator_{family['family']}_{estimate['target']}_reported_logical_counts_match_input",
                    estimate['reported_logical_counts'] == family['logical_counts'],
                    family['logical_counts'],
                    estimate['reported_logical_counts'],
                ),
                _check(
                    f"physical_estimator_{family['family']}_{estimate['target']}_physical_qubits_positive",
                    estimate['physical_counts']['physicalQubits'] > 0,
                    '> 0',
                    estimate['physical_counts']['physicalQubits'],
                ),
                _check(
                    f"physical_estimator_{family['family']}_{estimate['target']}_runtime_positive",
                    estimate['physical_counts']['runtime'] > 0,
                    '> 0',
                    estimate['physical_counts']['runtime'],
                ),
                _check(
                    f"physical_estimator_{family['family']}_{estimate['target']}_job_params_qubit_model_matches_target",
                    estimate['job_params']['qubitParams']['name'] == target['requested_params']['qubitParams']['name'],
                    target['requested_params']['qubitParams']['name'],
                    estimate['job_params']['qubitParams']['name'],
                ),
                _check(
                    f"physical_estimator_{family['family']}_{estimate['target']}_job_params_qec_matches_target",
                    estimate['job_params']['qecScheme']['name'] == target['requested_params']['qecScheme']['name'],
                    target['requested_params']['qecScheme']['name'],
                    estimate['job_params']['qecScheme']['name'],
                ),
            ])
    for target_name in target_names:
        target_estimates = [
            next(estimate for estimate in family['estimates'] if estimate['target'] == target_name)
            for family in family_rows
        ]
        best_space = min(
            target_estimates,
            key=lambda row: (
                row['physical_counts']['physicalQubits'],
                row['physical_counts']['runtime'],
                row['physical_counts']['rqops'],
            ),
        )
        best_runtime = min(
            target_estimates,
            key=lambda row: (
                row['physical_counts']['runtime'],
                row['physical_counts']['physicalQubits'],
                -row['physical_counts']['rqops'],
            ),
        )
        summary_row = next(row for row in results['target_summaries'] if row['target'] == target_name)
        checks.extend([
            _check(
                f'physical_estimator_target_{target_name}_summary_best_space_matches_families',
                summary_row['lowest_physical_qubits_family'] == {
                    'family': best_space['family'],
                    'physical_qubits': best_space['physical_counts']['physicalQubits'],
                    'runtime': best_space['physical_counts']['runtime'],
                },
                {
                    'family': best_space['family'],
                    'physical_qubits': best_space['physical_counts']['physicalQubits'],
                    'runtime': best_space['physical_counts']['runtime'],
                },
                summary_row['lowest_physical_qubits_family'],
            ),
            _check(
                f'physical_estimator_target_{target_name}_summary_best_runtime_matches_families',
                summary_row['fastest_runtime_family'] == {
                    'family': best_runtime['family'],
                    'runtime': best_runtime['physical_counts']['runtime'],
                    'physical_qubits': best_runtime['physical_counts']['physicalQubits'],
                },
                {
                    'family': best_runtime['family'],
                    'runtime': best_runtime['physical_counts']['runtime'],
                    'physical_qubits': best_runtime['physical_counts']['physicalQubits'],
                },
                summary_row['fastest_runtime_family'],
            ),
        ])
    return _summarize_checks(checks)


def build_semantic_replay_checks(semantic_replay: Mapping[str, Any], repo_root: Path, random_case_count: int) -> Dict[str, Any]:
    csv_path = repo_root / 'compiler_verification_project' / 'artifacts' / semantic_replay['csv']
    with csv_path.open(newline='') as handle:
        csv_row_count = sum(1 for _ in csv.reader(handle)) - 1
    structured_case_count = len(structured_raw32_cases())
    checks = [
        _check('semantic_replay_passes_all_cases', semantic_replay['summary']['pass'] == semantic_replay['summary']['total'], semantic_replay['summary']['total'], semantic_replay['summary']['pass']),
        _check('semantic_replay_csv_hash_matches_artifact', semantic_replay['sha256'] == sha256_path(csv_path), sha256_path(csv_path), semantic_replay['sha256']),
        _check('semantic_replay_csv_rows_match_summary_total', csv_row_count == semantic_replay['summary']['total'], semantic_replay['summary']['total'], csv_row_count),
        _check('semantic_replay_includes_structured_cases', semantic_replay['summary']['structured_cases'] == structured_case_count, structured_case_count, semantic_replay['summary']['structured_cases']),
        _check('semantic_replay_random_case_count_matches_request', semantic_replay['summary']['random_cases'] == random_case_count, random_case_count, semantic_replay['summary']['random_cases']),
        _check(
            'semantic_replay_summary_total_matches_case_partition',
            semantic_replay['summary']['total'] == semantic_replay['summary']['structured_cases'] + semantic_replay['summary']['random_cases'],
            semantic_replay['summary']['structured_cases'] + semantic_replay['summary']['random_cases'],
            semantic_replay['summary']['total'],
        ),
        _check('semantic_replay_observes_seed_zero_cases', semantic_replay['summary']['seed_zero_cases'] > 0, '> 0', semantic_replay['summary']['seed_zero_cases']),
        _check('semantic_replay_observes_phase_b_zero_cases', semantic_replay['summary']['phase_b_zero_cases'] > 0, '> 0', semantic_replay['summary']['phase_b_zero_cases']),
        _check('semantic_replay_observes_phase_b_nonzero_cases', semantic_replay['summary']['phase_b_nonzero_cases'] > 0, '> 0', semantic_replay['summary']['phase_b_nonzero_cases']),
    ]
    return _summarize_checks(checks)


def build_integrity_report(repo_root: Path, artifacts: Mapping[str, Any], group_names: Sequence[str] | None = None) -> Dict[str, Any]:
    builders = {
        'canonical_public_point_checks': lambda: build_canonical_public_point_checks(artifacts),
        'compiler_parameter_checks': lambda: build_compiler_parameter_checks(artifacts),
        'schedule_checks': lambda: build_schedule_checks(artifacts),
        'table_manifest_checks': lambda: build_table_manifest_checks(artifacts),
        'arithmetic_kernel_checks': lambda: build_arithmetic_kernel_checks(artifacts),
        'arithmetic_operation_ir_checks': lambda: build_arithmetic_operation_ir_checks(artifacts),
        'modular_arithmetic_certificate_checks': lambda: build_modular_arithmetic_certificate_checks(artifacts),
        'tail_macro_engine_checks': lambda: build_tail_macro_engine_checks(artifacts),
        'cleanup_pair_checks': lambda: build_cleanup_pair_checks(artifacts),
        'lookup_lowering_checks': lambda: build_lookup_lowering_checks(artifacts),
        'phase_shell_lowering_checks': lambda: build_phase_shell_lowering_checks(artifacts),
        'generated_block_inventory_checks': lambda: build_generated_block_inventory_checks(artifacts),
        'slot_allocation_checks': lambda: build_slot_allocation_checks(artifacts),
        'lookup_fed_slot_allocation_checks': lambda: build_lookup_fed_slot_allocation_checks(artifacts),
        'streamed_lookup_tail_slot_allocation_checks': lambda: build_streamed_lookup_tail_slot_allocation_checks(artifacts),
        'tail_macro_liveness_checks': lambda: build_tail_macro_liveness_checks(artifacts),
        'tail_macro_reversibility_checks': lambda: build_tail_macro_reversibility_checks(artifacts),
        'tail_macro_schedule_search_checks': lambda: build_tail_macro_schedule_search_checks(artifacts),
        'streamed_lookup_table_multiplier_resource_checks': lambda: build_streamed_lookup_table_multiplier_resource_checks(artifacts),
        'standard_qrom_lookup_assessment_checks': lambda: build_standard_qrom_lookup_assessment_checks(artifacts),
        'logical_resource_ledger_checks': lambda: build_logical_resource_ledger_checks(artifacts),
        'fallback_frontier_stress_checks': lambda: build_fallback_frontier_stress_checks(artifacts),
        'reusable_chunk_tail_candidate_checks': lambda: build_reusable_chunk_tail_candidate_checks(artifacts),
        'qroam_primitive_certificate_checks': lambda: build_qroam_primitive_certificate_checks(artifacts),
        'qroam_reference_crosscheck_checks': lambda: build_qroam_reference_crosscheck_checks(artifacts),
        'qroam_table_cnot_materialization_checks': lambda: build_qroam_table_cnot_materialization_checks(artifacts),
        'reusable_chunk_lowering_checks': lambda: build_reusable_chunk_lowering_checks(artifacts),
        'resource_liveness_certificate_checks': lambda: build_resource_liveness_certificate_checks(artifacts),
        'qubit_breakthrough_checks': lambda: build_qubit_breakthrough_checks(artifacts),
        'full_attack_inventory_checks': lambda: build_full_attack_inventory_checks(artifacts),
        'ft_ir_checks': lambda: build_ft_ir_checks(artifacts, repo_root),
        'whole_oracle_recount_checks': lambda: build_whole_oracle_recount_checks(artifacts, repo_root),
        'subcircuit_equivalence_checks': lambda: build_subcircuit_equivalence_checks(artifacts, repo_root),
        'headline_opcode_coverage_checks': lambda: build_headline_opcode_coverage_checks(artifacts),
        'headline_resource_manifest_checks': lambda: build_headline_resource_manifest_checks(artifacts),
        'public_engine_manifest_checks': lambda: build_public_engine_manifest_checks(artifacts),
        'engine_completion_audit_checks': lambda: build_engine_completion_audit_checks(artifacts),
        'arithmetic_operand_replay_audit_checks': lambda: build_arithmetic_operand_replay_audit_checks(artifacts),
        'constant_provenance_checks': lambda: build_constant_provenance_checks(artifacts, repo_root),
        'primitive_multiplier_checks': lambda: build_primitive_multiplier_checks(artifacts),
        'frontier_checks': lambda: build_frontier_checks(artifacts),
        'build_summary_checks': lambda: build_build_summary_checks(artifacts, repo_root),
        'artifact_digest_tree_checks': lambda: build_artifact_digest_tree_checks(artifacts, repo_root),
        'proof_environment_contract_checks': lambda: build_proof_environment_contract_checks(artifacts, repo_root),
        'proof_publication_status_checks': lambda: build_proof_publication_status_checks(artifacts, repo_root),
        'proof_corpus_profile_checks': lambda: build_proof_corpus_profile_checks(artifacts),
        'release_corpus_preflight_checks': lambda: build_release_corpus_preflight_checks(artifacts),
        'public_headline_result_checks': lambda: build_public_headline_result_checks(artifacts, repo_root),
        'strict_replayed_tail_headline_checks': lambda: build_strict_replayed_tail_headline_checks(artifacts),
        'primary_strict_result_checks': lambda: build_primary_strict_result_checks(artifacts),
        'hybrid_bridge_search_checks': lambda: build_hybrid_bridge_search_checks(artifacts),
        'cain_transfer_checks': lambda: build_cain_transfer_checks(artifacts),
        'azure_seed_checks': lambda: build_azure_seed_checks(artifacts),
        'physical_estimator_target_checks': lambda: build_physical_estimator_target_checks(artifacts),
        'physical_estimator_result_checks': lambda: build_physical_estimator_result_checks(artifacts, repo_root),
    }
    selected_names = list(builders) if group_names is None else list(group_names)
    return {name: builders[name]() for name in selected_names}


VERIFICATION_SUMMARY_SCHEMA = 'compiler-project-verification-summary-v13'


def _compose_verification_summary(
    *,
    repo_root: Path,
    artifacts: Mapping[str, Any],
    semantic: Mapping[str, Any],
    case_count: int,
) -> Dict[str, Any]:
    integrity = build_integrity_report(repo_root, artifacts)
    semantic_checks = build_semantic_replay_checks(semantic, repo_root, case_count)
    invariant_groups = {
        **integrity,
        'semantic_replay_checks': semantic_checks,
    }
    invariant_total = sum(group['total'] for group in invariant_groups.values())
    invariant_pass = sum(group['pass'] for group in invariant_groups.values())
    return {
        'schema': VERIFICATION_SUMMARY_SCHEMA,
        'semantic_replay': semantic,
        **invariant_groups,
        'summary': {
            'semantic_cases': {
                'total': semantic['summary']['total'],
                'pass': semantic['summary']['pass'],
            },
            'invariant_checks': {
                'total': invariant_total,
                'pass': invariant_pass,
            },
            'total': semantic['summary']['total'] + invariant_total,
            'pass': semantic['summary']['pass'] + invariant_pass,
        },
    }


def build_verification_summary(case_count: int = 16, repo_root: Path | None = None) -> Dict[str, Any]:
    effective_root = repo_root or Path(__file__).resolve().parents[2]
    artifacts = load_compiler_artifacts(effective_root)
    semantic = run_full_raw32_semantic_check(case_count=case_count)
    return _compose_verification_summary(
        repo_root=effective_root,
        artifacts=artifacts,
        semantic=semantic,
        case_count=case_count,
    )


def build_verification_summary_with_checked_semantic(repo_root: Path | None = None) -> Dict[str, Any]:
    effective_root = repo_root or Path(__file__).resolve().parents[2]
    summary_path = effective_root / 'compiler_verification_project' / 'artifacts' / 'verification_summary.json'
    existing = load_json(summary_path)
    semantic = existing['semantic_replay']
    case_count = int(semantic['summary']['random_cases'])
    artifacts = load_compiler_artifacts(effective_root)
    return _compose_verification_summary(
        repo_root=effective_root,
        artifacts=artifacts,
        semantic=semantic,
        case_count=case_count,
    )


def _summary_groups(summary: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    return {
        name: group
        for name, group in summary.items()
        if isinstance(group, Mapping) and 'checks' in group
    }


def _refresh_summary_totals(summary: Dict[str, Any]) -> Dict[str, Any]:
    semantic = summary['semantic_replay']
    invariant_groups = _summary_groups(summary)
    invariant_total = sum(group['total'] for group in invariant_groups.values())
    invariant_pass = sum(group['pass'] for group in invariant_groups.values())
    summary['summary'] = {
        'semantic_cases': {
            'total': semantic['summary']['total'],
            'pass': semantic['summary']['pass'],
        },
        'invariant_checks': {
            'total': invariant_total,
            'pass': invariant_pass,
        },
        'total': semantic['summary']['total'] + invariant_total,
        'pass': semantic['summary']['pass'] + invariant_pass,
    }
    return summary


def refresh_verification_summary_groups(
    group_names: Sequence[str],
    repo_root: Path | None = None,
) -> Dict[str, Any]:
    effective_root = repo_root or Path(__file__).resolve().parents[2]
    summary_path = effective_root / 'compiler_verification_project' / 'artifacts' / 'verification_summary.json'
    existing = load_json(summary_path)
    semantic = existing['semantic_replay']
    case_count = int(semantic['summary']['random_cases'])
    artifacts = load_compiler_artifacts(effective_root)
    refreshed = build_integrity_report(effective_root, artifacts, group_names=group_names)
    refreshed['semantic_replay_checks'] = build_semantic_replay_checks(semantic, effective_root, case_count)
    updated = dict(existing)
    updated['schema'] = VERIFICATION_SUMMARY_SCHEMA
    updated.update(refreshed)
    _refresh_summary_totals(updated)
    dump_json(summary_path, updated)
    return updated


def write_verification_summary(case_count: int = 16, repo_root: Path | None = None) -> Dict[str, Any]:
    effective_root = repo_root or Path(__file__).resolve().parents[2]
    summary = build_verification_summary(case_count=case_count, repo_root=effective_root)
    dump_json(effective_root / 'compiler_verification_project' / 'artifacts' / 'verification_summary.json', summary)
    return summary


def refresh_verification_summary_integrity(repo_root: Path | None = None) -> Dict[str, Any]:
    effective_root = repo_root or Path(__file__).resolve().parents[2]
    summary = build_verification_summary_with_checked_semantic(repo_root=effective_root)
    dump_json(effective_root / 'compiler_verification_project' / 'artifacts' / 'verification_summary.json', summary)
    return summary


def evaluate_mutated_verification_groups(
    artifacts: Mapping[str, Any],
    repo_root: Path | None = None,
    group_names: Sequence[str] | None = None,
) -> Dict[str, Any]:
    effective_root = repo_root or Path(__file__).resolve().parents[2]
    normalized = deepcopy(dict(artifacts))
    return build_integrity_report(effective_root, normalized, group_names=group_names)


__all__ = [
    'build_verification_summary',
    'build_verification_summary_with_checked_semantic',
    'write_verification_summary',
    'refresh_verification_summary_groups',
    'refresh_verification_summary_integrity',
    'load_compiler_artifacts',
    'evaluate_mutated_verification_groups',
]
