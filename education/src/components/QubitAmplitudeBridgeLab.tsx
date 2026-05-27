import { useMemo, useState } from 'react';
import { Waves } from 'lucide-react';

const formatPercent = (value: number) => `${Math.round(value * 100)}%`;

function arrowEnd(angleRadians: number, length: number) {
  return {
    x: 50 + Math.cos(angleRadians) * length,
    y: 50 - Math.sin(angleRadians) * length,
  };
}

export function QubitAmplitudeBridgeLab() {
  const [phaseDegrees, setPhaseDegrees] = useState(0);
  const phaseRadians = (phaseDegrees / 180) * Math.PI;
  const directP0 = 0.5;
  const directP1 = 0.5;
  const afterHP0 = useMemo(() => (1 + Math.cos(phaseRadians)) / 2, [phaseRadians]);
  const afterHP1 = 1 - afterHP0;
  const zeroArrow = arrowEnd(0, 30);
  const oneArrow = arrowEnd(phaseRadians, 30);
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

      <div className="concept-bridge-grid" aria-label="Qubit reading order">
        <article>
          <span>1</span>
          <strong>Two arrows</strong>
          <p>The state has one amplitude for 0 and one amplitude for 1.</p>
        </article>
        <article>
          <span>2</span>
          <strong>Lengths become chances</strong>
          <p>Equal lengths give equal direct measurement probabilities.</p>
        </article>
        <article>
          <span>3</span>
          <strong>Angle waits for a gate</strong>
          <p>The Hadamard gate mixes the arrows, so their relative angle becomes visible.</p>
        </article>
      </div>

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
        <div>
          <div className="amplitude-legend" aria-hidden="true">
            <span><i className="zero-dot" /> 0-arrow</span>
            <span><i className="one-dot" /> 1-arrow</span>
          </div>
          <svg className="amplitude-arrows" viewBox="0 0 100 100" role="img" aria-label="Two complex amplitude arrows">
            <circle cx="50" cy="50" r="38" />
            <line className="axis" x1="12" y1="50" x2="88" y2="50" />
            <line className="axis" x1="50" y1="12" x2="50" y2="88" />
            <line className="zero-arrow" x1="50" y1="50" x2={zeroArrow.x} y2={zeroArrow.y} />
            <circle className="zero-dot" cx={zeroArrow.x} cy={zeroArrow.y} r="3" />
            <line className="one-arrow" x1="50" y1="50" x2={oneArrow.x} y2={oneArrow.y} />
            <circle className="one-dot" cx={oneArrow.x} cy={oneArrow.y} r="3" />
          </svg>
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

      <p className="mono-line">state = (|0&gt; + phase({phaseDegrees}deg) * |1&gt;) / sqrt(2)</p>
    </article>
  );
}
