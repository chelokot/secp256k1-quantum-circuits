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
3. lowers each named lookup family into an explicit stage/block inventory below
   the folded lookup contract;
4. lowers the named arithmetic-kernel family into an explicit stage/block
   inventory instead of treating leaf arithmetic as bare scalar opcode costs;
5. derives **whole-oracle non-Clifford and logical-qubit counts** for those
   families; and
6. verifies the completed raw-32 schedule semantically on deterministic
   secp256k1 basis-state cases.

## Strongest exact claim here

The artifacts in `compiler_verification_project/artifacts/` are exact for the
**chosen compiler families**.

That is a stricter boundary than the repository's quarantined hypothesis layer,
but still
short of a globally optimal primitive-gate proof. In particular, the arithmetic
lowerings stop at explicit non-Clifford stage/block inventories; this
subproject still does **not** ship bit-for-bit Clifford-complete netlists for
every 256-bit field multiplier.
What it does ship is:

- an exact whole-oracle schedule,
- exact arithmetic-kernel stage/block inventories,
- exact lookup-family choices with explicit lowered stage inventories,
- exact leaf slot allocation,
- exact phase-shell families, and
- exact whole-oracle counts relative to the chosen arithmetic kernel family.

## Main checked-in artifacts

- `family_frontier.json` — exact whole-oracle frontier for the named compiler families
- `full_raw32_oracle.json` — exact fully quantum schedule: 1 direct seed + 31 leaf calls
- `exact_leaf_slot_allocation.json` — exact versioned live-range allocation of the checked leaf
- `arithmetic_lowerings.json` — explicit stage/block inventories for the named arithmetic-kernel family
- `module_library.json` — arithmetic-kernel summary used by the frontier
- `lookup_lowerings.json` — explicit stage/block inventories for the named folded lookup families
- `phase_shell_lowerings.json` — explicit stage/block inventories for the named full-register and semiclassical inverse-QFT shells
- `generated_block_inventories.json` — generated whole-oracle block inventories for the supporting decomposition layer
- `ft_ir_compositions.json` — compositional FT-style call graphs and leaf sigma reconstructions for every named compiler family
- `whole_oracle_recount.json` — independent exact whole-oracle recount derived from the FT IR leaf sigma
- `subcircuit_equivalence.json` — cross-layer equivalence witnesses for traced ISA opcodes, lowered lookup families, the coherent cleanup window, and generated whole-oracle composition
- `primitive_multiplier_library.json` — auditable manifest for all 341 multiplier instances in the raw-32 oracle
- `phase_shell_families.json` — compact summary of the exact phase-shell lowering families
- `table_manifests.json` — exact folded-table dimensions and canonical window bases
- `full_attack_inventory.json` — structural inventory for the completed oracle
- `verification_summary.json` — deterministic semantic replay plus cross-artifact integrity checks for schedule, slot allocation, FT IR composition, lowered inventories, frontier, physical-estimator integrations, and transfer handoffs
- `azure_resource_estimator_targets.json` — exact-family Microsoft Resource Estimator target profiles built from the official predefined presets
- `azure_resource_estimator_results.json` — recorded Microsoft Resource Estimator outputs for every exact family under every checked target profile
- `cain_exact_transfer.json` — heuristic physical transfer for the exact families
- `azure_resource_estimator_logical_counts.json` — logicalCounts-style handoff artifact for physical estimators

## Current exact frontier

- **best exact gate family:** `23,813,671 non-Clifford`
- **best exact qubit family:** `2,338 logical qubits`

The best exact gate family uses folded unary QROM with measurement-based
uncompute. The best exact qubit family uses folded linear-scan lookup plus an
exact semiclassical-QFT phase shell and an exact 9-slot leaf allocation.

## Interpreting the results

This subproject is strongest when read as a **compiler-family exact oracle**,
not as a claim of hidden-Google reconstruction or global optimality.

Its defining exact features are:

- exact slot allocation cuts the leaf-side arithmetic peak from 10 named field
  slots to **9 exact physical field slots**;
- explicit arithmetic lowerings reconstruct the leaf-side non-Clifford totals
  from stage/block inventories instead of from naked opcode formulas;
- explicit lookup lowerings reconstruct each lookup-family count from checked
  stage/block inventories instead of from naked family formulas;
- explicit phase-shell lowerings reconstruct Hadamard, rotation, measurement,
  and rotation-depth counts from checked stage/block inventories instead of
  from shell-level placeholders;
- FT IR compositions reconstruct each family from hierarchical bundles plus a
  traversed leaf sigma instead of only from flattened generated blocks;
- whole-oracle recount reconstructs the frontier totals from the FT IR leaf
  sigma rather than directly from the generated block inventory layer;
- subcircuit-equivalence witnesses bind traced ISA arithmetic/flag opcodes,
  lowered lookup-family semantics, the coherent cleanup window, and generated
  whole-oracle composition back to the checked source artifacts;
- exact logicalCounts are bound to explicit Microsoft Resource Estimator target
  profiles and recorded estimator outputs instead of stopping at a seed-only
  handoff layer;
- generated whole-oracle block inventories reconstruct each family total from
  arithmetic blocks, lookup blocks, qubit contributors, and explicit
  phase-shell lowering blocks;
- a semiclassical-QFT phase-shell family removes the fixed **512 live phase
  qubits** assumption; and
- those two ingredients place the best exact low-qubit family at **2,338
  logical qubits**.

## Quick start

From the repository root:

```bash
python compiler_verification_project/scripts/build.py
python compiler_verification_project/scripts/verify.py --cases 16
```
