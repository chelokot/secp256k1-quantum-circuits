import { useMemo, useState } from 'react';
import { CircuitBoard, Plus, RotateCcw } from 'lucide-react';

type GateKind = 'H' | 'X' | 'CX' | 'CCX' | 'M';

const gateCost: Record<GateKind, { nonClifford: number; qubitsTouched: number; label: string }> = {
  H: { nonClifford: 0, qubitsTouched: 1, label: 'Hadamard' },
  X: { nonClifford: 0, qubitsTouched: 1, label: 'Bit flip' },
  CX: { nonClifford: 0, qubitsTouched: 2, label: 'Controlled X' },
  CCX: { nonClifford: 1, qubitsTouched: 3, label: 'Toffoli-like' },
  M: { nonClifford: 0, qubitsTouched: 1, label: 'Measure' },
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
      <dl className="metric-row">
        <div><dt>Rows</dt><dd>{gates.length}</dd></div>
        <div><dt>Non-Clifford</dt><dd>{totals.nonClifford}</dd></div>
        <div><dt>Peak touched</dt><dd>{totals.maxTouched}</dd></div>
      </dl>
      <p>A real repo netlist is this idea at painful scale: every row points to concrete wires and owners.</p>
    </article>
  );
}
