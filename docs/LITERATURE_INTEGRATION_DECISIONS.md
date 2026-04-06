# Literature integration decisions

This document explains what was actually integrated, what was translated only as
scenario pressure, and what was deliberately left out of the mainline.

## New rule after the correction

The corrected cost model changes the interpretation of the literature.

Earlier internal notes over-emphasized lookup papers because the lookup share was
mistakenly computed as ~97% of the total. After correction, arithmetic remains
the larger modeled share.

That means:

- arithmetic papers remain highly relevant,
- lookup papers still matter, but now as a bounded secondary frontier,
- and the strongest next-step repo contribution is the one that can be integrated
  exactly and audited cleanly.

## Integrated directly

### 1. Benchmark-ladder thinking

Still integrated exactly as before.

Why:

- it strengthens regression testing,
- it supports external reimplementation,
- it aligns with the need for better ECDLP benchmark suites.

Where:

- `benchmarks/challenge_ladder/`
- `docs/CHALLENGE_LADDER.md`

### 2. Cost-model correction

Integrated directly because the previous interpretation was wrong.

Where:

- `docs/COST_MODEL_CORRECTION.md`
- `artifacts/optimized/out/dominant_cost_breakdown.json`
- `results/research_pass_summary.json`

### 3. Exact lookup-folding branch

Integrated directly because it could be stated as an exact contract rather than
as a vague heuristic.

Why:

- it uses the public two's-complement lookup framing,
- it exploits exact secp256k1 negation symmetry,
- it does not require rewriting the exact arithmetic leaf,
- it supports exhaustive and sampled audits.

Where:

- `artifacts/optimized/out/lookup_signed_fold_contract.json`
- `artifacts/optimized/out/ecdlp_scaffold_lookup_folded.json`
- `artifacts/optimized/out/lookup_signed_fold_summary.json`
- `docs/LOOKUP_FOLDING_RESEARCH_PASS.md`

## Translated only as scenarios

### Multiplier/backend improvements

Examples:

- Litinski-style schoolbook multiplier improvements
- more aggressive adder/backend substitutions

Why not merged into the headline:

- they would change the arithmetic leaf implementation itself,
- the repository has not yet rewritten and re-audited that leaf,
- so only model-level scenario translation is honest today.

How they are used:

- `artifacts/optimized/out/literature_projection_scenarios.json`

### Deeper lookup-lowering papers

Examples:

- Gidney windowed arithmetic
- Haner space-time lookup
- unified lookup-architecture work
- conditionally-clean ancilla work

Why not merged fully into the headline:

- the current repo stops at an exact contract layer for lookup,
- not at a primitive-lowered qRAM/QROM implementation.

How they are used:

- to guide the next lowering experiments,
- to justify the new folded-lookup branch,
- and to define what to build next after this pass.

## Deliberately not merged into the mainline

### External heavy frameworks

Examples:

- Qualtran
- Qrisp
- QCEC

Why not merged:

- the transparent standard-library verifier remains one of the repo's main
  strengths,
- and these are better treated as external reimplementation or flattening paths.

### Low-qubit affine/inversion branches

Example:

- Luo 2026

Why not merged:

- the current optimized line is built around complete mixed formulas and avoids
  affine inversion in the hot path,
- so a low-qubit affine branch is better framed as an alternate branch.

### Physical architecture papers as logical-circuit evidence

Examples:

- Cain 2026
- Gouzien 2023
- Gu 2025

Why not merged into the logical headline:

- they live at a different abstraction layer,
- they are great for transfer studies,
- they do not strengthen the exact ISA-level artifact directly.

## Ranked next steps after this pass

1. **arithmetic-backend swap experiments**
2. **primitive-lower more of the lookup layer**
3. **fragment flattening + external equivalence checking**
4. **alternate low-qubit branch**
5. **broader physical-stack comparison matrix**

## One-sentence summary

This pass strengthened the repo by correcting a real internal modeling error and
by adding one exact, audited lookup optimization instead of pretending that a
large heuristic frontier jump was already achieved.
