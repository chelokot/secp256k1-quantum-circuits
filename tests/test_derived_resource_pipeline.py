#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from support import ensure_repo_verification_summary
from derived_resources import minimal_addition_chain  # noqa: E402


class DerivedResourcePipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_repo_verification_summary()
        cls.projection = json.loads((REPO_ROOT / 'artifacts' / 'projections' / 'resource_projection.json').read_text())
        cls.structural = json.loads((REPO_ROOT / 'artifacts' / 'projections' / 'structural_accounting.json').read_text())
        cls.backend = json.loads((REPO_ROOT / 'artifacts' / 'projections' / 'backend_model_bundle.json').read_text())
        cls.expanded = json.loads((REPO_ROOT / 'artifacts' / 'circuits' / 'ecdlp_expanded_isa_optimized.json').read_text())
        cls.leaf = json.loads((REPO_ROOT / 'artifacts' / 'circuits' / 'optimized_pointadd_secp256k1.json').read_text())
        cls.lookup = json.loads((REPO_ROOT / 'artifacts' / 'lookup' / 'lookup_signed_fold_contract.json').read_text())

    def test_expanded_schedule_matches_leaf_and_scaffold(self):
        leaf_count = len(self.leaf['instructions'])
        retained = self.projection['optimized_ecdlp_projection']['retained_window_additions']
        self.assertEqual(self.expanded['expanded_leaf_instruction_count'], leaf_count * retained)
        self.assertEqual(self.expanded['expanded_instruction_count_total'], self.expanded['expanded_leaf_instruction_count'] + 4)

    def test_structural_histogram_matches_leaf(self):
        leaf_hist = self.structural['leaf']['opcode_histogram']
        self.assertEqual(leaf_hist['field_mul'], 11)
        self.assertEqual(leaf_hist['field_add'], 10)
        self.assertEqual(leaf_hist['field_sub'], 3)
        self.assertEqual(leaf_hist['mul_const'], 2)
        self.assertEqual(leaf_hist['select_field_if_flag'], 3)
        self.assertEqual(leaf_hist['lookup_affine_x'], 1)
        self.assertEqual(leaf_hist['lookup_affine_y'], 1)
        self.assertEqual(leaf_hist['lookup_meta'], 1)
        self.assertEqual(self.structural['expanded_scaffold']['leaf_instruction_count'], 1036)

    def test_liveness_and_named_slot_models_are_both_exposed(self):
        self.assertEqual(self.structural['leaf']['allocated_field_slot_count'], 12)
        self.assertEqual(self.structural['leaf']['liveness']['peak_arithmetic_slots']['active_arithmetic_slot_count'], 10)
        default = self.projection['optimized_ecdlp_projection']
        self.assertEqual(default['logical_qubits_total'], 880)
        alt = {entry['model_name']: entry for entry in self.projection['alternative_backend_scenarios']}
        self.assertEqual(alt['carry_save_liveness_alias_v1']['ecdlp']['logical_qubits_total'], 736)

    def test_default_lookup_cost_comes_from_folded_contract(self):
        positive_entries = self.lookup['table_shape']['x_coordinate_table_entries']
        self.assertEqual(positive_entries, 32768)
        default_model_name = self.backend['default_model']
        default_model = next(model for model in self.backend['models'] if model['name'] == default_model_name)
        self.assertEqual(default_model['lookup_model']['non_clifford_per_channel_per_window'], positive_entries)

    def test_mul_const_cost_is_exact_addition_chain_length(self):
        chain = minimal_addition_chain(21)
        self.assertEqual(chain, [1, 2, 4, 8, 16, 20, 21])
        default = self.projection['default_model_details']['per_opcode_non_clifford']
        self.assertEqual(default['mul_const'], 6 * 255)

    def test_explicit_arithmetic_scenario_is_lower_non_clifford(self):
        default_total = self.projection['optimized_ecdlp_projection']['lookup_model_2channel']['total_non_clifford']
        alt = {entry['model_name']: entry for entry in self.projection['alternative_backend_scenarios']}
        self.assertLess(alt['addsub_modmul_explicit_v1']['ecdlp']['lookup_model_2channel']['total_non_clifford'], default_total)
        self.assertLess(alt['addsub_modmul_liveness_v1']['ecdlp']['lookup_model_2channel']['total_non_clifford'], default_total)


if __name__ == '__main__':
    unittest.main()
