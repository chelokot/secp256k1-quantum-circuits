# Extended verification

These checks are part of the default `python scripts/verify_all.py` path. The
shorter core-only variant is:

```bash
python scripts/verify_all.py --quick
```

## Outputs

### 1. Lookup-contract audit

Files:

- `artifacts/out/lookup_contract_audit_8192.csv`
- `artifacts/out/lookup_contract_summary.json`

Purpose:

- make the lookup boundary explicit
- test deterministic signed and unsigned 16-bit contract cases
- check the arithmetic assumptions used at the ISA boundary

### 2. Scaffold replay

Files:

- `artifacts/out/scaffold_schedule_audit_256.csv`
- `artifacts/out/scaffold_schedule_summary.json`

Purpose:

- execute the published retained-window schedule as written
- verify that the scaffold metadata is internally coherent on deterministic
  secp256k1 instances

### 3. Extended toy-family proof

Files:

- `artifacts/out/toy_curve_family_extended_110692.csv`
- `artifacts/out/toy_curve_family_extended_summary.json`

Purpose:

- extend the finite-model proof to four prime-order `j = 0` toy curves

### 4. Projection sensitivity

File:

- `artifacts/out/projection_sensitivity.json`

Purpose:

- measure how much backend overhead the modeled headline can absorb while
  staying below the published Google baseline

## Boundary

The extended verifier still does not:

- primitive-lower lookup memory
- primitive-verify `mbuc_*` cleanup
- emit a single flat gate list for the whole Shor stack
