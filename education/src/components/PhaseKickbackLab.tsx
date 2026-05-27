import { useMemo, useState } from 'react';
import { Waves } from 'lucide-react';

const order = 13;

const mod = (value: number) => ((value % order) + order) % order;

const inverseMod = (value: number) => {
  for (let candidate = 1; candidate < order; candidate += 1) {
    if (mod(value * candidate) === 1) {
      return candidate;
    }
  }
  return 1;
};

const phaseColor = (phase: number) => `hsl(${Math.round((phase / order) * 300 + 35)} 78% 62%)`;

export function PhaseKickbackLab() {
  const [secret, setSecret] = useState(5);
  const [frequency, setFrequency] = useState(3);
  const [aScalar, setAScalar] = useState(4);
  const [bScalar, setBScalar] = useState(2);

  const derived = useMemo(() => {
    const output = mod(aScalar + bScalar * secret);
    const phaseExponent = mod(frequency * output);
    const gradientA = frequency;
    const gradientB = mod(frequency * secret);
    const recoveredSecret = mod(gradientB * inverseMod(gradientA));
    const shiftedA = mod(aScalar + secret);
    const shiftedB = mod(bScalar - 1);
    const shiftedOutput = mod(shiftedA + shiftedB * secret);
    const periodDot = mod(gradientA * secret - gradientB);
    const cells = Array.from({ length: order * order }, (_, index) => {
      const a = index % order;
      const b = Math.floor(index / order);
      const cellOutput = mod(a + b * secret);
      const phase = mod(frequency * cellOutput);
      return {
        a,
        b,
        phase,
        selected: a === aScalar && b === bScalar,
        shifted: a === shiftedA && b === shiftedB,
      };
    });
    return {
      cells,
      output,
      phaseExponent,
      gradientA,
      gradientB,
      recoveredSecret,
      shiftedA,
      shiftedB,
      shiftedOutput,
      periodDot,
    };
  }, [aScalar, bScalar, frequency, secret]);

  return (
    <section className="wide-panel" data-testid="phase-kickback-lab">
      <div className="panel-heading">
        <Waves size={20} />
        <h3>Phase-kickback hidden-period lab</h3>
      </div>
      <p>
        A Shor-style circuit does not read every oracle output. It can put the
        output register into a Fourier label and let <code>f(a,b) = a + b*d</code>
        kick back a phase onto the input lattice. The hidden period becomes a
        direction where the color does not change.
      </p>

      <div className="kickback-controls">
        <label>
          <span>Secret d: {secret}</span>
          <input
            aria-label="Kickback secret scalar"
            min="1"
            max="12"
            type="range"
            value={secret}
            onChange={(event) => setSecret(Number(event.currentTarget.value))}
          />
        </label>
        <label>
          <span>Fourier label t: {frequency}</span>
          <input
            aria-label="Kickback Fourier label"
            min="1"
            max="12"
            type="range"
            value={frequency}
            onChange={(event) => setFrequency(Number(event.currentTarget.value))}
          />
        </label>
        <label>
          <span>a register: {aScalar}</span>
          <input
            aria-label="Kickback a register"
            min="0"
            max="12"
            type="range"
            value={aScalar}
            onChange={(event) => setAScalar(Number(event.currentTarget.value))}
          />
        </label>
        <label>
          <span>b register: {bScalar}</span>
          <input
            aria-label="Kickback b register"
            min="0"
            max="12"
            type="range"
            value={bScalar}
            onChange={(event) => setBScalar(Number(event.currentTarget.value))}
          />
        </label>
      </div>

      <div className="kickback-grid-layout">
        <svg className="kickback-grid-svg" viewBox="0 0 156 156" role="img" aria-label="Phase kickback lattice">
          {derived.cells.map((cell) => (
            <g key={`${cell.a}-${cell.b}`}>
              <rect
                className={cell.selected ? 'selected' : cell.shifted ? 'shifted' : ''}
                x={cell.a * 12}
                y={(order - 1 - cell.b) * 12}
                width="11"
                height="11"
                style={{ fill: phaseColor(cell.phase) }}
              />
              {(cell.selected || cell.shifted) && (
                <text x={cell.a * 12 + 5.5} y={(order - 1 - cell.b) * 12 + 8}>{cell.selected ? 'A' : 'P'}</text>
              )}
            </g>
          ))}
        </svg>

        <div className="kickback-readout">
          <article>
            <span>Oracle output</span>
            <strong>a + b*d = {derived.output} mod 13</strong>
            <p>The selected input is ({aScalar}, {bScalar}) with Q = {secret}G.</p>
          </article>
          <article>
            <span>Kicked-back phase</span>
            <strong>phase exponent = {derived.phaseExponent}</strong>
            <p>The Fourier label t multiplies the oracle output before the output register is uncomputed.</p>
          </article>
          <article>
            <span>Fourier gradient</span>
            <strong>({derived.gradientA}, {derived.gradientB})</strong>
            <p>Because t * (a + b*d) has slope t*d in the b direction.</p>
          </article>
          <article>
            <span>Hidden period check</span>
            <strong>dot((d,-1), gradient) = {derived.periodDot} mod 13</strong>
            <p>Shift to ({derived.shiftedA}, {derived.shiftedB}) keeps output {derived.shiftedOutput} and the same phase.</p>
          </article>
          <article>
            <span>Recover d from a sample</span>
            <strong>d = {derived.gradientB} * inverse({derived.gradientA}) = {derived.recoveredSecret}</strong>
            <p>This toy sample is clean; the real phase-estimation shell uses many bits and continued-fraction style recovery.</p>
          </article>
        </div>
      </div>
    </section>
  );
}
