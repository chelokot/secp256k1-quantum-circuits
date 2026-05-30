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
  const [candidateValue, setCandidateValue] = useState(3);
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
  const candidate = bars[candidateValue];
  const candidateBits = formatBinary(candidateValue, precisionBits);
  const candidatePhaseGap = phase - candidate.estimate;
  const candidateScore = Math.round((candidate.weight / peak) * 100);
  const candidateArrows = Array.from({ length: denominator }, (_, index) => (
    2 * Math.PI * index * candidatePhaseGap
  ));

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
          <svg viewBox="0 0 70 78" className="phasor" key={index} role="img" aria-label={`power ${2 ** index}`}>
            <circle cx="35" cy="35" r="27" />
            <line x1="35" y1="35" x2={35 + Math.cos(angle) * 24} y2={35 + Math.sin(angle) * 24} />
            <text x="35" y="73">2^{index}</text>
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
      <section className="candidate-inspector" aria-label="Candidate rhythm inspector">
        <div>
          <h4>Test one candidate label</h4>
          <p>
            Pick a 4-bit label and watch the matcher subtract that rhythm from the
            hidden phase. Aligned arrows mean reinforcement; a rotating walk means cancellation.
          </p>
          <label>
            Candidate label
            <select
              aria-label="Candidate phase label"
              value={candidateValue}
              onChange={(event) => setCandidateValue(Number(event.currentTarget.value))}
            >
              {bars.map((bar) => (
                <option key={bar.value} value={bar.value}>{formatBinary(bar.value, precisionBits)}</option>
              ))}
            </select>
          </label>
          <p className="mono-line">
            test {candidateBits}: theta - y/16 = {(candidatePhaseGap).toFixed(3)}
          </p>
        </div>
        <svg viewBox="0 0 180 130" role="img" aria-label="Candidate arrow sum">
          <circle cx="64" cy="64" r="42" />
          <line className="axis" x1="22" y1="64" x2="106" y2="64" />
          <line className="axis" x1="64" y1="22" x2="64" y2="106" />
          {candidateArrows.map((angle, index) => (
            <line
              className="candidate-arrow"
              key={index}
              x1="64"
              y1="64"
              x2={64 + Math.cos(angle) * 36}
              y2={64 + Math.sin(angle) * 36}
            />
          ))}
          <text x="124" y="52">score</text>
          <text className={candidateScore > 80 ? 'candidate-pass' : 'candidate-fail'} x="124" y="76">{candidateScore}%</text>
        </svg>
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
