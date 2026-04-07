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
        self.assertLess(head['naive_linear_space_physical_qubits_min'], head['naive_linear_space_physical_qubits_max'])
        self.assertLess(head['half_fixed_overhead_space_physical_qubits_min'], head['half_fixed_overhead_space_physical_qubits_max'])

    def test_time_efficient_range_matches_expected_window(self):
        head = self.summary['headline_ranges']
        self.assertGreater(head['projected_time_efficient_days_min'], 3.23)
        self.assertLess(head['projected_time_efficient_days_min'], 3.25)
        self.assertGreater(head['projected_time_efficient_days_max'], 4.29)
        self.assertLess(head['projected_time_efficient_days_max'], 4.31)

    def test_balanced_range_matches_expected_window(self):
        head = self.summary['headline_ranges']
        self.assertGreater(head['projected_balanced_days_min'], 85.5)
        self.assertLess(head['projected_balanced_days_min'], 85.6)
        self.assertGreater(head['projected_balanced_days_max'], 113.4)
        self.assertLess(head['projected_balanced_days_max'], 113.5)

    def test_publication_safe_summary_exists(self):
        pub = self.summary['publication_safe_summary']
        self.assertIn('3-4 days', pub['single_sentence'])
        self.assertEqual(len(pub['do_not_say']), 3)


if __name__ == '__main__':
    unittest.main()
