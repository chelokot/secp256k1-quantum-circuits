import { Binary, Calculator, KeyRound, Route } from 'lucide-react';

const proofSteps = [
  {
    title: 'Start object',
    label: 'public key',
    text: 'The circuit is given Q, a public curve point. The hidden answer is the private key number d. The shorthand Q = dG means d repeated additions of the public generator point G.',
    Icon: KeyRound,
  },
  {
    title: 'Quantum algorithm',
    label: 'period finding',
    text: 'Shor-style phase estimation turns repeated curve additions into measurement data that can recover d.',
    Icon: Route,
  },
  {
    title: 'Executable circuit',
    label: 'primitive rows',
    text: 'The repo must lower that algorithm into concrete reversible gate rows over named quantum wires.',
    Icon: Binary,
  },
  {
    title: 'Resource claim',
    label: 'counted peak',
    text: 'Only then can it claim the maximum live protected wires and the total expensive quantum work from the same circuit path.',
    Icon: Calculator,
  },
];

export function ProjectProofMap() {
  return (
    <section className="wide-panel proof-map" data-testid="project-proof-map">
      <div className="panel-heading">
        <Route size={20} />
        <h3>What has to be proved</h3>
      </div>
      <div className="proof-step-grid">
        {proofSteps.map(({ title, label, text, Icon }, index) => (
          <article key={title}>
            <div>
              <span>{index + 1}</span>
              <Icon size={18} />
            </div>
            <strong>{title}</strong>
            <em>{label}</em>
            <p>{text}</p>
          </article>
        ))}
      </div>
      <p>
        The audit chain starts here. Any later claim must connect back to these four
        objects; otherwise it is not evidence for the headline resource number.
      </p>
      <section className="claim-scope-grid" aria-label="Claim scope">
        <article>
          <strong>What the repo is not trying to prove</strong>
          <p>
            It is not proving that every possible implementation of secp256k1 discrete
            log has the same cost, and it is not proving hardware runtime on a specific
            machine.
          </p>
        </article>
        <article>
          <strong>What the repo must prove</strong>
          <p>
            It must prove one selected circuit family: same public-key problem, same
            executable boundary, same primitive rows, same liveness scan, same artifact
            digest.
          </p>
        </article>
      </section>
      <div className="proof-boundary-warning">
        <article>
          <strong>Weak evidence</strong>
          <p>
            A nice algorithm sketch, a passing toy test, or a proof that binds a
            different summary can all be useful, but none of them proves the resource
            number by itself.
          </p>
        </article>
        <article>
          <strong>Strong evidence</strong>
          <p>
            The same executable circuit path is semantically tested, lowered into
            primitive rows, counted from liveness, and serialized into checked
            artifacts.
          </p>
        </article>
      </div>
    </section>
  );
}
