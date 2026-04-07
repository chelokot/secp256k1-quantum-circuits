# Cost-model accounting

This file defines the arithmetic-versus-lookup accounting used by the optimized
projection and explains the shares reported elsewhere in the repository.

## Inputs taken from repository artifacts

From `artifacts/out/resource_projection.json`:

- arithmetic-only cost per retained point-add leaf: `976,016`
- retained point-add leaves in the scaffold: `28`
- modeled arithmetic-only total across the scaffold: `27,328,448`
- modeled 2-channel total: `29,163,456`
- modeled conservative 3-channel total: `30,080,960`

## Derived lookup contribution

Subtracting the full-scaffold arithmetic total from each modeled total gives:

- 2-channel lookup contribution: `1,835,008`
- conservative 3-channel lookup contribution: `2,752,512`

## Share of total modeled cost

The resulting shares are:

- **6.29% lookup / 93.71% arithmetic** in the 2-channel model
- **9.15% lookup / 90.85% arithmetic** in the conservative 3-channel model

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
