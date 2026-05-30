import { useMemo, useState } from 'react';
import { Cpu } from 'lucide-react';

type ProjectData = {
  strictFormula: {
    field_bits: number;
    lookup_workspace_qubits: number;
    phase_qubits: number;
  };
  zeroLiftGuard: {
    current: {
      logical_qubits: number;
    };
    cleanLadder: {
      peak_predicate_workspace_bits: number;
    };
  };
  compilerParameters: {
    reusableChunkPolicy: {
      chunkBits: number;
    };
  };
};

type WireGroup = {
  wire: string;
  width: number;
  owner: string;
  live: string;
};

export function EngineInvariantLab({ projectData }: { projectData: ProjectData }) {
  const [includeHiddenScratch, setIncludeHiddenScratch] = useState(false);
  const [aliasGuardToLookup, setAliasGuardToLookup] = useState(false);

  const ownerCapacities = useMemo(() => ({
    tail_field_slot: projectData.strictFormula.field_bits,
    lookup_workspace: projectData.strictFormula.lookup_workspace_qubits,
    phase_shell: projectData.strictFormula.phase_qubits,
    tail_guard: projectData.zeroLiftGuard.current.logical_qubits,
    guard_workspace: projectData.zeroLiftGuard.cleanLadder.peak_predicate_workspace_bits,
  }), [projectData]);

  const audit = useMemo(() => {
    const rows: WireGroup[] = [
      {
        wire: `qx[0..${projectData.strictFormula.field_bits - 1}]`,
        width: projectData.strictFormula.field_bits,
        owner: 'tail_field_slot',
        live: 'tail rows 0-22',
      },
      {
        wire: `qchunk[0..${projectData.compilerParameters.reusableChunkPolicy.chunkBits - 1}]`,
        width: projectData.compilerParameters.reusableChunkPolicy.chunkBits,
        owner: 'lookup_workspace',
        live: 'qroam stream',
      },
      {
        wire: 'phase',
        width: projectData.strictFormula.phase_qubits,
        owner: 'phase_shell',
        live: 'semiclassical qft',
      },
      {
        wire: 'guard',
        width: projectData.zeroLiftGuard.current.logical_qubits,
        owner: 'tail_guard',
        live: 'zero-lift predicate bit',
      },
    ];

    if (aliasGuardToLookup) {
      rows.push({
        wire: `guard_ladder[0..${projectData.zeroLiftGuard.cleanLadder.peak_predicate_workspace_bits - 1}]`,
        width: projectData.zeroLiftGuard.cleanLadder.peak_predicate_workspace_bits,
        owner: 'lookup_workspace',
        live: 'clean guard ladder at peak row',
      });
    }

    if (includeHiddenScratch) {
      rows.push({
        wire: `scratch_tmp[0..${projectData.zeroLiftGuard.cleanLadder.peak_predicate_workspace_bits - 1}]`,
        width: projectData.zeroLiftGuard.cleanLadder.peak_predicate_workspace_bits,
        owner: 'unowned',
        live: 'hidden guard ladder',
      });
    }

    const ownerLoads = Object.entries(ownerCapacities).map(([owner, capacity]) => {
      const assigned = rows.filter((row) => row.owner === owner);
      const load = assigned.reduce((total, row) => total + row.width, 0);
      return {
        owner,
        capacity,
        load,
        formula: assigned.length === 0 ? '0' : assigned.map((row) => row.width).join(' + '),
        pass: load <= capacity,
      };
    });
    const unowned = rows.filter((row) => !(row.owner in ownerCapacities));
    const overflow = ownerLoads.filter((row) => !row.pass);
    return {
      rows,
      ownerLoads,
      pass: unowned.length === 0 && overflow.length === 0,
      unowned,
      overflow,
    };
  }, [aliasGuardToLookup, includeHiddenScratch, ownerCapacities, projectData]);

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
      <label className="toggle-row">
        <input checked={aliasGuardToLookup} onChange={(event) => setAliasGuardToLookup(event.currentTarget.checked)} type="checkbox" />
        Alias clean guard ladder into lookup workspace
      </label>
      <div className="owner-table" role="table" aria-label="Wire owner table">
        <div role="row"><strong>Wire</strong><strong>Owner</strong><strong>Width</strong><strong>Live interval</strong></div>
        {audit.rows.map((row) => (
          <div className={row.owner === 'unowned' || audit.overflow.some((owner) => owner.owner === row.owner) ? 'bad-owner' : ''} role="row" key={row.wire}>
            <span>{row.wire}</span>
            <span>{row.owner}</span>
            <span>{row.width}</span>
            <span>{row.live}</span>
          </div>
        ))}
      </div>
      <div className="owner-load-receipt">
        <h4>Owner load receipt</h4>
        {audit.ownerLoads.map((row) => (
          <article className={row.pass ? '' : 'bad-owner'} key={row.owner}>
            <span>{row.owner}</span>
            <strong>{row.formula} = {row.load}/{row.capacity}</strong>
          </article>
        ))}
      </div>
      <p className={audit.pass ? 'audit-pass' : 'audit-fail'}>
        Audit: {audit.pass ? 'pass' : 'fail'};
        {' '}owner assignment {audit.unowned.length === 0 ? 'ok' : `${audit.unowned.length} unowned group`},
        {' '}capacity {audit.overflow.length === 0 ? 'ok' : 'overflow'}
      </p>
      <p>
        Peak qubits must come from executable liveness, not from a hand-picked register list.
        Naming lookup workspace is insufficient unless the numeric owner load still fits.
      </p>
    </article>
  );
}
