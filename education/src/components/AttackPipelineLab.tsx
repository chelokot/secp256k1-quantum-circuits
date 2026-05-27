import { GitBranch } from 'lucide-react';

const stages = [
  {
    name: 'Public key',
    detail: 'Known secp256k1 point Q = dG',
    audit: 'fix the input problem',
  },
  {
    name: 'Quantum registers',
    detail: 'Superpose scalar/control choices',
    audit: 'hold many exponent choices',
  },
  {
    name: 'Controlled adds',
    detail: 'Repeated Q <- Q + lookup point',
    audit: 'create the hidden rhythm',
  },
  {
    name: 'Lookup/QROAM',
    detail: 'Fetch precomputed point chunks',
    audit: 'load constants without free wires',
  },
  {
    name: 'Point-add leaf',
    detail: 'Affine/projective arithmetic boundary',
    audit: 'execute reversible curve math',
  },
  {
    name: 'Phase estimation',
    detail: 'Inverse QFT exposes hidden rhythm',
    audit: 'turn phase into bits',
  },
  {
    name: 'Classical recovery',
    detail: 'Postprocess measurements into d',
    audit: 'recover the private scalar',
  },
];

export function AttackPipelineLab() {
  return (
    <section className="wide-panel" data-testid="attack-pipeline-lab">
      <div className="panel-heading">
        <GitBranch size={20} />
        <h3>Whole attack map</h3>
      </div>
      <p>
        Read left to right: the public key defines the hidden scalar, controlled
        curve additions write that scalar into phase, and phase estimation turns
        the phase into classical data.
      </p>
      <div className="pipeline">
        {stages.map((stage, index) => (
          <div className="pipeline-stage" key={stage.name}>
            <span>{index + 1}</span>
            <strong>{stage.name}</strong>
            <p>{stage.detail}</p>
            <em>{stage.audit}</em>
          </div>
        ))}
      </div>
      <div className="attack-readout-strip">
        <article>
          <span>What is secret?</span>
          <strong>d in Q = dG</strong>
          <p>The public key gives Q. The private key is the scalar d.</p>
        </article>
        <article>
          <span>What is expensive?</span>
          <strong>controlled point-add</strong>
          <p>Phase estimation repeats curve arithmetic many times.</p>
        </article>
        <article>
          <span>What does the repo audit?</span>
          <strong>the middle machinery</strong>
          <p>Lookup, point-add, netlist, liveness, and resource accounting.</p>
        </article>
      </div>
      <p>
        The repository optimizes the middle of this chain: lookup-fed secp256k1
        point addition, its primitive netlist, and the resource contract around
        live wires.
      </p>
    </section>
  );
}
