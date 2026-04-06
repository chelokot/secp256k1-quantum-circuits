# Optimization frontiers

The audited mainline headline in this repository is still:

- **880 logical qubits**
- **30.998M non-Clifford** in the 2-lookup model
- **32.833M non-Clifford** in the 3-lookup model

This file distinguishes between:

1. what is already exact and audited,
2. what the corrected cost model says about the current mainline,
3. what the new lookup-folding pass buys,
4. and what would still be overclaim.

## Executive verdict

The most important change in this revision is not a new headline. It is a
**correction**.

An earlier internal research pass misread a per-leaf arithmetic estimate as if
it were the arithmetic cost of the entire 28-call scaffold. After fixing that,
the current explicit backend model says:

- **11.84%** of the 2-channel total sits in the lookup layer
- **16.77%** of the 3-channel total sits in the lookup layer
- **88.16% / 83.23%** sits in the arithmetic layer respectively

So the current mainline is **not** lookup-dominated.

## What the new lookup pass achieves

The repository now adds an exact signed two's-complement lookup-folding branch.

At the contract level this is exact and audited. At the backend-cost level it is
still modeled.

Base-case projected impact:

- **29,163,456** non-Clifford in the folded 2-channel line
- **30,080,960** non-Clifford in the folded 3-channel conservative line

That corresponds to roughly:

- **5.92%** improvement in the 2-channel line
- **8.38%** improvement in the conservative 3-channel line

This is a real gain, but not a second 2x breakthrough.

## What the corrected frontier picture is

### Lookup-only work

Still valuable because:

- it can be integrated without rewriting the exact arithmetic leaf,
- it now has an explicit audited example in this repo,
- and it can compose with deeper backend/lowering work later.

But lookup-only work has bounded leverage under the current model.

### Arithmetic/backend work

Now looks more important than the previous frontier pass suggested.

Because arithmetic dominates the current modeled total, backend substitutions
such as cheaper multiplier realizations can plausibly move the total much more
than a small lookup tweak.

### Combined changes

The most plausible path to another large headline shift is now:

- a better arithmetic backend,
- plus a better lookup contract,
- plus more explicit lowering/scheduling.

## Quantified machine-readable frontiers

See:

- `artifacts/optimized/out/dominant_cost_breakdown.json`
- `artifacts/optimized/out/literature_projection_scenarios.json`
- `artifacts/optimized/out/lookup_folded_projection.json`
- `docs/COST_MODEL_CORRECTION.md`
- `docs/LOOKUP_FOLDING_RESEARCH_PASS.md`

## Ranked next directions

### Highest priority

1. **Arithmetic-backend experiments**
2. **primitive-lower more of the lookup layer**
3. **cross-window scheduling / batching**
4. **fragment flattening + external equivalence checking**

### Medium priority

5. **alternate low-qubit branch**
6. **architecture-sensitive adder and lookup choices**

### Lower priority for the current line

7. tiny leaf reshuffles that do not change the backend model,
8. headline claims imported directly from external architecture papers,
9. replacing audited artifacts with purely heuristic scenario numbers.

## Honesty line

The repository now includes an exact lookup-contract improvement and a corrected
frontier analysis.

The audited 880q / 30.998M / 32.833M mainline headline does **not** change unless
an updated exact artifact itself is shipped and re-audited.
