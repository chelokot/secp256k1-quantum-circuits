import { useMemo, useState } from 'react';
import { Map } from 'lucide-react';

type ProjectData = {
  currentStrictCandidate: {
    logical_qubits: number;
    non_clifford: number;
    status: string;
  };
  guardCorrectedNoAliasCandidate: {
    logical_qubits: number;
    status: string;
  };
  activeBlockers: Array<{ name: string; status: string }>;
};

const formatInt = (value: number) => new Intl.NumberFormat('en-US').format(value);
const readable = (value: string) => value.replaceAll('_', ' ');

const stages = [
  {
    id: 'phase',
    name: 'Phase estimation shell',
    consumes: 'secp256k1 public key relation and coherent control register',
    emits: 'controlled group-operation requests and final measurement peaks',
    audit: 'Do the phase/control bits remain counted until measurement or semiclassical collapse?',
  },
  {
    id: 'lookup',
    name: 'Lookup and QROAM',
    consumes: 'window address bits and precomputed curve-point table',
    emits: 'selected point chunks with counted table-selection workspace',
    audit: 'Are target lanes, decode workspace, cleanup, and no-op lookup infinity all explicit?',
  },
  {
    id: 'point-add',
    name: 'Point-add leaf',
    consumes: 'accumulator point, lookup point, edge-case predicates',
    emits: 'updated accumulator point with equivalent semantics across all boundary cases',
    audit: 'Do random, doubling, inverse, accumulator-infinity, and lookup-infinity cases pass?',
  },
  {
    id: 'field',
    name: 'Field arithmetic lowering',
    consumes: 'field operations such as add, subtract, multiply, fold, and reduce',
    emits: 'bit-level reversible arithmetic obligations and temporary scratch routes',
    audit: 'Can every partial product, carry, fold, and cleanup row be promoted into one primitive stream?',
  },
  {
    id: 'netlist',
    name: 'Primitive netlist engine',
    consumes: 'lowered primitive rows with named wires and owners',
    emits: 'operation stream, live intervals, owner-capacity proof, non-Clifford total',
    audit: 'Does one executable stream generate the same count used by tests and proof input?',
  },
  {
    id: 'zkp',
    name: 'ZKP publication boundary',
    consumes: 'resource digest, semantic corpus, public values, verifier key',
    emits: 'compressed/Groth16 verification result for a specific current statement',
    audit: 'Are proof artifacts current, release-grade, and bound to the selected physical contract?',
  },
];

export function CircuitStackMap({ projectData }: { projectData: ProjectData }) {
  const [activeStageId, setActiveStageId] = useState('phase');
  const activeStage = stages.find((stage) => stage.id === activeStageId) ?? stages[0];
  const primaryBlocker = projectData.activeBlockers[0];

  const stackStatus = useMemo(() => {
    const openBlockers = projectData.activeBlockers.length;
    return openBlockers === 0
      ? 'all publication blockers closed'
      : `${openBlockers} physical-baseline blocker${openBlockers === 1 ? '' : 's'} open`;
  }, [projectData.activeBlockers.length]);

  return (
    <section className="wide-panel" data-testid="circuit-stack-map">
      <div className="panel-heading">
        <Map size={20} />
        <h3>End-to-end circuit stack map</h3>
      </div>
      <p>
        Read the repo as a stack, not as one number. Each layer must consume exactly the object
        emitted by the previous layer, or a lower resource claim can silently stop referring to
        the circuit that is actually tested.
      </p>

      <div className="stack-map-grid">
        <div className="stack-stage-list">
          {stages.map((stage, index) => (
            <button
              className={stage.id === activeStage.id ? 'selected' : ''}
              key={stage.id}
              onClick={() => setActiveStageId(stage.id)}
              type="button"
            >
              <span>{index + 1}</span>
              <strong>{stage.name}</strong>
            </button>
          ))}
        </div>

        <article>
          <h4>{activeStage.name}</h4>
          <dl className="stack-detail-list">
            <div>
              <dt>Consumes</dt>
              <dd>{activeStage.consumes}</dd>
            </div>
            <div>
              <dt>Emits</dt>
              <dd>{activeStage.emits}</dd>
            </div>
            <div>
              <dt>Reviewer question</dt>
              <dd>{activeStage.audit}</dd>
            </div>
          </dl>
        </article>
      </div>

      <div className="stack-status-row">
        <div>
          <span>Strict candidate</span>
          <strong>{formatInt(projectData.currentStrictCandidate.logical_qubits)}q / {formatInt(projectData.currentStrictCandidate.non_clifford)}</strong>
          <em>{readable(projectData.currentStrictCandidate.status)}</em>
        </div>
        <div>
          <span>Guard-corrected consequence</span>
          <strong>{formatInt(projectData.guardCorrectedNoAliasCandidate.logical_qubits)}q</strong>
          <em>{readable(projectData.guardCorrectedNoAliasCandidate.status)}</em>
        </div>
        <div>
          <span>Stack status</span>
          <strong>{stackStatus}</strong>
          <em>{primaryBlocker ? readable(primaryBlocker.name) : 'none'}</em>
        </div>
      </div>
    </section>
  );
}
