import { useMemo, useState } from 'react';
import { Sigma } from 'lucide-react';

type Point = { x: number; y: number } | null;

const prime = 17;
const curveA = 2;
const curveB = 2;
const generator: Point = { x: 5, y: 1 };

function mod(value: number) {
  return ((value % prime) + prime) % prime;
}

function inv(value: number) {
  for (let candidate = 1; candidate < prime; candidate += 1) {
    if (mod(value * candidate) === 1) {
      return candidate;
    }
  }
  throw new Error(`no inverse for ${value}`);
}

function addPoints(left: Point, right: Point): Point {
  if (left === null) return right;
  if (right === null) return left;
  if (left.x === right.x && mod(left.y + right.y) === 0) return null;
  const slope = left.x === right.x && left.y === right.y
    ? mod((3 * left.x * left.x + curveA) * inv(2 * left.y))
    : mod((right.y - left.y) * inv(right.x - left.x));
  const x = mod(slope * slope - left.x - right.x);
  const y = mod(slope * (left.x - x) - left.y);
  return { x, y };
}

function multiplyPoint(point: Point, scalar: number) {
  const trace: Point[] = [];
  let result: Point = null;
  for (let index = 0; index < scalar; index += 1) {
    result = addPoints(result, point);
    trace.push(result);
  }
  return { result, trace };
}

function pointLabel(point: Point) {
  return point === null ? '∞' : `(${point.x}, ${point.y})`;
}

function enumeratePoints() {
  const points: { x: number; y: number }[] = [];
  for (let x = 0; x < prime; x += 1) {
    for (let y = 0; y < prime; y += 1) {
      if (mod(y * y) === mod(x * x * x + curveA * x + curveB)) {
        points.push({ x, y });
      }
    }
  }
  return points;
}

export function ToyCurveLab() {
  const [scalar, setScalar] = useState(7);
  const points = useMemo(enumeratePoints, []);
  const multiplication = useMemo(() => multiplyPoint(generator, scalar), [scalar]);
  const zScale = 3;
  const projective = multiplication.result === null
    ? 'infinity'
    : `(${mod(multiplication.result.x * zScale)}, ${mod(multiplication.result.y * zScale)}, ${zScale}) -> ${pointLabel(multiplication.result)}`;

  return (
    <article className="lab-panel" data-testid="toy-curve-lab">
      <div className="panel-heading">
        <Sigma size={20} />
        <h3>Toy elliptic curve group</h3>
      </div>
      <label className="slider-label">
        Scalar: {scalar}
        <input min="1" max="18" type="range" value={scalar} onChange={(event) => setScalar(Number(event.currentTarget.value))} />
      </label>
      <svg className="curve-svg" viewBox="0 0 220 220" role="img" aria-label="Toy elliptic curve points over a finite field">
        {Array.from({ length: prime }, (_, index) => (
          <g key={index}>
            <line x1={20 + index * 11} y1="20" x2={20 + index * 11} y2="196" />
            <line x1="20" y1={20 + index * 11} x2="196" y2={20 + index * 11} />
          </g>
        ))}
        {points.map((point) => {
          const active = multiplication.trace.some((tracePoint) => tracePoint?.x === point.x && tracePoint.y === point.y);
          return <circle className={active ? 'curve-point active' : 'curve-point'} key={`${point.x}-${point.y}`} cx={20 + point.x * 11} cy={196 - point.y * 11} r={active ? 4 : 2.7} />;
        })}
      </svg>
      <dl className="metric-row">
        <div><dt>Curve</dt><dd>y²=x³+2x+2</dd></div>
        <div><dt>Prime</dt><dd>17</dd></div>
        <div><dt>Base P</dt><dd>{pointLabel(generator)}</dd></div>
        <div><dt>nP</dt><dd>{pointLabel(multiplication.result)}</dd></div>
      </dl>
      <p className="mono-line">projective scaled example: {projective}</p>
      <p>Affine formulas are compact, but division appears in the slope. Projective-style coordinates trade more live slots for multiplication-friendly arithmetic.</p>
    </article>
  );
}
