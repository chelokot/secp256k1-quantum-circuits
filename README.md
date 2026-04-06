> [!WARNING]
> This repository was created entirely with ChatGPT 5.4 Pro. I personally have
> only surface-level knowledge of quantum computing, so I cannot audit it in
> depth myself. I have tried to make it as transparent, tested, and
> reproducible as possible. Anyone with domain expertise is strongly encouraged
> to review this repository and open issues or pull requests.

# secp256k1 kickmix open audit repository

This repository is an open audit package for a secp256k1 ECDLP point-addition
stack. It contains three artifact families:

- a public-envelope reconstruction aligned to the published appendix numbers in
  Babbush et al. 2026,
- an archived exact kickmix-ISA point-add artifact kept as a reference release,
- a primary optimized secp256k1-specialized artifact with verification,
  sensitivity, and research layers.

The repository is strongest at the arithmetic ISA boundary. It publishes exact,
machine-readable point-add schedules and checks their basis-state semantics. It
also publishes modeled backend totals for logical qubits and non-Clifford
counts. Those modeled totals are explicit projections, not primitive-gate
proofs.

## Main results

### Primary audited mainline

The primary release artifact is in `artifacts/optimized/`.

Its modeled ECDLP projection, as recorded in
`artifacts/optimized/out/resource_projection.json`, is:

- **880 logical qubits**
- **30,998,464 non-Clifford** under the 2-channel lookup model
- **32,833,472 non-Clifford** under the 3-channel lookup model

### Public baseline used for comparison

When this repository says **public Google appendix envelope**, it means the
published secp256k1 reference lines from Babbush et al. 2026 as stored in
`artifacts/optimized/out/resource_projection.json`:

- **low-qubit line:** `1191 logical qubits`, `81,105,024 non-Clifford`
- **low-gate line:** `1441 logical qubits`, `64,305,024 non-Clifford`
- **window size:** `16`
- **retained point additions:** `28`

The comparison is against those public appendix numbers only. It is not a claim
to have reconstructed any unpublished internal circuit.

### Exact signed lookup-folding branch

The optimized package also contains an exact signed lookup-contract variant in
`artifacts/optimized/out/lookup_signed_fold_contract.json` and
`artifacts/optimized/out/ecdlp_scaffold_lookup_folded.json`.

That branch is exact at the lookup-contract level and audited by:

- **65,536 / 65,536** exhaustive 16-bit words for the canonical `G` window-0
  base
- **15,906 / 15,906** additional multibase semantic samples

Its backend totals remain modeled. The base-case folded projection in
`artifacts/optimized/out/lookup_folded_projection.json` is:

- **29,163,456 non-Clifford** under the folded 2-channel model
- **30,080,960 non-Clifford** under the folded conservative 3-channel model

## Exact vs modeled layers

### Exact in this repository

- optimized secp256k1 point-add leaf semantics
- archived exact kickmix point-add leaf semantics
- deterministic secp256k1 audit transcripts
- exhaustive toy-curve family checks
- explicit lookup-contract semantics, including the signed folded variant
- retained-window scaffold metadata and deterministic scaffold replay

### Modeled in this repository

- primitive-gate lookup memory lowering
- primitive-gate cleanup for `mbuc_*` operations
- fully flattened Shor period-finding gate list
- logical-qubit and non-Clifford totals below the ISA boundary
- physical-machine runtime and physical-qubit transfer studies

If you need the shortest honest description of the repository, use:

> This repository publishes exact ISA-level arithmetic artifacts and explicit
> lookup contracts for a secp256k1 point-add stack, together with deterministic
> audits, finite-model checks, retained-window scaffold replay, and modeled
> backend resource projections against the public appendix baseline of Babbush
> et al. 2026.

## Verification summary

The checked-in summaries report:

- optimized secp256k1 audit: **16,384 / 16,384** pass
- archived exact replay: recorded in `results/exact_archive_verification_summary.json`
- original toy-curve proof: **19,850 / 19,850** pass
- strict lookup-contract audit: **8,192 / 8,192** pass
- strict scaffold replay: **256 / 256** pass
- extended toy-family proof: **110,692 / 110,692** pass
- challenge ladder replay: **763 / 763** pass across **7** benchmark curves

See:

- `results/repo_verification_summary.json`
- `results/strict_verification_summary.json`
- `results/research_pass_summary.json`

## Repository map

- `artifacts/optimized/` — primary optimized artifact, audits, projections,
  research outputs, and figures
- `artifacts/exact_kickmix/` — archived exact kickmix point-add release
- `artifacts/public_envelope/` — public-envelope reconstruction data for the
  Babbush et al. 2026 appendix lines
- `benchmarks/challenge_ladder/` — deterministic benchmark-curve replay suite
- `src/` — verifier and research logic implemented in Python
- `scripts/` — reproducibility entrypoints
- `docs/` — scope, claims, baseline definitions, verification notes, and
  research interpretation
- `results/` — generated summary JSON files
- `reports/` — report PDFs

## Quick start

From the repository root:

```bash
python scripts/verify_all.py
python scripts/verify_strict.py --mode all
python scripts/run_research_pass.py
python scripts/compare_google_baseline.py
python scripts/compare_cain_2026.py
python scripts/compare_literature.py
python scripts/compare_lookup_research.py
python -m unittest discover -s tests -v
```

Or with `make`:

```bash
make verify
make verify-strict
make research
make compare
make compare-lookup
make test
```

## Reading order

1. `docs/EXECUTIVE_SUMMARY.md`
2. `docs/CLAIMS_AND_BOUNDARIES.md`
3. `docs/GOOGLE_BASELINE_COMPARISON.md`
4. `docs/STRICT_VERIFICATION.md`
5. `docs/LOOKUP_FOLDING_RESEARCH_PASS.md`
6. `docs/OPTIMIZATION_FRONTIERS.md`
7. `docs/STATE_OF_THE_ART_2026.md`
8. `docs/RED_TEAM_REVIEW.md`
9. `reports/secp256k1_optimized_880q_31p0M_2p62x_report.pdf`
