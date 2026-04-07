# Public Google baseline comparison

This file defines the baseline used when the repository says **Google's
published 2026 secp256k1 estimates**.

## Baseline source

The baseline is the rounded public secp256k1 estimate from Babbush et al. 2026
as stored in `artifacts/projections/resource_projection.json`.

The tracked public lines are:

- low-qubit line: **1200 logical qubits**, **90,000,000 non-Clifford**
- low-gate line: **1450 logical qubits**, **70,000,000 non-Clifford**
- window size: **16**
- retained point additions: **28**

## Repository projection compared against that baseline

The primary optimized projection is the default derived backend model rebuilt
from:

- `artifacts/circuits/optimized_pointadd_secp256k1.json`
- `artifacts/circuits/ecdlp_scaffold_optimized.json`
- `artifacts/circuits/ecdlp_expanded_isa_optimized.json`
- `artifacts/lookup/lookup_signed_fold_contract.json`
- `artifacts/projections/backend_model_bundle.json`

Its current default headline is:

- **880 logical qubits**
- **22,377,404 non-Clifford** under the 2-channel lookup model
- **23,294,908 non-Clifford** under the conservative 3-channel lookup model

## Improvement factors

Versus the public low-qubit line:

- **1.3636x fewer logical qubits**
- **4.0219x lower non-Clifford** under the 2-channel model
- **3.8635x lower non-Clifford** under the conservative 3-channel model

Versus the public low-gate line:

- **1.6477x fewer logical qubits**
- **3.1282x lower non-Clifford** under the 2-channel model
- **3.0049x lower non-Clifford** under the conservative 3-channel model

## Alternative backend scenarios

The same structural artifact family also ships experimental alternatives:

- `addsub_modmul_liveness_v2` — same explicit arithmetic backend, but qubits
  priced from exact ISA liveness rather than named-slot allocation

These appear in `alternative_backend_scenarios` inside
`artifacts/projections/resource_projection.json`.

## Sensitivity margin

The repository also stores hostile-backend margin sweeps in:

- `artifacts/projections/projection_sensitivity.json`
- `figures/core/projection_headroom.png`

## Boundary

This comparison is between explicit modeled backend totals. It is not a
primitive-gate equivalence proof between two fully lowered circuits.
