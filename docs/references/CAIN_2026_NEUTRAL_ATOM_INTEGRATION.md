# Cain et al. 2026 neutral-atom transfer

This file explains how the repository's logical secp256k1 projection is
transferred into the neutral-atom architecture model of Cain et al. 2026.

## Inputs being combined

### Repository input

The repository supplies:

- an exact ISA-level arithmetic artifact for the optimized secp256k1 point-add
  stack
- a modeled logical projection in
  `artifacts/projections/resource_projection.json`

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

## Transfer rule

The main supported transfer is a time scaling:

> projected runtime ≈ Cain ECC runtime × (repository non-Clifford budget / public Google baseline non-Clifford budget)

The public Google baseline here is the rounded Babbush et al. 2026 secp256k1
estimate stored in `artifacts/projections/resource_projection.json`.

## Reported time range

Using the repository's two modeled lookup-accounting modes and the tracked
public baseline lines, the stored transfer range is:

- **3.24 to 4.30 days** for the time-efficient architecture
- **85.5 to 113.4 days** for the balanced architecture

## Space transfer

The space transfer is weaker and more model-sensitive than the time transfer.
The file reports:

- **15,779 to 19,067 physical qubits** under naive linear scaling
- **20,890 to 22,533 physical qubits** under a toy model with 50% fixed
  overhead

These space numbers are illustrative transfer outputs, not exact claims.

## Safe interpretation

The defensible claim is:

> If the repository's optimized logical secp256k1 projection is transferred into
> the neutral-atom architecture model of Cain et al. under fixed cycle-time and
> parallelism assumptions, runtime improves substantially, while physical-qubit
> savings are more model-sensitive.

## Not supported by this file

- a direct claim against Cain et al. on its own P-256 target
- an exact physical-qubit count
- an end-to-end formally verified physical implementation

## Machine-readable summary

See `results/cain_2026_integration_summary.json`.
