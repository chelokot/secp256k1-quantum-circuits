import { useMemo, useState } from 'react';
import { Binary } from 'lucide-react';

const toBits = (value: number, width: number) => Array.from({ length: width }, (_, index) => (value >> index) & 1);

export function MultiplierGridLab() {
  const [left, setLeft] = useState(11);
  const [right, setRight] = useState(13);
  const [selectedKey, setSelectedKey] = useState('0-0');
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
  const selectedCell = cells.find((cell) => `${cell.row}-${cell.column}` === selectedKey) ?? cells[0];
  const selectedTemp = `t_${selectedCell.column}_${selectedCell.row}`;

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
          <button
            aria-label={`Select product cell x${cell.column} y${cell.row}`}
            className={`${cell.active ? 'partial-cell active' : 'partial-cell'} ${selectedCell === cell ? 'selected' : ''}`}
            key={`${cell.row}-${cell.column}`}
            onClick={() => setSelectedKey(`${cell.row}-${cell.column}`)}
            type="button"
          >
            c{cell.outputColumn}
          </button>
        ))}
      </div>
      <div className="product-obligation-ledger">
        <article>
          <span>Selected cell</span>
          <strong>x{selectedCell.column} AND y{selectedCell.row}</strong>
          <p>{selectedCell.active ? 'active for this input' : 'inactive for this input, but still a possible branch in superposition'}</p>
        </article>
        <article>
          <span>Birth</span>
          <strong>CCX x{selectedCell.column} y{selectedCell.row} {selectedTemp}</strong>
          <p>A temporary target stores the one-bit product.</p>
        </article>
        <article>
          <span>Use</span>
          <strong>{selectedTemp} {'->'} column c{selectedCell.outputColumn}</strong>
          <p>The accumulator consumes the bit into the correct weight column.</p>
        </article>
        <article>
          <span>Death</span>
          <strong>inverse CCX with same controls</strong>
          <p>The cleanup row must erase {selectedTemp} before the owner can release it.</p>
        </article>
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
