#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
from project import FIELD_BITS, build_all_artifacts, build_resource_stack_artifacts, write_cain_transfer  # noqa: E402
from public_result import write_public_headline_result  # noqa: E402
from qroam_reference_crosscheck import build_qroam_reference_crosscheck  # noqa: E402
from release_corpus_preflight import build_release_corpus_preflight  # noqa: E402
from resource_certificate import build_resource_liveness_certificate  # noqa: E402
from reusable_chunk_lowering import build_reusable_chunk_lowering  # noqa: E402
from zkp_attestation import write_zkp_attestation_inputs  # noqa: E402


def build_candidate_zkp() -> None:
    candidate_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts' / 'zkp_attestation_reusable_chunk_candidate'
    write_zkp_attestation_inputs(
        family_name='reusable-chunk',
        output_dir=candidate_dir,
    )


def build_public_headline() -> None:
    write_public_headline_result(
        baseline=load_public_google_baseline_lines(),
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


def build_digest_tree() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    dump_json(artifact_dir / 'artifact_digest_tree.json', build_artifact_digest_tree(repo_root=PROJECT_ROOT))


def build_release_corpus_preflight_artifact() -> None:
    artifact_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
    payload = build_release_corpus_preflight(
        leaf=load_json(artifact_dir / 'streamed_lookup_tail_leaf.json'),
        proof_corpus_profiles=load_json(artifact_dir / 'proof_corpus_profiles.json'),
    )
    dump_json(artifact_dir / 'release_corpus_preflight.json', payload)


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
        choices=('all', 'core-artifacts', 'build-summary', 'artifact-digest-tree', 'release-corpus-preflight', 'arithmetic-operation-ir', 'resource-liveness-certificate', 'resource-stack', 'qroam-reference', 'reusable-chunk-resource', 'zkp', 'candidate-zkp', 'public-headline', 'zkp-and-public', 'resource-zkp-and-public'),
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
    if args.target in ('release-corpus-preflight',):
        build_release_corpus_preflight_artifact()
        payload['release_corpus_preflight'] = 'compiler_verification_project/artifacts/release_corpus_preflight.json'
    if args.target in ('resource-stack', 'resource-zkp-and-public'):
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
    if args.target in ('reusable-chunk-resource',):
        build_reusable_chunk_resource()
        payload['reusable_chunk_lowering'] = 'compiler_verification_project/artifacts/reusable_chunk_lowering.json'
    if args.target in ('all', 'zkp', 'zkp-and-public'):
        payload['zkp_attestation'] = write_zkp_attestation_inputs()
    if args.target in ('all', 'candidate-zkp', 'zkp-and-public', 'resource-zkp-and-public'):
        build_candidate_zkp()
        payload['zkp_attestation_reusable_chunk_candidate'] = 'compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_input.json'
    if args.target in ('all', 'public-headline', 'zkp-and-public', 'resource-zkp-and-public'):
        build_public_headline()
        payload['public_headline_result'] = 'compiler_verification_project/artifacts/public_headline_result.json'
    print(json.dumps({
        'target': args.target,
        'build_summary': payload['frontier']['best_gate_family'] if isinstance(payload.get('frontier'), dict) else None,
        'build_summary_artifact': payload.get('build_summary_artifact'),
        'artifact_digest_tree': payload.get('artifact_digest_tree'),
        'release_corpus_preflight': payload.get('release_corpus_preflight'),
        'arithmetic_operation_ir': payload.get('arithmetic_operation_ir'),
        'resource_liveness_certificate': payload.get('resource_liveness_certificate'),
        'qroam_reference_crosscheck': payload.get('qroam_reference_crosscheck'),
        'reusable_chunk_lowering': payload.get('reusable_chunk_lowering'),
        'public_headline_result': payload.get('public_headline_result'),
        'zkp_attestation_input': 'compiler_verification_project/artifacts/zkp_attestation_input.json' if 'zkp_attestation' in payload else None,
        'zkp_attestation_reusable_chunk_candidate_input': payload.get('zkp_attestation_reusable_chunk_candidate'),
        'artifact_dir': 'compiler_verification_project/artifacts',
    }, indent=2))


if __name__ == '__main__':
    main()
