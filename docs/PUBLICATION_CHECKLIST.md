# Publication checklist

This is the practical release checklist for publishing the repository.

## Before pushing public

### Mandatory
- run `python scripts/verify_all.py`
- run `python scripts/verify_strict.py --mode all`
- run `python -m unittest discover -s tests -v`
- run `python scripts/hash_repo.py`
- inspect `results/repo_verification_summary.json`
- inspect `results/strict_verification_summary.json`

### Strongly recommended
- open `docs/RED_TEAM_REVIEW.md` and make sure the README wording still matches it
- skim `docs/CLAIMS_AND_BOUNDARIES.md`
- skim `docs/OPTIMIZATION_FRONTIERS.md`
- verify the figures in `artifacts/optimized/figures/`
- replace citation metadata if you want non-anonymous release info

## Public positioning checklist

### Safe headline
Use:
- “exact ISA-level arithmetic artifact”
- “public-envelope comparison”
- “modeled backend projection”
- “open audit repository”

### Avoid
Avoid:
- “Google’s exact hidden circuit”
- “fully verified quantum circuit”
- “final physical machine cost proven exactly”
- “ZKP complete release” unless you actually add one

## Release assets that should be easy to find

- `README.md`
- `reports/secp256k1_optimized_880q_31p0M_2p62x_report.pdf`
- `docs/CLAIMS_AND_BOUNDARIES.md`
- `docs/RED_TEAM_REVIEW.md`
- `artifacts/optimized/out/resource_projection.json`
- `artifacts/optimized/out/projection_sensitivity.json`

## Q&A prep

If asked “what is the weakest part of the result?” answer:
- the primitive-gate boundary: lookup, cleanup, and backend lowering are still modeled layers.

If asked “what is the strongest part?” answer:
- the exact arithmetic leaf plus the deterministic secp256k1 audit and exhaustive finite-model family checks.

If asked “what could still improve?” answer:
- mostly lookup engineering and lower-level backend/compiler work, not another obvious formula-level 2x.

## Minimum honest public summary

A one-paragraph honest summary is:

This repository publishes an exact kickmix-ISA arithmetic reconstruction for a secp256k1-specialized point-add leaf, a tested retained-window scaffold compatible with the public Google appendix count, deterministic secp256k1 audits, exhaustive finite-model checks on several prime-order toy curves, and an explicit backend projection that beats the public Google appendix envelope while remaining honest about lookup, cleanup, and primitive-gate boundaries.
