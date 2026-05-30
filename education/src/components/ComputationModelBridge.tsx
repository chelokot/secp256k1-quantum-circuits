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

      <section className="program-skeleton-ledger" aria-label="Shared program skeleton">
        <h4>Same skeleton, different state object</h4>
        <div role="table">
          <div role="row">
            <strong role="columnheader">Program moment</strong>
            <strong role="columnheader">Ordinary computer</strong>
            <strong role="columnheader">Quantum circuit</strong>
          </div>
          <div role="row">
            <span role="cell">State before a step</span>
            <span role="cell"><MathTex tex="0101" /> is the stored value.</span>
            <span role="cell"><MathTex tex="\sum_x \alpha_x|x\rangle" /> is the stored amplitude vector.</span>
          </div>
          <div role="row">
            <span role="cell">Operation</span>
            <span role="cell">An instruction can branch, overwrite, or erase a temporary value.</span>
            <span role="cell">A gate must be a reversible linear transformation before measurement.</span>
          </div>
          <div role="row">
            <span role="cell">Scratch space</span>
            <span role="cell">A local temporary can disappear after the instruction sequence.</span>
            <span role="cell">A scratch wire remains part of the state until output or proven uncompute.</span>
          </div>
          <div role="row">
            <span role="cell">Readout</span>
            <span role="cell">Read the current bit string.</span>
            <span role="cell">Sample one label with probability <MathTex tex="|\alpha_x|^2" />.</span>
          </div>
        </div>
      </section>

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
