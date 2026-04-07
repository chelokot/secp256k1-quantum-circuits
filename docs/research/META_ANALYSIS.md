# Meta-analysis of repository layers

This file compares the repository's cited Google baseline and its optimized
artifact layer.

## Compared layers

### 1. Cited Google baseline

Location: `artifacts/projections/resource_projection.json`

Role:

- define the cited comparison numbers used throughout the repository
- keep the comparison target explicit and inspectable

### 2. Optimized secp256k1 artifact

Location: `artifacts/`

Role:

- provide the primary optimized point-add leaf
- provide the retained-window scaffold metadata
- provide the extended verification and research layers
- provide the modeled baseline comparison

## Quantified internal differences

`artifacts/projections/meta_analysis.json` records the main internal deltas
between the cited Google estimates and the optimized artifact:

- Google low-qubit ECDLP line: `1200 logical qubits`, `90,000,000 non-Clifford`
- Google low-gate ECDLP line: `1450 logical qubits`, `70,000,000 non-Clifford`
- optimized exact leaf: `37` ISA instructions, `12` arithmetic slots

## Main interpretation

The repository's strongest improvement comes from reducing the cost of the
retained point-add leaf while keeping the window structure and comparison
baseline explicit.
