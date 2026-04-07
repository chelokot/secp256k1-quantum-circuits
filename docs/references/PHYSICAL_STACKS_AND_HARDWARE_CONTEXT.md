# Physical stacks and hardware context

The repository's strongest claim is a logical or ISA-level arithmetic claim.
That is separate from any physical-machine claim.

## Three reference points

### 1. Babbush et al. 2026

Role here:

- published secp256k1 estimate baseline
- public urgency context for ECDLP resource estimation

Not claimed here:

- an exact released circuit implementation used by this repository
- a drop-in hardware model for the optimized artifact

### 2. Cain et al. 2026

Role here:

- neutral-atom transfer study for the repository's logical projection

Files:

- `docs/references/CAIN_2026_NEUTRAL_ATOM_INTEGRATION.md`
- `results/cain_2026_integration_summary.json`

### 3. Gouzien et al. 2023

Role here:

- alternate physical reference point under a different hardware stack

## How to read these layers

Physical papers are consumers of the logical artifact, not replacements for it.
The right questions are:

- what exact logical artifact is checked here?
- what public logical baseline is used here?
- what happens if that logical artifact is transferred into a particular
  physical architecture model?

## Repository separation of layers

The repository keeps three different file classes:

- `artifacts/out/projections/resource_projection.json` for modeled logical totals
- `results/cain_2026_integration_summary.json` for approximate neutral-atom
  transfer
- `results/physical_stack_reference_points.json` for cross-paper context
