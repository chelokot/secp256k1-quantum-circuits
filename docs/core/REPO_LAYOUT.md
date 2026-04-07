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
- extended verification outputs
- research and sensitivity outputs

## Source code

- `src/common.py` — arithmetic, hashing, and serialization helpers
- `src/cain_integration.py` — Cain et al. transfer summary generation
- `src/figure_generation.py` — figure generation logic
- `src/maintenance.py` — manifest and artifact-refresh helpers
- `src/resource_projection.py` — canonical modeled projection data and ratio computation
- `src/verifier.py` — primary optimized-artifact verifier
- `src/extended_verifier.py` — extended verification and sensitivity layer
- `src/research_extensions.py` — research-pass generation logic

## Scripts

- `scripts/verify_all.py` — main verification path, with `--quick` for the core-only run
- `scripts/compare_cain_2026.py` — neutral-atom transfer report
- `scripts/refresh_repo.py` — maintainer-only artifact refresh path

## Documentation

- `docs/core/CLAIMS_AND_BOUNDARIES.md` — exact versus modeled claim boundary
- `docs/references/GOOGLE_BASELINE_COMPARISON.md` — baseline definition and headline ratios
- `docs/core/EXTENDED_VERIFICATION.md` — extended verification coverage
- `docs/research/LOOKUP_FOLDING_RESEARCH_PASS.md` — signed folded lookup contract
- `docs/research/OPTIMIZATION_FRONTIERS.md` — budget split and next frontiers
- `docs/references/STATE_OF_THE_ART_2026.md` — external literature map
- `docs/core/RED_TEAM_REVIEW.md` — skeptical reading guide
- `docs/references/PHYSICAL_STACKS_AND_HARDWARE_CONTEXT.md` — logical versus physical layer
- `docs/references/CAIN_2026_NEUTRAL_ATOM_INTEGRATION.md` — neutral-atom transfer study
- `docs/research/META_ANALYSIS.md` — artifact-family comparison
- `docs/core/PUBLICATION_CHECKLIST.md` — release wording and verification checklist
- `docs/core/QUALITY_CONTROL.md` — reproducibility paths
- `docs/references/TOOLING_AND_REIMPLEMENTATION_PATHS.md` — external tooling directions

## Figures

- `figures/core/` — main report and comparison figures
- `figures/research/` — research and supporting-analysis figures

## Results

- `results/repo_verification_summary.json`
- `results/research_pass_summary.json`
- `results/literature_matrix.json`
- `results/physical_stack_reference_points.json`
- `results/cain_2026_integration_summary.json`
