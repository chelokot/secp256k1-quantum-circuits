# Deterministic secp-family challenge ladder

This document defines the benchmark-ladder layer in `benchmarks/challenge_ladder/`.

## What the ladder is

The ladder is a deterministic family of small benchmark curves of the form:

`y^2 = x^3 + 7 mod p`

Each benchmark instance includes:

- a prime field `p`
- a large prime-order subgroup
- a deterministic subgroup generator
- a deterministic challenge point with known discrete logarithm

These instances are benchmark curves, not security claims.

## What the repository checks on them

For each ladder curve, the research pass:

1. builds a fixed-width window table
2. replays the optimized family leaf window by window
3. includes zero-digit windows explicitly
4. compares the resulting accumulator with independent scalar-multiplication
   reference paths
5. records the transcript in CSV form

## Checked summary

`benchmarks/challenge_ladder/challenge_ladder_summary.json` reports:

- **7** curves
- up to **18** field bits
- **763 / 763** replay cases passed

## What this layer strengthens

- regression coverage
- external reproducibility
- family-level confidence between the tiny exhaustive toy curves and the large
  secp256k1 audit

## What this layer does not claim

- a physical-resource result
- a period-finding proof
- a primitive-gate circuit
