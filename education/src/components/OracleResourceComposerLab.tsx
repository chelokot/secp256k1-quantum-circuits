import { useMemo, useState } from 'react';
import { Sigma } from 'lucide-react';

type ProjectData = {
  currentStrictCandidate: {
    non_clifford: number;
    logical_qubits: number;
    status: string;
  };
  guardCorrectedNoAliasCandidate: {
    logical_qubits: number;
    status: string;
  };
  strictFormula: {
    tail_field_slots: number;
    field_bits: number;
    tail_field_qubits: number;
    lookup_workspace_qubits: number;
    control_qubits: number;
    fused_output_guard_qubits: number;
    phase_qubits: number;
    reconstructed_total: number;
  };
  strictNonCliffordFormula: {
    base_non_clifford_without_streamed_qroam: number;
    qroam_chunk_streams: number;
    per_chunk_stream_non_clifford: number;
    qroam_chunk_non_clifford: number;
    reconstructed_total: number;
  };
  attackScaffold: {
    compilerRaw32: {
      rawWindowCount: number;
      phaseRegisterBitsTotal: number;
      leafCallCount: number;
    };
  };
};

const formatInt = (value: number) => new Intl.NumberFormat('en-US').format(value);

export function OracleResourceComposerLab({ projectData }: { projectData: ProjectData }) {
  const maxLeafCalls = projectData.attackScaffold.compilerRaw32.leafCallCount;
  const [leafCalls, setLeafCalls] = useState(maxLeafCalls);
  const [includeBase, setIncludeBase] = useState(true);
  const [includeQroam, setIncludeQroam] = useState(true);
  const [sumQubitsPerLeaf, setSumQubitsPerLeaf] = useState(false);

  const qroamStreamsPerLeaf = projectData.strictNonCliffordFormula.qroam_chunk_streams / maxLeafCalls;
  const selectedQroamStreams = leafCalls * qroamStreamsPerLeaf;
  const selectedQroamNonClifford = selectedQroamStreams * projectData.strictNonCliffordFormula.per_chunk_stream_non_clifford;
  const composedNonClifford =
    (includeBase ? projectData.strictNonCliffordFormula.base_non_clifford_without_streamed_qroam : 0)
    + (includeQroam ? selectedQroamNonClifford : 0);

  const strictQubitFormula = projectData.strictFormula;
  const correctPeakQubits = strictQubitFormula.reconstructed_total;
  const mistakenSerialQubits = correctPeakQubits * leafCalls;
  const displayedQubits = sumQubitsPerLeaf ? mistakenSerialQubits : correctPeakQubits;

  const compositionAuditPass = useMemo(() => {
    return (
      leafCalls === maxLeafCalls
      && includeBase
      && includeQroam
      && !sumQubitsPerLeaf
      && composedNonClifford === projectData.currentStrictCandidate.non_clifford
      && correctPeakQubits === projectData.currentStrictCandidate.logical_qubits
    );
  }, [
    composedNonClifford,
    correctPeakQubits,
    includeBase,
    includeQroam,
    leafCalls,
    maxLeafCalls,
    projectData.currentStrictCandidate.logical_qubits,
    projectData.currentStrictCandidate.non_clifford,
    sumQubitsPerLeaf,
  ]);

  const qubitAuditPass = !sumQubitsPerLeaf && displayedQubits === correctPeakQubits;

  return (
    <section className="wide-panel" data-testid="oracle-resource-composer-lab">
      <div className="panel-heading">
        <Sigma size={20} />
        <h3>Whole-oracle resource composer</h3>
      </div>
      <p>
        The raw compiler oracle has {maxLeafCalls} point-add leaves after the direct seed and
        {projectData.attackScaffold.compilerRaw32.phaseRegisterBitsTotal} phase bits. Gate work
        accumulates across those calls, while logical qubits are the peak workspace reused by the
        schedule.
      </p>

      <div className="composer-controls">
        <label className="slider-label">
          <span>Point-add leaf calls: {leafCalls}/{maxLeafCalls}</span>
          <input
            aria-label="Point-add leaf calls"
            max={maxLeafCalls}
            min="0"
            onChange={(event) => setLeafCalls(Number(event.currentTarget.value))}
            type="range"
            value={leafCalls}
          />
        </label>
        <label>
          <input
            aria-label="Include strict non-QROAM base"
            checked={includeBase}
            onChange={(event) => setIncludeBase(event.currentTarget.checked)}
            type="checkbox"
          />
          Include strict non-QROAM base
        </label>
        <label>
          <input
            aria-label="Include QROAM chunk streams"
            checked={includeQroam}
            onChange={(event) => setIncludeQroam(event.currentTarget.checked)}
            type="checkbox"
          />
          Include QROAM chunk streams
        </label>
        <label>
          <input
            aria-label="Mistakenly sum qubits per leaf"
            checked={sumQubitsPerLeaf}
            onChange={(event) => setSumQubitsPerLeaf(event.currentTarget.checked)}
            type="checkbox"
          />
          Mistakenly sum qubits per leaf
        </label>
      </div>

      <div className="composer-grid">
        <article>
          <h4>Non-Clifford composition</h4>
          <div className="composer-formula-row">
            <span>Base without streamed QROAM</span>
            <strong>{formatInt(includeBase ? projectData.strictNonCliffordFormula.base_non_clifford_without_streamed_qroam : 0)}</strong>
            <em>{includeBase ? 'strict artifact term' : 'removed by learner'}</em>
          </div>
          <div className="composer-formula-row">
            <span>QROAM streams</span>
            <strong>{formatInt(selectedQroamStreams)} * {formatInt(projectData.strictNonCliffordFormula.per_chunk_stream_non_clifford)}</strong>
            <em>{qroamStreamsPerLeaf} streams per leaf</em>
          </div>
          <div className="composer-formula-row">
            <span>QROAM component</span>
            <strong>{formatInt(includeQroam ? selectedQroamNonClifford : 0)}</strong>
            <em>{includeQroam ? 'included' : 'removed by learner'}</em>
          </div>
          <div className="composer-total">
            <span>Reconstructed non-Clifford</span>
            <strong>{formatInt(composedNonClifford)}</strong>
            <em>strict headline expects {formatInt(projectData.currentStrictCandidate.non_clifford)}</em>
          </div>
        </article>

        <article>
          <h4>Peak logical-qubit composition</h4>
          <div className="composer-formula-row">
            <span>Tail field slots</span>
            <strong>{strictQubitFormula.tail_field_slots} * {strictQubitFormula.field_bits}</strong>
            <em>{formatInt(strictQubitFormula.tail_field_qubits)} field wires</em>
          </div>
          <div className="composer-formula-row">
            <span>Lookup workspace</span>
            <strong>{formatInt(strictQubitFormula.lookup_workspace_qubits)}</strong>
            <em>counted separately from tail slots</em>
          </div>
          <div className="composer-formula-row">
            <span>Controls, guard, phase</span>
            <strong>
              {strictQubitFormula.control_qubits}
              {' + '}
              {strictQubitFormula.fused_output_guard_qubits}
              {' + '}
              {strictQubitFormula.phase_qubits}
            </strong>
            <em>small live control surface</em>
          </div>
          <div className="composer-total">
            <span>{sumQubitsPerLeaf ? 'Wrong serial-sum qubits' : 'Peak live qubits'}</span>
            <strong>{formatInt(displayedQubits)}</strong>
            <em>
              {strictQubitFormula.tail_field_slots} * {strictQubitFormula.field_bits}
              {' + '}
              {strictQubitFormula.lookup_workspace_qubits}
              {' + '}
              {strictQubitFormula.control_qubits}
              {' + '}
              {strictQubitFormula.fused_output_guard_qubits}
              {' + '}
              {strictQubitFormula.phase_qubits}
            </em>
          </div>
        </article>
      </div>

      <div className="composer-audit-strip">
        <div className={compositionAuditPass ? 'audit-pass' : 'audit-fail'}>
          Composition audit: {compositionAuditPass ? 'pass' : 'fail'}
        </div>
        <div className={qubitAuditPass ? 'audit-pass' : 'audit-fail'}>
          Qubit model audit: {qubitAuditPass ? 'pass' : 'fail'}
        </div>
        <div>
          <strong>{formatInt(maxLeafCalls)} point-add leaves</strong>
          <span>Non-Clifford adds over calls; workspace is peak-live reuse.</span>
        </div>
      </div>
    </section>
  );
}
