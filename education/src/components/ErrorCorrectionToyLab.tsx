import { useMemo, useState } from 'react';
import { ShieldCheck } from 'lucide-react';

type BaselineRow = {
  id: string;
  label: string;
  logicalQubits: number;
};

type ProjectData = {
  baselineRows: BaselineRow[];
};

const formatInt = (value: number) => new Intl.NumberFormat('en-US').format(value);

const choose = (n: number, k: number) => {
  let numerator = 1;
  let denominator = 1;
  for (let index = 1; index <= k; index += 1) {
    numerator *= n - (k - index);
    denominator *= index;
  }
  return numerator / denominator;
};

const logicalFailureProbability = (distance: number, physicalErrorRate: number) => {
  const threshold = Math.floor(distance / 2) + 1;
  let probability = 0;
  for (let errors = threshold; errors <= distance; errors += 1) {
    probability += choose(distance, errors) * physicalErrorRate ** errors * (1 - physicalErrorRate) ** (distance - errors);
  }
  return probability;
};

const formatProbability = (probability: number) => {
  if (probability === 0) return '0%';
  if (probability < 0.000001) return `${(probability * 100).toExponential(2)}%`;
  return `${(probability * 100).toFixed(6)}%`;
};

export function ErrorCorrectionToyLab({ projectData }: { projectData: ProjectData }) {
  const [selectedId, setSelectedId] = useState('repo_guard_corrected');
  const [distance, setDistance] = useState(5);
  const [errorBasisPoints, setErrorBasisPoints] = useState(100);
  const [manualErrorBits, setManualErrorBits] = useState<Set<number>>(() => new Set([1]));
  const selected = projectData.baselineRows.find((row) => row.id === selectedId) ?? projectData.baselineRows[0];
  const activeManualErrors = [...manualErrorBits].filter((bit) => bit < distance);
  const threshold = Math.floor(distance / 2) + 1;
  const manualPass = activeManualErrors.length < threshold;
  const physicalErrorRate = errorBasisPoints / 10_000;

  const metrics = useMemo(() => {
    const logicalFailure = logicalFailureProbability(distance, physicalErrorRate);
    const unencodedFailure = physicalErrorRate;
    const suppression = logicalFailure === 0 ? Number.POSITIVE_INFINITY : unencodedFailure / logicalFailure;
    return {
      logicalFailure,
      physicalCarriers: selected.logicalQubits * distance,
      suppression,
      toleratedErrors: threshold - 1,
    };
  }, [distance, physicalErrorRate, selected.logicalQubits, threshold]);

  const toggleBit = (bit: number) => {
    setManualErrorBits((previous) => {
      const next = new Set(previous);
      if (next.has(bit)) {
        next.delete(bit);
      } else {
        next.add(bit);
      }
      return next;
    });
  };

  return (
    <section className="wide-panel" data-testid="error-correction-toy-lab">
      <div className="panel-heading">
        <ShieldCheck size={20} />
        <h3>Error-correction toy</h3>
      </div>
      <p>
        This is a repetition-code intuition lab, not a hardware estimate. It shows why a
        logical qubit is an encoded object: several noisy physical carriers vote so a small
        number of physical errors does not flip the represented logical value.
      </p>
      <section className="error-correction-boundary" aria-label="Error correction toy boundary">
        <article>
          <strong>Carrier</strong>
          <p>One noisy physical bit in this toy repetition code.</p>
        </article>
        <article>
          <strong>Logical value</strong>
          <p>The majority value represented by the carrier block.</p>
        </article>
        <article>
          <strong>Boundary</strong>
          <p>This demonstrates encoding intuition, not a surface-code layout or decoder.</p>
        </article>
      </section>

      <div className="error-code-grid">
        <label>
          <span>Repo logical row</span>
          <select
            aria-label="Error correction resource row"
            value={selectedId}
            onChange={(event) => setSelectedId(event.currentTarget.value)}
          >
            {projectData.baselineRows.map((row) => (
              <option key={row.id} value={row.id}>{row.label}</option>
            ))}
          </select>
        </label>
        <label>
          <span>Code distance: {distance}</span>
          <input
            aria-label="Repetition code distance"
            min="1"
            max="9"
            step="2"
            type="range"
            value={distance}
            onChange={(event) => setDistance(Number(event.currentTarget.value))}
          />
        </label>
        <label>
          <span>Physical error rate: {(physicalErrorRate * 100).toFixed(2)}%</span>
          <input
            aria-label="Physical error rate"
            min="10"
            max="1000"
            step="10"
            type="range"
            value={errorBasisPoints}
            onChange={(event) => setErrorBasisPoints(Number(event.currentTarget.value))}
          />
        </label>
      </div>

      <div className="physical-bit-row" aria-label="Manual physical carrier errors">
        {Array.from({ length: distance }, (_, bit) => {
          const hasError = activeManualErrors.includes(bit);
          return (
            <button
              aria-label={`Physical carrier ${bit + 1}`}
              className={hasError ? 'physical-bit error' : 'physical-bit'}
              key={bit}
              onClick={() => toggleBit(bit)}
              type="button"
            >
              <strong>{hasError ? '1' : '0'}</strong>
              <span>{hasError ? 'error' : 'ok'}</span>
            </button>
          );
        })}
      </div>

      <div className={manualPass ? 'audit-pass' : 'audit-fail'}>
        Manual decode: {manualPass ? 'pass' : 'fail'} by majority vote ({activeManualErrors.length}/{distance} errors,
        tolerates {metrics.toleratedErrors})
      </div>

      <div className="error-code-summary">
        <article>
          <span>Logical row</span>
          <strong>{formatInt(selected.logicalQubits)}q</strong>
          <p>{selected.label}</p>
        </article>
        <article>
          <span>Toy physical carriers</span>
          <strong>{formatInt(metrics.physicalCarriers)}</strong>
          <p>{formatInt(selected.logicalQubits)} logical * distance {distance}</p>
        </article>
        <article>
          <span>Logical failure probability</span>
          <strong>{formatProbability(metrics.logicalFailure)}</strong>
          <p>binomial majority-failure tail</p>
        </article>
        <article>
          <span>Suppression vs unencoded</span>
          <strong>{metrics.suppression.toFixed(1)}x</strong>
          <p>toy intuition only</p>
        </article>
      </div>
    </section>
  );
}
