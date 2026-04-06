# Quality control

## Quick reproducibility path

Run:

```bash
python scripts/verify_all.py
python -m unittest discover -s tests -v
```

This checks:

- optimized secp256k1 audit on 16,384 deterministic cases,
- original toy proof on 19,850 exhaustive toy cases,
- archived exact transcript replay on 9,024 rows,
- scaffold hash linkage,
- selected manifest hashes.

## Strict publication-hardening path

Run:

```bash
python scripts/verify_strict.py --mode all
```

This adds:

- lookup contract audit on 8,192 signed/unsigned 16-bit cases,
- scaffold replay on 256 deterministic secp256k1 `(a, b, H)` cases,
- extended toy-family proof on 110,692 exhaustive cases,
- projection sensitivity sweep,
- meta-analysis JSON,
- claim boundary matrix JSON.

## Extended research path

Run:

```bash
python scripts/run_research_pass.py
```

This adds:

- dominant cost breakdown,
- literature-inspired scenario bands,
- deterministic secp-family challenge ladder generation,
- challenge-ladder audit transcript,
- literature and physical-stack matrices.

## What is checked independently

The optimized secp256k1 arithmetic leaf is checked against:

1. a direct affine group-law implementation,
2. an independent complete-projective reference path,
3. a broad family of toy-curve instantiations,
4. and now also a deterministic secp-family benchmark ladder over additional `y^2 = x^3 + 7` curves.

That redundancy is intentional.
It reduces the chance that one buggy implementation accidentally blesses another.

## What is still outside the proven layer

Even after the strict and research passes, the repo does not primitive-flatten:

- lookup memory,
- MBUC cleanup,
- the full Shor gate stack below the hierarchical scaffold.

Those remain explicit boundaries rather than hidden assumptions.
