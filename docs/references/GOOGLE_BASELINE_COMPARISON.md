# Public Google baseline comparison

This file defines the baseline used when the repository says **Google's
published 2026 secp256k1 estimates** and records the standard-QROM
compiler-family comparison against that baseline.

## Baseline source

The baseline is the rounded public secp256k1 estimate from Babbush et al. 2026
as copied into `compiler_verification_project/artifacts/family_frontier.json`.

The tracked public lines are:

- low-qubit line: **1200 logical qubits**, **90,000,000 non-Clifford**
- low-gate line: **1450 logical qubits**, **70,000,000 non-Clifford**
- window size: **16**
- retained point additions: **28**

## Standard-QROM compiler-family comparison against that baseline

The repository's exact comparison layer is the compiler-family frontier in:

- `compiler_verification_project/artifacts/family_frontier.json`
- `compiler_verification_project/artifacts/standard_qrom_lookup_assessment.json`
- `compiler_verification_project/artifacts/logical_resource_ledger.json`

Its checked public headline is one central standard-QROM family:

- **central standard-QROM family:** `32,879,331 non-Clifford / 1,812 q`

The standard-QROM assessment records that the current central family uses a
standard QROAM coordinate-stream primitive over the full 32768-entry folded
coordinate domain. The ratios below are exact for that selected compiler family
and the public Google rounded baseline.

## Exact non-Clifford comparison

For the **central standard-QROM family**:

- **2.7373x** lower non-Clifford than the public low-qubit line
- **2.1290x** lower non-Clifford than the public low-gate line

## Exact qubit comparison

The standard-QROM frontier does **not** currently beat Google's published
qubit lines:

- the central standard-QROM family is **612 qubits above** the public low-qubit line
- the central standard-QROM family is **362 qubits above** the public low-gate line

The generated QROAMClean tradeoff ledger also records that, in the current
standard-QROAM family, the lowest-qubit point below `24M` non-Clifford is
`23,980,781 / 4,884`, and no checked QROAMClean block-size row reaches both
`<24M` non-Clifford and `<1700` logical qubits.

Lower-exact modeled hypotheses are intentionally separated into
`docs/research/MODELED_IMPLEMENTATION_HYPOTHESES.md`.
