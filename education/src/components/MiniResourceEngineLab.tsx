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
  const [selectedTick, setSelectedTick] = useState(4);

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

  const peakLiveSummary = derived.peak.live.map((wire) => `${wire.id} ${wire.width}q`).join(', ');
  const selectedRow = derived.tickLoads.find((tick) => tick.tick === selectedTick) ?? derived.peak;
  const selectedLiveSummary = selectedRow.live.map((wire) => `${wire.id} ${wire.width}q -> ${wire.owner}`).join(', ');
  const selectedOwnerEquations = selectedRow.ownerLoads.map((owner) => `${owner.id}: ${owner.load}/${owner.capacity}`).join('; ');
  const worstOwnerRows = owners.map((owner) => {
    const ownerRows = derived.tickLoads.map((tick) => {
      const load = derived.intervals
        .filter((wire) => wire.owner === owner.id && wire.start <= tick.tick && tick.tick < wire.end)
        .reduce((sum, wire) => sum + wire.width, 0);
      return { tick: tick.tick, load };
    });
    const worst = ownerRows.reduce((best, row) => (row.load > best.load ? row : best), ownerRows[0]);
    return `${owner.id} ${worst.load}/${owner.capacity} at row ${worst.tick}`;
  });

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

      <div className="engine-audit-grid">
        <article className="pass">
          <span>1. Liveness</span>
          <strong>peak {derived.peak.total} live wires</strong>
          <p>The peak is derived from intervals, not from a handpicked list.</p>
        </article>
        <article className={derived.ownerCapacityPass && derived.exactOwnerPass ? 'pass' : 'fail'}>
          <span>2. Owner capacity</span>
          <strong>{derived.ownerCapacityPass && derived.exactOwnerPass ? 'assigned and sized' : 'assignment invalid'}</strong>
          <p>Each live wire needs exactly one owner whose capacity can hold it.</p>
        </article>
        <article className={derived.cleanupPass ? 'pass' : 'fail'}>
          <span>3. Cleanup</span>
          <strong>{derived.cleanupPass ? 'scratch dies early' : 'scratch remains live'}</strong>
          <p>Uncompute must use the source path that created the temporary value.</p>
        </article>
      </div>

      <section className="row-witness-inspector" aria-label="Row witness inspector">
        <div>
          <h4>Row witness inspector</h4>
          <p>
            Select any primitive row and replay the same liveness query the peak
            counter uses. The peak row is just the row with the largest generated load.
          </p>
        </div>
        <div className="row-witness-controls">
          {derived.tickLoads.map((tick) => (
            <button
              className={tick.tick === selectedRow.tick ? 'selected' : ''}
              key={tick.tick}
              onClick={() => setSelectedTick(tick.tick)}
              type="button"
            >
              row {tick.tick}
            </button>
          ))}
          <button type="button" onClick={() => setSelectedTick(derived.peak.tick)}>
            jump to peak row
          </button>
        </div>
        <div className="row-witness-grid">
          <article>
            <span>Selected row</span>
            <strong>row {selectedRow.tick} witness</strong>
            <p>{selectedRow.total} live qubits</p>
          </article>
          <article>
            <span>Live groups</span>
            <strong>{selectedLiveSummary || 'none'}</strong>
            <p>This list is generated from row intervals.</p>
          </article>
          <article>
            <span>Owner equations</span>
            <strong>{selectedOwnerEquations}</strong>
            <p>Each owner load is checked against capacity at this same row.</p>
          </article>
        </div>
      </section>

      <div className="same-stream-ledger">
        <h4>Same stream ledger</h4>
        <article>
          <span>Primitive stream</span>
          <strong>{primitiveRows.length} rows</strong>
          <p>The executable rows are the only object the rest of the lab reads.</p>
        </article>
        <article>
          <span>Liveness query</span>
          <strong>peak row {derived.peak.tick}</strong>
          <p>{peakLiveSummary}</p>
        </article>
        <article className={derived.ownerCapacityPass ? 'pass' : 'fail'}>
          <span>Owner query</span>
          <strong>{derived.ownerCapacityPass ? 'capacity ok' : 'capacity overflow'}</strong>
          <p>{worstOwnerRows.join('; ')}</p>
        </article>
        <article className={derived.pass ? 'pass' : 'fail'}>
          <span>Claim line</span>
          <strong>peak {derived.peak.total}, audit {derived.pass ? 'pass' : 'fail'}</strong>
          <p>This is the tiny version of docs and proof reading emitted artifact fields.</p>
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
