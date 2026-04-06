# Meta-analysis of artifact families

This file compares the three artifact families stored in the repository.

## Artifact families

### 1. Public-envelope reconstruction

Location: `artifacts/public_envelope/`

Role:

- preserve the public appendix-aligned reconstruction data
- keep the comparison target concrete and inspectable

### 2. Archived exact kickmix artifact

Location: `artifacts/exact_kickmix/`

Role:

- preserve an exact point-add artifact and replay package
- serve as a reference release for exact ISA-level scheduling

### 3. Optimized secp256k1 artifact

Location: `artifacts/optimized/`

Role:

- provide the primary optimized point-add leaf
- provide the retained-window scaffold metadata
- provide the strict verification and research layers
- provide the modeled baseline comparison

## Quantified internal differences

`artifacts/optimized/out/meta_analysis.json` records the main internal deltas
between the archived exact artifact and the optimized artifact:

- instruction reduction: `90 / 37 = 2.43x`
- register reduction: `41 / 12 = 3.42x`

## Main interpretation

The repository's strongest improvement comes from reducing the cost of the
retained point-add leaf while keeping the window structure and comparison
baseline explicit.
