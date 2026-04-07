#!/usr/bin/env python3

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class PublicationFilesTests(unittest.TestCase):
    def test_docs_exist(self):
        expected = [
            'docs/core/CLAIMS_AND_BOUNDARIES.md',
            'docs/core/RED_TEAM_REVIEW.md',
            'docs/research/OPTIMIZATION_FRONTIERS.md',
            'docs/research/META_ANALYSIS.md',
            'docs/core/EXTENDED_VERIFICATION.md',
            'docs/core/PUBLICATION_CHECKLIST.md',
            'docs/references/CAIN_2026_NEUTRAL_ATOM_INTEGRATION.md',
            'docs/references/STATE_OF_THE_ART_2026.md',
            'docs/references/LITERATURE_INTEGRATION_DECISIONS.md',
            'docs/research/CHALLENGE_LADDER.md',
            'docs/references/TOOLING_AND_REIMPLEMENTATION_PATHS.md',
            'docs/references/PHYSICAL_STACKS_AND_HARDWARE_CONTEXT.md',
            'docs/research/COST_MODEL_CORRECTION.md',
            'docs/research/LOOKUP_FOLDING_RESEARCH_PASS.md',
            'LICENSE',
            'CITATION.cff',
        ]
        for rel in expected:
            path = REPO_ROOT / rel
            self.assertTrue(path.exists(), path)
            self.assertGreater(path.stat().st_size, 100)

    def test_new_figures_exist(self):
        expected = [
            'figures/core/progression_instruction_count.png',
            'figures/core/progression_register_count.png',
            'figures/core/projection_headroom.png',
            'figures/research/verification_coverage_extended.png',
            'figures/research/optimization_frontier_ranges.png',
            'figures/research/dominant_cost_breakdown.png',
            'figures/research/lookup_reduction_targets.png',
            'figures/research/challenge_ladder_orders.png',
            'figures/research/literature_layer_map.png',
            'figures/research/lookup_fold_pad_sweep.png',
        ]
        for rel in expected:
            path = REPO_ROOT / rel
            self.assertTrue(path.exists(), path)
            self.assertGreater(path.stat().st_size, 10_000)


if __name__ == '__main__':
    unittest.main()
