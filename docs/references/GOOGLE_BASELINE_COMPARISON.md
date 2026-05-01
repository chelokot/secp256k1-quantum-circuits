# Public Google baseline comparison

This file defines the baseline used when the repository says **Google's
published 2026 secp256k1 estimates** and records the named-boundary
compiler-family comparison against that baseline.

## Baseline source

The baseline is the rounded public secp256k1 estimate from Babbush et al. 2026
as copied into `compiler_verification_project/artifacts/family_frontier.json`.

The tracked public lines are:

- low-qubit line: **1200 logical qubits**, **90,000,000 non-Clifford**
- low-gate line: **1450 logical qubits**, **70,000,000 non-Clifford**
- window size: **16**
- retained point additions: **28**

## Named-boundary compiler-family comparison against that baseline

The repository's exact comparison layer is the compiler-family frontier in:

- `compiler_verification_project/artifacts/family_frontier.json`
- `compiler_verification_project/artifacts/standard_qrom_lookup_assessment.json`

Its checked public headline is one central named-boundary family:

- **central named-boundary family:** `23,912,611 non-Clifford / 1,587 q`

This is not an apples-to-apples standard-QROM primitive-circuit comparison. The
standard-QROM assessment records that the current bitwise-banked lookup lowering
does not prove a full arbitrary 32768-entry coordinate-table select. The ratios
below are therefore exact for the repository's named boundary model and public
Google rounded baseline, not a claim that the boundary model has been lowered
to a standard QROM primitive circuit.

## Exact non-Clifford comparison

For the **central named-boundary family**:

- **3.7637x** lower non-Clifford than the public low-qubit line
- **2.9273x** lower non-Clifford than the public low-gate line

## Exact qubit comparison

The named-boundary frontier does **not** currently beat Google's published
qubit lines:

- the central named-boundary family is **387 qubits above** the public low-qubit line
- the central named-boundary family is **137 qubits above** the public low-gate line

Lower-exact modeled hypotheses are intentionally separated into
`docs/research/MODELED_IMPLEMENTATION_HYPOTHESES.md`.
