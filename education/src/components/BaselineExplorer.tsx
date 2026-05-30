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

const statusKey = [
  {
    label: 'Public reference',
    text: 'Useful comparison data from outside this repo; it does not prove this implementation.',
  },
  {
    label: 'Repo candidate',
    text: 'Repo-generated engineering evidence that still carries explicit blockers.',
  },
  {
    label: 'Guard consequence',
    text: 'A derived correction from a candidate, not a separately accepted baseline.',
  },
  {
    label: 'Accepted baseline',
    text: 'The slot stays empty until primitive stream, blockers, docs, and proof boundary agree.',
  },
];

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
      <section className="baseline-status-key" aria-label="Baseline status key">
        {statusKey.map((item) => (
          <article key={item.label}>
            <strong>{item.label}</strong>
            <p>{item.text}</p>
          </article>
        ))}
      </section>
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
