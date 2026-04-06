# Strict verification

The quick path is:

```bash
python scripts/verify_all.py
```

The stricter publication-hardening path is:

```bash
python scripts/verify_strict.py --mode all
```

## What the strict verifier adds

### 1. Lookup contract audit
Output:
- `artifacts/optimized/out/lookup_contract_audit_8192.csv`
- `artifacts/optimized/out/lookup_contract_summary.json`

Purpose:
- make the lookup-table boundary explicit,
- test signed and unsigned 16-bit contracts on deterministic secp256k1 bases,
- avoid pretending that the lookup machinery is already primitive-gate flattened.

### 2. Scaffold schedule replay
Output:
- `artifacts/optimized/out/scaffold_schedule_audit_256.csv`
- `artifacts/optimized/out/scaffold_schedule_summary.json`

Purpose:
- execute the retained-window schedule as published,
- verify that one direct seed, 28 retained leaf calls, and 3 classical tail elisions reconstruct the expected point sum on deterministic secp256k1 instances.

### 3. Extended toy family proof
Output:
- `artifacts/optimized/out/toy_curve_family_extended_110692.csv`
- `artifacts/optimized/out/toy_curve_family_extended_summary.json`

Purpose:
- push the family proof beyond the two original toy curves,
- exhaust four prime-order `j = 0` curves with orders 61, 127, 181, and 241.

### 4. Projection sensitivity
Output:
- `artifacts/optimized/out/projection_sensitivity.json`

Purpose:
- quantify how much extra backend pain the result can absorb before losing the public-baseline comparison.

## Runtime note

The strict verifier is still lightweight enough to run on a normal laptop because:
- the secp256k1 scaffold replay uses 256 deterministic cases, not millions,
- the extended family proof uses small prime-order toy curves,
- everything is pure Python with no external dependencies.

## What the strict verifier still does not do

It still does **not**:
- flatten lookup memory into primitive gates,
- prove coherent phase-correct MBUC cleanup,
- produce a full flat gate list for the whole Shor period-finding stack.

That is by design. The point is to strengthen the repository without lying about what layer it is on.
