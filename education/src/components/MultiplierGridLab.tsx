import { useMemo, useState } from 'react';
import { Binary } from 'lucide-react';

const toBits = (value: number, width: number) => Array.from({ length: width }, (_, index) => (value >> index) & 1);

export function MultiplierGridLab() {
  const [left, setLeft] = useState(11);
  const [right, setRight] = useState(13);
  const width = 4;
  const leftBits = toBits(left, width);
  const rightBits = toBits(right, width);
  const cells = useMemo(() => {
    return rightBits.flatMap((rightBit, row) =>
      leftBits.map((leftBit, column) => ({
        row,
        column,
        active: leftBit === 1 && rightBit === 1,
        outputColumn: row + column,
      })),
    );
  }, [leftBits, rightBits]);
  const activeCount = cells.filter((cell) => cell.active).length;
  const columns = Array.from({ length: width * 2 - 1 }, (_, column) => ({
    column,
    count: cells.filter((cell) => cell.active && cell.outputColumn === column).length,
  }));

  return (
    <article className="lab-panel" data-testid="multiplier-grid-lab">
      <div className="panel-heading">
        <Binary size={20} />
        <h3>Partial-product grid</h3>
      </div>
      <div className="two-slider-grid">
        <label className="slider-label">
          left={left} ({left.toString(2).padStart(width, '0')})
          <input min="0" max="15" type="range" value={left} onChange={(event) => setLeft(Number(event.currentTarget.value))} />
        </label>
        <label className="slider-label">
          right={right} ({right.toString(2).padStart(width, '0')})
          <input min="0" max="15" type="range" value={right} onChange={(event) => setRight(Number(event.currentTarget.value))} />
        </label>
      </div>
      <div className="partial-grid" aria-label="Partial product cells">
        {cells.map((cell) => (
          <div className={cell.active ? 'partial-cell active' : 'partial-cell'} key={`${cell.row}-${cell.column}`}>
            c{cell.outputColumn}
          </div>
        ))}
      </div>
      <div className="column-loads" aria-label="Column loads">
        {columns.map((column) => (
          <div key={column.column}>
            <span>c{column.column}</span>
            <strong>{column.count}</strong>
          </div>
        ))}
      </div>
      <dl className="metric-row">
        <div><dt>Product</dt><dd>{left * right}</dd></div>
        <div><dt>Active ANDs</dt><dd>{activeCount}</dd></div>
        <div><dt>Columns</dt><dd>{columns.length}</dd></div>
        <div><dt>Width</dt><dd>{width} bits</dd></div>
      </dl>
      <p>
        At 256 bits this grid becomes the modular accumulator: many temporary
        AND targets, column carries, pseudo-Mersenne folds, and cleanup routes.
      </p>
    </article>
  );
}
