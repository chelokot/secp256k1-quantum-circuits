import { useMemo, useState } from 'react';
import { Sparkles } from 'lucide-react';

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
const formatDays = (value: number) => `${value.toFixed(value < 10 ? 1 : 0)} days`;

export function MagicBudgetLab({ projectData }: { projectData: ProjectData }) {
  const [selectedId, setSelectedId] = useState('repo_strict_candidate');
  const [factoryRate, setFactoryRate] = useState(5);
  const [factoryCount, setFactoryCount] = useState(2);
  const selected = projectData.baselineRows.find((row) => row.id === selectedId) ?? projectData.baselineRows[0];

  const budget = useMemo(() => {
    const dailyCapacity = factoryRate * factoryCount * 1_000_000;
    const runtimeDays = selected.nonClifford / dailyCapacity;
    const nonCliffordPerLogical = selected.nonClifford / selected.logicalQubits;
    const googleLowQubit = projectData.baselineRows.find((row) => row.id === 'google_low_qubit') ?? selected;
    const gateRatio = googleLowQubit.nonClifford / selected.nonClifford;
    return { dailyCapacity, runtimeDays, nonCliffordPerLogical, gateRatio };
  }, [factoryCount, factoryRate, projectData.baselineRows, selected]);

  return (
    <section className="wide-panel" data-testid="magic-budget-lab">
      <div className="panel-heading">
        <Sparkles size={20} />
        <h3>Non-Clifford magic budget</h3>
      </div>
      <p>
        Clifford gates are the easy stabilizer backbone in this simplified model.
        Non-Clifford gates are the scarce magic-state fuel. The budget dial shows why
        the repo tracks gate count separately from live logical qubits.
      </p>
      <section className="magic-budget-boundary" aria-label="Magic budget model boundary">
        <article>
          <strong>What the dial means</strong>
          <p>
            It divides the selected non-Clifford ledger by an imagined factory capacity
            so the pressure is easy to feel.
          </p>
        </article>
        <article>
          <strong>What it does not mean</strong>
          <p>
            It is not a runtime forecast: no routing, cycle time, decoder latency,
            factory layout, or target failure rate is modeled here.
          </p>
        </article>
      </section>

      <div className="magic-controls">
        <label>
          <span>Resource row</span>
          <select
            aria-label="Magic budget resource row"
            value={selectedId}
            onChange={(event) => setSelectedId(event.currentTarget.value)}
          >
            {projectData.baselineRows.map((row) => (
              <option key={row.id} value={row.id}>{row.label}</option>
            ))}
          </select>
        </label>
        <label>
          <span>Factory rate: {factoryRate}M/day</span>
          <input
            aria-label="Magic factory rate"
            min="1"
            max="20"
            step="1"
            type="range"
            value={factoryRate}
            onChange={(event) => setFactoryRate(Number(event.currentTarget.value))}
          />
        </label>
        <label>
          <span>Parallel factories: {factoryCount}</span>
          <input
            aria-label="Parallel magic factories"
            min="1"
            max="8"
            step="1"
            type="range"
            value={factoryCount}
            onChange={(event) => setFactoryCount(Number(event.currentTarget.value))}
          />
        </label>
      </div>

      <div className="magic-grid">
        <article>
          <span>Non-Clifford total</span>
          <strong>{formatInt(selected.nonClifford)}</strong>
          <p>{selected.status.replaceAll('_', ' ')}</p>
        </article>
        <article>
          <span>Toy daily capacity</span>
          <strong>{formatInt(budget.dailyCapacity)}</strong>
          <p>{factoryRate}M * {factoryCount} factories</p>
        </article>
        <article>
          <span>Toy magic runtime</span>
          <strong>{formatDays(budget.runtimeDays)}</strong>
          <p>non-Clifford total divided by factory capacity</p>
        </article>
        <article>
          <span>Per logical qubit</span>
          <strong>{formatInt(Math.round(budget.nonCliffordPerLogical))}</strong>
          <p>gate pressure per live logical wire</p>
        </article>
      </div>

      <div className="magic-stack">
        <div><strong>Clifford rows</strong><span>cheap steering, stabilizer bookkeeping, measurements</span></div>
        <div><strong>Non-Clifford rows</strong><span>Toffoli-like arithmetic decisions and table-selection work</span></div>
        <div><strong>Factory bottleneck</strong><span>{formatDays(budget.runtimeDays)} in this toy setting</span></div>
        <div><strong>Google low-q ratio</strong><span>{budget.gateRatio.toFixed(2)}x selected non-Clifford count</span></div>
      </div>
    </section>
  );
}
