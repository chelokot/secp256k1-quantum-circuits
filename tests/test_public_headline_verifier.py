#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class PublicHeadlineVerifierTests(unittest.TestCase):
    def test_public_headline_verifier_passes_checked_metadata(self):
        result = subprocess.run(
            [sys.executable, 'compiler_verification_project/scripts/verify_public_headline.py'],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        report = json.loads(result.stdout)
        self.assertTrue(report['pass'])
        self.assertTrue(report['metadata_pass'])
        self.assertEqual(report['failed_checks'], [])
        self.assertEqual(report['selected_result']['non_clifford'], 36_767_692)
        self.assertEqual(report['selected_result']['logical_qubits'], 1_199)
        self.assertEqual(
            report['checked_proofs']['groth16_verifier_key_sha256'],
            '4125fe6fab5e7d3af4bb9386f49589450a6d37f536e98650adca79768c469975',
        )
        self.assertNotIn('checks', report)


if __name__ == '__main__':
    unittest.main()
