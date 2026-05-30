import { useMemo, useState } from 'react';
import { Files } from 'lucide-react';

type GeneratedFrom = Record<string, string>;

type ProjectData = {
  generatedFrom: GeneratedFrom;
  acceptedBaselineGate: {
    status: string;
    rows: Array<{
      name: string;
      pass: boolean;
      evidence: string;
      required_to_close: string;
    }>;
  };
  pointAddBoundary: {
    streamedLookupTailLeaf: {
      total: number;
      pass: number;
    };
  };
  proofPublication: {
    publicationReady: boolean;
    staleSystems: string[];
  };
};

type AtlasEntry = {
  id: string;
  title: string;
  sourceKey: string;
  question: string;
  proves: string;
  doesNotProve: string;
  liveSignal: (projectData: ProjectData) => string;
};

const readable = (value: string) => value.replaceAll('_', ' ');

const atlasEntries: AtlasEntry[] = [
  {
    id: 'baseline-status',
    title: 'Baseline promotion authority',
    sourceKey: 'baselineStatus',
    question: 'May any resource number be called the accepted physical baseline?',
    proves: 'Current claim status, guard-corrected consequence, active blockers, and the explicit accepted-baseline gate.',
    doesNotProve: 'A lower qubit count, proof freshness, or a Clifford-complete primitive stream by itself.',
    liveSignal: (projectData) => `Gate ${readable(projectData.acceptedBaselineGate.status)} with ${projectData.acceptedBaselineGate.rows.length} required rows.`,
  },
  {
    id: 'strict-headline',
    title: 'Strict replayed-tail candidate',
    sourceKey: 'strictHeadline',
    question: 'Which candidate resource row is selected by the strict replayed-tail layer?',
    proves: 'The seven-slot candidate formula and standard-QROAM reusable-chunk non-Clifford reconstruction.',
    doesNotProve: 'That the candidate is accepted as the final physical baseline.',
    liveSignal: () => 'Candidate layer only; promotion is decided by current_baseline_status.json.',
  },
  {
    id: 'engine-completion',
    title: 'Engine completion audit',
    sourceKey: 'engineCompletion',
    question: 'Which macro boundary still prevents a Clifford-complete engine claim?',
    proves: 'Covered boundaries and the remaining modular arithmetic Clifford-expansion blocker.',
    doesNotProve: 'That all synthetic arithmetic scratch has been replaced by concrete cleaned wires.',
    liveSignal: () => 'Clifford-complete goal is false in the current generated data.',
  },
  {
    id: 'point-add-equivalence',
    title: 'Point-add equivalence',
    sourceKey: 'streamedLookupTailLeafEquivalence',
    question: 'Does the counted point-add boundary cover random and edge-case semantics?',
    proves: 'The checked streamed lookup tail leaf passes random, doubling, inverse, accumulator-infinity, and lookup-infinity cases.',
    doesNotProve: 'The full modular arithmetic primitive lowering below the leaf.',
    liveSignal: (projectData) => `${projectData.pointAddBoundary.streamedLookupTailLeaf.pass}/${projectData.pointAddBoundary.streamedLookupTailLeaf.total} checked cases pass.`,
  },
  {
    id: 'zero-lift-guard',
    title: 'Zero-lift guard capacity',
    sourceKey: 'zeroLiftGuard',
    question: 'Why is the guard-corrected 2,222q consequence not promoted?',
    proves: 'The one-bit guard owner does not cover the 255-bit standard clean-ladder predicate workspace.',
    doesNotProve: 'That no alias/no-ancilla construction exists; it only records that none is promoted.',
    liveSignal: (projectData) => {
      const row = projectData.acceptedBaselineGate.rows.find((item) => item.name === 'guard_corrected_no_alias_capacity_promoted_into_liveness');
      return row ? `Gate row ${readable(row.name)}: ${row.pass ? 'pass' : 'blocked'}.` : 'Guard promotion row is absent.';
    },
  },
  {
    id: 'source-uncompute',
    title: 'Accumulator source-uncompute',
    sourceKey: 'modularAccumulatorSourceUncompute',
    question: 'Which scratch cleanup is proven and which cleanup is still not promoted?',
    proves: 'Partial-product source-uncompute rows and the remaining missing source controls for guard cleanup.',
    doesNotProve: 'That consume/fold/source-uncompute is already the global public primitive stream.',
    liveSignal: (projectData) => {
      const row = projectData.acceptedBaselineGate.rows.find((item) => item.name === 'modular_accumulator_source_uncompute_promoted');
      return row ? `Gate row ${readable(row.name)}: ${row.pass ? 'pass' : 'blocked'}.` : 'Source-uncompute promotion row is absent.';
    },
  },
  {
    id: 'proof-publication',
    title: 'Proof publication status',
    sourceKey: 'proofPublicationStatus',
    question: 'Are checked proof fixtures current enough to publish?',
    proves: 'Freshness status for core relation, compressed SP1 receipt, Groth16 wrapper, and public-headline publication gates.',
    doesNotProve: 'A physical baseline if the resource contract underneath is still blocked.',
    liveSignal: (projectData) => `Publication ready: ${projectData.proofPublication.publicationReady ? 'yes' : 'no'}; stale systems: ${projectData.proofPublication.staleSystems.join(', ')}.`,
  },
  {
    id: 'hybrid-search',
    title: 'Optimization search map',
    sourceKey: 'hybridBridgeSearch',
    question: 'Which low-slot ideas are candidates, hypotheses, or blocked tradeoffs?',
    proves: 'The current search landscape and why a numerically attractive row is not automatically a result.',
    doesNotProve: 'That any candidate row is promoted into the accepted baseline.',
    liveSignal: () => 'Use this for optimization triage, not for publication claims.',
  },
];

export function ArtifactAtlasLab({ projectData }: { projectData: ProjectData }) {
  const [selectedId, setSelectedId] = useState('baseline-status');
  const [checkedItems, setCheckedItems] = useState<Set<string>>(() => new Set());
  const selectedEntry = atlasEntries.find((entry) => entry.id === selectedId) ?? atlasEntries[0];
  const path = projectData.generatedFrom[selectedEntry.sourceKey];
  const checklist = useMemo(() => ['Locate artifact path', 'Read status and scope', 'State what it does not prove'], []);
  const auditPass = checklist.every((item) => checkedItems.has(item));

  return (
    <section className="wide-panel" data-testid="artifact-atlas-lab">
      <div className="panel-heading">
        <Files size={20} />
        <h3>Artifact atlas</h3>
      </div>
      <p>
        Use this as the repo-reading map: each artifact answers one audit question and leaves
        other claims unproven until another artifact closes them.
      </p>

      <div className="artifact-atlas-grid">
        <article className="artifact-list">
          {atlasEntries.map((entry) => (
            <button
              className={entry.id === selectedEntry.id ? 'selected' : ''}
              key={entry.id}
              onClick={() => {
                setSelectedId(entry.id);
                setCheckedItems(new Set());
              }}
              type="button"
            >
              <strong>{entry.title}</strong>
              <span>{entry.question}</span>
            </button>
          ))}
        </article>

        <article className="artifact-detail">
          <h4>{selectedEntry.title}</h4>
          <dl className="artifact-fact-list">
            <div>
              <dt>Path</dt>
              <dd className="artifact-path">{path}</dd>
            </div>
            <div>
              <dt>Question</dt>
              <dd>{selectedEntry.question}</dd>
            </div>
            <div>
              <dt>What this proves</dt>
              <dd>{selectedEntry.proves}</dd>
            </div>
            <div>
              <dt>What this does not prove</dt>
              <dd>{selectedEntry.doesNotProve}</dd>
            </div>
            <div>
              <dt>Live signal</dt>
              <dd>{selectedEntry.liveSignal(projectData)}</dd>
            </div>
          </dl>

          <div className="artifact-checklist">
            {checklist.map((item) => (
              <label key={item}>
                <input
                  aria-label={item}
                  checked={checkedItems.has(item)}
                  onChange={(event) => {
                    const checked = event.currentTarget.checked;
                    setCheckedItems((current) => {
                      const next = new Set(current);
                      if (checked) next.add(item);
                      else next.delete(item);
                      return next;
                    });
                  }}
                  type="checkbox"
                />
                <span>{item}</span>
              </label>
            ))}
          </div>
          <p className={auditPass ? 'audit-pass' : 'audit-fail'}>
            Artifact audit: {auditPass ? 'pass' : 'fail'}
          </p>
        </article>
      </div>
    </section>
  );
}
