#!/usr/bin/env python3

from __future__ import annotations

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class ExtendedArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.extended = json.loads((REPO_ROOT / 'results' / 'repo_verification_summary.json').read_text())['extended']
        cls.boundaries = json.loads((REPO_ROOT / 'artifacts' / 'out' / 'claim_boundary_matrix.json').read_text())
        cls.meta = json.loads((REPO_ROOT / 'artifacts' / 'out' / 'meta_analysis.json').read_text())
        cls.sensitivity = json.loads((REPO_ROOT / 'artifacts' / 'out' / 'projection_sensitivity.json').read_text())

    def test_lookup_contract_passes(self):
        lookup = self.extended['lookup_contract']
        self.assertEqual(lookup['summary']['signed_i16']['total'], 4096)
        self.assertEqual(lookup['summary']['signed_i16']['pass'], 4096)
        self.assertEqual(lookup['summary']['unsigned_u16']['total'], 4096)
        self.assertEqual(lookup['summary']['unsigned_u16']['pass'], 4096)
        self.assertEqual(lookup['sha256'], '46864f51df4cdd68a7db4b2204f5d77ecece0ecf1f38e1c850bb92ef1f70fa2a')

    def test_scaffold_replay_passes(self):
        scaffold = self.extended['scaffold_schedule']
        self.assertEqual(scaffold['summary']['total'], 256)
        self.assertEqual(scaffold['summary']['pass'], 256)
        self.assertEqual(scaffold['summary']['phase_b_base_variants'], 256)
        self.assertEqual(scaffold['sha256'], '85017d7778bac523a50c8eb79c248685422c35d178dd8c0d29bf6e3c2f1712c4')

    def test_extended_toy_family_passes(self):
        toy = self.extended['toy_extended']
        self.assertEqual(toy['summary']['total'], 110692)
        self.assertEqual(toy['summary']['pass'], 110692)
        self.assertEqual(toy['sha256'], '1934fbac5e0c4bbd2d5afd58a2956cd3dd40edcfcf5bc53be747af7f00baab72')

    def test_meta_analysis_reductions_are_substantial(self):
        optimized = self.meta['optimized_vs_google_estimates']
        self.assertGreater(optimized['vs_low_qubit_non_clifford_factor'], 2.5)
        self.assertGreater(optimized['vs_low_gate_non_clifford_factor'], 2.0)
        self.assertGreater(optimized['vs_low_qubit_logical_qubit_factor'], 1.3)

    def test_headroom_is_positive(self):
        headroom = self.sensitivity['headroom']
        self.assertGreater(headroom['non_clifford_margin_vs_low_gate_2lookup'], 30_000_000)
        self.assertGreater(headroom['non_clifford_margin_vs_low_qubit_2lookup'], 50_000_000)
        self.assertGreater(headroom['qubit_margin_vs_low_qubit'], 300)

    def test_claim_boundary_statuses(self):
        statuses = {layer['layer']: layer['status'] for layer in self.boundaries['layers']}
        self.assertEqual(statuses['optimized_leaf_arithmetic'], 'exact_machine_checked')
        self.assertEqual(statuses['lookup_table_contract'], 'explicit_interface_tested_not_flattened')
        self.assertEqual(statuses['mbuc_cleanup'], 'abstract_contract_only')


if __name__ == '__main__':
    unittest.main()
