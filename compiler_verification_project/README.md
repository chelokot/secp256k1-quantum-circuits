# compiler + verification project

This root-level subproject exists to answer the strongest version of the review:
not “what does the ISA artifact suggest?”, but “what exact whole-oracle counts
can be derived once the schedule is completed into a fully quantum compiler
family?”.

It is intentionally separate from the repository mainline.

## What this subproject does

1. completes the schedule into a **fully quantum raw-32 oracle** with no
   classical tail elisions;
2. fixes **named exact compiler families** for folded lookup, phase-shell, and
   schedule orchestration;
3. imports a fixed exact non-Clifford arithmetic-kernel family instead of
   back-solving whole-leaf costs from a headline constant;
4. derives **whole-oracle non-Clifford and logical-qubit counts** for those
   families; and
5. verifies the completed raw-32 schedule semantically on deterministic
   secp256k1 basis-state cases.

## Strongest exact claim here

The artifacts in `compiler_verification_project/artifacts/` are exact for the
**chosen compiler families**.

That is a stricter boundary than the repository mainline modeled backend layer,
but still
short of a globally optimal primitive-gate proof. In particular, the arithmetic
kernels are imported exact subroutines; this subproject still does **not** ship
bit-for-bit primitive CX/CCX netlists for every 256-bit field multiplier.
What it does ship is:

- an exact whole-oracle schedule,
- exact lookup-family choices,
- exact leaf slot allocation,
- exact phase-shell families, and
- exact whole-oracle counts relative to the chosen arithmetic kernel family.

## Main checked-in artifacts

- `family_frontier.json` — exact whole-oracle frontier for the named compiler families
- `full_raw32_oracle.json` — exact fully quantum schedule: 1 direct seed + 31 leaf calls
- `exact_leaf_slot_allocation.json` — exact versioned live-range allocation of the checked leaf
- `module_library.json` — fixed arithmetic kernel library used by the frontier
- `primitive_multiplier_library.json` — auditable manifest for all 341 multiplier instances in the raw-32 oracle
- `phase_shell_families.json` — full-register and semiclassical-QFT shell families
- `table_manifests.json` — exact folded-table dimensions and canonical window bases
- `full_attack_inventory.json` — structural inventory for the completed oracle
- `verification_summary.json` — deterministic semantic replay summary
- `cain_exact_transfer.json` — heuristic physical transfer for the exact families
- `azure_resource_estimator_logical_counts.json` — logicalCounts-style handoff artifact for physical estimators

## Current exact frontier

- **best exact gate family:** `23,813,671 non-Clifford`
- **best exact qubit family:** `2,337 logical qubits`

The best exact gate family uses folded unary QROM with measurement-based
uncompute. The best exact qubit family uses folded linear-scan lookup plus an
exact semiclassical-QFT phase shell and an exact 9-slot leaf allocation.

## Interpreting the results

This subproject is strongest when read as a **compiler-family exact oracle**,
not as a claim of hidden-Google reconstruction or global optimality.

Its defining exact features are:

- exact slot allocation cuts the leaf-side arithmetic peak from 10 named field
  slots to **9 exact physical field slots**;
- a semiclassical-QFT phase-shell family removes the fixed **512 live phase
  qubits** assumption; and
- those two ingredients place the best exact low-qubit family at **2,337
  logical qubits**.

## Quick start

From the repository root:

```bash
python compiler_verification_project/scripts/build.py
python compiler_verification_project/scripts/verify.py --cases 16
```
