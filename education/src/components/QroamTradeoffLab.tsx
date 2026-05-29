import { useMemo, useState } from 'react';
import { Binary } from 'lucide-react';

type ProjectData = {
  compilerParameters: {
    windowing: {
      foldedMagnitudeDomain: number;
    };
    lookupPolicy: {
      standardQroamcleanBlockSize: number;
    };
    reusableChunkPolicy: {
      chunkBits: number;
    };
  };
};

export function QroamTradeoffLab({ projectData }: { projectData: ProjectData }) {
  const [k, setK] = useState(projectData.compilerParameters.lookupPolicy.standardQroamcleanBlockSize);
  const entries = projectData.compilerParameters.windowing.foldedMagnitudeDomain;
  const bitsize = projectData.compilerParameters.reusableChunkPolicy.chunkBits;
  const cost = useMemo(() => {
    const compute = Math.ceil(entries / k) + (k - 1) * bitsize;
    const cleanup = Math.ceil(entries / k) + (k - 1);
    const target = bitsize;
    const junk = (k - 1) * bitsize;
    const workspace = target + junk;
    return { compute, cleanup, target, junk, total: compute + cleanup, workspace };
  }, [bitsize, entries, k]);

  return (
    <article className="lab-panel" data-testid="qroam-tradeoff-lab">
      <div className="panel-heading">
        <Binary size={20} />
        <h3>QROAMClean tradeoff dial</h3>
      </div>
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
        <div><dt>NC toy cost</dt><dd>{cost.total}</dd></div>
        <div><dt>Workspace</dt><dd>{cost.workspace}</dd></div>
      </dl>
      <div className="qroam-formula-strip">
        <div><span>target</span><strong>{cost.target}</strong></div>
        <div><span>junk</span><strong>{cost.junk}</strong></div>
        <div><span>compute</span><strong>N/K + (K - 1)b</strong></div>
        <div><span>cleanup</span><strong>N/K + (K - 1)</strong></div>
      </div>
      <p>
        Increasing K can reduce selection work but increases junk-register
        capacity. This is exactly the consistency trap the repo now teaches you
        to audit.
      </p>
    </article>
  );
}
