#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class PublicHeadlineVerifierTests(unittest.TestCase):
    def test_public_headline_verifier_reports_stale_checked_proofs(self):
        result = subprocess.run(
            [sys.executable, 'compiler_verification_project/scripts/verify_public_headline.py'],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report['pass'])
        self.assertFalse(report['metadata_pass'])
        self.assertFalse(report['proof_freshness']['all_current'])
        self.assertEqual(
            report['proof_freshness']['heavy_rebuild_steps_remaining'],
            ['compressed', 'groth16'],
        )
        self.assertIn(
            'public_values_match_input_digest_headers',
            {check['name'] for check in report['failed_checks']},
        )
        public_result = json.loads(
            (REPO_ROOT / 'compiler_verification_project/artifacts/public_headline_result.json').read_text()
        )
        self.assertEqual(report['selected_result'], public_result['selected_result'])
        self.assertLess(
            report['selected_result']['non_clifford'],
            public_result['selection_policy']['limits']['non_clifford_limit_exclusive'],
        )
        self.assertLess(
            report['selected_result']['logical_qubits'],
            public_result['selection_policy']['limits']['logical_qubit_limit_exclusive'],
        )
        self.assertEqual(
            report['checked_proofs']['groth16_verifier_key_sha256'],
            '4125fe6fab5e7d3af4bb9386f49589450a6d37f536e98650adca79768c469975',
        )
        self.assertNotIn('checks', report)
        self.assertLess(len(result.stdout.splitlines()), 400)

    def test_public_headline_verifier_verbose_keeps_full_check_payload(self):
        result = subprocess.run(
            [sys.executable, 'compiler_verification_project/scripts/verify_public_headline.py', '--verbose'],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertIn('checks', report)
        self.assertGreater(len(report['checks']), len(report['failed_checks']))


if __name__ == '__main__':
    unittest.main()
