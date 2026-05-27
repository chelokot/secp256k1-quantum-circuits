import { useMemo, useState } from 'react';
import { Code2 } from 'lucide-react';

type ParsedRow = {
  line: number;
  op: string;
  wires: string[];
  nonClifford: number;
};

const initialProgram = `H q0
CX q0 q1
CCX q0 q1 q2
M q0`;

const arity: Record<string, number> = {
  H: 1,
  X: 1,
  S: 1,
  CX: 2,
  CCX: 3,
  M: 1,
};

function parseProgram(program: string) {
  const rows: ParsedRow[] = [];
  const errors: string[] = [];
  for (const [index, rawLine] of program.split('\n').entries()) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) {
      continue;
    }
    const [rawOp, ...wires] = line.split(/\s+/);
    const op = rawOp.toUpperCase();
    if (!(op in arity)) {
      errors.push(`line ${index + 1}: unknown op ${rawOp}`);
      continue;
    }
    if (wires.length !== arity[op]) {
      errors.push(`line ${index + 1}: ${op} expects ${arity[op]} wire(s)`);
      continue;
    }
    rows.push({
      line: index + 1,
      op,
      wires,
      nonClifford: op === 'CCX' ? 1 : 0,
    });
  }
  return { rows, errors };
}

export function QuantumDslLab() {
  const [program, setProgram] = useState(initialProgram);
  const parsed = useMemo(() => parseProgram(program), [program]);
  const uniqueWires = Array.from(new Set(parsed.rows.flatMap((row) => row.wires))).sort();
  const nonClifford = parsed.rows.reduce((total, row) => total + row.nonClifford, 0);
  const valid = parsed.errors.length === 0;

  return (
    <article className="lab-panel" data-testid="quantum-dsl-lab">
      <div className="panel-heading">
        <Code2 size={20} />
        <h3>Program a tiny netlist</h3>
      </div>
      <textarea
        aria-label="Quantum DSL editor"
        className="dsl-editor"
        value={program}
        onChange={(event) => setProgram(event.currentTarget.value)}
        spellCheck={false}
      />
      <dl className="metric-row">
        <div><dt>Rows</dt><dd>{parsed.rows.length}</dd></div>
        <div><dt>Wires</dt><dd>{uniqueWires.length}</dd></div>
        <div><dt>Non-Clifford</dt><dd>{nonClifford}</dd></div>
        <div><dt>Status</dt><dd>{valid ? 'valid' : 'error'}</dd></div>
      </dl>
      {parsed.errors.length > 0 ? (
        <div className="parse-errors">
          {parsed.errors.map((error) => <p key={error}>{error}</p>)}
        </div>
      ) : (
        <div className="parsed-netlist" role="table" aria-label="Parsed primitive netlist">
          <div role="row"><strong>Line</strong><strong>Op</strong><strong>Wires</strong><strong>NC</strong></div>
          {parsed.rows.map((row) => (
            <div role="row" key={`${row.line}-${row.op}`}>
              <span>{row.line}</span>
              <span>{row.op}</span>
              <span>{row.wires.join(', ')}</span>
              <span>{row.nonClifford}</span>
            </div>
          ))}
        </div>
      )}
      <p>Supported ops: <code>H</code>, <code>X</code>, <code>S</code>, <code>CX</code>, <code>CCX</code>, <code>M</code>. The real project needs this idea scaled to every emitted arithmetic and lookup row.</p>
    </article>
  );
}
