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
        for row in self.summary['baseline_transfer_ranges'].values():
            self.assertLessEqual(
                row['runtime_days_if_baseline_maps_to_10d_min'],
                row['runtime_days_if_baseline_maps_to_10d_max'],
            )
            self.assertLessEqual(
                row['same_density_physical_qubits_if_baseline_maps_to_26k_min'],
                row['same_density_physical_qubits_if_baseline_maps_to_26k_max'],
            )

    def test_case_transfer_formulas_are_self_consistent(self):
        cain = self.summary['source_papers']['cain_2026']
        baseline = self.summary['public_google_baseline']
        for case in self.summary['cases']:
            for baseline_name, baseline_row in baseline.items():
                transfer = case['baseline_transfers'][baseline_name]
                self.assertEqual(transfer['baseline'], baseline_name)
                self.assertEqual(transfer['baseline_non_clifford'], baseline_row['non_clifford'])
                self.assertEqual(transfer['baseline_logical_qubits'], baseline_row['logical_qubits'])
                self.assertAlmostEqual(
                    transfer['heuristic_time_efficient_days_if_baseline_maps_to_10d'],
                    cain['time_efficient_runtime_days'] * case['exact_non_clifford'] / baseline_row['non_clifford'],
                )
                self.assertAlmostEqual(
                    transfer['same_density_physical_qubits_if_baseline_maps_to_26k'],
                    cain['time_efficient_physical_qubits'] * case['exact_logical_qubits'] / baseline_row['logical_qubits'],
                )

    def test_headline_ranges_match_case_extrema(self):
        for baseline_name, head in self.summary['baseline_transfer_ranges'].items():
            runtime_values = [
                case['baseline_transfers'][baseline_name]['heuristic_time_efficient_days_if_baseline_maps_to_10d']
                for case in self.summary['cases']
            ]
            qubit_values = [
                case['baseline_transfers'][baseline_name]['same_density_physical_qubits_if_baseline_maps_to_26k']
                for case in self.summary['cases']
            ]
            self.assertEqual(head['runtime_days_if_baseline_maps_to_10d_min'], min(runtime_values))
            self.assertEqual(head['runtime_days_if_baseline_maps_to_10d_max'], max(runtime_values))
            self.assertEqual(head['same_density_physical_qubits_if_baseline_maps_to_26k_min'], min(qubit_values))
            self.assertEqual(head['same_density_physical_qubits_if_baseline_maps_to_26k_max'], max(qubit_values))

    def test_publication_safe_summary_exists(self):
        pub = self.summary['publication_safe_summary']
        self.assertIn('central standard-QROM compiler family', pub['single_sentence'])
        self.assertIn('3.9-5.0 days', pub['single_sentence'])
        self.assertEqual(len(pub['do_not_say']), 3)


if __name__ == '__main__':
    unittest.main()
