# Claims and boundaries

This file defines the strongest claims supported by the checked-in artifacts.

## Strongest defensible claim

The repository publishes exact kickmix-ISA arithmetic schedules for a
secp256k1-specialized point-add leaf and explicit retained-window scaffold
metadata, together with deterministic audits, finite-model checks, and a
separate exact compiler-family oracle subproject that closes the
classical-tail-elision gap for a fully quantum raw-32 schedule.

## Exact layers

### 1. Optimized arithmetic leaf

`artifacts/circuits/optimized_pointadd_secp256k1.json` is the primary
machine-readable leaf schedule for:

`Q <- Q + L`

where:

- `Q` is the accumulator in the repository's projective representation
- `L` is an externally supplied affine lookup point
- field arithmetic is over the secp256k1 prime field

This layer is checked by:

- `artifacts/verification/core/optimized_pointadd_audit_16384.csv`
- `artifacts/verification/core/toy_curve_exhaustive_19850.csv`
- `artifacts/verification/extended/toy_curve_family_extended_110692.csv`

### 2. Retained-window scaffold metadata

`artifacts/circuits/ecdlp_scaffold_optimized.json` is a machine-readable
retained-window schedule with:

- one direct seed,
- `28` retained point-add leaf calls,
- `3` classical tail elisions,
- window size `16`.

Its internal coherence is checked by
`artifacts/verification/extended/scaffold_schedule_audit_256.csv`.

### 3. Exact lookup contracts

The repository exposes lookup words, structured folding rules, and audited
semantic points explicitly.
Two exact contract layers are checked:

- the base lookup contract in
  `artifacts/verification/extended/lookup_contract_summary.json`
- the signed folded lookup contract in
  `artifacts/lookup/lookup_signed_fold_contract.json`

The signed folded variant is audited by:

- `artifacts/lookup/lookup_signed_fold_exhaustive_g.csv`
- `artifacts/lookup/lookup_signed_fold_multibase_sampled.csv`


### 4. Exact compiler-family whole-oracle layer

The root-level `compiler_verification_project/` adds the strongest exact layer
below the ISA boundary. It publishes:

- `compiler_verification_project/artifacts/full_raw32_oracle.json`
- `compiler_verification_project/artifacts/family_frontier.json`
- `compiler_verification_project/artifacts/exact_leaf_slot_allocation.json`
- `compiler_verification_project/artifacts/verification_summary.json`

This layer is exact for the **named compiler families** checked into that
subproject. In particular, it fixes:

- a fully quantum raw-32 schedule with no classical tail elisions,
- explicit folded lookup families,
- exact leaf slot allocation, and
- explicit phase-shell families, including a semiclassical-QFT shell.

## Modeled or non-exact layers

### A. Primitive-gate lookup realization

The repository does not lower lookup memory into a primitive-gate qRAM or QROM
construction. It validates the checked-in folded contract fields, ships explicit
compiler-family lookup lowerings below that contract, and proves the lookup
semantics assumed at the ISA boundary. It still stops short of a bit-for-bit
primitive qRAM/QROM netlist.

### B. Primitive-gate cleanup

The shipped no-op control cleanup is exact at the ISA boundary: the same
metadata bit that populates `f_lookup_inf` is applied again to uncompute that
one-bit control after the neutral-entry select path. The repository audits that
coherent flag-cleanup pair directly on deterministic secp256k1 cases.

The repository still does not lower that cleanup pair into a primitive-gate
subcircuit.

### C. Fully flattened Shor gate list

The mainline repository still provides a retained-window scaffold description,
not a single flat primitive-gate circuit for the complete period-finding stack.
The compiler subproject closes more of that gap by publishing an exact raw-32
whole-oracle family, but it still stops short of a globally optimized complete
primitive-gate Shor implementation.

### D. Modeled implementation hypotheses

Lower-exact budgeting artifacts are intentionally isolated in
`docs/research/MODELED_IMPLEMENTATION_HYPOTHESES.md`. They are not the
repository's headline result.

## Public baseline boundary

When this repository refers to the **public Google baseline**, it means the
rounded published lines stored in
`compiler_verification_project/artifacts/family_frontier.json`:

- `1200 logical qubits / 90,000,000 non-Clifford`
- `1450 logical qubits / 70,000,000 non-Clifford`

These are the rounded public estimate lines from Babbush et al. 2026.

## Bottom line

Exact arithmetic leaf semantics: yes.

Exact lookup-contract semantics: yes.

Mainline exact primitive-gate lookup, cleanup, and full Shor flattening: no.

Exact compiler-family whole-oracle counts: yes, in `compiler_verification_project/`, but only for the named compiler families checked into that subproject.

Exact compiler-family comparison against the public Google baseline: yes.
