# Optimization frontiers

This file describes which parts of the resource budget are already improved in
the checked-in artifacts and which parts remain the main frontier.

## Audited mainline

The primary modeled headline stored in
`artifacts/projections/resource_projection.json` is:

- **880 logical qubits** under the conservative named-slot default model
- **22.377M non-Clifford** under the 2-channel lookup model
- **23.295M non-Clifford** under the conservative 3-channel lookup model

That default line is derived from exact structural artifacts plus a
versioned backend-model bundle, not from whole-circuit headline constants.

## Budget split of that mainline

`artifacts/projections/dominant_cost_breakdown.json` records:

- **8.20%** lookup / **91.80%** arithmetic in the 2-channel model
- **11.82%** lookup / **88.18%** arithmetic in the 3-channel model

So the optimized mainline is arithmetic-dominated under the repository's
explicit backend model.

## Lookup frontier

Lookup work is still valuable because:

- the repository exposes lookup contracts explicitly,
- lookup improvements can compose with the current optimized arithmetic leaf,
- the signed folded contract already exists in the primary artifact and exposes a clean path for further lookup-side work.

The signed folded contract projects:

- **22,377,404 non-Clifford** under the folded 2-channel line
- **23,294,908 non-Clifford** under the folded conservative 3-channel line

## Arithmetic and backend frontier

Arithmetic and backend work remain the larger lever because most of the modeled
budget sits outside lookup. The checked-in projection family records this
directly:

- `addsub_modmul_named_slots_v2` is the default explicit arithmetic model, so
  the mainline does not depend on a legacy calibrated multiplier family.
- `addsub_modmul_liveness_v2` keeps that same arithmetic backend but drops to
  **736 logical qubits** if exact ISA-slot liveness is used for backend
  allocation.

The main open directions are therefore:

1. arithmetic-backend substitutions
2. lower-level lookup realization
3. cross-window scheduling and batching
4. fragment flattening plus external equivalence checking

## What would be overclaim

It would be inaccurate to describe the repository as already having:

- a primitive-gate lookup implementation,
- a primitive-gate cleanup proof,
- a fully flattened Shor circuit,
- a theorem-proved backend total.

## Supporting files

- `artifacts/projections/dominant_cost_breakdown.json`
- `artifacts/projections/literature_projection_scenarios.json`
- `artifacts/projections/lookup_folded_projection.json`
- `docs/research/COST_MODEL_CORRECTION.md`
- `docs/research/LOOKUP_FOLDING_RESEARCH_PASS.md`
