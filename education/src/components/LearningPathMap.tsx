import { Compass } from 'lucide-react';
import type { CourseLesson, LessonId } from '../content/course';

type LearningStage = {
  id: string;
  title: string;
  description: string;
  lessonIds: LessonId[];
};

type Props = {
  activeLessonId: LessonId;
  completedLessonIds: Set<LessonId>;
  lessons: CourseLesson[];
  onSelectLesson: (lessonId: LessonId) => void;
};

const stages: LearningStage[] = [
  {
    id: 'substrate',
    title: '1. Quantum substrate',
    description: 'Build the mental model for amplitudes, gates, reversibility, and fault-tolerant cost.',
    lessonIds: ['zero', 'qubit', 'gates', 'clifford', 'logic-physical', 'phase-estimation'],
  },
  {
    id: 'attack',
    title: '2. Attack algorithm',
    description: 'Connect phase estimation to ECDLP, windowed point-add calls, and lookup-fed curve arithmetic.',
    lessonIds: ['ecdlp', 'coordinates', 'lookup-qroam'],
  },
  {
    id: 'engine',
    title: '3. Circuit engine',
    description: 'Move from attractive formulas to primitive rows, live intervals, owners, and cleanup obligations.',
    lessonIds: ['netlists', 'programming', 'cleanup', 'modular-lowering', 'owner-capacity', 'resource-engine', 'mini-engine'],
  },
  {
    id: 'review',
    title: '4. Audit and contribution',
    description: 'Classify claims, respect blockers, and turn understanding into useful repo patches.',
    lessonIds: ['optimization', 'point-add-boundary', 'contribution', 'zkp-boundary', 'repo-baselines'],
  },
];

const contributorGate: LessonId[] = [
  'qubit',
  'gates',
  'phase-estimation',
  'ecdlp',
  'coordinates',
  'lookup-qroam',
  'cleanup',
  'modular-lowering',
  'owner-capacity',
  'mini-engine',
  'point-add-boundary',
  'contribution',
];

export function LearningPathMap({ activeLessonId, completedLessonIds, lessons, onSelectLesson }: Props) {
  const lessonById = new Map(lessons.map((lesson) => [lesson.id, lesson]));
  const nextMissing = contributorGate.find((lessonId) => !completedLessonIds.has(lessonId));
  const contributorReady = nextMissing === undefined;

  return (
    <section className="wide-panel" data-testid="learning-path-map">
      <div className="panel-heading">
        <Compass size={20} />
        <h3>Zero-to-contributor learning path</h3>
      </div>
      <p>
        Use this as the spine of the course. Each stage turns a previous idea into
        a stricter object: state evolution, then attack oracle, then primitive
        liveness, then review-ready contribution.
      </p>

      <div className="path-stage-grid">
        {stages.map((stage) => {
          const doneCount = stage.lessonIds.filter((lessonId) => completedLessonIds.has(lessonId)).length;
          return (
            <article key={stage.id}>
              <header>
                <strong>{stage.title}</strong>
                <span>{doneCount}/{stage.lessonIds.length}</span>
              </header>
              <p>{stage.description}</p>
              <div className="path-lesson-list">
                {stage.lessonIds.map((lessonId) => {
                  const lesson = lessonById.get(lessonId);
                  if (!lesson) return null;
                  const completed = completedLessonIds.has(lessonId);
                  const active = activeLessonId === lessonId;
                  return (
                    <button
                      className={active ? 'active' : completed ? 'complete' : ''}
                      key={lessonId}
                      onClick={() => onSelectLesson(lessonId)}
                      type="button"
                    >
                      <span>{lesson.title}</span>
                      <strong>{completed ? 'done' : active ? 'now' : 'open'}</strong>
                    </button>
                  );
                })}
              </div>
            </article>
          );
        })}
      </div>

      <div className="readiness-strip">
        <div>
          <span>Contributor readiness</span>
          <strong>{contributorReady ? 'ready' : 'not ready'}</strong>
        </div>
        <div>
          <span>Next missing prerequisite</span>
          <strong>{nextMissing ? lessonById.get(nextMissing)?.title : 'all gate lessons complete'}</strong>
        </div>
        <button
          disabled={nextMissing === undefined}
          onClick={() => {
            if (nextMissing) onSelectLesson(nextMissing);
          }}
          type="button"
        >
          Jump to next missing contributor step
        </button>
      </div>
    </section>
  );
}
