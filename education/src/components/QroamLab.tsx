import { useMemo, useState } from 'react';
import { Binary } from 'lucide-react';

type ProjectData = {
  strictNonCliffordFormula: {
    qroam_chunk_streams: number;
    per_chunk_stream_non_clifford: number;
    qroam_chunk_non_clifford: number;
  };
  strictFormula: {
    lookup_workspace_qubits: number;
  };
};

const table = [
  '0x6a', '0x13', '0xdf', '0x92', '0x41', '0xb8', '0x75', '0x0c',
];

export function QroamLab({ projectData }: { projectData: ProjectData }) {
  const [address, setAddress] = useState(5);
  const bits = useMemo(() => [4, 2, 1].map((mask) => (address & mask ? 1 : 0)), [address]);
  const selectedValue = table[address];

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
