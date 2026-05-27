import { useMemo, useState } from 'react';
import { Rows3 } from 'lucide-react';

type ProjectData = {
  attackScaffold: {
    publicGoogle: {
      windowSize: number;
      retainedWindowAdditions: number;
      lowQubitLogicalQubits: number;
      lowQubitNonClifford: number;
      lowGateLogicalQubits: number;
      lowGateNonClifford: number;
    };
    mainline: {
      windowSize: number;
      rawWindowCount: number;
      directSeedWindowIndex: number;
      retainedWindowAdditions: number;
      retainedWindows: number[];
      classicalTailElisions: number[];
      formulaRelation: string;
      formulaValue: number;
    };
    compilerRaw32: {
      windowSize: number;
      rawWindowCount: number;
      phaseRegisterBitsTotal: number;
      leafCallCount: number;
      leafWindows: Array<{
        callIndex: number;
        phaseRegister: string;
        windowIndexWithinRegister: number;
        bitStart: number;
        bitWidth: number;
      }>;
    };
  };
};

const formatInt = (value: number) => new Intl.NumberFormat('en-US').format(value);

function windowClass(kind: string) {
  if (kind === 'seed') return 'window-cell seed';
  if (kind === 'elided') return 'window-cell elided';
  if (kind === 'raw32') return 'window-cell raw32';
  return 'window-cell retained';
}

export function WindowScaffoldLab({ projectData }: { projectData: ProjectData }) {
  const [mode, setMode] = useState<'mainline' | 'raw32'>('mainline');
  const [selectedWindow, setSelectedWindow] = useState(16);
  const scaffold = projectData.attackScaffold;

  const windows = useMemo(() => {
    return Array.from({ length: scaffold.mainline.rawWindowCount }, (_, index) => {
      if (index === scaffold.mainline.directSeedWindowIndex) return { index, kind: 'seed' };
      if (mode === 'mainline' && scaffold.mainline.classicalTailElisions.includes(index)) return { index, kind: 'elided' };
      if (mode === 'raw32') return { index, kind: 'raw32' };
      return { index, kind: 'retained' };
    });
  }, [mode, scaffold.mainline.classicalTailElisions, scaffold.mainline.directSeedWindowIndex, scaffold.mainline.rawWindowCount]);

  const selectedRawCall = scaffold.compilerRaw32.leafWindows.find((call) => {
    const rawWindowIndex = call.phaseRegister === 'phase_a'
      ? call.windowIndexWithinRegister
      : call.windowIndexWithinRegister + 16;
    return rawWindowIndex === selectedWindow;
  });
  const selectedKind = windows[selectedWindow]?.kind ?? 'retained';
  const retainedCount = mode === 'mainline' ? scaffold.mainline.retainedWindowAdditions : scaffold.compilerRaw32.leafCallCount;
  const elidedCount = mode === 'mainline' ? scaffold.mainline.classicalTailElisions.length : 0;

  return (
    <section className="wide-panel" data-testid="window-scaffold-lab">
      <div className="panel-heading">
        <Rows3 size={20} />
        <h3>Windowed attack scaffold</h3>
      </div>
      <p>
        Phase estimation supplies 512 control bits. The circuit groups them into 32 windows of
        16 bits, then each retained window becomes one lookup-fed point-add leaf.
      </p>

      <div className="scaffold-controls">
        <label className="assignment-control">
          <span>Scaffold mode</span>
          <select
            aria-label="Scaffold mode"
            value={mode}
            onChange={(event) => setMode(event.currentTarget.value as 'mainline' | 'raw32')}
          >
            <option value="mainline">mainline retained-window scaffold</option>
            <option value="raw32">compiler raw-32 oracle</option>
          </select>
        </label>
        <label className="slider-label">
          <span>Selected window {selectedWindow}</span>
          <input
            aria-label="Selected scaffold window"
            max={scaffold.mainline.rawWindowCount - 1}
            min="0"
            onChange={(event) => setSelectedWindow(Number(event.currentTarget.value))}
            type="range"
            value={selectedWindow}
          />
        </label>
      </div>

      <div className="window-grid" aria-label="Window scaffold grid">
        {windows.map((window) => (
          <button
            aria-label={`Window ${window.index} ${window.kind}`}
            className={window.index === selectedWindow ? `${windowClass(window.kind)} selected` : windowClass(window.kind)}
            key={window.index}
            onClick={() => setSelectedWindow(window.index)}
            type="button"
          >
            <span>{window.index}</span>
          </button>
        ))}
      </div>

      <div className="scaffold-detail-grid">
        <article>
          <h4>Current mode</h4>
          <dl className="metric-pair">
            <div>
              <dt>Window size</dt>
              <dd>{scaffold.mainline.windowSize} bits</dd>
            </div>
            <div>
              <dt>Raw windows</dt>
              <dd>{scaffold.mainline.rawWindowCount}</dd>
            </div>
            <div>
              <dt>Point-add leaves</dt>
              <dd>{retainedCount}</dd>
            </div>
            <div>
              <dt>Classical tail elisions</dt>
              <dd>{elidedCount}</dd>
            </div>
          </dl>
          <p>
            Mainline formula check: {scaffold.mainline.formulaRelation} = {scaffold.mainline.formulaValue}.
            The compiler raw-32 path keeps {scaffold.compilerRaw32.leafCallCount} leaf calls after the direct seed.
          </p>
        </article>

        <article>
          <h4>Selected window</h4>
          <p className="mono-line">window {selectedWindow}: {selectedKind}</p>
          <p>
            {selectedKind === 'seed' && 'The seed initializes the accumulator directly, replacing the first raw windowed point-add.'}
            {selectedKind === 'retained' && 'This window becomes one lookup-fed point-add leaf in the retained-window scaffold.'}
            {selectedKind === 'elided' && 'This window is reconstructed classically in the mainline scaffold, but the raw-32 compiler path keeps it quantum.'}
            {selectedKind === 'raw32' && 'The raw-32 compiler oracle keeps this as part of the fully quantum schedule.'}
          </p>
          {selectedRawCall ? (
            <dl className="metric-pair">
              <div>
                <dt>Phase register</dt>
                <dd>{selectedRawCall.phaseRegister}</dd>
              </div>
              <div>
                <dt>Bit range</dt>
                <dd>{selectedRawCall.bitStart}-{selectedRawCall.bitStart + selectedRawCall.bitWidth - 1}</dd>
              </div>
            </dl>
          ) : (
            <p className="audit-pass">Direct seed window has no point-add call index.</p>
          )}
        </article>
      </div>

      <div className="google-scaffold-note">
        <strong>Public Google comparison line</strong>
        <span>
          window size {scaffold.publicGoogle.windowSize}, retained additions {scaffold.publicGoogle.retainedWindowAdditions},
          low-qubit row {formatInt(scaffold.publicGoogle.lowQubitLogicalQubits)}q / {formatInt(scaffold.publicGoogle.lowQubitNonClifford)} non-Clifford,
          low-gate row {formatInt(scaffold.publicGoogle.lowGateLogicalQubits)}q / {formatInt(scaffold.publicGoogle.lowGateNonClifford)} non-Clifford.
        </span>
      </div>
    </section>
  );
}
