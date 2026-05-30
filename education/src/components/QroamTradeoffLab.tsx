import { useMemo, useState } from 'react';
import { Binary } from 'lucide-react';

type ProjectData = {
  compilerParameters: {
    field: {
      fieldBits: number;
    };
    windowing: {
      foldedMagnitudeDomain: number;
    };
    lookupPolicy: {
      standardQroamcleanBlockSize: number;
    };
    reusableChunkPolicy: {
      chunkBits: number;
      chunkCount: number;
    };
  };
};

type LookupModel = 'chunk' | 'full_coordinate' | 'one_bit';

const lookupModels: Array<{
  id: LookupModel;
  label: string;
  summary: string;
}> = [
  {
    id: 'chunk',
    label: 'Checked chunk stream',
    summary: 'Use repo chunk size and repeat for the checked chunk count.',
  },
  {
    id: 'full_coordinate',
    label: 'Full-coordinate QROAM',
    summary: 'Amortize one 256-bit coordinate load, but count all target and junk bits.',
  },
  {
    id: 'one_bit',
    label: 'One-bit stream',
    summary: 'Keep the target tiny, but pay lookup work once per coordinate bit.',
  },
];

const formatInt = (value: number) => new Intl.NumberFormat('en-US').format(value);

export function QroamTradeoffLab({ projectData }: { projectData: ProjectData }) {
  const [k, setK] = useState(projectData.compilerParameters.lookupPolicy.standardQroamcleanBlockSize);
  const [modelId, setModelId] = useState<LookupModel>('full_coordinate');
  const entries = projectData.compilerParameters.windowing.foldedMagnitudeDomain;
  const bitsize = projectData.compilerParameters.reusableChunkPolicy.chunkBits;
  const fieldBits = projectData.compilerParameters.field.fieldBits;
  const chunkCount = projectData.compilerParameters.reusableChunkPolicy.chunkCount;
  const model = lookupModels.find((item) => item.id === modelId) ?? lookupModels[1];
  const cost = useMemo(() => {
    const compute = Math.ceil(entries / k) + (k - 1) * bitsize;
    const cleanup = Math.ceil(entries / k) + (k - 1);
    const target = bitsize;
    const junk = (k - 1) * bitsize;
    const workspace = target + junk;
    return { compute, cleanup, target, junk, total: compute + cleanup, workspace };
  }, [bitsize, entries, k]);
  const modelCost = useMemo(() => {
    const target = modelId === 'one_bit' ? 1 : modelId === 'full_coordinate' ? fieldBits : bitsize;
    const streams = modelId === 'one_bit' ? fieldBits : modelId === 'full_coordinate' ? 1 : chunkCount;
    const compute = Math.ceil(entries / k) + (k - 1) * target;
    const cleanup = Math.ceil(entries / k) + (k - 1);
    const junk = (k - 1) * target;
    const peakTargetAndJunk = target + junk;
    return {
      cleanup,
      compute,
      junk,
      peakTargetAndJunk,
      streams,
      target,
      total: (compute + cleanup) * streams,
    };
  }, [bitsize, chunkCount, entries, fieldBits, k, modelId]);

  return (
    <article className="lab-panel" data-testid="qroam-tradeoff-lab">
      <div className="panel-heading">
        <Binary size={20} />
        <h3>QROAMClean tradeoff dial</h3>
      </div>
      <p>
        QROAMClean is a clean-workspace table lookup model. Increasing the block size
        can reduce selection work, but the saved gates are paid for with extra live
        junk-register bits.
      </p>
      <label className="slider-label">
        Block size K={k}
        <input min="1" max="16" type="range" value={k} onChange={(event) => setK(Number(event.currentTarget.value))} />
      </label>
      <div className="lookup-audit-grid compact">
        <article>
          <span>Compute</span>
          <strong>{cost.compute}</strong>
          <p>N/K plus data-selection work.</p>
        </article>
        <article>
          <span>Cleanup</span>
          <strong>{cost.cleanup}</strong>
          <p>Reverse the temporary selection path.</p>
        </article>
        <article>
          <span>Workspace</span>
          <strong>{cost.workspace}</strong>
          <p>Target bits plus extra junk-register capacity.</p>
        </article>
      </div>
      <dl className="metric-row">
        <div><dt>Entries</dt><dd>{entries}</dd></div>
        <div><dt>Bits</dt><dd>{bitsize}</dd></div>
        <div><dt>Non-Clifford toy cost</dt><dd>{cost.total}</dd></div>
        <div><dt>Workspace</dt><dd>{cost.workspace}</dd></div>
      </dl>
      <div className="qroam-formula-strip">
        <div><span>target</span><strong>{cost.target}</strong></div>
        <div><span>junk</span><strong>{cost.junk}</strong></div>
        <div><span>compute</span><strong>N/K + (K - 1)b</strong></div>
        <div><span>cleanup</span><strong>N/K + (K - 1)</strong></div>
      </div>
      <section className="qroam-model-auditor" aria-label="QROAM construction consistency auditor">
        <div>
          <h4>Construction consistency auditor</h4>
          <p>
            Choose one construction and keep its gate and qubit formulas together. A
            full-width target can amortize data bits, but its junk registers are also
            full-width. A one-bit stream keeps workspace small by repeating the lookup.
          </p>
          <div className="qroam-model-buttons">
            {lookupModels.map((item) => (
              <button
                className={item.id === modelId ? 'selected' : ''}
                key={item.id}
                type="button"
                onClick={() => setModelId(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
        <div className="qroam-model-card">
          <span>{model.label}</span>
          <strong>{formatInt(modelCost.total)} total lookup work</strong>
          <p>{model.summary}</p>
          <div>
            <article>
              <em>target bits</em>
              <b>{formatInt(modelCost.target)}</b>
            </article>
            <article>
              <em>streams</em>
              <b>{formatInt(modelCost.streams)}</b>
            </article>
            <article>
              <em>junk bits</em>
              <b>{formatInt(modelCost.junk)}</b>
            </article>
            <article>
              <em>peak target+junk bits</em>
              <b>{formatInt(modelCost.peakTargetAndJunk)}</b>
            </article>
          </div>
        </div>
      </section>
      <p>
        Increasing K can reduce selection work but increases junk-register
        capacity. This is exactly the consistency trap the repo now teaches you
        to audit.
      </p>
    </article>
  );
}
