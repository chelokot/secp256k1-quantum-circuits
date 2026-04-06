# Claims and boundaries

This file defines the strongest claims supported by the checked-in artifacts.

## Strongest defensible claim

The repository publishes exact kickmix-ISA arithmetic schedules for a
secp256k1-specialized point-add leaf and explicit retained-window scaffold
metadata, together with deterministic audits, finite-model checks, and modeled
backend projections against the public appendix baseline of Babbush et al.
2026.

## Exact layers

### 1. Optimized arithmetic leaf

`artifacts/optimized/out/optimized_pointadd_secp256k1.json` is the primary
machine-readable leaf schedule for:

`Q <- Q + L`

where:

- `Q` is the accumulator in the repository's projective representation
- `L` is an externally supplied affine lookup point
- field arithmetic is over the secp256k1 prime field

This layer is checked by:

- `artifacts/optimized/out/optimized_pointadd_audit_16384.csv`
- `artifacts/optimized/out/toy_curve_exhaustive_19850.csv`
- `artifacts/optimized/out/toy_curve_family_extended_110692.csv`

### 2. Archived exact leaf

`artifacts/exact_kickmix/out/pointadd_exact_kickmix.json` is an archived exact
release of the same overall point-add role with a different schedule shape. It
is retained as a reference artifact and replay target.

### 3. Retained-window scaffold metadata

`artifacts/optimized/out/ecdlp_scaffold_optimized.json` is a machine-readable
retained-window schedule with:

- one direct seed,
- `28` retained point-add leaf calls,
- `3` classical tail elisions,
- window size `16`.

Its internal coherence is checked by
`artifacts/optimized/out/scaffold_schedule_audit_256.csv`.

### 4. Exact lookup contracts

The repository exposes lookup words and returned semantic points explicitly.
Two exact contract layers are checked:

- the base lookup contract in
  `artifacts/optimized/out/lookup_contract_summary.json`
- the signed folded lookup contract in
  `artifacts/optimized/out/lookup_signed_fold_contract.json`

The signed folded variant is audited by:

- `artifacts/optimized/out/lookup_signed_fold_exhaustive_g.csv`
- `artifacts/optimized/out/lookup_signed_fold_multibase_sampled.csv`

## Modeled or non-exact layers

### A. Primitive-gate lookup realization

The repository does not lower lookup memory into a primitive-gate qRAM or QROM
construction. It proves the lookup contracts assumed at the ISA boundary.

### B. Primitive-gate cleanup

The `mbuc_*` cleanup operations are represented as abstract cleanup contracts.
The verifier checks basis-state functional behavior, not a coherent
phase-accurate primitive-gate implementation.

### C. Fully flattened Shor gate list

The repository provides a retained-window scaffold description, not a single
flat primitive-gate circuit for the complete period-finding stack.

### D. Backend logical-qubit and non-Clifford totals

The headline totals in
`artifacts/optimized/out/resource_projection.json` and
`artifacts/optimized/out/lookup_folded_projection.json` are explicit backend
projections. They are not theorem-proved primitive-gate totals.

## Public baseline boundary

When this repository refers to the **public appendix baseline**, it means the
published lines stored in
`artifacts/optimized/out/resource_projection.json`:

- `1191 logical qubits / 81,105,024 non-Clifford`
- `1441 logical qubits / 64,305,024 non-Clifford`

These are the public appendix numbers from Babbush et al. 2026. The repository
does not claim to reconstruct any unpublished internal circuit beyond those
published lines.

## Bottom line

Exact arithmetic leaf semantics: yes.

Exact lookup-contract semantics: yes.

Exact primitive-gate lookup, cleanup, and full Shor flattening: no.

Backend projection below the public appendix baseline: yes, but explicitly as a
modeled result.
