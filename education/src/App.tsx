import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { ArrowLeft, ArrowRight, BookOpen, CheckCircle2, Circle, Code2, GitBranch, ListChecks, RotateCcw } from 'lucide-react';
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
import { ProjectProofMap } from './components/ProjectProofMap';
import { MathText } from './components/MathText';

const formatInt = (value: number) => new Intl.NumberFormat('en-US').format(value);
const lessonIds = new Set(lessons.map((lesson) => lesson.id));

function lessonFromHash() {
  const hash = window.location.hash.replace('#', '');
  return lessonIds.has(hash as LessonId) ? hash as LessonId : 'zero';
}

type LabRouteItem = {
  name: string;
  goal: string;
};

type LabItem = LabRouteItem & {
  element: ReactNode;
};

const slugify = (value: string) => value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
const progressStorageKey = 'secp256k1-education-completed-lessons-v1';
const lessonIdSet = new Set<LessonId>(lessons.map((lesson) => lesson.id));

function loadCompletedLessons() {
  const stored = window.localStorage.getItem(progressStorageKey);
  if (stored === null) return new Set<LessonId>();
  const parsed = JSON.parse(stored) as LessonId[];
  return new Set(parsed.filter((lessonId) => lessonIdSet.has(lessonId)));
}

const labRoutes: Partial<Record<LessonId, LabRouteItem[]>> = {
  qubit: [
    { name: 'Phase-to-probability bridge', goal: 'Change only relative angle and see when it becomes measurable.' },
    { name: 'Qubit steering', goal: 'Apply named one-qubit gates as steering moves before measurement.' },
    { name: 'Two-qubit state vector', goal: 'Run a tiny two-wire state to see superposition and entanglement.' },
  ],
  'phase-estimation': [
    { name: 'Phase estimation lens', goal: 'Move the hidden phase and watch the likely bit label move with it.' },
    { name: 'Fourier lens', goal: 'Test why the matching output label makes phase arrows align.' },
  ],
  gates: [
    { name: 'Primitive netlist toy', goal: 'See rows, touched wires, and non-Clifford cost.' },
    { name: 'Quantum DSL', goal: 'Write valid rows and make invalid opcodes fail loudly.' },
    { name: 'Cleanup puzzle', goal: 'Prove compute, use, and uncompute as one lifecycle.' },
  ],
  netlists: [
    { name: 'Circuit stack map', goal: 'See where a resource claim can drift away from the tested circuit.' },
    { name: 'Mini resource engine', goal: 'Derive peak qubits from rows, live intervals, owners, and cleanup.' },
    { name: 'Opcode lowering', goal: 'Expand one abstract opcode into primitive counted rows.' },
    { name: 'Schedule optimizer', goal: 'Move cleanup earlier and watch peak liveness change.' },
  ],
  ecdlp: [
    { name: 'Whole attack map', goal: 'Orient the public key, quantum registers, controlled adds, and readout.' },
    { name: 'Discrete-log oracle toy', goal: 'Change d and watch the hidden period relation move.' },
    { name: 'Phase kickback', goal: 'See oracle output disappear while its phase imprint stays.' },
    { name: 'Toy curve group', goal: 'Ground the abstract oracle in concrete point multiples.' },
    { name: 'Windowed scaffold', goal: 'Connect retained windows to repeated point-add leaves.' },
    { name: 'Resource composer', goal: 'Check why gates add over leaves while qubits are peak workspace.' },
  ],
  coordinates: [
    { name: 'Coordinate model', goal: 'Compare affine and projective slot pressure.' },
    { name: 'Overwrite lab', goal: 'Test when in-place updates are reversible permutations.' },
    { name: 'Formula microscope', goal: 'Step through ordinary and lookup-infinity point-add behavior.' },
    { name: 'Boundary debugger', goal: 'Separate random hot-path tests from edge-case coverage.' },
  ],
  'lookup-qroam': [
    { name: 'QROAM selection', goal: 'Separate address controls, selected target lane, owner, and cleanup.' },
    { name: 'QROAMClean tradeoff', goal: 'Increase K and watch gate savings require more counted workspace.' },
  ],
  'modular-lowering': [
    { name: 'Partial-product grid', goal: 'See why a multiply becomes many temporary bit products.' },
    { name: 'Modular reduction', goal: 'Follow high-column folds back into field range.' },
    { name: 'Accumulator lowering', goal: 'Inspect promoted vs unpromoted row obligations.' },
    { name: 'Scratch lifecycle', goal: 'Track consume and source-uncompute requirements.' },
  ],
  'owner-capacity': [
    { name: 'Slot liveness', goal: 'Reconstruct peak field-slot pressure and guard capacity.' },
    { name: 'Invariant lab', goal: 'Inject hidden scratch and watch the no-free-wire audit fail.' },
    { name: 'Capacity game', goal: 'Assign owners until numeric load fits capacity.' },
  ],
  'mini-engine': [
    { name: 'Mini resource engine', goal: 'Derive peak qubits from rows, owners, and cleanup.' },
    { name: 'Opcode lowering', goal: 'Expand one abstract opcode into primitive counted rows.' },
  ],
  'resource-engine': [
    { name: 'Circuit stack map', goal: 'Connect algorithm layers to one executable resource stream.' },
    { name: 'Mini resource engine', goal: 'Derive peak qubits from executable liveness instead of a register list.' },
    { name: 'Schedule optimizer', goal: 'Shorten live intervals without changing semantics.' },
  ],
  optimization: [
    { name: 'Optimization mission', goal: 'Compare candidates against qubit, gate, semantic, and promotion gates.' },
    { name: 'Baseline tradeoff', goal: 'Keep external comparison rows separate from repo claims.' },
  ],
  'zkp-boundary': [
    { name: 'ZKP boundary', goal: 'Close freshness, macro-boundary, and proof verification gates.' },
    { name: 'Confidence ladder', goal: 'Match claim wording to the strongest proved rung.' },
    { name: 'Artifact atlas', goal: 'Map checked paths to what they prove and do not prove.' },
  ],
  'repo-baselines': [
    { name: 'Baseline explorer', goal: 'Read each row with its source and claim status.' },
    { name: 'Tradeoff landscape', goal: 'Compare qubits and non-Clifford without merging incompatible rows.' },
    { name: 'Promotion audit', goal: 'Close blockers deliberately before saying accepted baseline.' },
    { name: 'Baseline chart', goal: 'Use the visual comparison only after status is understood.' },
  ],
};

const checkpointQuestions: Partial<Record<LessonId, string>> = {
  zero: 'What chain must the repo connect before a resource number is meaningful?',
  qubit: 'Why can two states with the same direct measurement chances behave differently after a gate?',
  gates: 'Why is a scratch wire not free in a quantum circuit?',
  'phase-estimation': 'What does phase estimation read out, and what creates the expensive phase pattern here?',
  netlists: 'Why is a primitive netlist stronger evidence than a manually chosen register list?',
  ecdlp: 'What is hidden in Q = dG, and which circuit operation dominates the cost?',
  coordinates: 'Why does one extra secp256k1 field slot change the qubit count so much?',
  'lookup-qroam': 'What has to be counted besides the lookup address bits?',
  'mini-engine': 'Which three checks make a peak-qubit count believable?',
  'zkp-boundary': 'Why can a valid proof still be too weak for a headline claim?',
  'repo-baselines': 'When is a candidate allowed to become the accepted baseline?',
};

export function App() {
  const [activeLessonId, setActiveLessonId] = useState<LessonId>(() => lessonFromHash());
  const [completed, setCompleted] = useState<Set<LessonId>>(() => loadCompletedLessons());
  const [focusedLabByLesson, setFocusedLabByLesson] = useState<Partial<Record<LessonId, number>>>({});
  const [showAllLabsByLesson, setShowAllLabsByLesson] = useState<Partial<Record<LessonId, boolean>>>({});
  const [revealedCheckpointByLesson, setRevealedCheckpointByLesson] = useState<Partial<Record<LessonId, boolean>>>({});
  const [selectedVocabByLesson, setSelectedVocabByLesson] = useState<Partial<Record<LessonId, string>>>({});
  const [showFullCourseIndex, setShowFullCourseIndex] = useState(false);
  const activeLesson = lessons.find((lesson) => lesson.id === activeLessonId) ?? lessons[0];
  const blockerNames = projectData.activeBlockers.map((blocker) => blocker.name.replaceAll('_', ' '));
  const currentIndex = lessons.findIndex((lesson) => lesson.id === activeLesson.id);
  const previousLesson = currentIndex > 0 ? lessons[currentIndex - 1] : null;
  const nextLesson = currentIndex < lessons.length - 1 ? lessons[currentIndex + 1] : null;
  const showResourceStatus = ['optimization', 'zkp-boundary', 'repo-baselines'].includes(activeLesson.id);
  const showRepoContract = ['resource-engine', 'optimization', 'point-add-boundary', 'contribution', 'zkp-boundary', 'repo-baselines'].includes(activeLesson.id);
  const showReviewPanels = activeLesson.id === 'repo-baselines';
  const checkpointQuestion = checkpointQuestions[activeLesson.id] ?? 'What exact claim does this page let you make, and what evidence supports it?';
  const checkpointRevealed = revealedCheckpointByLesson[activeLesson.id] ?? false;
  const labRoute = labRoutes[activeLesson.id] ?? [];
  const glossaryByTerm = useMemo(() => new Map(glossary.map(([term, definition]) => [term, definition])), []);
  const pageGlossary = (activeLesson.glossaryTerms ?? []).map((term) => ({
    term,
    definition: glossaryByTerm.get(term) ?? '',
  }));
  const selectedVocab = pageGlossary.find(({ term }) => term === selectedVocabByLesson[activeLesson.id]) ?? pageGlossary[0] ?? null;

  const groupedLessons = useMemo(() => {
    return lessons.reduce<Record<string, typeof lessons>>((groups, lesson) => {
      groups[lesson.module] = [...(groups[lesson.module] ?? []), lesson];
      return groups;
    }, {});
  }, []);
  const moduleNames = Object.keys(groupedLessons);
  const activeModuleIndex = moduleNames.indexOf(activeLesson.module);
  const navigationModules = showFullCourseIndex
    ? moduleNames
    : moduleNames.filter((_, index) => Math.abs(index - activeModuleIndex) <= 1);

  const completeAndContinue = () => {
    setCompleted((previous) => new Set(previous).add(activeLesson.id));
    if (nextLesson !== null) selectLesson(nextLesson.id);
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

  useEffect(() => {
    window.localStorage.setItem(progressStorageKey, JSON.stringify([...completed]));
  }, [completed]);

  const activeLabItems: LabItem[] = (() => {
    const labItem = (index: number, fallbackName: string, element: ReactNode): LabItem => {
      const routeItem = labRoute[index] ?? {
        name: fallbackName,
        goal: 'Use this lab, then compare the output with the page checkpoint.',
      };
      return { ...routeItem, element };
    };

    switch (activeLesson.id) {
      case 'zero':
        return [
          labItem(0, 'What has to be proved', <ProjectProofMap />),
          labItem(1, 'Learning path map',
            <LearningPathMap
              activeLessonId={activeLessonId}
              completedLessonIds={completed}
              lessons={lessons}
              onSelectLesson={selectLesson}
            />
          ),
        ];
      case 'qubit':
        return [
          labItem(0, 'Phase-to-probability bridge', <QubitAmplitudeBridgeLab />),
          labItem(1, 'Qubit steering', <BlochPlayground />),
          labItem(2, 'Two-qubit state vector', <StateVectorLab />),
        ];
      case 'gates':
        return [
          labItem(0, 'Primitive netlist toy', <CircuitBuilder />),
          labItem(1, 'Quantum DSL', <QuantumDslLab />),
          labItem(2, 'Cleanup puzzle', <CleanupPuzzleLab />),
        ];
      case 'clifford':
        return [
          labItem(0, 'Stabilizer vs magic wheel', <StabilizerMagicLab />),
          labItem(1, 'Magic budget', <MagicBudgetLab projectData={projectData} />),
        ];
      case 'logic-physical':
        return [
          labItem(0, 'Logical-to-physical bridge', <LogicalPhysicalBridgeLab projectData={projectData} />),
          labItem(1, 'Error-correction toy', <ErrorCorrectionToyLab projectData={projectData} />),
        ];
      case 'phase-estimation':
        return [
          labItem(0, 'Phase estimation lens', <PhaseEstimationLab />),
          labItem(1, 'Fourier lens', <FourierLensLab />),
        ];
      case 'netlists':
        return [
          labItem(0, 'Circuit stack map', <CircuitStackMap projectData={projectData} />),
          labItem(1, 'Mini resource engine', <MiniResourceEngineLab />),
          labItem(2, 'Opcode lowering', <OpcodeLoweringLab />),
          labItem(3, 'Schedule optimizer', <ScheduleOptimizerLab />),
        ];
      case 'ecdlp':
        return [
          labItem(0, 'Whole attack map', <AttackPipelineLab />),
          labItem(1, 'Discrete-log oracle toy', <DiscreteLogOracleLab />),
          labItem(2, 'Phase kickback', <PhaseKickbackLab />),
          labItem(3, 'Toy curve group', <ToyCurveLab />),
          labItem(4, 'Windowed scaffold', <WindowScaffoldLab projectData={projectData} />),
          labItem(5, 'Resource composer', <OracleResourceComposerLab projectData={projectData} />),
        ];
      case 'coordinates':
        return [
          labItem(0, 'Coordinate model', <CoordinateModelLab />),
          labItem(1, 'Overwrite lab', <ReversibleOverwriteLab projectData={projectData} />),
          labItem(2, 'Formula microscope', <PointAddFormulaLab />),
          labItem(3, 'Boundary debugger', <PointAddBoundaryDebugger projectData={projectData} />),
        ];
      case 'lookup-qroam':
        return [
          labItem(0, 'QROAM selection', <QroamLab projectData={projectData} />),
          labItem(1, 'QROAMClean tradeoff', <QroamTradeoffLab />),
        ];
      case 'programming':
        return [
          labItem(0, 'Primitive netlist toy', <CircuitBuilder />),
          labItem(1, 'Quantum DSL', <QuantumDslLab />),
          labItem(2, 'Opcode lowering', <OpcodeLoweringLab />),
        ];
      case 'cleanup':
        return [
          labItem(0, 'Cleanup puzzle', <CleanupPuzzleLab />),
          labItem(1, 'Scratch lifecycle', <AccumulatorScratchLifecycleLab projectData={projectData} />),
        ];
      case 'modular-lowering':
        return [
          labItem(0, 'Partial-product grid', <MultiplierGridLab />),
          labItem(1, 'Modular reduction', <ModularReductionLab />),
          labItem(2, 'Accumulator lowering', <AccumulatorLoweringLab projectData={projectData} />),
          labItem(3, 'Scratch lifecycle', <AccumulatorScratchLifecycleLab projectData={projectData} />),
        ];
      case 'owner-capacity':
        return [
          labItem(0, 'Slot liveness', <SlotLiveness projectData={projectData} />),
          labItem(1, 'Invariant lab', <EngineInvariantLab />),
          labItem(2, 'Capacity game', <OwnerCapacityGame />),
        ];
      case 'resource-engine':
        return [
          labItem(0, 'Circuit stack map', <CircuitStackMap projectData={projectData} />),
          labItem(1, 'Mini resource engine', <MiniResourceEngineLab />),
          labItem(2, 'Schedule optimizer', <ScheduleOptimizerLab />),
        ];
      case 'mini-engine':
        return [
          labItem(0, 'Mini resource engine', <MiniResourceEngineLab />),
          labItem(1, 'Opcode lowering', <OpcodeLoweringLab />),
        ];
      case 'optimization':
        return [
          labItem(0, 'Optimization mission', <OptimizationMissionLab projectData={projectData} />),
          labItem(1, 'Baseline tradeoff', <BaselineTradeoffLab projectData={projectData} />),
        ];
      case 'point-add-boundary':
        return [
          labItem(0, 'Boundary debugger', <PointAddBoundaryDebugger projectData={projectData} />),
          labItem(1, 'Artifact atlas', <ArtifactAtlasLab projectData={projectData} />),
        ];
      case 'contribution':
        return [
          labItem(0, 'Contributor mission board', <ContributorMissionBoard projectData={projectData} />),
          labItem(1, 'Claim audit drill', <ClaimAuditDrill projectData={projectData} />),
          labItem(2, 'Course coverage audit', <CourseCoverageAuditLab lessonCount={lessons.length} quizCount={quiz.length} />),
        ];
      case 'zkp-boundary':
        return [
          labItem(0, 'ZKP boundary', <ProofBoundaryLab projectData={projectData} />),
          labItem(1, 'Confidence ladder', <ConfidenceLadderLab projectData={projectData} />),
          labItem(2, 'Artifact atlas', <ArtifactAtlasLab projectData={projectData} />),
        ];
      case 'repo-baselines':
        return [
          labItem(0, 'Baseline explorer', <BaselineExplorer projectData={projectData} />),
          labItem(1, 'Tradeoff landscape', <BaselineTradeoffLab projectData={projectData} />),
          labItem(2, 'Promotion audit', <BaselinePromotionLab projectData={projectData} />),
          labItem(3, 'Baseline chart', <BaselineChart projectData={projectData} />),
        ];
    }
  })();

  const focusedLabIndex = Math.min(focusedLabByLesson[activeLesson.id] ?? 0, Math.max(0, activeLabItems.length - 1));
  const hasGuidedLabFocus = labRoute.length > 0 && activeLabItems.length > 1;
  const showAllLabs = showAllLabsByLesson[activeLesson.id] ?? false;
  const visibleLabItems = hasGuidedLabFocus && !showAllLabs ? [activeLabItems[focusedLabIndex]] : activeLabItems;
  const gridLabLessons = new Set<LessonId>(['qubit', 'clifford', 'phase-estimation', 'lookup-qroam']);
  const labCollectionClass = hasGuidedLabFocus && !showAllLabs
    ? 'lab-focus-stage'
    : gridLabLessons.has(activeLesson.id) ? 'lab-grid' : 'lab-stack';

  const selectFocusedLab = (index: number) => {
    setFocusedLabByLesson((previous) => ({ ...previous, [activeLesson.id]: index }));
    setShowAllLabsByLesson((previous) => ({ ...previous, [activeLesson.id]: false }));
  };

  const moveFocusedLab = (direction: -1 | 1) => {
    const nextIndex = Math.min(Math.max(focusedLabIndex + direction, 0), activeLabItems.length - 1);
    selectFocusedLab(nextIndex);
  };

  const renderedActiveLabs = (
    <section className={labCollectionClass} aria-label="Interactive labs" data-testid="active-lab-stage">
      {visibleLabItems.map((item) => (
        <div className="lab-focus-item" data-testid={`lab-step-${slugify(item.name)}`} key={item.name}>
          {item.element}
        </div>
      ))}
    </section>
  );

  const guidedActiveLabs = (
    <>
      {labRoute.length > 0 ? (
        <section className="lab-route" data-testid="lab-route" aria-label="Lab route">
          <div className="lab-route-header">
            <div className="panel-heading">
              <ListChecks size={18} />
              <h3>{showAllLabs ? 'All labs' : `Lab ${focusedLabIndex + 1} of ${activeLabItems.length}`}</h3>
            </div>
            {hasGuidedLabFocus ? (
              <div className="lab-focus-controls" data-testid="lab-focus-controls">
                <button className="secondary-action" disabled={showAllLabs || focusedLabIndex === 0} onClick={() => moveFocusedLab(-1)} type="button">
                  <ArrowLeft size={16} />
                  Previous lab
                </button>
                <button className="secondary-action" disabled={showAllLabs || focusedLabIndex === activeLabItems.length - 1} onClick={() => moveFocusedLab(1)} type="button">
                  Next lab
                  <ArrowRight size={16} />
                </button>
                <button
                  className="secondary-action"
                  onClick={() => setShowAllLabsByLesson((previous) => ({ ...previous, [activeLesson.id]: !showAllLabs }))}
                  type="button"
                >
                  {showAllLabs ? 'Focus one lab' : 'Show all labs'}
                </button>
              </div>
            ) : null}
          </div>
          <ol>
            {activeLabItems.map((item, index) => (
              <li className={index === focusedLabIndex && !showAllLabs ? 'active' : undefined} key={item.name}>
                <button
                  aria-current={index === focusedLabIndex && !showAllLabs ? 'step' : undefined}
                  onClick={() => selectFocusedLab(index)}
                  type="button"
                >
                  <span>{index + 1}</span>
                  <strong>{item.name}</strong>
                </button>
              </li>
            ))}
          </ol>
        </section>
      ) : null}
      {renderedActiveLabs}
    </>
  );

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
        <button
          className="nav-mode-toggle"
          type="button"
          aria-pressed={showFullCourseIndex}
          onClick={() => setShowFullCourseIndex((value) => !value)}
        >
          {showFullCourseIndex ? 'Current section' : 'All lessons'}
        </button>
        <nav className="lesson-list">
          {navigationModules.map((module) => (
            <section key={module}>
              <p className="module-title">{module}</p>
              {groupedLessons[module].map((lesson) => {
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
        <header className={showResourceStatus ? 'hero-panel no-status compact-hero' : 'hero-panel no-status'}>
          <div>
            <p className="eyebrow">{activeLesson.module}</p>
            <h2>{activeLesson.title}</h2>
            <p className="hero-copy">{activeLesson.intuition}</p>
          </div>
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
            <strong>Lesson {currentIndex + 1} of {lessons.length}</strong>
          </div>
          <button
            className="primary-action"
            disabled={nextLesson === null}
            onClick={() => nextLesson && selectLesson(nextLesson.id)}
            type="button"
          >
            {nextLesson === null ? 'End' : 'Next'}
            {nextLesson === null ? null : <ArrowRight size={18} />}
          </button>
        </nav>

        {showResourceStatus ? (
          <section className="resource-status-strip" aria-label="Current repository resource status">
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
          </section>
        ) : null}

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
              <section className="lesson-detail-steps" data-testid="lesson-detail-steps">
                <div className="lesson-detail-heading">
                  <span>Build it up</span>
                  <strong>{activeLesson.deepDive.length} short steps</strong>
                </div>
                <ol className="lesson-step-list">
                  {activeLesson.deepDive.map((paragraph, index) => (
                    <li key={paragraph}>
                      <span>{index + 1}</span>
                      <p><MathText text={paragraph} /></p>
                    </li>
                  ))}
                </ol>
              </section>
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
            {pageGlossary.length > 0 && selectedVocab !== null ? (
              <details className="page-vocab" data-testid="page-vocab">
                <summary>
                  <span>Glossary for this page</span>
                  <strong>{pageGlossary.length} terms</strong>
                </summary>
                <div className="vocab-tabs" role="tablist" aria-label={`${activeLesson.title} vocabulary`}>
                  {pageGlossary.map(({ term }) => (
                    <button
                      aria-selected={term === selectedVocab.term}
                      key={term}
                      onClick={() => setSelectedVocabByLesson((previous) => ({ ...previous, [activeLesson.id]: term }))}
                      role="tab"
                      type="button"
                    >
                      {term}
                    </button>
                  ))}
                </div>
                <dl className="vocab-definition">
                  <div>
                    <dt>{selectedVocab.term}</dt>
                    <dd>{selectedVocab.definition}</dd>
                  </div>
                </dl>
              </details>
            ) : null}
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
            <section className="lesson-labs inline" id="active-lesson-labs" aria-label={`${activeLesson.title} labs`}>
              {guidedActiveLabs}
            </section>
          )}
        </section>

        {showRepoContract ? (
          <section className="lesson-labs" id="active-lesson-labs" aria-label={`${activeLesson.title} labs`}>
            {guidedActiveLabs}
          </section>
        ) : null}

        <section className="lesson-finish-panel" aria-label="Lesson checkpoint">
          <section className={checkpointRevealed ? 'checkpoint revealed' : 'checkpoint'} data-testid="lesson-recall-check">
            <CheckCircle2 size={18} />
            <div>
              <span>Answer before reveal</span>
              <strong>{checkpointQuestion}</strong>
              {checkpointRevealed ? <p>{activeLesson.checkpoint}</p> : null}
              <button
                className="checkpoint-reveal"
                onClick={() => setRevealedCheckpointByLesson((previous) => ({ ...previous, [activeLesson.id]: !checkpointRevealed }))}
                type="button"
              >
                {checkpointRevealed ? 'Hide answer' : 'Reveal checkpoint answer'}
              </button>
            </div>
          </section>
          <div className="actions">
            <button className="primary-action" type="button" onClick={completeAndContinue}>
              <CheckCircle2 size={18} />
              {nextLesson === null ? 'Mark understood and finish course' : 'Mark understood and continue'}
            </button>
          </div>
        </section>

        {showReviewPanels ? (
          <>
            <section className="wide-panel">
              <div className="panel-heading">
                <RotateCcw size={20} />
                <h3>Full course glossary</h3>
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
