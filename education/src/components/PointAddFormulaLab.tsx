import { useMemo, useState } from 'react';
import { Sigma } from 'lucide-react';

type Point = { x: number; y: number } | null;

const prime = 17;
const curveA = 2;
const accumulator: Point = { x: 5, y: 1 };
const lookupPoints: Point[] = [
  { x: 6, y: 3 },
  { x: 10, y: 6 },
  { x: 3, y: 1 },
  { x: 9, y: 16 },
  null,
];

const mod = (value: number) => ((value % prime) + prime) % prime;

function inv(value: number) {
  for (let candidate = 1; candidate < prime; candidate += 1) {
    if (mod(value * candidate) === 1) return candidate;
  }
  throw new Error(`no inverse for ${value}`);
}

function label(point: Point) {
  return point === null ? '∞' : `(${point.x}, ${point.y})`;
}

function add(left: Point, right: Point) {
  if (left === null) return { result: right, slope: null, caseName: 'accumulator infinity' };
  if (right === null) return { result: left, slope: null, caseName: 'lookup infinity no-op' };
  if (left.x === right.x && mod(left.y + right.y) === 0) return { result: null, slope: null, caseName: 'inverse to infinity' };
  const doubling = left.x === right.x && left.y === right.y;
  const slope = doubling
    ? mod((3 * left.x * left.x + curveA) * inv(2 * left.y))
    : mod((right.y - left.y) * inv(right.x - left.x));
  const x = mod(slope * slope - left.x - right.x);
  const y = mod(slope * (left.x - x) - left.y);
  return { result: { x, y }, slope, caseName: doubling ? 'doubling' : 'random add' };
}

export function PointAddFormulaLab() {
  const [lookupIndex, setLookupIndex] = useState(0);
  const lookup = lookupPoints[lookupIndex];
  const result = useMemo(() => add(accumulator, lookup), [lookup]);
  const formulas = [
    { name: 'A', expr: 'x2 - x1', live: lookup === null ? 'bypass' : 'field slot' },
    { name: 'B', expr: 'y2 - y1', live: lookup === null ? 'bypass' : 'field slot' },
    { name: 'λ', expr: 'B / A', live: result.slope === null ? 'not needed' : `${result.slope}` },
    { name: 'x3', expr: 'λ² - x1 - x2', live: result.result === null ? '∞' : `${result.result.x}` },
    { name: 'y3', expr: 'λ(x1 - x3) - y1', live: result.result === null ? '∞' : `${result.result.y}` },
  ];

  return (
    <article className="lab-panel" data-testid="point-add-formula-lab">
      <div className="panel-heading">
        <Sigma size={20} />
        <h3>Point-add formula microscope</h3>
      </div>
      <label className="slider-label">
        Lookup row: {lookupIndex}
        <input min="0" max={lookupPoints.length - 1} type="range" value={lookupIndex} onChange={(event) => setLookupIndex(Number(event.currentTarget.value))} />
      </label>
      <dl className="metric-row">
        <div><dt>Accumulator</dt><dd>{label(accumulator)}</dd></div>
        <div><dt>Lookup</dt><dd>{label(lookup)}</dd></div>
        <div><dt>Case</dt><dd>{result.caseName}</dd></div>
        <div><dt>Output</dt><dd>{label(result.result)}</dd></div>
      </dl>
      <div className="formula-rows">
        {formulas.map((row) => (
          <div key={row.name}>
            <strong>{row.name}</strong>
            <code>{row.expr}</code>
            <span>{row.live}</span>
          </div>
        ))}
      </div>
      <p>The real secp256k1 leaf replaces this tiny affine division story with projective, lookup-fed, reversible field arithmetic and explicit edge-case contracts.</p>
    </article>
  );
}
