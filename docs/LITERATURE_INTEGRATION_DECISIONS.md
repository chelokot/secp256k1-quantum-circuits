# Literature integration decisions

This document explains how external work is used in the repository.

## Directly integrated into repository artifacts

### 1. Public Google baseline

Babbush et al. 2026 is used as the published secp256k1 estimate baseline recorded
in `artifacts/out/resource_projection.json`.

### 2. Validation pressure

Validation-oriented literature informs the repository's emphasis on:

- deterministic replay transcripts
- finite-model family checks
- explicit scope and boundary documents
- benchmark-ladder regression data

### 3. Exact lookup-contract shaping

Lookup and windowing literature informs the signed folded lookup contract, but
the repository only integrates the part that can be stated as an exact contract
and audited directly.

### 4. Scenario translation

Arithmetic-backend and architecture papers are used to define explicit scenario
files and future-work branches rather than being merged into the main headline
without a new exact artifact.

## Used as scenario or future-work inputs

The repository treats the following categories as scenario pressure, not as
direct headline evidence:

- alternative multiplier and adder backends
- deeper lookup-lowering frameworks
- external IR and equivalence tooling
- physical fault-tolerant architecture studies
- alternate low-qubit ECDLP branches

## Why that split exists

The repository's main strength is a short trust path:

- machine-readable artifacts
- transparent Python verification
- local reruns without heavy external stacks

Literature is integrated directly only when the result can be expressed in those
terms.

## Supporting files

- `results/literature_matrix.json`
- `docs/STATE_OF_THE_ART_2026.md`
- `docs/TOOLING_AND_REIMPLEMENTATION_PATHS.md`
- `docs/PHYSICAL_STACKS_AND_HARDWARE_CONTEXT.md`
