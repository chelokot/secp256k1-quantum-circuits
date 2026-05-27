import { useMemo, useState } from 'react';
import { Sigma } from 'lucide-react';

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

  return (
    <article className="lab-panel" data-testid="phase-estimation-lab">
      <div className="panel-heading">
        <Sigma size={20} />
        <h3>Phase estimation lens</h3>
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
      <div className="qft-bars" aria-label="Inverse QFT measurement distribution">
        {bars.map((bar) => (
          <div className="qft-column" key={bar.value}>
            <div style={{ height: `${Math.max(6, (bar.weight / peak) * 92)}%` }} />
            <span>{formatBinary(bar.value, precisionBits)}</span>
          </div>
        ))}
      </div>
      <p className="mono-line">largest measurement peak: {formatBinary(measured.value, precisionBits)} ~= {measured.estimate.toFixed(3)}</p>
      <p>The inverse QFT concentrates a periodic phase into a binary label. In the real attack, the controlled operation is secp256k1 group arithmetic.</p>
    </article>
  );
}
