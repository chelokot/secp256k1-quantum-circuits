# Meta-analysis of artifact families

This file compares the two active artifact families stored in the repository.

## Artifact families

### 1. Public-envelope reconstruction

Location: `artifacts/public_envelope/`

Role:

- preserve the public appendix-aligned reconstruction data
- keep the comparison target concrete and inspectable

### 2. Optimized secp256k1 artifact

Location: `artifacts/optimized/`

Role:

- provide the primary optimized point-add leaf
- provide the retained-window scaffold metadata
- provide the strict verification and research layers
- provide the modeled baseline comparison

## Quantified internal differences

`artifacts/optimized/out/meta_analysis.json` records the main internal deltas
between the public-envelope contracts and the optimized artifact:

- public low-qubit point-add contract: `1175 logical qubits`, `2,700,000 non-Clifford`
- public low-gate point-add contract: `1425 logical qubits`, `2,100,000 non-Clifford`
- optimized exact leaf: `37` ISA instructions, `12` arithmetic slots

## Main interpretation

The repository's strongest improvement comes from reducing the cost of the
retained point-add leaf while keeping the window structure and comparison
baseline explicit.
