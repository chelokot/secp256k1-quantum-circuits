import { useMemo, useState } from 'react';
import { Code2 } from 'lucide-react';
import { MathTex } from './MathText';

type ParsedRow = {
  line: number;
  op: string;
  wires: string[];
  nonClifford: number;
};

type StreamAudit = {
  lifecycleDetail: string;
  lifecycleStatus: string;
  parserStatus: string;
};

type WireInterval = {
  firstLine: number;
  lastLine: number;
  owner: string;
  touchedLines: number[];
  wire: string;
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
      errors.push(`line ${index + 1}: unknown operation ${rawOp}`);
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

function rowEffect(row: ParsedRow) {
  if (row.op === 'CCX') {
    return `two-control reversible AND toggles ${row.wires[2]}`;
  }
  if (row.op === 'CX') {
    return `control ${row.wires[0]} flips target ${row.wires[1]}`;
  }
  if (row.op === 'M') {
    return `readout of ${row.wires[0]}`;
  }
  return `one-wire unitary on ${row.wires[0]}`;
}

function ownerForWire(wire: string) {
  if (wire === 'q0' || wire === 'q1') {
    return 'source/control owner';
  }
  if (wire === 'q2') {
    return 'scratch/output owner';
  }
  return 'user-declared wire owner';
}

function operandRoles(row: ParsedRow) {
  if (row.op === 'CCX') {
    return [
      `${row.wires[0]}: first control`,
      `${row.wires[1]}: second control`,
      `${row.wires[2]}: toggled target`,
    ];
  }
  if (row.op === 'CX') {
    return [`${row.wires[0]}: control`, `${row.wires[1]}: toggled target`];
  }
  if (row.op === 'M') {
    return [`${row.wires[0]}: measured boundary wire`];
  }
  return [`${row.wires[0]}: updated one-qubit wire`];
}

function rowLifecycle(row: ParsedRow) {
  if (row.op === 'CCX') {
    return `${row.wires[2]} may now carry a scratch product. It is clean only after the same CCX appears again or an explicit contract declares the target as output.`;
  }
  if (row.op === 'CX') {
    return `${row.wires[0]} stays live as a control while ${row.wires[1]} is updated in place.`;
  }
  if (row.op === 'M') {
    return `${row.wires[0]} exits the coherent circuit at this tiny measurement boundary.`;
  }
  return `${row.wires[0]} stays the same owned wire, but its amplitude vector has changed.`;
}

function deriveIntervals(rows: ParsedRow[]): WireInterval[] {
  const wires = Array.from(new Set(rows.flatMap((row) => row.wires))).sort();
  return wires.map((wire) => {
    const touchedLines = rows.filter((row) => row.wires.includes(wire)).map((row) => row.line);
    return {
      firstLine: Math.min(...touchedLines),
      lastLine: Math.max(...touchedLines),
      owner: ownerForWire(wire),
      touchedLines,
      wire,
    };
  });
}

function auditStream(rows: ParsedRow[], valid: boolean): StreamAudit {
  if (!valid) {
    return {
      lifecycleDetail: 'Fix parser errors before trusting lifecycle or cost.',
      lifecycleStatus: 'not evaluated',
      parserStatus: 'syntax error',
    };
  }

  const ccxParity = new Map<string, number>();
  for (const row of rows) {
    if (row.op !== 'CCX') continue;
    const key = row.wires.join(' ');
    const currentCount = ccxParity.get(key);
    ccxParity.set(key, currentCount === undefined ? 1 : currentCount + 1);
  }
  const unresolvedTargets = Array.from(ccxParity.entries())
    .filter(([, count]) => count % 2 === 1)
    .map(([key]) => key.split(' ')[2]);

  if (unresolvedTargets.length === 0) {
    return {
      lifecycleDetail: 'Every CCX scratch-like target is paired by the same controls.',
      lifecycleStatus: 'cleanup paired',
      parserStatus: 'syntax valid',
    };
  }

  return {
    lifecycleDetail: `${unresolvedTargets.join(', ')} toggled by CCX without a matching uncompute row.`,
    lifecycleStatus: 'cleanup not proven',
    parserStatus: 'syntax valid',
  };
}

export function QuantumDslLab() {
  const [program, setProgram] = useState(initialProgram);
  const [selectedLine, setSelectedLine] = useState(3);
  const parsed = useMemo(() => parseProgram(program), [program]);
  const uniqueWires = Array.from(new Set(parsed.rows.flatMap((row) => row.wires))).sort();
  const nonClifford = parsed.rows.reduce((total, row) => total + row.nonClifford, 0);
  const valid = parsed.errors.length === 0;
  const streamAudit = auditStream(parsed.rows, valid);
  const intervals = useMemo(() => deriveIntervals(parsed.rows), [parsed.rows]);
  const liveScan = parsed.rows.map((row) => ({
    line: row.line,
    op: row.op,
    wires: intervals.filter((interval) => row.line >= interval.firstLine && row.line <= interval.lastLine),
  }));
  const peakRow = liveScan.reduce(
    (peak, row) => (row.wires.length > peak.wires.length ? row : peak),
    { line: 0, op: 'none', wires: [] as WireInterval[] },
  );
  const selectedRow = parsed.rows.find((row) => row.line === selectedLine) ?? parsed.rows[0] ?? null;
  const selectedLiveWires = selectedRow
    ? liveScan.find((row) => row.line === selectedRow.line)?.wires ?? []
    : [];

  return (
    <article className="lab-panel" data-testid="quantum-dsl-lab">
      <div className="panel-heading">
        <Code2 size={20} />
        <h3>Program a tiny netlist</h3>
      </div>
      <p>
        This editor uses compact circuit names, but each name still means a concrete
        reversible row over named wires. Write one row per line, then inspect the parsed
        row table and cleanup audit.
      </p>
      <section className="gate-vocabulary-grid" aria-label="Tiny netlist operation vocabulary">
        <article>
          <strong>H: Hadamard</strong>
          <p>One-wire mix: splits or recombines 0 and 1 amplitudes.</p>
        </article>
        <article>
          <strong>X: bit flip</strong>
          <p>One-wire swap: exchanges the 0-label and 1-label amplitudes.</p>
        </article>
        <article>
          <strong>S: phase turn</strong>
          <p>One-wire phase step: changes direction of the 1-amplitude.</p>
        </article>
        <article>
          <strong>CX: controlled-X</strong>
          <p>Two-wire permutation: flip the target only on branches where the control is 1.</p>
        </article>
        <article>
          <strong>CCX: Toffoli-style row</strong>
          <p>Three-wire product: two controls toggle one target, so this counts as non-Clifford work.</p>
        </article>
        <article>
          <strong>M: measurement</strong>
          <p>Readout row: sample a wire at the end of the tiny program.</p>
        </article>
      </section>
      <textarea
        aria-label="Tiny netlist editor"
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
      <h4>Stream audit</h4>
      <div className="stream-audit-strip">
        <article>
          <span>Parser</span>
          <strong>{streamAudit.parserStatus}</strong>
          <p>Only known operation names with the right number of wires become rows.</p>
        </article>
        <article>
          <span>Row table</span>
          <strong>{parsed.rows.length} executable row(s)</strong>
          <p>Each row has wires it touches, a concrete effect, and non-Clifford cost.</p>
        </article>
        <article>
          <span>Lifecycle</span>
          <strong>{streamAudit.lifecycleStatus}</strong>
          <p>{streamAudit.lifecycleDetail}</p>
        </article>
      </div>
      {selectedRow ? (
        <section className="row-replay-panel" aria-label="Executable row receipt">
          <div className="row-replay-heading">
            <div>
              <h4>Executable row receipt</h4>
              <p>
                Pick one parsed row. The receipt is the object a later engine can execute,
                test, assign to owners, and count.
              </p>
            </div>
            <div className="row-replay-buttons" aria-label="Select parsed row">
              {parsed.rows.map((row) => (
                <button
                  className={row.line === selectedRow.line ? 'active' : ''}
                  key={`${row.line}-${row.op}-selector`}
                  onClick={() => setSelectedLine(row.line)}
                  type="button"
                >
                  line {row.line}
                </button>
              ))}
            </div>
          </div>
          <article className="row-receipt-card dsl-row-receipt">
            <span>Selected primitive row</span>
            <strong>line {selectedRow.line}: {selectedRow.op} {selectedRow.wires.join(' ')}</strong>
            <em>{rowEffect(selectedRow)}</em>
            <dl>
              <div>
                <dt>Operand roles</dt>
                <dd>{operandRoles(selectedRow).join('; ')}</dd>
              </div>
              <div>
                <dt>Cost</dt>
                <dd>{selectedRow.nonClifford} toy non-Clifford row(s)</dd>
              </div>
              <div>
                <dt>Lifecycle effect</dt>
                <dd>{rowLifecycle(selectedRow)}</dd>
              </div>
              <div>
                <dt>Live at this row</dt>
                <dd>{selectedLiveWires.map((wire) => wire.wire).join(', ') || 'none'}</dd>
              </div>
            </dl>
          </article>
        </section>
      ) : null}
      <section className="dsl-liveness-panel" aria-label="Derived liveness ledger">
        <div className="dsl-liveness-heading">
          <h4>Derived liveness ledger</h4>
          <p>
            This ledger is generated from the parsed rows. It is the toy version of the
            rule <MathTex tex="\text{peak qubits}=\max_t |\text{live wires at row }t|" />.
          </p>
        </div>
        <div className="dsl-live-summary">
          <article>
            <span>Peak live wires</span>
            <strong>{peakRow.wires.length}</strong>
            <em>{peakRow.line === 0 ? 'no rows' : `line ${peakRow.line}: ${peakRow.op}`}</em>
          </article>
          <article>
            <span>Owners present</span>
            <strong>{new Set(intervals.map((interval) => interval.owner)).size}</strong>
            <em>{Array.from(new Set(intervals.map((interval) => interval.owner))).join(', ') || 'none'}</em>
          </article>
        </div>
        <div className="dsl-interval-table" role="table" aria-label="Derived wire live intervals">
          <div role="row">
            <strong role="columnheader">Wire</strong>
            <strong role="columnheader">Owner</strong>
            <strong role="columnheader">Live interval</strong>
            <strong role="columnheader">Touched lines</strong>
          </div>
          {intervals.map((interval) => (
            <div role="row" key={`${interval.wire}-interval`}>
              <span role="cell">{interval.wire}</span>
              <span role="cell">{interval.owner}</span>
              <span role="cell">lines {interval.firstLine}-{interval.lastLine}</span>
              <span role="cell">{interval.touchedLines.join(', ')}</span>
            </div>
          ))}
        </div>
      </section>
      {parsed.errors.length > 0 ? (
        <div className="parse-errors">
          {parsed.errors.map((error) => <p key={error}>{error}</p>)}
        </div>
      ) : (
        <div className="parsed-netlist" role="table" aria-label="Parsed primitive netlist">
          <div role="row"><strong>Line</strong><strong>Operation</strong><strong>Wires</strong><strong>Effect</strong><strong>Non-Clifford</strong></div>
          {parsed.rows.map((row) => (
            <div role="row" key={`${row.line}-${row.op}`}>
              <span>{row.line}</span>
              <span>{row.op}</span>
              <span>{row.wires.join(', ')}</span>
              <span>{rowEffect(row)}</span>
              <span>{row.nonClifford}</span>
            </div>
          ))}
        </div>
      )}
      <p>The real project needs this same discipline scaled to every emitted arithmetic and lookup row.</p>
    </article>
  );
}
