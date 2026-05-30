import { useMemo, useState } from 'react';
import { Atom, RotateCcw } from 'lucide-react';
import { MathTex } from './MathText';

type Gate = 'I' | 'X' | 'H' | 'S';
type RealGate = Exclude<Gate, 'I'>;

type Complex = { re: number; im: number };
type State = { zero: Complex; one: Complex };

const steerableGates = ['H', 'X', 'S'] as const;

const gateLabels: Record<RealGate, string> = {
  H: 'Hadamard',
  X: 'Bit flip',
  S: 'Phase turn',
};

const gateDescriptions: Record<RealGate, string> = {
  H: 'mixes 0 and 1 amplitudes',
  X: 'swaps the 0 and 1 amplitudes',
  S: 'rotates only the 1-amplitude phase',
};

const gateFormulas: Record<RealGate, string> = {
  H: 'H:(a,b)\\mapsto\\left((a+b)/\\sqrt2,(a-b)/\\sqrt2\\right)',
  X: 'X:(a,b)\\mapsto(b,a)',
  S: 'S:(a,b)\\mapsto(a,ib)',
};

const gateLessons: Record<RealGate, string> = {
  H: 'Hadamard is the first recombining move: it makes a sum channel and a difference channel.',
  X: 'Bit flip is reversible relabeling: every 0-slot amplitude trades places with the 1-slot amplitude.',
  S: 'Phase turn stores information in direction: direct measurement may not notice it until a later mix.',
};

const initialState: State = { zero: { re: 1, im: 0 }, one: { re: 0, im: 0 } };

const add = (left: Complex, right: Complex): Complex => ({ re: left.re + right.re, im: left.im + right.im });
const sub = (left: Complex, right: Complex): Complex => ({ re: left.re - right.re, im: left.im - right.im });
const mulI = (value: Complex): Complex => ({ re: -value.im, im: value.re });
const scale = (value: Complex, factor: number): Complex => ({ re: value.re * factor, im: value.im * factor });
const abs2 = (value: Complex) => value.re * value.re + value.im * value.im;

function arrowEnd(value: Complex) {
  return {
    x: 50 + value.re * 34,
    y: 50 - value.im * 34,
  };
}

function applyGate(state: State, gate: Gate): State {
  if (gate === 'X') {
    return { zero: state.one, one: state.zero };
  }
  if (gate === 'H') {
    const factor = 1 / Math.sqrt(2);
    return {
      zero: scale(add(state.zero, state.one), factor),
      one: scale(sub(state.zero, state.one), factor),
    };
  }
  if (gate === 'S') {
    return { zero: state.zero, one: mulI(state.one) };
  }
  return state;
}

const fmt = (value: number) => value.toFixed(2);

function AmplitudeWheel({ state, title, detail }: { state: State; title: string; detail: string }) {
  const zeroArrow = arrowEnd(state.zero);
  const oneArrow = arrowEnd(state.one);
  const p0 = abs2(state.zero);
  const p1 = abs2(state.one);

  return (
    <figure className="steering-snapshot">
      <figcaption>
        <strong>{title}</strong>
        <span>{detail}</span>
      </figcaption>
      <svg className="amplitude-arrows" viewBox="0 0 100 100" role="img" aria-label={`${title} amplitude arrows`}>
        <circle cx="50" cy="50" r="38" />
        <line className="axis" x1="12" y1="50" x2="88" y2="50" />
        <line className="axis" x1="50" y1="12" x2="50" y2="88" />
        <line className="zero-arrow" x1="50" y1="50" x2={zeroArrow.x} y2={zeroArrow.y} />
        <circle className="zero-dot" cx={zeroArrow.x} cy={zeroArrow.y} r="3" />
        <line className="one-arrow" x1="50" y1="50" x2={oneArrow.x} y2={oneArrow.y} />
        <circle className="one-dot" cx={oneArrow.x} cy={oneArrow.y} r="3" />
      </svg>
      <div className="snapshot-probability-row">
        <span>|0|²={fmt(p0)}</span>
        <span>|1|²={fmt(p1)}</span>
      </div>
    </figure>
  );
}

export function BlochPlayground() {
  const [gates, setGates] = useState<RealGate[]>([]);
  const state = useMemo(() => gates.reduce(applyGate, initialState), [gates]);
  const previousState = useMemo(() => gates.slice(0, -1).reduce(applyGate, initialState), [gates]);
  const lastGate = gates.at(-1);
  const p0 = abs2(state.zero);
  const p1 = abs2(state.one);

  return (
    <article className="lab-panel" data-testid="bloch-playground">
      <div className="panel-heading">
        <Atom size={20} />
        <h3>Qubit steering</h3>
      </div>
      <div className="amplitude-legend steering-legend" aria-hidden="true">
        <span><i className="zero-dot" /> 0-amplitude</span>
        <span><i className="one-dot" /> 1-amplitude</span>
      </div>
      <div className="steering-comparison-grid">
        <AmplitudeWheel
          detail={lastGate ? `state before applying ${gateLabels[lastGate]}` : 'prepared as definite 0'}
          state={previousState}
          title={lastGate ? 'Before last gate' : 'Starting state'}
        />
        <article className="gate-transform-card">
          {lastGate ? (
            <>
              <span>last gate</span>
              <strong>{gateLabels[lastGate]}</strong>
              <MathTex tex={gateFormulas[lastGate]} />
              <p>{gateLessons[lastGate]}</p>
            </>
          ) : (
            <>
              <span>start</span>
              <strong>No gate yet</strong>
              <MathTex tex="|\psi\rangle=1|0\rangle+0|1\rangle" />
              <p>Choose a gate below. The left panel will keep the before-state and the right panel will show the after-state.</p>
            </>
          )}
        </article>
        <AmplitudeWheel
          detail={lastGate ? `state after applying ${gateLabels[lastGate]}` : 'unchanged until a gate is chosen'}
          state={state}
          title={lastGate ? 'After last gate' : 'Current state'}
        />
      </div>
      <p className="steering-note">One qubit is still one state; this view draws its two amplitudes separately. The two circles show how one gate transforms them from before to after.</p>
      <div className="gate-row steering-gate-row" aria-label="One-qubit gate choices">
        {steerableGates.map((gate) => (
          <button key={gate} type="button" onClick={() => setGates((items) => [...items, gate])}>
            <strong>{gateLabels[gate]}</strong>
            <span>{gateDescriptions[gate]}</span>
          </button>
        ))}
        <button className="icon-only" type="button" aria-label="Reset qubit" onClick={() => setGates([])}>
          <RotateCcw size={16} />
        </button>
      </div>
      <p className="mono-line">|0|²={fmt(p0)} |1|²={fmt(p1)} sequence = {gates.join(' ') || 'I'}</p>
      <p>
        Try the gates in sequence. Hadamard mixes amplitudes, bit flip swaps outcomes,
        and phase turn changes an angle that only becomes visible after later mixing.
      </p>
    </article>
  );
}
