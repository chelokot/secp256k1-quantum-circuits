#!/usr/bin/env python3
"""Canonical modeled resource projection for the primary secp256k1 artifact."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from common import artifact_projection_path, dump_json


PUBLIC_GOOGLE_BASELINE = {
    'source': 'Google/Babbush et al. 2026 rounded published secp256k1 estimates',
    'window_size': 16,
    'retained_window_additions': 28,
    'low_qubit': {
        'logical_qubits': 1200,
        'non_clifford': 90_000_000,
    },
    'low_gate': {
        'logical_qubits': 1450,
        'non_clifford': 70_000_000,
    },
}

OPTIMIZED_LEAF_PROJECTION = {
    'scratch_logical_qubits': 864,
    'arithmetic_signature': {
        'field_mul': 11,
        'mul_const_b3': 2,
        'field_add_sub': 13,
    },
    'modeled_non_clifford_excluding_lookup': 976_016,
}

OPTIMIZED_ECDLP_PROJECTION = {
    'window_size': 16,
    'retained_window_additions': 28,
    'logical_qubits_total': 880,
    'lookup_model_2channel': {
        'lookup_channels': 2,
        'per_window_lookup_cost': 65_536,
        'total_non_clifford': 29_163_456,
    },
    'lookup_model_3channel': {
        'lookup_channels': 3,
        'per_window_lookup_cost': 98_304,
        'total_non_clifford': 30_080_960,
    },
}

def compute_improvement_vs_google() -> Dict[str, Dict[str, float]]:
    optimized = OPTIMIZED_ECDLP_PROJECTION
    baseline = PUBLIC_GOOGLE_BASELINE
    optimized_qubits = optimized['logical_qubits_total']
    optimized_2lookup = optimized['lookup_model_2channel']['total_non_clifford']
    optimized_3lookup = optimized['lookup_model_3channel']['total_non_clifford']
    low_qubit = baseline['low_qubit']
    low_gate = baseline['low_gate']
    return {
        'versus_low_qubit': {
            'qubit_gain': low_qubit['logical_qubits'] / optimized_qubits,
            'toffoli_gain_2lookup': low_qubit['non_clifford'] / optimized_2lookup,
            'toffoli_gain_3lookup': low_qubit['non_clifford'] / optimized_3lookup,
        },
        'versus_low_gate': {
            'qubit_gain': low_gate['logical_qubits'] / optimized_qubits,
            'toffoli_gain_2lookup': low_gate['non_clifford'] / optimized_2lookup,
            'toffoli_gain_3lookup': low_gate['non_clifford'] / optimized_3lookup,
        },
    }


def build_resource_projection() -> Dict[str, Any]:
    return {
        'model_name': 'single-lane_carry-save_projection_v1',
        'honesty_note': 'Semantic correctness is exact at the kickmix-ISA level. The non-Clifford and logical-qubit totals below are backend projections, not theorem-proved primitive-gate counts.',
        'public_google_baseline': PUBLIC_GOOGLE_BASELINE,
        'optimized_leaf_projection': OPTIMIZED_LEAF_PROJECTION,
        'optimized_ecdlp_projection': OPTIMIZED_ECDLP_PROJECTION,
        'improvement_vs_google': compute_improvement_vs_google(),
    }


def write_resource_projection(repo_root: Path) -> Dict[str, Any]:
    projection = build_resource_projection()
    dump_json(artifact_projection_path(repo_root / 'artifacts', 'resource_projection.json'), projection)
    return projection
