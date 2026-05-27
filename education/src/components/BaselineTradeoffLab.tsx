import { useMemo, useState } from 'react';
import * as d3 from 'd3';
import { GitCompareArrows } from 'lucide-react';

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

type Lens = 'all' | 'google' | 'repo' | 'accepted';

const formatInt = (value: number) => new Intl.NumberFormat('en-US').format(value);
const formatMillion = (value: number) => `${(value / 1_000_000).toFixed(value >= 10_000_000 ? 1 : 2)}M`;
const readable = (value: string) => value.replaceAll('_', ' ');

const pointColor = (row: BaselineRow) => {
  if (row.status === 'external_public_baseline') return '#8fb8ff';
  if (row.status.includes('not_accepted') || row.status.includes('not_promoted')) return '#f5cf6b';
  return '#b4c4d6';
};

export function BaselineTradeoffLab({ projectData }: { projectData: ProjectData }) {
  const [selectedId, setSelectedId] = useState('google_low_gate');
  const [lens, setLens] = useState<Lens>('all');

  const rows = projectData.baselineRows;
  const visibleRows = useMemo(() => {
    if (lens === 'google') return rows.filter((row) => row.status === 'external_public_baseline');
    if (lens === 'repo') return rows.filter((row) => row.status !== 'external_public_baseline');
    if (lens === 'accepted') return rows.filter((row) => row.status === 'accepted_physical_baseline');
    return rows;
  }, [lens, rows]);
  const selected = rows.find((row) => row.id === selectedId) ?? rows[0];
  const googleLowQubit = rows.find((row) => row.id === 'google_low_qubit') ?? rows[0];
  const googleLowGate = rows.find((row) => row.id === 'google_low_gate') ?? rows[0];

  const xScale = d3.scaleLinear()
    .domain([900, (d3.max(rows, (row) => row.logicalQubits) ?? 2200) + 150])
    .range([58, 530]);
  const yScale = d3.scaleLinear()
    .domain([30_000_000, (d3.max(rows, (row) => row.nonClifford) ?? 90_000_000) + 5_000_000])
    .range([250, 34]);
  const xTicks = xScale.ticks(5);
  const yTicks = yScale.ticks(4);
  const nonCliffordVsLowQubit = googleLowQubit.nonClifford / selected.nonClifford;
  const nonCliffordVsLowGate = googleLowGate.nonClifford / selected.nonClifford;
  const isAccepted = selected.status === 'accepted_physical_baseline';

  return (
    <section className="wide-panel" data-testid="baseline-tradeoff-lab">
      <div className="panel-heading">
        <GitCompareArrows size={20} />
        <h3>Baseline tradeoff landscape</h3>
      </div>
      <p>
        Lower-left is the dream: fewer logical qubits and fewer non-Clifford operations.
        Google published two rounded public lines, not one universal point:
        {' '}1,200q / 90M and 1,450q / 70M.
      </p>

      <div className="tradeoff-controls">
        <label>
          <span>Status lens</span>
          <select aria-label="Baseline status lens" onChange={(event) => setLens(event.currentTarget.value as Lens)} value={lens}>
            <option value="all">All rows</option>
            <option value="google">Google public lines</option>
            <option value="repo">Repo rows only</option>
            <option value="accepted">Accepted physical baselines</option>
          </select>
        </label>
        <label>
          <span>Selected baseline row</span>
          <select aria-label="Selected baseline row" onChange={(event) => setSelectedId(event.currentTarget.value)} value={selectedId}>
            {rows.map((row) => (
              <option key={row.id} value={row.id}>{row.label}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="tradeoff-grid">
        <article>
          {visibleRows.length === 0 ? (
            <div className="empty-tradeoff">
              No accepted physical baseline rows yet.
            </div>
          ) : (
            <svg className="tradeoff-plane" role="img" aria-label="Baseline qubit and non-Clifford tradeoff plane" viewBox="0 0 580 290">
              <line x1="58" x2="530" y1="250" y2="250" />
              <line x1="58" x2="58" y1="34" y2="250" />
              {xTicks.map((tick) => (
                <g key={tick}>
                  <line className="grid-line" x1={xScale(tick)} x2={xScale(tick)} y1="34" y2="250" />
                  <text x={xScale(tick)} y="272">{formatInt(tick)}q</text>
                </g>
              ))}
              {yTicks.map((tick) => (
                <g key={tick}>
                  <line className="grid-line" x1="58" x2="530" y1={yScale(tick)} y2={yScale(tick)} />
                  <text x="52" y={yScale(tick) + 4}>{formatMillion(tick)}</text>
                </g>
              ))}
              <text className="axis-label" x="290" y="288">logical qubits</text>
              <text className="axis-label rotated" x="-164" y="14">non-Clifford</text>
              {visibleRows.map((row) => (
                <g key={row.id}>
                  <circle
                    cx={xScale(row.logicalQubits)}
                    cy={yScale(row.nonClifford)}
                    fill={pointColor(row)}
                    onClick={() => setSelectedId(row.id)}
                    r={row.id === selected.id ? 9 : 7}
                  />
                  <text className="point-label" x={xScale(row.logicalQubits) + 10} y={yScale(row.nonClifford) + 4}>
                    {row.label.replace('Google ', 'G ').replace('Repo ', 'R ')}
                  </text>
                </g>
              ))}
            </svg>
          )}
        </article>

        <article>
          <h4>{selected.label}</h4>
          <dl className="metric-pair">
            <div>
              <dt>Logical qubits</dt>
              <dd>{formatInt(selected.logicalQubits)}</dd>
            </div>
            <div>
              <dt>Non-Clifford</dt>
              <dd>{formatMillion(selected.nonClifford)}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{readable(selected.status)}</dd>
            </div>
            <div>
              <dt>Accepted?</dt>
              <dd>{isAccepted ? 'yes' : 'no'}</dd>
            </div>
          </dl>
          <p>{selected.note}</p>
          <p>
            Non-Clifford ratio vs Google low-qubit line: {nonCliffordVsLowQubit.toFixed(2)}x.
            Ratio vs Google low-gate line: {nonCliffordVsLowGate.toFixed(2)}x.
          </p>
          <p className={isAccepted ? 'audit-pass' : 'audit-fail'}>
            Claim wording: {isAccepted ? 'accepted baseline allowed' : 'do not call this accepted baseline'}
          </p>
        </article>
      </div>
    </section>
  );
}
