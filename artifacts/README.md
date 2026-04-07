# Primary artifact package

This directory contains the primary release artifact of the repository.

## Core files

- `circuits/optimized_pointadd_secp256k1.json` — primary exact secp256k1
  point-add leaf
- `circuits/optimized_pointadd_family.json` — symbolic family netlist
- `circuits/ecdlp_scaffold_optimized.json` — retained-window scaffold
  metadata
- `circuits/ecdlp_expanded_isa_optimized.json` — exact retained-window replay
  of the checked-in leaf over the checked-in scaffold
- `projections/structural_accounting.json` — derived opcode, liveness, and
  scaffold accounting
- `projections/backend_model_bundle.json` — versioned backend-model family
- `projections/resource_projection.json` — modeled baseline comparison and
  headline totals

## Verification files

- `verification/core/optimized_pointadd_audit_16384.csv`
- `verification/core/toy_curve_exhaustive_19850.csv`
- `verification/extended/toy_curve_family_extended_110692.csv`
- `verification/extended/lookup_contract_audit_8192.csv`
- `verification/extended/scaffold_schedule_audit_256.csv`
- `verification/core/verification_summary.json`

## Research files

- `projections/dominant_cost_breakdown.json`
- `lookup/lookup_signed_fold_contract.json`
- `projections/lookup_folded_projection.json`
- `projections/literature_projection_scenarios.json`
- `projections/meta_analysis.json`

## Boundary

This artifact is exact at the arithmetic ISA boundary. Lookup realization,
cleanup realization, and backend totals remain explicit lower layers.
