# Repository layout

## Top level

- `README.md` — main entry point and claim ladder
- `RESEARCH_BOUNDARY.md` — concise honesty boundary
- `REFERENCES.md` — curated external literature and tooling references
- `LICENSE` — repository license
- `CITATION.cff` — machine-readable citation template
- `MANIFEST.sha256` — whole-tree file hash manifest

## Reports

- `reports/secp256k1_reconstruction_1191q_81p1M_1441q_64p3M_audit.pdf`
- `reports/secp256k1_exact_kickmix_netlist_report.pdf`
- `reports/secp256k1_optimized_880q_31p0M_2p62x_report.pdf`

## Artifacts

### `artifacts/public_envelope/`
Public-envelope reconstruction aligned to the public Google appendix lines.

### `artifacts/exact_kickmix/`
Archived exact kickmix artifact:
- exact leaf netlist,
- scaffold sample,
- transcript replay package.

### `artifacts/optimized/`
Primary release artifact:
- optimized leaf and family netlists,
- deterministic secp256k1 audit,
- toy-curve proofs,
- strict-verifier outputs,
- research-pass frontier outputs,
- figures.

## Benchmarks

### `benchmarks/challenge_ladder/`
Deterministic secp-family benchmark ladder:
- self-generated tiny `y^2 = x^3 + 7` curves,
- known subgroup generators,
- known challenge points,
- scalar-accumulation replay audit.

## Source code

### `src/common.py`
Shared arithmetic, hashing, and serialization helpers.

### `src/verifier.py`
Quick verifier for the optimized package.

### `src/verify_exact_archive.py`
Replay verifier for the archived exact package.

### `src/strict_verifier.py`
Publication-hardening verifier:
- lookup contract audit
- scaffold replay
- extended toy family proof
- projection sensitivity
- meta-analysis
- claim boundary matrix

### `src/research_extensions.py`
Research-pass module:
- dominant cost breakdown
- literature projection scenarios
- challenge-ladder generation and audit
- literature matrix
- physical-stack reference matrix

## Scripts

- `scripts/verify_all.py` — quick whole-repo verification
- `scripts/verify_strict.py` — strict publication-hardening verification
- `scripts/run_research_pass.py` — rebuild research-pass artifacts
- `scripts/compare_google_baseline.py` — headline public-baseline comparison
- `scripts/compare_cain_2026.py` — approximate neutral-atom transfer summary
- `scripts/compare_literature.py` — literature/frontier summary table
- `scripts/hash_repo.py` — rebuild `MANIFEST.sha256`
- `scripts/generate_figures.py` — regenerate publication figures

## Docs

- `docs/EXECUTIVE_SUMMARY.md`
- `docs/CLAIMS_AND_BOUNDARIES.md`
- `docs/RED_TEAM_REVIEW.md`
- `docs/OPTIMIZATION_FRONTIERS.md`
- `docs/STATE_OF_THE_ART_2026.md`
- `docs/LITERATURE_INTEGRATION_DECISIONS.md`
- `docs/CHALLENGE_LADDER.md`
- `docs/TOOLING_AND_REIMPLEMENTATION_PATHS.md`
- `docs/PHYSICAL_STACKS_AND_HARDWARE_CONTEXT.md`
- `docs/META_ANALYSIS.md`
- `docs/STRICT_VERIFICATION.md`
- `docs/PUBLICATION_CHECKLIST.md`
- `docs/GOOGLE_BASELINE_COMPARISON.md`
- `docs/QUALITY_CONTROL.md`

## Results

- `results/repo_verification_summary.json`
- `results/strict_verification_summary.json`
- `results/exact_archive_verification_summary.json`
- `results/research_pass_summary.json`
- `results/literature_matrix.json`
- `results/physical_stack_reference_points.json`
- `results/cain_2026_integration_summary.json`
