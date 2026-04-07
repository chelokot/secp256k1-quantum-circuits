# Primary artifact package

This directory contains the primary release artifact of the repository.

## Core files

- `out/optimized_pointadd_secp256k1.json` — primary exact secp256k1 point-add
  leaf
- `out/optimized_pointadd_family.json` — symbolic family netlist
- `out/ecdlp_scaffold_optimized.json` — retained-window scaffold metadata
- `out/resource_projection.json` — modeled baseline comparison and headline
  totals

## Verification files

- `out/optimized_pointadd_audit_16384.csv`
- `out/toy_curve_exhaustive_19850.csv`
- `out/toy_curve_family_extended_110692.csv`
- `out/lookup_contract_audit_8192.csv`
- `out/scaffold_schedule_audit_256.csv`
- `out/verification_summary.json`

## Research files

- `out/dominant_cost_breakdown.json`
- `out/lookup_signed_fold_contract.json`
- `out/lookup_folded_projection.json`
- `out/literature_projection_scenarios.json`
- `out/meta_analysis.json`

## Boundary

This artifact is exact at the arithmetic ISA boundary. Lookup realization,
cleanup realization, and backend totals remain explicit lower layers.
