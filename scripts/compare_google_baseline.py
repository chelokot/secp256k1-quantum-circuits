#!/usr/bin/env python3
"""Print a simple comparison table against the public Google appendix envelope."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
projection = json.loads((REPO_ROOT / 'artifacts' / 'out' / 'resource_projection.json').read_text())
sensitivity = json.loads((REPO_ROOT / 'artifacts' / 'out' / 'projection_sensitivity.json').read_text())
base = projection['public_google_baseline']
opt = projection['optimized_ecdlp_projection']
gain = projection['improvement_vs_google']
head = sensitivity['headroom']

rows = [
    ('Google low-qubit', base['low_qubit']['logical_qubits'], base['low_qubit']['non_clifford']),
    ('Google low-gate', base['low_gate']['logical_qubits'], base['low_gate']['non_clifford']),
    ('Optimized 2-lookup', opt['logical_qubits_total'], opt['lookup_model_2channel']['total_non_clifford']),
    ('Optimized 3-lookup', opt['logical_qubits_total'], opt['lookup_model_3channel']['total_non_clifford']),
]

print('Resource comparison')
print('===================')
for name, qubits, nc in rows:
    print(f'{name:20s}  qubits={qubits:>4d}  non_clifford={nc:>10d}')
print()
print('Improvement factors')
print('===================')
print(f"vs low-qubit: qubits x{gain['versus_low_qubit']['qubit_gain']:.4f}, non-clifford x{gain['versus_low_qubit']['toffoli_gain_2lookup']:.4f} (2-lookup), x{gain['versus_low_qubit']['toffoli_gain_3lookup']:.4f} (3-lookup)")
print(f"vs low-gate : qubits x{gain['versus_low_gate']['qubit_gain']:.4f}, non-clifford x{gain['versus_low_gate']['toffoli_gain_2lookup']:.4f} (2-lookup), x{gain['versus_low_gate']['toffoli_gain_3lookup']:.4f} (3-lookup)")
print()
print('Headroom margins')
print('================')
print(f"2-lookup vs low-gate : +{head['non_clifford_margin_vs_low_gate_2lookup']:,} non-clifford, +{head['qubit_margin_vs_low_gate']} logical qubits")
print(f"2-lookup vs low-qubit: +{head['non_clifford_margin_vs_low_qubit_2lookup']:,} non-clifford, +{head['qubit_margin_vs_low_qubit']} logical qubits")
print(f"3-lookup vs low-gate : +{head['non_clifford_margin_vs_low_gate_3lookup']:,} non-clifford, +{head['qubit_margin_vs_low_gate']} logical qubits")
print(f"3-lookup vs low-qubit: +{head['non_clifford_margin_vs_low_qubit_3lookup']:,} non-clifford, +{head['qubit_margin_vs_low_qubit']} logical qubits")
