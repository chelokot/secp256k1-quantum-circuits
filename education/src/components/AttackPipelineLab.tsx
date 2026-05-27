import { GitBranch } from 'lucide-react';

const stages = [
  {
    name: 'Public key',
    detail: 'Known secp256k1 point Q = dG',
  },
  {
    name: 'Quantum registers',
    detail: 'Superpose scalar/control choices',
  },
  {
    name: 'Controlled adds',
    detail: 'Repeated Q <- Q + lookup point',
  },
  {
    name: 'Lookup/QROAM',
    detail: 'Fetch precomputed point chunks',
  },
  {
    name: 'Point-add leaf',
    detail: 'Affine/projective arithmetic boundary',
  },
  {
    name: 'Phase estimation',
    detail: 'Inverse QFT exposes hidden rhythm',
  },
  {
    name: 'Classical recovery',
    detail: 'Postprocess measurements into d',
  },
];

export function AttackPipelineLab() {
  return (
    <section className="wide-panel" data-testid="attack-pipeline-lab">
      <div className="panel-heading">
        <GitBranch size={20} />
        <h3>Whole attack map</h3>
      </div>
      <div className="pipeline">
        {stages.map((stage, index) => (
          <div className="pipeline-stage" key={stage.name}>
            <span>{index + 1}</span>
            <strong>{stage.name}</strong>
            <p>{stage.detail}</p>
          </div>
        ))}
      </div>
      <p>
        The repository optimizes the middle of this chain: lookup-fed secp256k1
        point addition, its primitive netlist, and the resource contract around
        live wires.
      </p>
    </section>
  );
}
