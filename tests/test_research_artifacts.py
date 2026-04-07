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
        cls.lookup_summary = json.loads((REPO_ROOT / 'artifacts' / 'lookup' / 'lookup_signed_fold_summary.json').read_text())
        cls.matrix = json.loads((REPO_ROOT / 'results' / 'literature_matrix.json').read_text())
        cls.frontier = json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'family_frontier.json').read_text())

    def test_exact_frontier_gate_advantage_is_derived(self):
        baseline = self.frontier['public_google_baseline']
        gate = self.frontier['best_gate_family']
        self.assertAlmostEqual(gate['improvement_vs_google_low_qubit'], baseline['low_qubit']['non_clifford'] / gate['full_oracle_non_clifford'])
        self.assertAlmostEqual(gate['improvement_vs_google_low_gate'], baseline['low_gate']['non_clifford'] / gate['full_oracle_non_clifford'])

    def test_exact_frontier_qubit_ratios_are_derived(self):
        baseline = self.frontier['public_google_baseline']
        qubit = self.frontier['best_qubit_family']
        self.assertAlmostEqual(qubit['qubit_ratio_vs_google_low_qubit'], baseline['low_qubit']['logical_qubits'] / qubit['total_logical_qubits'])
        self.assertAlmostEqual(qubit['qubit_ratio_vs_google_low_gate'], baseline['low_gate']['logical_qubits'] / qubit['total_logical_qubits'])

    def test_lookup_folding_audit_passes(self):
        summary = self.lookup_summary['summary']
        self.assertEqual(summary['full_exhaustive_cases'], 65_536)
        self.assertEqual(summary['full_exhaustive_cases'], summary['full_exhaustive_pass'])
        self.assertGreaterEqual(summary['direct_semantic_samples'], 15_000)
        self.assertEqual(summary['direct_semantic_samples'], summary['direct_semantic_pass'])

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


if __name__ == '__main__':
    unittest.main()
