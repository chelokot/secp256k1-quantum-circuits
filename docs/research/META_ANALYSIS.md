# Meta-analysis of repository layers

This file compares the repository's cited Google baseline and its exact
artifact layers.

## Compared layers

### 1. Cited Google baseline

Location: `compiler_verification_project/artifacts/family_frontier.json`

Role:

- define the cited comparison numbers used throughout the exact comparison layer
- keep the comparison target explicit and inspectable

### 2. Exact artifact layers

Locations:

- `artifacts/`
- `compiler_verification_project/`

Role:

- provide the primary optimized point-add leaf
- provide the retained-window scaffold metadata
- provide the extended verification layers
- provide the exact compiler-family whole-oracle comparison

## Quantified internal differences

The structural comparison between the published baseline framing and the
optimized artifact family includes:

- Google low-qubit ECDLP line: `1200 logical qubits`, `90,000,000 non-Clifford`
- Google low-gate ECDLP line: `1450 logical qubits`, `70,000,000 non-Clifford`
- optimized exact leaf: `37` ISA instructions, `12` named arithmetic slots
- expanded retained-window replay: `1036` exact leaf instructions over `28` retained additions

## Main interpretation

The repository's strongest current result comes from pairing the optimized
retained point-add leaf with a standard-QROM compiler-family whole-oracle
frontier while keeping the public comparison baseline explicit. It is not a
standard-QROM primitive-circuit comparison.
