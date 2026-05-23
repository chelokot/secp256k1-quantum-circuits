#!/usr/bin/env python3

from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class IBMRoadmapContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = json.loads((REPO_ROOT / 'data' / 'ibm_quantum_roadmap_context.json').read_text())
        cls.headline = json.loads(
            (REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'strict_replayed_tail_headline.json').read_text()
        )
        cls.readme = (REPO_ROOT / 'README.md').read_text()
        cls.reference_note = (REPO_ROOT / 'docs' / 'references' / 'IBM_QUANTUM_ROADMAP_CONTEXT.md').read_text()

    def test_ibm_context_uses_checked_strict_replayed_tail_headline(self):
        selected = self.headline['selected_result']
        repo_headline = self.context['repo_headline_used_for_comparison']
        self.assertEqual(repo_headline['non_clifford'], selected['non_clifford'])
        self.assertEqual(repo_headline['logical_qubits'], selected['logical_qubits'])

    def test_roadmap_milestone_arithmetic_is_derived_from_artifact_values(self):
        milestones = self.context['roadmap_milestones']
        derived = self.context['derived_comparison']
        repo_headline = self.context['repo_headline_used_for_comparison']
        non_clifford = repo_headline['non_clifford']
        logical_qubits = repo_headline['logical_qubits']

        starling = milestones['starling_2029']
        blue_jay = milestones['blue_jay_2033_plus']

        self.assertEqual(starling['logical_qubits'], 200)
        self.assertEqual(starling['gate_target'], 100_000_000)
        self.assertEqual(blue_jay['logical_qubits'], 2_000)
        self.assertEqual(blue_jay['gate_target'], 1_000_000_000)

        self.assertAlmostEqual(
            derived['starling_gate_scale_ratio_vs_repo_non_clifford'],
            starling['gate_target'] / non_clifford,
        )
        self.assertEqual(
            derived['starling_logical_qubit_shortfall_vs_repo'],
            logical_qubits - starling['logical_qubits'],
        )
        self.assertAlmostEqual(
            derived['blue_jay_gate_scale_ratio_vs_repo_non_clifford'],
            blue_jay['gate_target'] / non_clifford,
        )
        self.assertEqual(
            derived['blue_jay_logical_qubit_headroom_vs_repo'],
            blue_jay['logical_qubits'] - logical_qubits,
        )

    def test_docs_preserve_favorable_but_bounded_ibm_claim(self):
        selected = self.headline['selected_result']
        non_clifford = f"{selected['non_clifford']:,}"
        logical_qubits = f"{selected['logical_qubits']:,}"
        for text in [self.readme, self.reference_note]:
            self.assertIn(non_clifford, text)
            self.assertIn(logical_qubits, text)
            self.assertIn('Starling', text)
            self.assertIn('Blue Jay', text)
            self.assertRegex(text, r'not (as )?a claim|not claimed')
        self.assertRegex(self.readme, r'named industrial\s+fault-tolerant machine\s+classes')
        self.assertRegex(self.reference_note, r'current IBM processors? (are|is) not claimed to run')


if __name__ == '__main__':
    unittest.main()
