# Signed lookup-folding contract

This document describes the repository's exact signed lookup-contract
optimization for the retained-window point-add stack.

## Goal

Reduce the lookup-domain size without changing the optimized arithmetic leaf in
`artifacts/circuits/optimized_pointadd_secp256k1.json`.

## Contract definition

The public appendix framing uses a `w`-bit signed lookup address. For
secp256k1, the repository exploits the group-law identity:

`[-d]U = (x([d]U), -y([d]U))`

For a 16-bit signed word `d`, the contract is:

1. interpret the raw 16-bit word as signed two's-complement,
2. fold the table to magnitudes `|d|` in `0..32767`,
3. treat `0x8000` as a dedicated exceptional constant,
4. derive zero and sign metadata from the raw word,
5. negate the looked-up `y` coordinate when `d < 0`.

## Exact checked artifacts

The exact contract-level artifacts are:

- `artifacts/lookup/lookup_signed_fold_contract.json`
- `artifacts/circuits/ecdlp_scaffold_lookup_folded.json`
- `artifacts/lookup/lookup_signed_fold_summary.json`

The contract summary records:

- raw word domain size: `65,536`
- folded entries per coordinate: `32,768`
- exhaustive canonical-base audit: `65,536 / 65,536` pass
- additional multibase semantic samples: `15,906 / 15,906` pass

## What is exact

- signed-word decomposition
- folded lookup-domain semantics
- returned affine point semantics
- folded scaffold metadata

## Remaining implementation gap

The strongest contract-level conclusion is a 2x reduction in the per-coordinate
table domain together with exact audited signed-word semantics. Lower-exact
budget hypotheses for this contract are isolated in
`docs/research/MODELED_IMPLEMENTATION_HYPOTHESES.md`.

## Why this optimization matters

This optimization is:

- algebraically explicit,
- exact at the contract layer,
- heavily audited,
- compatible with the existing optimized arithmetic leaf,
- easy to compare against other lookup-lowering strategies.
