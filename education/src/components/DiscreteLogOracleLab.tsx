import { useMemo, useState } from 'react';
import { KeyRound } from 'lucide-react';

const order = 13;

const mod = (value: number) => ((value % order) + order) % order;

export function DiscreteLogOracleLab() {
  const [secret, setSecret] = useState(5);
  const [aScalar, setAScalar] = useState(4);
  const [bScalar, setBScalar] = useState(2);

  const derived = useMemo(() => {
    const outputScalar = mod(aScalar + bScalar * secret);
    const collision = {
      a: mod(aScalar + secret),
      b: mod(bScalar - 1),
    };
    const collisionOutput = mod(collision.a + collision.b * secret);
    const cells = Array.from({ length: order * order }, (_, index) => {
      const a = index % order;
      const b = Math.floor(index / order);
      const output = mod(a + b * secret);
      const selected = a === aScalar && b === bScalar;
      const paired = a === collision.a && b === collision.b;
      return { a, b, output, selected, paired };
    });
    return {
      outputScalar,
      collision,
      collisionOutput,
      cells,
      periodVector: `(+${secret}, -1)`,
    };
  }, [aScalar, bScalar, secret]);

  return (
    <section className="wide-panel" data-testid="discrete-log-oracle-lab">
      <div className="panel-heading">
        <KeyRound size={20} />
        <h3>Discrete-log oracle toy</h3>
      </div>
      <p>
        In the real target, the public key is <code>Q = dG</code>. This toy group has
        order 13, so the oracle computes <code>aG + bQ = (a + b*d)G</code>. The
        secret is not a point by itself; it is the hidden slope that makes many
        different <code>(a,b)</code> pairs collide to the same group element.
      </p>

      <div className="oracle-controls">
        <label>
          <span>Secret d: {secret}</span>
          <input
            aria-label="Toy secret discrete log"
            min="1"
            max="12"
            type="range"
            value={secret}
            onChange={(event) => setSecret(Number(event.currentTarget.value))}
          />
        </label>
        <label>
          <span>a register: {aScalar}</span>
          <input
            aria-label="Toy a register"
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
            aria-label="Toy b register"
            min="0"
            max="12"
            type="range"
            value={bScalar}
            onChange={(event) => setBScalar(Number(event.currentTarget.value))}
          />
        </label>
      </div>

      <div className="oracle-grid-layout">
        <svg className="oracle-grid-svg" viewBox="0 0 156 156" role="img" aria-label="Toy discrete log oracle collision grid">
          {derived.cells.map((cell) => (
            <g key={`${cell.a}-${cell.b}`}>
              <rect
                className={cell.selected ? 'selected' : cell.paired ? 'paired' : ''}
                x={cell.a * 12}
                y={(order - 1 - cell.b) * 12}
                width="11"
                height="11"
                opacity={0.25 + cell.output / 18}
              />
              {(cell.selected || cell.paired) && (
                <text x={cell.a * 12 + 5.5} y={(order - 1 - cell.b) * 12 + 8}>{cell.selected ? 'A' : 'B'}</text>
              )}
            </g>
          ))}
        </svg>

        <div className="oracle-readout">
          <article>
            <span>Public key</span>
            <strong>Q = {secret}G</strong>
            <p>The attacker knows Q and G, not d.</p>
          </article>
          <article>
            <span>Selected oracle call</span>
            <strong>{aScalar}G + {bScalar}Q = {derived.outputScalar}G</strong>
            <p>because {aScalar} + {bScalar} * {secret} = {derived.outputScalar} mod 13</p>
          </article>
          <article>
            <span>Collision pair</span>
            <strong>({derived.collision.a}, {derived.collision.b}) {'->'} {derived.collisionOutput}G</strong>
            <p>same output, shifted by hidden period {derived.periodVector}</p>
          </article>
          <article>
            <span>Quantum reason</span>
            <strong>many-to-one oracle</strong>
            <p>phase estimation samples the hidden relation instead of testing every d.</p>
          </article>
        </div>
      </div>
    </section>
  );
}
