# Modeled implementation hypotheses

This file quarantines the repository's lower-exact modeling layer.

These numbers are **not** the repository's headline result. They are not used
for top-level README claims, verification summaries, or Google-baseline tests.
They remain useful only as implementation hypotheses: candidate lowerings,
allocation ideas, and engineering directions that may eventually be realized in
an exact compiler-family artifact.

## Scope

The modeled layer includes:

- `artifacts/projections/resource_projection.json`
- `artifacts/projections/lookup_folded_projection.json`
- `artifacts/projections/dominant_cost_breakdown.json`
- `artifacts/projections/literature_projection_scenarios.json`
- `artifacts/projections/optimization_frontier_estimates.json`
- `artifacts/projections/projection_sensitivity.json`
- `artifacts/projections/meta_analysis.json`
- `results/research_pass_summary.json`

## Current modeled ideas

The checked-in hypothesis layer currently explores:

- named-slot versus liveness-based backend allocation
- 2-channel versus 3-channel lookup budgeting
- signed folded lookup-contract backend implications
- arithmetic-dominant versus lookup-dominant improvement scenarios
- hostile-overhead sensitivity against the public Google baseline

## Why this layer still exists

These artifacts are useful for:

- identifying promising lowerings to implement in the exact compiler layer
- quantifying which assumptions dominate the current hypothesis stack
- separating “interesting if realized” from “already realized and counted”

## How to read it safely

Treat every number in the files above as:

- an implementation idea,
- a budgeting hypothesis,
- or a prioritization hint for future exact work.

Do not treat those numbers as:

- the repository's primary result,
- an exact whole-oracle count,
- or a proven comparison against another fully lowered circuit.
