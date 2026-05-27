import { useMemo, useState } from 'react';
import { ClipboardList } from 'lucide-react';

type ProjectData = {
  activeBlockers: Array<{ name: string; status: string }>;
};

type Mission = {
  id: string;
  title: string;
  outcome: string;
  checks: string[];
};

const missions: Mission[] = [
  {
    id: 'claim-trace',
    title: 'Trace a resource claim',
    outcome: 'Turn a number in docs into artifact-backed status language.',
    checks: ['find source artifact', 'read status field', 'list blockers', 'classify claim'],
  },
  {
    id: 'semantic-case',
    title: 'Add a semantic edge case',
    outcome: 'Extend point-add confidence without changing resource claims.',
    checks: ['name boundary case', 'build expected output', 'bind same executable leaf', 'add e2e or unit coverage'],
  },
  {
    id: 'primitive-lowering',
    title: 'Promote a primitive lowering row',
    outcome: 'Move one macro obligation closer to a counted primitive stream.',
    checks: ['identify source controls', 'name target wire', 'assign counted owner', 'prove cleanup or output ownership'],
  },
  {
    id: 'schedule-optimization',
    title: 'Shorten a live interval',
    outcome: 'Reduce peak qubits through a semantic-preserving schedule change.',
    checks: ['record baseline peak', 'move cleanup earlier', 'recompute liveness', 'prove edge cases unchanged'],
  },
  {
    id: 'release-hygiene',
    title: 'Prepare a publishable result',
    outcome: 'Keep docs, proof inputs, public values, and artifacts aligned.',
    checks: ['generate docs from artifacts', 'verify proof freshness', 'run fast engine checks', 'reject stale numbers'],
  },
];

const readable = (value: string) => value.replaceAll('_', ' ');

export function ContributorMissionBoard({ projectData }: { projectData: ProjectData }) {
  const [selectedMissionId, setSelectedMissionId] = useState('primitive-lowering');
  const [checkedItems, setCheckedItems] = useState<Set<string>>(() => new Set());
  const selectedMission = missions.find((mission) => mission.id === selectedMissionId) ?? missions[0];

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
        The course target is useful contribution. Pick a mission, then check the evidence habits
        needed before a patch or review comment should be trusted.
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

      <div className="mission-blocker-strip">
        <strong>Current repo blockers to respect</strong>
        {projectData.activeBlockers.map((blocker) => (
          <span key={blocker.name}>{readable(blocker.name)}</span>
        ))}
      </div>
    </section>
  );
}
