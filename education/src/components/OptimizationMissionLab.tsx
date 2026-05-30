import { useMemo, useState } from 'react';
import * as d3 from 'd3';
import { Target } from 'lucide-react';

type CandidateRow = {
  name: string;
  logical_qubits: number;
  non_clifford: number;
  field_slots?: number;
  status: string;
  fits_logical_qubit_limit: boolean;
  fits_non_clifford_limit: boolean;
  blocker: string;
};

type ProjectData = {
  optimizationMission: {
    target: {
      logical_qubits_exclusive: number;
      non_clifford_exclusive: number;
    };
    status: string;
    candidateRows: CandidateRow[];
    sixSlotLookupTradeoff: {
      chunk_bits_budget: number;
      chunks_per_coordinate: number;
      qroam_streams: number;
      total_non_clifford_lower_bound: number;
    };
    nextRequiredBreakthrough: {
      primary: string;
      secondary: string;
      not_enough: string;
    };
  };
};

const formatInt = (value: number) => new Intl.NumberFormat('en-US').format(value);
const formatCompact = (value: number) => `${(value / 1_000_000).toFixed(2)}M`;
const formatSignedInt = (value: number) => `${value >= 0 ? '+' : '-'}${formatInt(Math.abs(value))}`;
const formatSignedCompact = (value: number) => `${value >= 0 ? '+' : '-'}${formatCompact(Math.abs(value))}`;
const readable = (value: string) => value.replaceAll('_', ' ');

const executableStatuses = new Set([
  'proven_current_strict_baseline',
]);

const allowedWording = (candidate: CandidateRow, executable: boolean) => {
  if (executable && candidate.fits_logical_qubit_limit && candidate.fits_non_clifford_limit) {
    return 'promoted candidate';
  }
  if (executable) {
    return 'strict executable row, not target hit';
  }
  if (candidate.fits_logical_qubit_limit && candidate.fits_non_clifford_limit) {
    return 'hypothesis until lowered';
  }
  if (!candidate.fits_non_clifford_limit) {
    return 'blocked tradeoff, not headline';
  }
  return 'numeric projection only';
};

export function OptimizationMissionLab({ projectData }: { projectData: ProjectData }) {
  const candidates = projectData.optimizationMission.candidateRows;
  const [selectedName, setSelectedName] = useState(candidates[0]?.name ?? '');
  const [requireExecutable, setRequireExecutable] = useState(true);
  const [requireBothTargets, setRequireBothTargets] = useState(true);
  const selected = candidates.find((row) => row.name === selectedName) ?? candidates[0];
  const target = projectData.optimizationMission.target;

  const maxQubits = d3.max(candidates, (row) => row.logical_qubits) ?? 1;
  const maxNonClifford = d3.max(candidates, (row) => row.non_clifford) ?? 1;
  const qubitScale = d3.scaleLinear([0, maxQubits], [6, 100]);
  const gateScale = d3.scaleLinear([0, maxNonClifford], [6, 100]);

  const audit = useMemo(() => {
    const executable = executableStatuses.has(selected.status);
    const targetPass = selected.fits_logical_qubit_limit && selected.fits_non_clifford_limit;
    const targetGate = requireBothTargets ? targetPass : selected.fits_logical_qubit_limit || selected.fits_non_clifford_limit;
    const qubitRoom = target.logical_qubits_exclusive - selected.logical_qubits;
    const nonCliffordRoom = target.non_clifford_exclusive - selected.non_clifford;
    const pass = (!requireExecutable || executable) && targetGate;
    const reasons = [
      requireExecutable && !executable ? 'not executable/promoted' : null,
      requireBothTargets && !selected.fits_logical_qubit_limit ? 'qubits miss target' : null,
      requireBothTargets && !selected.fits_non_clifford_limit ? 'non-Clifford misses target' : null,
    ].filter((reason): reason is string => reason !== null);
    const requiredEvidence = [
      !executable ? 'promote candidate into primitive/liveness engine' : null,
      !selected.fits_logical_qubit_limit ? `reduce ${formatInt(Math.abs(qubitRoom))} logical qubits` : null,
      !selected.fits_non_clifford_limit ? `recover ${formatCompact(Math.abs(nonCliffordRoom))} non-Clifford` : null,
    ].filter((reason): reason is string => reason !== null);
    const nextAction = requiredEvidence[0] ?? 'bind this row into proof inputs and docs';
    return {
      executable,
      targetPass,
      pass,
      reasons,
      qubitRoom,
      nonCliffordRoom,
      requiredEvidence,
      nextAction,
      wording: allowedWording(selected, executable),
    };
  }, [requireBothTargets, requireExecutable, selected, target]);

  return (
    <section className="wide-panel" data-testid="optimization-mission-lab">
      <div className="panel-heading">
        <Target size={20} />
        <h3>Optimization mission</h3>
      </div>
      <p>
        Target: below {formatInt(target.logical_qubits_exclusive)} logical qubits
        and below {formatCompact(target.non_clifford_exclusive)} non-Clifford.
      </p>

      <div className="mission-controls">
        <label>
          <span>Candidate</span>
          <select
            aria-label="Optimization candidate"
            value={selected.name}
            onChange={(event) => setSelectedName(event.currentTarget.value)}
          >
            {candidates.map((candidate) => (
              <option key={candidate.name} value={candidate.name}>{readable(candidate.name)}</option>
            ))}
          </select>
        </label>
        <label className="toggle-row">
          <input
            aria-label="Require executable promoted candidate"
            checked={requireExecutable}
            onChange={(event) => setRequireExecutable(event.currentTarget.checked)}
            type="checkbox"
          />
          <span>require executable/promoted contract</span>
        </label>
        <label className="toggle-row">
          <input
            aria-label="Require both qubit and non-Clifford targets"
            checked={requireBothTargets}
            onChange={(event) => setRequireBothTargets(event.currentTarget.checked)}
            type="checkbox"
          />
          <span>require both resource targets</span>
        </label>
      </div>

      <div className="mission-grid">
        <article>
          <h4>{readable(selected.name)}</h4>
          <dl className="metric-pair">
            <div>
              <dt>Logical qubits</dt>
              <dd>{formatInt(selected.logical_qubits)}</dd>
            </div>
            <div>
              <dt>Non-Clifford</dt>
              <dd>{formatCompact(selected.non_clifford)}</dd>
            </div>
            <div>
              <dt>Field slots</dt>
              <dd>{selected.field_slots ?? 'n/a'}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{readable(selected.status)}</dd>
            </div>
          </dl>
          <p className={audit.pass ? 'audit-pass' : 'audit-fail'}>
            Mission audit: {audit.pass ? 'pass' : 'blocked'}
          </p>
          <p>{audit.reasons.length === 0 ? selected.blocker : audit.reasons.join(', ')}</p>
        </article>

        <article>
          <h4>Candidate landscape</h4>
          <div className="mission-bars">
            {candidates.map((candidate) => (
              <button
                className={candidate.name === selected.name ? 'selected' : ''}
                key={candidate.name}
                onClick={() => setSelectedName(candidate.name)}
                type="button"
              >
                <strong>{readable(candidate.name)}</strong>
                <span className="qubit-bar" style={{ width: `${qubitScale(candidate.logical_qubits)}%` }}>{formatInt(candidate.logical_qubits)}q</span>
                <span className="gate-bar" style={{ width: `${gateScale(candidate.non_clifford)}%` }}>{formatCompact(candidate.non_clifford)}</span>
              </button>
            ))}
          </div>
        </article>
      </div>

      <section className="mission-evidence-receipt" aria-label="Optimization evidence receipt">
        <h4>Evidence receipt for selected row</h4>
        <article className={selected.fits_logical_qubit_limit ? 'pass' : 'fail'}>
          <span>Qubit target</span>
          <strong>{formatInt(selected.logical_qubits)} / &lt;{formatInt(target.logical_qubits_exclusive)}</strong>
          <p>{selected.fits_logical_qubit_limit ? 'fits the qubit gate' : 'still above the qubit gate'}</p>
        </article>
        <article className={selected.fits_non_clifford_limit ? 'pass' : 'fail'}>
          <span>Non-Clifford target</span>
          <strong>{formatCompact(selected.non_clifford)} / &lt;{formatCompact(target.non_clifford_exclusive)}</strong>
          <p>{selected.fits_non_clifford_limit ? 'fits the gate budget' : 'spends too much magic work'}</p>
        </article>
        <article className={audit.executable ? 'pass' : 'fail'}>
          <span>Executable contract</span>
          <strong>{audit.executable ? 'promoted path exists' : 'not promoted'}</strong>
          <p>{readable(selected.status)}</p>
        </article>
        <article className="fail">
          <span>Blocking reason</span>
          <strong>{readable(selected.blocker)}</strong>
          <p>The blocker decides what evidence a patch must add before wording can improve.</p>
        </article>
        <article className={audit.pass ? 'pass' : 'fail'}>
          <span>Allowed wording</span>
          <strong>{audit.wording}</strong>
          <p>Do not promote the row beyond the weakest failed evidence column.</p>
        </article>
      </section>

      <section className="generated-mission-packet" aria-label="Generated optimization patch packet">
        <h4>Generated patch packet</h4>
        <div className="generated-mission-grid">
          <article className={audit.qubitRoom >= 0 ? 'pass' : 'fail'}>
            <span>Qubit room</span>
            <strong>{formatSignedInt(audit.qubitRoom)}</strong>
            <p>Positive room means the row is below the logical-qubit gate.</p>
          </article>
          <article className={audit.nonCliffordRoom >= 0 ? 'pass' : 'fail'}>
            <span>Non-Clifford room</span>
            <strong>{formatSignedCompact(audit.nonCliffordRoom)}</strong>
            <p>Positive room means the row stays under the magic-work budget.</p>
          </article>
          <article className={audit.requiredEvidence.length === 0 ? 'pass' : 'fail'}>
            <span>Next required evidence</span>
            <strong>{audit.nextAction}</strong>
            <p>{audit.requiredEvidence.length === 0 ? selected.blocker : audit.requiredEvidence.join('; ')}</p>
          </article>
          <article>
            <span>Public wording ceiling</span>
            <strong>{audit.wording}</strong>
            <p>The row cannot be described more strongly than this without new evidence.</p>
          </article>
        </div>
      </section>

      <div className="mission-grid">
        <article>
          <h4>Six-slot lookup squeeze</h4>
          <p>
            Reducing lookup workspace enough for six projective slots needs
            {` ${projectData.optimizationMission.sixSlotLookupTradeoff.qroam_streams} `}
            QROAM streams and pushes the lower bound to
            {` ${formatCompact(projectData.optimizationMission.sixSlotLookupTradeoff.total_non_clifford_lower_bound)} `}
            non-Clifford.
          </p>
          <p>
            Chunk budget: {projectData.optimizationMission.sixSlotLookupTradeoff.chunk_bits_budget} bits,
            {` ${projectData.optimizationMission.sixSlotLookupTradeoff.chunks_per_coordinate} `}
            chunks per coordinate.
          </p>
        </article>

        <article>
          <h4>Next breakthrough</h4>
          <p><strong>Primary:</strong> {projectData.optimizationMission.nextRequiredBreakthrough.primary}</p>
          <p><strong>Secondary:</strong> {projectData.optimizationMission.nextRequiredBreakthrough.secondary}</p>
          <p><strong>Not enough:</strong> {projectData.optimizationMission.nextRequiredBreakthrough.not_enough}</p>
        </article>
      </div>
    </section>
  );
}
