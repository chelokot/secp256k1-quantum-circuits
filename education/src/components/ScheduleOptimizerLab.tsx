import { useMemo, useState } from 'react';
import { TimerReset } from 'lucide-react';

type WireTemplate = {
  id: string;
  width: number;
  start: number;
  fixedEnd?: number;
  role: string;
};

const ticks = [0, 1, 2, 3, 4, 5, 6, 7];

const wireTemplates: WireTemplate[] = [
  { id: 'accumulator field slot', width: 4, start: 0, fixedEnd: 8, role: 'carried input' },
  { id: 'lookup coordinate chunk', width: 3, start: 1, fixedEnd: 3, role: 'table output' },
  { id: 'alpha partial scratch', width: 2, start: 2, role: 'temporary product' },
  { id: 'beta carry scratch', width: 3, start: 3, role: 'temporary carry' },
  { id: 'phase/control bit', width: 1, start: 5, fixedEnd: 8, role: 'control shell' },
  { id: 'output field slot', width: 4, start: 6, fixedEnd: 8, role: 'returned point' },
];

export function ScheduleOptimizerLab() {
  const [alphaCleanup, setAlphaCleanup] = useState(7);
  const [betaCleanup, setBetaCleanup] = useState(7);

  const schedule = useMemo(() => {
    const wires = wireTemplates.map((wire) => ({
      ...wire,
      end: wire.id === 'alpha partial scratch'
        ? alphaCleanup
        : wire.id === 'beta carry scratch'
          ? betaCleanup
          : wire.fixedEnd ?? 8,
    }));

    const rows = ticks.map((tick) => {
      const live = wires.filter((wire) => wire.start <= tick && tick < wire.end);
      const total = live.reduce((sum, wire) => sum + wire.width, 0);
      return { tick, live, total };
    });
    const peak = rows.reduce((best, row) => (row.total > best.total ? row : best), rows[0]);
    const targetPeak = 9;
    return {
      wires,
      rows,
      peak,
      targetPeak,
      pass: peak.total <= targetPeak && alphaCleanup <= 4 && betaCleanup <= 5,
    };
  }, [alphaCleanup, betaCleanup]);

  return (
    <section className="wide-panel" data-testid="schedule-optimizer-lab">
      <div className="panel-heading">
        <TimerReset size={20} />
        <h3>Schedule optimizer lab</h3>
      </div>
      <p>
        Peak qubits are not the sum of everything ever mentioned. They are the maximum
        concurrent live width. Moving cleanup earlier shortens lifetimes and can reduce the peak
        without changing the semantic outputs.
      </p>

      <div className="schedule-grid">
        <article>
          <h4>Move cleanup rows</h4>
          <label className="slider-label">
            Alpha scratch cleanup row: {alphaCleanup}
            <input
              aria-label="Alpha scratch cleanup row"
              min="4"
              max="7"
              type="range"
              value={alphaCleanup}
              onChange={(event) => setAlphaCleanup(Number(event.currentTarget.value))}
            />
          </label>
          <label className="slider-label">
            Beta scratch cleanup row: {betaCleanup}
            <input
              aria-label="Beta scratch cleanup row"
              min="5"
              max="7"
              type="range"
              value={betaCleanup}
              onChange={(event) => setBetaCleanup(Number(event.currentTarget.value))}
            />
          </label>
          <p className={schedule.pass ? 'audit-pass' : 'audit-fail'}>
            Schedule audit: {schedule.pass ? 'pass' : 'fail'}
          </p>
          <p>
            Peak live qubits: {schedule.peak.total} at row {schedule.peak.tick}.
            Target peak: {schedule.targetPeak}.
          </p>
        </article>

        <article>
          <h4>Live load by row</h4>
          <div className="schedule-loads">
            {schedule.rows.map((row) => (
              <div className={row.total === schedule.peak.total ? 'peak' : ''} key={row.tick}>
                <span>row {row.tick}</span>
                <strong>{row.total}</strong>
                <i style={{ width: `${row.total * 7}%` }} />
              </div>
            ))}
          </div>
        </article>
      </div>

      <div className="schedule-timeline">
        {schedule.wires.map((wire) => (
          <div key={wire.id}>
            <span>{wire.id}</span>
            {ticks.map((tick) => (
              <i
                className={wire.start <= tick && tick < wire.end ? 'live' : ''}
                key={tick}
                title={`row ${tick}`}
              />
            ))}
            <strong>{wire.width}q</strong>
            <em>{wire.role}</em>
          </div>
        ))}
      </div>
    </section>
  );
}
