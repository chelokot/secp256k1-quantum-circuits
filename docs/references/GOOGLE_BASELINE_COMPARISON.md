# Public Google baseline comparison

This file defines the baseline used when the repository says **Google's
published 2026 secp256k1 estimates** and records the standard-QROM
compiler-family comparison against that baseline.

## Baseline source

The baseline is the rounded public secp256k1 estimate from Babbush et al. 2026
as stored in `data/public_google_baseline.json`. The compiler build mirrors
that same artifact into
`compiler_verification_project/artifacts/public_google_baseline_source.json`
and uses its `lines` object in
`compiler_verification_project/artifacts/family_frontier.json`.

The tracked public lines are:

- low-qubit line: **1200 logical qubits**, **90,000,000 non-Clifford**
- low-gate line: **1450 logical qubits**, **70,000,000 non-Clifford**
- window size: **16**
- retained point additions: **28**

## Standard-QROM compiler-family comparison against that baseline

The repository's exact comparison layer is the public headline wrapper in:

- `compiler_verification_project/artifacts/strict_replayed_tail_headline.json`
- `compiler_verification_project/artifacts/public_headline_result.json`
- `compiler_verification_project/artifacts/family_frontier.json`
- `compiler_verification_project/artifacts/standard_qrom_lookup_assessment.json`
- `compiler_verification_project/artifacts/logical_resource_ledger.json`

Its checked primary strict headline is one standard-QROAM reusable-chunk family
with the fused-output seven-slot tail:

- **primary strict replayed-tail headline:** `36,957,412 non-Clifford / 1,967 q`

The strict replayed-tail artifact records the seven-slot owner-capacity replay,
the demoted macro-contract reference, and the exact ratios below. The old
`36,957,412 / 1,199` four-slot macro contract remains checked as a
ZKP/publication-wrapper reference, but it is not the primary strict headline.
The older `34,925,796 / 1,044` three-slot family remains checked as a reference
boundary, but it is not the single public headline.

## Exact non-Clifford comparison

For the **primary strict replayed-tail headline**:

- **2.4352x** lower non-Clifford than the public low-qubit line
- **1.8941x** lower non-Clifford than the public low-gate line

## Exact qubit comparison

The public headline does not beat Google's published qubit lines under the
strict replayed-tail count:

- the primary strict replayed-tail headline is **767 qubits above** the public low-qubit line
- the primary strict replayed-tail headline is **517 qubits above** the public low-gate line

The generated QROAMClean tradeoff ledger also records that, in the current
standard-QROAM family, the lowest-qubit point below `24M` non-Clifford is
`23,980,781 / 4,884`, and no checked QROAMClean block-size row reaches both
`<24M` non-Clifford and `<1700` logical qubits.

Lower-exact modeled hypotheses are intentionally separated into
`docs/research/MODELED_IMPLEMENTATION_HYPOTHESES.md`.
