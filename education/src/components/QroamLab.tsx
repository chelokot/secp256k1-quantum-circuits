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
        <div><dt>Selected</dt><dd>{table[address]}</dd></div>
        <div><dt>Workspace</dt><dd>{projectData.strictFormula.lookup_workspace_qubits}q</dd></div>
        <div><dt>Streams</dt><dd>{projectData.strictNonCliffordFormula.qroam_chunk_streams}</dd></div>
        <div><dt>NC total</dt><dd>{Math.round(projectData.strictNonCliffordFormula.qroam_chunk_non_clifford / 1_000_000)}M</dd></div>
      </dl>
      <p>The toy table selects one byte. The repo selects secp256k1 table chunks; target lanes and cleanup are part of the accounting contract.</p>
    </article>
  );
}
