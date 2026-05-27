import { useState } from 'react';
import { Layers3 } from 'lucide-react';

type ProjectData = {
  strictFormula: {
    tail_field_slots: number;
    field_bits: number;
    lookup_workspace_qubits: number;
    control_qubits: number;
    phase_qubits: number;
    reconstructed_total: number;
  };
  zeroLiftGuard: {
    cleanLadder: {
      peak_predicate_workspace_bits: number;
    };
    gap: {
      missing_logical_qubits_under_clean_ladder: number;
    };
  };
};

export function SlotLiveness({ projectData }: { projectData: ProjectData }) {
  const [includeGuardGap, setIncludeGuardGap] = useState(false);
  const formula = projectData.strictFormula;
  const total = formula.reconstructed_total + (includeGuardGap ? projectData.zeroLiftGuard.gap.missing_logical_qubits_under_clean_ladder : 0);
  const slots = Array.from({ length: formula.tail_field_slots }, (_, index) => index);

  return (
    <article className="lab-panel" data-testid="slot-liveness">
      <div className="panel-heading">
        <Layers3 size={20} />
        <h3>Field slots and guard gap</h3>
      </div>
      <div className="slot-grid" aria-label="Seven live field slots">
        {slots.map((slot) => (
          <div className="slot" key={slot}>
            <span>slot {slot + 1}</span>
            <strong>{formula.field_bits}</strong>
            <small>wires</small>
          </div>
        ))}
      </div>
      <label className="toggle-row">
        <input
          checked={includeGuardGap}
          onChange={(event) => setIncludeGuardGap(event.currentTarget.checked)}
          type="checkbox"
        />
        Count clean-ladder zero-lift guard capacity
      </label>
      <dl className="metric-row">
        <div><dt>Tail</dt><dd>{formula.tail_field_slots} * {formula.field_bits}</dd></div>
        <div><dt>Lookup</dt><dd>{formula.lookup_workspace_qubits}</dd></div>
        <div><dt>Control+phase</dt><dd>{formula.control_qubits + formula.phase_qubits}</dd></div>
        <div><dt>Total</dt><dd>{total}</dd></div>
      </dl>
      <p>
        The strict candidate counts one guard qubit. The conservative no-alias view adds
        {` ${projectData.zeroLiftGuard.gap.missing_logical_qubits_under_clean_ladder} `}
        missing predicate-workspace qubits.
      </p>
    </article>
  );
}
