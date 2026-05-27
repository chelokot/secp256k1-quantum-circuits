import { useMemo, useState } from 'react';
import { Network } from 'lucide-react';

type Wire = {
  id: string;
  width: number;
  start: number;
  endWithoutCleanup: number;
  endWithCleanup: number;
  fixedOwner?: string;
};

type Owner = {
  id: string;
  capacity: number;
};

const owners: Owner[] = [
  { id: 'tail_field_slot', capacity: 4 },
  { id: 'lookup_workspace', capacity: 3 },
  { id: 'scratch_workspace', capacity: 2 },
  { id: 'phase_shell', capacity: 1 },
];

const wires: Wire[] = [
  { id: 'A field slot', width: 4, start: 0, endWithoutCleanup: 6, endWithCleanup: 6, fixedOwner: 'tail_field_slot' },
  { id: 'lookup target', width: 3, start: 1, endWithoutCleanup: 5, endWithCleanup: 5, fixedOwner: 'lookup_workspace' },
  { id: 'partial scratch', width: 2, start: 2, endWithoutCleanup: 6, endWithCleanup: 4 },
  { id: 'phase bit', width: 1, start: 4, endWithoutCleanup: 6, endWithCleanup: 6, fixedOwner: 'phase_shell' },
];

const primitiveRows = [
  ['0', 'load_input', 'A field slot becomes live'],
  ['1', 'qroam_lookup', 'lookup target is filled'],
  ['2', 'ccx partials', 'partial scratch appears'],
  ['3', 'consume', 'scratch controls accumulator update'],
  ['4', 'uncompute?', 'scratch can be cleaned here'],
  ['5', 'measure phase', 'phase bit exits the coherent region'],
];

const ticks = [0, 1, 2, 3, 4, 5];

export function MiniResourceEngineLab() {
  const [scratchOwner, setScratchOwner] = useState('lookup_workspace');
  const [cleanupEnabled, setCleanupEnabled] = useState(false);

  const derived = useMemo(() => {
    const intervals = wires.map((wire) => ({
      ...wire,
      owner: wire.fixedOwner ?? scratchOwner,
      end: cleanupEnabled ? wire.endWithCleanup : wire.endWithoutCleanup,
    }));
    const tickLoads = ticks.map((tick) => {
      const live = intervals.filter((wire) => wire.start <= tick && tick < wire.end);
      const total = live.reduce((sum, wire) => sum + wire.width, 0);
      const ownerLoads = owners.map((owner) => {
        const load = live
          .filter((wire) => wire.owner === owner.id)
          .reduce((sum, wire) => sum + wire.width, 0);
        return { ...owner, load, pass: load <= owner.capacity };
      });
      return { tick, live, total, ownerLoads };
    });
    const peak = tickLoads.reduce((best, row) => (row.total > best.total ? row : best), tickLoads[0]);
    const ownerCapacityPass = tickLoads.every((row) => row.ownerLoads.every((owner) => owner.pass));
    const exactOwnerPass = scratchOwner === 'scratch_workspace';
    const cleanupPass = cleanupEnabled;
    return {
      intervals,
      tickLoads,
      peak,
      ownerCapacityPass,
      exactOwnerPass,
      cleanupPass,
      pass: ownerCapacityPass && exactOwnerPass && cleanupPass,
    };
  }, [cleanupEnabled, scratchOwner]);

  return (
    <section className="wide-panel" data-testid="mini-resource-engine-lab">
      <div className="panel-heading">
        <Network size={20} />
        <h3>Mini resource engine</h3>
      </div>
      <div className="mini-engine-grid">
        <article>
          <h4>Primitive rows</h4>
          <div className="mini-netlist" role="table" aria-label="Mini primitive netlist">
            {primitiveRows.map(([row, op, meaning]) => (
              <div role="row" key={row}>
                <strong>{row}</strong>
                <span>{op}</span>
                <span>{meaning}</span>
              </div>
            ))}
          </div>
        </article>

        <article>
          <h4>Your lowering choices</h4>
          <label className="assignment-control">
            <span>Owner for partial scratch</span>
            <select
              aria-label="Owner for partial scratch"
              value={scratchOwner}
              onChange={(event) => setScratchOwner(event.currentTarget.value)}
            >
              {owners.map((owner) => (
                <option key={owner.id} value={owner.id}>{owner.id}</option>
              ))}
            </select>
          </label>
          <label className="toggle-row">
            <input
              aria-label="Add source uncompute row"
              checked={cleanupEnabled}
              onChange={(event) => setCleanupEnabled(event.currentTarget.checked)}
              type="checkbox"
            />
            <span>add source-uncompute after consume</span>
          </label>
          <p className={derived.pass ? 'audit-pass' : 'audit-fail'}>
            Engine audit: {derived.pass ? 'pass' : 'fail'}
          </p>
          <p>
            Peak live qubits: {derived.peak.total} at row {derived.peak.tick}.
            Owner capacity {derived.ownerCapacityPass ? 'ok' : 'overflow'},
            scratch owner {derived.exactOwnerPass ? 'ok' : 'wrong'},
            cleanup {derived.cleanupPass ? 'ok' : 'missing'}.
          </p>
        </article>
      </div>

      <div className="liveness-timeline">
        {derived.intervals.map((wire) => (
          <div key={wire.id}>
            <span>{wire.id}</span>
            {ticks.map((tick) => (
              <i
                className={wire.start <= tick && tick < wire.end ? 'live' : ''}
                key={tick}
                title={`row ${tick}`}
              />
            ))}
            <strong>{wire.owner}</strong>
          </div>
        ))}
      </div>

      <div className="owner-load-timeline">
        {derived.tickLoads.map((tick) => (
          <article key={tick.tick}>
            <strong>row {tick.tick}</strong>
            <span>total {tick.total}</span>
            {tick.ownerLoads.map((owner) => (
              <em className={owner.pass ? '' : 'bad-owner'} key={owner.id}>
                {owner.id}: {owner.load}/{owner.capacity}
              </em>
            ))}
          </article>
        ))}
      </div>
    </section>
  );
}
