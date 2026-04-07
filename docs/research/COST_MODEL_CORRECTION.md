# Cost-model accounting

This file defines the arithmetic-versus-lookup accounting used by the optimized
projection and explains the shares reported elsewhere in the repository. The
mainline numbers are now derived from the checked-in leaf, expanded scaffold,
and backend-model bundle rather than repeated from standalone headline constants.

## Inputs taken from repository artifacts

From `artifacts/projections/resource_projection.json`:

- arithmetic-only cost per retained point-add leaf: `733,657`
- retained point-add leaves in the scaffold: `28`
- modeled arithmetic-only total across the scaffold: `20,542,396`
- modeled 2-channel total: `22,377,404`
- modeled conservative 3-channel total: `23,294,908`

## Derived lookup contribution

Subtracting the full-scaffold arithmetic total from each modeled total gives:

- 2-channel lookup contribution: `1,835,008`
- conservative 3-channel lookup contribution: `2,752,512`

## Share of total modeled cost

The resulting shares are:

- **8.20% lookup / 91.80% arithmetic** in the 2-channel model
- **11.82% lookup / 88.18% arithmetic** in the conservative 3-channel model

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

- `artifacts/projections/dominant_cost_breakdown.json`
- `results/research_pass_summary.json`
- `docs/research/OPTIMIZATION_FRONTIERS.md`
