import { useMemo, useState } from 'react';
import { ListTree } from 'lucide-react';

type PrimitiveRow = {
  index: number;
  gate: 'cx' | 'ccx' | 'measurement';
  operands: string[];
  meaning: string;
};

type BoolBit = 0 | 1;

type BitState = Record<string, BoolBit>;

type LoweringExample = {
  id: string;
  label: string;
  sourceOpcode: string;
  ownerCapacity: Record<string, number>;
  replayInputs: string[];
  replayAuxiliaries: string[];
  abstractReplay: (state: BitState) => BitState;
  rows: PrimitiveRow[];
};

const readBit = (state: BitState, wire: string) => {
  const bit = state[wire];
  if (bit === undefined) {
    throw new Error(`Missing bit for ${wire}`);
  }
  return bit;
};

const xorBits = (left: BoolBit, right: BoolBit): BoolBit => (left === right ? 0 : 1);

const andBits = (left: BoolBit, right: BoolBit): BoolBit => (left === 1 && right === 1 ? 1 : 0);

const examples: LoweringExample[] = [
  {
    id: 'controlled_select',
    label: 'controlled select bit',
    sourceOpcode: 'select_field_if_flag bit slice',
    ownerCapacity: {
      control: 1,
      field_slot: 2,
      scratch: 1,
    },
    replayInputs: ['src', 'flag', 'dst'],
    replayAuxiliaries: ['scratch'],
    abstractReplay: (state) => ({
      ...state,
      dst: xorBits(readBit(state, 'dst'), andBits(readBit(state, 'flag'), readBit(state, 'src'))),
      scratch: 0,
    }),
    rows: [
      { index: 0, gate: 'cx', operands: ['src', 'scratch'], meaning: 'copy candidate bit into scratch lane' },
      { index: 1, gate: 'ccx', operands: ['flag', 'scratch', 'dst'], meaning: 'conditionally flip destination bit' },
      { index: 2, gate: 'cx', operands: ['src', 'scratch'], meaning: 'uncompute scratch back to zero' },
    ],
  },
  {
    id: 'qroam_load',
    label: 'QROAM loaded bit',
    sourceOpcode: 'qroam_chunk_stream target bit',
    ownerCapacity: {
      address: 2,
      qroam_target: 1,
      table_control: 1,
    },
    replayInputs: ['addr0', 'addr1', 'target'],
    replayAuxiliaries: ['table_control'],
    abstractReplay: (state) => ({
      ...state,
      target: xorBits(readBit(state, 'target'), andBits(readBit(state, 'addr0'), readBit(state, 'addr1'))),
      table_control: 0,
    }),
    rows: [
      { index: 0, gate: 'ccx', operands: ['addr0', 'addr1', 'table_control'], meaning: 'activate one selected unary path' },
      { index: 1, gate: 'cx', operands: ['table_control', 'target'], meaning: 'load selected table bit into counted target' },
      { index: 2, gate: 'ccx', operands: ['addr0', 'addr1', 'table_control'], meaning: 'clean selected unary path' },
    ],
  },
  {
    id: 'phase_measure',
    label: 'semiclassical phase tick',
    sourceOpcode: 'phase_shell_measurement',
    ownerCapacity: {
      phase_bit: 1,
      classical_feedforward: 0,
    },
    replayInputs: ['phase_bit', 'rotation_control'],
    replayAuxiliaries: [],
    abstractReplay: (state) => ({
      ...state,
      rotation_control: xorBits(readBit(state, 'rotation_control'), readBit(state, 'phase_bit')),
    }),
    rows: [
      { index: 0, gate: 'cx', operands: ['phase_bit', 'rotation_control'], meaning: 'apply controlled Clifford feedback' },
      { index: 1, gate: 'measurement', operands: ['phase_bit'], meaning: 'exit coherent liveness for this phase bit' },
    ],
  },
];

const ownerForWire = (wire: string) => {
  if (wire.startsWith('addr')) return 'address';
  if (wire === 'target') return 'qroam_target';
  if (wire === 'table_control' || wire === 'table_constant') return 'table_control';
  if (wire === 'flag') return 'control';
  if (wire === 'src' || wire === 'dst') return 'field_slot';
  if (wire === 'scratch') return 'scratch';
  if (wire === 'phase_bit' || wire === 'rotation_control') return 'phase_bit';
  return 'classical_feedforward';
};

const gateCost = (gate: PrimitiveRow['gate']) => (gate === 'ccx' ? 1 : 0);

const enumerateAssignments = (variables: string[]): BitState[] => variables.reduce<BitState[]>(
  (states, variable) => states.flatMap((state) => [
    { ...state, [variable]: 0 },
    { ...state, [variable]: 1 },
  ]),
  [{}],
);

const createInitialState = (example: LoweringExample, assignment: BitState) => {
  const state: BitState = {};
  example.replayInputs.forEach((wire) => {
    state[wire] = readBit(assignment, wire);
  });
  example.replayAuxiliaries.forEach((wire) => {
    state[wire] = 0;
  });
  return state;
};

const applyPrimitiveRow = (state: BitState, row: PrimitiveRow) => {
  if (row.gate === 'measurement') {
    return state;
  }
  if (row.gate === 'cx') {
    const [control, target] = row.operands;
    state[target] = xorBits(readBit(state, target), readBit(state, control));
    return state;
  }
  const [firstControl, secondControl, target] = row.operands;
  state[target] = xorBits(
    readBit(state, target),
    andBits(readBit(state, firstControl), readBit(state, secondControl)),
  );
  return state;
};

const replayRows = (rows: PrimitiveRow[], initial: BitState) => rows.reduce(
  (state, row) => applyPrimitiveRow(state, row),
  { ...initial },
);

const snapshotState = (wires: string[], state: BitState) => wires
  .map((wire) => `${wire}=${readBit(state, wire)}`)
  .join(', ');

export function OpcodeLoweringLab() {
  const [exampleId, setExampleId] = useState(examples[0].id);
  const [cleanupRemoved, setCleanupRemoved] = useState(false);
  const selected = examples.find((example) => example.id === exampleId) ?? examples[0];

  const derived = useMemo(() => {
    const rows = cleanupRemoved ? selected.rows.filter((row) => !row.meaning.includes('uncompute') && !row.meaning.includes('clean selected')) : selected.rows;
    const wires = Array.from(new Set(rows.flatMap((row) => row.operands))).sort();
    const intervals = wires.map((wire) => {
      const uses = rows.filter((row) => row.operands.includes(wire)).map((row) => row.index);
      const owner = ownerForWire(wire);
      return {
        wire,
        owner,
        start: Math.min(...uses),
        end: Math.max(...uses) + 1,
      };
    });
    const tickLoads = rows.map((row) => {
      const live = intervals.filter((interval) => interval.start <= row.index && row.index < interval.end);
      const ownerLoads = Object.entries(selected.ownerCapacity).map(([owner, capacity]) => {
        const load = live.filter((interval) => interval.owner === owner).length;
        return { owner, capacity, load, pass: load <= capacity };
      });
      return { row: row.index, live, ownerLoads };
    });
    const nonClifford = rows.reduce((total, row) => total + gateCost(row.gate), 0);
    const ownerPass = tickLoads.every((tick) => tick.ownerLoads.every((owner) => owner.pass));
    const cleanupPass = !cleanupRemoved || selected.id === 'phase_measure';
    const semanticWires = [...selected.replayInputs, ...selected.replayAuxiliaries];
    const replayCases = enumerateAssignments(selected.replayInputs).map((assignment) => {
      const initial = createInitialState(selected, assignment);
      const primitive = replayRows(rows, initial);
      const expected = selected.abstractReplay(initial);
      const pass = semanticWires.every((wire) => readBit(primitive, wire) === readBit(expected, wire));
      return {
        assignment,
        expected,
        initial,
        pass,
        primitive,
      };
    });
    const replayPassCount = replayCases.filter((replayCase) => replayCase.pass).length;
    const firstReplayFailure = replayCases.find((replayCase) => !replayCase.pass);
    const costTerms = rows.map((row) => String(gateCost(row.gate))).join(' + ');
    return {
      rows,
      intervals,
      tickLoads,
      nonClifford,
      ownerPass,
      cleanupPass,
      replayCases,
      replayPassCount,
      firstReplayFailure,
      semanticWires,
      costTerms,
      pass: ownerPass && cleanupPass && replayPassCount === replayCases.length,
    };
  }, [cleanupRemoved, selected]);

  return (
    <section className="wide-panel" data-testid="opcode-lowering-lab">
      <div className="panel-heading">
        <ListTree size={20} />
        <h3>Opcode lowering microscope</h3>
      </div>
      <p>
        A repo claim gets stronger when an abstract opcode expands into primitive rows with
        operands, owners, cleanup, and counted non-Clifford cost. The microscope shows
        the chain from one source operation to rows a resource engine can scan.
      </p>

      <div className="lowering-controls">
        <label>
          <span>Source opcode</span>
          <select
            aria-label="Lowering source opcode"
            value={exampleId}
            onChange={(event) => setExampleId(event.currentTarget.value)}
          >
            {examples.map((example) => (
              <option key={example.id} value={example.id}>{example.label}</option>
            ))}
          </select>
        </label>
        <label className="toggle-row">
          <input
            aria-label="Remove cleanup rows"
            checked={cleanupRemoved}
            onChange={(event) => setCleanupRemoved(event.currentTarget.checked)}
            type="checkbox"
          />
          <span>remove cleanup rows</span>
        </label>
      </div>

      <div className="lowering-grid">
        <article>
          <h4>{selected.sourceOpcode}</h4>
          <div className="primitive-row-table" role="table" aria-label="Primitive lowering rows">
            <div role="row"><strong>Row</strong><strong>Gate</strong><strong>Operands</strong><strong>Meaning</strong></div>
            {derived.rows.map((row) => (
              <div role="row" key={`${selected.id}-${row.index}`}>
                <span>{row.index}</span>
                <span>{row.gate}</span>
                <span>{row.operands.join(', ')}</span>
                <span>{row.meaning}</span>
              </div>
            ))}
          </div>
        </article>

        <article>
          <h4>Engine view</h4>
          <dl className="metric-row">
            <div><dt>Primitive rows</dt><dd>{derived.rows.length}</dd></div>
            <div><dt>Wires</dt><dd>{derived.intervals.length}</dd></div>
            <div><dt>Non-Clifford</dt><dd>{derived.nonClifford}</dd></div>
            <div><dt>Audit</dt><dd>{derived.pass ? 'pass' : 'fail'}</dd></div>
          </dl>
          <p className={derived.pass ? 'audit-pass' : 'audit-fail'}>
            Lowering audit: {derived.pass ? 'pass' : 'fail'}.
            Owner capacity {derived.ownerPass ? 'ok' : 'overflow'}; cleanup {derived.cleanupPass ? 'ok' : 'missing'}.
          </p>
        </article>
      </div>

      <div className="lowering-intervals">
        {derived.intervals.map((interval) => (
          <div key={interval.wire}>
            <strong>{interval.wire}</strong>
            <span>{interval.owner}</span>
            <em>rows {interval.start}-{interval.end}</em>
          </div>
        ))}
      </div>

      <div className="lowering-replay-receipt">
        <article>
          <span>Semantic replay receipt</span>
          <strong>Case corpus {derived.replayPassCount}/{derived.replayCases.length}</strong>
          <p>Every binary input for this tiny opcode is executed through the primitive rows.</p>
        </article>
        <article>
          <span>Compared boundary</span>
          <strong>{derived.semanticWires.join(', ')}</strong>
          <p>Controls, targets, and auxiliary cleanup wires are compared against the source opcode.</p>
        </article>
        <article>
          <span>Cost reconstruction</span>
          <strong>{derived.costTerms} = {derived.nonClifford}</strong>
          <p>The displayed non-Clifford count is reconstructed from primitive row gates.</p>
        </article>
      </div>

      <div className={derived.firstReplayFailure ? 'replay-failure-card' : 'replay-pass-card'}>
        <strong>Executable replay: {derived.firstReplayFailure ? 'fail' : 'pass'}</strong>
        {derived.firstReplayFailure ? (
          <p>
            input {snapshotState(selected.replayInputs, derived.firstReplayFailure.initial)}:
            primitive {snapshotState(derived.semanticWires, derived.firstReplayFailure.primitive)};
            expected {snapshotState(derived.semanticWires, derived.firstReplayFailure.expected)}
          </p>
        ) : (
          <p>All replay cases match the abstract opcode and leave required auxiliaries clean.</p>
        )}
      </div>
    </section>
  );
}
