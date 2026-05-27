# Baseline hardening track

This report is generated from `compiler_verification_project/artifacts/current_baseline_status.json`.
It is the human-readable checklist for turning the current conservative
resource target into an accepted Clifford-complete physical baseline.

## Current verdict

- Accepted Clifford-complete physical baseline: **none yet**.
- Conservative hardening target under review: **36,973,222 non-Clifford / 2,222 logical qubits**.
- Lower strict replayed-tail candidate: **36,973,222 non-Clifford / 1,968 logical qubits**, not accepted.
- Acceptance gate: **blocked**; decision is `do_not_promote_any_resource_number_to_accepted_physical_baseline`.

The repository should present the conservative hardening target when it
needs a single current number, because it includes the zero-lift guard
clean-ladder capacity consequence that the lower strict candidate does not
promote. It must not be described as accepted until the gate below closes.

## Hardening-target derivation

| Term | Logical qubits |
|---|---:|
| strict replayed-tail candidate | 1,968 |
| additional clean-ladder guard qubits | 254 |
| reconstructed hardening target | 2,222 |

The non-Clifford count is unchanged in this conservative correction because
the guard audit is a capacity correction, not a new gate-count reduction.

## Acceptance gate

| Gate | Status | Evidence | Required closeout |
|---|---:|---|---|
| `single_authoritative_primitive_stream` | blocked | `engine_completion_audit.clifford_complete_goal_achieved` | Make the global flat primitive stream the only source for execution, liveness, owner capacity, and resource totals. |
| `guard_corrected_no_alias_capacity_promoted_into_liveness` | blocked | `zero_lift_guard_resource_audit.promotion_status` | Promote the zero-lift guard capacity into the scheduled primitive liveness owner model or prove a concrete alias/no-ancilla predicate construction. |
| `modular_accumulator_source_uncompute_promoted` | blocked | `modular_accumulator_source_uncompute.promotion_status` | Promote consume/fold/source-uncompute rows into the same scheduled primitive netlist used for the public peak calculation. |
| `no_abandoned_synthetic_arithmetic_scratch` | blocked | `engine_completion_audit.remaining_macro_boundaries[0].evidence_metrics.synthetic_arithmetic_scratch_abandoned_garbage` | Replace synthetic modular-arithmetic scratch observations with concrete primitive wires, owners, liveness, and cleanup. |
| `publication_gate_allows_resource_headline` | blocked | `public_headline_result.pass + publication_blockers` | Clear public-headline publication blockers before any accepted baseline is advertised outside the candidate layer. |

## Active physical-baseline blockers

- `zero_lift_guard_capacity_not_promoted`: `zero_lift_guard_capacity_gap_not_promoted_to_public_contract`
  Missing clean-ladder guard capacity: 254 logical qubits.
- `modular_accumulator_source_uncompute_not_promoted`: `source_uncompute_contract_not_promoted_to_scheduled_primitive_netlist`
  Proven partial-product cleanup: 720,896 CCX rows.
  Guard cleanup rows still missing source controls: 510.
- `modular_arithmetic_clifford_expansion_not_flattened`: `modular_arithmetic_clifford_expansion`
  Clifford-complete engine achieved: false.

## Forbidden wording before acceptance

- do not present 1199, 1044, or 1968 logical qubits as the accepted physical baseline
- do not present 2222 logical qubits as accepted; present it only as the conservative hardening target under review
- do not run or advertise proof freshness until the cheap artifact gates and proof_status gates pass

## Required closeout

- Promote zero-lift guard capacity into the scheduled primitive liveness owner model or prove an executable alias/no-ancilla construction.
- Promote modular accumulator consume/fold/source-uncompute rows into the global scheduled primitive netlist.
- Recompute public totals from the same primitive stream used by tests and ZKP input.
- Only then rebuild proof inputs and proof bundles if a ZKP-backed release claim is desired.

## Practical policy

Use `36,973,222 / 2,222` as the central hardening track and cleanup
target. Use `36,973,222 / 1,968`, `1,199`, `1,044`, and sub-1600 rows
only as candidates, references, or quarantined hypotheses unless a future
artifact closes the acceptance gate and recomputes the accepted totals from
the same executable primitive stream.
