#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from support import ensure_compiler_project_build_summary, ensure_compiler_project_verification_summary


REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_SRC = REPO_ROOT / 'src'
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from arithmetic_lowering import materialize_arithmetic_primitive_operations  # noqa: E402


class ArithmeticLoweringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_compiler_project_build_summary()
        ensure_compiler_project_verification_summary()
        cls.lowerings = json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'arithmetic_lowerings.json').read_text())
        cls.kernel = json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'module_library.json').read_text())
        cls.generated = json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'generated_block_inventories.json').read_text())
        cls.verification = json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'verification_summary.json').read_text())

    def test_block_totals_reconstruct_from_generated_operations(self):
        for kernel in self.lowerings['kernels']:
            for stage in kernel['stages']:
                for block in stage['blocks']:
                    reconstructed = {'ccx': 0, 'cx': 0, 'x': 0, 'measurement': 0}
                    for operation in materialize_arithmetic_primitive_operations(block):
                        reconstructed[operation[0]] += 1
                    self.assertEqual(reconstructed, block['primitive_counts_total'])

    def test_kernel_totals_reconstruct_from_stages(self):
        for kernel in self.lowerings['kernels']:
            stage_total = sum(stage['non_clifford_total'] for stage in kernel['stages'])
            self.assertEqual(stage_total, kernel['exact_non_clifford_per_kernel'])

    def test_module_library_matches_field_mul_kernel(self):
        field_mul = next(kernel for kernel in self.lowerings['kernels'] if kernel['opcode'] == 'field_mul')
        self.assertEqual(field_mul['exact_non_clifford_per_kernel'], self.kernel['field_mul_non_clifford'])
        self.assertEqual(self.lowerings['family']['name'], self.kernel['name'])

    def test_leaf_reconstruction_matches_module_library(self):
        reconstruction = self.lowerings['leaf_reconstruction']
        self.assertEqual(reconstruction['leaf_opcode_histogram'], self.kernel['leaf_opcode_histogram'])
        self.assertEqual(reconstruction['arithmetic_leaf_non_clifford'], self.kernel['arithmetic_leaf_non_clifford'])

    def test_generated_inventory_uses_arithmetic_lowering_family(self):
        self.assertEqual(self.generated['arithmetic_lowering_family'], self.lowerings['family'])
        arithmetic_blocks = [block for block in self.generated['shared_arithmetic_blocks'] if block['category'] == 'arithmetic_non_clifford']
        self.assertTrue(arithmetic_blocks)
        self.assertTrue(all(block['source_artifact'].endswith('arithmetic_lowerings.json') for block in arithmetic_blocks))

    def test_verification_summary_covers_arithmetic_kernels(self):
        checks = self.verification['arithmetic_kernel_checks']
        self.assertEqual(checks['pass'], checks['total'])


if __name__ == '__main__':
    unittest.main()
