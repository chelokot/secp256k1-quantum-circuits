import { useMemo, useState } from 'react';
import { ClipboardCheck } from 'lucide-react';
import { blockerLabel } from '../content/blockerCopy';

type ProjectData = {
  activeBlockers: Array<{ name: string }>;
  currentStrictCandidate: {
    logical_qubits: number;
    non_clifford: number;
  };
  guardCorrectedNoAliasCandidate: {
    logical_qubits: number;
    non_clifford: number;
  };
};

type ClaimStatus = 'accepted' | 'candidate' | 'consequence' | 'reference' | 'rejected';

type Claim = {
  id: string;
  title: string;
  text: string;
  correctStatus: ClaimStatus;
  evidence: string[];
  explanation: string;
};

const formatInt = (value: number) => new Intl.NumberFormat('en-US').format(value);

function buildClaims(projectData: ProjectData): Claim[] {
  const strict = projectData.currentStrictCandidate;
  const guard = projectData.guardCorrectedNoAliasCandidate;
  const blockerText = projectData.activeBlockers.map((blocker) => blockerLabel(blocker.name)).join(', ');

  return [
    {
      id: 'accepted-strict',
      title: 'Strict candidate as accepted baseline',
      text: `${formatInt(strict.non_clifford)} / ${formatInt(strict.logical_qubits)} is the accepted Clifford-complete physical baseline.`,
      correctStatus: 'rejected',
      evidence: ['same executable primitive stream', 'all physical blockers closed', 'proof input bound to selected contract'],
      explanation: `Reject as accepted baseline while blockers remain open: ${blockerText}. It may be a strict candidate, not a final physical baseline.`,
    },
    {
      id: 'guard-consequence',
      title: 'Guard-corrected no-alias result',
      text: `${formatInt(guard.non_clifford)} / ${formatInt(guard.logical_qubits)} is a conservative guard-corrected consequence, but not promoted.`,
      correctStatus: 'consequence',
      evidence: ['derivation from strict candidate', 'clean-ladder guard capacity counted', 'not promoted into global primitive stream'],
      explanation: 'Classify this as a consequence: it is useful and conservative, but the artifact says the owner model is not promoted.',
    },
    {
      id: 'google-line',
      title: 'Google comparison row',
      text: 'The 1,200q / 90M row is an external comparison baseline, not this repository’s accepted result.',
      correctStatus: 'reference',
      evidence: ['external source label', 'kept separate from repo claims', 'not used as repo proof artifact'],
      explanation: 'Classify external rows as references. They are valuable for comparison, but they do not become repo evidence.',
    },
    {
      id: 'green-proof',
      title: 'Green proof verifier',
      text: 'A valid Groth16 verification alone proves the current physical baseline is ready to publish.',
      correctStatus: 'rejected',
      evidence: ['proof freshness', 'public values match current input', 'physical macro boundary closed'],
      explanation: 'Reject the claim. A verifier proves one bound statement; freshness, corpus scope, public values, and physical boundary still matter.',
    },
  ];
}

export function ClaimAuditDrill({ projectData }: { projectData: ProjectData }) {
  const claims = useMemo(() => buildClaims(projectData), [projectData]);
  const [claimId, setClaimId] = useState(claims[0].id);
  const [selectedStatus, setSelectedStatus] = useState<ClaimStatus>('accepted');
  const [checkedEvidence, setCheckedEvidence] = useState<Set<string>>(() => new Set());
  const claim = claims.find((item) => item.id === claimId) ?? claims[0];

  const statusPass = selectedStatus === claim.correctStatus;
  const evidencePass = claim.evidence.every((item) => checkedEvidence.has(item));
  const auditPass = statusPass && evidencePass;

  return (
    <section className="wide-panel" data-testid="claim-audit-drill">
      <div className="panel-heading">
        <ClipboardCheck size={20} />
        <h3>Claim audit drill</h3>
      </div>
      <p>
        Contributor skill is not only finding a lower number. It is classifying the claim correctly
        and demanding the exact evidence needed before the repo presents it as a result.
      </p>

      <div className="claim-drill-grid">
        <article>
          <label className="assignment-control">
            <span>Claim to review</span>
            <select
              aria-label="Claim to review"
              value={claim.id}
              onChange={(event) => {
                setClaimId(event.currentTarget.value);
                setSelectedStatus('accepted');
                setCheckedEvidence(new Set());
              }}
            >
              {claims.map((item) => (
                <option key={item.id} value={item.id}>{item.title}</option>
              ))}
            </select>
          </label>
          <blockquote>{claim.text}</blockquote>
          <label className="assignment-control">
            <span>Your classification</span>
            <select
              aria-label="Claim classification"
              value={selectedStatus}
              onChange={(event) => setSelectedStatus(event.currentTarget.value as ClaimStatus)}
            >
              <option value="accepted">accepted</option>
              <option value="candidate">candidate</option>
              <option value="consequence">consequence</option>
              <option value="reference">reference</option>
              <option value="rejected">rejected</option>
            </select>
          </label>
          <p className={statusPass ? 'audit-pass' : 'audit-fail'}>
            Classification: {statusPass ? 'correct' : 'wrong'}
          </p>
        </article>

        <article>
          <h4>Evidence checklist</h4>
          <div className="claim-evidence-list">
            {claim.evidence.map((item) => (
              <label key={item}>
                <input
                  aria-label={`Require evidence ${item}`}
                  checked={checkedEvidence.has(item)}
                  onChange={(event) => {
                    const checked = event.currentTarget.checked;
                    setCheckedEvidence((current) => {
                      const next = new Set(current);
                      if (checked) next.add(item);
                      else next.delete(item);
                      return next;
                    });
                  }}
                  type="checkbox"
                />
                <span>{item}</span>
              </label>
            ))}
          </div>
          <p className={auditPass ? 'audit-pass' : 'audit-fail'}>
            Claim audit: {auditPass ? 'pass' : 'fail'}
          </p>
          <p>{claim.explanation}</p>
        </article>
      </div>
    </section>
  );
}
