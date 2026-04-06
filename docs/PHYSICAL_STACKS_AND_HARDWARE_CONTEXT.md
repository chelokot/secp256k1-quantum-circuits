# Physical stacks and hardware context

The repository's strongest exact claim is a **logical / ISA-level arithmetic**
claim.  That is not the same thing as a hardware claim.

This file explains how to think about the main physical-context papers that now
surround the repo.

## Three useful reference points

### 1. Google / Babbush et al. 2026

Use in this repo:
- public logical baseline for secp256k1 envelope comparisons,
- plus broad hardware urgency context.

What it is **not** in this repo:
- not the source of an exact released circuit,
- not a drop-in physical execution model for our artifact.

### 2. Cain et al. 2026

Use in this repo:
- primary neutral-atom physical integration target.

Why it matters:
- it gives a concrete architectural bridge from logical ECDLP circuits into
  physical space / runtime estimates,
- while being explicit that its own goal is approximate resource estimation,
  not exact concrete instruction sets.

Where it lives:
- `docs/CAIN_2026_NEUTRAL_ATOM_INTEGRATION.md`
- `results/cain_2026_integration_summary.json`

### 3. Gouzien et al. 2023

Use in this repo:
- alternative physical reference point under cat-qubit assumptions.

Why it matters:
- it reminds readers that hardware assumptions can swing physical conclusions
  dramatically even when the logical algorithmic target is broadly similar.

## The right mental model

These physical papers should be read as **consumers** of the repository's logical
artifact, not as replacements for it.

That means:

- a stronger logical artifact can improve their physical estimates,
- but it does not erase their hardware assumptions,
- and their hardware assumptions do not prove a stronger logical artifact.

## Why the repo keeps these layers separate

Because collapsing them into one headline would be the fastest path to overclaim.

The repository therefore keeps three separate files:

- `resource_projection.json` — modeled logical / backend projection
- `cain_2026_integration_summary.json` — approximate neutral-atom transfer
- `physical_stack_reference_points.json` — cross-paper physical reference map

## Bottom line

If a reader wants to know:

- *what exactly is the arithmetic artifact?* → read the verifier artifacts
- *what is the public logical comparison line?* → read the Google comparison
- *what might happen on specific hardware assumptions?* → read the Cain / Gouzien context

Treating those as separate questions makes the repository stronger, not weaker.
