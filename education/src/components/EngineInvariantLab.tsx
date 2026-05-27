import { useMemo, useState } from 'react';
import { Cpu } from 'lucide-react';

const baseRows = [
  { wire: 'qx[0..255]', owner: 'tail_slot_1', capacity: 256, live: 'tail rows 0-22' },
  { wire: 'qchunk[0..154]', owner: 'lookup_workspace', capacity: 173, live: 'qroam stream' },
  { wire: 'phase', owner: 'phase_shell', capacity: 1, live: 'semiclassical qft' },
  { wire: 'guard', owner: 'tail_guard', capacity: 1, live: 'zero-lift predicate' },
];

export function EngineInvariantLab() {
  const [includeHiddenScratch, setIncludeHiddenScratch] = useState(false);
  const rows = includeHiddenScratch
    ? [...baseRows, { wire: 'scratch_tmp[0..253]', owner: 'unowned', capacity: 0, live: 'hidden guard ladder' }]
    : baseRows;
  const audit = useMemo(() => {
    const unowned = rows.filter((row) => row.owner === 'unowned' || row.capacity === 0);
    return {
      pass: unowned.length === 0,
      unowned,
      countedCapacity: rows.reduce((total, row) => total + row.capacity, 0),
    };
  }, [rows]);

  return (
    <article className="lab-panel" data-testid="engine-invariant-lab">
      <div className="panel-heading">
        <Cpu size={20} />
        <h3>No-free-wire invariant</h3>
      </div>
      <label className="toggle-row">
        <input checked={includeHiddenScratch} onChange={(event) => setIncludeHiddenScratch(event.currentTarget.checked)} type="checkbox" />
        Inject hidden scratch lane
      </label>
      <div className="owner-table" role="table" aria-label="Wire owner table">
        <div role="row"><strong>Wire</strong><strong>Owner</strong><strong>Capacity</strong><strong>Live interval</strong></div>
        {rows.map((row) => (
          <div className={row.owner === 'unowned' ? 'bad-owner' : ''} role="row" key={row.wire}>
            <span>{row.wire}</span>
            <span>{row.owner}</span>
            <span>{row.capacity}</span>
            <span>{row.live}</span>
          </div>
        ))}
      </div>
      <p className={audit.pass ? 'audit-pass' : 'audit-fail'}>
        Audit: {audit.pass ? 'pass' : `fail, ${audit.unowned.length} wire group has no counted owner`}
      </p>
      <p>Peak qubits must come from executable liveness, not from a hand-picked register list. This is the class of invariant the repo is moving toward.</p>
    </article>
  );
}
