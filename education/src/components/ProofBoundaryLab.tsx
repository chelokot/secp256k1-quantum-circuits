import { useMemo, useState } from 'react';
import { FileCheck2 } from 'lucide-react';

type ProofSystem = {
  system: string;
  current: boolean;
  publicValuesMatchCurrent: boolean;
  resourceDigestMatchesInput: boolean;
  proofFileExists: boolean | null;
  verifierKeyFileExists: boolean | null;
  staleReasons: string[];
};

type ProofBlocker = {
  system: string;
  inputBindingStatus: string;
  staleReasons: string[];
  requiredToClose: string | null;
};

type ProjectData = {
  generatedFrom: {
    proofPublicationStatus: string;
    proofCorpusProfiles: string;
    publicHeadlineResult: string;
  };
  proofPublication: {
    publicationReady: boolean;
    allCurrent: boolean;
    staleSystems: string[];
    systems: ProofSystem[];
    blockers: ProofBlocker[];
    gateCommands: Array<{ name: string; phase: string }>;
  };
  proofCorpusProfiles: {
    publicCaseCount: number;
    releaseCaseCount: number;
    publicReleaseGrade: boolean;
    releaseGrade: boolean;
  };
};

const statusText = (value: boolean | null) => {
  if (value === null) return 'n/a';
  return value ? 'yes' : 'no';
};

const readable = (value: string) => value.replaceAll('_', ' ');

const proofSystemLabel = (system: string) => {
  if (system === 'core') return 'Core relation';
  if (system === 'compressed') return 'Compressed SP1 receipt';
  if (system === 'groth16') return 'Groth16 wrapper';
  return readable(system);
};

export function ProofBoundaryLab({ projectData }: { projectData: ProjectData }) {
  const [fixturesCurrent, setFixturesCurrent] = useState(projectData.proofPublication.allCurrent);
  const [macroBoundaryClosed, setMacroBoundaryClosed] = useState(projectData.proofPublication.publicationReady);
  const [verifiedReleaseProofs, setVerifiedReleaseProofs] = useState(projectData.proofPublication.publicationReady);
  const [selectedSystemName, setSelectedSystemName] = useState('groth16');
  const selectedSystem = projectData.proofPublication.systems.find((system) => system.system === selectedSystemName)
    ?? projectData.proofPublication.systems[0];
  const selectedBlocker = projectData.proofPublication.blockers.find((blocker) => blocker.system === selectedSystem.system);

  const simulatedStatus = useMemo(() => {
    const open: string[] = [];
    if (!fixturesCurrent) open.push('proof fixtures do not bind current input');
    if (!macroBoundaryClosed) open.push('remaining macro boundary is not flattened');
    if (!verifiedReleaseProofs) open.push('compressed SP1 receipt and Groth16 wrapper verification not rerun for release');
    return { open, pass: open.length === 0 };
  }, [fixturesCurrent, macroBoundaryClosed, verifiedReleaseProofs]);

  return (
    <section className="wide-panel" data-testid="proof-boundary-lab">
      <div className="panel-heading">
        <FileCheck2 size={20} />
        <h3>Zero-knowledge proof boundary lab</h3>
      </div>
      <p>
        A zero-knowledge proof verifier checks one encoded statement. Here the important
        question is not only “did verification pass?”, but “which input, corpus, public
        values, and resource digest did that proof bind?”
      </p>
      <div className="proof-grid">
        <article>
          <h4>Checked proof status</h4>
          <dl className="metric-pair">
            <div>
              <dt>Public corpus</dt>
              <dd>{projectData.proofCorpusProfiles.publicCaseCount} cases</dd>
            </div>
            <div>
              <dt>Release target</dt>
              <dd>{projectData.proofCorpusProfiles.releaseCaseCount} cases</dd>
            </div>
          </dl>
          <p className={projectData.proofPublication.publicationReady ? 'audit-pass' : 'audit-fail'}>
            Checked artifact status: {projectData.proofPublication.publicationReady ? 'publication ready' : 'not publication ready'}
          </p>
          <p>
            Current public proof corpus is {projectData.proofCorpusProfiles.publicReleaseGrade ? 'release-grade' : 'smoke-only'}.
            The Google-comparable target is {projectData.proofCorpusProfiles.releaseGrade ? 'release-grade' : 'not release-grade'}.
          </p>
        </article>

        <article>
          <h4>Proof systems</h4>
          <div className="proof-system-list">
            {projectData.proofPublication.systems.map((system) => (
              <div key={system.system}>
                <strong>{proofSystemLabel(system.system)}</strong>
                <span>current {statusText(system.current)}</span>
                <span>public values {statusText(system.publicValuesMatchCurrent)}</span>
                <span>resource digest {statusText(system.resourceDigestMatchesInput)}</span>
                <span>proof file {statusText(system.proofFileExists)}</span>
              </div>
            ))}
          </div>
        </article>
      </div>

      <section className="proof-binding-inspector" aria-label="Proof-system binding inspector">
        <div>
          <h4>Proof-system binding inspector</h4>
          <p>
            Pick a proof system and read the same chain a reviewer follows: input metadata,
            public values, resource digest, proof bytes, verifier key, and remaining blocker.
          </p>
        </div>
        <label>
          <span>Proof system</span>
          <select
            aria-label="Proof system binding inspector"
            value={selectedSystem.system}
            onChange={(event) => setSelectedSystemName(event.currentTarget.value)}
          >
            {projectData.proofPublication.systems.map((system) => (
              <option key={system.system} value={system.system}>{proofSystemLabel(system.system)}</option>
            ))}
          </select>
        </label>
        <div className="proof-binding-grid">
          <article className={selectedSystem.current ? 'pass' : 'fail'}>
            <span>System status</span>
            <strong>{proofSystemLabel(selectedSystem.system)} is {selectedSystem.current ? 'current' : 'stale'}</strong>
          </article>
          <article className={selectedBlocker ? 'fail' : 'pass'}>
            <span>Input metadata</span>
            <strong>{selectedBlocker ? readable(selectedBlocker.inputBindingStatus) : 'binds current input metadata'}</strong>
          </article>
          <article className={selectedSystem.publicValuesMatchCurrent ? 'pass' : 'fail'}>
            <span>Public values</span>
            <strong>{selectedSystem.publicValuesMatchCurrent ? 'match current checked values' : 'do not match current checked values'}</strong>
          </article>
          <article className={selectedSystem.resourceDigestMatchesInput ? 'pass' : 'fail'}>
            <span>Resource digest</span>
            <strong>{selectedSystem.resourceDigestMatchesInput ? 'matches checked input' : 'does not match current input'}</strong>
          </article>
          <article className={selectedSystem.proofFileExists ? 'pass' : 'fail'}>
            <span>Proof bundle</span>
            <strong>{statusText(selectedSystem.proofFileExists)}</strong>
          </article>
          <article className={selectedSystem.verifierKeyFileExists === false ? 'fail' : 'pass'}>
            <span>Verifier key</span>
            <strong>{statusText(selectedSystem.verifierKeyFileExists)}</strong>
          </article>
        </div>
        <div className={selectedSystem.current ? 'proof-binding-pass' : 'proof-binding-fail'}>
          <strong>Binding verdict: {selectedSystem.current ? 'current' : 'blocked'}</strong>
          <p>
            {selectedBlocker?.requiredToClose
              ?? (selectedSystem.staleReasons.length === 0 ? 'No stale reasons recorded for this system.' : selectedSystem.staleReasons.map(readable).join(', '))}
          </p>
        </div>
      </section>

      <div className="proof-receipt-grid">
        <article>
          <span>Verifier checks</span>
          <strong>proof bytes match public values</strong>
          <p>
            A valid compressed SP1 receipt or Groth16 wrapper verifier result says the proof bundle
            satisfies the encoded statement and public values for that proof format.
          </p>
        </article>
        <article>
          <span>Freshness check adds</span>
          <strong>current input and resource digest</strong>
          <p>
            The publication artifact must show that those public values still bind
            the checked input JSON and current resource certificate.
          </p>
        </article>
        <article>
          <span>Still outside the verifier</span>
          <strong>claim scope and corpus strength</strong>
          <p>
            The verifier does not know whether a README sentence says too much, whether
            the corpus is release-grade, or whether a macro boundary remains open.
          </p>
        </article>
      </div>

      <div className="proof-artifact-receipt">
        <article>
          <span>Publication status artifact</span>
          <strong>{projectData.generatedFrom.proofPublicationStatus}</strong>
        </article>
        <article>
          <span>Corpus profile artifact</span>
          <strong>{projectData.generatedFrom.proofCorpusProfiles}</strong>
        </article>
        <article>
          <span>Headline gate artifact</span>
          <strong>{projectData.generatedFrom.publicHeadlineResult}</strong>
        </article>
      </div>

      <div className="publication-workflow-strip">
        <article>
          <span>1. Statement</span>
          <strong>what does the proof bind?</strong>
          <p>Check selected family, resource digest, case corpus, and public values before trusting the verifier.</p>
        </article>
        <article>
          <span>2. Freshness</span>
          <strong>are artifacts current?</strong>
          <p>Compressed SP1 receipt and Groth16 wrapper proof bundles must match the checked input and verifier key.</p>
        </article>
        <article>
          <span>3. Scope</span>
          <strong>is the claim physical?</strong>
          <p>A valid proof is not enough if the remaining macro boundary is weaker than the advertised circuit claim.</p>
        </article>
      </div>

      <div className="proof-simulator">
        <h4>Promotion simulator</h4>
        <label>
          <input
            aria-label="Refresh proof fixtures against current input"
            checked={fixturesCurrent}
            onChange={(event) => setFixturesCurrent(event.currentTarget.checked)}
            type="checkbox"
          />
          <span>proof fixtures bind current input and resource digest</span>
        </label>
        <label>
          <input
            aria-label="Close physical macro boundary"
            checked={macroBoundaryClosed}
            onChange={(event) => setMacroBoundaryClosed(event.currentTarget.checked)}
            type="checkbox"
          />
          <span>remaining physical macro boundary is flattened</span>
        </label>
        <label>
          <input
            aria-label="Verify compressed SP1 receipt and Groth16 wrapper proofs"
            checked={verifiedReleaseProofs}
            onChange={(event) => setVerifiedReleaseProofs(event.currentTarget.checked)}
            type="checkbox"
          />
          <span>compressed SP1 receipt and Groth16 wrapper verification passed for the checked artifacts</span>
        </label>
        <p className={simulatedStatus.pass ? 'audit-pass' : 'audit-fail'}>
          Proof release gate: {simulatedStatus.pass ? 'pass' : 'blocked'}
        </p>
        <p>
          Open proof issues: {simulatedStatus.open.length === 0 ? 'none' : simulatedStatus.open.join(', ')}
        </p>
      </div>

      <div className="proof-command-ledger">
        <h4>Release gate commands tracked by the artifact</h4>
        {projectData.proofPublication.gateCommands.map((command) => (
          <article key={command.name}>
            <span>{readable(command.phase)}</span>
            <strong>{command.name}</strong>
          </article>
        ))}
      </div>

      <div className="proof-blockers">
        {projectData.proofPublication.blockers.map((blocker) => (
          <article key={blocker.system}>
            <strong>{proofSystemLabel(blocker.system)}</strong>
            <span>{readable(blocker.inputBindingStatus)}</span>
            <p>{blocker.staleReasons.map(readable).join(', ')}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
