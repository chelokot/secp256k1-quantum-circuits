type BlockerCopy = {
  label: string;
  summary: string;
};

const blockerCopy: Record<string, BlockerCopy> = {
  zero_lift_guard_capacity_not_promoted: {
    label: 'Zero-lift guard capacity',
    summary: 'The clean predicate ladder needs counted workspace or a concrete alias proof before it can support a public qubit total.',
  },
  modular_accumulator_source_uncompute_not_promoted: {
    label: 'Modular accumulator cleanup',
    summary: 'Partial-product consume and source-uncompute rows still need promotion into the scheduled primitive netlist.',
  },
  modular_arithmetic_clifford_expansion_not_flattened: {
    label: 'Full arithmetic primitive expansion',
    summary: 'The remaining modular arithmetic boundary must become exact Clifford and non-Clifford wire rows inside the same flat stream.',
  },
  single_authoritative_primitive_stream: {
    label: 'Single primitive stream',
    summary: 'Execution, liveness, owner capacity, resource totals, and proof input must all use the same flat row stream.',
  },
  guard_corrected_no_alias_capacity_promoted_into_liveness: {
    label: 'Guard capacity in liveness',
    summary: 'The guard-corrected owner model must be promoted, or a concrete no-ancilla alias construction must be proved.',
  },
  modular_accumulator_source_uncompute_promoted: {
    label: 'Accumulator cleanup promoted',
    summary: 'Consume, fold, and source-uncompute rows must be part of the same scheduled netlist used for the public peak.',
  },
  no_abandoned_synthetic_arithmetic_scratch: {
    label: 'No synthetic scratch leftovers',
    summary: 'Synthetic arithmetic scratch observations must be replaced by concrete primitive wires, owners, liveness, and cleanup.',
  },
  publication_gate_allows_resource_headline: {
    label: 'Publication gate cleared',
    summary: 'Docs, public headline artifacts, and proof publication checks must agree before any number is advertised as accepted.',
  },
};

const statusCopy: Record<string, string> = {
  blocked: 'blocked',
  zero_lift_guard_capacity_gap_not_promoted_to_public_contract: 'capacity gap not promoted',
  source_uncompute_contract_not_promoted_to_scheduled_primitive_netlist: 'cleanup contract not promoted',
  modular_arithmetic_clifford_expansion: 'primitive expansion still incomplete',
};

const readable = (value: string) => value.replaceAll('_', ' ');

export function blockerLabel(name: string) {
  return blockerCopy[name]?.label ?? readable(name);
}

export function blockerSummary(name: string) {
  return blockerCopy[name]?.summary ?? 'This gate needs artifact-backed evidence before the claim level can be raised.';
}

export function blockerStatusLabel(status: string) {
  return statusCopy[status] ?? readable(status);
}
