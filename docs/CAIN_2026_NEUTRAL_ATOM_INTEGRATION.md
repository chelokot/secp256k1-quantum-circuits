# Cain et al. 2026 neutral-atom integration

This note explains how to combine the repository's optimized **logical** secp256k1 resource model with the **physical** neutral-atom architecture estimates in the 2026 paper **"Shor's algorithm is possible with as few as 10,000 reconfigurable atomic qubits"**.

## What is being combined

- **Our side** supplies a transparent, audited, kickmix-ISA-level arithmetic artifact and a backend projection of the optimized secp256k1 ECDLP resource budget.
- **Cain et al. 2026** supplies a physical fault-tolerant architecture model for Shor-style cryptanalysis on neutral-atom hardware, including a headline of about **10 days** for **ECC-256 / P-256** with about **26,000 physical qubits**, and a much slower **balanced** architecture line at **264 days** for ECC-256.

These are not the same object. The paper's physical estimate is for **P-256**, whereas the strongest repository optimization is specialized to **secp256k1**. Therefore the transfer below is an **approximate composition**, not a theorem-proved new headline for P-256.

## Transfer rule used here

The main supported transfer is a **time transfer**:

> projected runtime ≈ Cain ECC runtime × (optimized non-Clifford budget / Google-public baseline non-Clifford budget)

This treats the dominant non-Clifford / Toffoli budget as the leading term, while holding the neutral-atom architecture, cycle time, and parallelism regime fixed.

## Combined estimate range

Using the repository's two lookup-accounting modes and the two public Google appendix comparison lines already tracked in `artifacts/optimized/out/resource_projection.json`, the combined estimate comes out to:

- **time-efficient architecture:** about **3.82 to 5.11 days**
- **balanced architecture:** about **100.9 to 134.8 days**

That range is the most defensible combined headline the repository can presently support.

## Space transfer: use with caution

A straight linear logical-qubit transfer from Cain's **26,000 physical qubits** gives an illustrative range of:

- **naive linear scaling:** about **15878 to 19211 physical qubits**

Because neutral-atom architectures have nontrivial fixed overhead, a more conservative 50%-fixed-overhead toy model gives:

- **half-fixed-overhead scaling:** about **20939 to 22605 physical qubits**

The repository does **not** claim these space numbers are exact. They are included only to show the likely scale of the transfer. The **time transfer is much stronger than the space transfer**.

## Publication-safe wording

A defensible sentence is:

> If the optimized secp256k1 logical layer is transferred into the neutral-atom architecture model of Cain et al. under constant cycle-time and parallelism assumptions, the headline ECC runtime moves from about 10 days to roughly 4-5 days, while physical-qubit savings are likely more modest and much more model-sensitive.

## What not to claim

Do **not** claim any of the following:

- that this repository directly beats Cain et al. on their own **P-256** target without recompiling for P-256,
- that the new physical qubit count is exactly 20k or exactly 26k,
- that the combined result is formally verified end-to-end,
- that the neutral-atom paper is replaced or invalidated by this repository.

## Machine-readable summary

See `results/cain_2026_integration_summary.json` for the exact arithmetic behind the ranges quoted above.
