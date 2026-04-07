# Quality control

## Quick reproducibility path

Run:

```bash
python scripts/verify_all.py
python -m unittest discover -s tests -v
```

This covers:

- optimized secp256k1 audit on `16,384` deterministic cases
- original toy proof on `19,850` exhaustive toy cases
- cited Google baseline presence inside the projection file
- manifest and summary checks

## Strict verification path

Run:

```bash
python scripts/verify_strict.py --mode all
```

This adds:

- lookup-contract audit on `8,192` deterministic signed and unsigned cases
- scaffold replay on `256` deterministic secp256k1 cases
- extended toy-family proof on `110,692` exhaustive cases
- projection sensitivity outputs
- claim-boundary and meta-analysis outputs

## Research path

Run:

```bash
python scripts/run_research_pass.py
```

This adds:

- dominant cost breakdown
- lookup-folding provenance versus the pre-folding baseline
- challenge-ladder generation and replay
- literature and physical-context matrices

## Independent reference paths

The optimized arithmetic leaf is checked against:

1. direct affine group-law computation
2. an independent complete-projective reference path
3. finite-model toy-curve families
4. deterministic benchmark-ladder replay

The goal is to avoid trusting a single implementation path.

## Outside the proven layer

The repository still does not primitive-lower:

- lookup memory
- `mbuc_*` cleanup
- the entire Shor stack as a flat gate list
