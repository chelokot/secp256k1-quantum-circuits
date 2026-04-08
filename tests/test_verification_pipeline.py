#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from support import ensure_repo_verification_summary

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from common import sha256_path  # noqa: E402


class VerificationPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = json.loads(ensure_repo_verification_summary().read_text())
        cls.audit_csv = REPO_ROOT / 'artifacts' / 'verification' / 'core' / 'optimized_pointadd_audit_16384.csv'
        cls.toy_csv = REPO_ROOT / 'artifacts' / 'verification' / 'core' / 'toy_curve_exhaustive_19850.csv'
        cls.leaf = REPO_ROOT / 'artifacts' / 'circuits' / 'optimized_pointadd_secp256k1.json'

    def test_optimized_audit_passes(self):
        audit = self.summary['optimized']['audit']
        self.assertEqual(audit['summary']['total'], 16384)
        self.assertEqual(audit['summary']['pass'], 16384)
        self.assertEqual(audit['sha256'], sha256_path(self.audit_csv))
        self.assertEqual(audit['netlist_sha256'], sha256_path(self.leaf))

    def test_optimized_toy_passes(self):
        toy = self.summary['optimized']['toy']
        self.assertEqual(toy['summary']['total'], 19850)
        self.assertEqual(toy['summary']['pass'], 19850)
        self.assertEqual(toy['sha256'], sha256_path(self.toy_csv))

    def test_google_baseline_is_recorded(self):
        baseline = self.summary['google_baseline']
        self.assertEqual(baseline['low_qubit']['logical_qubits'], 1200)
        self.assertEqual(baseline['low_qubit']['non_clifford'], 90_000_000)
        self.assertEqual(baseline['low_gate']['logical_qubits'], 1450)
        self.assertEqual(baseline['low_gate']['non_clifford'], 70_000_000)

    def test_extended_supporting_checks_are_recorded(self):
        extended = self.summary['extended']
        lookup = extended['lookup_contract']['summary']
        cleanup = extended['coherent_cleanup']['summary']
        self.assertEqual(lookup['parameter_checks']['pass'], lookup['parameter_checks']['total'])
        self.assertEqual(lookup['canonical_full_exhaustive']['total'], 65_536)
        self.assertEqual(lookup['canonical_full_exhaustive']['pass'], 65_536)
        self.assertEqual(lookup['multibase_direct_samples']['pass'], lookup['multibase_direct_samples']['total'])
        self.assertEqual(cleanup['pass'], cleanup['total'])
        self.assertEqual(cleanup['categories']['random']['pass'], cleanup['categories']['random']['total'])
        self.assertEqual(extended['scaffold_schedule']['summary']['pass'], 256)
        self.assertEqual(extended['toy_extended']['summary']['pass'], 110692)
        self.assertEqual(extended['challenge_ladder']['summary']['curve_count'], 7)
        self.assertEqual(extended['challenge_ladder']['summary']['pass'], extended['challenge_ladder']['summary']['total'])
        self.assertTrue(self.summary['headline_checks']['extended_checks_pass'])

    def test_compiler_project_checks_are_recorded(self):
        compiler = self.summary['compiler_project']
        build = compiler['build_summary']
        frontier = compiler['frontier']
        verify = compiler['verification_summary']
        self.assertEqual(build['headline']['best_gate_family'], frontier['best_gate_family'])
        self.assertEqual(build['headline']['best_qubit_family'], frontier['best_qubit_family'])
        self.assertEqual(verify['summary']['semantic_cases']['pass'], verify['summary']['semantic_cases']['total'])
        self.assertEqual(verify['summary']['invariant_checks']['pass'], verify['summary']['invariant_checks']['total'])
        self.assertEqual(verify['schedule_checks']['pass'], verify['schedule_checks']['total'])
        self.assertEqual(verify['arithmetic_kernel_checks']['pass'], verify['arithmetic_kernel_checks']['total'])
        self.assertEqual(verify['cleanup_pair_checks']['pass'], verify['cleanup_pair_checks']['total'])
        self.assertEqual(verify['lookup_lowering_checks']['pass'], verify['lookup_lowering_checks']['total'])
        self.assertEqual(verify['generated_block_inventory_checks']['pass'], verify['generated_block_inventory_checks']['total'])
        self.assertEqual(verify['slot_allocation_checks']['pass'], verify['slot_allocation_checks']['total'])
        self.assertEqual(verify['frontier_checks']['pass'], verify['frontier_checks']['total'])
        self.assertEqual(verify['cain_transfer_checks']['pass'], verify['cain_transfer_checks']['total'])
        self.assertEqual(verify['azure_seed_checks']['pass'], verify['azure_seed_checks']['total'])
        baseline = self.summary['google_baseline']
        self.assertAlmostEqual(
            frontier['best_gate_family']['improvement_vs_google_low_qubit'],
            baseline['low_qubit']['non_clifford'] / frontier['best_gate_family']['full_oracle_non_clifford'],
        )
        self.assertAlmostEqual(
            frontier['best_qubit_family']['qubit_ratio_vs_google_low_qubit'],
            baseline['low_qubit']['logical_qubits'] / frontier['best_qubit_family']['total_logical_qubits'],
        )
        self.assertTrue(self.summary['headline_checks']['compiler_exact_checks_pass'])


if __name__ == '__main__':
    unittest.main()
