#!/usr/bin/env python3

from __future__ import annotations

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class ReleaseInventoryTests(unittest.TestCase):
    def test_core_repository_inventory_is_present(self):
        expected = [
            'README.md',
            'RESEARCH_BOUNDARY.md',
            'REFERENCES.md',
            'LICENSE',
            'CITATION.cff',
            'MANIFEST.sha256',
            'docs/EXECUTIVE_SUMMARY.md',
            'docs/CLAIMS_AND_BOUNDARIES.md',
            'docs/GOOGLE_BASELINE_COMPARISON.md',
            'docs/STRICT_VERIFICATION.md',
            'docs/LOOKUP_FOLDING_RESEARCH_PASS.md',
            'docs/OPTIMIZATION_FRONTIERS.md',
            'docs/STATE_OF_THE_ART_2026.md',
            'docs/LITERATURE_INTEGRATION_DECISIONS.md',
            'docs/RED_TEAM_REVIEW.md',
            'docs/CAIN_2026_NEUTRAL_ATOM_INTEGRATION.md',
            'docs/CHALLENGE_LADDER.md',
            'docs/META_ANALYSIS.md',
            'docs/PUBLICATION_CHECKLIST.md',
            'docs/QUALITY_CONTROL.md',
            'docs/REPO_LAYOUT.md',
            'docs/PHYSICAL_STACKS_AND_HARDWARE_CONTEXT.md',
            'docs/COST_MODEL_CORRECTION.md',
            'docs/TOOLING_AND_REIMPLEMENTATION_PATHS.md',
            'reports/secp256k1_reconstruction_1191q_81p1M_1441q_64p3M_audit.pdf',
            'reports/secp256k1_optimized_880q_31p0M_2p62x_report.pdf',
            'scripts/verify_all.py',
            'scripts/verify_strict.py',
            'scripts/run_research_pass.py',
            'scripts/compare_google_baseline.py',
            'scripts/compare_lookup_research.py',
            'scripts/compare_literature.py',
            'scripts/compare_cain_2026.py',
            'scripts/generate_figures.py',
            'scripts/hash_repo.py',
            'scripts/release_check.py',
            'src/common.py',
            'src/verifier.py',
            'src/strict_verifier.py',
            'src/research_extensions.py',
            'src/lookup_research.py',
            'artifacts/out/optimized_pointadd_secp256k1.json',
            'artifacts/out/optimized_pointadd_family.json',
            'artifacts/out/optimized_pointadd_audit_16384.csv',
            'artifacts/out/ecdlp_scaffold_optimized.json',
            'artifacts/out/resource_projection.json',
            'artifacts/out/register_map.json',
            'artifacts/out/proof_manifest.json',
            'artifacts/out/lookup_contract_audit_8192.csv',
            'artifacts/out/lookup_contract_summary.json',
            'artifacts/out/scaffold_schedule_audit_256.csv',
            'artifacts/out/scaffold_schedule_summary.json',
            'artifacts/out/toy_curve_exhaustive_19850.csv',
            'artifacts/out/toy_curve_family_extended_110692.csv',
            'artifacts/out/toy_curve_family_extended_summary.json',
            'artifacts/out/projection_sensitivity.json',
            'artifacts/out/claim_boundary_matrix.json',
            'artifacts/out/meta_analysis.json',
            'artifacts/out/optimization_frontier_estimates.json',
            'artifacts/out/dominant_cost_breakdown.json',
            'artifacts/out/literature_projection_scenarios.json',
            'artifacts/out/lookup_signed_fold_contract.json',
            'artifacts/out/lookup_signed_fold_exhaustive_g.csv',
            'artifacts/out/lookup_signed_fold_multibase_sampled.csv',
            'artifacts/out/lookup_signed_fold_summary.json',
            'artifacts/out/ecdlp_scaffold_lookup_folded.json',
            'artifacts/out/lookup_folded_projection.json',
            'benchmarks/challenge_ladder/challenge_ladder.json',
            'benchmarks/challenge_ladder/challenge_ladder_audit.csv',
            'benchmarks/challenge_ladder/challenge_ladder_summary.json',
            'results/strict_verification_summary.json',
            'results/research_pass_summary.json',
            'results/literature_matrix.json',
            'results/physical_stack_reference_points.json',
            'results/cain_2026_integration_summary.json',
        ]
        for rel in expected:
            path = REPO_ROOT / rel
            self.assertTrue(path.exists(), path)
            self.assertGreater(path.stat().st_size, 0, path)

    def test_machine_readable_summaries_are_deterministic(self):
        strict = json.loads((REPO_ROOT / 'results' / 'strict_verification_summary.json').read_text())
        research = json.loads((REPO_ROOT / 'results' / 'research_pass_summary.json').read_text())
        rebuild = json.loads((REPO_ROOT / 'artifacts' / 'out' / 'verifier_rebuild_summary.json').read_text())
        self.assertNotIn('elapsed_seconds', strict)
        self.assertNotIn('elapsed_seconds', research)
        self.assertNotIn('elapsed_seconds', rebuild)


if __name__ == '__main__':
    unittest.main()
