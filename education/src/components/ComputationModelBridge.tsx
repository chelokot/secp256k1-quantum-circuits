import { Binary, Cpu, Eye, GitCompareArrows, Sigma } from 'lucide-react';
import { MathTex } from './MathText';

const comparisonRows = [
  {
    label: 'Memory',
    classical: 'one bit string, such as 0101',
    quantum: 'amplitudes over many labels',
  },
  {
    label: 'Operation',
    classical: 'logic, arithmetic, branches, overwrites',
    quantum: 'linear reversible gates before measurement',
  },
  {
    label: 'Math object',
    classical: 'discrete state update',
    quantum: 'vector transformation',
  },
  {
    label: 'Readout',
    classical: 'read stored bits',
    quantum: 'sample a discrete result from amplitudes',
  },
];

export function ComputationModelBridge() {
  return (
    <section className="wide-panel computation-bridge" data-testid="computation-model-bridge">
      <div className="panel-heading">
        <Cpu size={20} />
        <h3>Computer model bridge</h3>
      </div>
      <p>
        The project is not mystical: it is still about a program. The useful first
        comparison is ordinary computation versus quantum circuit computation.
      </p>

      <div className="computer-flow-grid">
        <article>
          <Binary size={18} />
          <strong>Ordinary computer</strong>
          <MathTex tex="\text{bits}\rightarrow\text{instructions}\rightarrow\text{bits}" />
          <p>The state is one definite bit string, and each instruction changes that stored string.</p>
        </article>
        <article>
          <GitCompareArrows size={18} />
          <strong>Quantum circuit</strong>
          <MathTex tex="\text{amplitudes}\rightarrow\text{gates}\rightarrow\text{amplitudes}" />
          <p>The state is an amplitude vector, and each gate transforms the whole vector reversibly.</p>
        </article>
        <article>
          <Eye size={18} />
          <strong>Measurement</strong>
          <MathTex tex="\sum_x a_x|x\rangle\rightarrow\text{one sampled }x" />
          <p>The continuous amplitude calculation ends with an ordinary discrete bit-string outcome.</p>
        </article>
      </div>

      <div className="comparison-table" role="table" aria-label="Classical and quantum computation comparison">
        <div role="row">
          <strong role="columnheader">Aspect</strong>
          <strong role="columnheader">Classical</strong>
          <strong role="columnheader">Quantum circuit</strong>
        </div>
        {comparisonRows.map((row) => (
          <div role="row" key={row.label}>
            <span role="cell">{row.label}</span>
            <span role="cell">{row.classical}</span>
            <span role="cell">{row.quantum}</span>
          </div>
        ))}
      </div>

      <div className="bridge-takeaway">
        <Sigma size={18} />
        <p>
          So the repo’s job is to materialize the mathematical quantum program into
          concrete gates and wires, then count those wires and expensive gates from
          that same executable path.
        </p>
      </div>
    </section>
  );
}
