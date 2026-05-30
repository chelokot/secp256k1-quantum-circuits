import { useMemo, useState } from 'react';
import { Cpu } from 'lucide-react';

type Wire = {
  id: string;
  width: number;
  requiredOwner: string;
};

const wires: Wire[] = [
  { id: 'tail slot E', width: 256, requiredOwner: 'tail_field_slot' },
  { id: 'qroam target', width: 155, requiredOwner: 'lookup_workspace' },
  { id: 'guard ladder', width: 255, requiredOwner: 'guard_workspace' },
  { id: 'phase bit', width: 1, requiredOwner: 'phase_shell' },
];

const owners = {
  tail_field_slot: 256,
  lookup_workspace: 173,
  guard_workspace: 255,
  phase_shell: 1,
};

export function OwnerCapacityGame() {
  const [assignments, setAssignments] = useState<Record<string, string>>({
    'tail slot E': 'tail_field_slot',
    'qroam target': 'lookup_workspace',
    'guard ladder': 'lookup_workspace',
    'phase bit': 'phase_shell',
  });

  const audit = useMemo(() => {
    const rows = Object.entries(owners).map(([owner, capacity]) => {
      const assigned = wires.filter((wire) => assignments[wire.id] === owner);
      const load = assigned.reduce((total, wire) => total + wire.width, 0);
      const formula = assigned.length === 0
        ? '0'
        : assigned.map((wire) => wire.width).join(' + ');
      return {
        owner,
        capacity,
        formula,
        load,
        margin: capacity - load,
        pass: load <= capacity,
      };
    });
    const assignmentRows = wires.map((wire) => ({
      ...wire,
      assignedOwner: assignments[wire.id],
      pass: assignments[wire.id] === wire.requiredOwner,
    }));
    const exactOwnerPass = wires.every((wire) => assignments[wire.id] === wire.requiredOwner);
    const capacityPass = rows.every((row) => row.pass);
    return { assignmentRows, rows, exactOwnerPass, capacityPass, pass: exactOwnerPass && capacityPass };
  }, [assignments]);

  return (
    <article className="lab-panel" data-testid="owner-capacity-game">
      <div className="panel-heading">
        <Cpu size={20} />
        <h3>Owner capacity game</h3>
      </div>
      <div className="assignment-list">
        {wires.map((wire) => (
          <label key={wire.id}>
            <span>{wire.id} ({wire.width}q)</span>
            <select
              aria-label={`Owner for ${wire.id}`}
              value={assignments[wire.id]}
              onChange={(event) => {
                const owner = event.currentTarget.value;
                setAssignments((current) => ({ ...current, [wire.id]: owner }));
              }}
            >
              {Object.keys(owners).map((owner) => (
                <option key={owner} value={owner}>{owner}</option>
              ))}
            </select>
          </label>
        ))}
      </div>
      <div className="owner-capacity-rows">
        {audit.rows.map((row) => (
          <div className={row.pass ? '' : 'bad-owner'} key={row.owner}>
            <span>{row.owner}</span>
            <strong>{row.load}/{row.capacity}</strong>
            <em>{row.margin >= 0 ? `${row.margin}q room` : `${Math.abs(row.margin)}q overflow`}</em>
          </div>
        ))}
      </div>
      <section className="owner-assignment-receipt" aria-label="Owner assignment receipt">
        <h4>Owner assignment receipt</h4>
        {audit.assignmentRows.map((wire) => (
          <article className={wire.pass ? '' : 'bad-owner'} key={wire.id}>
            <span>{wire.id}</span>
            <strong>{wire.assignedOwner} {'->'} needs {wire.requiredOwner}</strong>
            <p>{wire.pass ? 'semantic owner ok' : 'wrong semantic owner even before capacity math'}</p>
          </article>
        ))}
      </section>
      <div className="owner-peak-witness">
        <article>
          <span>Peak witness row</span>
          <strong>fused output boundary</strong>
          <p>All four toy wire groups are live before the row can release them.</p>
        </article>
        <article>
          <span>Live wire groups</span>
          <strong>{wires.map((wire) => `${wire.id} ${wire.width}q`).join(', ')}</strong>
          <p>This row-local list is the source of the peak, not a manually chosen total.</p>
        </article>
        <article>
          <span>Owner load equations</span>
          {audit.rows.map((row) => (
            <strong key={row.owner}>{row.owner}: {row.formula} = {row.load}/{row.capacity}</strong>
          ))}
          <p>Every owner is checked against numeric capacity at the same witness row.</p>
        </article>
      </div>
      <p className={audit.pass ? 'audit-pass' : 'audit-fail'}>
        Audit: {audit.pass ? 'pass' : 'fail'}; owner match {audit.exactOwnerPass ? 'ok' : 'wrong'}, capacity {audit.capacityPass ? 'ok' : 'overflow'}
      </p>
      <p>
        Move the guard ladder out of lookup workspace and into guard workspace.
        That is the toy version of not hiding a 255-bit predicate ladder under a
        one-bit owner.
      </p>
    </article>
  );
}
