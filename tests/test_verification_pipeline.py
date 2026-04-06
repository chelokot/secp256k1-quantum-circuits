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

    def test_public_envelope_inputs_are_present(self):
        envelope = self.summary['public_envelope']
        self.assertEqual(
            envelope['low_qubit_circuit_sha256'],
            '6597edd8832b2210b147e5b84d9f58f9ba8a474771e9465e84f9b8c9d0c0593d',
        )
        self.assertEqual(
            envelope['low_gate_circuit_sha256'],
            'fcbe3420926e934148bb7f21d63618939dc64c6c014c7720e2129bf50e93af2e',
        )


if __name__ == '__main__':
    unittest.main()
