import { useMemo, useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { blockerLabel, blockerSummary } from '../content/blockerCopy';

type Blocker = {
  name: string;
  status: string;
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
  activeBlockers: Blocker[];
};

const formatInt = (value: number) => new Intl.NumberFormat('en-US').format(value);

export function BaselinePromotionLab({ projectData }: { projectData: ProjectData }) {
  const [closedBlockers, setClosedBlockers] = useState<Set<string>>(() => new Set());
  const [useGuardCorrected, setUseGuardCorrected] = useState(true);

  const promotion = useMemo(() => {
    const openBlockers = projectData.activeBlockers.filter((blocker) => !closedBlockers.has(blocker.name));
    const selected = useGuardCorrected
      ? projectData.guardCorrectedNoAliasCandidate
      : projectData.currentStrictCandidate;
    const guardIsCounted = useGuardCorrected;
    const pass = guardIsCounted && openBlockers.length === 0;
    return { selected, openBlockers, guardIsCounted, pass };
  }, [closedBlockers, projectData, useGuardCorrected]);

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
        <article className={promotion.openBlockers.length === 0 ? 'pass' : 'fail'}>
          <span>2. Close blockers</span>
          <strong>{promotion.openBlockers.length === 0 ? 'none open' : `${promotion.openBlockers.length} open`}</strong>
          <p>Macro expansion, modular cleanup, and capacity gates must be closed deliberately.</p>
        </article>
        <article className={promotion.pass ? 'pass' : 'fail'}>
          <span>3. Publish wording</span>
          <strong>{promotion.pass ? 'accepted baseline' : 'candidate only'}</strong>
          <p>The public claim level follows the weakest remaining gate.</p>
        </article>
      </div>
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
          <h4>Release blockers</h4>
          <div className="blocker-switches">
            {projectData.activeBlockers.map((blocker) => (
              <label key={blocker.name}>
                <input
                  aria-label={`Close ${blockerLabel(blocker.name)}`}
                  checked={closedBlockers.has(blocker.name)}
                  onChange={(event) => {
                    const checked = event.currentTarget.checked;
                    setClosedBlockers((current) => {
                      const next = new Set(current);
                      if (checked) next.add(blocker.name);
                      else next.delete(blocker.name);
                      return next;
                    });
                  }}
                  type="checkbox"
                />
                <span>
                  <strong>{blockerLabel(blocker.name)}</strong>
                  <em>{blockerSummary(blocker.name)}</em>
                </span>
              </label>
            ))}
          </div>
          <p>
            Open blockers: {promotion.openBlockers.length === 0
              ? 'none'
              : promotion.openBlockers.map((blocker) => blockerLabel(blocker.name)).join(', ')}
          </p>
        </article>
      </div>
      <p>
        This is the repo policy in miniature: a number can be interesting before
        it is publishable, but it becomes the accepted baseline only after the
        guard capacity, modular source-uncompute, and full primitive expansion
        gates are closed against the same executable artifact.
      </p>
    </section>
  );
}
