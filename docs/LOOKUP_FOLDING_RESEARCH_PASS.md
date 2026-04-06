# Lookup folding research pass

This document describes the new lookup-focused improvement added in this repo
revision.

## Goal

Improve the lookup layer **without changing the exact arithmetic leaf**.

That keeps the strongest current property of the repo intact:

- the optimized secp256k1 arithmetic leaf remains the same machine-readable
  kickmix ISA artifact,
- while the lookup contract around it is improved and re-audited.

## Main idea

The public Google appendix states that the retained-window point additions are
addressed by a `w`-bit register in **two's-complement** form.

For secp256k1 we can exploit the exact group-law identity:

- `[-d]U = (x([d]U), -y([d]U))`

So for a signed 16-bit lookup address we do not need a full 65,536-entry table
per coordinate.

Instead we can:

1. interpret the raw 16-bit word as a signed value `d`,
2. fold the table to magnitudes `|d|` in `0..32767`,
3. handle the unique exceptional word `0x8000 = -2^15` via one dedicated
   special constant per base,
4. derive the zero/no-op condition from the word directly,
5. negate the looked-up Y coordinate when `d < 0`.

## What is exact here

Exact and directly audited in the repository:

- the signed-word decomposition,
- the folded lookup contract,
- the semantic point returned by the folded contract,
- the folded scaffold metadata.

Files:

- `artifacts/optimized/out/lookup_signed_fold_contract.json`
- `artifacts/optimized/out/ecdlp_scaffold_lookup_folded.json`
- `artifacts/optimized/out/lookup_signed_fold_exhaustive_g.csv`
- `artifacts/optimized/out/lookup_signed_fold_multibase_sampled.csv`
- `artifacts/optimized/out/lookup_signed_fold_summary.json`

## Audit coverage

The repository now includes:

- a **full exhaustive audit over all 65,536 raw 16-bit words** for the canonical
  secp256k1 `G`-window-0 lookup base,
- plus **15,906 multibase semantic samples** over additional secp256k1 window
  bases.

Current status in the checked-in summary:

- exhaustive: **65,536 / 65,536 pass**
- multibase samples: **15,906 / 15,906 pass**

## What remains modeled

The translation from "folded 16-bit table" to total non-Clifford count is still
below the repository's ISA boundary. So the new total numbers are projections,
not new theorem-proved primitive-gate counts.

## Projected impact under the current repo model

Base case with zero extra per-window pad:

- current 2-channel total: `30,998,464`
- folded 2-channel total: `29,163,456`
- improvement: **5.92%**

- current 3-channel total: `32,833,472`
- folded 3-channel conservative total: `30,080,960`
- improvement: **8.38%**

These are meaningful but bounded wins. They are not another dramatic 2x jump.

## Why this is still useful

This branch is valuable because it is:

- algebraically clean,
- exact at the lookup-contract level,
- heavily audited,
- and easy to explain to external readers.

That makes it a strong next-step optimization even though it is not the final
answer to the whole resource problem.
