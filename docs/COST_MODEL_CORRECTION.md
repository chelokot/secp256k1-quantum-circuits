# Cost-model accounting

This file defines the arithmetic-versus-lookup accounting used by the optimized
projection and explains the shares reported elsewhere in the repository.

## Inputs taken from repository artifacts

From `artifacts/out/resource_projection.json`:

- arithmetic-only cost per retained point-add leaf: `976,016`
- retained point-add leaves in the scaffold: `28`
- modeled arithmetic-only total across the scaffold: `27,328,448`
- modeled 2-channel total: `30,998,464`
- modeled 3-channel total: `32,833,472`

## Derived lookup contribution

Subtracting the full-scaffold arithmetic total from each modeled total gives:

- 2-channel lookup contribution: `3,670,016`
- 3-channel lookup contribution: `5,505,024`

## Share of total modeled cost

The resulting shares are:

- **11.84% lookup / 88.16% arithmetic** in the 2-channel model
- **16.77% lookup / 83.23% arithmetic** in the 3-channel model

## Interpretation

Under the repository's explicit backend model:

- arithmetic dominates the mainline total,
- lookup remains a meaningful secondary frontier,
- lookup-only improvements can still matter because they compose with the exact
  arithmetic leaf,
- another large overall drop would eventually require arithmetic-backend,
  scheduling, or combined changes.

## Machine-readable outputs

See:

- `artifacts/out/dominant_cost_breakdown.json`
- `results/research_pass_summary.json`
- `docs/OPTIMIZATION_FRONTIERS.md`
