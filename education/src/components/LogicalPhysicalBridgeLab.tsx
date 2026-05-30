import { useMemo, useState } from 'react';
import { ServerCog } from 'lucide-react';
import { MathTex } from './MathText';

type BaselineRow = {
  id: string;
  label: string;
  status: string;
  logicalQubits: number;
  nonClifford: number;
  note: string;
};

type ProjectData = {
  baselineRows: BaselineRow[];
};

const formatInt = (value: number) => new Intl.NumberFormat('en-US').format(value);
const formatCompact = (value: number) => {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k`;
  return formatInt(value);
};

export function LogicalPhysicalBridgeLab({ projectData }: { projectData: ProjectData }) {
  const [selectedId, setSelectedId] = useState('repo_strict_candidate');
  const [distance, setDistance] = useState(15);
  const [layoutFactor, setLayoutFactor] = useState(2);
  const selected = projectData.baselineRows.find((row) => row.id === selectedId) ?? projectData.baselineRows[0];

  const estimate = useMemo(() => {
    const physicalPerLogical = layoutFactor * distance * distance;
    const physicalTotal = selected.logicalQubits * physicalPerLogical;
    const magicPressure = selected.nonClifford / selected.logicalQubits;
    return { physicalPerLogical, physicalTotal, magicPressure };
  }, [distance, layoutFactor, selected]);

  const claimCards = [
    {
      label: 'Allowed logical claim',
      status: 'allowed',
      value: `${formatInt(selected.logicalQubits)} logical wires`,
      detail: 'This is the selected repo row: peak algorithm-layer wires plus its non-Clifford ledger.',
    },
    {
      label: 'Blocked hardware claim',
      status: 'blocked',
      value: `${formatInt(selected.logicalQubits)} physical qubits`,
      detail: 'This silently changes layers. The repo artifact alone does not count hardware carriers.',
    },
    {
      label: 'Conditional envelope',
      status: 'conditional',
      value: `${formatCompact(estimate.physicalTotal)} illustrative physical qubits`,
      detail: `Only under d=${distance} and layout factor ${layoutFactor}x; factories, timing, routing, and decoder costs remain outside this panel.`,
    },
  ] as const;

  return (
    <section className="wide-panel" data-testid="logical-physical-bridge-lab">
      <div className="panel-heading">
        <ServerCog size={20} />
        <h3>Logical to physical bridge</h3>
      </div>
      <p>
        Repo headlines count logical qubits. Hardware planning needs an error-correction and
        layout model on top. The dial deliberately refuses to be a hardware forecast:
        it exposes the extra layer that turns a logical circuit into a physical-qubit
        envelope.
      </p>
      <section className="physical-layer-warning" aria-label="Logical and physical claim boundary">
        <article>
          <strong>Logical result</strong>
          <p>Chosen circuit row, peak logical wires, and non-Clifford ledger.</p>
        </article>
        <article>
          <strong>Illustrative envelope</strong>
          <p>One visible multiplier applied on top of the logical result.</p>
        </article>
        <article>
          <strong>Hardware forecast</strong>
          <p>Requires a complete fault-tolerance and architecture model, not provided here.</p>
        </article>
      </section>

      <div className="physical-controls">
        <label>
          <span>Resource row</span>
          <select
            aria-label="Logical resource row"
            value={selectedId}
            onChange={(event) => setSelectedId(event.currentTarget.value)}
          >
            {projectData.baselineRows.map((row) => (
              <option key={row.id} value={row.id}>{row.label}</option>
            ))}
          </select>
        </label>
        <label>
          <span>Code distance: {distance}</span>
          <input
            aria-label="Code distance"
            min="5"
            max="31"
            step="2"
            type="range"
            value={distance}
            onChange={(event) => setDistance(Number(event.currentTarget.value))}
          />
        </label>
        <label>
          <span>Layout factor: {layoutFactor}x</span>
          <input
            aria-label="Layout factor"
            min="1"
            max="6"
            step="1"
            type="range"
            value={layoutFactor}
            onChange={(event) => setLayoutFactor(Number(event.currentTarget.value))}
          />
        </label>
      </div>

      <div className="physical-grid">
        <article>
          <span>Logical qubits</span>
          <strong>{formatInt(selected.logicalQubits)}</strong>
          <p>{selected.status.replaceAll('_', ' ')}</p>
        </article>
        <article>
          <span>Physical per logical</span>
          <strong>{formatInt(estimate.physicalPerLogical)}</strong>
          <p>{layoutFactor} * {distance}² illustrative tiles</p>
        </article>
        <article>
          <span>Illustrative physical envelope</span>
          <strong>{formatCompact(estimate.physicalTotal)}</strong>
          <p>{formatInt(selected.logicalQubits)} logical * {formatInt(estimate.physicalPerLogical)}</p>
        </article>
        <article>
          <span>Magic pressure</span>
          <strong>{formatCompact(Math.round(estimate.magicPressure))}</strong>
          <p>non-Clifford per logical qubit</p>
        </article>
      </div>

      <section className="claim-translator-panel" aria-label="Logical to physical claim translator">
        <h4>Claim translator</h4>
        <p>
          The same number can be honest or wrong depending on the layer named beside it.
          Translate the sentence before comparing the result to a hardware roadmap.
        </p>
        <div>
          {claimCards.map((claim) => (
            <article className={claim.status} key={claim.label}>
              <span>{claim.label}</span>
              <strong>{claim.value}</strong>
              <p>{claim.detail}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="physical-translation-receipt" aria-label="Logical to physical translation receipt">
        <article>
          <span>Fixed by repo row</span>
          <strong>{formatInt(selected.logicalQubits)} logical wires</strong>
          <p>
            Changing code distance or layout factor does not change the algorithmic
            live-qubit count. It only changes the hardware envelope layered on top.
          </p>
        </article>
        <article>
          <span>Illustrative multiplier</span>
          <strong>{formatInt(estimate.physicalPerLogical)} physical per logical</strong>
          <p>
            The visible placeholder is <MathTex tex="\text{layout factor}\cdot d^2" />.
            A real fault-tolerance layout model would replace this factor.
          </p>
        </article>
        <article>
          <span>Not converted here</span>
          <strong>{formatCompact(selected.nonClifford)} non-Clifford operations</strong>
          <p>
            Magic factories, timing, decoding latency, and routing can dominate a real
            machine estimate, so this panel refuses to call the illustrative envelope a forecast.
          </p>
        </article>
      </section>

      <div className="physical-stack">
        <div><strong>Algorithm</strong><span>phase estimation and controlled point-adds</span></div>
        <div><strong>Logical circuit</strong><span>{formatInt(selected.logicalQubits)} live logical wires at peak</span></div>
        <div><strong>Error correction</strong><span>distance {distance}, layout factor {layoutFactor}x</span></div>
        <div><strong>Hardware envelope</strong><span>{formatCompact(estimate.physicalTotal)} illustrative physical qubits</span></div>
      </div>

      <section className="physical-assumption-ledger" aria-label="Physical estimate assumption ledger">
        <article>
          <strong>Included in the illustrative envelope</strong>
          <p>logical peak qubits, code distance, and one coarse layout multiplier</p>
        </article>
        <article>
          <strong>Still excluded</strong>
          <p>cycle time, decoder latency, routing, factory footprint, and target failure rate</p>
        </article>
        <article>
          <strong>Allowed claim</strong>
          <p>logical result plus explicit assumptions gives an illustrative envelope, not a hardware forecast</p>
        </article>
      </section>
    </section>
  );
}
