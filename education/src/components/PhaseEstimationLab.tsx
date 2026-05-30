import { useMemo, useState } from 'react';
import { Sigma } from 'lucide-react';
import { MathTex } from './MathText';

const formatBinary = (value: number, bits: number) => value.toString(2).padStart(bits, '0');

function circularDistance(left: number, right: number) {
  const raw = Math.abs(left - right);
  return Math.min(raw, 1 - raw);
}

export function PhaseEstimationLab() {
  const [phaseNumerator, setPhaseNumerator] = useState(3);
  const precisionBits = 4;
  const denominator = 16;
  const phase = phaseNumerator / denominator;
  const bars = useMemo(() => {
    return Array.from({ length: 2 ** precisionBits }, (_, value) => {
      const estimate = value / 2 ** precisionBits;
      const distance = circularDistance(phase, estimate);
      const weight = Math.exp(-95 * distance * distance);
      return { value, estimate, weight };
    });
  }, [phase]);
  const peak = Math.max(...bars.map((bar) => bar.weight));
  const measured = bars.reduce((best, row) => (row.weight > best.weight ? row : best), bars[0]);
  const handAngles = [1, 2, 4, 8].map((power) => 2 * Math.PI * ((phase * power) % 1));
  const measuredBits = formatBinary(measured.value, precisionBits);

  return (
    <article className="lab-panel" data-testid="phase-estimation-lab">
      <div className="panel-heading">
        <Sigma size={20} />
        <h3>Phase estimation lens</h3>
      </div>
      <p>
        A four-control example keeps the mechanism visible: controlled powers create
        a phase pattern, and the inverse QFT turns the pattern into the bit label
        below.
      </p>
      <div className="concept-bridge-grid" aria-label="Phase estimation reading order">
        <article>
          <span>1</span>
          <strong>Hidden phase</strong>
          <p>The slider chooses the repeating angle pattern the circuit must read.</p>
        </article>
        <article>
          <span>2</span>
          <strong>Controlled powers</strong>
          <p>The four clocks show powers 1, 2, 4, and 8 of that same phase.</p>
        </article>
        <article>
          <span>3</span>
          <strong>Bit label</strong>
          <p>The tallest bar is the binary estimate produced by the readout.</p>
        </article>
      </div>
      <label className="slider-label">
        Hidden phase numerator: {phaseNumerator}/16
        <input
          min="1"
          max="15"
          type="range"
          value={phaseNumerator}
          onChange={(event) => setPhaseNumerator(Number(event.currentTarget.value))}
        />
      </label>
      <div className="phasor-row" aria-label="Controlled powers as rotating phase hands">
        {handAngles.map((angle, index) => (
          <svg viewBox="0 0 70 70" className="phasor" key={index} role="img" aria-label={`power ${2 ** index}`}>
            <circle cx="35" cy="35" r="27" />
            <line x1="35" y1="35" x2={35 + Math.cos(angle) * 24} y2={35 + Math.sin(angle) * 24} />
            <text x="35" y="65">2^{index}</text>
          </svg>
        ))}
      </div>
      <div className="experiment-checklist">
        <span>Current readout</span>
        <strong>{phaseNumerator}/16 maps to {measuredBits}</strong>
        <p>
          In the real attack, secp256k1 group operations create the phase pattern.
          The readout shell is isolated here before curve arithmetic is added.
        </p>
      </div>
      <section className="matched-filter-ledger" aria-label="Inverse QFT matched-filter ledger">
        <article>
          <span>State written by controls</span>
          <strong>phase rhythm {phaseNumerator}/16</strong>
          <p>Controlled powers create a different rotation on each control bit.</p>
        </article>
        <article>
          <span>Readout test</span>
          <strong>try every 4-bit label</strong>
          <p>The inverse QFT behaves like a bank of rhythm matchers.</p>
        </article>
        <article>
          <span>Scoring rule</span>
          <strong>alignment wins</strong>
          <p><MathTex tex="\theta-y/16=0" /> makes arrows line up instead of cancel.</p>
        </article>
        <article>
          <span>Published sample</span>
          <strong>winner {measuredBits}</strong>
          <p>The tallest bar is the label that best matches the hidden phase.</p>
        </article>
      </section>
      <div className="qft-bars" aria-label="Inverse QFT measurement distribution">
        {bars.map((bar) => (
          <div className="qft-column" key={bar.value}>
            <div style={{ height: `${Math.max(6, (bar.weight / peak) * 92)}%` }} />
            <span>{formatBinary(bar.value, precisionBits)}</span>
          </div>
        ))}
      </div>
      <p className="mono-line">largest measurement peak: {measuredBits} ~= {measured.estimate.toFixed(3)}</p>
      <p>The inverse QFT concentrates a periodic phase into a binary label. In the real attack, the controlled operation is secp256k1 group arithmetic.</p>
    </article>
  );
}
