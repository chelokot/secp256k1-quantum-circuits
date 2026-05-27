import { useMemo, useState } from 'react';
import { Waves } from 'lucide-react';
import { MathTex } from './MathText';

const formatPercent = (value: number) => `${Math.round(value * 100)}%`;

type Complex = {
  re: number;
  im: number;
};

const invSqrt2 = 1 / Math.sqrt(2);

function arrowEnd(value: Complex, scale: number) {
  return {
    x: 50 + value.re * scale,
    y: 50 - value.im * scale,
  };
}

const abs2 = (value: Complex) => value.re * value.re + value.im * value.im;

export function QubitAmplitudeBridgeLab() {
  const [phaseDegrees, setPhaseDegrees] = useState(0);
  const phaseRadians = (phaseDegrees / 180) * Math.PI;
  const inputZero = useMemo<Complex>(() => ({ re: invSqrt2, im: 0 }), []);
  const inputOne = useMemo<Complex>(() => ({
    re: Math.cos(phaseRadians) * invSqrt2,
    im: Math.sin(phaseRadians) * invSqrt2,
  }), [phaseRadians]);
  const outputZero = useMemo<Complex>(() => ({
    re: (inputZero.re + inputOne.re) * invSqrt2,
    im: (inputZero.im + inputOne.im) * invSqrt2,
  }), [inputOne, inputZero]);
  const outputOne = useMemo<Complex>(() => ({
    re: (inputZero.re - inputOne.re) * invSqrt2,
    im: (inputZero.im - inputOne.im) * invSqrt2,
  }), [inputOne, inputZero]);
  const directP0 = abs2(inputZero);
  const directP1 = abs2(inputOne);
  const afterHP0 = abs2(outputZero);
  const afterHP1 = abs2(outputOne);
  const inputZeroArrow = arrowEnd(inputZero, 38);
  const inputOneArrow = arrowEnd(inputOne, 38);
  const outputZeroArrow = arrowEnd(outputZero, 38);
  const outputOneArrow = arrowEnd(outputOne, 38);
  const phaseObservation = phaseDegrees === 0
    ? 'same direction: Hadamard makes outcome 0 certain'
    : phaseDegrees === 180
      ? 'opposite direction: Hadamard makes outcome 1 certain'
      : 'between the extremes: Hadamard turns angle into a probability split';

  return (
    <article className="lab-panel" data-testid="qubit-amplitude-bridge-lab">
      <div className="panel-heading">
        <Waves size={20} />
        <h3>Phase becomes probability</h3>
      </div>
      <p>
        Start with two equal-length arrows: the 0-amplitude and the 1-amplitude.
        Equal lengths mean direct measurement is 50/50. Move only the angle of the
        1-arrow: direct measurement still sees 50/50. Then the Hadamard gate combines
        the two arrows, so their angle changes the final chances.
      </p>

      <section className="gate-explainer" aria-label="Hadamard gate explanation">
        <h4>From state vector to gate</h4>
        <p>
          A gate is a controlled physical operation applied before measurement. In
          hardware it is a calibrated pulse or interaction. In the circuit model it is
          a function from the old amplitude vector to a new amplitude vector.
        </p>
        <div className="math-stack" aria-label="One-qubit state and linear gate formulas">
          <div className="math-line">
            <span className="math-label">state</span>
            <MathTex tex="|\psi\rangle = a|0\rangle + b|1\rangle,\quad |a|^2 + |b|^2 = 1" />
          </div>
          <div className="matrix-equation">
            <span className="math-label">linear gate</span>
            <MathTex tex="\begin{bmatrix} a' \\ b' \end{bmatrix} = \begin{bmatrix} \alpha & \beta \\ \gamma & \delta \end{bmatrix}\begin{bmatrix} a \\ b \end{bmatrix}" />
          </div>
          <div className="math-line">
            <span className="math-label">same rule</span>
            <MathTex tex="a'=\alpha a+\beta b,\quad b'=\gamma a+\delta b" />
          </div>
        </div>
        <p>
          Linearity means the whole candidate gate is described by four complex
          coefficients. That still allows nonsense rules, so quantum mechanics adds
          the validity condition.
        </p>
        <h4>Valid gates are unitary</h4>
        <p>
          <strong>Unitary</strong> means the rule is linear, reversible, and preserves
          the total probability for every possible input state.
        </p>
        <div className="math-stack" aria-label="Unitary normalization constraints">
          <div className="math-line">
            <span className="math-label">compact test</span>
            <MathTex tex="U^\dagger U = I" />
          </div>
          <div className="math-line">
            <span className="math-label">columns</span>
            <MathTex tex="|\alpha|^2+|\gamma|^2=1,\quad |\beta|^2+|\delta|^2=1,\quad \overline{\alpha}\beta+\overline{\gamma}\delta=0" />
          </div>
        </div>
        <p>
          So a one-qubit gate is not any formula someone writes down. All complex
          2×2 linear maps start with eight real knobs. The unitary equations cut that
          down to four real knobs, and one global phase is physically invisible, so a
          one-qubit gate has three physical knobs.
        </p>
        <h4>First example: Hadamard</h4>
        <div className="matrix-equation hadamard-equation" aria-label="Hadamard matrix">
          <MathTex tex="H=\frac{1}{\sqrt{2}}\begin{bmatrix}1&1\\1&-1\end{bmatrix}" />
        </div>
        <div className="math-stack" aria-label="Hadamard output amplitudes">
          <div className="math-line">
            <span className="math-label">output</span>
            <MathTex tex="a'=\frac{a+b}{\sqrt{2}},\quad b'=\frac{a-b}{\sqrt{2}}" />
          </div>
        </div>
        <p>
          Semantically, Hadamard makes a sum channel and a difference channel. Same
          direction arrows reinforce the sum. Opposite direction arrows cancel the
          sum. In-between angles produce a probability split.
        </p>
      </section>

      <label className="slider-label">
        <span>Relative angle: {phaseDegrees} degrees</span>
        <input
          aria-label="Relative amplitude angle"
          max="180"
          min="0"
          onChange={(event) => setPhaseDegrees(Number(event.currentTarget.value))}
          step="15"
          type="range"
          value={phaseDegrees}
        />
      </label>

      <div className="amplitude-bridge-grid">
        <div className="amplitude-visual-stack">
          <div className="amplitude-legend" aria-hidden="true">
            <span><i className="zero-dot" /> 0-arrow</span>
            <span><i className="one-dot" /> 1-arrow</span>
          </div>
          <div className="amplitude-snapshot-grid">
            <figure>
              <figcaption>Before Hadamard</figcaption>
              <svg className="amplitude-arrows" viewBox="0 0 100 100" role="img" aria-label="Input amplitude arrows before Hadamard">
                <circle cx="50" cy="50" r="38" />
                <line className="axis" x1="12" y1="50" x2="88" y2="50" />
                <line className="axis" x1="50" y1="12" x2="50" y2="88" />
                <line className="zero-arrow" x1="50" y1="50" x2={inputZeroArrow.x} y2={inputZeroArrow.y} />
                <circle className="zero-dot" cx={inputZeroArrow.x} cy={inputZeroArrow.y} r="3" />
                <line className="one-arrow" x1="50" y1="50" x2={inputOneArrow.x} y2={inputOneArrow.y} />
                <circle className="one-dot" cx={inputOneArrow.x} cy={inputOneArrow.y} r="3" />
              </svg>
            </figure>
            <figure>
              <figcaption>After Hadamard</figcaption>
              <svg className="amplitude-arrows" viewBox="0 0 100 100" role="img" aria-label="Output amplitude arrows after Hadamard">
                <circle cx="50" cy="50" r="38" />
                <line className="axis" x1="12" y1="50" x2="88" y2="50" />
                <line className="axis" x1="50" y1="12" x2="50" y2="88" />
                <line className="zero-arrow" x1="50" y1="50" x2={outputZeroArrow.x} y2={outputZeroArrow.y} />
                <circle className="zero-dot" cx={outputZeroArrow.x} cy={outputZeroArrow.y} r="3" />
                <line className="one-arrow" x1="50" y1="50" x2={outputOneArrow.x} y2={outputOneArrow.y} />
                <circle className="one-dot" cx={outputOneArrow.x} cy={outputOneArrow.y} r="3" />
              </svg>
            </figure>
          </div>
        </div>

        <div className="amplitude-readout">
          <div>
            <span>Measure now</span>
            <strong>0: {formatPercent(directP0)} / 1: {formatPercent(directP1)}</strong>
            <p>Arrow lengths are unchanged, so direct probabilities are unchanged.</p>
          </div>
          <div>
            <span>Apply Hadamard, then measure</span>
            <strong>0: {formatPercent(afterHP0)} / 1: {formatPercent(afterHP1)}</strong>
            <p>Hadamard mixes the arrows. Same direction reinforces 0; opposite direction cancels 0.</p>
          </div>
        </div>
      </div>

      <div className="experiment-checklist">
        <span>Current observation</span>
        <strong>{phaseObservation}</strong>
        <p>
          The slider never changes the arrow lengths. It only changes the hidden
          angle relationship that a later gate can expose.
        </p>
      </div>

      <div className="mono-line">
        <MathTex tex={`|\\psi\\rangle=(|0\\rangle+e^{i${phaseDegrees}^{\\circ}}|1\\rangle)/\\sqrt{2}`} />
      </div>
    </article>
  );
}
