# Public appendix baseline comparison

This file defines the baseline used when the repository says **public Google
appendix envelope**.

## Baseline source

The baseline is the published appendix envelope from Babbush et al. 2026 as
stored in `artifacts/optimized/out/resource_projection.json`.

The tracked public lines are:

- low-qubit line: **1191 logical qubits**, **81,105,024 non-Clifford**
- low-gate line: **1441 logical qubits**, **64,305,024 non-Clifford**
- window size: **16**
- retained point additions: **28**

## Repository projection compared against that baseline

The primary optimized projection is:

- **880 logical qubits**
- **30,998,464 non-Clifford** under the 2-channel lookup model
- **32,833,472 non-Clifford** under the 3-channel lookup model

## Improvement factors

Versus the public low-qubit line:

- **1.3534x fewer logical qubits**
- **2.6164x lower non-Clifford** under the 2-channel model
- **2.4702x lower non-Clifford** under the 3-channel model

Versus the public low-gate line:

- **1.6375x fewer logical qubits**
- **2.0745x lower non-Clifford** under the 2-channel model
- **1.9585x lower non-Clifford** under the 3-channel model

## Sensitivity margin

The repository also stores hostile-backend margin sweeps in:

- `artifacts/optimized/out/projection_sensitivity.json`
- `artifacts/optimized/figures/projection_headroom.png`

## Boundary

This comparison is between explicit modeled backend totals. It is not a
primitive-gate equivalence proof between two fully lowered circuits.
