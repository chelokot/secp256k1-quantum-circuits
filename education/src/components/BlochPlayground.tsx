import { useMemo, useState } from 'react';
import { Atom, RotateCcw } from 'lucide-react';

type Gate = 'I' | 'X' | 'H' | 'S';

type Complex = { re: number; im: number };
type State = { zero: Complex; one: Complex };

const steerableGates = ['H', 'X', 'S'] as const;

const gateLabels: Record<Exclude<Gate, 'I'>, string> = {
  H: 'Hadamard',
  X: 'Bit flip',
  S: 'Phase turn',
};

const gateDescriptions: Record<Exclude<Gate, 'I'>, string> = {
  H: 'mixes 0 and 1 amplitudes',
  X: 'swaps the 0 and 1 amplitudes',
  S: 'rotates only the 1-amplitude phase',
};

const initialState: State = { zero: { re: 1, im: 0 }, one: { re: 0, im: 0 } };

const add = (left: Complex, right: Complex): Complex => ({ re: left.re + right.re, im: left.im + right.im });
const sub = (left: Complex, right: Complex): Complex => ({ re: left.re - right.re, im: left.im - right.im });
const mulI = (value: Complex): Complex => ({ re: -value.im, im: value.re });
const scale = (value: Complex, factor: number): Complex => ({ re: value.re * factor, im: value.im * factor });
const abs2 = (value: Complex) => value.re * value.re + value.im * value.im;

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

export function BlochPlayground() {
  const [gates, setGates] = useState<Gate[]>([]);
  const state = useMemo(() => gates.reduce(applyGate, initialState), [gates]);
  const p0 = abs2(state.zero);
  const p1 = abs2(state.one);
  const vectorX = 50 + (p1 - p0) * 26;
  const vectorY = 50 - state.one.re * 34;

  return (
    <article className="lab-panel" data-testid="bloch-playground">
      <div className="panel-heading">
        <Atom size={20} />
        <h3>Qubit steering</h3>
      </div>
      <svg className="bloch-svg" viewBox="0 0 100 100" role="img" aria-label="Simplified qubit state visualizer">
        <circle cx="50" cy="50" r="38" />
        <line x1="12" y1="50" x2="88" y2="50" />
        <line x1="50" y1="12" x2="50" y2="88" />
        <line className="state-vector" x1="50" y1="50" x2={vectorX} y2={vectorY} />
        <circle className="state-dot" cx={vectorX} cy={vectorY} r="3" />
      </svg>
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
      <p className="mono-line">|0|²={fmt(p0)} |1|²={fmt(p1)} gates={gates.join(' ') || 'I'}</p>
      <p>
        Try the gates in sequence. Hadamard mixes amplitudes, bit flip swaps outcomes,
        and phase turn changes an angle that only becomes visible after later mixing.
      </p>
    </article>
  );
}
