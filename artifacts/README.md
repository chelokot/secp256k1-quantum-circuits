# Primary artifact package

This directory contains the primary release artifact of the repository.

## Core files

- `out/circuits/optimized_pointadd_secp256k1.json` — primary exact secp256k1
  point-add leaf
- `out/circuits/optimized_pointadd_family.json` — symbolic family netlist
- `out/circuits/ecdlp_scaffold_optimized.json` — retained-window scaffold
  metadata
- `out/projections/resource_projection.json` — modeled baseline comparison and
  headline totals

## Verification files

- `out/verification/core/optimized_pointadd_audit_16384.csv`
- `out/verification/core/toy_curve_exhaustive_19850.csv`
- `out/verification/extended/toy_curve_family_extended_110692.csv`
- `out/verification/extended/lookup_contract_audit_8192.csv`
- `out/verification/extended/scaffold_schedule_audit_256.csv`
- `out/verification/core/verification_summary.json`

## Research files

- `out/projections/dominant_cost_breakdown.json`
- `out/lookup/lookup_signed_fold_contract.json`
- `out/projections/lookup_folded_projection.json`
- `out/projections/literature_projection_scenarios.json`
- `out/projections/meta_analysis.json`

## Boundary

This artifact is exact at the arithmetic ISA boundary. Lookup realization,
cleanup realization, and backend totals remain explicit lower layers.
