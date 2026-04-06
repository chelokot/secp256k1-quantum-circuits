#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from common import sha256_path  # noqa: E402


class RepoIntegrityTests(unittest.TestCase):
    def test_key_reports_exist(self):
        for name in [
            'secp256k1_optimized_880q_31p0M_2p62x_report.pdf',
            'secp256k1_exact_kickmix_netlist_report.pdf',
            'secp256k1_reconstruction_1191q_81p1M_1441q_64p3M_audit.pdf',
        ]:
            path = REPO_ROOT / 'reports' / name
            self.assertTrue(path.exists(), path)
            self.assertGreater(path.stat().st_size, 100_000)

    def test_hash_manifest_matches_selected_files(self):
        subprocess.run([sys.executable, 'scripts/hash_repo.py'], cwd=REPO_ROOT, check=True)
        manifest_lines = (REPO_ROOT / 'MANIFEST.sha256').read_text().splitlines()
        manifest = {}
        for line in manifest_lines:
            digest, rel = line.split('  ', 1)
            manifest[rel] = digest
        selected = [
            'reports/secp256k1_optimized_880q_31p0M_2p62x_report.pdf',
            'artifacts/optimized/out/optimized_pointadd_secp256k1.json',
            'artifacts/exact_kickmix/out/pointadd_exact_kickmix.json',
        ]
        for rel in selected:
            self.assertIn(rel, manifest)
            self.assertEqual(manifest[rel], sha256_path(REPO_ROOT / rel))


if __name__ == '__main__':
    unittest.main()
