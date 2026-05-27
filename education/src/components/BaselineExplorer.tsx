import * as d3 from 'd3';
import { BarChart3 } from 'lucide-react';

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

const formatCompact = (value: number) => {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(value >= 10_000_000 ? 1 : 2)}M`;
  return new Intl.NumberFormat('en-US').format(value);
};

export function BaselineExplorer({ projectData }: { projectData: ProjectData }) {
  const rows = projectData.baselineRows;
  const maxQubits = d3.max(rows, (row) => row.logicalQubits) ?? 1;
  const maxNonClifford = d3.max(rows, (row) => row.nonClifford) ?? 1;
  const qubitScale = d3.scaleLinear([0, maxQubits], [0, 100]);
  const nonCliffordScale = d3.scaleLinear([0, maxNonClifford], [0, 100]);

  return (
    <section className="wide-panel" data-testid="baseline-explorer">
      <div className="panel-heading">
        <BarChart3 size={20} />
        <h3>Baseline status explorer</h3>
      </div>
      <div className="baseline-explorer-grid">
        {rows.map((row) => (
          <article key={row.id}>
            <header>
              <strong>{row.label}</strong>
              <span>{row.status.replaceAll('_', ' ')}</span>
            </header>
            <div className="bar-pair">
              <div className="bar qubit" style={{ width: `${qubitScale(row.logicalQubits)}%` }}><span>{row.logicalQubits}q</span></div>
              <div className="bar gate" style={{ width: `${nonCliffordScale(row.nonClifford)}%` }}><span>{formatCompact(row.nonClifford)}</span></div>
            </div>
            <p>{row.note}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
