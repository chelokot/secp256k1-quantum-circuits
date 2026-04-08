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

from common import sha256_bytes, sha256_path  # noqa: E402


class ExtendedArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = json.loads(ensure_repo_verification_summary().read_text())
        cls.extended = cls.summary['extended']
        cls.compiler = cls.summary['compiler_project']
        cls.frontier = cls.compiler['frontier']
        cls.boundaries = json.loads((REPO_ROOT / 'artifacts' / 'projections' / 'claim_boundary_matrix.json').read_text())
        cls.lookup_summary_json = REPO_ROOT / 'artifacts' / 'verification' / 'extended' / 'lookup_contract_summary.json'
        cls.cleanup_summary_json = REPO_ROOT / 'artifacts' / 'verification' / 'extended' / 'coherent_cleanup_summary.json'
        cls.cleanup_csv = REPO_ROOT / 'artifacts' / 'verification' / 'extended' / 'coherent_cleanup_audit_16384.csv'
        cls.lookup_contract = REPO_ROOT / 'artifacts' / 'lookup' / 'lookup_signed_fold_contract.json'
        cls.lookup_research_summary = REPO_ROOT / 'artifacts' / 'lookup' / 'lookup_signed_fold_summary.json'
        cls.scaffold_csv = REPO_ROOT / 'artifacts' / 'verification' / 'extended' / 'scaffold_schedule_audit_256.csv'
        cls.toy_csv = REPO_ROOT / 'artifacts' / 'verification' / 'extended' / 'toy_curve_family_extended_110692.csv'

    def test_lookup_contract_passes(self):
        lookup = self.extended['lookup_contract']
        summary = lookup['summary']
        self.assertEqual(summary['parameter_checks']['pass'], summary['parameter_checks']['total'])
        self.assertEqual(summary['canonical_full_exhaustive']['total'], 65_536)
        self.assertEqual(summary['canonical_full_exhaustive']['pass'], 65_536)
        self.assertEqual(summary['multibase_direct_samples']['pass'], summary['multibase_direct_samples']['total'])
        self.assertEqual(lookup['sha256'], sha256_path(self.lookup_summary_json))
        self.assertEqual(lookup['contract_sha256'], sha256_path(self.lookup_contract))
        self.assertEqual(lookup['lookup_research_summary_sha256'], sha256_path(self.lookup_research_summary))

    def test_scaffold_replay_passes(self):
        scaffold = self.extended['scaffold_schedule']
        self.assertEqual(scaffold['summary']['total'], 256)
        self.assertEqual(scaffold['summary']['pass'], 256)
        self.assertEqual(scaffold['summary']['phase_b_base_variants'], 256)
        self.assertEqual(scaffold['sha256'], sha256_path(self.scaffold_csv))

    def test_coherent_cleanup_passes(self):
        cleanup = self.extended['coherent_cleanup']
        summary = cleanup['summary']
        self.assertEqual(summary['total'], 16_384)
        self.assertEqual(summary['pass'], 16_384)
        self.assertEqual(summary['categories']['lookup_infinity']['pass'], summary['categories']['lookup_infinity']['total'])
        self.assertEqual(cleanup['csv_sha256'], sha256_path(self.cleanup_csv))
        self.assertEqual(cleanup['sha256'], sha256_path(self.cleanup_summary_json))

    def test_extended_toy_family_passes(self):
        toy = self.extended['toy_extended']
        self.assertEqual(toy['summary']['total'], 110692)
        self.assertEqual(toy['summary']['pass'], 110692)
        self.assertEqual(toy['sha256'], sha256_path(self.toy_csv))

    def test_challenge_ladder_passes(self):
        ladder = self.extended['challenge_ladder']
        self.assertEqual(ladder['summary']['curve_count'], 7)
        self.assertEqual(ladder['summary']['total'], ladder['summary']['pass'])
        self.assertGreaterEqual(ladder['summary']['total'], 700)

    def test_exact_gate_frontier_matches_baseline_ratios(self):
        baseline = self.frontier['public_google_baseline']
        gate = self.frontier['best_gate_family']
        self.assertAlmostEqual(gate['improvement_vs_google_low_qubit'], baseline['low_qubit']['non_clifford'] / gate['full_oracle_non_clifford'])
        self.assertAlmostEqual(gate['improvement_vs_google_low_gate'], baseline['low_gate']['non_clifford'] / gate['full_oracle_non_clifford'])

    def test_exact_qubit_frontier_matches_baseline_ratios(self):
        baseline = self.frontier['public_google_baseline']
        qubit = self.frontier['best_qubit_family']
        self.assertAlmostEqual(qubit['qubit_ratio_vs_google_low_qubit'], baseline['low_qubit']['logical_qubits'] / qubit['total_logical_qubits'])
        self.assertAlmostEqual(qubit['qubit_ratio_vs_google_low_gate'], baseline['low_gate']['logical_qubits'] / qubit['total_logical_qubits'])
        self.assertAlmostEqual(qubit['improvement_vs_google_low_qubit'], baseline['low_qubit']['non_clifford'] / qubit['full_oracle_non_clifford'])

    def test_claim_boundary_statuses(self):
        statuses = {layer['layer']: layer['status'] for layer in self.boundaries['layers']}
        self.assertEqual(statuses['optimized_leaf_arithmetic'], 'exact_machine_checked')
        self.assertEqual(statuses['lookup_table_contract'], 'exact_contract_semantics_machine_checked_not_flattened')
        self.assertEqual(statuses['mbuc_cleanup'], 'exact_isa_coherent_pair_machine_checked_not_flattened')


if __name__ == '__main__':
    unittest.main()
