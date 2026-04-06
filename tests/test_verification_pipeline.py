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

    def test_exact_archive_replay_passes(self):
        replay = self.summary['archived_exact']['audit_replay']
        self.assertEqual(replay['total_rows'], 9024)
        self.assertEqual(replay['failed_rows'], 0)
        self.assertEqual(replay['csv_sha256'], '39b0afb2d8059ab0d11c571d4c744576afdec9b8c93b43993092794e8a9b6f32')

    def test_scaffold_linkage_passes(self):
        scaffold = self.summary['archived_exact']['scaffold']
        self.assertTrue(scaffold['oracle_hash_matches_netlist'])
        self.assertEqual(scaffold['call_count'], 28)
        self.assertEqual(scaffold['expected_call_count'], 28)


if __name__ == '__main__':
    unittest.main()
