# Meta-analysis: where the progress came from

This file compares the repository's own artifacts, not any 2026 implementation leak.

## Progression inside this repository

### Stage 1 — public-envelope reconstruction
Goal:
recover an open, auditable circuit family that matches the **public** Google appendix envelope.

Strength:
- ties the work to public numbers,
- makes the comparison target explicit.

Limitation:
- still mostly a resource-aligned reconstruction, not an exact micro-architectural artifact.

### Stage 2 — archived exact kickmix artifact
Goal:
publish an exact ISA-level leaf and transcript replay.

Strength:
- exact machine-readable arithmetic schedule,
- transcript replay on secp256k1,
- exact scaffold hash linkage.

Limitation:
- verbose,
- wider working set,
- still exception-heavy,
- still not where the best arithmetic/formula tradeoff lives.

### Stage 3 — optimized secp256k1-specialized artifact
Goal:
keep the public retained-window structure but radically shrink the hot path.

Strength:
- 37 instructions instead of 90,
- 12 arithmetic slots instead of 41 working registers,
- strong secp256k1 audit plus independent reference paths,
- substantial backend-projection margin over the public Google envelope.

## Quantified internal deltas

See `artifacts/optimized/out/meta_analysis.json`.

The most important internal ratios are:

- **instruction reduction:** `90 / 37 = 2.43x`
- **register reduction:** `41 / 12 = 3.42x`

Those are not small cosmetic changes.
They explain why the public-envelope comparison moved so sharply.

## Why this was possible

### 1. The curve structure mattered
secp256k1 is a short Weierstrass curve with `a = 0`.
That makes complete mixed `j = 0` formulas especially attractive.

### 2. The point-add leaf was the real battleground
Once the public retained-window count is held fixed, the dominant lever is not “more windows” or “fancier rhetoric”.
It is the cost of the retained addition itself.

### 3. Boundary discipline helped rather than hurt
Paradoxically, being more honest about layers helped the optimization:
- exact arithmetic leaf here,
- lookup boundary here,
- scaffold here,
- backend model here.

That separation made it easier to improve the right thing without pretending to have solved the whole stack.

## What was likely overlooked in older baselines

The main likely misses were:
- too much weight on affine/inversion-heavy exception handling,
- not compressing the accumulator aggressively enough,
- not exploiting the `a = 0 / j = 0` mixed formulas deeply enough,
- not isolating the lookup and cleanup boundaries cleanly enough.

## The biggest lesson

The most important meta-lesson is:

**The public Google envelope does not force the public arithmetic design.**

You can keep the same public envelope-level scaffold count and still move the arithmetic core by a large factor.
