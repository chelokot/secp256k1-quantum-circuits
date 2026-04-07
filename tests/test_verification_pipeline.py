#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class VerificationPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable, 'scripts/verify_all.py'], cwd=REPO_ROOT, check=True)
        cls.summary = json.loads((REPO_ROOT / 'results' / 'repo_verification_summary.json').read_text())

    def test_optimized_audit_passes(self):
        audit = self.summary['optimized']['audit']
        self.assertEqual(audit['summary']['total'], 16384)
        self.assertEqual(audit['summary']['pass'], 16384)
        self.assertEqual(audit['sha256'], 'aea0983dbd9827717fcd10875e31110374208d63c9f009e40c0a4e959071cab0')
        self.assertEqual(audit['netlist_sha256'], '48363319f1efabc24b4adf78ff2b9c1a80585e676c7c6ad5a917d0bbf8227a74')

    def test_optimized_toy_passes(self):
        toy = self.summary['optimized']['toy']
        self.assertEqual(toy['summary']['total'], 19850)
        self.assertEqual(toy['summary']['pass'], 19850)
        self.assertEqual(toy['sha256'], '70235a7be65ecbdd1a69583d12be3ab8ec0d39cf148f9dae1c36bd9c2e71b6e1')

    def test_google_baseline_is_recorded(self):
        baseline = self.summary['google_baseline']
        self.assertEqual(baseline['window_size'], 16)
        self.assertEqual(baseline['retained_window_additions'], 28)
        self.assertEqual(baseline['low_qubit']['logical_qubits'], 1200)
        self.assertEqual(baseline['low_qubit']['non_clifford'], 90_000_000)
        self.assertEqual(baseline['low_gate']['logical_qubits'], 1450)
        self.assertEqual(baseline['low_gate']['non_clifford'], 70_000_000)

    def test_extended_supporting_checks_are_recorded(self):
        extended = self.summary['extended']
        self.assertEqual(extended['lookup_contract']['summary']['signed_i16']['pass'], 4096)
        self.assertEqual(extended['lookup_contract']['summary']['unsigned_u16']['pass'], 4096)
        self.assertEqual(extended['scaffold_schedule']['summary']['pass'], 256)
        self.assertEqual(extended['toy_extended']['summary']['pass'], 110692)
        self.assertTrue(self.summary['headline_checks']['extended_checks_pass'])


if __name__ == '__main__':
    unittest.main()
