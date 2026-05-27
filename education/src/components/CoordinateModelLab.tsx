import { useMemo, useState } from 'react';
import { Move3d } from 'lucide-react';

const prime = 17;
const affinePoint = { x: 5, y: 1 };

const mod = (value: number) => ((value % prime) + prime) % prime;

function inv(value: number) {
  for (let candidate = 1; candidate < prime; candidate += 1) {
    if (mod(value * candidate) === 1) return candidate;
  }
  throw new Error(`no inverse for ${value}`);
}

export function CoordinateModelLab() {
  const [scale, setScale] = useState(3);
  const projective = useMemo(() => ({
    x: mod(affinePoint.x * scale),
    y: mod(affinePoint.y * scale),
    z: scale,
    inverse: inv(scale),
  }), [scale]);
  const normalized = {
    x: mod(projective.x * projective.inverse),
    y: mod(projective.y * projective.inverse),
  };

  return (
    <section className="wide-panel" data-testid="coordinate-model-lab">
      <div className="panel-heading">
        <Move3d size={20} />
        <h3>Affine and projective coordinates</h3>
      </div>
      <p>
        Affine coordinates name one point directly. Projective coordinates name an equivalence
        class: many triples normalize back to the same affine point after dividing by Z.
      </p>

      <div className="coordinate-lab-grid">
        <article>
          <label className="slider-label">
            Projective scale Z: {scale}
            <input
              aria-label="Projective scale"
              min="1"
              max="16"
              type="range"
              value={scale}
              onChange={(event) => setScale(Number(event.currentTarget.value))}
            />
          </label>
          <dl className="metric-pair">
            <div>
              <dt>Affine point</dt>
              <dd>({affinePoint.x}, {affinePoint.y})</dd>
            </div>
            <div>
              <dt>Projective triple</dt>
              <dd>({projective.x}, {projective.y}, {projective.z})</dd>
            </div>
          </dl>
          <p className="mono-line">
            normalize: ({projective.x} * {projective.inverse}, {projective.y} * {projective.inverse}) mod {prime}
            = ({normalized.x}, {normalized.y})
          </p>
        </article>

        <article>
          <h4>Why this helps circuits</h4>
          <div className="coordinate-stack">
            <div><strong>Affine hot path</strong><span>2 field slots, but slope uses division/inversion.</span></div>
            <div><strong>Projective hot path</strong><span>more field slots, mostly multiply/add/subtract.</span></div>
            <div><strong>Final normalize</strong><span>pay inversion when leaving projective space.</span></div>
          </div>
        </article>
      </div>

      <div className="coordinate-slot-row">
        <div><span>Affine live coordinates</span><strong>x, y</strong><em>2 field slots</em></div>
        <div><span>Projective live coordinates</span><strong>X, Y, Z</strong><em>3 field slots</em></div>
        <div><span>Repo consequence</span><strong>slot pressure</strong><em>every extra field value is 256 logical wires</em></div>
      </div>
      <div className="slot-audit-strip">
        <article>
          <span>Field slot</span>
          <strong>one coordinate-sized register</strong>
          <p>For secp256k1, a live x, y, or z value means 256 logical wires.</p>
        </article>
        <article>
          <span>Boundary rule</span>
          <strong>edge cases share the count</strong>
          <p>Random, doubling, inverse, accumulator-infinity, and lookup-infinity cases must execute the same counted contract.</p>
        </article>
        <article>
          <span>Audit question</span>
          <strong>where does each coordinate live?</strong>
          <p>A coordinate can be overwritten only when the circuit proves a reversible owner-preserving map.</p>
        </article>
      </div>
    </section>
  );
}
