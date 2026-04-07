#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from research_extensions import run_research_pass


class ResearchArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run_research_pass(REPO_ROOT)
        cls.summary = json.loads((REPO_ROOT / 'results' / 'research_pass_summary.json').read_text())
        cls.dominant = json.loads((REPO_ROOT / 'artifacts' / 'out' / 'projections' / 'dominant_cost_breakdown.json').read_text())
        cls.scenarios = json.loads((REPO_ROOT / 'artifacts' / 'out' / 'projections' / 'literature_projection_scenarios.json').read_text())
        cls.lookup_summary = json.loads((REPO_ROOT / 'artifacts' / 'out' / 'lookup' / 'lookup_signed_fold_summary.json').read_text())
        cls.lookup_projection = json.loads((REPO_ROOT / 'artifacts' / 'out' / 'projections' / 'lookup_folded_projection.json').read_text())
        cls.ladder = json.loads((REPO_ROOT / 'benchmarks' / 'challenge_ladder' / 'challenge_ladder.json').read_text())
        cls.ladder_summary = json.loads((REPO_ROOT / 'benchmarks' / 'challenge_ladder' / 'challenge_ladder_summary.json').read_text())
        cls.matrix = json.loads((REPO_ROOT / 'results' / 'literature_matrix.json').read_text())

    def test_cost_model_correction_is_reflected(self):
        self.assertGreater(self.dominant['breakdown']['arithmetic_share_fraction_2lookup'], 0.93 - 1e-9)
        self.assertGreater(self.dominant['breakdown']['arithmetic_share_fraction_3lookup'], 0.90 - 1e-9)
        self.assertLess(self.dominant['breakdown']['lookup_share_fraction_2lookup'], 0.07)
        self.assertLess(self.dominant['breakdown']['lookup_share_fraction_3lookup'], 0.10)
        self.assertGreater(self.dominant['ceilings']['max_total_reduction_fraction_from_arithmetic_only_2lookup'], 0.93 - 1e-9)
        self.assertGreater(self.dominant['ceilings']['max_total_reduction_fraction_from_arithmetic_only_3lookup'], 0.90 - 1e-9)

    def test_lookup_target_table_is_ordered(self):
        targets = self.dominant['lookup_reduction_targets']
        goals = [row['goal_total_non_clifford'] for row in targets]
        self.assertEqual(goals, [30_000_000, 29_000_000, 25_000_000, 20_000_000])
        reductions = [row['required_lookup_reduction_fraction_2lookup_without_other_changes'] for row in targets]
        self.assertTrue(all(a < b for a, b in zip(reductions, reductions[1:])))

    def test_lookup_folding_audit_passes(self):
        summary = self.lookup_summary['summary']
        self.assertEqual(summary['full_exhaustive_cases'], 65_536)
        self.assertEqual(summary['full_exhaustive_cases'], summary['full_exhaustive_pass'])
        self.assertGreaterEqual(summary['direct_semantic_samples'], 15_000)
        self.assertEqual(summary['direct_semantic_samples'], summary['direct_semantic_pass'])

    def test_lookup_folding_projection_is_meaningful(self):
        base = self.lookup_projection['base_case_pad0']
        self.assertLess(base['total_non_clifford_2channel_folded'], 30_000_000)
        self.assertLess(base['total_non_clifford_3channel_folded_conservative'], 31_000_000)
        self.assertGreater(base['gain_vs_google_low_qubit_2channel'], 3.0)
        self.assertGreater(base['gain_vs_google_low_gate_2channel'], 2.3)

    def test_challenge_ladder_audit_passes(self):
        self.assertEqual(self.ladder_summary['summary']['curve_count'], 7)
        self.assertEqual(self.ladder_summary['summary']['total'], self.ladder_summary['summary']['pass'])
        self.assertGreaterEqual(self.summary['challenge_ladder']['audit_total'], 700)
        self.assertGreaterEqual(self.summary['challenge_ladder']['max_field_bits'], 18)

    def test_literature_matrix_has_expected_entries(self):
        ids = {entry['id'] for entry in self.matrix['entries']}
        for key in {
            'google_babbush_2026',
            'cain_2026',
            'luongo_2025',
            'papa_2025',
            'qualtran_2024',
            'qcec_repo',
            'qrisp_2025',
            'luo_2026',
            'gidney_2019_windowed_qrom',
            'low_zhu_2024_lookup_architecture',
        }:
            self.assertIn(key, ids)

    def test_scenarios_include_lookup_frontier_and_folding(self):
        names = {entry['name'] for entry in self.scenarios['scenarios']}
        self.assertIn('lookup_layer_reduction_frontier', names)
        self.assertIn('litinski_style_multiplier_swap_band', names)
        self.assertIn('exact_arithmetic_elimination_ceiling', names)
        self.assertIn('signed_lookup_folding_contract_projection', names)


if __name__ == '__main__':
    unittest.main()
