import { useMemo, useState } from 'react';
import { Binary } from 'lucide-react';
import { MathTex } from './MathText';

type ProjectData = {
  strictNonCliffordFormula: {
    qroam_chunk_streams: number;
    per_chunk_stream_non_clifford: number;
    qroam_chunk_non_clifford: number;
  };
  strictFormula: {
    lookup_workspace_qubits: number;
  };
  compilerParameters: {
    field: {
      fieldBits: number;
    };
    reusableChunkPolicy: {
      chunkBits: number;
      chunkCount: number;
      scratchSlot: string;
    };
  };
};

const table = [
  '0x6a', '0x13', '0xdf', '0x92', '0x41', '0xb8', '0x75', '0x0c',
];

export function QroamLab({ projectData }: { projectData: ProjectData }) {
  const [address, setAddress] = useState(5);
  const bits = useMemo(() => [4, 2, 1].map((mask) => (address & mask ? 1 : 0)), [address]);
  const selectedValue = table[address];
  const selectedBits = Number.parseInt(selectedValue, 16).toString(2).padStart(8, '0');
  const fieldBits = projectData.compilerParameters.field.fieldBits;
  const chunkBits = projectData.compilerParameters.reusableChunkPolicy.chunkBits;
  const chunkCount = projectData.compilerParameters.reusableChunkPolicy.chunkCount;
  const scratchSlot = projectData.compilerParameters.reusableChunkPolicy.scratchSlot;

  const toggleBit = (bitIndex: number) => {
    const mask = 1 << (2 - bitIndex);
    setAddress((current) => current ^ mask);
  };

  return (
    <article className="lab-panel" data-testid="qroam-lab">
      <div className="panel-heading">
        <Binary size={20} />
        <h3>QROAM table selection</h3>
      </div>
      <p>
        A lookup has four different resources. The address controls select a row,
        the target lane receives the selected data, workspace helps the selection,
        and cleanup removes temporary selection state.
      </p>
      <div className="lookup-audit-grid">
        <article>
          <span>1. Address controls</span>
          <strong>a0 a1 a2</strong>
          <p>These choose which table row is active. They are not the output lane.</p>
        </article>
        <article>
          <span>2. Target lane</span>
          <strong>{selectedValue}</strong>
          <p>The selected value must live in a counted target register or alias a proven owner.</p>
        </article>
        <article>
          <span>3. Workspace</span>
          <strong>{projectData.strictFormula.lookup_workspace_qubits}q</strong>
          <p>Decode/control workspace cannot silently include field-sized output lanes unless the artifact says so.</p>
        </article>
        <article>
          <span>4. Cleanup</span>
          <strong>uncompute selection</strong>
          <p>The temporary table-selection path must be reversed after the target value is consumed.</p>
        </article>
      </div>
      <div className="address-bits" aria-label="Address bits">
        {bits.map((bit, index) => (
          <button className={bit ? 'bit on' : 'bit'} key={index} type="button" onClick={() => toggleBit(index)}>
            a{index}={bit}
          </button>
        ))}
      </div>
      <div className="lookup-table">
        {table.map((value, index) => (
          <div className={index === address ? 'lookup-cell selected' : 'lookup-cell'} key={value}>
            <span>{index.toString(2).padStart(3, '0')}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
      <section className="lookup-receipt" aria-label="Lookup ownership receipt">
        <div className="lookup-receipt-intro">
          <h4>Ownership receipt for this selection</h4>
          <p>
            The visible table emits one byte, but the real circuit emits coordinate
            chunks. The audit is the same: the selected data must be assigned to a
            counted target owner before cleanup is allowed to erase the selection path.
          </p>
        </div>
        <div className="lookup-receipt-flow" aria-hidden="true">
          <div>
            <span>address</span>
            <strong>{bits.join('')}</strong>
            <em>row {address}</em>
          </div>
          <i />
          <div>
            <span>selected data</span>
            <strong>{selectedBits}</strong>
            <em>{selectedValue}</em>
          </div>
          <i />
          <div>
            <span>counted owner</span>
            <strong>{scratchSlot}</strong>
            <em>{chunkBits} live wires</em>
          </div>
          <i />
          <div>
            <span>cleanup</span>
            <strong>reverse select</strong>
            <em>junk removed</em>
          </div>
        </div>
        <div className="lookup-receipt-ledger">
          <article>
            <span>Toy target capacity</span>
            <strong>8 wires</strong>
            <p>The selected byte is tiny so the lab can show every output bit.</p>
          </article>
          <article>
            <span>Repo chunk capacity</span>
            <strong>{chunkBits} wires</strong>
            <p>
              One streamed coordinate chunk is bigger than the toy byte and must have
              a live target owner while it is consumed.
            </p>
          </article>
          <article>
            <span>Full coordinate pressure</span>
            <strong>{fieldBits} wires</strong>
            <p>
              A complete secp256k1 coordinate is a field-sized value, represented here
              as <MathTex tex={`${chunkCount}`} /> streamed chunks rather than a free lane.
            </p>
          </article>
          <article>
            <span>Invalid shortcut</span>
            <strong>workspace name only</strong>
            <p>
              A resource row cannot say “lookup workspace” unless its numeric capacity
              covers decode/control bits plus the live selected-data target or a proven alias.
            </p>
          </article>
        </div>
      </section>
      <dl className="metric-row">
        <div><dt>Selected</dt><dd>{selectedValue}</dd></div>
        <div><dt>Workspace</dt><dd>{projectData.strictFormula.lookup_workspace_qubits}q</dd></div>
        <div><dt>Streams</dt><dd>{projectData.strictNonCliffordFormula.qroam_chunk_streams}</dd></div>
        <div><dt>NC total</dt><dd>{Math.round(projectData.strictNonCliffordFormula.qroam_chunk_non_clifford / 1_000_000)}M</dd></div>
      </dl>
      <div className="no-free-lane-callout">
        <span>No-free-lane audit</span>
        <strong>selected data must have an owner</strong>
        <p>
          In the real circuit, lookup x/y outputs are field-sized values. Counting
          only decode workspace is not enough unless liveness proves those outputs
          occupy already-counted arithmetic slots.
        </p>
      </div>
      <p>The toy table selects one byte. The repo selects secp256k1 table chunks; target lanes and cleanup are part of the accounting contract.</p>
    </article>
  );
}
