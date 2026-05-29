import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { ArrowLeft, ArrowRight, BookOpen, CheckCircle2, Circle, Code2, GitBranch, ListChecks, RotateCcw } from 'lucide-react';
import projectData from './generated/project-data.json';
import { lessons, glossary, quiz, type LessonId } from './content/course';
import { BaselineChart } from './components/BaselineChart';
import { BlochPlayground } from './components/BlochPlayground';
import { StateVectorLab } from './components/StateVectorLab';
import { QubitAmplitudeBridgeLab } from './components/QubitAmplitudeBridgeLab';
import { OneQubitPatternsLab } from './components/OneQubitPatternsLab';
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
import { ComputationModelBridge } from './components/ComputationModelBridge';
import { MathTex, MathText } from './components/MathText';

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
  ],
  'one-qubit': [
    { name: 'Qubit steering', goal: 'Apply named one-qubit gates as steering moves before measurement.' },
    { name: 'Gate pattern missions', goal: 'Feel finite cycles, long motion, reversible groups, and no-attractor behavior.' },
  ],
  'two-qubit': [
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
  qubit: 'What does direct measurement read from a one-qubit amplitude pair?',
  'one-qubit': 'Why can a closed one-qubit gate cycle or rotate forever but not converge many starts to one point?',
  'two-qubit': 'What changes when the state has four joint amplitudes instead of two one-qubit amplitude pairs?',
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

function QubitStepVisual({ stepIndex }: { stepIndex: number }) {
  if (stepIndex === 0) {
    return (
      <div className="step-visual" data-testid="qubit-state-vector-visual" aria-label="Qubit state vector sketch">
        <svg viewBox="0 0 120 92" role="img" aria-label="Two equal-length amplitude arrows">
          <circle cx="46" cy="46" r="32" />
          <line className="axis" x1="14" y1="46" x2="78" y2="46" />
          <line className="axis" x1="46" y1="14" x2="46" y2="78" />
          <line className="zero-arrow" x1="46" y1="46" x2="78" y2="46" />
          <circle className="zero-dot" cx="78" cy="46" r="3.2" />
          <line className="one-arrow" x1="46" y1="46" x2="70" y2="25" />
          <circle className="one-dot" cx="70" cy="25" r="3.2" />
        </svg>
        <div>
          <MathTex tex="|\psi\rangle=a|0\rangle+b|1\rangle" />
          <p>This is one qubit: two amplitudes stored as one coherent state.</p>
        </div>
      </div>
    );
  }

  if (stepIndex === 2) {
    return (
      <div className="step-visual formula-step" data-testid="qubit-gate-visual" aria-label="Hadamard gate formula sketch">
        <div className="step-formula-stack">
          <strong>Example: Hadamard gate</strong>
          <MathTex tex="H:\ (a,b)\mapsto \left(\frac{a+b}{\sqrt2},\frac{a-b}{\sqrt2}\right)" />
        </div>
        <p>One concrete valid gate: it preserves total probability while recombining the two amplitudes.</p>
      </div>
    );
  }

  if (stepIndex === 4) {
    return (
      <div className="step-visual" data-testid="qubit-mixing-visual" aria-label="Probability split after Hadamard mixing">
        <div className="probability-mini-chart">
          <div>
            <strong>0</strong>
            <i style={{ width: '76%' }} />
          </div>
          <div>
            <strong>1</strong>
            <i style={{ width: '24%' }} />
          </div>
        </div>
        <MathTex tex="P(0)=|a'|^2,\quad P(1)=|b'|^2" />
        <p>Angle can become visible only after the gate changes arrow lengths.</p>
      </div>
    );
  }

  return null;
}

function OrientationModelVisual() {
  return (
    <div className="orientation-model-strip" data-testid="orientation-model-strip">
      <article>
        <strong>Classical</strong>
        <MathTex tex="\text{bits}\rightarrow\text{instructions}\rightarrow\text{bits}" />
        <p>One definite memory state is updated by discrete operations.</p>
      </article>
      <article>
        <strong>Quantum</strong>
        <MathTex tex="\text{amplitudes}\rightarrow\text{gates}\rightarrow\text{amplitudes}" />
        <p>A vector of amplitudes is transformed by reversible linear gates.</p>
      </article>
      <article>
        <strong>Readout</strong>
        <MathTex tex="\text{amplitudes}\rightarrow\text{measured bits}" />
        <p>The calculation is continuous internally, but the observed answer is discrete.</p>
      </article>
    </div>
  );
}

function OneQubitStoryPanel() {
  return (
    <section className="one-qubit-story" data-testid="one-qubit-story" aria-label="One-qubit gate story">
      <article className="story-question">
        <h4>What is allowed to move?</h4>
        <p>
          A qubit is one coherent two-amplitude state, not two independent probability
          sliders. Before measurement we are allowed to steer the pair of arrows. The
          steering can change lengths and angles, but it must transform the whole pair
          as one object.
        </p>
        <div className="qubit-motion-strip" aria-hidden="true">
          <figure>
            <svg className="mini-phase-wheel" viewBox="0 0 120 72">
              <circle cx="36" cy="36" r="25" />
              <line x1="36" y1="36" x2="61" y2="36" />
              <line className="phase-line" x1="36" y1="36" x2="52" y2="17" />
            </svg>
            <figcaption>two arrows before measurement</figcaption>
          </figure>
          <i />
          <figure>
            <div className="mini-prob-bars">
              <span>measure 0</span>
              <i style={{ width: '82%' }} />
              <span>measure 1</span>
              <i className="alt" style={{ width: '28%' }} />
            </div>
            <figcaption>lengths become probabilities only at readout</figcaption>
          </figure>
        </div>
      </article>

      <article className="story-rule">
        <div>
          <h4>Why a gate is a two-by-two rule</h4>
          <p>
            If the input is a mixture of a 0-branch and a 1-branch, the output must be
            the same mixture of what the rule would do to each branch. That is the
            linearity requirement. For one qubit, every linear rule has four complex
            coefficients.
          </p>
        </div>
        <div className="unitary-rule-box">
          <MathTex displayMode tex="\begin{bmatrix}a'\\ b'\end{bmatrix}=\begin{bmatrix}\alpha&\beta\\ \gamma&\delta\end{bmatrix}\begin{bmatrix}a\\ b\end{bmatrix}" />
          <span>the gate acts on the amplitude vector, not on sampled bits</span>
        </div>
      </article>

      <article className="story-rule">
        <div>
          <h4>Why most formulas are not legal gates</h4>
          <p>
            Measurement probabilities come from squared lengths, so a valid closed gate
            must preserve the total length for every possible input state. That is what
            unitary means here: linear, reversible, and total-probability preserving.
          </p>
          <p>
            This is stronger than “works on the examples we tried.” The inverse must
            exist for the whole amplitude plane, otherwise two different starting states
            could be crushed into one final state.
          </p>
        </div>
        <div className="unitary-rule-box">
          <MathTex tex="|a|^2+|b|^2=1" />
          <MathTex tex="U^\dagger U=I" />
          <span>normalization stays true after every closed gate</span>
        </div>
      </article>

      <div className="story-card-grid">
        <article>
          <strong>Hadamard: create and recombine a split</strong>
          <p>
            Start at definite 0. A Hadamard move creates equal 0 and 1 amplitudes. Run
            Hadamard again and the sum/difference channels recombine back to the start.
          </p>
          <div className="mini-arrow-split" aria-hidden="true">
            <span>0</span>
            <i />
            <b>H</b>
            <i />
            <span>0 + 1</span>
          </div>
        </article>
        <article>
          <strong>Bit flip: rename the two outcomes</strong>
          <p>
            X swaps the two amplitude slots. It behaves like a classical NOT only on
            definite inputs, but on a superposition it swaps the whole two-arrow state.
          </p>
          <div className="swap-sketch" aria-hidden="true">
            <span>0-slot</span>
            <i />
            <span>1-slot</span>
            <b>X</b>
          </div>
        </article>
        <article>
          <strong>Phase turn: store information in angle</strong>
          <p>
            S, T, or a rotation can turn only the 1-amplitude arrow. Direct measurement
            may still see the same 50/50 lengths, but later mixing can expose the angle.
          </p>
          <svg className="mini-phase-wheel" viewBox="0 0 120 72" aria-hidden="true">
            <circle cx="36" cy="36" r="25" />
            <line x1="36" y1="36" x2="61" y2="36" />
            <line className="phase-line" x1="36" y1="36" x2="52" y2="17" />
            <path d="M78 36 h24" />
            <path className="phase-line" d="M93 22 a18 18 0 0 1 0 28" />
          </svg>
        </article>
      </div>

      <div className="story-motion-grid">
        <article>
          <h4>Short cycles</h4>
          <p>
            Some moves loop back quickly. Do H twice and you are back where you started.
            Do X twice and the swap undoes itself. Do S four times and the phase has made
            a full turn.
          </p>
          <div className="cycle-badges" aria-hidden="true">
            <span>H² = I</span>
            <span>X² = I</span>
            <span>S⁴ = I</span>
          </div>
        </article>
        <article>
          <h4>Long reversible walks</h4>
          <p>
            A rotation by an awkward angle does not have to close after a few repeats.
            It can keep visiting new angles. That is still reversible motion, not
            convergence.
          </p>
          <svg className="long-rotation-sketch" viewBox="0 0 160 86" aria-hidden="true">
            <circle cx="43" cy="43" r="30" />
            {[0, 1, 2, 3, 4, 5].map((index) => {
              const angle = index * 0.92;
              return (
                <circle
                  className={index === 5 ? 'last' : ''}
                  cx={43 + Math.cos(angle) * 30}
                  cy={43 - Math.sin(angle) * 30}
                  key={index}
                  r="3"
                />
              );
            })}
            <path d="M88 43 h46" />
            <text x="92" y="32">same rule</text>
            <text x="92" y="58">new angle</text>
          </svg>
        </article>
        <article>
          <h4>No closed-gate attractor</h4>
          <p>
            If many different starting states all drifted into the same final state,
            the inverse gate would be impossible. Convergence belongs to measurement,
            noise, or deliberate reset, not to a closed gate.
          </p>
          <svg className="no-attractor-sketch" viewBox="0 0 170 86" aria-hidden="true">
            <circle cx="24" cy="20" r="5" />
            <circle cx="24" cy="43" r="5" />
            <circle cx="24" cy="66" r="5" />
            <path d="M34 20 C70 20 80 43 119 43" />
            <path d="M34 43 H119" />
            <path d="M34 66 C70 66 80 43 119 43" />
            <circle className="bad" cx="128" cy="43" r="8" />
            <text x="143" y="48">not a gate</text>
          </svg>
        </article>
      </div>

      <article className="story-question">
        <h4>The lab is a small control room</h4>
        <p>
          The buttons below are deliberately tiny examples of the same discipline used
          later in the resource engine: apply named reversible operations, inspect the
          state they produce, then verify a concrete mission. Make a split, hide phase,
          reveal phase, and return by a cycle before moving to two-qubit gates.
        </p>
      </article>
    </section>
  );
}

function TwoQubitStoryPanel() {
  return (
    <section className="two-qubit-story" data-testid="two-qubit-story" aria-label="Two-qubit state story">
      <article className="story-question">
        <h4>The new object is a joint table</h4>
        <p>
          With one qubit, the state had two amplitudes. With two qubits, the state
          has four amplitudes, one for each possible two-bit label. The labels look
          classical, but before measurement they are branches of one coherent state.
        </p>
        <div className="joint-state-table" aria-hidden="true">
          {['|00>', '|01>', '|10>', '|11>'].map((label) => (
            <span key={label}>{label}<i /></span>
          ))}
        </div>
      </article>

      <article className="story-rule product-rule">
        <div>
          <h4>Sometimes two wires are still independent</h4>
          <p>
            If q0 has amplitudes <MathTex tex="a_0,a_1" /> and q1 has amplitudes{' '}
            <MathTex tex="b_0,b_1" />, an independent two-qubit state is built by
            multiplying choices. That special shape is called a product state.
          </p>
          <p>
            Product states can still be in superposition. They are just not entangled:
            each wire still has its own one-qubit description.
          </p>
        </div>
        <div className="product-factor" aria-hidden="true">
          <MathTex displayMode tex="\begin{bmatrix}a_0\\a_1\end{bmatrix}\otimes\begin{bmatrix}b_0\\b_1\end{bmatrix}=\begin{bmatrix}a_0b_0\\a_0b_1\\a_1b_0\\a_1b_1\end{bmatrix}" />
          <span>four amplitudes, but generated from two private one-qubit states</span>
        </div>
      </article>

      <article className="story-rule cx-rule">
        <div>
          <h4>Controlled-X is not a measurement</h4>
          <p>
            Controlled-X, also called CNOT or CX, does not peek at q0 and choose one
            classical branch. It is a reversible permutation of the joint labels:
            branches with q0 = 0 stay put, branches with q0 = 1 swap the q1 label.
          </p>
          <p>
            That matters because if q0 is in a split, CX applies coherently to every
            live branch and can tie the two wires into one joint pattern.
          </p>
        </div>
        <div className="cx-permutation" aria-hidden="true">
          <span>|00&gt; -&gt; |00&gt;</span>
          <span>|01&gt; -&gt; |01&gt;</span>
          <span>|10&gt; -&gt; |11&gt;</span>
          <span>|11&gt; -&gt; |10&gt;</span>
        </div>
      </article>

      <article className="story-question">
        <h4>How the Bell pair is born</h4>
        <div className="bell-steps" aria-hidden="true">
          <div>
            <strong>start</strong>
            <MathTex tex="|00\rangle" />
          </div>
          <i />
          <div>
            <strong>split q0</strong>
            <MathTex tex="(|00\rangle+|10\rangle)/\sqrt{2}" />
          </div>
          <i />
          <div>
            <strong>control q1</strong>
            <MathTex tex="(|00\rangle+|11\rangle)/\sqrt{2}" />
          </div>
        </div>
        <p>
          After the split, the q0 = 1 branch is <MathTex tex="|10\rangle" />. CX turns
          that branch into <MathTex tex="|11\rangle" />. Now only matching labels remain:
          00 and 11. Repeated measurement gives random individual bits, but the two
          bits agree in the same run.
        </p>
      </article>

      <div className="story-motion-grid">
        <article>
          <h4>Product split</h4>
          <p>
            H on both wires makes four equal branches. This is a big state, but it
            still factors into q0's state times q1's state.
          </p>
          <div className="state-table-grid" aria-hidden="true">
            {['00', '01', '10', '11'].map((label) => <span key={label}>{label}</span>)}
          </div>
        </article>
        <article>
          <h4>Entangled pattern</h4>
          <p>
            A Bell pair has only 00 and 11 branches. No pair of private one-qubit
            states can reproduce exactly that table.
          </p>
          <div className="state-table-grid bell-grid" aria-hidden="true">
            <span>00</span>
            <span className="empty">01</span>
            <span className="empty">10</span>
            <span>11</span>
          </div>
        </article>
        <article>
          <h4>Separable or not?</h4>
          <p>
            For a pure two-qubit table, the quick algebraic check is whether
            {' '}<MathTex tex="a_{00}a_{11}-a_{01}a_{10}" /> is zero. Nonzero means the table
            cannot factor into two one-qubit states.
          </p>
          <div className="entanglement-test" aria-hidden="true">det = 0 ? product : entangled</div>
        </article>
      </div>

      <article className="story-question">
        <h4>What measurement shows</h4>
        <p>
          One run samples one full label, such as 00 or 11. The state vector is not
          visible in a single run; it is inferred by preparing the same circuit many
          times and looking at the distribution and correlations.
        </p>
        <div className="measurement-repeat" aria-hidden="true">
          <span>run 1: 00</span>
          <span>run 2: 11</span>
          <span>run 3: 11</span>
          <span>run 4: 00</span>
        </div>
      </article>
    </section>
  );
}

function CliffordStoryPanel() {
  return (
    <section className="clifford-story" data-testid="clifford-story" aria-label="Clifford and non-Clifford cost story">
      <article className="story-question">
        <h4>Why there is a second cost axis</h4>
        <p>
          Counting live qubits answers “how much quantum memory is occupied at the
          busiest moment?” It does not answer “how hard is the circuit to run fault
          tolerantly?” The second question appears because some gates are cheap inside
          the stabilizer world, while other gates need scarce prepared magic resources.
        </p>
        <div className="cost-axis-strip" aria-hidden="true">
          <div><strong>logical qubits</strong><span>peak live storage</span></div>
          <div><strong>non-Clifford</strong><span>magic-state work</span></div>
        </div>
      </article>

      <article className="story-rule stabilizer-rule">
        <div>
          <h4>The stabilizer map is a restricted but useful world</h4>
          <p>
            Clifford gates include familiar moves like H, S, and CX. They can create
            superposition, interference, and some entanglement, so they are not
            “classical gates.” Their special property is narrower: they keep Pauli
            axes mapped to Pauli axes, which lets a stabilizer description stay compact.
          </p>
          <p>
            That is why Clifford-only circuits are a big, useful class that can still
            be tracked efficiently by classical stabilizer simulators.
          </p>
        </div>
        <div className="stabilizer-map" aria-hidden="true">
          <span>+X</span>
          <span>+Y</span>
          <span>-X</span>
          <span>-Y</span>
          <i />
        </div>
      </article>

      <article className="story-rule magic-rule">
        <div>
          <h4>A magic step leaves the cheap map</h4>
          <p>
            A T gate is a 45-degree phase step. On the toy wheel it lands halfway
            between stabilizer axes. That “between axes” state is exactly the point:
            Clifford gates alone cannot synthesize it.
          </p>
          <p>
            Fault-tolerant designs commonly implement such non-Clifford steps by
            preparing and consuming magic states. Those factories can dominate runtime,
            so the repo treats non-Clifford count as a first-class resource.
          </p>
        </div>
        <div className="magic-step-map" aria-hidden="true">
          <span>Clifford axis</span>
          <i />
          <b>T</b>
          <i className="magic" />
          <span>magic region</span>
        </div>
      </article>

      <div className="story-motion-grid">
        <article>
          <h4>Cheap does not mean useless</h4>
          <p>
            Clifford gates still move quantum information and wire correlations around.
            They are cheap because of the stabilizer structure, not because nothing
            quantum happened.
          </p>
          <div className="clifford-stack" aria-hidden="true">
            <span>H</span>
            <span>S</span>
            <span>CX</span>
          </div>
        </article>
        <article>
          <h4>Expensive does not mean optional</h4>
          <p>
            Arithmetic needs controlled products, comparisons, and table selection.
            Those decisions are where Toffoli-like non-Clifford work enters.
          </p>
          <div className="clifford-stack magic-stack-mini" aria-hidden="true">
            <span>AND</span>
            <span>CCX</span>
            <span>select</span>
          </div>
        </article>
        <article>
          <h4>The result is a tradeoff</h4>
          <p>
            A low-qubit design can spend too much magic work. A low-magic design can
            keep too many values live. Peak qubits and non-Clifford count are separate
            headline axes, so the repo has to report them together.
          </p>
          <div className="tradeoff-mini-chart" aria-hidden="true">
            <span>q</span>
            <i />
            <span>magic</span>
          </div>
        </article>
      </div>

      <article className="story-question">
        <h4>What the labs are proving</h4>
        <p>
          The wheel makes the boundary visible: S and Z stay on stabilizer axes, while
          T moves into the magic region and increments the non-Clifford counter. The
          budget lab then scales the same distinction to repo-sized claims: a headline
          needs live-qubit accounting and magic-work accounting at the same time.
        </p>
      </article>
    </section>
  );
}

function LogicalPhysicalStoryPanel() {
  return (
    <section className="logical-physical-story" data-testid="logical-physical-story" aria-label="Logical and physical qubit story">
      <article className="story-question">
        <h4>The repo counts the algorithm layer</h4>
        <p>
          The repo headline qubit count is not the number of hardware devices in a
          machine. It is the peak number of logical quantum wires the algorithm needs
          after lowering and scheduling. That layer is the right place to compare
          circuit designs before choosing a hardware architecture.
        </p>
        <div className="resource-layer-stack" aria-hidden="true">
          <span>algorithm idea</span>
          <i />
          <span>logical circuit rows</span>
          <i />
          <span>physical layout</span>
        </div>
      </article>

      <article className="story-rule encoding-rule">
        <div>
          <h4>A logical qubit is protected information</h4>
          <p>
            A physical qubit is a device-level carrier. A logical qubit is one qubit of
            encoded information protected by an error-correcting code. The code spreads
            the information across many physical carriers and repeatedly checks for
            error patterns without directly reading the logical state.
          </p>
          <p>
            That protection is why a single logical wire can correspond to many physical
            qubits, measurement rounds, classical decoding, and layout constraints.
          </p>
        </div>
        <div className="logical-encoding-sketch" aria-hidden="true">
          <strong>logical wire</strong>
          <div>
            {Array.from({ length: 9 }, (_, index) => <span key={index} />)}
          </div>
          <em>physical carriers + checks</em>
        </div>
      </article>

      <div className="story-motion-grid">
        <article>
          <h4>Code distance</h4>
          <p>
            Distance is a protection parameter. Larger distance usually means more
            physical resources and lower logical failure risk, assuming the hardware
            noise is below the code threshold.
          </p>
          <div className="distance-ladder" aria-hidden="true">
            <span>d=3</span>
            <span>d=5</span>
            <span>d=7</span>
          </div>
        </article>
        <article>
          <h4>Syndrome checks</h4>
          <p>
            Error correction does not copy the quantum value. It measures check
            information that points to likely errors while preserving the encoded
            logical state.
          </p>
          <div className="syndrome-row" aria-hidden="true">
            <span>data</span>
            <i />
            <span>checks</span>
            <i />
            <span>decoder</span>
          </div>
        </article>
        <article>
          <h4>Factories are extra</h4>
          <p>
            Non-Clifford magic work can require dedicated factory space and time. A
            full hardware estimate must place both the algorithmic logical qubits and
            the factory resources.
          </p>
          <div className="factory-layout-mini" aria-hidden="true">
            <span>algorithm</span>
            <span>factory</span>
          </div>
        </article>
      </div>

      <article className="story-rule physical-estimate-rule">
        <div>
          <h4>Why the same logical result can imply many machines</h4>
          <p>
            Physical estimates depend on the selected code, code distance, physical
            error rates, operation times, connectivity, routing, classical decoding,
            and magic-state factories. Change those assumptions and the same logical
            circuit can produce a very different physical-qubit envelope.
          </p>
        </div>
        <div className="estimate-equation" aria-hidden="true">
          <MathTex tex="\text{logical circuit}+\text{QEC model}+\text{layout}\Rightarrow\text{hardware estimate}" />
        </div>
      </article>

      <article className="story-question">
        <h4>What the labs are allowed to claim</h4>
        <p>
          The first lab is a toy bridge from logical rows to a physical envelope. The
          second lab is a repetition-code intuition demo. Neither is the repo’s hardware
          claim. They exist to teach why a logical result is a circuit-design claim, and
          why hardware claims need an additional fault-tolerance model.
        </p>
      </article>
    </section>
  );
}

function PhaseEstimationStoryPanel() {
  return (
    <section className="phase-estimation-story" data-testid="phase-estimation-story" aria-label="Phase estimation story">
      <article className="story-question">
        <h4>The problem is not “measure the answer directly”</h4>
        <p>
          The hidden value is not sitting in one readable qubit. The circuit creates a
          repeating phase pattern across a control register. Phase estimation is the
          readout shell that turns that angle pattern into ordinary bits.
        </p>
        <div className="phase-readout-strip" aria-hidden="true">
          <span>hidden rhythm</span>
          <i />
          <span>phase pattern</span>
          <i />
          <span>bit label</span>
        </div>
      </article>

      <article className="story-rule phase-powers-rule">
        <div>
          <h4>Controlled powers write a binary rhythm</h4>
          <p>
            The control register asks for powers of the same operation: one copy, two
            copies, four copies, eight copies, and so on. Each power turns the phase by
            a related amount, so the bits of the hidden phase are written as a pattern
            of rotating arrows.
          </p>
          <p>
            In textbook phase estimation that operation is a unitary <MathTex tex="U" />.
            In this repo’s attack, the expensive controlled operation is elliptic-curve
            group arithmetic over secp256k1.
          </p>
        </div>
        <div className="controlled-power-sketch" aria-hidden="true">
          {['U', 'U^2', 'U^4', 'U^8'].map((label, index) => (
            <div key={label}>
              <span>{label}</span>
              <i style={{ transform: `rotate(${index * 35}deg)` }} />
            </div>
          ))}
        </div>
      </article>

      <article className="story-rule fourier-readout-rule">
        <div>
          <h4>The inverse QFT is a rhythm matcher</h4>
          <p>
            Fourier readout tries candidate output labels. The matching label makes the
            phase arrows line up, so amplitudes reinforce. Wrong labels leave the arrows
            spread around the circle, so they cancel.
          </p>
          <p>
            That is why the lab shows bars: after the inverse QFT, measurement is likely
            to return the label whose rhythm best matches the phase pattern.
          </p>
        </div>
        <div className="fourier-match-sketch" aria-hidden="true">
          <div>
            <strong>match</strong>
            <span />
            <span />
            <span />
          </div>
          <div>
            <strong>wrong</strong>
            <span className="wrong-a" />
            <span className="wrong-b" />
            <span className="wrong-c" />
          </div>
        </div>
      </article>

      <div className="story-motion-grid">
        <article>
          <h4>Precision bits</h4>
          <p>
            More control bits give more binary places of the phase estimate, but they
            also require more controlled powers and more readout work.
          </p>
          <div className="precision-bit-row" aria-hidden="true">
            <span>1/2</span>
            <span>1/4</span>
            <span>1/8</span>
            <span>1/16</span>
          </div>
        </article>
        <article>
          <h4>Semiclassical readout</h4>
          <p>
            Large circuits often use a semiclassical inverse QFT: measure one bit, feed
            the result forward, and continue. The concept is the same rhythm matching.
          </p>
          <div className="semiclassical-strip" aria-hidden="true">
            <span>measure</span>
            <i />
            <span>correct phase</span>
          </div>
        </article>
        <article>
          <h4>Cost lives before readout</h4>
          <p>
            The inverse QFT is the lens. The costly object is the repeated controlled
            group operation that creates the phase pattern the lens can read.
          </p>
          <div className="cost-before-readout" aria-hidden="true">
            <span>point-adds</span>
            <span>QFT lens</span>
          </div>
        </article>
      </div>

      <article className="story-question">
        <h4>What to do in the labs</h4>
        <p>
          First move the hidden phase and watch the likely binary label move. Then use
          the Fourier lens to compare a matching candidate against a wrong one. The
          important lesson is the direction of causality: controlled arithmetic creates
          the phase rhythm, and inverse QFT turns that rhythm into bits.
        </p>
      </article>
    </section>
  );
}

function EcdlpStoryPanel() {
  return (
    <section className="ecdlp-story" data-testid="ecdlp-story" aria-label="secp256k1 discrete-log attack story">
      <article className="story-question">
        <h4>What is public, and what is hidden?</h4>
        <p>
          A secp256k1 private key is a scalar <MathTex tex="d" />. The corresponding
          public key is the curve point <MathTex tex="Q=dG" />, where{' '}
          <MathTex tex="G" /> is the standard generator point. Everyone may know{' '}
          <MathTex tex="G" /> and <MathTex tex="Q" />. The hard problem is recovering{' '}
          <MathTex tex="d" />.
        </p>
        <div className="key-derivation-strip" aria-hidden="true">
          <span>secret scalar d</span>
          <i />
          <span>repeat point-add from G</span>
          <i />
          <span>public point Q</span>
        </div>
      </article>

      <article className="story-rule ecdlp-rule">
        <div>
          <h4>“Logarithm” means undoing repeated group addition</h4>
          <p>
            In ordinary arithmetic, a logarithm asks how many repeated multiplications
            produced a value. In an elliptic-curve group, the analogous question asks
            how many repeated additions of <MathTex tex="G" /> produced{' '}
            <MathTex tex="Q" />.
          </p>
          <p>
            Classical security comes from this one-way shape: computing{' '}
            <MathTex tex="dG" /> is easy, but recovering <MathTex tex="d" /> from{' '}
            <MathTex tex="G" /> and <MathTex tex="Q" /> is believed hard for classical
            computers at secp256k1 size.
          </p>
        </div>
        <div className="repeated-add-sketch" aria-hidden="true">
          <span>G</span>
          <span>2G</span>
          <span>3G</span>
          <span>...</span>
          <span>dG = Q</span>
        </div>
      </article>

      <article className="story-rule oracle-shape-rule">
        <div>
          <h4>The quantum oracle asks two-register questions</h4>
          <p>
            Shor-style discrete-log circuits do not test every possible private key.
            They build a reversible group operation over two registers:
            <MathTex tex="(a,b)\mapsto aG+bQ" />.
          </p>
          <p>
            Since <MathTex tex="Q=dG" />, the output is really{' '}
            <MathTex tex="(a+bd)G" />. Different <MathTex tex="(a,b)" /> pairs collide
            whenever they move along a hidden period direction tied to{' '}
            <MathTex tex="d" />.
          </p>
        </div>
        <div className="oracle-lattice-sketch" aria-hidden="true">
          <span className="selected">a,b</span>
          <span />
          <span />
          <span />
          <span className="paired">a+d,b-1</span>
          <span />
          <span />
          <span />
          <span />
        </div>
      </article>

      <div className="story-motion-grid">
        <article>
          <h4>Hidden period</h4>
          <p>
            Moving from <MathTex tex="(a,b)" /> to <MathTex tex="(a+d,b-1)" /> keeps{' '}
            <MathTex tex="a+bd" /> unchanged. That invisible slope is what phase
            estimation can sample.
          </p>
          <div className="period-vector-pill" aria-hidden="true">(+d, -1)</div>
        </article>
        <article>
          <h4>Why point-add dominates</h4>
          <p>
            The expensive unit is not the final algebra that recovers <MathTex tex="d" />.
            It is repeatedly and reversibly computing controlled additions of
            precomputed secp256k1 points.
          </p>
          <div className="point-add-chain" aria-hidden="true">
            <span>lookup point</span>
            <i />
            <span>controlled add</span>
          </div>
        </article>
        <article>
          <h4>Why this repo is narrow</h4>
          <p>
            The project does not claim to break wallets on today’s hardware. It audits
            one circuit-engineering boundary: how costly the repeated secp256k1 point-add
            leaf is under strict quantum accounting.
          </p>
          <div className="scope-badges" aria-hidden="true">
            <span>not runtime</span>
            <span>not hardware bill</span>
            <span>logical circuit</span>
          </div>
        </article>
      </div>

      <article className="story-question">
        <h4>How the labs fit together</h4>
        <p>
          The attack map shows the full pipeline. The discrete-log oracle toy shows the
          hidden period relation. Phase kickback shows how the oracle leaves a phase
          imprint. The toy curve lab grounds scalar multiplication as repeated point
          addition. The resource labs then connect those ideas to repeated point-add leaves.
        </p>
      </article>
    </section>
  );
}

function GatesStoryPanel() {
  return (
    <section className="gates-story" data-testid="gates-story" aria-label="Gates wires and cleanup story">
      <article className="story-question">
        <h4>From formula to circuit row</h4>
        <p>
          A high-level formula says what should happen. A circuit row says exactly
          which named wires are touched at one moment in time. That difference is
          why this repo cares about netlists: rows are countable, formulas are not.
        </p>
      </article>

      <div className="wire-timeline-panel" aria-label="Wire timeline sketch">
        <div className="wire-labels">
          <span>q0 control</span>
          <span>q1 control</span>
          <span>scratch A</span>
          <span>accumulator</span>
        </div>
        <div className="wire-timelines">
          {[0, 1, 2, 3].map((wire) => <i key={wire} />)}
          <b style={{ gridColumn: '2', gridRow: '1 / 4' }}>compute</b>
          <b className="use" style={{ gridColumn: '3', gridRow: '3 / 5' }}>use</b>
          <b className="clean" style={{ gridColumn: '4', gridRow: '1 / 4' }}>uncompute</b>
        </div>
      </div>

      <div className="story-card-grid">
        <article>
          <strong>Wire</strong>
          <p>A wire is not just a drawing lane. It is named quantum storage across time.</p>
          <span className="story-token">q2 lives from row 1 to row 7</span>
        </article>
        <article>
          <strong>Controlled gate</strong>
          <p>A control does not measure. It says: on branches where this wire is 1, move the target.</p>
          <span className="story-token">CX q0 -&gt; q1</span>
        </article>
        <article>
          <strong>Toffoli-like step</strong>
          <p>Two controls can compute a product bit into a target. This is why arithmetic becomes expensive.</p>
          <span className="story-token">CCX q0,q1 -&gt; q2</span>
        </article>
      </div>

      <article className="story-rule cleanup-rule">
        <div>
          <h4>Why cleanup is not optional</h4>
          <p>
            Classical code can compute a temporary variable, use it, and let the variable
            disappear from your attention. In a quantum circuit, that temporary value may
            still be entangled with the rest of the state. The standard pattern is compute,
            copy or consume the useful effect, then run the computation backward.
          </p>
        </div>
        <div className="cleanup-equation">
          <span>compute</span>
          <i />
          <span>use</span>
          <i />
          <span>uncompute</span>
        </div>
      </article>

      <div className="story-motion-grid">
        <article>
          <h4>If cleanup is missing</h4>
          <p>The scratch wire is still live. It counts against peak qubits and can carry unwanted correlation.</p>
          <div className="audit-fail">scratch is still live</div>
        </article>
        <article>
          <h4>If cleanup is wrong</h4>
          <p>Running an inverse with stale controls does not restore zero. The circuit no longer implements the promised function.</p>
          <div className="audit-fail">inverse precondition failed</div>
        </article>
        <article>
          <h4>If cleanup is proven</h4>
          <p>The temporary wire returns to zero and can stop being counted as a live value.</p>
          <div className="audit-pass">scratch returned to |0&gt;</div>
        </article>
      </div>
    </section>
  );
}

function splitLessonStep(paragraph: string) {
  const separatorIndex = paragraph.indexOf(':');
  const firstSentenceIndex = paragraph.indexOf('.');
  const hasShortLabel = separatorIndex > 0 && separatorIndex < 32 && (firstSentenceIndex === -1 || separatorIndex < firstSentenceIndex);

  if (!hasShortLabel) {
    return { body: paragraph, title: null };
  }

  return {
    body: paragraph.slice(separatorIndex + 1).trim(),
    title: paragraph.slice(0, separatorIndex),
  };
}

export function App() {
  const [activeLessonId, setActiveLessonId] = useState<LessonId>(() => lessonFromHash());
  const [completed, setCompleted] = useState<Set<LessonId>>(() => loadCompletedLessons());
  const [focusedLabByLesson, setFocusedLabByLesson] = useState<Partial<Record<LessonId, number>>>({});
  const [showAllLabsByLesson, setShowAllLabsByLesson] = useState<Partial<Record<LessonId, boolean>>>({});
  const [revealedCheckpointByLesson, setRevealedCheckpointByLesson] = useState<Partial<Record<LessonId, boolean>>>({});
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
          labItem(0, 'Classical vs quantum program', <ComputationModelBridge />),
          labItem(1, 'What has to be proved', <ProjectProofMap />),
          labItem(2, 'Learning path map',
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
        ];
      case 'one-qubit':
        return [
          labItem(0, 'Qubit steering', <BlochPlayground />),
          labItem(1, 'Gate pattern missions', <OneQubitPatternsLab />),
        ];
      case 'two-qubit':
        return [
          labItem(0, 'Two-qubit state vector', <StateVectorLab />),
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
  const gridLabLessons = new Set<LessonId>(['qubit', 'one-qubit', 'two-qubit', 'clifford', 'phase-estimation', 'lookup-qroam']);
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
            <section className="lesson-primer" aria-label="Lesson introduction">
              <p>{activeLesson.mentalModel}</p>
            </section>
            {activeLesson.id === 'zero' ? <OrientationModelVisual /> : null}
            {activeLesson.id === 'one-qubit' ? <OneQubitStoryPanel /> : null}
            {activeLesson.id === 'two-qubit' ? <TwoQubitStoryPanel /> : null}
            {activeLesson.id === 'clifford' ? <CliffordStoryPanel /> : null}
            {activeLesson.id === 'logic-physical' ? <LogicalPhysicalStoryPanel /> : null}
            {activeLesson.id === 'phase-estimation' ? <PhaseEstimationStoryPanel /> : null}
            {activeLesson.id === 'ecdlp' ? <EcdlpStoryPanel /> : null}
            {activeLesson.id === 'gates' ? <GatesStoryPanel /> : null}
            {activeLesson.deepDive && !['one-qubit', 'two-qubit', 'clifford', 'logic-physical', 'phase-estimation', 'ecdlp', 'gates'].includes(activeLesson.id) ? (
              <section className="lesson-detail-steps" data-testid="lesson-detail-steps">
                <ol className="lesson-step-list">
                  {activeLesson.deepDive.map((paragraph, index) => {
                    const step = splitLessonStep(paragraph);

                    return (
                      <li key={paragraph}>
                        <div className="lesson-step-body">
                          {step.title ? <h4>{step.title}</h4> : null}
                          <p><MathText text={step.body} /></p>
                        {activeLesson.id === 'qubit' ? <QubitStepVisual stepIndex={index} /> : null}
                        </div>
                      </li>
                    );
                  })}
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
