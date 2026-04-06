# Cost-model correction note

This file records an important internal correction made during the lookup-focused
research pass.

## What was wrong

The optimized resource projection stores:

- a **per-leaf arithmetic-only** non-Clifford estimate, and
- a **whole-scaffold** total for the retained 28 windowed point additions.

An earlier research-pass script accidentally subtracted the per-leaf arithmetic
number from the whole-scaffold total. That made the lookup layer appear to be
about 97% of the total cost.

That was wrong.

## What the corrected accounting is

From `artifacts/optimized/out/resource_projection.json`:

- arithmetic-only per leaf: `976,016`
- retained window additions: `28`
- total arithmetic-only across the scaffold: `27,328,448`
- current 2-channel total: `30,998,464`
- current 3-channel total: `32,833,472`

Therefore:

- 2-channel lookup contribution = `3,670,016`
- 3-channel lookup contribution = `5,505,024`

and the corrected shares are:

- **11.84% lookup / 88.16% arithmetic** in the 2-channel model
- **16.77% lookup / 83.23% arithmetic** in the 3-channel model

## Why this matters

The earlier frontier story was too aggressive. It implied that almost all future
wins had to come from lookup engineering. After correction, that statement is no
longer defensible.

The honest interpretation is now:

- arithmetic still dominates the current modeled total,
- lookup is still a meaningful secondary frontier,
- and a clean lookup-only improvement can still matter because it can be added
  without rewriting the exact arithmetic leaf.

## What changed in the repository

The corrected accounting is now published in:

- `artifacts/optimized/out/dominant_cost_breakdown.json`
- `results/research_pass_summary.json`
- `docs/OPTIMIZATION_FRONTIERS.md`

The lookup-focused research pass then builds on the corrected model rather than
on the mistaken 97% interpretation.
