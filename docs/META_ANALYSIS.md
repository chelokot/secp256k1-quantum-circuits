# Meta-analysis of repository layers

This file compares the repository's cited Google baseline and its optimized
artifact layer.

## Compared layers

### 1. Cited Google appendix baseline

Location: `artifacts/out/resource_projection.json`

Role:

- define the cited comparison numbers used throughout the repository
- keep the comparison target explicit and inspectable

### 2. Optimized secp256k1 artifact

Location: `artifacts/`

Role:

- provide the primary optimized point-add leaf
- provide the retained-window scaffold metadata
- provide the strict verification and research layers
- provide the modeled baseline comparison

## Quantified internal differences

`artifacts/out/meta_analysis.json` records the main internal deltas
between the cited Google estimates and the optimized artifact:

- Google low-qubit ECDLP line: `1191 logical qubits`, `81,105,024 non-Clifford`
- Google low-gate ECDLP line: `1441 logical qubits`, `64,305,024 non-Clifford`
- optimized exact leaf: `37` ISA instructions, `12` arithmetic slots

## Main interpretation

The repository's strongest improvement comes from reducing the cost of the
retained point-add leaf while keeping the window structure and comparison
baseline explicit.
