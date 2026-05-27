import { useMemo, useState } from 'react';
import { RotateCcw } from 'lucide-react';

const prime = 17;

export function ModularReductionLab() {
  const [left, setLeft] = useState(13);
  const [right, setRight] = useState(11);
  const product = left * right;
  const chunks = useMemo(() => {
    const low = product % prime;
    const high = Math.floor(product / prime);
    return { low, high, folded: (low + high * (17 % prime)) % prime };
  }, [product]);

  return (
    <article className="lab-panel" data-testid="modular-reduction-lab">
      <div className="panel-heading">
        <RotateCcw size={20} />
        <h3>Modular multiplication shape</h3>
      </div>
      <div className="two-slider-grid">
        <label className="slider-label">
          left={left}
          <input min="0" max="16" type="range" value={left} onChange={(event) => setLeft(Number(event.currentTarget.value))} />
        </label>
        <label className="slider-label">
          right={right}
          <input min="0" max="16" type="range" value={right} onChange={(event) => setRight(Number(event.currentTarget.value))} />
        </label>
      </div>
      <div className="reduction-flow">
        <div><span>multiply</span><strong>{left} * {right} = {product}</strong></div>
        <div><span>split</span><strong>low {chunks.low}, high {chunks.high}</strong></div>
        <div><span>reduce</span><strong>{product} mod {prime} = {product % prime}</strong></div>
      </div>
      <p>
        The repo’s modular accumulator problem is this idea at 256-bit scale:
        partial products, fold rows, cleanup rows, carry obligations, and no
        hidden scratch capacity.
      </p>
    </article>
  );
}
