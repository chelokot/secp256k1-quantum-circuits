import { useMemo, useState } from 'react';
import { RotateCcw } from 'lucide-react';

const steps = [
  { id: 'compute_a', label: 'compute A = x & y', phase: 'compute' },
  { id: 'consume_a', label: 'consume A into accumulator', phase: 'use' },
  { id: 'uncompute_a', label: 'uncompute A with same x,y', phase: 'cleanup' },
  { id: 'measure_phase', label: 'measure phase bit', phase: 'output' },
];

export function CleanupPuzzleLab() {
  const [selected, setSelected] = useState<string[]>(['compute_a', 'consume_a']);
  const toggle = (id: string) => {
    setSelected((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  };
  const audit = useMemo(() => {
    const computes = selected.includes('compute_a');
    const consumes = selected.includes('consume_a');
    const uncomputes = selected.includes('uncompute_a');
    const pass = computes && consumes && uncomputes;
    return {
      pass,
      message: pass ? 'scratch returns to |0>; no garbage remains' : 'scratch is still live or unproven',
      liveScratch: computes && !uncomputes,
    };
  }, [selected]);

  return (
    <article className="lab-panel" data-testid="cleanup-puzzle-lab">
      <div className="panel-heading">
        <RotateCcw size={20} />
        <h3>Reversible cleanup puzzle</h3>
      </div>
      <div className="cleanup-steps">
        {steps.map((step) => (
          <button
            className={selected.includes(step.id) ? `cleanup-step selected ${step.phase}` : `cleanup-step ${step.phase}`}
            key={step.id}
            type="button"
            onClick={() => toggle(step.id)}
          >
            <span>{step.phase}</span>
            <strong>{step.label}</strong>
          </button>
        ))}
      </div>
      <div className="cleanup-wire">
        <span>x</span>
        <span>y</span>
        <span className={audit.liveScratch ? 'wire-live' : 'wire-clean'}>scratch A</span>
        <span>accumulator</span>
      </div>
      <p className={audit.pass ? 'audit-pass' : 'audit-fail'}>Audit: {audit.pass ? 'pass' : 'fail'}; {audit.message}</p>
      <p>
        The source-uncompute artifact in this repo is the large-scale version:
        prove that a temporary target can be rebuilt from still-live controls and
        toggled back away.
      </p>
    </article>
  );
}
