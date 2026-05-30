import { useMemo, useState } from 'react';
import { Binary, Wand2 } from 'lucide-react';
import { MathTex } from './MathText';

type Complex = {
  re: number;
  im: number;
};

type ParsedGate =
  | { op: 'H' | 'X' | 'Z'; target: 'q0' | 'q1'; line: number }
  | { op: 'CX'; control: 'q0' | 'q1'; target: 'q0' | 'q1'; line: number };

type TraceRow = {
  instruction: string;
  meaning: string;
  branches: string;
};

const basis = ['|00>', '|01>', '|10>', '|11>'];
const zero: Complex = { re: 0, im: 0 };
const one: Complex = { re: 1, im: 0 };
const initialState = [one, zero, zero, zero];

const examples = {
  bell: `H q0
CX q0 q1`,
  productSplit: `H q0
H q1`,
  interference: `H q0
Z q0
H q0`,
  entangleThenFlip: `X q1
H q0
CX q0 q1`,
};

const add = (left: Complex, right: Complex): Complex => ({ re: left.re + right.re, im: left.im + right.im });
const sub = (left: Complex, right: Complex): Complex => ({ re: left.re - right.re, im: left.im - right.im });
const mul = (left: Complex, right: Complex): Complex => ({
  re: left.re * right.re - left.im * right.im,
  im: left.re * right.im + left.im * right.re,
});
const scale = (value: Complex, factor: number): Complex => ({ re: value.re * factor, im: value.im * factor });
const abs2 = (value: Complex) => value.re * value.re + value.im * value.im;
const maskFor = (wire: 'q0' | 'q1') => (wire === 'q0' ? 2 : 1);

function parseProgram(program: string) {
  const gates: ParsedGate[] = [];
  const errors: string[] = [];
  const validWire = (wire: string): wire is 'q0' | 'q1' => wire === 'q0' || wire === 'q1';

  for (const [index, rawLine] of program.split('\n').entries()) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;

    const [rawOp, ...wires] = line.split(/\s+/);
    const op = rawOp.toUpperCase();
    if ((op === 'H' || op === 'X' || op === 'Z') && wires.length === 1 && validWire(wires[0])) {
      gates.push({ op, target: wires[0], line: index + 1 });
      continue;
    }
    if (op === 'CX' && wires.length === 2 && validWire(wires[0]) && validWire(wires[1]) && wires[0] !== wires[1]) {
      gates.push({ op, control: wires[0], target: wires[1], line: index + 1 });
      continue;
    }

    errors.push(`line ${index + 1}: expected one-qubit gate H/X/Z plus q0 or q1, or controlled-X as CX q0 q1`);
  }

  return { gates, errors };
}

function applySingleQubitGate(state: Complex[], target: 'q0' | 'q1', matrix: [[Complex, Complex], [Complex, Complex]]) {
  const result = state.map((value) => ({ ...value }));
  const mask = maskFor(target);

  for (let index = 0; index < state.length; index += 1) {
    if ((index & mask) !== 0) continue;
    const pairedIndex = index | mask;
    const zeroAmplitude = state[index];
    const oneAmplitude = state[pairedIndex];
    result[index] = add(mul(matrix[0][0], zeroAmplitude), mul(matrix[0][1], oneAmplitude));
    result[pairedIndex] = add(mul(matrix[1][0], zeroAmplitude), mul(matrix[1][1], oneAmplitude));
  }

  return result;
}

function applyCx(state: Complex[], control: 'q0' | 'q1', target: 'q0' | 'q1') {
  const result = state.map(() => zero);
  const controlMask = maskFor(control);
  const targetMask = maskFor(target);

  for (let index = 0; index < state.length; index += 1) {
    const outputIndex = (index & controlMask) === 0 ? index : index ^ targetMask;
    result[outputIndex] = state[index];
  }

  return result;
}

function applyParsedGate(state: Complex[], gate: ParsedGate) {
  const h = scale(one, 1 / Math.sqrt(2));
  const matrices = {
    H: [[h, h], [h, scale(h, -1)]] as [[Complex, Complex], [Complex, Complex]],
    X: [[zero, one], [one, zero]] as [[Complex, Complex], [Complex, Complex]],
    Z: [[one, zero], [zero, scale(one, -1)]] as [[Complex, Complex], [Complex, Complex]],
  };

  if (gate.op === 'CX') return applyCx(state, gate.control, gate.target);
  return applySingleQubitGate(state, gate.target, matrices[gate.op]);
}

function runProgram(gates: ParsedGate[]) {
  return gates.reduce(applyParsedGate, initialState);
}

const formatComplex = (value: Complex) => {
  const real = Math.abs(value.re) < 0.005 ? 0 : value.re;
  const imaginary = Math.abs(value.im) < 0.005 ? 0 : value.im;
  if (imaginary === 0) return real.toFixed(2);
  if (real === 0) return `${imaginary.toFixed(2)}i`;
  return `${real.toFixed(2)}${imaginary > 0 ? '+' : ''}${imaginary.toFixed(2)}i`;
};

const near = (value: number, target: number) => Math.abs(value - target) < 0.03;

function formatInstruction(gate: ParsedGate) {
  if (gate.op === 'CX') return `CX ${gate.control} ${gate.target}`;
  return `${gate.op} ${gate.target}`;
}

function describeGate(gate: ParsedGate) {
  if (gate.op === 'CX') return `Controlled-X flips ${gate.target} only on branches where ${gate.control} is 1.`;
  if (gate.op === 'H') return `Hadamard mixes the 0 and 1 branches of ${gate.target}.`;
  if (gate.op === 'X') return `Bit flip swaps the 0 and 1 labels of ${gate.target}.`;
  return `Phase flip changes the sign of branches where ${gate.target} is 1.`;
}

function summarizeBranches(state: Complex[]) {
  return state
    .map((amplitude, index) => ({
      amplitude,
      label: basis[index],
      probability: abs2(amplitude),
    }))
    .filter((branch) => branch.probability > 0.005)
    .map((branch) => `${branch.label}: ${formatComplex(branch.amplitude)} (${Math.round(branch.probability * 100)}%)`)
    .join('  |  ');
}

function buildTrace(gates: ParsedGate[]) {
  let currentState = initialState;
  const rows: TraceRow[] = [
    {
      instruction: 'start',
      meaning: 'Prepare both wires as 0 before any gate runs.',
      branches: summarizeBranches(currentState),
    },
  ];

  for (const gate of gates) {
    currentState = applyParsedGate(currentState, gate);
    rows.push({
      instruction: formatInstruction(gate),
      meaning: describeGate(gate),
      branches: summarizeBranches(currentState),
    });
  }

  return rows;
}

export function StateVectorLab() {
  const [program, setProgram] = useState(examples.bell);
  const parsed = useMemo(() => parseProgram(program), [program]);
  const state = useMemo(() => (parsed.errors.length === 0 ? runProgram(parsed.gates) : initialState), [parsed]);
  const trace = useMemo(() => (parsed.errors.length === 0 ? buildTrace(parsed.gates) : []), [parsed]);
  const probabilities = state.map(abs2);
  const separabilityDeterminant = sub(mul(state[0], state[3]), mul(state[1], state[2]));
  const determinantMagnitude = Math.sqrt(abs2(separabilityDeterminant));
  const entangled = determinantMagnitude > 0.01;
  const missions = [
    {
      label: 'Product split',
      pass: !entangled && probabilities.every((probability) => near(probability, 0.25)),
      hint: 'Use H on both wires: H q0 and H q1.',
    },
    {
      label: 'Bell correlation',
      pass: entangled && near(probabilities[0], 0.5) && near(probabilities[3], 0.5),
      hint: 'Use H q0, then CX q0 q1.',
    },
    {
      label: 'Cancel to |10>',
      pass: near(probabilities[2], 1),
      hint: 'Use H q0, Z q0, H q0.',
    },
  ];

  return (
    <article className="lab-panel" data-testid="state-vector-lab">
      <div className="panel-heading">
        <Binary size={20} />
        <h3>Run a two-qubit state vector</h3>
      </div>
      <div className="example-row">
        <button type="button" onClick={() => setProgram(examples.bell)}>
          <Wand2 size={16} />
          Bell pair
        </button>
        <button type="button" onClick={() => setProgram(examples.productSplit)}>Product split</button>
        <button type="button" onClick={() => setProgram(examples.interference)}>Interference</button>
        <button type="button" onClick={() => setProgram(examples.entangleThenFlip)}>Entangle + flip</button>
      </div>
      <p>
        The editor uses a tiny circuit language. Each line applies one reversible
        operation to the current four-amplitude table, then the trace below shows the
        new live branches.
      </p>
      <section className="gate-vocabulary-grid" aria-label="Two-qubit program vocabulary">
        <article>
          <strong>H q0</strong>
          <p>Hadamard on q0: split or recombine the q0 side of the joint table.</p>
        </article>
        <article>
          <strong>X q1</strong>
          <p>Bit flip on q1: swap labels where q1 is 0 with labels where q1 is 1.</p>
        </article>
        <article>
          <strong>Z q0</strong>
          <p>Phase flip on q0: change the sign of branches whose q0 label is 1.</p>
        </article>
        <article>
          <strong>CX q0 q1</strong>
          <p>Controlled-X: use q0 as control; it permutes labels by flipping q1 only on q0 = 1 branches.</p>
        </article>
      </section>
      <section className="two-qubit-primer" aria-label="Two-qubit state primer">
        <article>
          <strong>Two qubits, four labels</strong>
          <p>The state now has four amplitudes: |00&gt;, |01&gt;, |10&gt;, and |11&gt;.</p>
        </article>
        <article>
          <strong>Product state</strong>
          <p>Sometimes the two wires can still be described as two independent one-qubit states.</p>
        </article>
        <article>
          <strong>Entangled state</strong>
          <p>Sometimes only the joint four-amplitude pattern describes the state correctly.</p>
        </article>
        <article>
          <strong>Measurement</strong>
          <p>Measurement samples one full two-bit label, such as |00&gt; or |11&gt;.</p>
        </article>
      </section>
      <section className="two-qubit-schemes" aria-label="Two-qubit scheme examples">
        <article>
          <strong>Bell pair</strong>
          <p>Split q0, then use q0 as a control. The only live branches are |00&gt; and |11&gt;.</p>
          <span>H q0; CX q0 q1</span>
        </article>
        <article>
          <strong>Interference</strong>
          <p>Mixing twice can cancel one branch and reinforce another.</p>
          <span>H q0; Z q0; H q0</span>
        </article>
        <article>
          <strong>Entangle + flip</strong>
          <p>After branches are linked, a later flip moves the joint labels together.</p>
          <span>H q0; CX q0 q1; X q1</span>
        </article>
      </section>
      <section className="controlled-x-explainer" aria-label="Controlled-X explanation">
        <div className="cx-wire-diagram" aria-hidden="true">
          <div>
            <span>q0 control</span>
            <i />
            <strong>1?</strong>
          </div>
          <div>
            <span>q1 target</span>
            <i />
            <strong>X</strong>
          </div>
        </div>
        <p>
          <strong>Controlled-X</strong> means: look at the control qubit. On every branch
          where the control is 1, apply a bit flip to the target qubit. On branches
          where the control is 0, leave the target alone.
        </p>
        <div className="cx-branch-map" role="table" aria-label="Controlled-X branch map">
          <div role="row"><span>|00&gt;</span><strong>|00&gt;</strong></div>
          <div role="row"><span>|01&gt;</span><strong>|01&gt;</strong></div>
          <div role="row"><span>|10&gt;</span><strong>|11&gt;</strong></div>
          <div role="row"><span>|11&gt;</span><strong>|10&gt;</strong></div>
        </div>
        <p className="mono-line">CX q0 q1 = control q0, bit-flip target q1 only when q0 is 1</p>
      </section>
      <section className="two-qubit-mission-grid" aria-label="Two-qubit verified missions">
        {missions.map((mission) => (
          <article className={mission.pass ? 'mission-pass' : ''} key={mission.label}>
            <strong>{mission.pass ? 'pass' : 'try'}</strong>
            <span>{mission.label}</span>
            <p>{mission.hint}</p>
          </article>
        ))}
      </section>
      <textarea
        aria-label="State vector program editor"
        className="dsl-editor"
        value={program}
        onChange={(event) => setProgram(event.currentTarget.value)}
        spellCheck={false}
      />
      {parsed.errors.length > 0 ? (
        <div className="parse-errors">
          {parsed.errors.map((error) => <p key={error}>{error}</p>)}
        </div>
      ) : (
        <>
          <section className="state-execution-trace" aria-label="State vector execution trace">
            <h4>Execution trace</h4>
            {trace.map((row, index) => (
              <article key={`${index}-${row.instruction}`}>
                <strong>{row.instruction}</strong>
                <p>{row.meaning}</p>
                <span>{row.branches}</span>
              </article>
            ))}
          </section>
          <dl className="metric-row">
            <div><dt>Gates</dt><dd>{parsed.gates.length}</dd></div>
            <div><dt>Qubits</dt><dd>2</dd></div>
            <div><dt>State size</dt><dd>4</dd></div>
            <div><dt>Entangled</dt><dd>{entangled ? 'yes' : 'no'}</dd></div>
          </dl>
          <div className="state-vector-grid">
            {state.map((amplitude, index) => (
              <div key={basis[index]}>
                <span>{basis[index]}</span>
                <strong>{formatComplex(amplitude)}</strong>
                <div className="probability-track">
                  <i style={{ width: `${Math.round(probabilities[index] * 100)}%` }} />
                </div>
                <em>{Math.round(probabilities[index] * 100)}%</em>
              </div>
            ))}
          </div>
          <section className="separability-check" aria-label="Separability check">
            <div>
              <strong>Product-state test</strong>
              <MathTex tex="a_{00}a_{11}-a_{01}a_{10}=0" />
            </div>
            <p>
              Zero means the four-amplitude table can factor into two separate
              one-qubit states. Nonzero means the state is entangled.
            </p>
            <span>
              current determinant magnitude {determinantMagnitude.toFixed(2)}: {entangled ? 'entangled' : 'product'}
            </span>
          </section>
        </>
      )}
      <p>
        Only two wires are shown so every amplitude can stay visible. The same branch,
        control, and cleanup discipline later scales into resource netlists.
      </p>
    </article>
  );
}
