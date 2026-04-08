#!/usr/bin/env python3

from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from common import SECP_B, SECP_G, SECP_N, SECP_P, affine_to_proj, artifact_circuits_path, load_json, mul_fixed_window, precompute_window_tables  # noqa: E402
from verifier import exec_netlist_with_trace  # noqa: E402


class CleanupSemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.leaf = load_json(artifact_circuits_path(REPO_ROOT / 'artifacts', 'optimized_pointadd_secp256k1.json'))
        cls.tables = precompute_window_tables(SECP_G, SECP_P, SECP_B, width=8, bits=256)

    def _run_case(self, accumulator_scalar: int, lookup_scalar: int) -> None:
        accumulator = mul_fixed_window(accumulator_scalar, self.tables, SECP_P, SECP_B, width=8, order=SECP_N)
        lookup = None if lookup_scalar == 0 else mul_fixed_window(lookup_scalar, self.tables, SECP_P, SECP_B, width=8, order=SECP_N)
        final_proj, trace = exec_netlist_with_trace(
            self.leaf['instructions'],
            SECP_P,
            affine_to_proj(accumulator, SECP_P),
            lookup,
            0 if lookup is None else 1,
            {6, 35, 36},
        )
        pre_cleanup_proj = (trace[35]['qx'] % SECP_P, trace[35]['qy'] % SECP_P, trace[35]['qz'] % SECP_P)
        post_cleanup_proj = (trace[36]['qx'] % SECP_P, trace[36]['qy'] % SECP_P, trace[36]['qz'] % SECP_P)
        expected_flag = 1 if lookup is None else 0
        self.assertEqual(trace[6]['f_lookup_inf'], expected_flag)
        self.assertEqual(trace[35]['f_lookup_inf'], expected_flag)
        self.assertEqual(trace[36]['f_lookup_inf'], 0)
        self.assertEqual(trace[35]['meta'], expected_flag)
        self.assertEqual(trace[36]['meta'], expected_flag)
        self.assertEqual(pre_cleanup_proj, post_cleanup_proj)
        self.assertEqual(post_cleanup_proj, final_proj)

    def test_lookup_infinity_cleanup(self):
        self._run_case(accumulator_scalar=7, lookup_scalar=0)

    def test_nonzero_lookup_cleanup(self):
        self._run_case(accumulator_scalar=7, lookup_scalar=5)


if __name__ == '__main__':
    unittest.main()
