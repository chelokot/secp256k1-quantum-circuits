import { useMemo, useState } from 'react';
import { GitCompareArrows } from 'lucide-react';

type BoundaryCategoryName =
  | 'random'
  | 'doubling'
  | 'inverse'
  | 'accumulator_infinity'
  | 'lookup_infinity';

type BoundaryCategory = {
  total: number;
  pass: number;
};

type BoundaryArtifact = {
  total: number;
  pass: number;
  categories: Record<BoundaryCategoryName, BoundaryCategory>;
};

type ProjectData = {
  pointAddBoundary: {
    lookupFedLeaf: BoundaryArtifact;
    streamedLookupTailLeaf: BoundaryArtifact;
  };
};

const caseOrder: BoundaryCategoryName[] = [
  'random',
  'doubling',
  'inverse',
  'accumulator_infinity',
  'lookup_infinity',
];

const caseCopy: Record<BoundaryCategoryName, { label: string; risk: string; fix: string }> = {
  random: {
    label: 'random ordinary add',
    risk: 'The easy path checks generic addition, but it misses branch boundaries.',
    fix: 'Keep it, but never treat it as the whole semantic proof.',
  },
  doubling: {
    label: 'doubling',
    risk: 'P == Q changes the slope formula. A generic add path can divide by the wrong difference.',
    fix: 'Route the doubling branch into the same executable leaf contract.',
  },
  inverse: {
    label: 'inverse pair',
    risk: 'P == -Q should produce the point at infinity, not a malformed affine coordinate.',
    fix: 'Bind the inverse branch and infinity encoding to the tested point-add boundary.',
  },
  accumulator_infinity: {
    label: 'accumulator infinity',
    risk: 'The running accumulator may start at infinity, so the leaf must copy in the lookup point.',
    fix: 'Test the accumulator-infinity branch against the same counted interface.',
  },
  lookup_infinity: {
    label: 'lookup infinity',
    risk: 'A lookup entry may be the no-op identity. The accumulator should remain unchanged.',
    fix: 'Bind lookup-infinity no-op semantics before trusting any lookup-fed resource result.',
  },
};

const readable = (name: BoundaryCategoryName) => caseCopy[name].label;

export function PointAddBoundaryDebugger({ projectData }: { projectData: ProjectData }) {
  const artifact = projectData.pointAddBoundary.streamedLookupTailLeaf;
  const [selectedCase, setSelectedCase] = useState<BoundaryCategoryName>('random');
  const [randomOnly, setRandomOnly] = useState(false);
  const [doublingGuard, setDoublingGuard] = useState(true);
  const [inverseGuard, setInverseGuard] = useState(true);
  const [accumulatorInfinityGuard, setAccumulatorInfinityGuard] = useState(true);
  const [lookupInfinityGuard, setLookupInfinityGuard] = useState(true);

  const simulatedCoverage = useMemo(() => {
    const enabled: Record<BoundaryCategoryName, boolean> = {
      random: true,
      doubling: !randomOnly && doublingGuard,
      inverse: !randomOnly && inverseGuard,
      accumulator_infinity: !randomOnly && accumulatorInfinityGuard,
      lookup_infinity: !randomOnly && lookupInfinityGuard,
    };

    const covered = caseOrder.filter((name) => enabled[name]);
    const missing = caseOrder.filter((name) => !enabled[name]);
    const passCount = covered.reduce((total, name) => total + artifact.categories[name].pass, 0);

    return {
      covered,
      missing,
      passCount,
      pass: missing.length === 0 && artifact.pass === artifact.total,
    };
  }, [accumulatorInfinityGuard, artifact, doublingGuard, inverseGuard, lookupInfinityGuard, randomOnly]);

  const selected = caseCopy[selectedCase];
  const oldArtifact = projectData.pointAddBoundary.lookupFedLeaf;
  const artifactsAgree = oldArtifact.total === artifact.total && oldArtifact.pass === artifact.pass;

  return (
    <section className="wide-panel" data-testid="point-add-boundary-debugger">
      <div className="panel-heading">
        <GitCompareArrows size={20} />
        <h3>Point-add boundary debugger</h3>
      </div>
      <p>
        Random point-add tests are necessary but not enough. The checked streamed leaf passes every
        named boundary family against the same lookup-fed contract: {artifact.pass}/{artifact.total}.
      </p>

      <div className="boundary-grid">
        <article>
          <h4>Checked equivalence artifact</h4>
          <div className="boundary-case-list">
            {caseOrder.map((name) => {
              const category = artifact.categories[name];
              return (
                <button
                  className={selectedCase === name ? 'selected' : ''}
                  key={name}
                  onClick={() => setSelectedCase(name)}
                  type="button"
                >
                  <span>{readable(name)}</span>
                  <strong>{category.pass}/{category.total}</strong>
                </button>
              );
            })}
          </div>
          <p className={artifactsAgree ? 'audit-pass' : 'audit-fail'}>
            Old lookup-fed and streamed-tail summaries: {artifactsAgree ? 'agree' : 'mismatch'}
          </p>
        </article>

        <article>
          <h4>Selected edge case</h4>
          <dl className="metric-pair">
            <div>
              <dt>Family</dt>
              <dd>{selected.label}</dd>
            </div>
            <div>
              <dt>Artifact result</dt>
              <dd>{artifact.categories[selectedCase].pass}/{artifact.categories[selectedCase].total}</dd>
            </div>
          </dl>
          <p><strong>Failure mode:</strong> {selected.risk}</p>
          <p><strong>Required contract:</strong> {selected.fix}</p>
        </article>
      </div>

      <div className="boundary-simulator">
        <h4>Red-team simulator</h4>
        <div className="boundary-controls">
          <label>
            <input
              aria-label="Test only random point-add cases"
              checked={randomOnly}
              onChange={(event) => setRandomOnly(event.currentTarget.checked)}
              type="checkbox"
            />
            <span>test only random cases</span>
          </label>
          <label>
            <input
              aria-label="Enable doubling branch"
              checked={doublingGuard}
              disabled={randomOnly}
              onChange={(event) => setDoublingGuard(event.currentTarget.checked)}
              type="checkbox"
            />
            <span>doubling branch enabled</span>
          </label>
          <label>
            <input
              aria-label="Enable inverse infinity branch"
              checked={inverseGuard}
              disabled={randomOnly}
              onChange={(event) => setInverseGuard(event.currentTarget.checked)}
              type="checkbox"
            />
            <span>inverse-infinity branch enabled</span>
          </label>
          <label>
            <input
              aria-label="Enable accumulator infinity branch"
              checked={accumulatorInfinityGuard}
              disabled={randomOnly}
              onChange={(event) => setAccumulatorInfinityGuard(event.currentTarget.checked)}
              type="checkbox"
            />
            <span>accumulator-infinity branch enabled</span>
          </label>
          <label>
            <input
              aria-label="Enable lookup infinity branch"
              checked={lookupInfinityGuard}
              disabled={randomOnly}
              onChange={(event) => setLookupInfinityGuard(event.currentTarget.checked)}
              type="checkbox"
            />
            <span>lookup-infinity no-op enabled</span>
          </label>
        </div>
        <p className={simulatedCoverage.pass ? 'audit-pass' : 'audit-fail'}>
          Boundary audit: {simulatedCoverage.pass ? 'pass' : 'fail'}
        </p>
        <p>
          Covered checked cases: {simulatedCoverage.passCount}/{artifact.total}. Missing:
          {' '}
          {simulatedCoverage.missing.length === 0
            ? 'none'
            : simulatedCoverage.missing.map(readable).join(', ')}
        </p>
      </div>
    </section>
  );
}
