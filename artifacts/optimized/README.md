# Optimized artifact

This is the main release artifact.

## Core files

- `out/optimized_pointadd_secp256k1.json` — exact secp256k1-specialized kickmix ISA leaf
- `out/optimized_pointadd_family.json` — exact family netlist with symbolic `b3 = 3*b`
- `out/ecdlp_scaffold_optimized.json` — retained-window scaffold metadata
- `out/resource_projection.json` — backend projection against the public Google appendix envelope

## Quick verification outputs

- `out/optimized_pointadd_audit_16384.csv`
- `out/toy_curve_exhaustive_19850.csv`
- `out/verification_summary.json`

## Strict verification outputs

- `out/lookup_contract_audit_8192.csv`
- `out/scaffold_schedule_audit_256.csv`
- `out/toy_curve_family_extended_110692.csv`
- `out/projection_sensitivity.json`
- `out/meta_analysis.json`
- `out/claim_boundary_matrix.json`

## Main commands

Quick:
```bash
python src/verifier.py --package-dir artifacts/optimized --mode all
```

Strict:
```bash
python scripts/verify_strict.py --mode all
```

## Reading order

1. `../../docs/CLAIMS_AND_BOUNDARIES.md`
2. `../../docs/META_ANALYSIS.md`
3. `../../docs/RED_TEAM_REVIEW.md`
4. `../../docs/OPTIMIZATION_FRONTIERS.md`
5. `../../reports/secp256k1_optimized_880q_31p0M_2p62x_report.pdf`

## Boundary reminder

The optimized artifact is exact at the arithmetic ISA layer.
Lookup, cleanup, scaffold flattening, and backend totals remain explicit boundaries rather than hidden claims.
