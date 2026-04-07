#!/usr/bin/env python3

from __future__ import annotations

import json
import unittest
from pathlib import Path

from support import ensure_cain_summary

REPO_ROOT = Path(__file__).resolve().parents[1]


class CainIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = json.loads(ensure_cain_summary().read_text())

    def test_headline_ranges_are_ordered(self):
        head = self.summary['headline_ranges']
        self.assertLess(head['projected_time_efficient_days_min'], head['projected_time_efficient_days_max'])
        self.assertLess(head['projected_balanced_days_min'], head['projected_balanced_days_max'])
        self.assertLess(head['same_density_time_efficient_physical_qubits_min'], head['same_density_time_efficient_physical_qubits_max'])
        self.assertLess(head['same_density_min_space_physical_qubits_min'], head['same_density_min_space_physical_qubits_max'])

    def test_case_transfer_formulas_are_self_consistent(self):
        cain = self.summary['source_papers']['cain_2026']
        for case in self.summary['cases']:
            ratio = case['ratios']['non_clifford_ratio']
            logical_ratio = case['ratios']['logical_qubit_ratio']
            self.assertAlmostEqual(case['runtime_transfer']['projected_time_efficient_days'], cain['time_efficient_runtime_days'] * ratio)
            self.assertAlmostEqual(case['runtime_transfer']['projected_balanced_days'], cain['balanced_runtime_days'] * ratio)
            self.assertAlmostEqual(case['space_transfer']['same_density_time_efficient_physical_qubits'], cain['time_efficient_physical_qubits'] * logical_ratio)
            self.assertAlmostEqual(case['space_transfer']['same_density_min_space_physical_qubits'], cain['headline_min_physical_qubits'] * logical_ratio)

    def test_headline_ranges_match_case_extrema(self):
        head = self.summary['headline_ranges']
        time_values = [case['runtime_transfer']['projected_time_efficient_days'] for case in self.summary['cases']]
        balanced_values = [case['runtime_transfer']['projected_balanced_days'] for case in self.summary['cases']]
        time_space_values = [case['space_transfer']['same_density_time_efficient_physical_qubits'] for case in self.summary['cases']]
        min_space_values = [case['space_transfer']['same_density_min_space_physical_qubits'] for case in self.summary['cases']]
        self.assertEqual(head['projected_time_efficient_days_min'], min(time_values))
        self.assertEqual(head['projected_time_efficient_days_max'], max(time_values))
        self.assertEqual(head['projected_balanced_days_min'], min(balanced_values))
        self.assertEqual(head['projected_balanced_days_max'], max(balanced_values))
        self.assertEqual(head['same_density_time_efficient_physical_qubits_min'], min(time_space_values))
        self.assertEqual(head['same_density_time_efficient_physical_qubits_max'], max(time_space_values))
        self.assertEqual(head['same_density_min_space_physical_qubits_min'], min(min_space_values))
        self.assertEqual(head['same_density_min_space_physical_qubits_max'], max(min_space_values))

    def test_publication_safe_summary_exists(self):
        pub = self.summary['publication_safe_summary']
        self.assertIn('2.5-3.3 days', pub['single_sentence'])
        self.assertEqual(len(pub['do_not_say']), 3)


if __name__ == '__main__':
    unittest.main()
