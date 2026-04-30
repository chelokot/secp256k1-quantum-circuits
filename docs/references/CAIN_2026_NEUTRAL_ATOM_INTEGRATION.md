# Cain et al. 2026 neutral-atom transfer

This file explains how the repository's exact compiler-family frontier is
transferred into the neutral-atom architecture model of Cain et al. 2026.
The repository's direct physical-estimator integration lives separately in the
Microsoft Resource Estimator artifacts under
`compiler_verification_project/artifacts/`.

## Inputs being combined

### Repository input

The repository supplies:

- an exact ISA-level arithmetic artifact for the optimized secp256k1 point-add
  stack
- an exact compiler-family whole-oracle frontier in
  `compiler_verification_project/artifacts/family_frontier.json`
- a checked Microsoft Resource Estimator target-and-results layer in
  `compiler_verification_project/artifacts/azure_resource_estimator_targets.json`
  and `compiler_verification_project/artifacts/azure_resource_estimator_results.json`
- an exact-family transfer table in
  `compiler_verification_project/artifacts/cain_exact_transfer.json`

### Cain et al. 2026 input

Cain et al. supplies:

- a physical fault-tolerant neutral-atom architecture study
- a headline around **10 days** for **ECC-256 / P-256**
- a reference point around **26,000 physical qubits**
- a slower balanced architecture line around **264 days**

## Boundary of the transfer

The two inputs are not the same object:

- the repository's optimized artifact is specialized to **secp256k1**
- the Cain study is stated for **P-256**

This file therefore describes an approximate transfer study, not a new exact
headline for P-256.

## Transfer rules

The supported transfer keeps runtime and space separate inside the exact-family
table:

- runtime scales against Cain's reference lines by exact-family non-Clifford ratio
- physical qubits scale by exact-family logical-qubit ratio

The public Google baseline here is the rounded Babbush et al. 2026 secp256k1
estimate copied into the exact compiler frontier. The stored range is taken
across the checked exact compiler families.

## Reported time range

Using the checked exact compiler families and the tracked public baseline lines,
the stored runtime range is:

- **2.65 to 5.35 days** for the time-efficient architecture

## Space transfer

The space transfer remains highly family-sensitive because the exact frontier
contains multiple internal compiler-family variants. The current same-density scaling
ranges are:

- **50.6k to 776.9k physical qubits** against Cain's time-efficient line
- **41.9k to 643.0k physical qubits** against Cain's 1450q reference scaling

These space numbers are transfer outputs, not exact claims.

## Safe interpretation

The defensible claim is:

> If the repository's optimized logical secp256k1 projection is transferred into
> the neutral-atom architecture model of Cain et al. under fixed cycle-time and
> parallelism assumptions, the checked exact compiler-family frontier maps to a
> broad range of runtime and space outcomes whose spread is driven by the exact
> family choice.

## Not supported by this file

- a direct claim against Cain et al. on its own P-256 target
- an exact physical-qubit count
- an end-to-end formally verified physical implementation

## Machine-readable summary

See `results/cain_2026_integration_summary.json` and
`compiler_verification_project/artifacts/cain_exact_transfer.json`.
