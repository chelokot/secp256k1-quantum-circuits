#!/usr/bin/env python3

from __future__ import annotations

from typing import Dict


BUILD_SUMMARY_SCHEMA = 'compiler-project-build-summary-v35'

BUILD_SUMMARY_ARTIFACT_PATHS: Dict[str, str] = {
    'canonical_public_point': 'compiler_verification_project/artifacts/canonical_public_point.json',
    'compiler_parameters': 'compiler_verification_project/artifacts/compiler_parameters.json',
    'public_google_baseline_source': 'compiler_verification_project/artifacts/public_google_baseline_source.json',
    'proof_corpus_profiles': 'compiler_verification_project/artifacts/proof_corpus_profiles.json',
    'full_raw32_oracle': 'compiler_verification_project/artifacts/full_raw32_oracle.json',
    'exact_leaf_slot_allocation': 'compiler_verification_project/artifacts/exact_leaf_slot_allocation.json',
    'lookup_fed_leaf': 'compiler_verification_project/artifacts/lookup_fed_leaf.json',
    'lookup_fed_leaf_equivalence': 'compiler_verification_project/artifacts/lookup_fed_leaf_equivalence.json',
    'lookup_fed_leaf_slot_allocation': 'compiler_verification_project/artifacts/lookup_fed_leaf_slot_allocation.json',
    'streamed_lookup_tail_leaf': 'compiler_verification_project/artifacts/streamed_lookup_tail_leaf.json',
    'streamed_lookup_tail_leaf_equivalence': 'compiler_verification_project/artifacts/streamed_lookup_tail_leaf_equivalence.json',
    'streamed_lookup_tail_leaf_slot_allocation': 'compiler_verification_project/artifacts/streamed_lookup_tail_leaf_slot_allocation.json',
    'arithmetic_lowerings': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
    'modular_arithmetic_certificate': 'compiler_verification_project/artifacts/modular_arithmetic_certificate.json',
    'tail_macro_liveness': 'compiler_verification_project/artifacts/tail_macro_liveness.json',
    'tail_macro_reversibility': 'compiler_verification_project/artifacts/tail_macro_reversibility.json',
    'tail_macro_schedule_search': 'compiler_verification_project/artifacts/tail_macro_schedule_search.json',
    'streamed_lookup_table_multiplier_resource': 'compiler_verification_project/artifacts/streamed_lookup_table_multiplier_resource.json',
    'module_library': 'compiler_verification_project/artifacts/module_library.json',
    'primitive_multiplier_library': 'compiler_verification_project/artifacts/primitive_multiplier_library.json',
    'phase_shell_lowerings': 'compiler_verification_project/artifacts/phase_shell_lowerings.json',
    'phase_shell_families': 'compiler_verification_project/artifacts/phase_shell_families.json',
    'table_manifests': 'compiler_verification_project/artifacts/table_manifests.json',
    'lookup_lowerings': 'compiler_verification_project/artifacts/lookup_lowerings.json',
    'generated_block_inventories': 'compiler_verification_project/artifacts/generated_block_inventories.json',
    'ft_ir_compositions': 'compiler_verification_project/artifacts/ft_ir_compositions.json',
    'whole_oracle_recount': 'compiler_verification_project/artifacts/whole_oracle_recount.json',
    'family_frontier': 'compiler_verification_project/artifacts/family_frontier.json',
    'release_corpus_preflight': 'compiler_verification_project/artifacts/release_corpus_preflight.json',
    'standard_qrom_lookup_assessment': 'compiler_verification_project/artifacts/standard_qrom_lookup_assessment.json',
    'logical_resource_ledger': 'compiler_verification_project/artifacts/logical_resource_ledger.json',
    'fallback_frontier_stress': 'compiler_verification_project/artifacts/fallback_frontier_stress.json',
    'reusable_chunk_tail_candidate': 'compiler_verification_project/artifacts/reusable_chunk_tail_candidate.json',
    'qroam_primitive_certificate': 'compiler_verification_project/artifacts/qroam_primitive_certificate.json',
    'qroam_reference_crosscheck': 'compiler_verification_project/artifacts/qroam_reference_crosscheck.json',
    'reusable_chunk_lowering': 'compiler_verification_project/artifacts/reusable_chunk_lowering.json',
    'resource_liveness_certificate': 'compiler_verification_project/artifacts/resource_liveness_certificate.json',
    'materialized_circuit_manifest': 'compiler_verification_project/artifacts/materialized_circuit_manifest.json',
    'qubit_breakthrough_analysis': 'compiler_verification_project/artifacts/qubit_breakthrough_analysis.json',
    'full_attack_inventory': 'compiler_verification_project/artifacts/full_attack_inventory.json',
    'subcircuit_equivalence': 'compiler_verification_project/artifacts/subcircuit_equivalence.json',
    'headline_opcode_coverage': 'compiler_verification_project/artifacts/headline_opcode_coverage.json',
    'public_headline_result': 'compiler_verification_project/artifacts/public_headline_result.json',
    'azure_resource_estimator_logical_counts': 'compiler_verification_project/artifacts/azure_resource_estimator_logical_counts.json',
    'azure_resource_estimator_targets': 'compiler_verification_project/artifacts/azure_resource_estimator_targets.json',
    'azure_resource_estimator_results': 'compiler_verification_project/artifacts/azure_resource_estimator_results.json',
    'artifact_digest_tree': 'compiler_verification_project/artifacts/artifact_digest_tree.json',
}


__all__ = ['BUILD_SUMMARY_ARTIFACT_PATHS', 'BUILD_SUMMARY_SCHEMA']
