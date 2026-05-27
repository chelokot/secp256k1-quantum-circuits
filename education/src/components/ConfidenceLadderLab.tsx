import { useMemo, useState } from 'react';
import { ListChecks } from 'lucide-react';

type ProjectData = {
  pointAddBoundary: {
    streamedLookupTailLeaf: {
      pass: number;
      total: number;
    };
  };
  acceptedBaselineGate: {
    status: string;
    rows: Array<{ name: string; pass: boolean }>;
  };
  proofPublication: {
    publicationReady: boolean;
    allCurrent: boolean;
  };
  engineCompletion: {
    cliffordCompleteGoalAchieved: boolean;
  };
};

type EvidenceKey =
  | 'idea'
  | 'semantic'
  | 'primitive'
  | 'ownerCapacity'
  | 'proofFreshness'
  | 'acceptedGate';

type LadderRow = {
  key: EvidenceKey;
  title: string;
  allowedClaim: string;
  missingClaim: string;
};

const ladderRows: LadderRow[] = [
  {
    key: 'idea',
    title: 'Modeled idea',
    allowedClaim: 'Hypothesis or optimization direction.',
    missingClaim: 'No resource headline yet.',
  },
  {
    key: 'semantic',
    title: 'Semantic boundary',
    allowedClaim: 'Candidate leaf behavior passes the checked point-add boundary.',
    missingClaim: 'No physical resource claim yet.',
  },
  {
    key: 'primitive',
    title: 'Single primitive stream',
    allowedClaim: 'Resource totals are generated from the executable stream.',
    missingClaim: 'Do not call it Clifford-complete.',
  },
  {
    key: 'ownerCapacity',
    title: 'Owner capacity',
    allowedClaim: 'Every live wire has exactly one counted owner with enough capacity.',
    missingClaim: 'Qubit count can still hide capacity bugs.',
  },
  {
    key: 'proofFreshness',
    title: 'Fresh proof wrapper',
    allowedClaim: 'Compressed/Groth16 artifacts bind the current selected input.',
    missingClaim: 'No publication claim if proof fixtures are stale.',
  },
  {
    key: 'acceptedGate',
    title: 'Accepted baseline gate',
    allowedClaim: 'Accepted Clifford-complete physical baseline.',
    missingClaim: 'Keep the number as candidate, consequence, or reference.',
  },
];

const readable = (value: string) => value.replaceAll('_', ' ');

function defaultEvidence(projectData: ProjectData): Set<EvidenceKey> {
  const evidence = new Set<EvidenceKey>(['idea']);
  if (projectData.pointAddBoundary.streamedLookupTailLeaf.pass === projectData.pointAddBoundary.streamedLookupTailLeaf.total) {
    evidence.add('semantic');
  }
  if (projectData.engineCompletion.cliffordCompleteGoalAchieved) {
    evidence.add('primitive');
  }
  if (projectData.acceptedBaselineGate.rows.every((row) => row.pass)) {
    evidence.add('ownerCapacity');
    evidence.add('acceptedGate');
  }
  if (projectData.proofPublication.allCurrent && projectData.proofPublication.publicationReady) {
    evidence.add('proofFreshness');
  }
  return evidence;
}

function highestClaim(evidence: Set<EvidenceKey>) {
  let lastPassed = ladderRows[0];
  for (const row of ladderRows) {
    if (!evidence.has(row.key)) return lastPassed;
    lastPassed = row;
  }
  return lastPassed;
}

export function ConfidenceLadderLab({ projectData }: { projectData: ProjectData }) {
  const [evidence, setEvidence] = useState<Set<EvidenceKey>>(() => defaultEvidence(projectData));
  const [claimText, setClaimText] = useState('accepted baseline');

  const audit = useMemo(() => {
    const highest = highestClaim(evidence);
    const acceptedReady = highest.key === 'acceptedGate';
    const claimIsTooStrong = claimText === 'accepted baseline' && !acceptedReady;
    const missingRows = ladderRows.filter((row) => !evidence.has(row.key));
    return { highest, acceptedReady, claimIsTooStrong, missingRows };
  }, [claimText, evidence]);

  return (
    <section className="wide-panel" data-testid="confidence-ladder-lab">
      <div className="panel-heading">
        <ListChecks size={20} />
        <h3>Result confidence ladder</h3>
      </div>
      <p>
        A reviewer should climb claim levels one by one. Passing a lower rung is useful, but it
        does not authorize wording from a higher rung.
      </p>
      <div className="claim-verdict-strip">
        <article>
          <span>Current wording</span>
          <strong>{claimText}</strong>
          <p>{audit.claimIsTooStrong ? 'This wording is ahead of the available evidence.' : 'This wording matches the selected evidence.'}</p>
        </article>
        <article>
          <span>Highest justified rung</span>
          <strong>{audit.highest.title}</strong>
          <p>{audit.highest.allowedClaim}</p>
        </article>
        <article>
          <span>Next missing gate</span>
          <strong>{audit.missingRows[0]?.title ?? 'none'}</strong>
          <p>{audit.missingRows[0]?.missingClaim ?? 'All evidence rungs are selected.'}</p>
        </article>
      </div>

      <div className="confidence-grid">
        <article>
          <h4>Evidence rungs</h4>
          <div className="confidence-ladder">
            {ladderRows.map((row, index) => {
              const checked = evidence.has(row.key);
              return (
                <label className={checked ? 'ladder-row passed' : 'ladder-row'} key={row.key}>
                  <input
                    aria-label={`Evidence ${row.title}`}
                    checked={checked}
                    onChange={(event) => {
                      const isChecked = event.currentTarget.checked;
                      setEvidence((current) => {
                        const next = new Set(current);
                        if (isChecked) next.add(row.key);
                        else next.delete(row.key);
                        return next;
                      });
                    }}
                    type="checkbox"
                  />
                  <span>{index + 1}</span>
                  <strong>{row.title}</strong>
                  <em>{checked ? row.allowedClaim : row.missingClaim}</em>
                </label>
              );
            })}
          </div>
        </article>

        <article>
          <h4>Claim wording audit</h4>
          <label className="assignment-control">
            <span>Claim you want to say</span>
            <select
              aria-label="Claim wording"
              value={claimText}
              onChange={(event) => setClaimText(event.currentTarget.value)}
            >
              <option value="candidate">strict candidate</option>
              <option value="consequence">guard-corrected consequence</option>
              <option value="proof wrapper">fresh proof wrapper</option>
              <option value="accepted baseline">accepted baseline</option>
            </select>
          </label>
          <dl className="confidence-summary">
            <div>
              <dt>Highest justified rung</dt>
              <dd>{audit.highest.title}</dd>
            </div>
            <div>
              <dt>Allowed wording</dt>
              <dd>{audit.highest.allowedClaim}</dd>
            </div>
            <div>
              <dt>Current repo baseline gate</dt>
              <dd>{readable(projectData.acceptedBaselineGate.status)}</dd>
            </div>
          </dl>
          <p className={audit.claimIsTooStrong ? 'audit-fail' : 'audit-pass'}>
            Wording audit: {audit.claimIsTooStrong ? 'too strong' : 'allowed for selected evidence'}
          </p>
          <p>
            Missing rungs: {audit.missingRows.length === 0 ? 'none' : audit.missingRows.map((row) => row.title).join(', ')}
          </p>
        </article>
      </div>
    </section>
  );
}
