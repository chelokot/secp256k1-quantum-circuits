import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, ArrowRight, BookOpen, CheckCircle2, Circle, Code2, GitBranch, Play, RotateCcw } from 'lucide-react';
import projectData from './generated/project-data.json';
import { lessons, glossary, quiz, type LessonId } from './content/course';
import { BaselineChart } from './components/BaselineChart';
import { BlochPlayground } from './components/BlochPlayground';
import { StateVectorLab } from './components/StateVectorLab';
import { QubitAmplitudeBridgeLab } from './components/QubitAmplitudeBridgeLab';
import { StabilizerMagicLab } from './components/StabilizerMagicLab';
import { CircuitBuilder } from './components/CircuitBuilder';
import { SlotLiveness } from './components/SlotLiveness';
import { QuizPanel } from './components/QuizPanel';
import { PhaseEstimationLab } from './components/PhaseEstimationLab';
import { FourierLensLab } from './components/FourierLensLab';
import { ToyCurveLab } from './components/ToyCurveLab';
import { CoordinateModelLab } from './components/CoordinateModelLab';
import { ReversibleOverwriteLab } from './components/ReversibleOverwriteLab';
import { QroamLab } from './components/QroamLab';
import { EngineInvariantLab } from './components/EngineInvariantLab';
import { QuantumDslLab } from './components/QuantumDslLab';
import { OpcodeLoweringLab } from './components/OpcodeLoweringLab';
import { AttackPipelineLab } from './components/AttackPipelineLab';
import { DiscreteLogOracleLab } from './components/DiscreteLogOracleLab';
import { PhaseKickbackLab } from './components/PhaseKickbackLab';
import { WindowScaffoldLab } from './components/WindowScaffoldLab';
import { CircuitStackMap } from './components/CircuitStackMap';
import { OracleResourceComposerLab } from './components/OracleResourceComposerLab';
import { PointAddFormulaLab } from './components/PointAddFormulaLab';
import { ModularReductionLab } from './components/ModularReductionLab';
import { QroamTradeoffLab } from './components/QroamTradeoffLab';
import { BaselineExplorer } from './components/BaselineExplorer';
import { BaselineTradeoffLab } from './components/BaselineTradeoffLab';
import { LogicalPhysicalBridgeLab } from './components/LogicalPhysicalBridgeLab';
import { ErrorCorrectionToyLab } from './components/ErrorCorrectionToyLab';
import { MagicBudgetLab } from './components/MagicBudgetLab';
import { CleanupPuzzleLab } from './components/CleanupPuzzleLab';
import { MultiplierGridLab } from './components/MultiplierGridLab';
import { OwnerCapacityGame } from './components/OwnerCapacityGame';
import { BaselinePromotionLab } from './components/BaselinePromotionLab';
import { ProofBoundaryLab } from './components/ProofBoundaryLab';
import { AccumulatorLoweringLab } from './components/AccumulatorLoweringLab';
import { AccumulatorScratchLifecycleLab } from './components/AccumulatorScratchLifecycleLab';
import { MiniResourceEngineLab } from './components/MiniResourceEngineLab';
import { ScheduleOptimizerLab } from './components/ScheduleOptimizerLab';
import { ClaimAuditDrill } from './components/ClaimAuditDrill';
import { ContributorMissionBoard } from './components/ContributorMissionBoard';
import { ArtifactAtlasLab } from './components/ArtifactAtlasLab';
import { ConfidenceLadderLab } from './components/ConfidenceLadderLab';
import { OptimizationMissionLab } from './components/OptimizationMissionLab';
import { PointAddBoundaryDebugger } from './components/PointAddBoundaryDebugger';
import { LearningPathMap } from './components/LearningPathMap';
import { CourseCoverageAuditLab } from './components/CourseCoverageAuditLab';

const formatInt = (value: number) => new Intl.NumberFormat('en-US').format(value);
const lessonIds = new Set(lessons.map((lesson) => lesson.id));

function lessonFromHash() {
  const hash = window.location.hash.replace('#', '');
  return lessonIds.has(hash as LessonId) ? hash as LessonId : 'zero';
}

export function App() {
  const [activeLessonId, setActiveLessonId] = useState<LessonId>(() => lessonFromHash());
  const [completed, setCompleted] = useState<Set<LessonId>>(() => new Set());
  const activeLesson = lessons.find((lesson) => lesson.id === activeLessonId) ?? lessons[0];
  const completionPercent = Math.round((completed.size / lessons.length) * 100);
  const blockerNames = projectData.activeBlockers.map((blocker) => blocker.name.replaceAll('_', ' '));
  const currentIndex = lessons.findIndex((lesson) => lesson.id === activeLesson.id);
  const previousLesson = currentIndex > 0 ? lessons[currentIndex - 1] : null;
  const nextLesson = lessons[(currentIndex + 1) % lessons.length];
  const showResourceStatus = ['optimization', 'zkp-boundary', 'repo-baselines'].includes(activeLesson.id);
  const showRepoContract = ['resource-engine', 'optimization', 'point-add-boundary', 'contribution', 'zkp-boundary', 'repo-baselines'].includes(activeLesson.id);
  const showReviewPanels = activeLesson.id === 'repo-baselines';

  const groupedLessons = useMemo(() => {
    return lessons.reduce<Record<string, typeof lessons>>((groups, lesson) => {
      groups[lesson.module] = [...(groups[lesson.module] ?? []), lesson];
      return groups;
    }, {});
  }, []);

  const markComplete = () => {
    setCompleted((previous) => new Set(previous).add(activeLesson.id));
  };

  const selectLesson = (lessonId: LessonId) => {
    setActiveLessonId(lessonId);
    window.history.replaceState(null, '', `#${lessonId}`);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  useEffect(() => {
    const syncHash = () => setActiveLessonId(lessonFromHash());
    window.addEventListener('hashchange', syncHash);
    return () => window.removeEventListener('hashchange', syncHash);
  }, []);

  const activeLabs = (() => {
    switch (activeLesson.id) {
      case 'zero':
        return (
          <>
            <LearningPathMap
              activeLessonId={activeLessonId}
              completedLessonIds={completed}
              lessons={lessons}
              onSelectLesson={selectLesson}
            />
          </>
        );
      case 'qubit':
        return (
          <section className="lab-grid" aria-label="Interactive labs">
            <QubitAmplitudeBridgeLab />
            <BlochPlayground />
            <StateVectorLab />
          </section>
        );
      case 'gates':
        return (
          <section className="lab-grid" aria-label="Interactive labs">
            <CircuitBuilder />
            <QuantumDslLab />
            <CleanupPuzzleLab />
          </section>
        );
      case 'clifford':
        return (
          <section className="lab-grid" aria-label="Interactive labs">
            <StabilizerMagicLab />
            <MagicBudgetLab projectData={projectData} />
          </section>
        );
      case 'logic-physical':
        return (
          <>
            <LogicalPhysicalBridgeLab projectData={projectData} />
            <ErrorCorrectionToyLab projectData={projectData} />
          </>
        );
      case 'phase-estimation':
        return (
          <section className="lab-grid" aria-label="Interactive labs">
            <PhaseEstimationLab />
            <FourierLensLab />
          </section>
        );
      case 'netlists':
        return (
          <>
            <CircuitStackMap projectData={projectData} />
            <MiniResourceEngineLab />
            <OpcodeLoweringLab />
            <ScheduleOptimizerLab />
          </>
        );
      case 'ecdlp':
        return (
          <>
            <AttackPipelineLab />
            <DiscreteLogOracleLab />
            <PhaseKickbackLab />
            <ToyCurveLab />
            <WindowScaffoldLab projectData={projectData} />
            <OracleResourceComposerLab projectData={projectData} />
          </>
        );
      case 'coordinates':
        return (
          <>
            <CoordinateModelLab />
            <ReversibleOverwriteLab projectData={projectData} />
            <PointAddFormulaLab />
            <PointAddBoundaryDebugger projectData={projectData} />
          </>
        );
      case 'lookup-qroam':
        return (
          <section className="lab-grid" aria-label="Interactive labs">
            <QroamLab projectData={projectData} />
            <QroamTradeoffLab />
          </section>
        );
      case 'programming':
        return (
          <section className="lab-grid" aria-label="Interactive labs">
            <CircuitBuilder />
            <QuantumDslLab />
            <OpcodeLoweringLab />
          </section>
        );
      case 'cleanup':
        return (
          <>
            <CleanupPuzzleLab />
            <AccumulatorScratchLifecycleLab projectData={projectData} />
          </>
        );
      case 'modular-lowering':
        return (
          <>
            <MultiplierGridLab />
            <ModularReductionLab />
            <AccumulatorLoweringLab projectData={projectData} />
            <AccumulatorScratchLifecycleLab projectData={projectData} />
          </>
        );
      case 'owner-capacity':
        return (
          <section className="lab-grid" aria-label="Interactive labs">
            <SlotLiveness projectData={projectData} />
            <EngineInvariantLab />
            <OwnerCapacityGame />
          </section>
        );
      case 'resource-engine':
        return (
          <>
            <CircuitStackMap projectData={projectData} />
            <MiniResourceEngineLab />
            <ScheduleOptimizerLab />
          </>
        );
      case 'mini-engine':
        return (
          <>
            <MiniResourceEngineLab />
            <OpcodeLoweringLab />
          </>
        );
      case 'optimization':
        return (
          <>
            <OptimizationMissionLab projectData={projectData} />
            <BaselineTradeoffLab projectData={projectData} />
          </>
        );
      case 'point-add-boundary':
        return (
          <>
            <PointAddBoundaryDebugger projectData={projectData} />
            <ArtifactAtlasLab projectData={projectData} />
          </>
        );
      case 'contribution':
        return (
          <>
            <ContributorMissionBoard projectData={projectData} />
            <ClaimAuditDrill projectData={projectData} />
            <CourseCoverageAuditLab lessonCount={lessons.length} quizCount={quiz.length} />
          </>
        );
      case 'zkp-boundary':
        return (
          <>
            <ProofBoundaryLab projectData={projectData} />
            <ConfidenceLadderLab projectData={projectData} />
            <ArtifactAtlasLab projectData={projectData} />
          </>
        );
      case 'repo-baselines':
        return (
          <>
            <BaselineExplorer projectData={projectData} />
            <BaselineTradeoffLab projectData={projectData} />
            <BaselinePromotionLab projectData={projectData} />
            <BaselineChart projectData={projectData} />
          </>
        );
    }
  })();

  return (
    <main className="app-shell">
      <aside className="course-nav" aria-label="Course navigation">
        <div className="brand">
          <div className="brand-mark"><GitBranch size={22} /></div>
          <div>
            <p className="eyebrow">secp256k1 open audit</p>
            <h1>Quantum Circuit Lab</h1>
          </div>
        </div>
        <div className="progress-block" aria-label="Course progress">
          <div className="progress-label">
            <span>{completionPercent}% complete</span>
            <span>{completed.size}/{lessons.length}</span>
          </div>
          <div className="progress-track"><div style={{ width: `${completionPercent}%` }} /></div>
        </div>
        <nav className="lesson-list">
          {Object.entries(groupedLessons).map(([module, moduleLessons]) => (
            <section key={module}>
              <p className="module-title">{module}</p>
              {moduleLessons.map((lesson) => {
                const Icon = lesson.icon;
                const isActive = lesson.id === activeLesson.id;
                const isDone = completed.has(lesson.id);
                return (
                  <button
                    key={lesson.id}
                    className={isActive ? 'lesson-link active' : 'lesson-link'}
                    onClick={() => selectLesson(lesson.id)}
                    type="button"
                    aria-current={isActive ? 'page' : undefined}
                  >
                    <Icon size={18} />
                    <span>{lesson.title}</span>
                    {isDone ? <CheckCircle2 size={16} /> : <Circle size={16} />}
                  </button>
                );
              })}
            </section>
          ))}
        </nav>
      </aside>

      <section className="lesson-workspace">
        <header className={showResourceStatus ? 'hero-panel' : 'hero-panel no-status'}>
          <div>
            <p className="eyebrow">{activeLesson.module}</p>
            <h2>{activeLesson.title}</h2>
            <p className="hero-copy">{activeLesson.intuition}</p>
          </div>
          {showResourceStatus ? (
            <div className="baseline-strip" aria-label="Current repository resource status">
              <div>
                <span>Accepted baseline</span>
                <strong>none yet</strong>
              </div>
              <div>
                <span>Strict candidate</span>
                <strong>{formatInt(projectData.currentStrictCandidate.logical_qubits)}q</strong>
              </div>
              <div>
                <span>Guard-corrected</span>
                <strong>{formatInt(projectData.guardCorrectedNoAliasCandidate.logical_qubits)}q</strong>
              </div>
              <div>
                <span>Non-Clifford</span>
                <strong>{formatInt(projectData.currentStrictCandidate.non_clifford)}</strong>
              </div>
            </div>
          ) : null}
        </header>

        <nav className="lesson-pager" aria-label="Lesson pager" data-testid="lesson-pager">
          <button
            className="secondary-action"
            disabled={previousLesson === null}
            onClick={() => previousLesson && selectLesson(previousLesson.id)}
            type="button"
          >
            <ArrowLeft size={18} />
            Previous
          </button>
          <div>
            <span>{activeLesson.module}</span>
            <strong>Lesson {currentIndex + 1} of {lessons.length}</strong>
          </div>
          <button className="primary-action" type="button" onClick={() => selectLesson(nextLesson.id)}>
            Next
            <ArrowRight size={18} />
          </button>
        </nav>

        <section className={showRepoContract ? 'content-grid' : 'content-grid learning-grid'}>
          <article className="concept-panel">
            <div className="panel-heading">
              <BookOpen size={20} />
              <h3>Core idea</h3>
            </div>
            <section className="lesson-primer" aria-label="Start here">
              <span>Start here</span>
              <p>{activeLesson.mentalModel}</p>
            </section>
            {activeLesson.deepDive ? (
              <ol className="lesson-step-list">
                {activeLesson.deepDive.map((paragraph, index) => (
                  <li key={paragraph}>
                    <span>{index + 1}</span>
                    <p>{paragraph}</p>
                  </li>
                ))}
              </ol>
            ) : null}
            {activeLesson.coreIdeas ? (
              <div className="core-idea-list">
                {activeLesson.coreIdeas.map((idea) => (
                  <span key={idea}>{idea}</span>
                ))}
              </div>
            ) : null}
            <h4>Why it matters here</h4>
            <p>{activeLesson.whyItMatters}</p>
            {activeLesson.practicePrompt ? (
              <>
                <h4>Try this page</h4>
                <p>{activeLesson.practicePrompt}</p>
              </>
            ) : null}
            <div className="checkpoint">
              <CheckCircle2 size={18} />
              <span>{activeLesson.checkpoint}</span>
            </div>
            <div className="actions">
              <button className="primary-action" type="button" onClick={markComplete}>
                <CheckCircle2 size={18} />
                Mark understood
              </button>
              <button className="secondary-action" type="button" onClick={() => selectLesson(nextLesson.id)}>
                <Play size={18} />
                Next concept
              </button>
            </div>
          </article>

          {showRepoContract ? (
            <article className="concept-panel">
              <div className="panel-heading">
                <Code2 size={20} />
                <h3>Current repo contract</h3>
              </div>
              <p>
                The educational app reads checked artifacts through <code>scripts/sync-project-data.mjs</code>.
                The UI treats resource numbers as contract states, not as marketing copy.
              </p>
              <ul className="blocker-list">
                {blockerNames.map((name) => (
                  <li key={name}>{name}</li>
                ))}
              </ul>
            </article>
          ) : (
            <section className="lesson-labs inline" aria-label={`${activeLesson.title} labs`}>
              {activeLabs}
            </section>
          )}
        </section>

        {showRepoContract ? (
          <section className="lesson-labs" aria-label={`${activeLesson.title} labs`}>
            {activeLabs}
          </section>
        ) : null}

        {showReviewPanels ? (
          <>
            <section className="wide-panel">
              <div className="panel-heading">
                <RotateCcw size={20} />
                <h3>Vocabulary spine</h3>
              </div>
              <div className="glossary-grid">
                {glossary.map(([term, definition]) => (
                  <div className="glossary-item" key={term}>
                    <strong>{term}</strong>
                    <span>{definition}</span>
                  </div>
                ))}
              </div>
            </section>

            <QuizPanel quiz={quiz} />
          </>
        ) : null}
      </section>
    </main>
  );
}
