#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / 'compiler_verification_project' / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
ROOT_SRC = PROJECT_ROOT / 'src'
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))

from baselines import load_public_google_baseline_lines  # noqa: E402
from common import dump_json, load_json  # noqa: E402
from artifact_digest_tree import build_artifact_digest_tree  # noqa: E402
from artifact_registry import BUILD_SUMMARY_ARTIFACT_PATHS, BUILD_SUMMARY_SCHEMA  # noqa: E402
from arithmetic_operation_ir import build_arithmetic_operation_ir  # noqa: E402
from constant_provenance import build_constant_provenance  # noqa: E402
from engine_completion_audit import build_engine_completion_audit  # noqa: E402
from headline_opcode_coverage import build_headline_opcode_coverage  # noqa: E402
from headline_resource_manifest import build_headline_resource_manifest  # noqa: E402
from hybrid_bridge_search import build_hybrid_bridge_search  # noqa: E402
from materialized_circuit import build_arithmetic_operand_replay_audit, build_materialized_family_manifest, build_public_candidate_materialized_circuit_manifest  # noqa: E402
from modular_accumulator_capacity_certificate import build_modular_accumulator_capacity_certificate  # noqa: E402
from modular_accumulator_carry_obligations import build_modular_accumulator_carry_obligations  # noqa: E402
from modular_accumulator_carry_save_candidate import build_modular_accumulator_carry_save_candidate  # noqa: E402
from modular_accumulator_full_adder_contract import build_modular_accumulator_full_adder_contract  # noqa: E402
from modular_accumulator_full_adder_liveness import build_modular_accumulator_full_adder_liveness  # noqa: E402
from modular_accumulator_full_adder_stream import build_modular_accumulator_full_adder_stream  # noqa: E402
from modular_accumulator_lowering import build_modular_accumulator_lowering  # noqa: E402
from modular_accumulator_row_stream import build_modular_accumulator_row_stream  # noqa: E402
from modular_accumulator_scratch_schedule import build_modular_accumulator_scratch_schedule  # noqa: E402
from modular_accumulator_semantic_obligations import build_modular_accumulator_semantic_obligations  # noqa: E402
from modular_execution_trace import build_modular_execution_trace  # noqa: E402
from modular_multiplier_lifecycle import build_modular_multiplier_lifecycle  # noqa: E402
from modular_primitive_wire_audit import build_modular_primitive_wire_audit  # noqa: E402
from project import FIELD_BITS, build_all_artifacts, build_resource_stack_artifacts, full_attack_inventory, write_cain_transfer  # noqa: E402
from public_result import write_public_headline_result  # noqa: E402
from qroam_reference_crosscheck import build_qroam_reference_crosscheck  # noqa: E402
from release_corpus_preflight import build_release_corpus_preflight  # noqa: E402
from resource_certificate import build_resource_liveness_certificate  # noqa: E402
from reusable_chunk_lowering import build_reusable_chunk_lowering  # noqa: E402
from scheduled_modular_primitive_netlist import build_scheduled_modular_primitive_netlist  # noqa: E402
from strict_replayed_tail_result import write_strict_replayed_tail_headline_result  # noqa: E402
from subcircuit_equivalence import build_subcircuit_equivalence_artifact  # noqa: E402
from zkp_attestation import write_zkp_attestation_inputs  # noqa: E402
from proof_corpus_profiles import resolve_proof_corpus_profile  # noqa: E402
from proof_environment_contract import build_proof_environment_contract  # noqa: E402
from proof_publication_status import build_proof_publication_status  # noqa: E402
from primary_strict_result import write_primary_strict_result  # noqa: E402
from public_engine_manifest import build_public_engine_manifest  # noqa: E402

BUILD_TARGETS = (
    'all',
    'core-artifacts',
    'build-summary',
    'artifact-digest-tree',
    'proof-environment-contract',
    'proof-publication-status',
    'constant-provenance',
    'release-corpus-preflight',
    'materialized-circuit-manifest',
    'public-candidate-materialized-circuit-manifest',
    'arithmetic-operand-replay-audit',
    'modular-execution-trace',
    'scheduled-modular-primitive-netlist',
    'modular-primitive-wire-audit',
    'modular-multiplier-lifecycle',
    'modular-accumulator-lowering',
    'modular-accumulator-row-stream',
    'modular-accumulator-capacity-certificate',
    'modular-accumulator-scratch-schedule',
    'modular-accumulator-semantic-obligations',
    'modular-accumulator-carry-obligations',
    'modular-accumulator-carry-save-candidate',
    'modular-accumulator-full-adder-contract',
    'modular-accumulator-full-adder-stream',
    'modular-accumulator-full-adder-liveness',
    'headline-resource-manifest',
    'public-engine-manifest',
    'engine-completion-audit',
    'arithmetic-operation-ir',
    'resource-liveness-certificate',
    'resource-stack',
    'composition-artifacts',
    'qroam-reference',
    'reusable-chunk-resource',
    'zkp',
    'candidate-zkp',
    'release-candidate-zkp',
    'public-headline',
    'strict-replayed-tail-headline',
    'primary-strict-result',
    'hybrid-bridge-search',
    'zkp-and-public',
    'resource-zkp-and-public',
)


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: object) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def build_candidate_zkp() -> None:
    candidate_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts' / 'zkp_attestation_reusable_chunk_candidate'
    write_zkp_attestation_inputs(
        family_name='reusable-chunk',
        output_dir=candidate_dir,
    )


def build_release_candidate_zkp() -> None:
    candidate_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts' / 'zkp_attestation_release_candidate'
    profile = resolve_proof_corpus_profile('release')
    write_zkp_attestation_inputs(
        family_name='reusable-chunk',
        case_count=int(profile['case_count']),
        case_start=int(profile['case_start']),
        output_dir=candidate_dir,
    )


def build_public_headline() -> None:
    write_public_headline_result(
        baseline=load_public_google_baseline_lines(),
    )


def build_strict_replayed_tail_headline() -> None:
    write_strict_replayed_tail_headline_result(
        baseline=load_public_google_baseline_lines(),
    )


def build_primary_strict_result_artifact() -> None:
    write_primary_strict_result()


def build_hybrid_bridge_search_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    dump_json(
        artifact_dir / 'hybrid_bridge_search.json',
        build_hybrid_bridge_search(
            strict_replayed_tail_headline=load_json(artifact_dir / 'strict_replayed_tail_headline.json'),
            reusable_chunk_lowering=load_json(artifact_dir / 'reusable_chunk_lowering.json'),
        ),
    )


def build_reusable_chunk_resource() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    payload = build_reusable_chunk_lowering(
        reusable_chunk_tail_candidate=load_json(artifact_dir / 'reusable_chunk_tail_candidate.json'),
        fallback_frontier_stress=load_json(artifact_dir / 'fallback_frontier_stress.json'),
        logical_resource_ledger=load_json(artifact_dir / 'logical_resource_ledger.json'),
        arithmetic_lowerings=load_json(artifact_dir / 'arithmetic_lowerings.json'),
        qroam_primitive_certificate=load_json(artifact_dir / 'qroam_primitive_certificate.json'),
        qroam_reference_crosscheck=load_json(artifact_dir / 'qroam_reference_crosscheck.json'),
        modular_arithmetic_certificate=load_json(artifact_dir / 'modular_arithmetic_certificate.json'),
        field_bits=FIELD_BITS,
    )
    dump_json(artifact_dir / 'reusable_chunk_lowering.json', payload)


def build_resource_stack() -> dict:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    payload = build_resource_stack_artifacts()
    path_by_key = {
        'arithmetic_lowerings': 'arithmetic_lowerings.json',
        'tail_macro_engine': 'tail_macro_engine.json',
        'arithmetic_operation_ir': 'arithmetic_operation_ir.json',
        'modular_arithmetic_certificate': 'modular_arithmetic_certificate.json',
        'streamed_lookup_table_multiplier_resource': 'streamed_lookup_table_multiplier_resource.json',
        'module_library': 'module_library.json',
        'generated_block_inventories': 'generated_block_inventories.json',
        'ft_ir_compositions': 'ft_ir_compositions.json',
        'whole_oracle_recount': 'whole_oracle_recount.json',
        'frontier': 'family_frontier.json',
        'logical_resource_ledger': 'logical_resource_ledger.json',
        'fallback_frontier_stress': 'fallback_frontier_stress.json',
        'reusable_chunk_tail_candidate': 'reusable_chunk_tail_candidate.json',
        'qroam_primitive_certificate': 'qroam_primitive_certificate.json',
        'qroam_reference_crosscheck': 'qroam_reference_crosscheck.json',
        'qroam_table_cnot_materialization': 'qroam_table_cnot_materialization.json',
        'reusable_chunk_lowering': 'reusable_chunk_lowering.json',
        'phase_shell_lowerings': 'phase_shell_lowerings.json',
        'phase_shell_families': 'phase_shell_families.json',
    }
    for key, filename in path_by_key.items():
        source_key = 'arithmetic_kernel_library' if key == 'module_library' else key
        dump_json(artifact_dir / filename, payload[source_key])
    return {
        key: f'compiler_verification_project/artifacts/{filename}'
        for key, filename in path_by_key.items()
    }


def build_arithmetic_operation_ir_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    lowerings = load_json(artifact_dir / 'arithmetic_lowerings.json')
    leaf_histogram = lowerings['leaf_reconstruction']['leaf_opcode_histogram']
    dump_json(
        artifact_dir / 'arithmetic_operation_ir.json',
        build_arithmetic_operation_ir(
            arithmetic_lowerings=lowerings,
            leaf_opcode_histogram=leaf_histogram,
        ),
    )


def build_resource_liveness_certificate_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    payload = build_resource_liveness_certificate(
        frontier=load_json(artifact_dir / 'family_frontier.json'),
        streamed_lookup_tail_slot_allocation=load_json(artifact_dir / 'streamed_lookup_tail_leaf_slot_allocation.json'),
        arithmetic_lowerings=load_json(artifact_dir / 'arithmetic_lowerings.json'),
        arithmetic_operation_ir=load_json(artifact_dir / 'arithmetic_operation_ir.json'),
        streamed_lookup_resource=load_json(artifact_dir / 'streamed_lookup_table_multiplier_resource.json'),
        logical_resource_ledger=load_json(artifact_dir / 'logical_resource_ledger.json'),
        ft_ir_compositions=load_json(artifact_dir / 'ft_ir_compositions.json'),
        phase_shell_lowerings=load_json(artifact_dir / 'phase_shell_lowerings.json'),
        materialized_circuit_manifest=load_json(artifact_dir / 'materialized_circuit_manifest.json'),
        field_bits=FIELD_BITS,
    )
    dump_json(artifact_dir / 'resource_liveness_certificate.json', payload)


def build_qroam_reference() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    payload = build_qroam_reference_crosscheck(
        qroam_primitive_certificate=load_json(artifact_dir / 'qroam_primitive_certificate.json'),
        logical_resource_ledger=load_json(artifact_dir / 'logical_resource_ledger.json'),
    )
    dump_json(artifact_dir / 'qroam_reference_crosscheck.json', payload)


def build_composition_artifacts() -> dict:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    generated_block_inventories = load_json(artifact_dir / 'generated_block_inventories.json')
    frontier = load_json(artifact_dir / 'family_frontier.json')
    full_inventory = full_attack_inventory(
        frontier=frontier,
        generated_block_inventories=generated_block_inventories,
    )
    dump_json(artifact_dir / 'full_attack_inventory.json', full_inventory)
    subcircuit = build_subcircuit_equivalence_artifact(
        arithmetic_lowerings=load_json(artifact_dir / 'arithmetic_lowerings.json'),
        lookup_lowerings=load_json(artifact_dir / 'lookup_lowerings.json'),
        generated_block_inventories=generated_block_inventories,
        frontier=frontier,
        full_attack_inventory=full_inventory,
    )
    dump_json(artifact_dir / 'subcircuit_equivalence.json', subcircuit)
    headline = build_headline_opcode_coverage(
        leaf=load_json(artifact_dir / 'streamed_lookup_tail_leaf.json'),
        streamed_lookup_tail_leaf_equivalence=load_json(artifact_dir / 'streamed_lookup_tail_leaf_equivalence.json'),
        subcircuit_equivalence=subcircuit,
        arithmetic_lowerings=load_json(artifact_dir / 'arithmetic_lowerings.json'),
        resource_liveness_certificate=load_json(artifact_dir / 'resource_liveness_certificate.json'),
    )
    dump_json(artifact_dir / 'headline_opcode_coverage.json', headline)
    return {
        'full_attack_inventory': 'compiler_verification_project/artifacts/full_attack_inventory.json',
        'subcircuit_equivalence': 'compiler_verification_project/artifacts/subcircuit_equivalence.json',
        'headline_opcode_coverage': 'compiler_verification_project/artifacts/headline_opcode_coverage.json',
    }


def build_digest_tree() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    dump_json(artifact_dir / 'artifact_digest_tree.json', build_artifact_digest_tree(repo_root=PROJECT_ROOT))


def build_proof_environment_contract_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    payload = build_proof_environment_contract(repo_root=PROJECT_ROOT)
    dump_json(artifact_dir / 'proof_environment_contract.json', payload)


def build_proof_publication_status_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    payload = build_proof_publication_status(repo_root=PROJECT_ROOT)
    dump_json(artifact_dir / 'proof_publication_status.json', payload)


def build_constant_provenance_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    payload = build_constant_provenance(
        repo_root=PROJECT_ROOT,
        compiler_parameters=load_json(artifact_dir / 'compiler_parameters.json'),
        phase_shell_lowerings=load_json(artifact_dir / 'phase_shell_lowerings.json'),
        reusable_chunk_lowering=load_json(artifact_dir / 'reusable_chunk_lowering.json'),
        zkp_attestation_input=load_json(artifact_dir / 'zkp_attestation_reusable_chunk_candidate' / 'zkp_attestation_input.json'),
        public_headline_result=load_json(artifact_dir / 'public_headline_result.json'),
        headline_resource_manifest=load_json(artifact_dir / 'headline_resource_manifest.json'),
    )
    dump_json(artifact_dir / 'constant_provenance.json', payload)


def build_release_corpus_preflight_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    payload = build_release_corpus_preflight(
        leaf=load_json(artifact_dir / 'streamed_lookup_tail_leaf.json'),
        proof_corpus_profiles=load_json(artifact_dir / 'proof_corpus_profiles.json'),
    )
    dump_json(artifact_dir / 'release_corpus_preflight.json', payload)


def build_materialized_circuit_manifest_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    frontier = load_json(artifact_dir / 'family_frontier.json')
    payload = build_materialized_family_manifest(
        frontier['best_qubit_family']['name'],
        frontier=frontier,
    )
    dump_json(artifact_dir / 'materialized_circuit_manifest.json', payload)


def build_public_candidate_materialized_circuit_manifest_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    compiler_parameters = load_json(artifact_dir / 'compiler_parameters.json')
    reusable_chunk_lowering = load_json(artifact_dir / 'reusable_chunk_lowering.json')
    arithmetic_operation_ir = load_json(artifact_dir / 'arithmetic_operation_ir.json')
    lookup_lowerings = load_json(artifact_dir / 'lookup_lowerings.json')
    qroam_primitive_certificate = load_json(artifact_dir / 'qroam_primitive_certificate.json')
    qroam_table_cnot_materialization = load_json(artifact_dir / 'qroam_table_cnot_materialization.json')
    phase_shell_lowerings = load_json(artifact_dir / 'phase_shell_lowerings.json')
    modular_arithmetic_certificate = load_json(artifact_dir / 'modular_arithmetic_certificate.json')
    source_digests = {
        'reusable_chunk_lowering_sha256': _sha256_payload(reusable_chunk_lowering),
        'counted_resource_ir_sha256': reusable_chunk_lowering['executable_resource_engine']['counted_resource_ir_sha256'],
        'arithmetic_operation_ir_sha256': _sha256_payload(arithmetic_operation_ir),
        'lookup_lowerings_sha256': _sha256_payload(lookup_lowerings),
        'qroam_primitive_certificate_sha256': _sha256_payload(qroam_primitive_certificate),
        'phase_shell_lowerings_sha256': _sha256_payload(phase_shell_lowerings),
        'compiler_parameters_sha256': _sha256_payload(compiler_parameters),
        'strict_replayed_tail_headline_sha256': _sha256_payload(load_json(artifact_dir / 'strict_replayed_tail_headline.json')),
        'tail_macro_engine_sha256': _sha256_payload(load_json(artifact_dir / 'tail_macro_engine.json')),
        'modular_arithmetic_certificate_sha256': _sha256_payload(modular_arithmetic_certificate),
    }
    existing_path = artifact_dir / 'public_candidate_materialized_circuit_manifest.json'
    materialized_flat_netlist_override = None
    strict_materialized_flat_netlist_override = None
    if existing_path.exists():
        existing = load_json(existing_path)
        existing_flat = existing.get('materialized_flat_netlist')
        existing_strict_flat = existing.get('strict_replayed_tail_materialized_flat_netlist')
        lightweight_payload = build_public_candidate_materialized_circuit_manifest(
            reusable_chunk_lowering=reusable_chunk_lowering,
            arithmetic_operation_ir=arithmetic_operation_ir,
            lookup_lowerings=lookup_lowerings,
            qroam_primitive_certificate=qroam_primitive_certificate,
            qroam_table_cnot_materialization=qroam_table_cnot_materialization,
            phase_shell_lowerings=phase_shell_lowerings,
            compiler_parameters=compiler_parameters,
            selected_family_name=compiler_parameters['public_headline_policy']['selected_public_family_name'],
            include_materialized_flat_netlist=False,
            strict_replayed_tail_headline=load_json(artifact_dir / 'strict_replayed_tail_headline.json'),
            tail_macro_engine=load_json(artifact_dir / 'tail_macro_engine.json'),
            modular_arithmetic_certificate=modular_arithmetic_certificate,
        )
        if (
            existing.get('operation_stream_sha256') == lightweight_payload['operation_stream_sha256']
            and existing.get('liveness_binding_stream_sha256') == lightweight_payload['liveness_binding_stream_sha256']
            and isinstance(existing_flat, dict)
            and existing_flat.get('exact_operation_stream_materialized') is True
        ):
            materialized_flat_netlist_override = existing_flat
        if (
            existing.get('operation_stream_sha256') == lightweight_payload['operation_stream_sha256']
            and existing.get('strict_replayed_tail_liveness_projection', {}).get('liveness_binding_stream_sha256') == lightweight_payload.get('strict_replayed_tail_liveness_projection', {}).get('liveness_binding_stream_sha256')
            and isinstance(existing_strict_flat, dict)
            and existing_strict_flat.get('exact_operation_stream_materialized') is True
        ):
            strict_materialized_flat_netlist_override = existing_strict_flat
    payload = build_public_candidate_materialized_circuit_manifest(
        reusable_chunk_lowering=reusable_chunk_lowering,
        arithmetic_operation_ir=arithmetic_operation_ir,
        lookup_lowerings=lookup_lowerings,
        qroam_primitive_certificate=qroam_primitive_certificate,
        qroam_table_cnot_materialization=qroam_table_cnot_materialization,
        phase_shell_lowerings=phase_shell_lowerings,
        compiler_parameters=compiler_parameters,
        selected_family_name=compiler_parameters['public_headline_policy']['selected_public_family_name'],
        materialized_flat_netlist_override=materialized_flat_netlist_override,
        strict_materialized_flat_netlist_override=strict_materialized_flat_netlist_override,
        strict_replayed_tail_headline=load_json(artifact_dir / 'strict_replayed_tail_headline.json'),
        tail_macro_engine=load_json(artifact_dir / 'tail_macro_engine.json'),
        modular_arithmetic_certificate=modular_arithmetic_certificate,
    )
    dump_json(artifact_dir / 'public_candidate_materialized_circuit_manifest.json', payload)


def build_arithmetic_operand_replay_audit_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    dump_json(
        artifact_dir / 'arithmetic_operand_replay_audit.json',
        build_arithmetic_operand_replay_audit(
            public_candidate_materialized_circuit_manifest=load_json(artifact_dir / 'public_candidate_materialized_circuit_manifest.json'),
            arithmetic_lowerings=load_json(artifact_dir / 'arithmetic_lowerings.json'),
            arithmetic_operation_ir=load_json(artifact_dir / 'arithmetic_operation_ir.json'),
        ),
    )


def build_modular_execution_trace_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    dump_json(
        artifact_dir / 'modular_execution_trace.json',
        build_modular_execution_trace(
            tail_macro_engine=load_json(artifact_dir / 'tail_macro_engine.json'),
            modular_arithmetic_certificate=load_json(artifact_dir / 'modular_arithmetic_certificate.json'),
            public_candidate_materialized_circuit_manifest=load_json(artifact_dir / 'public_candidate_materialized_circuit_manifest.json'),
        ),
    )


def build_scheduled_modular_primitive_netlist_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    dump_json(
        artifact_dir / 'scheduled_modular_primitive_netlist.json',
        build_scheduled_modular_primitive_netlist(
            modular_execution_trace=load_json(artifact_dir / 'modular_execution_trace.json'),
            modular_arithmetic_certificate=load_json(artifact_dir / 'modular_arithmetic_certificate.json'),
            arithmetic_lowerings=load_json(artifact_dir / 'arithmetic_lowerings.json'),
            reusable_chunk_lowering=load_json(artifact_dir / 'reusable_chunk_lowering.json'),
        ),
    )


def build_modular_primitive_wire_audit_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    dump_json(
        artifact_dir / 'modular_primitive_wire_audit.json',
        build_modular_primitive_wire_audit(
            modular_execution_trace=load_json(artifact_dir / 'modular_execution_trace.json'),
            modular_arithmetic_certificate=load_json(artifact_dir / 'modular_arithmetic_certificate.json'),
            arithmetic_lowerings=load_json(artifact_dir / 'arithmetic_lowerings.json'),
            reusable_chunk_lowering=load_json(artifact_dir / 'reusable_chunk_lowering.json'),
            scheduled_modular_primitive_netlist=load_json(artifact_dir / 'scheduled_modular_primitive_netlist.json'),
        ),
    )


def build_modular_multiplier_lifecycle_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    dump_json(
        artifact_dir / 'modular_multiplier_lifecycle.json',
        build_modular_multiplier_lifecycle(
            modular_execution_trace=load_json(artifact_dir / 'modular_execution_trace.json'),
            modular_arithmetic_certificate=load_json(artifact_dir / 'modular_arithmetic_certificate.json'),
            arithmetic_lowerings=load_json(artifact_dir / 'arithmetic_lowerings.json'),
            reusable_chunk_lowering=load_json(artifact_dir / 'reusable_chunk_lowering.json'),
            scheduled_modular_primitive_netlist=load_json(artifact_dir / 'scheduled_modular_primitive_netlist.json'),
            modular_primitive_wire_audit=load_json(artifact_dir / 'modular_primitive_wire_audit.json'),
            field_bits=FIELD_BITS,
        ),
    )


def build_modular_accumulator_lowering_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    dump_json(
        artifact_dir / 'modular_accumulator_lowering.json',
        build_modular_accumulator_lowering(
            modular_multiplier_lifecycle=load_json(artifact_dir / 'modular_multiplier_lifecycle.json'),
            field_bits=FIELD_BITS,
        ),
    )


def build_modular_accumulator_row_stream_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    dump_json(
        artifact_dir / 'modular_accumulator_row_stream.json',
        build_modular_accumulator_row_stream(
            modular_multiplier_lifecycle=load_json(artifact_dir / 'modular_multiplier_lifecycle.json'),
            modular_accumulator_lowering=load_json(artifact_dir / 'modular_accumulator_lowering.json'),
            field_bits=FIELD_BITS,
        ),
    )


def build_modular_accumulator_capacity_certificate_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    dump_json(
        artifact_dir / 'modular_accumulator_capacity_certificate.json',
        build_modular_accumulator_capacity_certificate(
            modular_accumulator_row_stream=load_json(artifact_dir / 'modular_accumulator_row_stream.json'),
            field_bits=FIELD_BITS,
        ),
    )


def build_modular_accumulator_scratch_schedule_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    dump_json(
        artifact_dir / 'modular_accumulator_scratch_schedule.json',
        build_modular_accumulator_scratch_schedule(
            modular_multiplier_lifecycle=load_json(artifact_dir / 'modular_multiplier_lifecycle.json'),
            modular_accumulator_capacity_certificate=load_json(artifact_dir / 'modular_accumulator_capacity_certificate.json'),
            field_bits=FIELD_BITS,
        ),
    )


def build_modular_accumulator_semantic_obligations_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    dump_json(
        artifact_dir / 'modular_accumulator_semantic_obligations.json',
        build_modular_accumulator_semantic_obligations(
            modular_accumulator_row_stream=load_json(artifact_dir / 'modular_accumulator_row_stream.json'),
            modular_accumulator_capacity_certificate=load_json(artifact_dir / 'modular_accumulator_capacity_certificate.json'),
            modular_accumulator_scratch_schedule=load_json(artifact_dir / 'modular_accumulator_scratch_schedule.json'),
            field_bits=FIELD_BITS,
        ),
    )


def build_modular_accumulator_carry_obligations_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    dump_json(
        artifact_dir / 'modular_accumulator_carry_obligations.json',
        build_modular_accumulator_carry_obligations(
            modular_accumulator_row_stream=load_json(artifact_dir / 'modular_accumulator_row_stream.json'),
            modular_accumulator_capacity_certificate=load_json(artifact_dir / 'modular_accumulator_capacity_certificate.json'),
            modular_accumulator_semantic_obligations=load_json(artifact_dir / 'modular_accumulator_semantic_obligations.json'),
            field_bits=FIELD_BITS,
        ),
    )


def build_modular_accumulator_carry_save_candidate_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    dump_json(
        artifact_dir / 'modular_accumulator_carry_save_candidate.json',
        build_modular_accumulator_carry_save_candidate(
            modular_accumulator_row_stream=load_json(artifact_dir / 'modular_accumulator_row_stream.json'),
            modular_accumulator_carry_obligations=load_json(artifact_dir / 'modular_accumulator_carry_obligations.json'),
            field_bits=FIELD_BITS,
        ),
    )


def build_modular_accumulator_full_adder_contract_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    dump_json(
        artifact_dir / 'modular_accumulator_full_adder_contract.json',
        build_modular_accumulator_full_adder_contract(
            modular_accumulator_carry_save_candidate=load_json(artifact_dir / 'modular_accumulator_carry_save_candidate.json'),
        ),
    )


def build_modular_accumulator_full_adder_stream_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    dump_json(
        artifact_dir / 'modular_accumulator_full_adder_stream.json',
        build_modular_accumulator_full_adder_stream(
            modular_accumulator_carry_save_candidate=load_json(artifact_dir / 'modular_accumulator_carry_save_candidate.json'),
            modular_accumulator_full_adder_contract=load_json(artifact_dir / 'modular_accumulator_full_adder_contract.json'),
        ),
    )


def build_modular_accumulator_full_adder_liveness_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    dump_json(
        artifact_dir / 'modular_accumulator_full_adder_liveness.json',
        build_modular_accumulator_full_adder_liveness(
            modular_accumulator_carry_save_candidate=load_json(artifact_dir / 'modular_accumulator_carry_save_candidate.json'),
            modular_accumulator_full_adder_stream=load_json(artifact_dir / 'modular_accumulator_full_adder_stream.json'),
        ),
    )


def build_headline_resource_manifest_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    compiler_parameters = load_json(artifact_dir / 'compiler_parameters.json')
    payload = build_headline_resource_manifest(
        reusable_chunk_lowering=load_json(artifact_dir / 'reusable_chunk_lowering.json'),
        selected_family_name=compiler_parameters['public_headline_policy']['selected_public_family_name'],
    )
    dump_json(artifact_dir / 'headline_resource_manifest.json', payload)


def build_public_engine_manifest_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    compiler_parameters = load_json(artifact_dir / 'compiler_parameters.json')
    payload = build_public_engine_manifest(
        reusable_chunk_lowering=load_json(artifact_dir / 'reusable_chunk_lowering.json'),
        reusable_chunk_tail_candidate=load_json(artifact_dir / 'reusable_chunk_tail_candidate.json'),
        streamed_lookup_tail_leaf_equivalence=load_json(artifact_dir / 'streamed_lookup_tail_leaf_equivalence.json'),
        release_corpus_preflight=load_json(artifact_dir / 'release_corpus_preflight.json'),
        compiler_parameters=compiler_parameters,
        arithmetic_operation_ir=load_json(artifact_dir / 'arithmetic_operation_ir.json'),
        qroam_primitive_certificate=load_json(artifact_dir / 'qroam_primitive_certificate.json'),
        qroam_table_cnot_materialization=load_json(artifact_dir / 'qroam_table_cnot_materialization.json'),
        phase_shell_lowerings=load_json(artifact_dir / 'phase_shell_lowerings.json'),
        public_candidate_materialized_circuit_manifest=load_json(artifact_dir / 'public_candidate_materialized_circuit_manifest.json'),
        modular_execution_trace=load_json(artifact_dir / 'modular_execution_trace.json'),
        scheduled_modular_primitive_netlist=load_json(artifact_dir / 'scheduled_modular_primitive_netlist.json'),
        selected_family_name=compiler_parameters['public_headline_policy']['selected_public_family_name'],
    )
    dump_json(artifact_dir / 'public_engine_manifest.json', payload)


def build_engine_completion_audit_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    compiler_parameters = load_json(artifact_dir / 'compiler_parameters.json')
    payload = build_engine_completion_audit(
        public_engine_manifest=load_json(artifact_dir / 'public_engine_manifest.json'),
        public_candidate_materialized_circuit_manifest=load_json(artifact_dir / 'public_candidate_materialized_circuit_manifest.json'),
        arithmetic_operand_replay_audit=load_json(artifact_dir / 'arithmetic_operand_replay_audit.json'),
        reusable_chunk_lowering=load_json(artifact_dir / 'reusable_chunk_lowering.json'),
        arithmetic_operation_ir=load_json(artifact_dir / 'arithmetic_operation_ir.json'),
        lookup_lowerings=load_json(artifact_dir / 'lookup_lowerings.json'),
        qroam_primitive_certificate=load_json(artifact_dir / 'qroam_primitive_certificate.json'),
        qroam_table_cnot_materialization=load_json(artifact_dir / 'qroam_table_cnot_materialization.json'),
        phase_shell_lowerings=load_json(artifact_dir / 'phase_shell_lowerings.json'),
        release_corpus_preflight=load_json(artifact_dir / 'release_corpus_preflight.json'),
        streamed_lookup_tail_leaf_equivalence=load_json(artifact_dir / 'streamed_lookup_tail_leaf_equivalence.json'),
        modular_arithmetic_certificate=load_json(artifact_dir / 'modular_arithmetic_certificate.json'),
        modular_execution_trace=load_json(artifact_dir / 'modular_execution_trace.json'),
        scheduled_modular_primitive_netlist=load_json(artifact_dir / 'scheduled_modular_primitive_netlist.json'),
        modular_primitive_wire_audit=load_json(artifact_dir / 'modular_primitive_wire_audit.json'),
        modular_multiplier_lifecycle=load_json(artifact_dir / 'modular_multiplier_lifecycle.json'),
        modular_accumulator_lowering=load_json(artifact_dir / 'modular_accumulator_lowering.json'),
        modular_accumulator_row_stream=load_json(artifact_dir / 'modular_accumulator_row_stream.json'),
        modular_accumulator_capacity_certificate=load_json(artifact_dir / 'modular_accumulator_capacity_certificate.json'),
        modular_accumulator_scratch_schedule=load_json(artifact_dir / 'modular_accumulator_scratch_schedule.json'),
        modular_accumulator_semantic_obligations=load_json(artifact_dir / 'modular_accumulator_semantic_obligations.json'),
        modular_accumulator_carry_obligations=load_json(artifact_dir / 'modular_accumulator_carry_obligations.json'),
        modular_accumulator_carry_save_candidate=load_json(artifact_dir / 'modular_accumulator_carry_save_candidate.json'),
        modular_accumulator_full_adder_contract=load_json(artifact_dir / 'modular_accumulator_full_adder_contract.json'),
        modular_accumulator_full_adder_stream=load_json(artifact_dir / 'modular_accumulator_full_adder_stream.json'),
        modular_accumulator_full_adder_liveness=load_json(artifact_dir / 'modular_accumulator_full_adder_liveness.json'),
        tail_macro_engine=load_json(artifact_dir / 'tail_macro_engine.json'),
        tail_macro_liveness=load_json(artifact_dir / 'tail_macro_liveness.json'),
        tail_macro_reversibility=load_json(artifact_dir / 'tail_macro_reversibility.json'),
        tail_macro_schedule_search=load_json(artifact_dir / 'tail_macro_schedule_search.json'),
        compiler_parameters=compiler_parameters,
        zkp_attestation_input=load_json(artifact_dir / 'zkp_attestation_reusable_chunk_candidate' / 'zkp_attestation_input.json'),
    )
    dump_json(artifact_dir / 'engine_completion_audit.json', payload)


def build_summary_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    frontier = load_json(artifact_dir / 'family_frontier.json')
    payload = {
        'schema': BUILD_SUMMARY_SCHEMA,
        'artifacts': dict(BUILD_SUMMARY_ARTIFACT_PATHS),
        'headline': {
            'best_gate_family': frontier['best_gate_family'],
            'best_qubit_family': frontier['best_qubit_family'],
            'best_google_low_gate_qubit_family': frontier['best_google_low_gate_qubit_family'],
            'best_sub30m_qubit_family': frontier['best_sub30m_qubit_family'],
            'public_headline_result_artifact': 'compiler_verification_project/artifacts/public_headline_result.json',
            'strict_replayed_tail_headline_artifact': 'compiler_verification_project/artifacts/strict_replayed_tail_headline.json',
            'primary_strict_result_artifact': 'compiler_verification_project/artifacts/primary_strict_result.json',
        },
        'notes': [
            'Targeted build-summary refresh: artifact paths and headline references are read from checked registry and frontier artifacts.',
            'Use --target all for a full compiler artifact rebuild.',
        ],
    }
    dump_json(artifact_dir / 'build_summary.json', payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--target',
        choices=BUILD_TARGETS,
        default='all',
    )
    args = parser.parse_args()
    payload = {}
    if args.target in ('all', 'core-artifacts'):
        payload = build_all_artifacts()
        payload['cain_transfer'] = write_cain_transfer()
    if args.target in ('build-summary',):
        build_summary_artifact()
        payload['build_summary_artifact'] = 'compiler_verification_project/artifacts/build_summary.json'
    if args.target in ('artifact-digest-tree',):
        build_digest_tree()
        payload['artifact_digest_tree'] = 'compiler_verification_project/artifacts/artifact_digest_tree.json'
    if args.target in ('proof-environment-contract',):
        build_proof_environment_contract_artifact()
        payload['proof_environment_contract'] = 'compiler_verification_project/artifacts/proof_environment_contract.json'
    if args.target in ('proof-publication-status',):
        build_proof_publication_status_artifact()
        payload['proof_publication_status'] = 'compiler_verification_project/artifacts/proof_publication_status.json'
    if args.target in ('constant-provenance',):
        build_constant_provenance_artifact()
        payload['constant_provenance'] = 'compiler_verification_project/artifacts/constant_provenance.json'
    if args.target in ('release-corpus-preflight',):
        build_release_corpus_preflight_artifact()
        payload['release_corpus_preflight'] = 'compiler_verification_project/artifacts/release_corpus_preflight.json'
    if args.target in ('materialized-circuit-manifest',):
        build_materialized_circuit_manifest_artifact()
        payload['materialized_circuit_manifest'] = 'compiler_verification_project/artifacts/materialized_circuit_manifest.json'
    if args.target in ('public-candidate-materialized-circuit-manifest',):
        build_public_candidate_materialized_circuit_manifest_artifact()
        payload['public_candidate_materialized_circuit_manifest'] = 'compiler_verification_project/artifacts/public_candidate_materialized_circuit_manifest.json'
    if args.target in ('headline-resource-manifest',):
        build_headline_resource_manifest_artifact()
        payload['headline_resource_manifest'] = 'compiler_verification_project/artifacts/headline_resource_manifest.json'
    if args.target in ('public-engine-manifest',):
        build_modular_execution_trace_artifact()
        payload['modular_execution_trace'] = 'compiler_verification_project/artifacts/modular_execution_trace.json'
        build_scheduled_modular_primitive_netlist_artifact()
        payload['scheduled_modular_primitive_netlist'] = 'compiler_verification_project/artifacts/scheduled_modular_primitive_netlist.json'
        build_modular_primitive_wire_audit_artifact()
        payload['modular_primitive_wire_audit'] = 'compiler_verification_project/artifacts/modular_primitive_wire_audit.json'
        build_modular_multiplier_lifecycle_artifact()
        payload['modular_multiplier_lifecycle'] = 'compiler_verification_project/artifacts/modular_multiplier_lifecycle.json'
        build_modular_accumulator_lowering_artifact()
        payload['modular_accumulator_lowering'] = 'compiler_verification_project/artifacts/modular_accumulator_lowering.json'
        build_modular_accumulator_row_stream_artifact()
        payload['modular_accumulator_row_stream'] = 'compiler_verification_project/artifacts/modular_accumulator_row_stream.json'
        build_modular_accumulator_capacity_certificate_artifact()
        payload['modular_accumulator_capacity_certificate'] = 'compiler_verification_project/artifacts/modular_accumulator_capacity_certificate.json'
        build_modular_accumulator_scratch_schedule_artifact()
        payload['modular_accumulator_scratch_schedule'] = 'compiler_verification_project/artifacts/modular_accumulator_scratch_schedule.json'
        build_modular_accumulator_semantic_obligations_artifact()
        payload['modular_accumulator_semantic_obligations'] = 'compiler_verification_project/artifacts/modular_accumulator_semantic_obligations.json'
        build_modular_accumulator_carry_obligations_artifact()
        payload['modular_accumulator_carry_obligations'] = 'compiler_verification_project/artifacts/modular_accumulator_carry_obligations.json'
        build_modular_accumulator_carry_save_candidate_artifact()
        payload['modular_accumulator_carry_save_candidate'] = 'compiler_verification_project/artifacts/modular_accumulator_carry_save_candidate.json'
        build_modular_accumulator_full_adder_contract_artifact()
        payload['modular_accumulator_full_adder_contract'] = 'compiler_verification_project/artifacts/modular_accumulator_full_adder_contract.json'
        build_modular_accumulator_full_adder_stream_artifact()
        payload['modular_accumulator_full_adder_stream'] = 'compiler_verification_project/artifacts/modular_accumulator_full_adder_stream.json'
        build_modular_accumulator_full_adder_liveness_artifact()
        payload['modular_accumulator_full_adder_liveness'] = 'compiler_verification_project/artifacts/modular_accumulator_full_adder_liveness.json'
        build_public_engine_manifest_artifact()
        payload['public_engine_manifest'] = 'compiler_verification_project/artifacts/public_engine_manifest.json'
    if args.target in ('engine-completion-audit',):
        build_arithmetic_operand_replay_audit_artifact()
        payload['arithmetic_operand_replay_audit'] = 'compiler_verification_project/artifacts/arithmetic_operand_replay_audit.json'
        build_modular_execution_trace_artifact()
        payload['modular_execution_trace'] = 'compiler_verification_project/artifacts/modular_execution_trace.json'
        build_scheduled_modular_primitive_netlist_artifact()
        payload['scheduled_modular_primitive_netlist'] = 'compiler_verification_project/artifacts/scheduled_modular_primitive_netlist.json'
        build_modular_primitive_wire_audit_artifact()
        payload['modular_primitive_wire_audit'] = 'compiler_verification_project/artifacts/modular_primitive_wire_audit.json'
        build_modular_multiplier_lifecycle_artifact()
        payload['modular_multiplier_lifecycle'] = 'compiler_verification_project/artifacts/modular_multiplier_lifecycle.json'
        build_modular_accumulator_lowering_artifact()
        payload['modular_accumulator_lowering'] = 'compiler_verification_project/artifacts/modular_accumulator_lowering.json'
        build_modular_accumulator_row_stream_artifact()
        payload['modular_accumulator_row_stream'] = 'compiler_verification_project/artifacts/modular_accumulator_row_stream.json'
        build_modular_accumulator_capacity_certificate_artifact()
        payload['modular_accumulator_capacity_certificate'] = 'compiler_verification_project/artifacts/modular_accumulator_capacity_certificate.json'
        build_modular_accumulator_scratch_schedule_artifact()
        payload['modular_accumulator_scratch_schedule'] = 'compiler_verification_project/artifacts/modular_accumulator_scratch_schedule.json'
        build_modular_accumulator_semantic_obligations_artifact()
        payload['modular_accumulator_semantic_obligations'] = 'compiler_verification_project/artifacts/modular_accumulator_semantic_obligations.json'
        build_modular_accumulator_carry_obligations_artifact()
        payload['modular_accumulator_carry_obligations'] = 'compiler_verification_project/artifacts/modular_accumulator_carry_obligations.json'
        build_modular_accumulator_carry_save_candidate_artifact()
        payload['modular_accumulator_carry_save_candidate'] = 'compiler_verification_project/artifacts/modular_accumulator_carry_save_candidate.json'
        build_modular_accumulator_full_adder_contract_artifact()
        payload['modular_accumulator_full_adder_contract'] = 'compiler_verification_project/artifacts/modular_accumulator_full_adder_contract.json'
        build_modular_accumulator_full_adder_stream_artifact()
        payload['modular_accumulator_full_adder_stream'] = 'compiler_verification_project/artifacts/modular_accumulator_full_adder_stream.json'
        build_modular_accumulator_full_adder_liveness_artifact()
        payload['modular_accumulator_full_adder_liveness'] = 'compiler_verification_project/artifacts/modular_accumulator_full_adder_liveness.json'
        build_engine_completion_audit_artifact()
        payload['engine_completion_audit'] = 'compiler_verification_project/artifacts/engine_completion_audit.json'
    if args.target in ('resource-stack', 'public-headline', 'zkp-and-public', 'resource-zkp-and-public'):
        payload.update(build_resource_stack())
    if args.target in ('arithmetic-operation-ir',):
        build_arithmetic_operation_ir_artifact()
        payload['arithmetic_operation_ir'] = 'compiler_verification_project/artifacts/arithmetic_operation_ir.json'
    if args.target in ('resource-liveness-certificate',):
        build_resource_liveness_certificate_artifact()
        payload['resource_liveness_certificate'] = 'compiler_verification_project/artifacts/resource_liveness_certificate.json'
    if args.target in ('qroam-reference',):
        build_qroam_reference()
        payload['qroam_reference_crosscheck'] = 'compiler_verification_project/artifacts/qroam_reference_crosscheck.json'
    if args.target in ('composition-artifacts',):
        payload.update(build_composition_artifacts())
    if args.target in ('reusable-chunk-resource',):
        build_reusable_chunk_resource()
        payload['reusable_chunk_lowering'] = 'compiler_verification_project/artifacts/reusable_chunk_lowering.json'
    if args.target in ('all', 'zkp', 'zkp-and-public'):
        payload['zkp_attestation'] = write_zkp_attestation_inputs()
    if args.target in ('candidate-zkp',):
        build_candidate_zkp()
        payload['zkp_attestation_reusable_chunk_candidate'] = 'compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_input.json'
    if args.target in ('all', 'public-headline', 'zkp-and-public', 'resource-zkp-and-public'):
        build_headline_resource_manifest_artifact()
        payload['headline_resource_manifest'] = 'compiler_verification_project/artifacts/headline_resource_manifest.json'
        build_public_candidate_materialized_circuit_manifest_artifact()
        payload['public_candidate_materialized_circuit_manifest'] = 'compiler_verification_project/artifacts/public_candidate_materialized_circuit_manifest.json'
        build_arithmetic_operand_replay_audit_artifact()
        payload['arithmetic_operand_replay_audit'] = 'compiler_verification_project/artifacts/arithmetic_operand_replay_audit.json'
        build_modular_execution_trace_artifact()
        payload['modular_execution_trace'] = 'compiler_verification_project/artifacts/modular_execution_trace.json'
        build_scheduled_modular_primitive_netlist_artifact()
        payload['scheduled_modular_primitive_netlist'] = 'compiler_verification_project/artifacts/scheduled_modular_primitive_netlist.json'
        build_modular_primitive_wire_audit_artifact()
        payload['modular_primitive_wire_audit'] = 'compiler_verification_project/artifacts/modular_primitive_wire_audit.json'
        build_modular_multiplier_lifecycle_artifact()
        payload['modular_multiplier_lifecycle'] = 'compiler_verification_project/artifacts/modular_multiplier_lifecycle.json'
        build_modular_accumulator_lowering_artifact()
        payload['modular_accumulator_lowering'] = 'compiler_verification_project/artifacts/modular_accumulator_lowering.json'
        build_modular_accumulator_row_stream_artifact()
        payload['modular_accumulator_row_stream'] = 'compiler_verification_project/artifacts/modular_accumulator_row_stream.json'
        build_modular_accumulator_capacity_certificate_artifact()
        payload['modular_accumulator_capacity_certificate'] = 'compiler_verification_project/artifacts/modular_accumulator_capacity_certificate.json'
        build_modular_accumulator_scratch_schedule_artifact()
        payload['modular_accumulator_scratch_schedule'] = 'compiler_verification_project/artifacts/modular_accumulator_scratch_schedule.json'
        build_modular_accumulator_semantic_obligations_artifact()
        payload['modular_accumulator_semantic_obligations'] = 'compiler_verification_project/artifacts/modular_accumulator_semantic_obligations.json'
        build_modular_accumulator_carry_obligations_artifact()
        payload['modular_accumulator_carry_obligations'] = 'compiler_verification_project/artifacts/modular_accumulator_carry_obligations.json'
        build_modular_accumulator_carry_save_candidate_artifact()
        payload['modular_accumulator_carry_save_candidate'] = 'compiler_verification_project/artifacts/modular_accumulator_carry_save_candidate.json'
        build_modular_accumulator_full_adder_contract_artifact()
        payload['modular_accumulator_full_adder_contract'] = 'compiler_verification_project/artifacts/modular_accumulator_full_adder_contract.json'
        build_modular_accumulator_full_adder_stream_artifact()
        payload['modular_accumulator_full_adder_stream'] = 'compiler_verification_project/artifacts/modular_accumulator_full_adder_stream.json'
        build_modular_accumulator_full_adder_liveness_artifact()
        payload['modular_accumulator_full_adder_liveness'] = 'compiler_verification_project/artifacts/modular_accumulator_full_adder_liveness.json'
        build_public_engine_manifest_artifact()
        payload['public_engine_manifest'] = 'compiler_verification_project/artifacts/public_engine_manifest.json'
        build_candidate_zkp()
        payload['zkp_attestation_reusable_chunk_candidate'] = 'compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_input.json'
        build_engine_completion_audit_artifact()
        payload['engine_completion_audit'] = 'compiler_verification_project/artifacts/engine_completion_audit.json'
    if args.target in ('release-candidate-zkp',):
        build_release_candidate_zkp()
        payload['zkp_attestation_release_candidate'] = 'compiler_verification_project/artifacts/zkp_attestation_release_candidate/zkp_attestation_input.json'
    if args.target in ('arithmetic-operand-replay-audit',):
        build_arithmetic_operand_replay_audit_artifact()
        payload['arithmetic_operand_replay_audit'] = 'compiler_verification_project/artifacts/arithmetic_operand_replay_audit.json'
    if args.target in ('modular-execution-trace',):
        build_modular_execution_trace_artifact()
        payload['modular_execution_trace'] = 'compiler_verification_project/artifacts/modular_execution_trace.json'
    if args.target in ('scheduled-modular-primitive-netlist',):
        build_scheduled_modular_primitive_netlist_artifact()
        payload['scheduled_modular_primitive_netlist'] = 'compiler_verification_project/artifacts/scheduled_modular_primitive_netlist.json'
    if args.target in ('modular-primitive-wire-audit',):
        build_modular_primitive_wire_audit_artifact()
        payload['modular_primitive_wire_audit'] = 'compiler_verification_project/artifacts/modular_primitive_wire_audit.json'
    if args.target in ('modular-multiplier-lifecycle',):
        build_modular_multiplier_lifecycle_artifact()
        payload['modular_multiplier_lifecycle'] = 'compiler_verification_project/artifacts/modular_multiplier_lifecycle.json'
    if args.target in ('modular-accumulator-lowering',):
        build_modular_accumulator_lowering_artifact()
        payload['modular_accumulator_lowering'] = 'compiler_verification_project/artifacts/modular_accumulator_lowering.json'
    if args.target in ('modular-accumulator-row-stream',):
        build_modular_accumulator_row_stream_artifact()
        payload['modular_accumulator_row_stream'] = 'compiler_verification_project/artifacts/modular_accumulator_row_stream.json'
    if args.target in ('modular-accumulator-capacity-certificate',):
        build_modular_accumulator_capacity_certificate_artifact()
        payload['modular_accumulator_capacity_certificate'] = 'compiler_verification_project/artifacts/modular_accumulator_capacity_certificate.json'
    if args.target in ('modular-accumulator-scratch-schedule',):
        build_modular_accumulator_scratch_schedule_artifact()
        payload['modular_accumulator_scratch_schedule'] = 'compiler_verification_project/artifacts/modular_accumulator_scratch_schedule.json'
    if args.target in ('modular-accumulator-semantic-obligations',):
        build_modular_accumulator_semantic_obligations_artifact()
        payload['modular_accumulator_semantic_obligations'] = 'compiler_verification_project/artifacts/modular_accumulator_semantic_obligations.json'
    if args.target in ('modular-accumulator-carry-obligations',):
        build_modular_accumulator_carry_obligations_artifact()
        payload['modular_accumulator_carry_obligations'] = 'compiler_verification_project/artifacts/modular_accumulator_carry_obligations.json'
    if args.target in ('modular-accumulator-carry-save-candidate',):
        build_modular_accumulator_carry_save_candidate_artifact()
        payload['modular_accumulator_carry_save_candidate'] = 'compiler_verification_project/artifacts/modular_accumulator_carry_save_candidate.json'
    if args.target in ('modular-accumulator-full-adder-contract',):
        build_modular_accumulator_full_adder_contract_artifact()
        payload['modular_accumulator_full_adder_contract'] = 'compiler_verification_project/artifacts/modular_accumulator_full_adder_contract.json'
    if args.target in ('modular-accumulator-full-adder-stream',):
        build_modular_accumulator_full_adder_stream_artifact()
        payload['modular_accumulator_full_adder_stream'] = 'compiler_verification_project/artifacts/modular_accumulator_full_adder_stream.json'
    if args.target in ('modular-accumulator-full-adder-liveness',):
        build_modular_accumulator_full_adder_liveness_artifact()
        payload['modular_accumulator_full_adder_liveness'] = 'compiler_verification_project/artifacts/modular_accumulator_full_adder_liveness.json'
    if args.target in ('all', 'public-headline', 'strict-replayed-tail-headline', 'zkp-and-public', 'resource-zkp-and-public'):
        build_strict_replayed_tail_headline()
        payload['strict_replayed_tail_headline'] = 'compiler_verification_project/artifacts/strict_replayed_tail_headline.json'
    if args.target in ('all', 'public-headline', 'zkp-and-public', 'resource-zkp-and-public'):
        build_public_headline()
        payload['public_headline_result'] = 'compiler_verification_project/artifacts/public_headline_result.json'
    if args.target in ('all', 'hybrid-bridge-search', 'public-headline', 'zkp-and-public', 'resource-zkp-and-public'):
        build_hybrid_bridge_search_artifact()
        payload['hybrid_bridge_search'] = 'compiler_verification_project/artifacts/hybrid_bridge_search.json'
    if args.target in ('all', 'primary-strict-result', 'public-headline', 'zkp-and-public', 'resource-zkp-and-public'):
        build_primary_strict_result_artifact()
        payload['primary_strict_result'] = 'compiler_verification_project/artifacts/primary_strict_result.json'
    if args.target in ('all', 'public-headline', 'zkp-and-public', 'resource-zkp-and-public'):
        build_proof_environment_contract_artifact()
        payload['proof_environment_contract'] = 'compiler_verification_project/artifacts/proof_environment_contract.json'
        build_proof_publication_status_artifact()
        payload['proof_publication_status'] = 'compiler_verification_project/artifacts/proof_publication_status.json'
        build_constant_provenance_artifact()
        payload['constant_provenance'] = 'compiler_verification_project/artifacts/constant_provenance.json'
    print(json.dumps({
        'target': args.target,
        'build_summary': payload['frontier']['best_gate_family'] if isinstance(payload.get('frontier'), dict) else None,
        'build_summary_artifact': payload.get('build_summary_artifact'),
        'artifact_digest_tree': payload.get('artifact_digest_tree'),
        'proof_environment_contract': payload.get('proof_environment_contract'),
        'proof_publication_status': payload.get('proof_publication_status'),
        'constant_provenance': payload.get('constant_provenance'),
        'release_corpus_preflight': payload.get('release_corpus_preflight'),
        'materialized_circuit_manifest': payload.get('materialized_circuit_manifest'),
        'public_candidate_materialized_circuit_manifest': payload.get('public_candidate_materialized_circuit_manifest'),
        'arithmetic_operand_replay_audit': payload.get('arithmetic_operand_replay_audit'),
        'modular_execution_trace': payload.get('modular_execution_trace'),
        'scheduled_modular_primitive_netlist': payload.get('scheduled_modular_primitive_netlist'),
        'modular_primitive_wire_audit': payload.get('modular_primitive_wire_audit'),
        'headline_resource_manifest': payload.get('headline_resource_manifest'),
        'public_engine_manifest': payload.get('public_engine_manifest'),
        'engine_completion_audit': payload.get('engine_completion_audit'),
        'arithmetic_operation_ir': payload.get('arithmetic_operation_ir'),
        'resource_liveness_certificate': payload.get('resource_liveness_certificate'),
        'qroam_reference_crosscheck': payload.get('qroam_reference_crosscheck'),
        'qroam_table_cnot_materialization': payload.get('qroam_table_cnot_materialization'),
        'full_attack_inventory': payload.get('full_attack_inventory'),
        'subcircuit_equivalence': payload.get('subcircuit_equivalence'),
        'headline_opcode_coverage': payload.get('headline_opcode_coverage'),
        'reusable_chunk_lowering': payload.get('reusable_chunk_lowering'),
        'public_headline_result': payload.get('public_headline_result'),
        'strict_replayed_tail_headline': payload.get('strict_replayed_tail_headline'),
        'primary_strict_result': payload.get('primary_strict_result'),
        'hybrid_bridge_search': payload.get('hybrid_bridge_search'),
        'zkp_attestation_input': 'compiler_verification_project/artifacts/zkp_attestation_input.json' if 'zkp_attestation' in payload else None,
        'zkp_attestation_reusable_chunk_candidate_input': payload.get('zkp_attestation_reusable_chunk_candidate'),
        'zkp_attestation_release_candidate_input': payload.get('zkp_attestation_release_candidate'),
        'artifact_dir': 'compiler_verification_project/artifacts',
    }, indent=2))


if __name__ == '__main__':
    main()
