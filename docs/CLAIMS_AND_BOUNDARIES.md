# Claims and boundaries

This file is the shortest honest statement of what the repository *does* and *does not* prove.

## Strongest defensible claim

The repository publishes an **exact kickmix-ISA arithmetic netlist** for a secp256k1-specialized complete mixed addition leaf, plus deterministic audits and finite-model family checks, and a **modeled** backend projection showing a large improvement over the **public** Google appendix envelope.

## Exact layers

### 1. Optimized arithmetic leaf
The file `artifacts/optimized/out/optimized_pointadd_secp256k1.json` is a machine-readable instruction schedule for:

`Q <- Q + L`

where:
- `Q` is the accumulator in the repository's homogeneous projective representation,
- `L` is an externally supplied affine lookup point,
- field arithmetic is over secp256k1's prime field.

This layer is checked by:
- `optimized_pointadd_audit_16384.csv`
- `toy_curve_exhaustive_19850.csv`
- `toy_curve_family_extended_110692.csv`

### 2. Archived exact leaf
The file `artifacts/exact_kickmix/out/pointadd_exact_kickmix.json` is a more verbose archived exact artifact.
It remains useful as a semantic reference point and as a comparison baseline for the optimized leaf.

### 3. Finite-model family checks
The optimized family netlist is exhaustively checked on four prime-order `j = 0` toy curves.
That is a genuine exhaustive finite-model result, not a random sample.

### 4. Signed folded lookup contract
The files `artifacts/optimized/out/lookup_signed_fold_contract.json` and
`artifacts/optimized/out/ecdlp_scaffold_lookup_folded.json` define an exact
lookup-contract variant that folds signed 16-bit two's-complement lookup words
through secp256k1 negation symmetry.

This layer is checked by:
- `lookup_signed_fold_exhaustive_g.csv`
- `lookup_signed_fold_multibase_sampled.csv`

It is exact at the contract/semantics level, but it is still not a primitive-gate
qRAM realization.

## Explicitly non-exact layers

### A. Lookup memory / qRAM
The leaf netlists do **not** flatten the lookup machinery into primitive gates.

Instead, they expose a lookup boundary:
- affine `x`
- affine `y`
- metadata flags

The publication-hardening pass adds `lookup_contract_audit_8192.csv` to make this boundary explicit and testable, but this is still not a primitive-gate qRAM construction.

### B. MBUC cleanup
The archived leaf contains `mbuc_clear` operations and the optimized leaf contains `mbuc_clear_bool`.
These are abstract cleanup contracts, not flattened reversible gates.

The verifier checks basis-state functional semantics.
It does **not** prove phase-correct cleanup in a fully coherent primitive-gate model.

### C. Hierarchical retained-window scaffold
`ecdlp_scaffold_optimized.json` is a machine-readable retained-window schedule compatible with the public appendix count.
It is not a flat gate list for the whole Shor period-finding stack.

The strict verifier adds `scaffold_schedule_audit_256.csv` to show that the published schedule is semantically coherent on deterministic secp256k1 instances.

### D. Backend qubit / non-Clifford totals
The headline `880q / 31.0M-32.8M` numbers live below the ISA boundary.
They are explicit backend projections, not theorem-proved primitive-gate totals.

Read:
- `artifacts/optimized/out/resource_projection.json`
- `artifacts/optimized/out/projection_sensitivity.json`

## Public-comparison boundary

The comparison target in this repository is the **public** Google appendix envelope:
- `1191 / 81,105,024`
- `1441 / 64,305,024`

This repository does **not** claim recovery of Google's unpublished hidden circuit.

## Bottom line

If you want one sentence:

**Exact arithmetic leaf and exact finite-model checks: yes.  
Exact primitive-gate qRAM + cleanup + full Shor gate list: no.  
Backend projection beating the public appendix envelope: yes, but explicitly modeled.**
