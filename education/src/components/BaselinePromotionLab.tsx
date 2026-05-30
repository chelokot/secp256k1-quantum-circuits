import { useMemo, useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { blockerLabel, blockerSummary } from '../content/blockerCopy';

type GateRow = {
  name: string;
  status: string;
  pass: boolean;
  evidence: string;
  required_to_close: string;
};

type ProjectData = {
  currentStrictCandidate: {
    non_clifford: number;
    logical_qubits: number;
  };
  guardCorrectedNoAliasCandidate: {
    non_clifford: number;
    logical_qubits: number;
  };
  acceptedBaselineGate: {
    status: string;
    decision: string;
    candidate_under_review: string;
    candidate_under_review_logical_qubits: number;
    candidate_under_review_non_clifford: number;
    policy: string;
    rows: GateRow[];
  };
};

const formatInt = (value: number) => new Intl.NumberFormat('en-US').format(value);

export function BaselinePromotionLab({ projectData }: { projectData: ProjectData }) {
  const [closedGateRows, setClosedGateRows] = useState<Set<string>>(() => new Set());
  const [useGuardCorrected, setUseGuardCorrected] = useState(true);

  const promotion = useMemo(() => {
    const openGateRows = projectData.acceptedBaselineGate.rows.filter((row) => !row.pass && !closedGateRows.has(row.name));
    const selected = useGuardCorrected
      ? projectData.guardCorrectedNoAliasCandidate
      : projectData.currentStrictCandidate;
    const guardIsCounted = useGuardCorrected;
    const gateRowsClosed = openGateRows.length === 0;
    const pass = guardIsCounted && gateRowsClosed;
    return { selected, openGateRows, gateRowsClosed, guardIsCounted, pass };
  }, [closedGateRows, projectData, useGuardCorrected]);

  return (
    <section className="wide-panel" data-testid="baseline-promotion-lab">
      <div className="panel-heading">
        <ShieldCheck size={20} />
        <h3>Accepted-baseline gate</h3>
      </div>
      <div className="promotion-steps">
        <article className={promotion.guardIsCounted ? 'pass' : 'fail'}>
          <span>1. Count guard capacity</span>
          <strong>{promotion.guardIsCounted ? 'included' : 'missing'}</strong>
          <p>The headline cannot ignore clean-ladder guard space.</p>
        </article>
        <article className={promotion.gateRowsClosed ? 'pass' : 'fail'}>
          <span>2. Close artifact gate rows</span>
          <strong>{promotion.gateRowsClosed ? 'none open' : `${promotion.openGateRows.length} open`}</strong>
          <p>The accepted-baseline gate is the checked artifact, not a handpicked blocker subset.</p>
        </article>
        <article className={promotion.pass ? 'pass' : 'fail'}>
          <span>3. Publish wording</span>
          <strong>{promotion.pass ? 'accepted baseline' : 'candidate only'}</strong>
          <p>The public claim level follows the weakest remaining gate.</p>
        </article>
      </div>

      <section className="baseline-gate-receipt" aria-label="Accepted baseline gate receipt">
        <h4>Accepted-baseline gate receipt</h4>
        <article>
          <span>Gate status</span>
          <strong>{projectData.acceptedBaselineGate.status}</strong>
          <p>{projectData.acceptedBaselineGate.decision.replaceAll('_', ' ')}</p>
        </article>
        <article>
          <span>Candidate under review</span>
          <strong>{formatInt(projectData.acceptedBaselineGate.candidate_under_review_logical_qubits)}q / {formatInt(projectData.acceptedBaselineGate.candidate_under_review_non_clifford)}</strong>
          <p>{projectData.acceptedBaselineGate.candidate_under_review.replaceAll('_', ' ')}</p>
        </article>
        <article>
          <span>Policy</span>
          <strong>all {projectData.acceptedBaselineGate.rows.length} gate rows must pass</strong>
          <p>{projectData.acceptedBaselineGate.policy}</p>
        </article>
      </section>

      <div className="promotion-grid">
        <article>
          <h4>Candidate being audited</h4>
          <label className="toggle-row">
            <input
              aria-label="Use guard-corrected qubit count"
              checked={useGuardCorrected}
              onChange={(event) => setUseGuardCorrected(event.currentTarget.checked)}
              type="checkbox"
            />
            <span>count clean-ladder guard capacity</span>
          </label>
          <dl className="metric-pair">
            <div>
              <dt>Logical qubits</dt>
              <dd>{formatInt(promotion.selected.logical_qubits)}</dd>
            </div>
            <div>
              <dt>Non-Clifford</dt>
              <dd>{formatInt(promotion.selected.non_clifford)}</dd>
            </div>
          </dl>
          <p className={promotion.pass ? 'audit-pass' : 'audit-fail'}>
            Promotion audit: {promotion.pass ? 'accepted-baseline ready' : 'blocked'}
          </p>
        </article>

        <article>
          <h4>Artifact gate rows</h4>
          <div className="blocker-switches">
            {projectData.acceptedBaselineGate.rows.map((row) => {
              const closed = row.pass || closedGateRows.has(row.name);
              return (
                <label key={row.name}>
                  <input
                    aria-label={`Close ${blockerLabel(row.name)}`}
                    checked={closed}
                    disabled={row.pass}
                    onChange={(event) => {
                      const checked = event.currentTarget.checked;
                      setClosedGateRows((current) => {
                        const next = new Set(current);
                        if (checked) next.add(row.name);
                        else next.delete(row.name);
                        return next;
                      });
                    }}
                    type="checkbox"
                  />
                  <span>
                    <strong>{blockerLabel(row.name)}</strong>
                    <em>{blockerSummary(row.name)}</em>
                    <em>Evidence: {row.evidence}</em>
                  </span>
                </label>
              );
            })}
          </div>
          <p>
            Open gate rows: {promotion.openGateRows.length === 0
              ? 'none'
              : promotion.openGateRows.map((row) => blockerLabel(row.name)).join(', ')}
          </p>
        </article>
      </div>
      <div className="baseline-gate-row-detail">
        {promotion.openGateRows.length === 0 ? (
          <article className="pass">
            <strong>All simulated gate rows closed</strong>
            <p>The lab can now show what an accepted-baseline-ready state would look like, but the repo artifact remains the authority.</p>
          </article>
        ) : (
          promotion.openGateRows.map((row) => (
            <article className="fail" key={row.name}>
              <strong>{blockerLabel(row.name)}</strong>
              <p>{row.required_to_close}</p>
            </article>
          ))
        )}
      </div>
      <p>
        This is the repo policy in miniature: a number can be interesting before
        it is publishable, but it becomes the accepted baseline only after the
        checked accepted-baseline gate rows are closed against the same executable
        artifact.
      </p>
    </section>
  );
}
