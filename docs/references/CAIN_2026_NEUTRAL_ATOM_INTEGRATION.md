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

## Transfer rules

The supported transfer keeps runtime and space separate:

> projected runtime ≈ Cain ECC runtime × (repository non-Clifford budget / public Google baseline non-Clifford budget)

> projected physical qubits ≈ Cain reference physical qubits × (repository logical qubits / public Google baseline logical qubits)

The public Google baseline here is the rounded Babbush et al. 2026 secp256k1
estimate stored in `artifacts/projections/resource_projection.json`. The stored
range is taken across the current backend-model family and both published Google
comparison lines.

## Reported time range

Using the repository's supported backend-model family and the tracked public
baseline lines, the stored runtime range is:

- **2.49 to 3.33 days** for the time-efficient architecture
- **65.6 to 87.9 days** for the balanced architecture

## Space transfer

The space transfer remains more model-sensitive than the runtime transfer. The
current same-density scaling ranges are:

- **13.2k to 19.1k physical qubits** against Cain's time-efficient line
- **5.1k to 7.3k physical qubits** against Cain's minimum-space line

These space numbers are transfer outputs, not exact claims.

## Safe interpretation

The defensible claim is:

> If the repository's optimized logical secp256k1 projection is transferred into
> the neutral-atom architecture model of Cain et al. under fixed cycle-time and
> parallelism assumptions, the current backend family maps to roughly 2.5 to
> 3.3 days on the time-efficient line, while same-density physical-qubit ranges
> remain more model-sensitive.

## Not supported by this file

- a direct claim against Cain et al. on its own P-256 target
- an exact physical-qubit count
- an end-to-end formally verified physical implementation

## Machine-readable summary

See `results/cain_2026_integration_summary.json`.
