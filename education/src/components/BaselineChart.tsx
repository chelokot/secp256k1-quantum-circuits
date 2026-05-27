import { useMemo } from 'react';
import * as d3 from 'd3';
import { BarChart3 } from 'lucide-react';

type ProjectData = {
  currentStrictCandidate: { logical_qubits: number; non_clifford: number };
  guardCorrectedNoAliasCandidate: { logical_qubits: number; non_clifford: number };
  googleBaseline: Record<string, { logical_qubits: number; non_clifford: number }>;
};

export function BaselineChart({ projectData }: { projectData: ProjectData }) {
  const rows = useMemo(() => [
    { name: 'Google low-q', qubits: projectData.googleBaseline.low_qubit.logical_qubits, gates: projectData.googleBaseline.low_qubit.non_clifford },
    { name: 'Google low-gate', qubits: projectData.googleBaseline.low_gate.logical_qubits, gates: projectData.googleBaseline.low_gate.non_clifford },
    { name: 'Strict candidate', qubits: projectData.currentStrictCandidate.logical_qubits, gates: projectData.currentStrictCandidate.non_clifford },
    { name: 'Guard corrected', qubits: projectData.guardCorrectedNoAliasCandidate.logical_qubits, gates: projectData.guardCorrectedNoAliasCandidate.non_clifford },
  ], [projectData]);

  const maxQubits = d3.max(rows, (row) => row.qubits) ?? 1;
  const maxGates = d3.max(rows, (row) => row.gates) ?? 1;
  const qubitScale = d3.scaleLinear([0, maxQubits], [0, 100]);
  const gateScale = d3.scaleLinear([0, maxGates], [0, 100]);

  return (
    <article className="lab-panel" data-testid="baseline-chart">
      <div className="panel-heading">
        <BarChart3 size={20} />
        <h3>Baselines as tradeoffs</h3>
      </div>
      <div className="bar-list">
        {rows.map((row) => (
          <div className="bar-row" key={row.name}>
            <span>{row.name}</span>
            <div className="bar-pair">
              <div className="bar qubit" style={{ width: `${qubitScale(row.qubits)}%` }}><span>{row.qubits}q</span></div>
              <div className="bar gate" style={{ width: `${gateScale(row.gates)}%` }}><span>{Math.round(row.gates / 1_000_000)}M</span></div>
            </div>
          </div>
        ))}
      </div>
      <p>Blue bars are logical qubits. Green bars are non-Clifford scale. The learning target is understanding why both axes fight each other.</p>
    </article>
  );
}
