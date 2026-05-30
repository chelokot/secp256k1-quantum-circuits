import { useMemo, useState } from 'react';
import { ClipboardList } from 'lucide-react';
import { blockerLabel, blockerSummary } from '../content/blockerCopy';

type ProjectData = {
  activeBlockers: Array<{ name: string; status: string }>;
};

type Mission = {
  id: string;
  title: string;
  outcome: string;
  object: string;
  evidenceGate: string;
  blockerName: string;
  readyClaim: string;
  checks: string[];
};

const missions: Mission[] = [
  {
    id: 'claim-trace',
    title: 'Trace a resource claim',
    outcome: 'Turn a number in docs into artifact-backed status language.',
    object: 'one public resource sentence',
    evidenceGate: 'source artifact, status field, blockers, and claim classification agree',
    blockerName: 'publication_gate_allows_resource_headline',
    readyClaim: 'This sentence can be rewritten to match the checked artifact status.',
    checks: ['find source artifact', 'read status field', 'list blockers', 'classify claim'],
  },
  {
    id: 'semantic-case',
    title: 'Add a semantic edge case',
    outcome: 'Extend point-add confidence without changing resource claims.',
    object: 'one point-add boundary case',
    evidenceGate: 'expected output and same executable leaf are covered by tests',
    blockerName: 'single_authoritative_primitive_stream',
    readyClaim: 'This edge case strengthens semantic confidence without changing the headline.',
    checks: ['name boundary case', 'build expected output', 'bind same executable leaf', 'add e2e or unit coverage'],
  },
  {
    id: 'primitive-lowering',
    title: 'Promote a primitive lowering row',
    outcome: 'Move one macro obligation closer to a counted primitive stream.',
    object: 'one modular accumulator lowering obligation',
    evidenceGate: 'source controls, target wire, owner capacity, and cleanup/output ownership are all explicit',
    blockerName: 'modular_accumulator_source_uncompute_not_promoted',
    readyClaim: 'This row can be reviewed as a promoted primitive-lowering step, not as a new headline.',
    checks: ['identify source controls', 'name target wire', 'assign counted owner', 'prove cleanup or output ownership'],
  },
  {
    id: 'schedule-optimization',
    title: 'Shorten a live interval',
    outcome: 'Reduce peak qubits through a semantic-preserving schedule change.',
    object: 'one live interval in the primitive schedule',
    evidenceGate: 'baseline peak, earlier cleanup, recomputed liveness, and unchanged edge cases are recorded',
    blockerName: 'zero_lift_guard_capacity_not_promoted',
    readyClaim: 'This schedule patch can claim a local liveness improvement after recomputation.',
    checks: ['record baseline peak', 'move cleanup earlier', 'recompute liveness', 'prove edge cases unchanged'],
  },
  {
    id: 'release-hygiene',
    title: 'Prepare a publishable result',
    outcome: 'Keep docs, proof inputs, public values, and artifacts aligned.',
    object: 'one public release boundary',
    evidenceGate: 'docs, proof freshness, engine checks, and stale-number rejection all pass',
    blockerName: 'publication_gate_allows_resource_headline',
    readyClaim: 'This release patch can claim publication hygiene, not a stronger physical baseline.',
    checks: ['generate docs from artifacts', 'verify proof freshness', 'run fast engine checks', 'reject stale numbers'],
  },
];

export function ContributorMissionBoard({ projectData }: { projectData: ProjectData }) {
  const [selectedMissionId, setSelectedMissionId] = useState('primitive-lowering');
  const [checkedItems, setCheckedItems] = useState<Set<string>>(() => new Set());
  const selectedMission = missions.find((mission) => mission.id === selectedMissionId) ?? missions[0];
  const selectedBlocker = projectData.activeBlockers.find((blocker) => blocker.name === selectedMission.blockerName)
    ?? projectData.activeBlockers[0];

  const progress = useMemo(() => {
    const done = selectedMission.checks.filter((check) => checkedItems.has(check)).length;
    return {
      done,
      total: selectedMission.checks.length,
      ready: done === selectedMission.checks.length,
    };
  }, [checkedItems, selectedMission]);

  return (
    <section className="wide-panel" data-testid="contributor-mission-board">
      <div className="panel-heading">
        <ClipboardList size={20} />
        <h3>Contributor mission board</h3>
      </div>
      <p>
        A useful patch behaves like a reviewable claim: it names the object, says what
        evidence changed, and keeps the public wording at the level that evidence proves.
      </p>

      <div className="mission-board-grid">
        <article>
          <h4>Mission</h4>
          <div className="mission-board-list">
            {missions.map((mission) => (
              <button
                className={mission.id === selectedMission.id ? 'selected' : ''}
                key={mission.id}
                onClick={() => {
                  setSelectedMissionId(mission.id);
                  setCheckedItems(new Set());
                }}
                type="button"
              >
                <strong>{mission.title}</strong>
                <span>{mission.outcome}</span>
              </button>
            ))}
          </div>
        </article>

        <article>
          <h4>{selectedMission.title}</h4>
          <p>{selectedMission.outcome}</p>
          <div className="mission-checklist">
            {selectedMission.checks.map((check) => (
              <label key={check}>
                <input
                  aria-label={`Complete mission item ${check}`}
                  checked={checkedItems.has(check)}
                  onChange={(event) => {
                    const checked = event.currentTarget.checked;
                    setCheckedItems((current) => {
                      const next = new Set(current);
                      if (checked) next.add(check);
                      else next.delete(check);
                      return next;
                    });
                  }}
                  type="checkbox"
                />
                <span>{check}</span>
              </label>
            ))}
          </div>
          <p className={progress.ready ? 'audit-pass' : 'audit-fail'}>
            Mission ready: {progress.ready ? 'yes' : 'no'} ({progress.done}/{progress.total})
          </p>
        </article>
      </div>

      <section className="mission-packet-preview" aria-label="Generated contributor patch packet">
        <h4>Generated patch packet</h4>
        <article>
          <span>Patch object</span>
          <strong>{selectedMission.object}</strong>
          <p>A reviewable patch starts by naming the one thing it changes.</p>
        </article>
        <article>
          <span>Evidence gate</span>
          <strong>{selectedMission.evidenceGate}</strong>
          <p>{progress.done}/{progress.total} checklist items complete.</p>
        </article>
        <article>
          <span>Blocker to respect</span>
          <strong>{selectedBlocker ? blockerLabel(selectedBlocker.name) : 'No matching blocker'}</strong>
          <p>{selectedBlocker ? blockerSummary(selectedBlocker.name) : 'No open blocker is mapped to this mission.'}</p>
        </article>
        <article className={progress.ready ? 'pass' : 'fail'}>
          <span>Allowed wording</span>
          <strong>{progress.ready ? selectedMission.readyClaim : 'Not reviewable yet'}</strong>
          <p>{progress.ready ? 'The packet has enough local evidence for review.' : 'Finish the evidence checklist before making a PR claim.'}</p>
        </article>
      </section>

      <div className="mission-blocker-strip">
        <strong>Open blockers to respect</strong>
        <ul>
          {projectData.activeBlockers.map((blocker) => (
            <li key={blocker.name}>
              <span>{blockerLabel(blocker.name)}</span>
              <em>{blockerSummary(blocker.name)}</em>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
