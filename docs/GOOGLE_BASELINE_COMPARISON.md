# Public Google baseline comparison

This file defines the baseline used when the repository says **Google's
published 2026 secp256k1 estimates**.

## Baseline source

The baseline is the rounded public secp256k1 estimate from Babbush et al. 2026
as stored in `artifacts/out/resource_projection.json`.

The tracked public lines are:

- low-qubit line: **1200 logical qubits**, **90,000,000 non-Clifford**
- low-gate line: **1450 logical qubits**, **70,000,000 non-Clifford**
- window size: **16**
- retained point additions: **28**

## Repository projection compared against that baseline

The primary optimized projection is:

- **880 logical qubits**
- **29,163,456 non-Clifford** under the 2-channel lookup model
- **30,080,960 non-Clifford** under the conservative 3-channel lookup model

## Improvement factors

Versus the public low-qubit line:

- **1.3636x fewer logical qubits**
- **3.0861x lower non-Clifford** under the 2-channel model
- **2.9919x lower non-Clifford** under the conservative 3-channel model

Versus the public low-gate line:

- **1.6477x fewer logical qubits**
- **2.4003x lower non-Clifford** under the 2-channel model
- **2.3271x lower non-Clifford** under the conservative 3-channel model

## Sensitivity margin

The repository also stores hostile-backend margin sweeps in:

- `artifacts/out/projection_sensitivity.json`
- `artifacts/figures/projection_headroom.png`

## Boundary

This comparison is between explicit modeled backend totals. It is not a
primitive-gate equivalence proof between two fully lowered circuits.
