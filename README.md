# secp256k1 kickmix open audit repository

Open, auditable reconstruction package for a **secp256k1 ECDLP quantum point-add
family** with:

- a public-envelope reconstruction aligned to the public Google appendix numbers,
- an archived exact kickmix ISA artifact,
- an optimized secp256k1-specialized kickmix leaf and retained-window scaffold,
- a transparent standard-library verifier,
- a publication-hardening pass with red-team notes, stricter audits, and
  boundary files,
- and a research pass covering literature integration, benchmark ladders,
  cost-frontier analysis, and now an exact lookup-contract optimization branch.

## Main headline

The strongest audited mainline in this tree is still the optimized package in
`artifacts/optimized/`.

Under the repository's explicit backend model it reports:

- **880 logical qubits**
- **30,998,464 non-Clifford** in the 2-lookup model
- **32,833,472 non-Clifford** in the 3-lookup model

Compared with the public Google appendix envelope archived in
`artifacts/optimized/out/resource_projection.json`, that is still a substantial
modeled improvement.

## New in this revision

This revision adds two important things.

### 1. A correction

An earlier internal frontier-analysis script overstated the lookup share by
subtracting a **per-leaf** arithmetic estimate from a **whole-scaffold** total.

That is now fixed and documented in:

- `docs/COST_MODEL_CORRECTION.md`
- `artifacts/optimized/out/dominant_cost_breakdown.json`

Corrected interpretation under the current backend model:

- lookup share is **11.84%** in the 2-channel line,
- lookup share is **16.77%** in the 3-channel line,
- arithmetic remains the dominant modeled share.

### 2. A new exact lookup-contract improvement

The repo now includes a **signed two's-complement lookup-folding branch**.

What is exact here:

- the folded signed-lookup contract,
- the folded scaffold metadata,
- exhaustive semantic audit over **all 65,536 raw 16-bit words** for one
  secp256k1 base,
- **15,906** additional multibase semantic samples.

What remains modeled:

- translation from the folded contract to total backend non-Clifford count.

Base-case modeled impact of the folded branch:

- **29,163,456** in the folded 2-channel line
- **30,080,960** in the conservative folded 3-channel line
- roughly **5.9% to 8.4%** lower than the current modeled totals

Read:

- `docs/LOOKUP_FOLDING_RESEARCH_PASS.md`
- `artifacts/optimized/out/lookup_signed_fold_contract.json`
- `artifacts/optimized/out/lookup_folded_projection.json`

## The most important honesty line

**This repository is exact at the kickmix ISA arithmetic layer. It is not a theorem-proved primitive-gate quantum circuit for the full Shor stack.**

Read these first if you plan to publish or present the work:

- `RESEARCH_BOUNDARY.md`
- `docs/CLAIMS_AND_BOUNDARIES.md`
- `docs/RED_TEAM_REVIEW.md`
- `docs/COST_MODEL_CORRECTION.md`
- `docs/LOOKUP_FOLDING_RESEARCH_PASS.md`
- `docs/OPTIMIZATION_FRONTIERS.md`
- `docs/STATE_OF_THE_ART_2026.md`
- `docs/CAIN_2026_NEUTRAL_ATOM_INTEGRATION.md`
- `docs/PHYSICAL_STACKS_AND_HARDWARE_CONTEXT.md`

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

## Verification and research layers

| Layer | Status | Main files |
|---|---|---|
| Optimized arithmetic leaf `Q <- Q + L` | exact machine-checked | `optimized_pointadd_secp256k1.json`, `optimized_pointadd_audit_16384.csv` |
| Family instantiation on toy curves | exact finite-model check | `toy_curve_exhaustive_19850.csv`, `toy_curve_family_extended_110692.csv` |
| Original lookup contract | explicit and tested, not flattened | `lookup_contract_audit_8192.csv` |
| **New folded signed lookup contract** | exact contract + exhaustive semantic audit | `lookup_signed_fold_contract.json`, `lookup_signed_fold_exhaustive_g.csv` |
| Retained-window scaffold | hierarchical schedule + sampled replay | `ecdlp_scaffold_optimized.json`, `scaffold_schedule_audit_256.csv` |
| Folded scaffold metadata | exact contract-level variant | `ecdlp_scaffold_lookup_folded.json` |
| Cleanup (`mbuc_*`) | abstract contract only | leaf JSON files + verifier docs |
| Backend qubit / non-Clifford totals | modeled, not theorem-proved | `resource_projection.json`, `projection_sensitivity.json`, `lookup_folded_projection.json` |
| Challenge ladder | deterministic family regression layer | `benchmarks/challenge_ladder/` |
| Literature / frontier analysis | explicit scenario layer | `dominant_cost_breakdown.json`, `literature_projection_scenarios.json` |

## Repository map

- `reports/` — the PDF reports
- `artifacts/optimized/` — the primary release artifact, figures, transcripts,
  projections, strict-pass outputs, and research-pass outputs
- `artifacts/exact_kickmix/` — archived exact kickmix leaf and transcript replay
  package
- `artifacts/public_envelope/` — public-envelope reconstruction aligned to the
  Google appendix lines
- `benchmarks/challenge_ladder/` — deterministic secp-family micro-benchmark
  ladder and audit transcript
- `src/` — transparent verifier code using only the Python standard library
- `scripts/` — entrypoints for verify, strict verify, research pass, figures,
  hashing, and comparison tables
- `docs/` — publication notes, cost-model correction, lookup pass, frontier
  analysis, challenge ladder, literature integration, physical-stack context,
  and tooling paths
- `tests/` — unit and integrity tests
- `results/` — generated verification summaries and literature / physical
  matrices
- `archive/` — earlier reconstruction assets used while preparing the reports

## What to say publicly without overclaiming

A defensible one-sentence description is:

> This repository publishes an exact ISA-level arithmetic reconstruction for the secp256k1 point-add leaf, an exact signed lookup-contract improvement with exhaustive semantic audit, a tested retained-window scaffold compatible with the public Google appendix counts, and backend projections that remain explicit about lookup, cleanup, and primitive-gate boundaries.

## What not to say

Do **not** market this repository as any of the following:

- “Google's hidden exact circuit”
- “full primitive-gate proof”
- “complete verified quantum computer implementation”
- “proof that the final physical machine cost is exactly 880 logical qubits and 31.0M non-Clifford”
- “lookup dominates almost all remaining cost”

Those are stronger than what is actually checked here.

## Suggested reading order

1. `docs/CLAIMS_AND_BOUNDARIES.md`
2. `docs/COST_MODEL_CORRECTION.md`
3. `docs/LOOKUP_FOLDING_RESEARCH_PASS.md`
4. `docs/STATE_OF_THE_ART_2026.md`
5. `docs/OPTIMIZATION_FRONTIERS.md`
6. `docs/LITERATURE_INTEGRATION_DECISIONS.md`
7. `docs/RED_TEAM_REVIEW.md`
8. `reports/secp256k1_optimized_880q_31p0M_2p62x_report.pdf`
