import { useMemo, useState } from 'react';
import * as d3 from 'd3';
import { Waves } from 'lucide-react';

type Complex = {
  re: number;
  im: number;
};

const sampleCount = 16;
const formatBinary = (value: number) => value.toString(2).padStart(4, '0');

const add = (left: Complex, right: Complex): Complex => ({ re: left.re + right.re, im: left.im + right.im });
const abs = (value: Complex) => Math.hypot(value.re, value.im);

function phasor(angle: number): Complex {
  return { re: Math.cos(angle), im: Math.sin(angle) };
}

function vectorSumFor(frequency: number, candidate: number) {
  return Array.from({ length: sampleCount }, (_, index) => {
    const angle = (2 * Math.PI * (frequency - candidate) * index) / sampleCount;
    return phasor(angle);
  }).reduce(add, { re: 0, im: 0 });
}

export function FourierLensLab() {
  const [frequency, setFrequency] = useState(3);
  const [candidateOutput, setCandidateOutput] = useState(3);

  const bars = useMemo(() => {
    return Array.from({ length: sampleCount }, (_, candidate) => {
      const vectorSum = vectorSumFor(frequency, candidate);
      return {
        candidate,
        weight: (abs(vectorSum) / sampleCount) ** 2,
        vectorLength: abs(vectorSum),
      };
    });
  }, [frequency]);
  const selectedSum = useMemo(() => vectorSumFor(frequency, candidateOutput), [candidateOutput, frequency]);
  const selectedLength = abs(selectedSum);
  const peak = bars.reduce((best, row) => (row.weight > best.weight ? row : best), bars[0]);
  const candidateGap = Math.min(Math.abs(frequency - candidateOutput), sampleCount - Math.abs(frequency - candidateOutput));
  const candidateStatus = candidateGap === 0 ? 'candidate matches hidden rhythm' : `candidate misses by ${candidateGap}/16`;
  const arrowScale = d3.scaleLinear([0, sampleCount], [0, 92]);
  const phaseArrows = Array.from({ length: sampleCount }, (_, index) => {
    const angle = (2 * Math.PI * (frequency - candidateOutput) * index) / sampleCount;
    return {
      index,
      angle,
      x2: 55 + Math.cos(angle) * 39,
      y2: 55 + Math.sin(angle) * 39,
    };
  });

  return (
    <article className="lab-panel" data-testid="fourier-lens-lab">
      <div className="panel-heading">
        <Waves size={20} />
        <h3>Fourier lens lab</h3>
      </div>
      <p>
        Inverse QFT is an angle-rhythm detector. For each possible output label it asks:
        if I subtract this candidate rhythm, do all arrows align?
      </p>

      <div className="fourier-controls">
        <label className="slider-label">
          Hidden angle rhythm: {frequency}/16
          <input
            aria-label="Fourier hidden frequency"
            max="15"
            min="0"
            onChange={(event) => setFrequency(Number(event.currentTarget.value))}
            type="range"
            value={frequency}
          />
        </label>
        <label className="slider-label">
          Candidate output: {candidateOutput}/16
          <input
            aria-label="Fourier candidate output"
            max="15"
            min="0"
            onChange={(event) => setCandidateOutput(Number(event.currentTarget.value))}
            type="range"
            value={candidateOutput}
          />
        </label>
      </div>
      <section className="candidate-score-strip" aria-label="Fourier candidate score">
        <article>
          <span>Hidden rhythm</span>
          <strong>{formatBinary(frequency)}</strong>
          <p>The circuit does not print this value directly; it writes it as rotating phase.</p>
        </article>
        <article>
          <span>Selected candidate</span>
          <strong>{formatBinary(candidateOutput)}</strong>
          <p>{candidateStatus}</p>
        </article>
        <article>
          <span>Alignment score</span>
          <strong>{selectedLength.toFixed(0)}/16</strong>
          <p>Full alignment survives as a measurement peak; spread arrows cancel.</p>
        </article>
        <article>
          <span>Winning output</span>
          <strong>{formatBinary(peak.candidate)}</strong>
          <p>The full distribution is the same scoring loop for every candidate.</p>
        </article>
      </section>

      <div className="fourier-grid">
        <article>
          <h4>Candidate arrow test</h4>
          <svg className="fourier-phasor-sum" viewBox="0 0 110 110" role="img" aria-label="Fourier candidate phasor sum">
            <circle cx="55" cy="55" r="43" />
            {phaseArrows.map((arrow) => (
              <line
                key={arrow.index}
                x1="55"
                x2={arrow.x2}
                y1="55"
                y2={arrow.y2}
              />
            ))}
            <circle className="sum-dot" cx={55 + (selectedSum.re / sampleCount) * 39} cy={55 + (selectedSum.im / sampleCount) * 39} r="4" />
          </svg>
          <p className="mono-line">
            vector sum length {selectedLength.toFixed(0)}/16 for candidate {formatBinary(candidateOutput)}
          </p>
          <p>
            Matching the hidden rhythm makes every arrow point the same way. Wrong labels
            spread the arrows around the circle and destructively interfere.
          </p>
        </article>

        <article>
          <h4>Inverse-QFT output distribution</h4>
          <div className="qft-bars" aria-label="Fourier lens output distribution">
            {bars.map((bar) => (
              <div className="qft-column" key={bar.candidate}>
                <div style={{ height: `${Math.max(5, bar.weight * 96)}%` }} />
                <span>{formatBinary(bar.candidate)}</span>
              </div>
            ))}
          </div>
          <p className="mono-line">peak: {formatBinary(peak.candidate)} with {(peak.weight * 100).toFixed(0)}%</p>
          <p>
            The real secp256k1 attack builds this angle rhythm with controlled group operations;
            the semiclassical inverse-QFT shell reads it out one bit at a time.
          </p>
        </article>
      </div>
    </article>
  );
}
