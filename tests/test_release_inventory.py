#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from support import ensure_repo_verification_summary

REPO_ROOT = Path(__file__).resolve().parents[1]

SRC_DIR = REPO_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from common import sha256_path  # noqa: E402


class ReleaseInventoryTests(unittest.TestCase):
    def test_core_repository_inventory_is_present(self):
        expected = [
            'README.md',
            'REFERENCES.md',
            'LICENSE',
            'CITATION.cff',
            'MANIFEST.sha256',
            'docs/core/CLAIMS_AND_BOUNDARIES.md',
            'docs/references/GOOGLE_BASELINE_COMPARISON.md',
            'docs/core/EXTENDED_VERIFICATION.md',
            'docs/research/LOOKUP_FOLDING_RESEARCH_PASS.md',
            'docs/research/OPTIMIZATION_FRONTIERS.md',
            'docs/references/STATE_OF_THE_ART_2026.md',
            'docs/core/RED_TEAM_REVIEW.md',
            'docs/references/CAIN_2026_NEUTRAL_ATOM_INTEGRATION.md',
            'docs/research/META_ANALYSIS.md',
            'docs/core/REPO_LAYOUT.md',
            'docs/references/PHYSICAL_STACKS_AND_HARDWARE_CONTEXT.md',
            'docs/research/COST_MODEL_CORRECTION.md',
            'docs/research/MODELED_IMPLEMENTATION_HYPOTHESES.md',
            'docs/references/TOOLING_AND_REIMPLEMENTATION_PATHS.md',
            'scripts/verify_all.py',
            'scripts/compare_cain_2026.py',
            'scripts/refresh_repo.py',
            'src/common.py',
            'src/cain_integration.py',
            'src/derived_resources.py',
            'src/figure_generation.py',
            'src/maintenance.py',
            'src/resource_projection.py',
            'src/verifier.py',
            'src/extended_verifier.py',
            'src/research_extensions.py',
            'src/lookup_research.py',
            'artifacts/circuits/optimized_pointadd_secp256k1.json',
            'artifacts/circuits/optimized_pointadd_family.json',
            'artifacts/circuits/ecdlp_scaffold_optimized.json',
            'artifacts/circuits/ecdlp_expanded_isa_optimized.json',
            'artifacts/circuits/register_map.json',
            'artifacts/verification/core/optimized_pointadd_audit_16384.csv',
            'artifacts/projections/resource_projection.json',
            'artifacts/projections/structural_accounting.json',
            'artifacts/projections/backend_model_bundle.json',
            'artifacts/package/proof_manifest.json',
            'artifacts/verification/extended/lookup_contract_summary.json',
            'artifacts/verification/extended/coherent_cleanup_audit_16384.csv',
            'artifacts/verification/extended/coherent_cleanup_summary.json',
            'artifacts/verification/extended/scaffold_schedule_audit_256.csv',
            'artifacts/verification/extended/scaffold_schedule_summary.json',
            'artifacts/verification/core/toy_curve_exhaustive_19850.csv',
            'artifacts/verification/extended/toy_curve_family_extended_110692.csv',
            'artifacts/verification/extended/toy_curve_family_extended_summary.json',
            'artifacts/projections/projection_sensitivity.json',
            'artifacts/projections/claim_boundary_matrix.json',
            'artifacts/projections/meta_analysis.json',
            'artifacts/projections/optimization_frontier_estimates.json',
            'artifacts/projections/dominant_cost_breakdown.json',
            'artifacts/projections/literature_projection_scenarios.json',
            'artifacts/lookup/lookup_signed_fold_contract.json',
            'artifacts/lookup/lookup_signed_fold_exhaustive_g.csv',
            'artifacts/lookup/lookup_signed_fold_multibase_sampled.csv',
            'artifacts/lookup/lookup_signed_fold_summary.json',
            'artifacts/circuits/ecdlp_scaffold_lookup_folded.json',
            'artifacts/projections/lookup_folded_projection.json',
            'results/research_pass_summary.json',
            'results/literature_matrix.json',
            'results/physical_stack_reference_points.json',
            'results/cain_2026_integration_summary.json',
            'compiler_verification_project/README.md',
            'compiler_verification_project/scripts/build.py',
            'compiler_verification_project/scripts/verify.py',
            'compiler_verification_project/src/arithmetic_lowering.py',
            'compiler_verification_project/src/integrity.py',
            'compiler_verification_project/src/generated_block_inventory.py',
            'compiler_verification_project/src/ft_ir.py',
            'compiler_verification_project/src/lookup_lowering.py',
            'compiler_verification_project/src/lookup_fed_leaf.py',
            'compiler_verification_project/src/phase_shell_lowering.py',
            'compiler_verification_project/src/physical_estimator.py',
            'compiler_verification_project/src/project.py',
            'compiler_verification_project/src/subcircuit_equivalence.py',
            'compiler_verification_project/src/whole_oracle_recount.py',
            'compiler_verification_project/src/zkp_attestation.py',
            'compiler_verification_project/artifacts/build_summary.json',
            'compiler_verification_project/artifacts/arithmetic_lowerings.json',
            'compiler_verification_project/artifacts/family_frontier.json',
            'compiler_verification_project/artifacts/lookup_lowerings.json',
            'compiler_verification_project/artifacts/generated_block_inventories.json',
            'compiler_verification_project/artifacts/ft_ir_compositions.json',
            'compiler_verification_project/artifacts/whole_oracle_recount.json',
            'compiler_verification_project/artifacts/qubit_breakthrough_analysis.json',
            'compiler_verification_project/artifacts/subcircuit_equivalence.json',
            'compiler_verification_project/artifacts/verification_summary.json',
            'compiler_verification_project/artifacts/exact_leaf_slot_allocation.json',
            'compiler_verification_project/artifacts/lookup_fed_leaf.json',
            'compiler_verification_project/artifacts/lookup_fed_leaf_equivalence.json',
            'compiler_verification_project/artifacts/lookup_fed_leaf_slot_allocation.json',
            'compiler_verification_project/artifacts/interface_borrowed_leaf.json',
            'compiler_verification_project/artifacts/interface_borrowed_leaf_equivalence.json',
            'compiler_verification_project/artifacts/interface_borrowed_leaf_slot_allocation.json',
            'compiler_verification_project/artifacts/primitive_multiplier_library.json',
            'compiler_verification_project/artifacts/phase_shell_lowerings.json',
            'compiler_verification_project/artifacts/phase_shell_families.json',
            'compiler_verification_project/artifacts/cain_exact_transfer.json',
            'compiler_verification_project/artifacts/azure_resource_estimator_logical_counts.json',
            'compiler_verification_project/artifacts/azure_resource_estimator_targets.json',
            'compiler_verification_project/artifacts/azure_resource_estimator_results.json',
            'compiler_verification_project/artifacts/zkp_attestation_input.json',
            'compiler_verification_project/artifacts/zkp_attestation_claim.json',
            'compiler_verification_project/artifacts/zkp_attestation_family.json',
            'compiler_verification_project/artifacts/zkp_attestation_cases.json',
            'compiler_verification_project/artifacts/zkp_attestation_public_values.json',
            'compiler_verification_project/artifacts/zkp_attestation_fixture_core.json',
            'compiler_verification_project/artifacts/zkp_attestation_fixture_compressed.json',
            'compiler_verification_project/artifacts/zkp_attestation_fixture_groth16.json',
            'compiler_verification_project/artifacts/zkp_attestation_proof_groth16.bin',
            'compiler_verification_project/artifacts/zkp_attestation_groth16_verifier/groth16_vk.bin',
            'compiler_verification_project/scripts/build_zkp_attestation_input.py',
            'compiler_verification_project/scripts/run_zkp_attestation_guarded.py',
            'compiler_verification_project/zkp_attestation/Cargo.toml',
            'compiler_verification_project/zkp_attestation/Cargo.lock',
            'compiler_verification_project/zkp_attestation/lib/Cargo.toml',
            'compiler_verification_project/zkp_attestation/lib/src/lib.rs',
            'compiler_verification_project/zkp_attestation/program/Cargo.toml',
            'compiler_verification_project/zkp_attestation/program/src/main.rs',
            'compiler_verification_project/zkp_attestation/script/Cargo.toml',
            'compiler_verification_project/zkp_attestation/script/build.rs',
            'compiler_verification_project/zkp_attestation/script/src/bin/main.rs',
            'compiler_verification_project/zkp_attestation/script/src/core_only.rs',
            'compiler_verification_project/zkp_attestation/script/src/wrap_only.rs',
            'compiler_verification_project/zkp_attestation/vendor/sp1-recursion-gnark-ffi/build.rs',
            'compiler_verification_project/zkp_attestation/vendor/sp1-recursion-gnark-ffi/Cargo.toml',
            'compiler_verification_project/zkp_attestation/vendor/sp1-recursion-gnark-ffi/go/go.mod',
            'compiler_verification_project/zkp_attestation/vendor/sp1-recursion-gnark-ffi/go/go.sum',
            'compiler_verification_project/zkp_attestation/vendor/sp1-recursion-gnark-ffi/go/sp1/build.go',
            'compiler_verification_project/zkp_attestation/vendor/sp1-recursion-gnark-ffi/go/sp1/groth16_commitments.go',
            'compiler_verification_project/zkp_attestation/vendor/sp1-recursion-gnark-ffi/go/sp1/prove_groth16.go',
            'compiler_verification_project/zkp_attestation/vendor/sp1-recursion-gnark-ffi/src/lib.rs',
        ]
        for rel in expected:
            path = REPO_ROOT / rel
            self.assertTrue(path.exists(), path)
            self.assertGreater(path.stat().st_size, 0, path)

    def test_machine_readable_summaries_are_deterministic(self):
        verification = json.loads(ensure_repo_verification_summary().read_text())
        research = json.loads((REPO_ROOT / 'results' / 'research_pass_summary.json').read_text())
        rebuild = json.loads((REPO_ROOT / 'artifacts' / 'verification' / 'core' / 'verifier_rebuild_summary.json').read_text())
        self.assertNotIn('elapsed_seconds', verification)
        self.assertNotIn('elapsed_seconds', research)
        self.assertNotIn('elapsed_seconds', rebuild)

    def test_exact_frontier_is_self_consistent(self):
        ensure_repo_verification_summary()
        frontier = json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'family_frontier.json').read_text())
        baseline = frontier['public_google_baseline']
        best_gate = frontier['best_gate_family']
        best_qubit = frontier['best_qubit_family']
        self.assertAlmostEqual(best_gate['improvement_vs_google_low_gate'], baseline['low_gate']['non_clifford'] / best_gate['full_oracle_non_clifford'])
        self.assertAlmostEqual(best_qubit['qubit_ratio_vs_google_low_gate'], baseline['low_gate']['logical_qubits'] / best_qubit['total_logical_qubits'])

    def test_proof_manifest_matches_curated_files(self):
        proof = json.loads((REPO_ROOT / 'artifacts' / 'package' / 'proof_manifest.json').read_text())
        for rel, record in proof['files'].items():
            path = REPO_ROOT / rel
            self.assertTrue(path.exists(), path)
            self.assertEqual(path.stat().st_size, record['bytes'])
            self.assertEqual(sha256_path(path), record['sha256'])

    def test_proof_manifest_includes_custom_attestation_prover_sources(self):
        proof = json.loads((REPO_ROOT / 'artifacts' / 'package' / 'proof_manifest.json').read_text())
        required = [
            'compiler_verification_project/zkp_attestation/script/src/core_only.rs',
            'compiler_verification_project/zkp_attestation/script/src/wrap_only.rs',
            'compiler_verification_project/zkp_attestation/vendor/sp1-recursion-gnark-ffi/build.rs',
            'compiler_verification_project/zkp_attestation/vendor/sp1-recursion-gnark-ffi/Cargo.toml',
            'compiler_verification_project/zkp_attestation/vendor/sp1-recursion-gnark-ffi/go/go.mod',
            'compiler_verification_project/zkp_attestation/vendor/sp1-recursion-gnark-ffi/go/go.sum',
            'compiler_verification_project/zkp_attestation/vendor/sp1-recursion-gnark-ffi/go/sp1/build.go',
            'compiler_verification_project/zkp_attestation/vendor/sp1-recursion-gnark-ffi/go/sp1/groth16_commitments.go',
            'compiler_verification_project/zkp_attestation/vendor/sp1-recursion-gnark-ffi/go/sp1/prove_groth16.go',
            'compiler_verification_project/zkp_attestation/vendor/sp1-recursion-gnark-ffi/src/lib.rs',
        ]
        for rel in required:
            self.assertIn(rel, proof['files'])


if __name__ == '__main__':
    unittest.main()
