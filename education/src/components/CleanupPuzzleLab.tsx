import { useMemo, useState } from 'react';
import { RotateCcw } from 'lucide-react';

type CleanupStep = {
  id: string;
  label: string;
  phase: 'compute' | 'use' | 'hazard' | 'cleanup' | 'output';
  row: string;
};

const steps = [
  { id: 'compute_a', label: 'compute A = x & y', phase: 'compute', row: 'CCX x y A' },
  { id: 'consume_a', label: 'consume A into accumulator', phase: 'use', row: 'CX A accumulator' },
  { id: 'overwrite_x', label: 'overwrite x before cleanup', phase: 'hazard', row: 'UPDATE x' },
  { id: 'uncompute_a', label: 'uncompute A with same x,y', phase: 'cleanup', row: 'CCX x y A' },
  { id: 'measure_phase', label: 'measure phase bit', phase: 'output', row: 'M phase' },
] satisfies CleanupStep[];

export function CleanupPuzzleLab() {
  const [selected, setSelected] = useState<string[]>(['compute_a', 'consume_a']);
  const toggle = (id: string) => {
    setSelected((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  };
  const audit = useMemo(() => {
    const computes = selected.includes('compute_a');
    const consumes = selected.includes('consume_a');
    const uncomputes = selected.includes('uncompute_a');
    const measures = selected.includes('measure_phase');
    const sourceOverwritten = selected.includes('overwrite_x');
    const cleanupExecutable = uncomputes && !sourceOverwritten;
    const pass = computes && consumes && cleanupExecutable;
    const selectedRows = steps.filter((step) => selected.includes(step.id));
    return {
      pass,
      cleanupExecutable,
      consumes,
      computes,
      measures,
      message: pass ? 'scratch returns to |0>; no garbage remains' : sourceOverwritten ? 'cleanup label exists, but x changed before the inverse' : 'scratch is still live or unproven',
      liveScratch: computes && !cleanupExecutable,
      selectedRows,
      sourceOverwritten,
      uncomputes,
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
            <em>{step.row}</em>
          </button>
        ))}
      </div>
      <div className="cleanup-wire">
        <span>x</span>
        <span>y</span>
        <span className={audit.liveScratch ? 'wire-live' : 'wire-clean'}>scratch A</span>
        <span>accumulator</span>
      </div>
      <div className="cleanup-ledger">
        <article>
          <span>Birth row</span>
          <strong>{audit.computes ? 'present' : 'missing'}</strong>
          <p>Scratch A is created from source controls x,y.</p>
        </article>
        <article>
          <span>Use row</span>
          <strong>{audit.consumes ? 'present' : 'missing'}</strong>
          <p>The useful effect is copied into the accumulator.</p>
        </article>
        <article>
          <span>Death row</span>
          <strong>{audit.uncomputes ? 'present' : 'missing'}</strong>
          <p>The same source controls x,y must rebuild and erase A.</p>
        </article>
        <article>
          <span>Measurement</span>
          <strong>{audit.measures ? 'selected' : 'not cleanup'}</strong>
          <p>Reading another output does not erase scratch A.</p>
        </article>
      </div>
      <section className="cleanup-proof-packet" aria-label="Cleanup proof packet">
        <h4>Cleanup proof packet</h4>
        <article>
          <span>Row sequence</span>
          <strong>{audit.selectedRows.map((step) => step.row).join(' -> ')}</strong>
          <p>The audit reads the selected rows in circuit order, not as a prose summary.</p>
        </article>
        <article>
          <span>Source availability</span>
          <strong>{audit.sourceOverwritten ? 'broken' : 'x,y still live'}</strong>
          <p>{audit.sourceOverwritten ? 'x was changed before the inverse, so CCX x y A is only a label.' : 'The controls that created A are still available for the inverse row.'}</p>
        </article>
        <article>
          <span>Death receipt</span>
          <strong>{audit.cleanupExecutable ? 'executable inverse' : audit.uncomputes ? 'label only' : 'missing'}</strong>
          <p>{audit.cleanupExecutable ? 'The same CCX row can be replayed to return A to zero.' : 'Without an executable inverse, A remains live or unproven.'}</p>
        </article>
      </section>
      <p className={audit.pass ? 'audit-pass' : 'audit-fail'}>Audit: {audit.pass ? 'pass' : 'fail'}; {audit.message}</p>
      <p>
        The source-uncompute artifact in this repo is the large-scale version:
        prove that a temporary target can be rebuilt from still-live controls and
        toggled back away.
      </p>
    </article>
  );
}
