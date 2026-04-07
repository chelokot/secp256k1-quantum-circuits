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
        cls.boundaries = json.loads((REPO_ROOT / 'artifacts' / 'projections' / 'claim_boundary_matrix.json').read_text())
        cls.meta = json.loads((REPO_ROOT / 'artifacts' / 'projections' / 'meta_analysis.json').read_text())
        cls.sensitivity = json.loads((REPO_ROOT / 'artifacts' / 'projections' / 'projection_sensitivity.json').read_text())
        cls.projection = cls.summary['optimized']['resource_projection']
        cls.lookup_csv = REPO_ROOT / 'artifacts' / 'verification' / 'extended' / 'lookup_contract_audit_8192.csv'
        cls.lookup_leaf = REPO_ROOT / 'artifacts' / 'circuits' / 'optimized_pointadd_secp256k1.json'
        cls.lookup_scaffold = REPO_ROOT / 'artifacts' / 'circuits' / 'ecdlp_scaffold_optimized.json'
        cls.scaffold_csv = REPO_ROOT / 'artifacts' / 'verification' / 'extended' / 'scaffold_schedule_audit_256.csv'
        cls.toy_csv = REPO_ROOT / 'artifacts' / 'verification' / 'extended' / 'toy_curve_family_extended_110692.csv'

    def test_lookup_contract_passes(self):
        lookup = self.extended['lookup_contract']
        self.assertEqual(lookup['summary']['signed_i16']['total'], 4096)
        self.assertEqual(lookup['summary']['signed_i16']['pass'], 4096)
        self.assertEqual(lookup['summary']['unsigned_u16']['total'], 4096)
        self.assertEqual(lookup['summary']['unsigned_u16']['pass'], 4096)
        self.assertEqual(lookup['sha256'], sha256_path(self.lookup_csv))
        expected_seed = sha256_bytes(
            bytes.fromhex(
                sha256_bytes(bytes.fromhex(sha256_path(self.lookup_leaf)) + bytes.fromhex(sha256_path(self.lookup_scaffold)))
            )
        )
        self.assertEqual(lookup['seed_sha256'], expected_seed)

    def test_scaffold_replay_passes(self):
        scaffold = self.extended['scaffold_schedule']
        self.assertEqual(scaffold['summary']['total'], 256)
        self.assertEqual(scaffold['summary']['pass'], 256)
        self.assertEqual(scaffold['summary']['phase_b_base_variants'], 256)
        self.assertEqual(scaffold['sha256'], sha256_path(self.scaffold_csv))

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

    def test_meta_analysis_reductions_are_substantial(self):
        optimized = self.meta['optimized_vs_google_estimates']
        self.assertGreater(optimized['vs_low_qubit_non_clifford_factor'], 2.5)
        self.assertGreater(optimized['vs_low_gate_non_clifford_factor'], 2.0)
        self.assertGreater(optimized['vs_low_qubit_logical_qubit_factor'], 1.3)

    def test_headroom_is_positive(self):
        headroom = self.sensitivity['headroom']
        self.assertGreater(headroom['non_clifford_margin_vs_low_gate_2lookup'], 30_000_000)
        self.assertGreater(headroom['non_clifford_margin_vs_low_qubit_2lookup'], 50_000_000)
        self.assertGreater(headroom['qubit_margin_vs_low_qubit'], 300)

    def test_projection_sensitivity_tracks_current_projection(self):
        optimized = self.projection['optimized_ecdlp_projection']
        self.assertEqual(self.sensitivity['base']['optimized_qubits'], optimized['logical_qubits_total'])
        self.assertEqual(self.sensitivity['base']['optimized_nc_2lookup'], optimized['lookup_model_2channel']['total_non_clifford'])
        self.assertEqual(self.sensitivity['base']['optimized_nc_3lookup'], optimized['lookup_model_3channel']['total_non_clifford'])

    def test_meta_analysis_tracks_current_projection(self):
        optimized_leaf = self.projection['optimized_leaf_projection']
        gains = self.projection['improvement_vs_google']
        self.assertEqual(
            self.meta['optimized_vs_google_estimates']['optimized_leaf_modeled_non_clifford_excluding_lookup'],
            optimized_leaf['modeled_non_clifford_excluding_lookup'],
        )
        self.assertEqual(self.meta['resource_projection_headline'], gains)

    def test_claim_boundary_statuses(self):
        statuses = {layer['layer']: layer['status'] for layer in self.boundaries['layers']}
        self.assertEqual(statuses['optimized_leaf_arithmetic'], 'exact_machine_checked')
        self.assertEqual(statuses['lookup_table_contract'], 'explicit_interface_tested_not_flattened')
        self.assertEqual(statuses['mbuc_cleanup'], 'abstract_contract_only')


if __name__ == '__main__':
    unittest.main()
