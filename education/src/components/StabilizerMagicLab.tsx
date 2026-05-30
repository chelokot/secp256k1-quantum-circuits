import { useMemo, useState } from 'react';
import { RotateCcw, Sparkles } from 'lucide-react';

type Gate = 'S' | 'Z' | 'T';

const gateTurns: Record<Gate, number> = {
  S: 2,
  Z: 4,
  T: 1,
};

const gateKind: Record<Gate, 'Clifford' | 'non-Clifford'> = {
  S: 'Clifford',
  Z: 'Clifford',
  T: 'non-Clifford',
};

const gateLegend: Record<Gate, { name: string; description: string }> = {
  S: {
    name: 'Clifford quarter-turn',
    description: 'moves from one stabilizer axis to the next',
  },
  Z: {
    name: 'Clifford half-turn',
    description: 'flips to the opposite stabilizer axis',
  },
  T: {
    name: 'non-Clifford eighth-turn',
    description: 'lands between axes and spends magic accounting',
  },
};

const axisNames = ['+X', '+Y', '-X', '-Y'];

const normalizeTurn = (turn: number) => ((turn % 8) + 8) % 8;

export function StabilizerMagicLab() {
  const [gates, setGates] = useState<Gate[]>([]);

  const state = useMemo(() => {
    const turn = normalizeTurn(gates.reduce((total, gate) => total + gateTurns[gate], 0));
    const angle = (turn * Math.PI) / 4;
    const isStabilizer = turn % 2 === 0;
    const nearestAxis = axisNames[Math.round(turn / 2) % axisNames.length];
    const nonCliffordCount = gates.filter((gate) => gateKind[gate] === 'non-Clifford').length;
    const magicAngle = isStabilizer ? 0 : 45;
    const costHistoryLabel = nonCliffordCount === 0
      ? 'Clifford-only path'
      : isStabilizer
        ? 'stabilizer endpoint after magic'
        : 'magic endpoint';
    const costHistoryDetail = nonCliffordCount === 0
      ? 'The selected sequence stayed inside the Clifford stabilizer map.'
      : isStabilizer
        ? `The final point is back on a stabilizer axis, but the stream already spent ${nonCliffordCount} non-Clifford step${nonCliffordCount === 1 ? '' : 's'}.`
        : 'The final point is between stabilizer axes, and the stream also has non-Clifford cost history.';
    return { angle, isStabilizer, magicAngle, nearestAxis, nonCliffordCount, turn, costHistoryLabel, costHistoryDetail };
  }, [gates]);

  const vectorEnd = {
    x: 50 + Math.cos(state.angle) * 34,
    y: 50 - Math.sin(state.angle) * 34,
  };

  return (
    <article className="lab-panel" data-testid="stabilizer-magic-lab">
      <div className="panel-heading">
        <Sparkles size={20} />
        <h3>Stabilizer vs magic wheel</h3>
      </div>
      <p>
        A small equator diagram is enough to expose the cost split. Clifford gates move
        between stabilizer axes that stay easy to track. A <code>T</code> step lands
        halfway between axes, creating the kind of non-stabilizer resource that
        fault-tolerant circuits must pay for.
      </p>

      <section className="magic-gate-legend" aria-label="Gate letter legend">
        {(['S', 'Z', 'T'] as Gate[]).map((gate) => (
          <article key={gate}>
            <strong>{gate}</strong>
            <span>{gateLegend[gate].name}</span>
            <p>{gateLegend[gate].description}</p>
          </article>
        ))}
      </section>

      <svg className="magic-wheel" viewBox="0 0 100 100" role="img" aria-label="Stabilizer and magic state wheel">
        <circle cx="50" cy="50" r="36" />
        <line x1="10" y1="50" x2="90" y2="50" />
        <line x1="50" y1="10" x2="50" y2="90" />
        <line className="magic-axis" x1="24.5" y1="75.5" x2="75.5" y2="24.5" />
        <line className="magic-axis" x1="24.5" y1="24.5" x2="75.5" y2="75.5" />
        <text x="86" y="47">+X</text>
        <text x="53" y="17">+Y</text>
        <text x="9" y="47">-X</text>
        <text x="53" y="88">-Y</text>
        <line className={state.isStabilizer ? 'state-vector stabilizer' : 'state-vector magic'} x1="50" y1="50" x2={vectorEnd.x} y2={vectorEnd.y} />
        <circle className={state.isStabilizer ? 'state-dot stabilizer' : 'state-dot magic'} cx={vectorEnd.x} cy={vectorEnd.y} r="3.2" />
      </svg>

      <div className="gate-row">
        {(['S', 'Z', 'T'] as Gate[]).map((gate) => (
          <button className={gateKind[gate] === 'non-Clifford' ? 'non-clifford-button' : undefined} key={gate} type="button" onClick={() => setGates((items) => [...items, gate])}>
            {gate}
          </button>
        ))}
        <button type="button" onClick={() => setGates(['T', 'T'])}>
          T then T
        </button>
        <button type="button" aria-label="Reset stabilizer magic wheel" onClick={() => setGates([])}>
          <RotateCcw size={16} />
        </button>
      </div>

      <section className="magic-sequence-ledger" aria-label="Selected magic sequence ledger">
        <h4>Sequence ledger</h4>
        {gates.length === 0 ? (
          <article>
            <strong>identity</strong>
            <span>no cost yet</span>
            <p>The state is still on a stabilizer axis, so the toy counter stays at zero.</p>
          </article>
        ) : gates.map((gate, index) => (
          <article key={`${gate}-${index}`}>
            <strong>{index + 1}. {gate}</strong>
            <span>{gateKind[gate]}</span>
            <p>{gateLegend[gate].description}</p>
          </article>
        ))}
      </section>

      <div className="magic-status-grid">
        <article>
          <span>State class</span>
          <strong>{state.isStabilizer ? 'stabilizer' : 'magic'}</strong>
          <p>{state.isStabilizer ? 'Clifford-trackable axis' : 'between stabilizer axes'}</p>
        </article>
        <article>
          <span>Nearest stabilizer</span>
          <strong>{state.nearestAxis}</strong>
          <p>{state.magicAngle}° away in this toy wheel</p>
        </article>
        <article>
          <span>Non-Clifford steps</span>
          <strong>{state.nonCliffordCount}</strong>
          <p>{gates.join(' ') || 'identity'} sequence</p>
        </article>
      </div>

      <section className={`magic-history-lab-panel ${state.nonCliffordCount > 0 ? 'spent' : 'clean'}`} aria-label="Endpoint versus non-Clifford history">
        <div>
          <h4>Endpoint class is not the cost history</h4>
          <p>
            A sequence can end on a stabilizer axis after spending T gates. The wheel
            shows the final point; the ledger records the expensive steps taken to get
            there.
          </p>
        </div>
        <strong>{state.costHistoryLabel}</strong>
        <span>{state.costHistoryDetail}</span>
      </section>

      <p className="mono-line">turn={state.turn}/8 simulator={state.isStabilizer ? 'stabilizer-friendly' : 'needs magic accounting'}</p>
    </article>
  );
}
