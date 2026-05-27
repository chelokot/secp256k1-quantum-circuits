import { useMemo, useState } from 'react';
import { CircuitBoard, Plus, RotateCcw } from 'lucide-react';

type GateKind = 'H' | 'X' | 'CX' | 'CCX' | 'M';

const gateCost: Record<GateKind, { nonClifford: number; qubitsTouched: number; label: string; operands: string; effect: string }> = {
  H: { nonClifford: 0, qubitsTouched: 1, label: 'Hadamard', operands: 'q0', effect: 'creates a 0/1 amplitude split' },
  X: { nonClifford: 0, qubitsTouched: 1, label: 'Bit flip', operands: 'q2', effect: 'flips one target wire' },
  CX: { nonClifford: 0, qubitsTouched: 2, label: 'Controlled X', operands: 'q0 -> q1', effect: 'target changes only under control' },
  CCX: { nonClifford: 1, qubitsTouched: 3, label: 'Toffoli-like', operands: 'q0,q1 -> q2', effect: 'expensive controlled product' },
  M: { nonClifford: 0, qubitsTouched: 1, label: 'Measure', operands: 'q2', effect: 'reads one output wire' },
};

export function CircuitBuilder() {
  const [gates, setGates] = useState<GateKind[]>(['H', 'CX', 'CCX']);
  const totals = useMemo(() => {
    return gates.reduce(
      (accumulator, gate) => ({
        nonClifford: accumulator.nonClifford + gateCost[gate].nonClifford,
        maxTouched: Math.max(accumulator.maxTouched, gateCost[gate].qubitsTouched),
      }),
      { nonClifford: 0, maxTouched: 0 },
    );
  }, [gates]);

  return (
    <article className="lab-panel" data-testid="circuit-builder">
      <div className="panel-heading">
        <CircuitBoard size={20} />
        <h3>Primitive netlist toy</h3>
      </div>
      <p>
        A resource claim starts as rows like these: operation, operands, and cost.
        The visual rail is only a picture; the row table is the countable object.
      </p>
      <div className="gate-literacy-grid" aria-label="How to read a primitive row">
        <article>
          <span>Row</span>
          <strong>time step</strong>
          <p>Rows are ordered. Later rows may depend on earlier wire values.</p>
        </article>
        <article>
          <span>Operands</span>
          <strong>named wires</strong>
          <p>Every touched wire must exist, stay live, and be owned.</p>
        </article>
        <article>
          <span>Cost</span>
          <strong>primitive resource</strong>
          <p>CCX marks the first non-Clifford expense in this toy.</p>
        </article>
      </div>
      <div className="circuit-rails" aria-label="Toy circuit netlist">
        {[0, 1, 2].map((wire) => (
          <div className="wire" key={wire}>
            <span>q{wire}</span>
            <div />
          </div>
        ))}
        <div className="gate-stack">
          {gates.map((gate, index) => (
            <span className={gate === 'CCX' ? 'gate non-clifford' : 'gate'} key={`${gate}-${index}`}>
              {gate}
            </span>
          ))}
        </div>
      </div>
      <div className="gate-row">
        {Object.keys(gateCost).map((gate) => (
          <button key={gate} type="button" onClick={() => setGates((items) => [...items, gate as GateKind])}>
            <Plus size={14} />
            {gate}
          </button>
        ))}
        <button type="button" aria-label="Reset circuit" onClick={() => setGates([])}>
          <RotateCcw size={16} />
        </button>
      </div>
      <div className="netlist-table" aria-label="Primitive row table">
        <div className="netlist-header">
          <span>row</span>
          <span>op</span>
          <span>operands</span>
          <span>effect</span>
          <span>non-Clifford</span>
        </div>
        {gates.map((gate, index) => (
          <div className={gate === 'CCX' ? 'netlist-row hot' : 'netlist-row'} key={`${gate}-row-${index}`}>
            <span>{index + 1}</span>
            <strong>{gate}</strong>
            <span>{gateCost[gate].operands}</span>
            <span>{gateCost[gate].effect}</span>
            <span>{gateCost[gate].nonClifford}</span>
          </div>
        ))}
      </div>
      <dl className="metric-row">
        <div><dt>Rows</dt><dd>{gates.length}</dd></div>
        <div><dt>Non-Clifford</dt><dd>{totals.nonClifford}</dd></div>
        <div><dt>Peak touched</dt><dd>{totals.maxTouched}</dd></div>
      </dl>
      <p>A real repo netlist is this idea at painful scale: every row points to concrete wires, owners, cleanup obligations, and primitive costs.</p>
    </article>
  );
}
