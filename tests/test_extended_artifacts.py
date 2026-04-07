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
        cls.lookup_summary_json = REPO_ROOT / 'artifacts' / 'verification' / 'extended' / 'lookup_contract_summary.json'
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

    def test_meta_analysis_matches_projection_ratios(self):
        optimized = self.meta['optimized_vs_google_estimates']
        gains = self.projection['improvement_vs_google']
        self.assertEqual(optimized['vs_low_qubit_non_clifford_factor'], gains['versus_low_qubit']['toffoli_gain_2lookup'])
        self.assertEqual(optimized['vs_low_gate_non_clifford_factor'], gains['versus_low_gate']['toffoli_gain_2lookup'])
        self.assertEqual(optimized['vs_low_qubit_logical_qubit_factor'], gains['versus_low_qubit']['qubit_gain'])

    def test_headroom_tracks_projection(self):
        headroom = self.sensitivity['headroom']
        optimized = self.projection['optimized_ecdlp_projection']
        baseline = self.projection['public_google_baseline']
        self.assertEqual(
            headroom['non_clifford_margin_vs_low_gate_2lookup'],
            baseline['low_gate']['non_clifford'] - optimized['lookup_model_2channel']['total_non_clifford'],
        )
        self.assertEqual(
            headroom['non_clifford_margin_vs_low_qubit_2lookup'],
            baseline['low_qubit']['non_clifford'] - optimized['lookup_model_2channel']['total_non_clifford'],
        )
        self.assertEqual(
            headroom['qubit_margin_vs_low_qubit'],
            baseline['low_qubit']['logical_qubits'] - optimized['logical_qubits_total'],
        )

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
        self.assertEqual(statuses['lookup_table_contract'], 'exact_contract_semantics_machine_checked_not_flattened')
        self.assertEqual(statuses['mbuc_cleanup'], 'abstract_contract_only')


if __name__ == '__main__':
    unittest.main()
