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
    return { angle, isStabilizer, magicAngle, nearestAxis, nonCliffordCount, turn };
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
        This toy equator is the smallest mental model for the cost split. Clifford gates
        move between stabilizer axes that stay easy to track. A <code>T</code> step lands
        halfway between axes, creating the kind of non-stabilizer resource that fault-tolerant
        circuits must pay for.
      </p>

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
        <button type="button" aria-label="Reset stabilizer magic wheel" onClick={() => setGates([])}>
          <RotateCcw size={16} />
        </button>
      </div>

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

      <p className="mono-line">turn={state.turn}/8 simulator={state.isStabilizer ? 'stabilizer-friendly' : 'needs magic accounting'}</p>
    </article>
  );
}
