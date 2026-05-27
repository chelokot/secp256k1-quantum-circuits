import { useMemo, useState } from 'react';
import { BookOpen, CheckCircle2, Circle, Code2, GitBranch, Play, RotateCcw } from 'lucide-react';
import projectData from './generated/project-data.json';
import { lessons, glossary, quiz, type LessonId } from './content/course';
import { BaselineChart } from './components/BaselineChart';
import { BlochPlayground } from './components/BlochPlayground';
import { StateVectorLab } from './components/StateVectorLab';
import { StabilizerMagicLab } from './components/StabilizerMagicLab';
import { CircuitBuilder } from './components/CircuitBuilder';
import { SlotLiveness } from './components/SlotLiveness';
import { QuizPanel } from './components/QuizPanel';
import { PhaseEstimationLab } from './components/PhaseEstimationLab';
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

const formatInt = (value: number) => new Intl.NumberFormat('en-US').format(value);

export function App() {
  const [activeLessonId, setActiveLessonId] = useState<LessonId>('zero');
  const [completed, setCompleted] = useState<Set<LessonId>>(() => new Set());
  const activeLesson = lessons.find((lesson) => lesson.id === activeLessonId) ?? lessons[0];
  const completionPercent = Math.round((completed.size / lessons.length) * 100);
  const blockerNames = projectData.activeBlockers.map((blocker) => blocker.name.replaceAll('_', ' '));
  const currentIndex = lessons.findIndex((lesson) => lesson.id === activeLesson.id);
  const nextLesson = lessons[(currentIndex + 1) % lessons.length];

  const groupedLessons = useMemo(() => {
    return lessons.reduce<Record<string, typeof lessons>>((groups, lesson) => {
      groups[lesson.module] = [...(groups[lesson.module] ?? []), lesson];
      return groups;
    }, {});
  }, []);

  const markComplete = () => {
    setCompleted((previous) => new Set(previous).add(activeLesson.id));
  };

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
                    onClick={() => setActiveLessonId(lesson.id)}
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
        <header className="hero-panel">
          <div>
            <p className="eyebrow">{activeLesson.module}</p>
            <h2>{activeLesson.title}</h2>
            <p className="hero-copy">{activeLesson.intuition}</p>
          </div>
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
        </header>

        <section className="content-grid">
          <article className="concept-panel">
            <div className="panel-heading">
              <BookOpen size={20} />
              <h3>Idea first</h3>
            </div>
            <p>{activeLesson.mentalModel}</p>
            <h4>Why it matters here</h4>
            <p>{activeLesson.whyItMatters}</p>
            <div className="checkpoint">
              <CheckCircle2 size={18} />
              <span>{activeLesson.checkpoint}</span>
            </div>
            <div className="actions">
              <button className="primary-action" type="button" onClick={markComplete}>
                <CheckCircle2 size={18} />
                Mark understood
              </button>
              <button className="secondary-action" type="button" onClick={() => setActiveLessonId(nextLesson.id)}>
                <Play size={18} />
                Next concept
              </button>
            </div>
          </article>

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
        </section>

        <AttackPipelineLab />
        <DiscreteLogOracleLab />
        <PhaseKickbackLab />
        <WindowScaffoldLab projectData={projectData} />
        <CircuitStackMap projectData={projectData} />

        <section className="lab-grid" aria-label="Interactive labs">
          <BlochPlayground />
          <StateVectorLab />
          <StabilizerMagicLab />
          <PhaseEstimationLab />
          <CircuitBuilder />
          <QuantumDslLab />
          <CleanupPuzzleLab />
          <ToyCurveLab />
          <PointAddFormulaLab />
          <MultiplierGridLab />
          <ModularReductionLab />
          <QroamLab projectData={projectData} />
          <QroamTradeoffLab />
          <SlotLiveness projectData={projectData} />
          <EngineInvariantLab />
          <OwnerCapacityGame />
          <BaselineChart projectData={projectData} />
        </section>

        <CoordinateModelLab />
        <ReversibleOverwriteLab projectData={projectData} />
        <BaselineExplorer projectData={projectData} />
        <BaselineTradeoffLab projectData={projectData} />
        <ErrorCorrectionToyLab projectData={projectData} />
        <LogicalPhysicalBridgeLab projectData={projectData} />
        <MagicBudgetLab projectData={projectData} />
        <OptimizationMissionLab projectData={projectData} />
        <PointAddBoundaryDebugger projectData={projectData} />
        <MiniResourceEngineLab />
        <OpcodeLoweringLab />
        <ScheduleOptimizerLab />
        <AccumulatorLoweringLab projectData={projectData} />
        <AccumulatorScratchLifecycleLab projectData={projectData} />
        <BaselinePromotionLab projectData={projectData} />
        <ClaimAuditDrill projectData={projectData} />
        <ArtifactAtlasLab projectData={projectData} />
        <ConfidenceLadderLab projectData={projectData} />
        <ContributorMissionBoard projectData={projectData} />
        <ProofBoundaryLab projectData={projectData} />

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
      </section>
    </main>
  );
}
