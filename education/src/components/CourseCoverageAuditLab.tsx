import { useMemo, useState } from 'react';
import { ClipboardList } from 'lucide-react';

type CoverageRow = {
  id: string;
  requirement: string;
  evidence: string[];
  reviewerQuestion: string;
  status: 'covered' | 'covered-with-boundary';
};

const coverageRows: CoverageRow[] = [
  {
    id: 'stack',
    requirement: 'Standalone modern web subproject',
    evidence: ['Vite + React + TypeScript', 'D3 scales', 'lucide-react icons', 'Playwright browser tests'],
    reviewerQuestion: 'Can the course be developed, built, and tested as its own web project?',
    status: 'covered',
  },
  {
    id: 'zero',
    requirement: 'Start from zero quantum computing',
    evidence: ['Qubits as vectors', 'Gates and reversibility', 'State-vector simulator', 'Bloch playground'],
    reviewerQuestion: 'Can a programmer begin before knowing amplitudes, measurement, or gates?',
    status: 'covered',
  },
  {
    id: 'clifford',
    requirement: 'Explain Clifford, non-Clifford, logical, and physical qubits',
    evidence: ['Stabilizer vs magic wheel', 'Magic budget lab', 'Logical-to-physical bridge', 'Error-correction toy'],
    reviewerQuestion: 'Does the course separate algorithmic logical resources from hardware overhead?',
    status: 'covered',
  },
  {
    id: 'programming',
    requirement: 'Let the learner program quantum circuits',
    evidence: ['Circuit builder', 'Tiny netlist editor', 'Opcode lowering microscope', 'Mini resource engine'],
    reviewerQuestion: 'Can the learner write operations, see primitive rows, and debug liveness?',
    status: 'covered',
  },
  {
    id: 'attack',
    requirement: 'Teach the secp256k1 attack algorithm',
    evidence: ['ECDLP oracle toy', 'Phase estimation lab', 'Fourier lens', 'Phase kickback hidden-period lab'],
    reviewerQuestion: 'Does the course connect period finding to aG + bQ over secp256k1-style groups?',
    status: 'covered',
  },
  {
    id: 'circuit',
    requirement: 'Teach the whole circuit stack',
    evidence: ['Attack pipeline', 'Window scaffold', 'Circuit stack map', 'Whole-oracle resource composer'],
    reviewerQuestion: 'Can the learner see how phase bits become lookup-fed point-add leaves and resource totals?',
    status: 'covered',
  },
  {
    id: 'coordinates',
    requirement: 'Explain slots, affine/projective coordinates, lookup, and point-add boundaries',
    evidence: ['Coordinate model lab', 'Slot liveness', 'QROAM labs', 'Point-add boundary debugger'],
    reviewerQuestion: 'Does the course show why field slots, infinity cases, and lookup workspace are not free?',
    status: 'covered',
  },
  {
    id: 'resources',
    requirement: 'Teach netlists, liveness, owners, and resource accounting',
    evidence: ['Owner-capacity game', 'Schedule optimizer', 'Engine invariant lab', 'Scratch lifecycle lab'],
    reviewerQuestion: 'Does the course train the exact no-free-wire instincts needed by this repo?',
    status: 'covered',
  },
  {
    id: 'baselines',
    requirement: 'Present repo and Google baselines honestly',
    evidence: ['Baseline explorer', 'Baseline tradeoff landscape', 'Accepted-baseline gate', 'Current candidates and blockers page'],
    reviewerQuestion: 'Does it separate Google public lines, repo references, strict candidates, and accepted baselines?',
    status: 'covered',
  },
  {
    id: 'proof',
    requirement: 'Explain ZKP/proof boundary and current repo confidence',
    evidence: ['ZKP boundary lab', 'Artifact atlas', 'Claim audit drill', 'Confidence ladder'],
    reviewerQuestion: 'Does it prevent treating a valid proof wrapper as stronger than its bound statement?',
    status: 'covered',
  },
  {
    id: 'contributor',
    requirement: 'Become useful enough to help improve the repo',
    evidence: ['Zero-to-contributor path', 'Contributor mission board', 'Optimization mission', 'Current blocker list'],
    reviewerQuestion: 'Does the learner leave with concrete patch missions and evidence habits?',
    status: 'covered',
  },
  {
    id: 'boundary',
    requirement: 'State remaining boundaries instead of pretending the course proves the repo result',
    evidence: ['Current course boundary', 'Accepted baseline: none yet', 'Guard-corrected consequence', 'Proof release gate'],
    reviewerQuestion: 'Does the app keep education and resource-publication claims separate?',
    status: 'covered-with-boundary',
  },
];

export function CourseCoverageAuditLab({ lessonCount, quizCount }: { lessonCount: number; quizCount: number }) {
  const [showOnlyBoundaries, setShowOnlyBoundaries] = useState(false);
  const visibleRows = useMemo(() => {
    if (!showOnlyBoundaries) return coverageRows;
    return coverageRows.filter((row) => row.status === 'covered-with-boundary');
  }, [showOnlyBoundaries]);
  const coveredCount = coverageRows.filter((row) => row.status === 'covered').length;
  const boundaryCount = coverageRows.length - coveredCount;

  return (
    <section className="wide-panel" data-testid="course-coverage-audit-lab">
      <div className="panel-heading">
        <ClipboardList size={20} />
        <h3>Course coverage audit</h3>
      </div>
      <p>
        This dashboard turns the original education request into an inspectable map:
        every major requirement points to concrete lessons, labs, or tests inside this subproject.
      </p>

      <div className="coverage-summary">
        <div>
          <span>Lessons</span>
          <strong>{lessonCount}</strong>
          <em>ordered from zero to repo baselines</em>
        </div>
        <div>
          <span>Quiz questions</span>
          <strong>{quizCount}</strong>
          <em>review checks across the whole course</em>
        </div>
        <div>
          <span>Requirements mapped</span>
          <strong>{coverageRows.length}/{coverageRows.length}</strong>
          <em>{coveredCount} covered, {boundaryCount} boundary-aware</em>
        </div>
        <label>
          <input
            aria-label="Show only boundary-aware coverage rows"
            checked={showOnlyBoundaries}
            onChange={(event) => setShowOnlyBoundaries(event.currentTarget.checked)}
            type="checkbox"
          />
          Show boundary-aware rows
        </label>
      </div>

      <div className="coverage-grid">
        {visibleRows.map((row) => (
          <article className={row.status === 'covered' ? 'coverage-card covered' : 'coverage-card boundary'} key={row.id}>
            <header>
              <strong>{row.requirement}</strong>
              <span>{row.status.replaceAll('-', ' ')}</span>
            </header>
            <p>{row.reviewerQuestion}</p>
            <div className="coverage-evidence">
              {row.evidence.map((item) => (
                <span key={item}>{item}</span>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
