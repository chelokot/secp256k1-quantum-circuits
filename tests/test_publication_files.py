#!/usr/bin/env python3

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class PublicationFilesTests(unittest.TestCase):
    def test_docs_exist(self):
        expected = [
            'docs/CLAIMS_AND_BOUNDARIES.md',
            'docs/RED_TEAM_REVIEW.md',
            'docs/OPTIMIZATION_FRONTIERS.md',
            'docs/META_ANALYSIS.md',
            'docs/EXTENDED_VERIFICATION.md',
            'docs/PUBLICATION_CHECKLIST.md',
            'docs/CAIN_2026_NEUTRAL_ATOM_INTEGRATION.md',
            'docs/STATE_OF_THE_ART_2026.md',
            'docs/LITERATURE_INTEGRATION_DECISIONS.md',
            'docs/CHALLENGE_LADDER.md',
            'docs/TOOLING_AND_REIMPLEMENTATION_PATHS.md',
            'docs/PHYSICAL_STACKS_AND_HARDWARE_CONTEXT.md',
            'docs/COST_MODEL_CORRECTION.md',
            'docs/LOOKUP_FOLDING_RESEARCH_PASS.md',
            'LICENSE',
            'CITATION.cff',
        ]
        for rel in expected:
            path = REPO_ROOT / rel
            self.assertTrue(path.exists(), path)
            self.assertGreater(path.stat().st_size, 100)

    def test_new_figures_exist(self):
        expected = [
            'artifacts/figures/progression_instruction_count.png',
            'artifacts/figures/progression_register_count.png',
            'artifacts/figures/projection_headroom.png',
            'artifacts/figures/verification_coverage_extended.png',
            'artifacts/figures/optimization_frontier_ranges.png',
            'artifacts/figures/dominant_cost_breakdown.png',
            'artifacts/figures/lookup_reduction_targets.png',
            'artifacts/figures/challenge_ladder_orders.png',
            'artifacts/figures/literature_layer_map.png',
            'artifacts/figures/lookup_fold_pad_sweep.png',
        ]
        for rel in expected:
            path = REPO_ROOT / rel
            self.assertTrue(path.exists(), path)
            self.assertGreater(path.stat().st_size, 10_000)


if __name__ == '__main__':
    unittest.main()
