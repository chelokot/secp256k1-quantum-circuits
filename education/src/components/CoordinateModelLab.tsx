import { useMemo, useState } from 'react';
import { Move3d } from 'lucide-react';
import { MathTex } from './MathText';

const prime = 17;
const affinePoint = { x: 5, y: 1 };
const fieldBits = 256;

const slotProfiles = [
  {
    id: 'affine',
    label: 'Affine point',
    slots: ['x', 'y'],
    note: 'compact point name, but slope division asks for inversion inside point-add',
  },
  {
    id: 'projective',
    label: 'Projective carrier',
    slots: ['X', 'Y', 'Z'],
    note: 'one extra scale slot avoids paying inversion at every hot point-add',
  },
  {
    id: 'projective_temps',
    label: 'Projective + temporaries',
    slots: ['X', 'Y', 'Z', 'A', 'B'],
    note: 'formula scratch counts while live; names like A and B are not free',
  },
] as const;

const mod = (value: number) => ((value % prime) + prime) % prime;

function inv(value: number) {
  for (let candidate = 1; candidate < prime; candidate += 1) {
    if (mod(value * candidate) === 1) return candidate;
  }
  throw new Error(`no inverse for ${value}`);
}

export function CoordinateModelLab() {
  const [scale, setScale] = useState(3);
  const [profileId, setProfileId] = useState<(typeof slotProfiles)[number]['id']>('projective');
  const slotProfile = slotProfiles.find((profile) => profile.id === profileId) ?? slotProfiles[1];
  const logicalWires = slotProfile.slots.length * fieldBits;
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
        Modulo 17 keeps the arithmetic visible on screen. The circuit tradeoff is the
        same shape as the large field: projective-style names carry a scale coordinate,
        and several names normalize back to the same affine point.
      </p>

      <div className="coordinate-lab-grid">
        <article>
          <h4>Scale family</h4>
          <div className="coordinate-equation-strip" aria-hidden="true">
            <span><MathTex tex="P=(x,y)" /></span>
            <i />
            <span><MathTex tex="(X,Y,Z)=(Zx,Zy,Z)" /></span>
            <i />
            <span><MathTex tex="P=(XZ^{-1},YZ^{-1})" /></span>
          </div>
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
          <p className="coordinate-confirmation">
            Same point confirmed: the triple changed, but normalization returned
            ({affinePoint.x}, {affinePoint.y}).
          </p>
        </article>

        <article>
          <h4>Hot-path trade</h4>
          <div className="coordinate-stack">
            <div><strong>Affine hot path</strong><span>2 field slots, but slope uses division/inversion.</span></div>
            <div><strong>Projective hot path</strong><span>more field slots, mostly multiply/add/subtract.</span></div>
            <div><strong>Final normalize</strong><span>pay inversion when leaving projective space.</span></div>
          </div>
          <p className="coordinate-note">
            Real secp256k1 formulas use full field arithmetic and projective/Jacobian-style
            variants, but the audit question is the same: which coordinate-sized registers
            are live together?
          </p>
        </article>
      </div>

      <div className="coordinate-slot-row">
        <div><span>Affine live coordinates</span><strong>x, y</strong><em>2 field slots</em></div>
        <div><span>Projective live coordinates</span><strong>X, Y, Z</strong><em>3 field slots</em></div>
        <div><span>Repo consequence</span><strong>slot pressure</strong><em>every extra field value is 256 logical wires</em></div>
      </div>
      <section className="slot-accountant-panel" aria-label="Field-slot accountant">
        <div>
          <h4>Slot accountant</h4>
          <p>
            Count field-sized live values, then multiply by 256. This is the first
            accounting move behind the repo’s qubit disputes.
          </p>
          <div className="slot-profile-buttons">
            {slotProfiles.map((profile) => (
              <button
                className={profile.id === profileId ? 'selected' : ''}
                key={profile.id}
                type="button"
                onClick={() => setProfileId(profile.id)}
              >
                {profile.label}
              </button>
            ))}
          </div>
        </div>
        <div className="slot-accountant-card">
          <span>{slotProfile.label}</span>
          <strong>{logicalWires.toLocaleString('en-US')} logical wires</strong>
          <p>{slotProfile.slots.length} field slots * {fieldBits} wires per slot</p>
          <div className="slot-chip-row">
            {slotProfile.slots.map((slot) => <i key={slot}>{slot}</i>)}
          </div>
          <p>{slotProfile.note}</p>
        </div>
      </section>
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
