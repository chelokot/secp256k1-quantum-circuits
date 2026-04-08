# Extended verification

These checks are part of the default `python scripts/verify_all.py` path. The
shorter core-only variant is:

```bash
python scripts/verify_all.py --quick
```

## Outputs

### 1. Lookup-contract audit

Files:

- `artifacts/verification/extended/lookup_contract_summary.json`
- `artifacts/lookup/lookup_signed_fold_summary.json`
- `artifacts/lookup/lookup_signed_fold_exhaustive_g.csv`
- `artifacts/lookup/lookup_signed_fold_multibase_sampled.csv`

Purpose:

- make the lookup boundary explicit
- validate the machine-readable folded-contract fields
- exhaustively check the canonical 16-bit secp256k1 base over the full word domain
- check deterministic multibase semantic samples used at the ISA boundary

### 2. Coherent cleanup audit

Files:

- `artifacts/verification/extended/coherent_cleanup_audit_16384.csv`
- `artifacts/verification/extended/coherent_cleanup_summary.json`

Purpose:

- check the shipped one-bit no-op control cleanup pair on deterministic
  secp256k1 cases
- verify that the cleanup step clears `f_lookup_inf`
- verify that cleanup preserves the selected projective output and the loaded
  metadata bit

### 3. Scaffold replay

Files:

- `artifacts/verification/extended/scaffold_schedule_audit_256.csv`
- `artifacts/verification/extended/scaffold_schedule_summary.json`

Purpose:

- execute the published retained-window schedule as written
- verify that the scaffold metadata is internally coherent on deterministic
  secp256k1 instances

### 4. Extended toy-family proof

Files:

- `artifacts/verification/extended/toy_curve_family_extended_110692.csv`
- `artifacts/verification/extended/toy_curve_family_extended_summary.json`

Purpose:

- extend the finite-model proof to four prime-order `j = 0` toy curves

## Boundary

The extended verifier still does not:

- primitive-lower lookup memory
- primitive-lower the shipped flag-cleanup pair
- emit a single flat gate list for the whole Shor stack
