# Research boundary

This bundle is intentionally scoped as an open, auditable reconstruction package.

## What it does

- publishes exact kickmix-ISA arithmetic netlists and the optimized secp256k1-specialized variant,
- publishes deterministic secp256k1 audit transcripts and exhaustive finite-model family transcripts,
- publishes a transparent standard-library verifier,
- publishes a retained-window scaffold compatible with the public appendix count,
- compares the optimized backend projection against the public resource envelope from Google's cryptocurrency whitepaper,
- publishes an internal red-team review and sensitivity sweep.

## What it does not claim

- it does not claim recovery of Google's unpublished hidden gate-level circuit,
- it does not claim theorem-proved primitive-gate flattening below the kickmix ISA,
- it does not claim that lookup memory is already flattened into a primitive-gate qRAM construction,
- it does not claim that MBUC cleanup is already primitive-gate verified,
- it does not claim that the backend non-Clifford counts are formally verified below the ISA level.

## Strongest exact layer

The strongest exact layer here is:

**basis-state arithmetic semantics of the point-add leaf at the kickmix ISA boundary, plus finite-model family checks and deterministic secp256k1 audit replay.**

## Main non-exact layers

The main non-exact layers are:

- lookup interface,
- cleanup contract,
- full-Shor scaffold flattening,
- backend lowering into logical-qubit / non-Clifford totals.

## Source boundary used while assembling these materials

- the core comparison baseline is the public Google whitepaper appendix,
- the main optimization rationale follows complete mixed addition on short Weierstrass `a = 0 / j = 0` curves,
- no 2026 implementation writeups are vendored into this repository.
