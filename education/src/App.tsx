import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { ArrowLeft, ArrowRight, BookOpen, CheckCircle2, Circle, GitBranch, ListChecks, RotateCcw } from 'lucide-react';
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
import { MathTex } from './components/MathText';

const formatInt = (value: number) => new Intl.NumberFormat('en-US').format(value);
const readableStatus = (value: string) => value.replaceAll('_', ' ');
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
  zero: [
    { name: 'Classical vs quantum program', goal: 'Compare ordinary bit-string updates with amplitude-vector updates.' },
    { name: 'What has to be proved', goal: 'Connect the public key target to executable circuits and resource claims.' },
    { name: 'Learning path map', goal: 'See the route from zero background to useful repo contribution.' },
  ],
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
  clifford: [
    { name: 'Stabilizer vs magic wheel', goal: 'Separate Clifford motion from the first non-Clifford magic step.' },
    { name: 'Magic budget', goal: 'Scale non-Clifford count into a factory-pressure thought experiment.' },
  ],
  'logic-physical': [
    { name: 'Logical-to-physical bridge', goal: 'Translate logical rows through explicit QEC assumptions.' },
    { name: 'Error-correction toy', goal: 'Decode a tiny repetition code and see why distance changes protection.' },
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
  programming: [
    { name: 'Primitive netlist toy', goal: 'Build rows and see operands, effects, and non-Clifford cost.' },
    { name: 'Quantum DSL', goal: 'Type valid rows, reject invalid opcodes, and inspect the parsed table.' },
    { name: 'Opcode lowering', goal: 'Expand one abstract opcode into primitive counted rows.' },
  ],
  cleanup: [
    { name: 'Cleanup puzzle', goal: 'Prove compute, consume, and uncompute as one lifecycle.' },
    { name: 'Scratch lifecycle', goal: 'Compare artifact-backed partial-product and guard cleanup obligations.' },
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
  'point-add-boundary': [
    { name: 'Boundary debugger', goal: 'Exercise random, doubling, inverse, accumulator-infinity, and lookup-infinity cases.' },
    { name: 'Artifact atlas', goal: 'Map equivalence artifacts to what they prove and what they do not prove.' },
  ],
  contribution: [
    { name: 'Contributor mission board', goal: 'Turn the course into a concrete patch with evidence requirements.' },
    { name: 'Claim audit drill', goal: 'Classify repo claims by the evidence they actually bind.' },
    { name: 'Course coverage audit', goal: 'Check how the course maps the original learning requirements.' },
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
        <div>
          <MathTex tex="P(0)=|a'|^2,\quad P(1)=|b'|^2" />
          <p>Angle can become visible only after the gate changes arrow lengths.</p>
        </div>
      </div>
    );
  }

  return null;
}

function OrientationStoryPanel() {
  return (
    <section className="orientation-story" data-testid="orientation-story" aria-label="Project proof orientation story">
      <article className="story-question">
        <h4>Start from an ordinary computer</h4>
        <p>
          A normal CPU step updates a bit string. At one instant memory might be
          {' '}<MathTex tex="0101" />; after an instruction it might be{' '}<MathTex tex="0111" />.
          The machine has memory, operations, intermediate states, and final readout.
        </p>
        <p>
          A quantum circuit keeps that same skeleton. The difference is that the
          memory is not one point. It is an amplitude vector, and each gate is a
          strict mathematical transformation of that vector before measurement
          returns ordinary bits.
        </p>
      </article>

      <OrientationModelVisual />

      <article className="story-rule orientation-state-rule">
        <div>
          <h4>What changes</h4>
          <p>
            Classical memory can be pictured as one selected label. Quantum memory is
            a weighted list of labels, written as
            {' '}<MathTex tex="|\psi\rangle=\sum_x \alpha_x|x\rangle" />. The labels
            are still bit strings; the new part is the amplitude attached to each one.
          </p>
          <p>
            Gates must preserve the total probability and remain reversible. That is
            why this repo keeps talking about wires, cleanup, and liveness instead of
            treating temporary values as disposable local variables.
          </p>
        </div>
        <div className="state-label-stack" aria-hidden="true">
          <span><b>classical</b><i>0101</i></span>
          <span><b>quantum</b><i>a|0000&gt; + b|0101&gt; + ...</i></span>
        </div>
      </article>

      <article className="story-question orientation-target">
        <h4>The concrete target</h4>
        <p>
          Given a public key <MathTex tex="Q" />, the hidden private number is
          {' '}<MathTex tex="d" />. For secp256k1 they are connected by
          {' '}<MathTex tex="Q=dG" />. The project is not trying to prove that quantum
          computers are scary in general; it is trying to prove the cost of one
          executable quantum circuit for recovering <MathTex tex="d" />.
        </p>
      </article>

      <article className="story-rule proof-chain-rule">
        <div>
          <h4>What would make the number believable</h4>
          <p>
            The chain must stay connected end to end: mathematical attack, executable
            circuit, semantic tests, primitive resource accounting, and checked
            artifacts. If a link summarizes away a wire, the final number can still
            look precise while no longer describing the circuit that was tested.
          </p>
        </div>
        <div className="proof-chain-mini" aria-hidden="true">
          <span>attack</span>
          <i />
          <span>circuit</span>
          <i />
          <span>resources</span>
          <i />
          <span>artifact</span>
        </div>
      </article>
    </section>
  );
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

function QubitStoryPanel() {
  return (
    <section className="qubit-story" data-testid="qubit-story" aria-label="Qubit amplitude and measurement story">
      <article className="story-question">
        <h4>Notation</h4>
        <p>
          A single qubit is one coherent state with two amplitudes:
          {' '}<MathTex tex="|\psi\rangle=a|0\rangle+b|1\rangle" />. The symbols
          {' '}<MathTex tex="a" /> and <MathTex tex="b" /> are complex numbers. For
          this course, a complex number just means an arrow in a flat plane: it has
          a length and a direction.
        </p>
        <QubitStepVisual stepIndex={0} />
      </article>

      <article className="story-rule qubit-probability-rule">
        <div>
          <h4>Probability rule</h4>
          <p>
            Direct measurement does not read the arrows as arrows. It samples outcome
            0 or outcome 1 using squared arrow lengths:
            {' '}<MathTex tex="P(0)=|a|^2" /> and <MathTex tex="P(1)=|b|^2" />.
            If both arrow lengths are <MathTex tex="1/\sqrt2" />, direct measurement
            gives a 50/50 split.
          </p>
        </div>
        <div className="mini-prob-bars" aria-hidden="true">
          <span>0 outcome</span>
          <i style={{ width: '50%' }} />
          <span>1 outcome</span>
          <i className="alt" style={{ width: '50%' }} />
        </div>
      </article>

      <article className="story-rule qubit-angle-rule">
        <div>
          <h4>Relative angle</h4>
          <p>
            Two states can have the same direct 50/50 measurement but different arrow
            directions. That direction is not private magic; it is circuit information
            that a later gate can use when it mixes the two amplitudes.
          </p>
          <p>
            This is the first reason a qubit is not just a probability coin: the coin
            remembers only chances, while the qubit also carries relative phase before
            measurement.
          </p>
        </div>
        <QubitStepVisual stepIndex={4} />
      </article>

      <article className="story-question">
        <h4>Measurement</h4>
        <p>
          Measurement samples one outcome and changes what remains. It is not a
          passive screenshot of both amplitudes. The next lesson therefore studies
          gates first: valid gates can turn relative angle into a changed probability
          before the measurement happens.
        </p>
      </article>
    </section>
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
          <span>four amplitudes, but generated from two separate one-qubit states</span>
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
            A Bell pair has only 00 and 11 branches. No pair of separate one-qubit
            descriptions can reproduce exactly that table.
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

      <article className="story-rule stabilizer-ledger-rule">
        <div>
          <h4>Compact does not mean classical</h4>
          <p>
            A stabilizer description is like a ledger of Pauli facts that remain true
            about the state. Clifford gates update that ledger in a structured way:
            X-type facts become other Pauli facts, Z-type facts become other Pauli
            facts, and correlations can still be recorded without expanding the full
            amplitude table.
          </p>
          <p>
            That is the source of the “cheap” label. Clifford circuits can still make
            superposition and entanglement; they are cheap because the bookkeeping stays
            compact and fault-tolerant implementations usually do not need magic-state
            injection for each row.
          </p>
        </div>
        <div className="stabilizer-ledger" aria-hidden="true">
          <div><span>before H</span><strong>Z fact</strong></div>
          <div><span>after H</span><strong>X fact</strong></div>
          <div><span>after CX</span><strong>parity fact</strong></div>
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

      <article className="story-rule magic-factory-rule">
        <div>
          <h4>Magic states behave like consumable fuel</h4>
          <p>
            In many fault-tolerant designs, a hard non-Clifford gate is implemented by
            preparing a special ancilla state, checking or distilling it to high enough
            quality, and consuming it through mostly Clifford circuitry. The algorithm
            row says “do a T-like step”; the hardware plan has to supply enough clean
            magic states at the right rate.
          </p>
          <p>
            That is why the repo tracks non-Clifford separately from total rows. It is
            not a moral ranking of gates; it is a proxy for a different factory-like
            resource bottleneck.
          </p>
        </div>
        <div className="magic-factory-flow" aria-hidden="true">
          <span>noisy magic</span>
          <i />
          <span>distill/check</span>
          <i />
          <span>consume in gate</span>
        </div>
      </article>

      <article className="story-rule clifford-universal-rule">
        <div>
          <h4>Why the repo does not report “all gates” as one number</h4>
          <p>
            Clifford-only circuits are special enough to have efficient stabilizer
            bookkeeping, but they are not enough for arbitrary reversible arithmetic.
            Add a non-Clifford ingredient such as T, CCZ, or Toffoli-style work and the
            gate set becomes powerful enough for general computation. That is exactly
            why the repo keeps a separate non-Clifford ledger instead of mixing every
            row into one undifferentiated gate count.
          </p>
        </div>
        <div className="proof-contract-list" aria-hidden="true">
          <span>Clifford: H, S, CX</span>
          <span>magic ingredient: T / CCZ / Toffoli</span>
          <span>arithmetic spends the magic ledger</span>
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

      <article className="story-rule qubit-name-rule">
        <div>
          <h4>“Qubit” names three different layers here</h4>
          <p>
            The repo uses logical qubit to mean an algorithm-level circuit wire after
            lowering and scheduling. Error correction uses logical qubit to mean one
            encoded quantum value protected across physical carriers. Hardware and
            Qiskit-style tooling may then expose a backend hardware qubit, which can be
            a bare physical qubit today or, in a fault-tolerant stack, an encoded qubit
            controlled behind the backend interface.
          </p>
          <p>
            Mixing those layers turns a useful algorithm number into a misleading
            hardware claim. The course keeps them separate on purpose.
          </p>
        </div>
        <div className="qubit-layer-cards" aria-hidden="true">
          <div><span>repo logical wire</span><strong>algorithm resource</strong></div>
          <div><span>QEC logical qubit</span><strong>encoded information</strong></div>
          <div><span>hardware qubit</span><strong>backend carrier</strong></div>
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

      <article className="story-rule code-parameter-rule">
        <div>
          <h4>Read code parameters as a hardware contract</h4>
          <p>
            Error-correcting codes are often summarized as <MathTex tex="[[n,k,d]]" />.
            The first number says how many physical data qubits the code uses, the
            second says how many logical qubits it protects, and the distance says how
            many errors are needed to silently turn one valid encoded state into another.
          </p>
          <p>
            This is why a repo result like “1,968 logical qubits” is not a device count.
            A physical estimate still has to choose a code family, distance, syndrome
            schedule, layout, decoder, and magic factories.
          </p>
        </div>
        <div className="code-parameter-card" aria-hidden="true">
          <span><MathTex tex="n" /> physical data qubits</span>
          <span><MathTex tex="k" /> protected logical qubits</span>
          <span><MathTex tex="d" /> distance / silent-error barrier</span>
        </div>
      </article>

      <article className="story-rule qec-service-rule">
        <div>
          <h4>Error correction is a running service loop</h4>
          <p>
            A protected computation does not just allocate a larger register once.
            Physical data qubits carry the encoded state, check qubits extract syndrome
            information, measurements feed a classical decoder, and the decoder updates
            the correction frame while the quantum computation continues.
          </p>
          <p>
            That service loop is why a physical estimate needs measurement rounds,
            decoder latency, connectivity, and scheduling assumptions in addition to
            the algorithmic live-qubit count.
          </p>
        </div>
        <div className="qec-service-loop" aria-hidden="true">
          <span>data qubits</span>
          <i />
          <span>syndrome checks</span>
          <i />
          <span>decoder</span>
          <i />
          <span>updated frame</span>
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

      <article className="story-rule eigenphase-rule">
        <div>
          <h4>The exact statement is an eigenphase</h4>
          <p>
            Phase estimation starts from a unitary operation and a state that comes back
            to itself except for phase:
          </p>
          <p className="capacity-equation">
            <MathTex tex="U|\psi\rangle=e^{2\pi i\theta}|\psi\rangle" />
          </p>
          <p>
            The goal is to learn the ordinary binary digits of <MathTex tex="\theta" />.
            If the phase is exactly <MathTex tex="y/2^m" />, an ideal inverse QFT on{' '}
            <MathTex tex="m" /> control qubits maps the phase pattern to the readable
            label <MathTex tex="|y\rangle" />.
          </p>
        </div>
        <div className="eigenphase-card" aria-hidden="true">
          <span>state returns</span>
          <i />
          <span>phase remains</span>
          <i />
          <span>bits reveal it</span>
        </div>
      </article>

      <article className="story-rule phase-kickback-rule">
        <div>
          <h4>Phase kickback moves the angle onto the control</h4>
          <p>
            Put one control qubit in a split and apply controlled-<MathTex tex="U" /> to
            an eigenstate target. The <MathTex tex="|0\rangle" /> branch skips the
            operation. The <MathTex tex="|1\rangle" /> branch applies{' '}
            <MathTex tex="U" />, and because the target is an eigenstate, the target
            returns while that branch gains phase <MathTex tex="e^{2\pi i\theta}" />.
          </p>
          <p>
            The target did not reveal the answer. The useful information is now a
            relative angle between the two control branches, where later controlled
            powers can build a readable binary rhythm.
          </p>
        </div>
        <div className="phase-kickback-card" aria-hidden="true">
          <div>
            <span>control 0 branch</span>
            <strong>target unchanged</strong>
          </div>
          <div>
            <span>control 1 branch</span>
            <strong>same target + phase</strong>
          </div>
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

      <article className="story-rule phase-approx-rule">
        <div>
          <h4>Approximate phases produce peaks, not certainty</h4>
          <p>
            The cleanest story assumes <MathTex tex="\theta=y/2^m" /> exactly. Real
            algorithms use a finite number of control bits to approximate a phase. Then
            the inverse QFT produces a distribution concentrated near the closest{' '}
            <MathTex tex="m" />-bit fractions instead of one guaranteed label.
          </p>
          <p>
            More precision bits sharpen that distribution but also require more
            controlled powers, so precision is part of the resource contract.
          </p>
        </div>
        <div className="phase-approx-strip" aria-hidden="true">
          <div>
            <span>exact binary phase</span>
            <strong>one sharp label</strong>
          </div>
          <div>
            <span>between labels</span>
            <strong>nearby peaks</strong>
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

      <article className="story-rule secp-domain-rule">
        <div>
          <h4>secp256k1 has two modular worlds</h4>
          <p>
            The curve equation lives over a prime field <MathTex tex="\mathbb{F}_p" />:
            point coordinates are residues modulo <MathTex tex="p" />. The private key
            scalar lives modulo the base-point order <MathTex tex="n" />. Both are about
            256 bits, but they are not the same register type in the circuit.
          </p>
          <p>
            Mixing those worlds is a common beginner mistake. The oracle combines scalar
            labels modulo <MathTex tex="n" />, then executes point additions whose
            coordinate arithmetic is modulo <MathTex tex="p" />.
          </p>
        </div>
        <div className="proof-contract-list" aria-hidden="true">
          <span>scalar d, a, b: modulo n</span>
          <span>coordinates x, y: modulo p</span>
          <span>point-add leaf bridges them</span>
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
          <p className="capacity-equation">
            <MathTex tex="f_d(a,b)=aG+bQ=(a+bd)G" />
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

      <article className="story-rule sample-to-key-rule">
        <div>
          <h4>A Fourier sample becomes an equation for d</h4>
          <p>
            The oracle turns every pair <MathTex tex="(a,b)" /> into a point label
            controlled by one scalar value <MathTex tex="a+bd" />. The point output
            can be uncomputed, but the equal-output structure remains as phase. The
            hidden direction is the move that does not change that label:
          </p>
          <p className="capacity-equation">
            <MathTex tex="(a,b)\mapsto(a+d,b-1),\quad (a+d)+(b-1)d=a+bd" />
          </p>
          <p>
            Fourier readout does not return the direction itself. It tends to return a
            sample gradient <MathTex tex="(u,v)" /> whose wave is flat along that
            direction. Flat means the modular dot product vanishes:
          </p>
          <p className="capacity-equation">
            <MathTex tex="u d-v\equiv 0\pmod n" />
          </p>
          <p>
            If <MathTex tex="u" /> has an inverse modulo <MathTex tex="n" />, the
            sample gives <MathTex tex="d\equiv v u^{-1}\pmod n" />. Real attacks repeat
            the sampling because a measured label is a probabilistic clue, not a direct
            readout of the secret register.
          </p>
        </div>
        <div className="sample-key-bridge-card" aria-hidden="true">
          <span>
            <strong>Oracle label</strong>
            <em><MathTex tex="a+bd" /></em>
          </span>
          <i />
          <span>
            <strong>Same-label move</strong>
            <em><MathTex tex="(d,-1)" /></em>
          </span>
          <i />
          <span>
            <strong>Fourier sample</strong>
            <em><MathTex tex="(u,v)" /></em>
          </span>
          <i />
          <span>
            <strong>Solve</strong>
            <em><MathTex tex="d=v\cdot u^{-1}\pmod n" /></em>
          </span>
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

function CoordinatesStoryPanel() {
  return (
    <section className="coordinate-story" data-testid="coordinate-story" aria-label="Coordinate and field-slot story">
      <article className="story-question">
        <h4>Coordinates are field elements, not plain integers</h4>
        <p>
          secp256k1 points use coordinates in a prime field. Adding, subtracting,
          multiplying, and dividing all happen modulo <MathTex tex="p" />. Division is
          multiplication by a modular inverse, which is why the point-add formula cares
          so much about avoiding inversions in the hot loop.
        </p>
        <div className="proof-contract-list" aria-hidden="true">
          <span>x, y live in F_p</span>
          <span>division uses an inverse mod p</span>
          <span>field slot = 256 logical wires</span>
        </div>
      </article>

      <article className="story-question">
        <h4>The same curve point can have several names</h4>
        <p>
          An affine point writes the location directly as <MathTex tex="(x,y)" />.
          A projective-style point adds a scale coordinate. In the toy chart below,
          {' '}<MathTex tex="(X,Y,Z)" /> means the same affine point after multiplying
          by <MathTex tex="Z^{-1}" />. Many triples can therefore name one point.
        </p>
        <div className="coordinate-name-strip" aria-hidden="true">
          <span><MathTex tex="(5,1)" /> affine</span>
          <i />
          <span><MathTex tex="(15,3,3)" /></span>
          <span><MathTex tex="(8,5,5)" /></span>
          <span><MathTex tex="(12,11,16)" /></span>
        </div>
      </article>

      <article className="story-rule coordinate-slot-rule">
        <div>
          <h4>A coordinate name is not the same as counted storage</h4>
          <p>
            The math may say “this triple names the same point,” but the circuit still
            has to carry the current bits of <MathTex tex="X" />, <MathTex tex="Y" />,
            and <MathTex tex="Z" /> while the formula runs. Each live field element is
            a bundle of 256 quantum wires that must have an owner and a death row.
          </p>
          <p>
            Projective coordinates are therefore not compression. They are a trade:
            keep extra scale storage live now so the hot loop can avoid repeated
            reversible inversions.
          </p>
        </div>
        <div className="coordinate-slot-contract" aria-hidden="true">
          <div>
            <span>math object</span>
            <strong>one curve point</strong>
          </div>
          <div>
            <span>circuit storage</span>
            <strong>X, Y, Z field slots</strong>
          </div>
          <div>
            <span>audit question</span>
            <strong>who owns 3 * 256 wires?</strong>
          </div>
        </div>
      </article>

      <article className="story-rule coordinate-overwrite-rule">
        <div>
          <h4>“Overwrite” means reversible in-place update</h4>
          <p>
            Classical code can assign a new value into a variable and forget the old
            one. A closed quantum circuit cannot silently erase a live field element:
            if two possible old values lead to the same new state, there is no inverse
            operation that can reconstruct which branch existed.
          </p>
          <p>
            The allowed version is an in-place reversible map over the lane plus its
            still-live controls. For a toy scalar row, the engine may reuse a lane only
            when the new value and controls determine the old value:
          </p>
          <p className="capacity-equation">
            <MathTex tex="Y_3=LC+NM,\quad L\ne0\Rightarrow C=L^{-1}(Y_3-NM)" />
          </p>
          <p>
            The zero-lift guard exists because <MathTex tex="L=0" /> would otherwise
            collapse every old <MathTex tex="C" /> to the same output. That is why an
            overwrite claim needs a permutation contract, edge-case replay, and counted
            owner capacity for every still-live field slot.
          </p>
        </div>
        <div className="overwrite-law-card" aria-hidden="true">
          <div>
            <strong>Not allowed</strong>
            <span>many old C values {'->'} one output</span>
            <em>erases branch identity</em>
          </div>
          <div>
            <strong>Allowed</strong>
            <span>(C, controls) {'->'} (Y3, controls)</span>
            <em>inverse recovers C</em>
          </div>
          <div>
            <strong>Audit</strong>
            <span>permutation + replay + owner capacity</span>
            <em>same lane, no free wire</em>
          </div>
        </div>
      </article>

      <article className="story-rule coordinate-division-rule">
        <div>
          <h4>Why avoid division in the hot loop?</h4>
          <p>
            A direct affine point-add computes a slope such as{' '}
            <MathTex tex="\lambda=(y_2-y_1)/(x_2-x_1)" />. Over a finite field,
            that division means a modular inverse. Reversible inversion is a large
            arithmetic subcircuit, so repeatedly paying it inside the oracle is costly.
          </p>
          <p>
            Projective formulas keep scale information live and trade the hot inverse
            for multiply/add/subtract work. The final inverse is delayed until the
            circuit actually needs to leave projective space.
          </p>
        </div>
        <div className="coordinate-path-compare" aria-hidden="true">
          <div>
            <strong>affine path</strong>
            <span>slope</span>
            <b>inverse now</b>
          </div>
          <div>
            <strong>projective path</strong>
            <span>carry scale</span>
            <b>multiply now</b>
          </div>
        </div>
      </article>

      <article className="story-rule infinity-rule">
        <div>
          <h4>Infinity is not a footnote</h4>
          <p>
            Elliptic-curve addition has an identity element, the point at infinity.
            A counted point-add boundary must handle ordinary additions, doubling,
            inverse pairs, accumulator infinity, and lookup infinity with the same
            executable contract.
          </p>
          <p>
            If one edge case secretly needs another field register, the peak-qubit
            claim has changed. That is why the repo tests these cases at the same
            boundary that the resource engine counts.
          </p>
        </div>
        <div className="edge-case-stack" aria-hidden="true">
          <span>random add</span>
          <span>doubling</span>
          <span>inverse pair</span>
          <span>accumulator infinity</span>
          <span>lookup infinity</span>
        </div>
      </article>

      <div className="story-motion-grid">
        <article>
          <h4>Field slot</h4>
          <p>
            A secp256k1 coordinate is a 256-bit field element. One live{' '}
            <MathTex tex="X" />, <MathTex tex="Y" />, or <MathTex tex="Z" /> register
            is therefore 256 logical quantum wires, not one UI value.
          </p>
          <div className="slot-width-meter" aria-hidden="true"><span /></div>
        </article>
        <article>
          <h4>Live interval</h4>
          <p>
            A slot counts from the row where its value is created until the row where
            it is uncomputed, measured, or overwritten by a proven reversible map.
          </p>
          <div className="slot-lifetime-sketch" aria-hidden="true">
            <span>birth</span>
            <i />
            <span>last use</span>
          </div>
        </article>
        <article>
          <h4>Overwrite audit</h4>
          <p>
            Reusing a coordinate lane is allowed only when the engine proves the
            transformation is reversible at the boundary. A name change alone is not
            a quantum overwrite proof.
          </p>
          <div className="overwrite-warning-pill" aria-hidden="true">owner + inverse required</div>
        </article>
      </div>

      <article className="story-question">
        <h4>What to do in the labs</h4>
        <p>
          First move the scale slider and verify that different triples normalize to
          the same affine point. Then use the overwrite and boundary labs to ask the
          resource question: which coordinate-sized values are live at the same time,
          and which edge cases execute the same counted contract?
        </p>
      </article>
    </section>
  );
}

function LookupQroamStoryPanel({ data }: { data: typeof projectData }) {
  const entries = data.compilerParameters.windowing.foldedMagnitudeDomain;
  const chunkBits = data.compilerParameters.reusableChunkPolicy.chunkBits;
  const standardK = data.compilerParameters.lookupPolicy.standardQroamcleanBlockSize;
  const fullCoordinateJunkAtK16 = (16 - 1) * data.compilerParameters.field.fieldBits;

  return (
    <section className="lookup-story" data-testid="lookup-story" aria-label="QROAM lookup accounting story">
      <article className="story-question">
        <h4>A table lookup is still a circuit</h4>
        <p>
          Classical code can write <MathTex tex="table[address]" /> and let the
          machine hide the memory system. A quantum address may be in superposition,
          so the lookup must coherently route the selected data into a target register
          without measuring which row was chosen.
        </p>
        <div className="qroam-flow-strip" aria-hidden="true">
          <span>address register</span>
          <i />
          <span>selection network</span>
          <i />
          <span>target chunk</span>
          <i />
          <span>cleanup</span>
        </div>
      </article>

      <article className="story-rule qroam-cost-rule">
        <div>
          <h4>What QROAMClean buys and what it spends</h4>
          <p>
            A standard clean-ancilla QROAM lookup over <MathTex tex="N" /> entries
            and <MathTex tex="b" /> target bits trades Toffoli work against workspace:
            compute cost <MathTex tex="N/K+(K-1)b" />, cleanup cost{' '}
            <MathTex tex="N/K+(K-1)" />, and <MathTex tex="(K-1)b" /> junk bits.
          </p>
          <p>
            The current checked chunk policy gives <MathTex tex={`N=${entries}`} /> and{' '}
            <MathTex tex={`b=${chunkBits}`} /> for this lab. The default public block
            size is <MathTex tex={`K=${standardK}`} />.
          </p>
        </div>
        <div className="qroam-parameter-card" aria-hidden="true">
          <div><span>entries</span><strong>{formatInt(entries)}</strong></div>
          <div><span>chunk bits</span><strong>{chunkBits}</strong></div>
          <div><span>default K</span><strong>{standardK}</strong></div>
        </div>
      </article>

      <article className="story-rule qroam-data-rule">
        <div>
          <h4>The selected coordinate bits are real data</h4>
          <p>
            A folded lookup address has structure, but the table contents are
            precomputed curve-coordinate constants. A valid lowering must actually
            select those data bits into a counted target or into a proven alias. It is
            not enough to decode address predicates and call the output free.
          </p>
          <p>
            This is the exact class of bug the course wants learners to catch: the same
            lookup model must pay for address controls, data selection, target capacity,
            junk workspace, and cleanup.
          </p>
        </div>
        <div className="proof-contract-list" aria-hidden="true">
          <span>address predicates</span>
          <span>coordinate constants</span>
          <span>counted target bits</span>
          <span>cleanup path</span>
        </div>
      </article>

      <article className="story-rule qroam-select-rule">
        <div>
          <h4>Address decoding is not table selection</h4>
          <p>
            A 15-bit address can mark one of 32,768 rows, but marking the row is not
            the same as loading its coordinate constant. The lowering also needs a
            reversible data-selection layer that combines the row predicates with the
            precomputed table bits.
          </p>
          <p>
            For an arbitrary coordinate table, those data bits behave like constants
            with no useful algebraic pattern. A valid resource model must therefore
            count the select work and the output capacity for the exact streamed or
            full-width construction it uses.
          </p>
        </div>
        <div className="qroam-select-stack" aria-hidden="true">
          <div><span>1</span><strong>decode address</strong><em>which row?</em></div>
          <div><span>2</span><strong>select data bits</strong><em>which constants?</em></div>
          <div><span>3</span><strong>count target</strong><em>where do bits live?</em></div>
        </div>
      </article>

      <article className="story-rule qroam-consistency-rule">
        <div>
          <h4>The consistency trap</h4>
          <p>
            You cannot use a full-width QROAM gate formula and then keep only a
            tiny one-bit latch in the qubit count. If the lookup selects a full
            field-sized coordinate with <MathTex tex="K=16" />, the junk registers
            alone cost <MathTex tex={`15\\cdot256=${fullCoordinateJunkAtK16}`} /> bits.
          </p>
          <p>
            If you instead stream one bit at a time, the workspace can be small, but
            the lookup cost must be paid per bit stream. Those are different models,
            and the repo must keep them separate.
          </p>
        </div>
        <div className="qroam-model-split" aria-hidden="true">
          <div><strong>full target</strong><span>amortize bits, count junk</span></div>
          <div><strong>bit stream</strong><span>small target, repeat lookup</span></div>
        </div>
      </article>

      <div className="story-motion-grid">
        <article>
          <h4>Address controls</h4>
          <p>The row selector is live quantum state. It chooses rows without being measured.</p>
          <span className="story-token">selection bits</span>
        </article>
        <article>
          <h4>Target lane</h4>
          <p>The selected value must land in a counted register or in a proven alias of an existing owner.</p>
          <span className="story-token">not free output</span>
        </article>
        <article>
          <h4>Uncompute</h4>
          <p>Selection junk must be kept long enough to reverse or measured-uncompute the lookup path.</p>
          <span className="story-token">cleanup bound</span>
        </article>
      </div>

      <article className="story-question">
        <h4>What to do in the labs</h4>
        <p>
          First flip address bits and identify which register is address, target,
          workspace, and cleanup. Then move <MathTex tex="K" /> in the tradeoff dial
          and watch the same formula change gates and workspace together.
        </p>
      </article>
    </section>
  );
}

function ProgrammingStoryPanel() {
  return (
    <section className="programming-story" data-testid="programming-story" aria-label="Tiny circuit programming story">
      <article className="story-question">
        <h4>A circuit program is a contract over wires</h4>
        <p>
          A classical program can hide many details behind a line like{' '}
          <code>acc ^= x &amp; y</code>. A quantum circuit cannot treat that as a
          black box. The compiler must say which wires hold <MathTex tex="x" /> and{' '}
          <MathTex tex="y" />, where the temporary product lands, how the accumulator
          changes, and how the temporary is cleaned.
        </p>
        <div className="program-contract-split" aria-hidden="true">
          <div><span>classical expression</span><strong>acc ^= x & y</strong></div>
          <i />
          <div><span>primitive rows</span><strong>compute, consume, uncompute</strong></div>
        </div>
      </article>

      <article className="story-rule row-branch-rule">
        <div>
          <h4>A row acts on the whole quantum state</h4>
          <p>
            When the editor shows <code>CX q0 q1</code>, do not picture one classical
            branch being edited. The row is a reversible rule applied coherently to
            every amplitude branch at once. If <MathTex tex="q0" /> is in a split, the
            branch where <MathTex tex="q0=0" /> leaves <MathTex tex="q1" /> alone, and
            the branch where <MathTex tex="q0=1" /> flips <MathTex tex="q1" />.
          </p>
          <p>
            That is why operands matter. A wrong operand is not a local typo; it changes
            the transformation over the full state vector the later interference depends on.
          </p>
        </div>
        <div className="row-branch-card" aria-hidden="true">
          <div><span>q0 = 0 branch</span><strong>q1 unchanged</strong></div>
          <div><span>q0 = 1 branch</span><strong>q1 flips</strong></div>
          <div><span>same row</span><strong>one coherent transform</strong></div>
        </div>
      </article>

      <article className="story-rule reversible-half-adder-rule">
        <div>
          <h4>The quantum version keeps the inputs</h4>
          <p>
            A classical half-adder computes sum with XOR and carry with AND. The AND
            output alone loses information: three different inputs produce carry 0.
            A reversible circuit keeps the input wires and writes sum or carry into
            helper targets initialized to <MathTex tex="|0\rangle" />. That is why a
            small arithmetic sentence turns into rows with sources, targets, and cleanup.
          </p>
        </div>
        <div className="half-adder-compare" aria-hidden="true">
          <div><span>classical</span><strong>(x, y) becomes sum, carry</strong></div>
          <div><span>reversible</span><strong>(x, y, 0, 0) becomes (x, y, sum, carry)</strong></div>
        </div>
      </article>

      <article className="story-rule row-schema-rule">
        <div>
          <h4>Rows are the smallest auditable unit</h4>
          <p>
            The toy DSL is deliberately small: <code>H</code>, <code>X</code>,{' '}
            <code>S</code>, <code>CX</code>, <code>CCX</code>, and <code>M</code>.
            The important skill is not memorizing these names. It is learning to read
            every row as <em>operation + operands + cost + lifecycle effect</em>.
          </p>
          <p>
            Once a row has concrete operands, a test can execute it, the liveness engine
            can derive births and deaths, and a resource certificate can count it.
          </p>
        </div>
        <div className="row-schema-strip" aria-hidden="true">
          <span>op</span>
          <span>operands</span>
          <span>owner</span>
          <span>cost</span>
          <span>cleanup</span>
        </div>
      </article>

      <article className="story-rule stream-lifecycle-rule">
        <div>
          <h4>Valid rows are not the same as a clean stream</h4>
          <p>
            A parser can prove that every line uses a known operation with the right
            number of operands. That is only the first gate. The next gate asks what
            each row did to wire lifetimes: did it create a scratch target, consume its
            effect, and later erase the same target with the same controls?
          </p>
          <p>
            The repo’s resource numbers should be downstream of that lifecycle audit.
            Otherwise a program can be syntactically valid, executable for a toy state,
            and still wrong as a resource claim because scratch remains live.
          </p>
        </div>
        <div className="stream-audit-card" aria-hidden="true">
          <span>parse rows</span>
          <i />
          <span>derive lifetimes</span>
          <i />
          <span>prove cleanup</span>
          <i />
          <span>count peak</span>
        </div>
      </article>

      <article className="story-rule parser-rule">
        <div>
          <h4>A rejected row is a feature</h4>
          <p>
            Unknown operations must fail loudly. If a compiler silently accepts a row
            it cannot lower, the final resource number may still look exact while no
            executable circuit exists behind it.
          </p>
          <p>
            That is why the lab asks you to type a bad opcode first. The useful habit
            is to distrust summaries until the parser, row table, costs, and cleanup
            checks all describe the same object.
          </p>
        </div>
        <div className="parser-fail-card" aria-hidden="true">
          <span>BAD q0</span>
          <strong>reject before counting</strong>
        </div>
      </article>

      <div className="story-motion-grid">
        <article>
          <h4>Primitive row</h4>
          <p>One scheduled operation touching named wires at one point in time.</p>
          <span className="story-token">CCX q0 q1 q2</span>
        </article>
        <article>
          <h4>Wire set</h4>
          <p>The set of names touched by the program becomes the first liveness surface.</p>
          <span className="story-token">q0, q1, q2</span>
        </article>
        <article>
          <h4>Cost surface</h4>
          <p>Clifford rows can be cheap while Toffoli-like rows spend non-Clifford budget.</p>
          <span className="story-token">CCX = 1 toy NC</span>
        </article>
      </div>

      <article className="story-question">
        <h4>What to do in the labs</h4>
        <p>
          Build a tiny row table first, then edit the DSL until it rejects and recovers.
          When the parser says valid, compare rows, wires, and non-Clifford total. Then
          continue to cleanup: a valid row stream is still incomplete if it leaves scratch.
        </p>
      </article>
    </section>
  );
}

function CleanupStoryPanel({ data }: { data: typeof projectData }) {
  const lifecycle = data.modularMultiplierLifecycle;
  const sourceUncompute = data.modularAccumulator.sourceUncompute;
  const provenCleanup = sourceUncompute.cleanupStatusCounts.source_uncompute_cleanup_ccx_proven ?? 0;
  const missingGuardCleanup = sourceUncompute.cleanupStatusCounts.missing_source_controls_for_cleanup ?? 0;

  return (
    <section className="cleanup-story-panel" data-testid="cleanup-story" aria-label="Uncomputation and scratch lifecycle story">
      <article className="story-question">
        <h4>Scratch becomes garbage when its story stops</h4>
        <p>
          A temporary value is allowed while it has a purpose. The problem starts when
          the circuit computes it, uses the name in a summary, and then never proves
          where the quantum state went. In a quantum subroutine, leftover scratch can
          remain correlated with the output and block the interference the larger
          algorithm needs.
        </p>
        <div className="scratch-story-strip" aria-hidden="true">
          <span>compute scratch</span>
          <i />
          <span>use effect</span>
          <i />
          <span>uncompute scratch</span>
        </div>
      </article>

      <article className="story-rule bennett-rule">
        <div>
          <h4>The safe pattern is compute, consume, reverse</h4>
          <p>
            Bennett-style reversible computation keeps enough information to run the
            computation backward. For a circuit leaf, that usually means compute a
            temporary, consume its useful effect into a counted destination, then replay
            the same source controls to return the temporary target to <MathTex tex="|0\rangle" />.
          </p>
          <p>
            Cleanup is therefore a semantic proof, not a formatting preference. If the
            source controls are not still available, the inverse row is not justified.
          </p>
        </div>
        <div className="bennett-cycle" aria-hidden="true">
          <span>forward</span>
          <span>copy or consume output</span>
          <span>reverse</span>
        </div>
      </article>

      <article className="story-rule cleanup-dependency-rule">
        <div>
          <h4>Cleanup can keep sources live longer</h4>
          <p>
            To erase a temporary value, the inverse needs the same source controls that
            created it. If those sources were overwritten or freed too early, the cleanup
            row is only a label, not an executable inverse.
          </p>
          <p>
            This is a qubit-counting issue, not only a correctness issue. A schedule
            that delays cleanup may have to keep the sources, target, and destination
            live together, so peak liveness can rise even when the algebraic formula is
            unchanged.
          </p>
        </div>
        <div className="cleanup-dependency-card" aria-hidden="true">
          <span>sources stay available</span>
          <i />
          <span>scratch can be erased</span>
          <i />
          <span>live peak is recomputed</span>
        </div>
      </article>

      <div className="story-motion-grid">
        <article>
          <h4>Missing cleanup</h4>
          <p>The scratch wire stays live. It must still be counted and may carry unwanted correlation.</p>
          <div className="audit-fail">garbage live</div>
        </article>
        <article>
          <h4>Wrong cleanup</h4>
          <p>An inverse using different controls can change the function instead of erasing scratch.</p>
          <div className="audit-fail">source mismatch</div>
        </article>
        <article>
          <h4>Proven cleanup</h4>
          <p>Same sources, same target, inverse action, and a live interval ending at cleanup.</p>
          <div className="audit-pass">scratch returns to zero</div>
        </article>
      </div>

      <article className="story-rule artifact-cleanup-rule">
        <div>
          <h4>How this maps to the repo blocker</h4>
          <p>
            The modular multiplier lifecycle currently reports{' '}
            {formatInt(lifecycle.currentStream.scratchObservationCount)} scratch
            observations in the current stream and status{' '}
            <code>{lifecycle.currentStream.physicalLifecycleStatus}</code>. The candidate
            lifecycle model requires {formatInt(lifecycle.streamedCandidate.requiredConsumeEvents)}
            {' '}consume events and {formatInt(lifecycle.streamedCandidate.requiredCleanupEvents)}
            {' '}cleanup events.
          </p>
          <p>
            The source-uncompute artifact proves {formatInt(provenCleanup)} cleanup rows,
            but {formatInt(missingGuardCleanup)} guard cleanup rows still lack source controls.
          </p>
        </div>
        <div className="cleanup-artifact-numbers" aria-hidden="true">
          <div><span>proven</span><strong>{formatInt(provenCleanup)}</strong></div>
          <div><span>guard gap</span><strong>{formatInt(missingGuardCleanup)}</strong></div>
          <div><span>serialized temp peak</span><strong>{formatInt(lifecycle.streamedCandidate.peakTemporaryAndWiresIfSerialized)}</strong></div>
        </div>
      </article>

      <article className="story-question">
        <h4>What to do in the labs</h4>
        <p>
          First make the small cleanup puzzle pass by adding the matching uncompute
          row. Then inspect the scratch lifecycle lab and switch from partial-product
          rows to guard rows. The lesson is the same at both scales: cleanup needs
          source controls, not just an optimistic label.
        </p>
      </article>
    </section>
  );
}

function ModularLoweringStoryPanel({ data }: { data: typeof projectData }) {
  const accumulator = data.modularAccumulator;
  const fieldBits = data.compilerParameters.field.fieldBits;
  const grid = accumulator.carrySave.singleGrid;
  const allGrids = accumulator.carrySave.allGrids;
  const fullAdder = accumulator.fullAdderContract;
  const sourceUncompute = accumulator.sourceUncompute;
  const layerSamples = grid.layers.slice(0, 6);
  const provenCleanup = sourceUncompute.cleanupStatusCounts.source_uncompute_cleanup_ccx_proven;
  const missingGuardCleanup = sourceUncompute.cleanupStatusCounts.missing_source_controls_for_cleanup;

  return (
    <section className="modular-lowering-story" data-testid="modular-lowering-story" aria-label="Modular arithmetic lowering story">
      <article className="story-question">
        <h4>A tiny formula becomes a large reversible machine</h4>
        <p>
          The algebra says <MathTex tex="z=x\cdot y \bmod p" />. A circuit cannot
          simply write that sentence into a register. It has to create bit products,
          add them into columns, fold the high columns back into the field range, and
          erase the temporary evidence without changing the answer.
        </p>
        <div className="modular-pipeline-strip" aria-hidden="true">
          <span><MathTex tex={`${fieldBits}`} />-bit inputs</span>
          <i />
          <span>bit product grid</span>
          <i />
          <span>column accumulator</span>
          <i />
          <span>fold + cleanup</span>
        </div>
      </article>

      <article className="story-rule modular-grid-rule">
        <div>
          <h4>The first expansion is the product grid</h4>
          <p>
            One schoolbook <MathTex tex={`${fieldBits}`} />-bit multiply exposes{' '}
            <MathTex tex={`${fieldBits}\\cdot${fieldBits}=${grid.initialPartialProductBits}`} />
            {' '}one-bit product obligations before the accumulator can compress them.
            The current artifact has {formatInt(accumulator.carrySave.schoolbookGridCount)}
            {' '}schoolbook grids and {formatInt(allGrids.partial_product_rows)}
            {' '}partial-product consume rows.
          </p>
          <p>
            Each product bit is a temporary quantum wire unless it is consumed into a
            counted accumulator and then uncomputed from the same source controls.
          </p>
        </div>
        <div className="modular-number-stack" aria-hidden="true">
          <div><span>one grid products</span><strong>{formatInt(grid.initialPartialProductBits)}</strong></div>
          <div><span>all consume rows</span><strong>{formatInt(allGrids.partial_product_rows)}</strong></div>
          <div><span>source cleanup rows</span><strong>{formatInt(sourceUncompute.rowCount)}</strong></div>
        </div>
      </article>

      <article className="story-rule product-obligation-rule">
        <div>
          <h4>One active product cell is already a lifecycle</h4>
          <p>
            A product bit is not just a dot in the grid. The row stream needs a target
            where <MathTex tex="x_i\wedge y_j" /> is born, a consume row that adds its
            effect into the correct output column, and a cleanup row that uses the same
            <MathTex tex="x_i" /> and <MathTex tex="y_j" /> controls to erase the target.
          </p>
          <p>
            Only after that lifecycle is explicit can the engine ask where the temporary
            was live, which owner paid for it, and whether it overlapped the accumulator
            at the peak row.
          </p>
        </div>
        <div className="product-obligation-card" aria-hidden="true">
          <span>birth: CCX controls {'->'} temp</span>
          <i />
          <span>use: add temp into column</span>
          <i />
          <span>death: inverse CCX</span>
          <i />
          <span>count: owner + live interval</span>
        </div>
      </article>

      <article className="story-rule modular-fold-rule">
        <div>
          <h4>Modulo reduction is not an after-the-fact note</h4>
          <p>
            In ordinary code, it is tempting to say “multiply, then reduce mod{' '}
            <MathTex tex="p" />.” In a reversible circuit, the high columns of the
            product are quantum data while they exist. They must be folded into the
            field range by explicit rows, with carries and cleanup tracked.
          </p>
          <p>
            The output cannot simply forget high bits, because forgetting is many-to-one.
            The lowering needs a reversible route that preserves enough information to
            uncompute temporary evidence after the field result has been accumulated.
          </p>
        </div>
        <div className="modular-fold-card" aria-hidden="true">
          <div><span>high columns</span><strong>still quantum data</strong></div>
          <div><span>fold rows</span><strong>explicit reversible work</strong></div>
          <div><span>cleanup</span><strong>remove temporary evidence</strong></div>
        </div>
      </article>

      <article className="story-rule carry-compression-rule">
        <div>
          <h4>Carry-save compression reduces height, not obligations</h4>
          <p>
            A full-adder cell turns three column bits into a sum bit and a carry bit.
            In this artifact one embedded cell costs{' '}
            {fullAdder.primitiveCountsPerCell.ccx} CCX and{' '}
            {fullAdder.primitiveCountsPerCell.cx} CX, and the candidate stream contains{' '}
            {formatInt(fullAdder.totals.full_adder_cell_count)} such cells.
          </p>
          <p>
            The important audit question is not only “how many adders?” It is also
            “where did the old inputs, sum wires, carry wires, and cleanup controls
            live while this was happening?”
          </p>
        </div>
        <div className="carry-layer-sparkline" aria-label="Carry-save live bit samples">
          {layerSamples.map((layer) => (
            <span key={layer.layer_index}>
              <b>L{layer.layer_index}</b>
              <i style={{ width: `${Math.max(12, (layer.live_column_bits_after_layer / layerSamples[0].live_column_bits_after_layer) * 100)}%` }} />
              <strong>{formatInt(layer.live_column_bits_after_layer)}</strong>
            </span>
          ))}
        </div>
      </article>

      <div className="story-card-grid">
        <article>
          <strong>Rows exist</strong>
          <p>
            The row stream has {formatInt(accumulator.rowStream.rowCount)} obligations
            across {formatInt(accumulator.rowStream.segmentCount)} segments.
          </p>
          <span className="story-token">{accumulator.rowStream.status}</span>
        </article>
        <article>
          <strong>Gates are partly known</strong>
          <p>
            The full-adder stream contributes {formatInt(accumulator.fullAdderStream.nonCliffordCount)}
            {' '}CCX, but it is not yet the global public resource stream.
          </p>
          <span className="story-token">{accumulator.fullAdderStream.status}</span>
        </article>
        <article>
          <strong>Cleanup still gates promotion</strong>
          <p>
            {formatInt(provenCleanup)} cleanup rows are proven; {formatInt(missingGuardCleanup)}
            {' '}guard rows still lack exposed source controls.
          </p>
          <span className="story-token">{sourceUncompute.status}</span>
        </article>
      </div>

      <article className="story-question">
        <h4>How to read the labs</h4>
        <p>
          Start with the small product grid to feel why multiplication creates many
          one-bit temporary products. Then open accumulator lowering: the lesson is
          not that the candidate is useless, but that promotion requires replacing
          every obligation row with exact primitive gates, owners, liveness, and cleanup.
        </p>
      </article>
    </section>
  );
}

function OwnerCapacityStoryPanel({ data }: { data: typeof projectData }) {
  const strict = data.strictFormula;
  const guard = data.zeroLiftGuard;
  const correctedTotal = strict.reconstructed_total + guard.gap.missing_logical_qubits_under_clean_ladder;

  return (
    <section className="owner-capacity-story" data-testid="owner-capacity-story" aria-label="Owner capacity audit story">
      <article className="story-question">
        <h4>An owner is a budget, not a nickname</h4>
        <p>
          A wire group is not counted just because a file writes an owner name next
          to it. The engine has to derive when the group is live, assign it to exactly
          one owner, sum all concurrently live widths for that owner, and compare the
          peak load with the owner&apos;s logical-qubit budget.
        </p>
        <div className="owner-ledger-strip" aria-hidden="true">
          <span>wire group</span>
          <i />
          <span>live interval</span>
          <i />
          <span>one owner</span>
          <i />
          <span>capacity check</span>
        </div>
      </article>

      <article className="story-rule capacity-equation-rule">
        <div>
          <h4>The mechanical rule</h4>
          <p>
            At every row, for every owner, the total live width assigned to that owner
            must fit inside its declared capacity:
          </p>
          <p className="capacity-equation">
            <MathTex tex="\max_t\sum_{\text{live }w\to O}|w|\le \mathrm{capacity}(O)" />
          </p>
          <p>
            This is why a borrowed lane is not automatically free. It is free only
            if executable liveness proves it is already inside a counted owner and is
            not live at the same time as the resource it replaces.
          </p>
        </div>
        <div className="owner-checklist" aria-hidden="true">
          <span>exactly one owner</span>
          <span>numeric capacity</span>
          <span>peak from liveness</span>
          <span>alias proof if borrowed</span>
        </div>
      </article>

      <article className="story-rule peak-row-rule">
        <div>
          <h4>The peak has a witness row</h4>
          <p>
            A qubit total is not an average over the circuit and not the sum of all
            values that ever appear. It is the largest row-by-row live load. The
            resource certificate should be able to point to the row or interval where
            the maximum occurs and list the owners that are simultaneously occupied.
          </p>
          <p>
            That is the no-free-wire invariant in practical form: if a field-sized
            value exists at that peak row, it must appear in exactly one owner bucket,
            and that bucket must have enough capacity.
          </p>
        </div>
        <div className="peak-row-card" aria-hidden="true">
          <div><span>strict peak</span><strong>{formatInt(strict.reconstructed_total)}q</strong></div>
          <div><span>clean guard delta</span><strong>+{formatInt(guard.gap.missing_logical_qubits_under_clean_ladder)}q</strong></div>
          <div><span>corrected witness</span><strong>{formatInt(correctedTotal)}q</strong></div>
        </div>
      </article>

      <article className="story-rule owner-witness-rule">
        <div>
          <h4>A capacity proof has two ledgers</h4>
          <p>
            The first ledger is row-local: at this exact row, these wire groups are
            simultaneously live. The second ledger is owner-local: after assignment,
            each owner carries the sum of the widths assigned to it at that same row.
          </p>
          <p>
            A proof needs both. Saying “guard ladder belongs to lookup workspace” is
            not enough; the lookup owner must have numeric room for lookup target plus
            guard ladder if they are live together.
          </p>
        </div>
        <div className="owner-witness-card" aria-hidden="true">
          <span>peak row: live wire list</span>
          <i />
          <span>owner buckets: summed widths</span>
          <i />
          <span>capacity verdict: load {'<='} budget</span>
        </div>
      </article>

      <article className="story-rule guard-ladder-rule">
        <div>
          <h4>The guard gap is the concrete example</h4>
          <p>
            The strict candidate currently counts {guard.current.logical_qubits} guard
            qubit for a predicate around the fused output row. A clean ladder for the
            <MathTex tex="L=0" /> predicate over a {strict.field_bits}-bit register
            needs {guard.cleanLadder.prefix_ancilla_bits} prefix ancilla bits plus{' '}
            {guard.cleanLadder.predicate_output_bits} predicate output bit, so the
            peak predicate workspace is {guard.cleanLadder.peak_predicate_workspace_bits}.
          </p>
          <p>
            Unless the artifact proves a concrete alias/no-ancilla construction, the
            conservative correction adds {guard.gap.missing_logical_qubits_under_clean_ladder}
            {' '}qubits.
          </p>
        </div>
        <div className="guard-capacity-math" aria-hidden="true">
          <div><span>strict candidate</span><strong>{formatInt(strict.reconstructed_total)}</strong></div>
          <div><span>guard delta</span><strong>+{formatInt(guard.gap.missing_logical_qubits_under_clean_ladder)}</strong></div>
          <div><span>guard-corrected candidate</span><strong>{formatInt(correctedTotal)}</strong></div>
        </div>
      </article>

      <div className="story-card-grid">
        <article>
          <strong>Unowned wire</strong>
          <p>A hidden scratch lane exists in execution but has no counted owner.</p>
          <span className="story-token">audit fail</span>
        </article>
        <article>
          <strong>Overflowed owner</strong>
          <p>Several live groups share one owner, but their summed width exceeds capacity.</p>
          <span className="story-token">load &gt; budget</span>
        </article>
        <article>
          <strong>Valid alias</strong>
          <p>A borrowed lane reuses counted storage only after liveness proves no overlap.</p>
          <span className="story-token">capacity + interval proof</span>
        </article>
      </div>

      <article className="story-question">
        <h4>How to read the labs</h4>
        <p>
          In slot liveness, toggle the clean-ladder guard and watch the candidate
          move from {formatInt(strict.reconstructed_total)} to {formatInt(correctedTotal)}
          qubits. In the capacity game, moving the guard ladder out of lookup workspace
          is the toy version of the same audit: owner assignment and numeric capacity
          have to pass together.
        </p>
      </article>
    </section>
  );
}

function NetlistStoryPanel() {
  return (
    <section className="netlist-story" data-testid="netlist-story" aria-label="Primitive netlist and liveness story">
      <article className="story-question">
        <h4>A formula is too smooth to count</h4>
        <p>
          A formula such as “add this point” describes a mathematical effect. A
          resource audit needs the rougher object underneath it: named rows, named
          wires, widths, owners, and the exact row where each temporary value is
          cleaned or carried forward.
        </p>
        <div className="engine-flow-strip" aria-hidden="true">
          <span>formula</span>
          <i />
          <span>primitive rows</span>
          <i />
          <span>live intervals</span>
          <i />
          <span>peak resources</span>
        </div>
      </article>

      <article className="story-rule netlist-rule">
        <div>
          <h4>Rows turn intuition into receipts</h4>
          <p>
            A primitive row is small enough to audit mechanically: operation, controls,
            targets, owner, width, and cost. Once rows exist, liveness becomes a scan:
            a wire is born when a row creates it, remains counted while later rows need
            it, and dies only when output, cleanup, or measurement justifies that death.
          </p>
          <p>
            That is why a flat netlist feels boring. It is supposed to be boring:
            boring rows are the thing a reviewer can replay.
          </p>
        </div>
        <div className="row-receipt-card" aria-hidden="true">
          <span>row 42</span>
          <strong>ccx partial_product</strong>
          <em>birth: scratch[17]</em>
          <em>owner: temporary_and_target_wire</em>
          <em>cleanup: row 83</em>
        </div>
      </article>

      <article className="story-rule lowering-boundary-rule">
        <div>
          <h4>Lowering is where trust usually leaks</h4>
          <p>
            A high-level opcode can be honest as an algorithm idea and still be too
            vague for a resource claim. The lowerer has to replace that opcode with
            primitive rows whose operands, owner capacities, and cleanup rows are
            explicit. If the macro summary says “lookup output” but the primitive
            stream never creates a counted target, the count is proving the wrong
            object.
          </p>
        </div>
        <div className="proof-contract-list" aria-hidden="true">
          <span>macro opcode</span>
          <span>primitive rows</span>
          <span>owner ledger</span>
          <span>cleanup rows</span>
        </div>
      </article>

      <article className="story-rule schedule-liveness-rule">
        <div>
          <h4>Scheduling changes the peak, not the function</h4>
          <p>
            Two row streams can compute the same boundary function while using different
            peak qubits. If a temporary value is cleaned immediately after its last
            use, it stops overlapping later values. If cleanup is delayed, the answer
            can still be right while the peak live count grows.
          </p>
          <p>
            That is the optimization loop in miniature: preserve semantics, move rows
            only when dependencies allow it, then recompute the peak from the generated
            live intervals.
          </p>
        </div>
        <div className="schedule-peak-strip" aria-hidden="true">
          <div><span>late cleanup</span><strong>more overlap</strong></div>
          <div><span>early cleanup</span><strong>lower peak</strong></div>
        </div>
      </article>

      <div className="story-card-grid">
        <article>
          <strong>Not a register list</strong>
          <p>Peak qubits are not chosen by listing registers that seem important.</p>
          <span className="story-token">derive from intervals</span>
        </article>
        <article>
          <strong>Not a macro summary</strong>
          <p>A macro can hide temporary wires unless it lowers into primitive rows.</p>
          <span className="story-token">lower before claiming</span>
        </article>
        <article>
          <strong>Not a doc number</strong>
          <p>The number in docs should be pulled from the same artifact the engine produced.</p>
          <span className="story-token">artifact-backed docs</span>
        </article>
      </div>

      <article className="story-question">
        <h4>How to use the labs</h4>
        <p>
          Start with the stack map to locate where a formula can drift away from the
          counted object. Then run the mini engine and opcode-lowering labs: they are
          the small version of the desired repo architecture. End with the schedule
          optimizer to see why the same function can have a different peak live-qubit
          count after legal cleanup motion.
        </p>
      </article>
    </section>
  );
}

function ResourceEngineStoryPanel({ data }: { data: typeof projectData }) {
  const gate = data.acceptedBaselineGate;
  const completion = data.engineCompletion;
  const blockerRows = gate.rows.slice(0, 4);

  return (
    <section className="resource-engine-story" data-testid="resource-engine-story" aria-label="Resource engine source of truth story">
      <article className="story-question">
        <h4>The engine exists because precise-looking counts lied</h4>
        <p>
          Earlier attempts failed when a lookup lane, guard ladder, or arithmetic
          scratch value was treated as if it were already paid for. The repair is not
          a better paragraph. It is one executable primitive stream that every later
          number has to come from.
        </p>
        <div className="source-of-truth-strip" aria-hidden="true">
          <span>execute rows</span>
          <i />
          <span>derive liveness</span>
          <i />
          <span>check owners</span>
          <i />
          <span>emit artifacts</span>
        </div>
      </article>

      <article className="story-rule proof-contract-rule">
        <div>
          <h4>One stream should feed every claim surface</h4>
          <p>
            The same primitive stream should be used for semantic replay, liveness,
            non-Clifford cost, generated docs, public values, and proof input. If any
            surface uses a different summary, the result can be internally consistent
            while proving the wrong object.
          </p>
        </div>
        <div className="proof-contract-list" aria-hidden="true">
          <span>execution tests</span>
          <span>owner capacity</span>
          <span>resource certificate</span>
          <span>ZKP public values</span>
        </div>
      </article>

      <article className="story-rule single-stream-rule">
        <div>
          <h4>No second calculator</h4>
          <p>
            Once the primitive rows exist, the qubit total, owner ledger, gate cost,
            docs table, and proof input should be queries over that row stream. A
            copied spreadsheet cell or a hand-retyped README number is a second
            calculator, which means it can silently drift away from the executable
            object.
          </p>
          <p>
            The artifact boundary is therefore boring on purpose: one stream is
            replayed, scanned for live wires, reduced into capacities and costs, and
            serialized into the fields that public claims read.
          </p>
        </div>
        <div className="single-stream-card" aria-hidden="true">
          <span>row stream</span>
          <span>semantic replay</span>
          <span>liveness scan</span>
          <span>capacity and cost</span>
          <span>artifact fields</span>
        </div>
      </article>

      <article className="story-rule engine-loop-rule">
        <div>
          <h4>The engine is a generator plus auditors</h4>
          <p>
            The desired shape is not “write a number, then add checks around it.” The
            engine should generate the primitive rows, replay the rows on boundary
            tests, derive every live interval, derive non-Clifford cost from row kinds,
            and emit the artifacts that docs and proof inputs read. A human can still
            design a better schedule, but the number comes from the generated object.
          </p>
        </div>
        <div className="proof-contract-list" aria-hidden="true">
          <span>generate</span>
          <span>replay</span>
          <span>derive</span>
          <span>publish</span>
        </div>
      </article>

      <article className="story-rule artifact-interface-rule">
        <div>
          <h4>The artifact is the public interface</h4>
          <p>
            The README, course, and proof wrapper should not each repeat a hand-written
            version of the resource claim. They should read the checked artifact emitted
            by the engine. Otherwise a stale document can advertise one number while
            the proof binds another digest or the tests cover another boundary.
          </p>
          <p>
            A reviewer should be able to start from a public value, find the resource
            certificate digest, open the checked artifact, and reproduce which primitive
            stream, owners, liveness intervals, and gate counts produced the claim.
          </p>
        </div>
        <div className="artifact-interface-card" aria-hidden="true">
          <span>primitive stream</span>
          <span>resource artifact</span>
          <span>docs and proof input</span>
          <span>public values</span>
        </div>
      </article>

      <article className="story-rule engine-status-rule">
        <div>
          <h4>Current status is intentionally not “accepted baseline”</h4>
          <p>
            The engine completion artifact says Clifford-complete goal achieved:{' '}
            <code>{String(completion.cliffordCompleteGoalAchieved)}</code>. The accepted
            baseline gate is <code>{gate.status}</code> because the public baseline may
            be populated only after every gate row passes and totals are recomputed
            from that same primitive stream.
          </p>
          <p>
            That status is useful. It tells a contributor where to work next instead of
            hiding the remaining macro boundary behind a precise-looking resource row.
          </p>
        </div>
        <div className="engine-blocker-list">
          {blockerRows.map((row) => (
            <div key={row.name}>
              <span>{readableStatus(row.name)}</span>
              <strong>{readableStatus(row.status)}</strong>
            </div>
          ))}
        </div>
      </article>
    </section>
  );
}

function MiniEngineStoryPanel() {
  return (
    <section className="mini-engine-story" data-testid="mini-engine-story" aria-label="Mini resource engine story">
      <article className="story-question">
        <h4>The toy engine is the real rule at small scale</h4>
        <p>
          The lab does not ask you to trust a resource number. It gives you a tiny
          circuit program, materializes the rows, derives wire lifetimes, checks owner
          budgets, and then reports the peak. The widths are small so the whole
          derivation fits on one page; the rule is the same rule the repo needs at
          secp256k1 scale.
        </p>
        <div className="mini-engine-flow-strip" aria-hidden="true">
          <span>program rows</span>
          <i />
          <span>wire intervals</span>
          <i />
          <span>owner ledger</span>
          <i />
          <span>peak row</span>
        </div>
      </article>

      <article className="story-rule mini-row-rule">
        <div>
          <h4>One row creates a lifetime, not just a line of text</h4>
          <p>
            When a row creates a scratch value, the engine records three facts before
            counting anything: the row where the value is born, the last row that still
            needs it, and the owner whose capacity must pay for its width. Peak qubits
            are then a consequence of overlapping intervals, not a manually selected
            register list.
          </p>
        </div>
        <div className="mini-row-card" aria-hidden="true">
          <span>row 3</span>
          <strong>partial = x AND y</strong>
          <em>birth: 3</em>
          <em>last use: 6</em>
          <em>owner: scratch_workspace</em>
        </div>
      </article>

      <article className="story-rule mini-witness-rule">
        <div>
          <h4>The peak count comes with a witness</h4>
          <p>
            In the lab’s initial failing state, the peak is row 4: input slot, lookup
            target, partial scratch, and phase bit overlap for a total of 10 toy wires.
            After assigning scratch to its own owner and adding source-uncompute, the
            scratch dies before the phase bit overlaps it, so the peak drops to 9.
          </p>
          <p>
            This is the habit to carry back to the repo. Do not ask “which registers
            did the author remember to count?” Ask “which row witnesses the peak, and
            can I replay the interval scan that found it?”
          </p>
        </div>
        <div className="mini-witness-card" aria-hidden="true">
          <div><span>before cleanup</span><strong>row 4 = 10</strong></div>
          <div><span>after cleanup</span><strong>row 2/3 = 9</strong></div>
        </div>
      </article>

      <article className="story-rule mini-engine-rule">
        <div>
          <h4>Cleanup can lower qubits without changing the answer</h4>
          <p>
            Source-uncompute does not mean “delete a variable from the report.” It
            means run the inverse of the temporary computation while the sources are
            still available. The output behavior is the same, but the scratch interval
            ends earlier, so the peak overlap can drop.
          </p>
          <p className="capacity-equation">
            <MathTex tex="\mathrm{peak}=\max_t\sum_{\text{live at }t}|w|" />
          </p>
        </div>
        <div className="mini-lifecycle-compare" aria-hidden="true">
          <div><span>without cleanup</span><strong>scratch lives to the end</strong></div>
          <div><span>with cleanup</span><strong>scratch dies after use</strong></div>
        </div>
      </article>

      <article className="story-rule mini-audit-rule">
        <div>
          <h4>Three checks make the count executable</h4>
          <p>
            The mini engine deliberately separates questions that earlier repo attempts
            blurred together. Does the program compute the same output? Are all live
            wires assigned to exactly one owner? Is each owner wide enough at its worst
            row? Only after those checks agree does the displayed peak deserve to be
            called a resource count.
          </p>
        </div>
        <div className="proof-contract-list" aria-hidden="true">
          <span>semantic replay</span>
          <span>single owner per wire</span>
          <span>capacity covers peak load</span>
          <span>docs read the artifact</span>
        </div>
      </article>
    </section>
  );
}

function OptimizationStoryPanel({ data }: { data: typeof projectData }) {
  const mission = data.optimizationMission;
  const current = mission.candidateRows[0];
  const sixFitsQubits = mission.candidateRows[2];
  const fiveSlot = mission.candidateRows[3];

  return (
    <section className="optimization-story" data-testid="optimization-story" aria-label="Optimization search story">
      <article className="story-question">
        <h4>The smallest number is not automatically the best result</h4>
        <p>
          Optimization here is a constrained search. A candidate must improve qubits,
          keep non-Clifford under the gate budget, preserve the point-add contract,
          expose every owner capacity, lower into executable primitives, and then feed
          the proof boundary. Missing one axis changes the claim status.
        </p>
        <div className="optimization-gate-strip" aria-hidden="true">
          <span>qubits</span>
          <i />
          <span>non-Clifford</span>
          <i />
          <span>semantics</span>
          <i />
          <span>promotion</span>
        </div>
      </article>

      <article className="story-rule candidate-frontier-rule">
        <div>
          <h4>Why the current frontier is blocked</h4>
          <p>
            The active target is below {formatInt(mission.target.logical_qubits_exclusive)}
            {' '}logical qubits and below {formatInt(mission.target.non_clifford_exclusive)}
            {' '}non-Clifford. The current strict row keeps gates under budget but is
            at {formatInt(current.logical_qubits)} qubits. A six-slot lookup squeeze
            can fit qubits only by raising non-Clifford to {formatInt(sixFitsQubits.non_clifford)}.
            A five-slot row would fit both numbers, but no executable promoted schedule
            is known.
          </p>
        </div>
        <div className="optimization-candidate-strip" aria-hidden="true">
          <div><span>current strict</span><strong>{formatInt(current.logical_qubits)}q</strong><em>{formatInt(current.non_clifford)}</em></div>
          <div><span>six-slot squeeze</span><strong>{formatInt(sixFitsQubits.logical_qubits)}q</strong><em>{formatInt(sixFitsQubits.non_clifford)}</em></div>
          <div><span>five-slot hope</span><strong>{formatInt(fiveSlot.logical_qubits)}q</strong><em>{readableStatus(fiveSlot.status)}</em></div>
        </div>
      </article>

      <article className="story-rule optimization-loop-rule">
        <div>
          <h4>The search loop is mechanical when the engine owns the count</h4>
          <p>
            A useful optimization freezes the functional boundary, changes one schedule
            or lowering rule, regenerates the primitive stream, reruns semantic replay,
            recomputes liveness and non-Clifford cost, then compares the new candidate
            against the gate. That loop makes “try an idea” safe because a failed idea
            becomes a named artifact, not a new headline.
          </p>
        </div>
        <div className="proof-contract-list" aria-hidden="true">
          <span>freeze boundary</span>
          <span>change lowering</span>
          <span>rerun engine</span>
          <span>classify result</span>
        </div>
      </article>

      <article className="story-rule evidence-matrix-rule">
        <div>
          <h4>Claim status is an evidence matrix</h4>
          <p>
            A candidate can be excellent on one axis and still blocked on another.
            Think of every row as a matrix: semantic boundary, primitive lowering,
            owner capacity, non-Clifford budget, proof binding, and documentation
            wording. The weakest missing column determines the public status.
          </p>
          <p>
            That is why a five-slot idea can stay a hypothesis even if its arithmetic
            intuition is good, and why a strict row can be useful while still not being
            the accepted physical baseline.
          </p>
        </div>
        <div className="evidence-matrix-card" aria-hidden="true">
          <span>semantics</span>
          <span>lowering</span>
          <span>capacity</span>
          <span>gates</span>
          <span>proof</span>
          <span>wording</span>
        </div>
      </article>

      <article className="story-rule breakthrough-rule">
        <div>
          <h4>The next useful patch must close a specific gate</h4>
          <p>
            The primary breakthrough is: {mission.nextRequiredBreakthrough.primary}.
            The secondary route is: {mission.nextRequiredBreakthrough.secondary}.
            Merely changing the headline number is not enough.
          </p>
        </div>
        <div className="owner-checklist" aria-hidden="true">
          <span>state what changed</span>
          <span>show the paid cost</span>
          <span>prove semantic boundary</span>
          <span>promote into the engine</span>
        </div>
      </article>
    </section>
  );
}

function PointAddBoundaryStoryPanel({ data }: { data: typeof projectData }) {
  const boundary = data.pointAddBoundary.streamedLookupTailLeaf;
  const oldBoundary = data.pointAddBoundary.lookupFedLeaf;
  const artifactsAgree = boundary.pass === oldBoundary.pass && boundary.total === oldBoundary.total;

  return (
    <section className="point-add-boundary-story" data-testid="point-add-boundary-story" aria-label="Point-add boundary contract story">
      <article className="story-question">
        <h4>A point-add leaf is an API, not one happy-path formula</h4>
        <p>
          Ordinary additions are only the branch most people picture first. The same
          counted leaf must also handle doubling, inverse pairs, an accumulator that
          starts at infinity, and a lookup entry that is the no-op identity.
        </p>
        <div className="source-of-truth-strip" aria-hidden="true">
          <span>random</span>
          <i />
          <span>doubling</span>
          <i />
          <span>inverse</span>
          <i />
          <span>infinity cases</span>
        </div>
      </article>

      <article className="story-rule point-boundary-rule">
        <div>
          <h4>The counted interface and tested interface must be the same</h4>
          <p>
            A lower-qubit leaf is not proven if tests exercise one boundary while the
            resource count describes a different interface. The current streamed-tail
            equivalence artifact reports {boundary.pass}/{boundary.total} checked
            cases, and the older lookup-fed summary {artifactsAgree ? 'agrees' : 'does not agree'}
            {' '}with that total.
          </p>
        </div>
        <div className="proof-contract-list" aria-hidden="true">
          {Object.entries(boundary.categories).map(([name, category]) => (
            <span key={name}>{name.replaceAll('_', ' ')}: {category.pass}/{category.total}</span>
          ))}
        </div>
      </article>

      <article className="story-rule branch-selector-rule">
        <div>
          <h4>Edge cases require branch selectors, not wishes</h4>
          <p>
            A point-add formula usually has predicates such as “same point,” “inverse
            point,” or “lookup is infinity.” In a quantum circuit those predicates are
            live controls. They need wires, owners, cleanup, and semantic tests just
            like coordinate values do.
          </p>
          <p>
            Therefore an edge-case artifact must prove two things at once: the selected
            branch returns the right point, and the selector/control machinery is part
            of the same counted executable interface.
          </p>
        </div>
        <div className="branch-selector-card" aria-hidden="true">
          <div><span>predicate</span><strong>which branch?</strong></div>
          <div><span>controlled formula</span><strong>right point</strong></div>
          <div><span>cleanup</span><strong>selectors erased or counted</strong></div>
        </div>
      </article>

      <div className="story-card-grid">
        <article>
          <strong>Random-only trap</strong>
          <p>Random ordinary cases can all pass while edge branches remain untested.</p>
          <span className="story-token">coverage collapse</span>
        </article>
        <article>
          <strong>Infinity is semantic</strong>
          <p>Identity and inverse branches define the group operation, not rare extras.</p>
          <span className="story-token">branch contract</span>
        </article>
        <article>
          <strong>Boundary before headline</strong>
          <p>Do not lower or publish a point-add result unless the same boundary is executed and counted.</p>
          <span className="story-token">same leaf, same contract</span>
        </article>
      </div>
    </section>
  );
}

function ZkpBoundaryStoryPanel({ data }: { data: typeof projectData }) {
  const publication = data.proofPublication;
  const corpus = data.proofCorpusProfiles;

  return (
    <section className="zkp-boundary-story" data-testid="zkp-boundary-story" aria-label="ZKP boundary and publication story">
      <article className="story-question">
        <h4>A valid proof is only a receipt for its exact statement</h4>
        <p>
          A ZKP verifier does not read the README and decide whether the whole project
          is true. It checks one encoded statement against one proof bundle. If that
          statement points at an old resource digest, an eight-case smoke corpus, or a
          macro-level boundary, the proof can be valid while the public sentence is still
          too strong.
        </p>
        <div className="source-of-truth-strip" aria-hidden="true">
          <span>input JSON</span>
          <i />
          <span>public values</span>
          <i />
          <span>proof bundle</span>
          <i />
          <span>claim wording</span>
        </div>
      </article>

      <article className="story-rule zkp-binding-rule">
        <div>
          <h4>The binding chain is the thing a reviewer follows</h4>
          <p>
            The proof should bind a concrete input JSON. That input should contain the
            resource certificate digest. The public values should repeat the digests and
            expected totals. The checked files should be the files in the repo branch a
            reviewer can clone. A break in that chain does not make ZKP useless; it
            narrows what the proof actually says.
          </p>
        </div>
        <div className="zkp-binding-ledger" aria-hidden="true">
          <span>checked input</span>
          <span>resource digest</span>
          <span>public values</span>
          <span>branch artifact</span>
        </div>
      </article>

      <article className="story-rule zkp-receipt-rule">
        <div>
          <h4>The current checked proof status is deliberately conservative</h4>
          <p>
            Publication ready: <code>{String(publication.publicationReady)}</code>.
            Current systems marked stale: {publication.staleSystems.join(', ')}.
            The public proof profile has {corpus.publicCaseCount} cases; the
            Google-comparable release target has {formatInt(corpus.releaseCaseCount)}.
          </p>
        </div>
        <div className="proof-contract-list" aria-hidden="true">
          {publication.systems.map((system) => (
            <span key={system.system}>
              {system.system}: current {String(system.current)}, digest {String(system.resourceDigestMatchesInput)}
            </span>
          ))}
        </div>
      </article>

      <div className="story-card-grid">
        <article>
          <strong>Verifier says valid</strong>
          <p>That proves only the relation encoded by the checked input and public values.</p>
          <span className="story-token">proof validity</span>
        </article>
        <article>
          <strong>Artifact says current</strong>
          <p>That additionally proves the proof bundle matches the current resource input.</p>
          <span className="story-token">freshness</span>
        </article>
        <article>
          <strong>Claim says physical</strong>
          <p>That needs the macro boundary closed, not just a proof wrapper around a weaker statement.</p>
          <span className="story-token">scope match</span>
        </article>
      </div>

      <article className="story-rule proof-wording-rule">
        <div>
          <h4>Proof validity still needs a wording audit</h4>
          <p>
            The same valid proof can support several different public sentences. “This
            proof verifies,” “this proof binds the current candidate,” and “this proves
            the accepted physical baseline” are not equivalent. The wording must be no
            stronger than the input, corpus, resource digest, and macro-boundary status.
          </p>
          <p>
            This is why the course asks the learner to classify claims before repeating
            numbers. A verifier result is evidence, but the claim decides what that
            evidence is being used to say.
          </p>
        </div>
        <div className="proof-wording-card" aria-hidden="true">
          <span>verifies proof bytes</span>
          <span>binds current candidate</span>
          <span>supports accepted baseline</span>
        </div>
      </article>

      <article className="story-question">
        <h4>Why the lab asks for both compressed and Groth16 gates</h4>
        <p>
          A compressed proof is the normal SP1 receipt shape used during iteration.
          Groth16 is the smaller wrapped proof format people often want for external
          verification. Rebuilding only one of them leaves a reviewer asking whether the
          other artifact still binds the same input. That is why the publication gate
          treats freshness, corpus size, macro closure, and both verification systems as
          one release boundary.
        </p>
      </article>
    </section>
  );
}

function ContributionStoryPanel({ data }: { data: typeof projectData }) {
  const blockers = data.activeBlockers;

  return (
    <section className="contribution-story" data-testid="contribution-story" aria-label="Contributor mission story">
      <article className="story-question">
        <h4>A useful patch is a small claim plus evidence</h4>
        <p>
          “Improve the circuit” is not a reviewable claim. “Promote this cleanup row
          into the primitive stream and recompute owner capacity” is reviewable because
          it names the object, the evidence, and the status change it should justify.
        </p>
        <div className="source-of-truth-strip" aria-hidden="true">
          <span>claim</span>
          <i />
          <span>artifact</span>
          <i />
          <span>test</span>
          <i />
          <span>wording</span>
        </div>
      </article>

      <article className="story-rule mission-packet-rule">
        <div>
          <h4>The open blockers define useful work</h4>
          <p>
            A contribution should either close one blocker, sharpen an artifact that
            proves a blocker, or prevent a class of wrong claims. Current open blockers
            are listed next to the mission board so learners do not optimize a side path.
          </p>
        </div>
        <div className="engine-blocker-list">
          {blockers.map((blocker) => (
            <div key={blocker.name}>
              <span>{blocker.name}</span>
              <strong>{blocker.status}</strong>
            </div>
          ))}
        </div>
      </article>

      <div className="story-card-grid">
        <article>
          <strong>Choose the smallest claim</strong>
          <p>
            Start from one named boundary: a row, artifact, verifier input, liveness
            interval, or documentation claim. A small claim is easier to falsify and
            easier to merge.
          </p>
          <span className="story-token">one boundary</span>
        </article>
        <article>
          <strong>Attach executable evidence</strong>
          <p>
            Pair the patch with the check that would fail if the claim were false:
            semantic replay, owner-capacity audit, artifact digest check, or focused
            browser/course regression.
          </p>
          <span className="story-token">failing test first</span>
        </article>
        <article>
          <strong>Match the public wording</strong>
          <p>
            Do not let a local improvement upgrade the headline. Claim only the level
            the evidence proves: toy intuition, internal candidate, guard consequence,
            or accepted baseline.
          </p>
          <span className="story-token">claim level</span>
        </article>
      </div>

      <article className="story-question">
        <h4>How to use the three labs</h4>
        <p>
          The mission board turns blockers into concrete patches. The claim drill
          trains the habit of rejecting attractive but under-proved statements. The
          coverage audit checks whether the course itself still teaches the route from
          first principles to useful repo work. A useful contributor should be able to
          move between all three: choose work, prove it, and describe it without
          overstating it.
        </p>
      </article>
    </section>
  );
}

function RepoBaselineStoryPanel({ data }: { data: typeof projectData }) {
  const strict = data.currentStrictCandidate;
  const corrected = data.guardCorrectedNoAliasCandidate;
  const gate = data.acceptedBaselineGate;
  const blockedRows = gate.rows.filter((row) => !row.pass);

  return (
    <section className="repo-baseline-story" data-testid="repo-baseline-story" aria-label="Repo baseline status story">
      <article className="story-question">
        <h4>The repo status is a status table, not a victory poster</h4>
        <p>
          The last page is where overclaiming is easiest. A reader sees exact numbers
          and wants one sentence: “this is the result.” The repo has to be stricter than
          that. It separates numbers that are useful for engineering from numbers that
          are accepted as a physical baseline, and it keeps the accepted slot empty until
          the gate rows close.
        </p>
      </article>

      <article className="story-rule baseline-status-rule">
        <div>
          <h4>Current numbers and their claim level</h4>
          <p>
            Strict candidate: {formatInt(strict.logical_qubits)} qubits /{' '}
            {formatInt(strict.non_clifford)} non-Clifford. Guard-corrected consequence:
            {' '}{formatInt(corrected.logical_qubits)} qubits / {formatInt(corrected.non_clifford)}
            {' '}non-Clifford. Accepted-baseline gate: <code>{gate.status}</code>.
          </p>
        </div>
        <div className="optimization-candidate-strip" aria-hidden="true">
          <div><span>strict candidate</span><strong>{formatInt(strict.logical_qubits)}q</strong><em>{readableStatus(strict.status)}</em></div>
          <div><span>guard corrected</span><strong>{formatInt(corrected.logical_qubits)}q</strong><em>{readableStatus(corrected.status)}</em></div>
          <div><span>accepted baseline</span><strong>none yet</strong><em>{readableStatus(gate.decision)}</em></div>
        </div>
      </article>

      <article className="story-rule baseline-gate-rule">
        <div>
          <h4>“None yet” is a claim about evidence, not pessimism</h4>
          <p>
            The accepted baseline is blocked by {blockedRows.length} gate rows. Those
            rows are concrete: one authoritative primitive stream, guard capacity
            promotion, modular accumulator promotion, no abandoned synthetic scratch,
            and public-headline publication clearance. Closing one row should update the
            artifact and the page should follow from the artifact.
          </p>
        </div>
        <div className="engine-blocker-list">
          {blockedRows.slice(0, 5).map((row) => (
            <div key={row.name}>
              <span>{readableStatus(row.name)}</span>
              <strong>{readableStatus(row.status)}</strong>
            </div>
          ))}
        </div>
      </article>

      <div className="story-card-grid">
        <article>
          <strong>External baseline</strong>
          <p>Useful for comparison, but not generated by this repo’s artifacts and not proof of this implementation.</p>
          <span className="story-token">reference row</span>
        </article>
        <article>
          <strong>Repo candidate</strong>
          <p>Useful for engineering direction, but wording must preserve the exact blockers still open.</p>
          <span className="story-token">candidate row</span>
        </article>
        <article>
          <strong>Accepted baseline</strong>
          <p>Requires all gates closed against the same primitive stream and proof boundary.</p>
          <span className="story-token">not populated</span>
        </article>
      </div>

      <article className="story-question">
        <h4>How the README should eventually get its numbers</h4>
        <p>
          The target architecture is mechanical: rebuild the primitive stream, derive
          liveness and non-Clifford cost from it, emit the baseline artifact, regenerate
          the README section from that artifact, and only then rebuild the proofs. Manual
          copying is exactly the class of failure this course is training readers to
          notice.
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

      <article className="story-rule circuit-reading-rule">
        <div>
          <h4>Read a circuit left to right</h4>
          <p>
            A circuit diagram is a time story. Horizontal lines are qubit wires. Boxes
            or control symbols are gates. A gate touches only the wires connected to it,
            and the state then continues to the next column. Measurement is different:
            it turns a quantum wire into a classical outcome, so it usually belongs at
            an explicit boundary rather than hidden in the middle of arithmetic.
          </p>
        </div>
        <div className="circuit-reading-strip" aria-hidden="true">
          <span>wire</span>
          <span>gate</span>
          <span>next state</span>
          <span>measure</span>
        </div>
      </article>

      <article className="story-rule control-branch-rule">
        <div>
          <h4>A control is a branch condition, not a hidden readout</h4>
          <p>
            A controlled gate is easiest to misunderstand if you read it like an
            ordinary <code>if</code> statement. The control wire is not measured. The
            whole state is transformed branch by branch: every branch whose control
            bit is 0 keeps the target unchanged, and every branch whose control bit is
            1 receives the target operation.
          </p>
          <p>
            This is why a controlled gate can create entanglement. If the control wire
            is in a split, the gate applies coherently to both live branches instead of
            choosing one classical path.
          </p>
        </div>
        <div className="controlled-branch-card" aria-hidden="true">
          <span>control = 0</span>
          <strong>target unchanged</strong>
          <span>control = 1</span>
          <strong>target is flipped</strong>
        </div>
      </article>

      <article className="story-rule row-contract-rule">
        <div>
          <h4>A row is a small contract</h4>
          <p>
            Once the diagram becomes an auditable row, the repo needs more than a gate
            name. It needs the operation, operands, branch condition, target effect,
            cost class, and cleanup promise. Without that row contract, the later
            liveness engine cannot know which wires are born, carried, or released.
          </p>
        </div>
        <div className="row-schema-strip" aria-hidden="true">
          <span>op</span>
          <span>controls</span>
          <span>target</span>
          <span>cost</span>
          <span>cleanup</span>
        </div>
      </article>

      <article className="story-rule scratch-lifecycle-rule">
        <div>
          <h4>A scratch wire has a lifecycle, not a scope</h4>
          <p>
            In ordinary code a temporary variable can disappear when the block ends.
            In a quantum row stream the value is still physical until the circuit
            explicitly returns it to <MathTex tex="|0\rangle" /> or declares it as an
            output. The liveness engine therefore needs a birth row, every use, a valid
            cleanup row, and the row where the value stops being live.
          </p>
        </div>
        <div className="scratch-lifecycle-card" aria-hidden="true">
          <span><b>birth</b><i>compute scratch</i></span>
          <span><b>use</b><i>control useful update</i></span>
          <span><b>cleanup</b><i>run inverse with same sources</i></span>
          <span><b>death</b><i>scratch is |0&gt;</i></span>
        </div>
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
          <p>A control does not measure. It says: on every branch where this wire is 1, move the target.</p>
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

      <article className="story-question">
        <h4>How to use the labs</h4>
        <p>
          First use the primitive netlist toy to see a button become a row with
          touched wires and cost. Then type rows in the DSL until invalid opcodes fail
          loudly. Finish with cleanup: the same row stream is not resource-safe until
          every temporary wire has a justified end of life.
        </p>
      </article>
    </section>
  );
}

export function App() {
  const [activeLessonId, setActiveLessonId] = useState<LessonId>(() => lessonFromHash());
  const [completed, setCompleted] = useState<Set<LessonId>>(() => loadCompletedLessons());
  const [focusedLabByLesson, setFocusedLabByLesson] = useState<Partial<Record<LessonId, number>>>({});
  const [showAllLabsByLesson, setShowAllLabsByLesson] = useState<Partial<Record<LessonId, boolean>>>({});
  const [revealedCheckpointByLesson, setRevealedCheckpointByLesson] = useState<Partial<Record<LessonId, boolean>>>({});
  const [showFullCourseIndex, setShowFullCourseIndex] = useState(false);
  const activeLesson = lessons.find((lesson) => lesson.id === activeLessonId) ?? lessons[0];
  const currentIndex = lessons.findIndex((lesson) => lesson.id === activeLesson.id);
  const previousLesson = currentIndex > 0 ? lessons[currentIndex - 1] : null;
  const nextLesson = currentIndex < lessons.length - 1 ? lessons[currentIndex + 1] : null;
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
          labItem(0, 'Whole attack map', <AttackPipelineLab projectData={projectData} />),
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
          labItem(1, 'QROAMClean tradeoff', <QroamTradeoffLab projectData={projectData} />),
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
          labItem(1, 'Invariant lab', <EngineInvariantLab projectData={projectData} />),
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
        <header className="hero-panel no-status">
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

        <section className="content-grid learning-grid">
          <article className="concept-panel">
            <div className="panel-heading">
              <BookOpen size={20} />
              <h3>Core idea</h3>
            </div>
            <section className="lesson-primer" aria-label="Lesson introduction">
              <p>{activeLesson.mentalModel}</p>
            </section>
            {activeLesson.id === 'zero' ? <OrientationStoryPanel /> : null}
            {activeLesson.id === 'qubit' ? <QubitStoryPanel /> : null}
            {activeLesson.id === 'one-qubit' ? <OneQubitStoryPanel /> : null}
            {activeLesson.id === 'two-qubit' ? <TwoQubitStoryPanel /> : null}
            {activeLesson.id === 'clifford' ? <CliffordStoryPanel /> : null}
            {activeLesson.id === 'logic-physical' ? <LogicalPhysicalStoryPanel /> : null}
            {activeLesson.id === 'phase-estimation' ? <PhaseEstimationStoryPanel /> : null}
            {activeLesson.id === 'netlists' ? <NetlistStoryPanel /> : null}
            {activeLesson.id === 'ecdlp' ? <EcdlpStoryPanel /> : null}
            {activeLesson.id === 'coordinates' ? <CoordinatesStoryPanel /> : null}
            {activeLesson.id === 'lookup-qroam' ? <LookupQroamStoryPanel data={projectData} /> : null}
            {activeLesson.id === 'programming' ? <ProgrammingStoryPanel /> : null}
            {activeLesson.id === 'cleanup' ? <CleanupStoryPanel data={projectData} /> : null}
            {activeLesson.id === 'modular-lowering' ? <ModularLoweringStoryPanel data={projectData} /> : null}
            {activeLesson.id === 'owner-capacity' ? <OwnerCapacityStoryPanel data={projectData} /> : null}
            {activeLesson.id === 'resource-engine' ? <ResourceEngineStoryPanel data={projectData} /> : null}
            {activeLesson.id === 'mini-engine' ? <MiniEngineStoryPanel /> : null}
            {activeLesson.id === 'optimization' ? <OptimizationStoryPanel data={projectData} /> : null}
            {activeLesson.id === 'point-add-boundary' ? <PointAddBoundaryStoryPanel data={projectData} /> : null}
            {activeLesson.id === 'zkp-boundary' ? <ZkpBoundaryStoryPanel data={projectData} /> : null}
            {activeLesson.id === 'contribution' ? <ContributionStoryPanel data={projectData} /> : null}
            {activeLesson.id === 'repo-baselines' ? <RepoBaselineStoryPanel data={projectData} /> : null}
            {activeLesson.id === 'gates' ? <GatesStoryPanel /> : null}
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

          <section className="lesson-labs inline" id="active-lesson-labs" aria-label={`${activeLesson.title} labs`}>
            {guidedActiveLabs}
          </section>
        </section>

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
