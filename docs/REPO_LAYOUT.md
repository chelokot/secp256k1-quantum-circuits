# Repository layout

## Top level

- `README.md` — main entry point and terminology
- `RESEARCH_BOUNDARY.md` — shortest scope statement
- `REFERENCES.md` — external papers and tooling used as baselines or future-work
  inputs
- `LICENSE` — repository license
- `CITATION.cff` — citation metadata
- `MANIFEST.sha256` — whole-tree hash manifest

## Artifact layer

### `artifacts/`

Primary optimized release with:

- optimized leaf and family netlists
- retained-window scaffold metadata
- deterministic audits
- strict verification outputs
- research and sensitivity outputs
- figures used by the reports

## Benchmarks

### `benchmarks/challenge_ladder/`

Deterministic benchmark-curve replay suite in the `y^2 = x^3 + 7` family.

## Source code

- `src/common.py` — arithmetic, hashing, and serialization helpers
- `src/resource_projection.py` — canonical modeled projection data and ratio computation
- `src/verifier.py` — primary optimized-artifact verifier
- `src/strict_verifier.py` — strict verification and sensitivity layer
- `src/research_extensions.py` — research-pass generation logic

## Scripts

- `scripts/verify_all.py` — quick reproducibility path
- `scripts/verify_strict.py` — strict verification path
- `scripts/run_research_pass.py` — research-pass regeneration
- `scripts/rebuild_resource_projection.py` — canonical modeled projection regeneration
- `scripts/compare_google_baseline.py` — baseline comparison report
- `scripts/compare_cain_2026.py` — neutral-atom transfer report
- `scripts/compare_literature.py` — literature summary
- `scripts/compare_lookup_research.py` — merged lookup-folding mainline versus the unfolded pre-folding reference
- `scripts/hash_repo.py` — manifest regeneration
- `scripts/generate_figures.py` — figure regeneration

## Documentation

- `docs/EXECUTIVE_SUMMARY.md` — high-level repository summary
- `docs/CLAIMS_AND_BOUNDARIES.md` — exact versus modeled claim boundary
- `docs/GOOGLE_BASELINE_COMPARISON.md` — baseline definition and headline ratios
- `docs/STRICT_VERIFICATION.md` — strict verification coverage
- `docs/LOOKUP_FOLDING_RESEARCH_PASS.md` — signed folded lookup contract
- `docs/OPTIMIZATION_FRONTIERS.md` — budget split and next frontiers
- `docs/STATE_OF_THE_ART_2026.md` — external literature map
- `docs/RED_TEAM_REVIEW.md` — skeptical reading guide
- `docs/PHYSICAL_STACKS_AND_HARDWARE_CONTEXT.md` — logical versus physical layer
- `docs/CAIN_2026_NEUTRAL_ATOM_INTEGRATION.md` — neutral-atom transfer study
- `docs/CHALLENGE_LADDER.md` — benchmark-ladder definition
- `docs/META_ANALYSIS.md` — artifact-family comparison
- `docs/PUBLICATION_CHECKLIST.md` — release wording and verification checklist
- `docs/QUALITY_CONTROL.md` — reproducibility paths
- `docs/TOOLING_AND_REIMPLEMENTATION_PATHS.md` — external tooling directions

## Results

- `results/repo_verification_summary.json`
- `results/strict_verification_summary.json`
- `results/research_pass_summary.json`
- `results/literature_matrix.json`
- `results/physical_stack_reference_points.json`
- `results/cain_2026_integration_summary.json`
