# Research boundary

This repository is an open audit package, not an end-to-end primitive-gate
proof release.

## What the repository does

- publishes exact kickmix-ISA point-add artifacts for secp256k1
- publishes deterministic secp256k1 replay audits and finite-model checks
- publishes explicit retained-window scaffold metadata
- publishes explicit lookup contracts, including a signed folded variant
- publishes a transparent Python verifier
- publishes modeled logical-qubit and non-Clifford projections
- compares those modeled projections with the published Google baseline of
  Babbush et al. 2026

## What the repository does not claim

- it does not claim recovery of an unpublished Google internal circuit
- it does not claim primitive-gate lowering of lookup memory
- it does not claim primitive-gate verification of `mbuc_*` cleanup
- it does not claim a single flat gate list for the full Shor stack
- it does not claim theorem-proved backend logical-qubit or non-Clifford totals

## Strongest exact layer

The strongest exact layer is the basis-state arithmetic semantics of the
point-add leaf, supported by deterministic secp256k1 replay and finite-model
family checks.

## Main modeled layer

The main modeled layer is the translation from ISA-level arithmetic and lookup
contracts into backend logical-qubit and non-Clifford totals.

## Baseline definition

The repository's public comparison baseline is the rounded published secp256k1
estimate from Babbush et al. 2026:

- low-qubit: `1200 logical qubits / 90,000,000 non-Clifford`
- low-gate: `1450 logical qubits / 70,000,000 non-Clifford`

Those are the only Google numbers this repository claims to compare against.
