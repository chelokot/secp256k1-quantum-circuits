# Publication checklist

## Required reproducibility checks

- run `python scripts/verify_all.py`
- run `python scripts/verify_strict.py --mode all`
- run `python -m unittest discover -s tests -v`
- run `python scripts/hash_repo.py`
- inspect `results/repo_verification_summary.json`
- inspect `results/strict_verification_summary.json`

## Required wording checks

Before publishing, verify that the public-facing text still uses the repository
definitions consistently:

- baseline means Google's rounded published 2026 secp256k1 estimates from Babbush et al. 2026
- exact means the ISA-level arithmetic and lookup-contract layers
- modeled means backend totals below the ISA boundary
- physical transfer means a separate architecture study, not a stronger logical
  proof

## Safe public wording

- “exact ISA-level arithmetic artifact”
- “explicit lookup contract”
- “tested retained-window scaffold”
- “modeled backend projection”
- “comparison against Google's published 2026 secp256k1 estimates”

## Wording to avoid

- “unpublished Google circuit reconstruction”
- “fully verified primitive-gate quantum circuit”
- “final physical machine cost proven exactly”
- “primitive-gate qRAM already included”

## Release assets to surface prominently

- `README.md`
- `docs/CLAIMS_AND_BOUNDARIES.md`
- `docs/GOOGLE_BASELINE_COMPARISON.md`
- `docs/RED_TEAM_REVIEW.md`
- `artifacts/out/resource_projection.json`
- `artifacts/out/projection_sensitivity.json`
- `reports/secp256k1_optimized_report.pdf`
