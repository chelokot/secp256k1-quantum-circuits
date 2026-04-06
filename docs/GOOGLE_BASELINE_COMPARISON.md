# Google baseline comparison

The comparison target in this repository is the **public** Google appendix envelope.
It is archived in:

- `artifacts/optimized/out/resource_projection.json`

## Public baseline lines

- low-qubit line: **1191 logical qubits**, **81,105,024 non-Clifford**
- low-gate line: **1441 logical qubits**, **64,305,024 non-Clifford**
- window size: **16**
- retained point additions: **28**

## Optimized repository projection

- optimized line: **880 logical qubits**
- 2-lookup model: **30,998,464 non-Clifford**
- 3-lookup model: **32,833,472 non-Clifford**

## Improvement factors

Versus the public low-qubit line:
- **1.3534x fewer logical qubits**
- **2.6164x lower non-Clifford** in the 2-lookup model
- **2.4702x lower non-Clifford** in the 3-lookup model

Versus the public low-gate line:
- **1.6375x fewer logical qubits**
- **2.0745x lower non-Clifford** in the 2-lookup model
- **1.9585x lower non-Clifford** in the 3-lookup model

## Sensitivity / hostile-backend margin

See:

- `artifacts/optimized/out/projection_sensitivity.json`
- `artifacts/optimized/figures/projection_headroom.png`

The key margins are:

- about **33.3M** non-Clifford headroom versus the public low-gate line in the 2-lookup model,
- about **50.1M** headroom versus the public low-qubit line in the 2-lookup model,
- about **31.5M** and **48.3M** respectively in the 3-lookup model.

## Honesty note

This file compares **modeled backend totals** below the ISA boundary.
It is not a theorem-proved primitive-gate comparison.
