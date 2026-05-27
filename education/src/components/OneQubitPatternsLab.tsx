import { useMemo, useState } from 'react';
import { GitCompareArrows } from 'lucide-react';

type Gate = 'H' | 'X' | 'S';
type Complex = { re: number; im: number };
type State = { zero: Complex; one: Complex };

const zero: Complex = { re: 0, im: 0 };
const one: Complex = { re: 1, im: 0 };
const initialState: State = { zero: one, one: zero };
const presets = {
  hh: { label: 'Hadamard twice', sequence: ['H', 'H'] as Gate[], result: 'returns to the starting state' },
  xx: { label: 'Bit flip twice', sequence: ['X', 'X'] as Gate[], result: 'returns to the starting state' },
  ssss: { label: 'Four phase turns', sequence: ['S', 'S', 'S', 'S'] as Gate[], result: 'rotates phase through a cycle' },
  hsh: { label: 'Mix, phase, mix', sequence: ['H', 'S', 'H'] as Gate[], result: 'turns hidden phase into new probabilities' },
};

const add = (left: Complex, right: Complex): Complex => ({ re: left.re + right.re, im: left.im + right.im });
const sub = (left: Complex, right: Complex): Complex => ({ re: left.re - right.re, im: left.im - right.im });
const mulI = (value: Complex): Complex => ({ re: -value.im, im: value.re });
const scale = (value: Complex, factor: number): Complex => ({ re: value.re * factor, im: value.im * factor });
const abs2 = (value: Complex) => value.re * value.re + value.im * value.im;

function applyGate(state: State, gate: Gate): State {
  if (gate === 'X') return { zero: state.one, one: state.zero };
  if (gate === 'S') return { zero: state.zero, one: mulI(state.one) };
  const factor = 1 / Math.sqrt(2);
  return {
    zero: scale(add(state.zero, state.one), factor),
    one: scale(sub(state.zero, state.one), factor),
  };
}

function arrowEnd(value: Complex) {
  return {
    x: 50 + value.re * 34,
    y: 50 - value.im * 34,
  };
}

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

export function OneQubitPatternsLab() {
  const [selected, setSelected] = useState<keyof typeof presets>('hsh');
  const preset = presets[selected];
  const state = useMemo(() => preset.sequence.reduce(applyGate, initialState), [preset]);
  const zeroArrow = arrowEnd(state.zero);
  const oneArrow = arrowEnd(state.one);
  const p0 = abs2(state.zero);
  const p1 = abs2(state.one);

  return (
    <article className="lab-panel" data-testid="one-qubit-patterns-lab">
      <div className="panel-heading">
        <GitCompareArrows size={20} />
        <h3>One-qubit gate patterns</h3>
      </div>
      <p>
        One-qubit gates can rotate, swap, and recombine amplitudes. They are useful,
        but closed quantum gates are reversible, so they do not behave like attractors.
      </p>
      <div className="one-qubit-capability-row">
        <article>
          <strong>Prepare a split</strong>
          <p>Hadamard turns a definite 0 into a balanced 0/1 state.</p>
        </article>
        <article>
          <strong>Rename outcomes</strong>
          <p>Bit flip swaps the 0 and 1 labels without deleting either branch.</p>
        </article>
        <article>
          <strong>Store a hidden angle</strong>
          <p>Phase turn changes direction, which later mixing can expose.</p>
        </article>
      </div>
      <div className="pattern-choice-row">
        {Object.entries(presets).map(([id, item]) => (
          <button
            aria-pressed={selected === id}
            key={id}
            onClick={() => setSelected(id as keyof typeof presets)}
            type="button"
          >
            <strong>{item.label}</strong>
            <span>{item.sequence.join(' ')}</span>
          </button>
        ))}
      </div>
      <div className="pattern-lab-grid">
        <section className="pattern-state-panel" aria-label="Selected one-qubit state">
          <div className="amplitude-legend" aria-hidden="true">
            <span><i className="zero-dot" /> 0-amplitude</span>
            <span><i className="one-dot" /> 1-amplitude</span>
          </div>
          <svg className="amplitude-arrows" viewBox="0 0 100 100" role="img" aria-label="Two amplitude arrows after the selected gate sequence">
            <circle cx="50" cy="50" r="38" />
            <line className="axis" x1="12" y1="50" x2="88" y2="50" />
            <line className="axis" x1="50" y1="12" x2="50" y2="88" />
            <line className="zero-arrow" x1="50" y1="50" x2={zeroArrow.x} y2={zeroArrow.y} />
            <circle className="zero-dot" cx={zeroArrow.x} cy={zeroArrow.y} r="3" />
            <line className="one-arrow" x1="50" y1="50" x2={oneArrow.x} y2={oneArrow.y} />
            <circle className="one-dot" cx={oneArrow.x} cy={oneArrow.y} r="3" />
          </svg>
          <div className="pattern-probabilities">
            <div><span>Measure 0</span><strong>{formatPercent(p0)}</strong></div>
            <div><span>Measure 1</span><strong>{formatPercent(p1)}</strong></div>
          </div>
          <p className="mono-line">sequence = {preset.sequence.join(' ')}; {preset.result}</p>
        </section>
        <section className="pattern-explainer" aria-label="One-qubit gate intuitions">
          <article>
            <strong>Cycles and groups</strong>
            <p>
              Some gates form visible cycles: <span className="pattern-formula">X² = I</span>,
              <span className="pattern-formula">H² = I</span>, and
              <span className="pattern-formula">S⁴ = I</span>. Repeating them walks around
              a reversible pattern.
            </p>
          </article>
          <article>
            <strong>No attractor under gates</strong>
            <p>
              A closed gate has an inverse. If many different states all converged to one point,
              you could not reverse the motion and recover which state you started from.
            </p>
          </article>
          <article>
            <strong>Measurement is different</strong>
            <p>
              Measurement samples one outcome and changes what remains. That collapse is not the
              same thing as a reversible gate step.
            </p>
          </article>
        </section>
      </div>
    </article>
  );
}
