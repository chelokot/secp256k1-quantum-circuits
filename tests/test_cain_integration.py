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
        self.assertLessEqual(head['time_efficient_days_if_90M_min'], head['time_efficient_days_if_90M_max'])
        self.assertLessEqual(head['time_efficient_days_if_70M_min'], head['time_efficient_days_if_70M_max'])
        self.assertLessEqual(head['same_density_physical_qubits_if_1200_min'], head['same_density_physical_qubits_if_1200_max'])
        self.assertLessEqual(head['same_density_physical_qubits_if_1450_min'], head['same_density_physical_qubits_if_1450_max'])

    def test_case_transfer_formulas_are_self_consistent(self):
        cain = self.summary['source_papers']['cain_2026']
        baseline = self.summary['public_google_baseline']
        for case in self.summary['cases']:
            self.assertAlmostEqual(
                case['runtime_transfer']['time_efficient_days_if_90M_maps_to_10d'],
                cain['time_efficient_runtime_days'] * case['exact_non_clifford'] / baseline['low_qubit']['non_clifford'],
            )
            self.assertAlmostEqual(
                case['runtime_transfer']['time_efficient_days_if_70M_maps_to_10d'],
                cain['time_efficient_runtime_days'] * case['exact_non_clifford'] / baseline['low_gate']['non_clifford'],
            )
            self.assertAlmostEqual(
                case['space_transfer']['same_density_physical_qubits_if_1200_maps_to_26k'],
                cain['time_efficient_physical_qubits'] * case['exact_logical_qubits'] / baseline['low_qubit']['logical_qubits'],
            )
            self.assertAlmostEqual(
                case['space_transfer']['same_density_physical_qubits_if_1450_maps_to_26k'],
                cain['time_efficient_physical_qubits'] * case['exact_logical_qubits'] / baseline['low_gate']['logical_qubits'],
            )

    def test_headline_ranges_match_case_extrema(self):
        head = self.summary['headline_ranges']
        runtime_90m_values = [case['runtime_transfer']['time_efficient_days_if_90M_maps_to_10d'] for case in self.summary['cases']]
        runtime_70m_values = [case['runtime_transfer']['time_efficient_days_if_70M_maps_to_10d'] for case in self.summary['cases']]
        qubit_1200_values = [case['space_transfer']['same_density_physical_qubits_if_1200_maps_to_26k'] for case in self.summary['cases']]
        qubit_1450_values = [case['space_transfer']['same_density_physical_qubits_if_1450_maps_to_26k'] for case in self.summary['cases']]
        self.assertEqual(head['time_efficient_days_if_90M_min'], min(runtime_90m_values))
        self.assertEqual(head['time_efficient_days_if_90M_max'], max(runtime_90m_values))
        self.assertEqual(head['time_efficient_days_if_70M_min'], min(runtime_70m_values))
        self.assertEqual(head['time_efficient_days_if_70M_max'], max(runtime_70m_values))
        self.assertEqual(head['same_density_physical_qubits_if_1200_min'], min(qubit_1200_values))
        self.assertEqual(head['same_density_physical_qubits_if_1200_max'], max(qubit_1200_values))
        self.assertEqual(head['same_density_physical_qubits_if_1450_min'], min(qubit_1450_values))
        self.assertEqual(head['same_density_physical_qubits_if_1450_max'], max(qubit_1450_values))

    def test_publication_safe_summary_exists(self):
        pub = self.summary['publication_safe_summary']
        self.assertIn('central standard-QROM compiler family', pub['single_sentence'])
        self.assertIn('2.7-3.4 days', pub['single_sentence'])
        self.assertEqual(len(pub['do_not_say']), 3)


if __name__ == '__main__':
    unittest.main()
