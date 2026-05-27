import { useMemo, useState } from 'react';
import { Binary } from 'lucide-react';

export function QroamTradeoffLab() {
  const [k, setK] = useState(1);
  const entries = 32_768;
  const bitsize = 155;
  const cost = useMemo(() => {
    const compute = Math.ceil(entries / k) + (k - 1) * bitsize;
    const cleanup = Math.ceil(entries / k) + (k - 1);
    const workspace = bitsize + (k - 1) * bitsize;
    return { compute, cleanup, total: compute + cleanup, workspace };
  }, [k]);

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
      <dl className="metric-row">
        <div><dt>Entries</dt><dd>{entries}</dd></div>
        <div><dt>Bits</dt><dd>{bitsize}</dd></div>
        <div><dt>NC toy cost</dt><dd>{cost.total}</dd></div>
        <div><dt>Workspace</dt><dd>{cost.workspace}</dd></div>
      </dl>
      <p>
        Increasing K can reduce selection work but increases junk-register
        capacity. This is exactly the consistency trap the repo now teaches you
        to audit.
      </p>
    </article>
  );
}
