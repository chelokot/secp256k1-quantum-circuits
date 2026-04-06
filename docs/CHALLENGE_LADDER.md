# Deterministic secp-family challenge ladder

The repository originally had two kinds of correctness evidence for the optimized
family:

1. a large secp256k1 audit, and
2. exhaustive checks on a small toy-family subset.

That is already useful, but it leaves a gap:

- the secp256k1 audit is large but not exhaustive,
- the toy curves are exhaustive but very small and limited in diversity.

This file documents the new middle layer.

## What the ladder is

A deterministic family of tiny benchmark curves of the form:

- `y^2 = x^3 + 7 mod p`

with:
- prime `p`,
- `p ≡ 3 (mod 4)` so square-root extraction stays simple and reproducible,
- a large prime-order subgroup,
- a deterministic subgroup generator,
- and a deterministic challenge point `H = kG` with known discrete logarithm.

These are **not** meant to be cryptographically secure challenge instances.
They are meant to be:

- simple,
- inspectable,
- reproducible,
- and close enough to the secp256k1 algebraic family to be useful regression
  tests.

## What gets checked

For each ladder curve, the research pass:

1. builds a fixed-width window table,
2. replays the optimized family leaf window-by-window,
3. includes zero-digit windows so no-op semantics are tested explicitly,
4. compares the accumulated output against both:
   - table-based scalar multiplication, and
   - direct affine scalar multiplication,
5. records all cases in a CSV.

This is not a period-finding proof and not a physical-resource result.
It is an **end-to-end scalar-accumulation replay layer**.

## Why it exists

Three reasons:

### 1. Better regression coverage

It exercises the family netlist on more curves than the original toy subset,
without jumping all the way to a huge external framework.

### 2. Better external auditability

A skeptical reader can inspect the full ladder generation path and rerun it from
source.

### 3. Better alignment with benchmark-oriented literature

Recent work has highlighted the need for precise ECDLP benchmark suites rather
than sparse or arbitrary toy examples.  This ladder is the repository's answer to
that demand, while staying self-generated and transparent.

## Files

- `benchmarks/challenge_ladder/challenge_ladder.json`
- `benchmarks/challenge_ladder/challenge_ladder_audit.csv`
- `benchmarks/challenge_ladder/challenge_ladder_summary.json`
- `artifacts/optimized/figures/challenge_ladder_orders.png`

## Scope boundary

The ladder **does not** strengthen the repository's physical-resource claims.
It strengthens:

- transparency,
- regression quality,
- and functional confidence in the family-level arithmetic artifact.
