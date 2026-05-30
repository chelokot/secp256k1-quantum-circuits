import { useMemo, useState } from 'react';
import { Shuffle } from 'lucide-react';
import { MathTex } from './MathText';

type ProjectData = {
  reversibleOverwrite: {
    overwrittenOutputRowCount: number;
    allOutputOverwritesHaveBoundaryPermutationContract: boolean;
    costMatchesRows: boolean;
    guardOwnerCapacity: {
      logical_qubits: number;
      non_clifford: number;
    };
    overwriteRow: {
      target: string;
      schedule_overwritten_source: string;
      overwrite_contract: {
        ordinary_branch: string;
        zero_lift_branch: string;
        domain_rows_checked: number;
        secp256k1_permutation_pass: boolean;
      };
    };
    replay: {
      checkedNonInfinityPairs: number;
      checkedLookupInfinityPairs: number;
      ownerCapacityPass: boolean;
      pass: boolean;
    };
  };
};

const prime = 17;
const mod = (value: number) => ((value % prime) + prime) % prime;

function uniqueCount(values: number[]) {
  return new Set(values).size;
}

function determinant(a: number, b: number, c: number, d: number) {
  return mod(a * d - b * c);
}

function matrixUniqueCount(a: number, b: number, c: number, d: number) {
  const outputs = new Set<string>();
  for (let x = 0; x < prime; x += 1) {
    for (let y = 0; y < prime; y += 1) {
      outputs.add(`${mod(a * x + b * y)},${mod(c * x + d * y)}`);
    }
  }
  return outputs.size;
}

export function ReversibleOverwriteLab({ projectData }: { projectData: ProjectData }) {
  const [coefficient, setCoefficient] = useState(0);
  const [offset, setOffset] = useState(5);
  const [zeroLiftGuard, setZeroLiftGuard] = useState(true);
  const [matrix, setMatrix] = useState({ a: 1, b: 1, c: 2, d: 3 });
  const contract = projectData.reversibleOverwrite;

  const scalarMap = useMemo(() => {
    const outputs = Array.from({ length: prime }, (_, input) => {
      if (coefficient === 0 && zeroLiftGuard) return mod(input + offset);
      return mod(coefficient * input + offset);
    });
    const count = uniqueCount(outputs);
    return {
      outputs,
      unique: count,
      pass: count === prime,
    };
  }, [coefficient, offset, zeroLiftGuard]);

  const matrixAudit = useMemo(() => {
    const det = determinant(matrix.a, matrix.b, matrix.c, matrix.d);
    const unique = matrixUniqueCount(matrix.a, matrix.b, matrix.c, matrix.d);
    return {
      det,
      unique,
      pass: det !== 0 && unique === prime * prime,
    };
  }, [matrix]);

  const setSingularMatrix = () => setMatrix({ a: 1, b: 2, c: 2, d: 4 });
  const setInvertibleMatrix = () => setMatrix({ a: 1, b: 1, c: 2, d: 3 });

  return (
    <section className="wide-panel" data-testid="reversible-overwrite-lab">
      <div className="panel-heading">
        <Shuffle size={20} />
        <h3>Reversible overwrite lab</h3>
      </div>
      <p>
        Quantum overwrite is not deletion. An in-place row is valid only when the old
        value can still be recovered from the new state and the other live inputs.
      </p>
      <div className="overwrite-rule-strip">
        <article>
          <span>Allowed shape</span>
          <strong><MathTex tex="(old,controls)\leftrightarrow(new,controls)" /></strong>
          <p>One-to-one means amplitudes can be reversed exactly.</p>
        </article>
        <article>
          <span>Forbidden shape</span>
          <strong>many old values {'->'} one output</strong>
          <p>A collision would erase which branch was present.</p>
        </article>
        <article>
          <span>Repo gate</span>
          <strong>permutation contract + replay</strong>
          <p>The counted row must execute the same edge cases it claims.</p>
        </article>
      </div>

      <div className="overwrite-contract-strip">
        <div>
          <span>Repo overwritten row</span>
          <strong>{contract.overwriteRow.target} over {contract.overwriteRow.schedule_overwritten_source}</strong>
        </div>
        <div>
          <span>Permutation contract</span>
          <strong>{contract.allOutputOverwritesHaveBoundaryPermutationContract ? 'present' : 'missing'}</strong>
        </div>
        <div>
          <span>Replay</span>
          <strong>{contract.replay.pass ? 'pass' : 'fail'}</strong>
        </div>
        <div>
          <span>Guard cost</span>
          <strong>{contract.guardOwnerCapacity.logical_qubits}q / {contract.guardOwnerCapacity.non_clifford}</strong>
        </div>
      </div>

      <div className="overwrite-grid">
        <article>
          <h4>Scalar overwrite toy</h4>
          <p className="mono-line">
            <MathTex tex={`C\\mapsto L\\cdot C+offset\\pmod {${prime}}`} />
          </p>
          <label className="slider-label">
            Coefficient L: {coefficient}
            <input
              aria-label="Overwrite coefficient"
              max={prime - 1}
              min="0"
              onChange={(event) => setCoefficient(Number(event.currentTarget.value))}
              type="range"
              value={coefficient}
            />
          </label>
          <label className="slider-label">
            Offset N*M: {offset}
            <input
              aria-label="Overwrite offset"
              max={prime - 1}
              min="0"
              onChange={(event) => setOffset(Number(event.currentTarget.value))}
              type="range"
              value={offset}
            />
          </label>
          <label className="toggle-row">
            <input
              aria-label="Enable zero-lift guard"
              checked={zeroLiftGuard}
              onChange={(event) => setZeroLiftGuard(event.currentTarget.checked)}
              type="checkbox"
            />
            <span>zero-lift branch when L == 0</span>
          </label>
          <div className="overwrite-map">
            {scalarMap.outputs.map((output, input) => (
              <div key={input}>
                <span>{input}</span>
                <strong>{output}</strong>
              </div>
            ))}
          </div>
          <p className={scalarMap.pass ? 'audit-pass' : 'audit-fail'}>
            Scalar map audit: {scalarMap.pass ? 'permutation' : 'collision'} ({scalarMap.unique}/{prime} outputs)
          </p>
          <p>
            Repo analogue: {contract.overwriteRow.overwrite_contract.ordinary_branch}; zero branch:
            {' '}{contract.overwriteRow.overwrite_contract.zero_lift_branch}.
          </p>
        </article>

        <article>
          <h4>2x2 matrix toy</h4>
          <p>
            A variable pair transform is reversible only when its determinant is nonzero.
            This is the same mental model behind matrix-style slot reductions.
          </p>
          <div className="example-row">
            <button onClick={setInvertibleMatrix} type="button">Invertible matrix</button>
            <button onClick={setSingularMatrix} type="button">Singular matrix</button>
          </div>
          <div className="matrix-grid">
            {(['a', 'b', 'c', 'd'] as const).map((key) => (
              <label key={key}>
                <span>{key}</span>
                <input
                  aria-label={`Matrix coefficient ${key}`}
                  max={prime - 1}
                  min="0"
                  onChange={(event) => setMatrix((current) => ({ ...current, [key]: Number(event.currentTarget.value) }))}
                  type="range"
                  value={matrix[key]}
                />
                <strong>{matrix[key]}</strong>
              </label>
            ))}
          </div>
          <dl className="metric-pair">
            <div>
              <dt>determinant</dt>
              <dd>{matrixAudit.det}</dd>
            </div>
            <div>
              <dt>unique outputs</dt>
              <dd>{matrixAudit.unique}/{prime * prime}</dd>
            </div>
          </dl>
          <p className={matrixAudit.pass ? 'audit-pass' : 'audit-fail'}>
            Matrix audit: {matrixAudit.pass ? 'reversible permutation' : 'not reversible'}
          </p>
          <p>
            Checked repo replay covers {contract.replay.checkedNonInfinityPairs.toLocaleString('en-US')} non-infinity
            pairs and {contract.replay.checkedLookupInfinityPairs.toLocaleString('en-US')} lookup-infinity pairs.
          </p>
        </article>
      </div>
    </section>
  );
}
