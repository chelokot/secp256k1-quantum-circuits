import { useMemo, useState } from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';

type RoleCounts = Record<string, number>;

type ProjectData = {
  modularAccumulator: {
    sourceUncompute: {
      routeKindCounts: RoleCounts;
      cleanupStatusCounts: RoleCounts;
      requiredToPromote: string[];
    };
  };
  modularMultiplierLifecycle: {
    currentStream: {
      scratchObservationCount: number;
      scratchCleanupObservationCount: number;
      scratchAbandonedGarbageCount: number;
      partialProductScratchObservationCount: number;
      nonPartialProductScratchObservationCount: number;
      physicalLifecycleStatus: string;
    };
    streamedCandidate: {
      model: string;
      status: string;
      temporaryAndComputeEvents: number;
      requiredConsumeEvents: number;
      requiredCleanupEvents: number;
      peakTemporaryAndWiresIfSerialized: number;
    };
    candidateStream: {
      eventCount: number;
      segmentCount: number;
      routeStatusCounts: RoleCounts;
    };
  };
};

type RouteKind = 'partial_product' | 'zero_lift_guard';

const formatInt = (value: number) => new Intl.NumberFormat('en-US').format(value);
const readable = (value: string) => value.replaceAll('_', ' ');
const promotionStepCard = (step: string) => {
  if (step.startsWith('Expose concrete predicate controls')) {
    return {
      title: 'Expose guard controls',
      detail: 'Show the exact predicate controls for guard scratch rows, or remove the placeholder route.',
    };
  }
  if (step.startsWith('Lower consume_into_counted_accumulator')) {
    return {
      title: 'Lower consume rows',
      detail: 'Turn temporary-controlled accumulator updates into concrete primitive gates.',
    };
  }
  if (step.startsWith('Append the proven source-uncompute')) {
    return {
      title: 'Append cleanup rows',
      detail: 'Promote the proven CCX cleanup rows and recompute global liveness and non-Clifford totals.',
    };
  }
  return {
    title: readable(step),
    detail: 'Promotion evidence required before this cleanup route can enter the public primitive stream.',
  };
};

const routeLabels: Record<RouteKind, string> = {
  partial_product: 'partial product temporary AND',
  zero_lift_guard: 'zero-lift guard predicate',
};

export function AccumulatorScratchLifecycleLab({ projectData }: { projectData: ProjectData }) {
  const lifecycle = projectData.modularMultiplierLifecycle;
  const sourceUncompute = projectData.modularAccumulator.sourceUncompute;
  const [routeKind, setRouteKind] = useState<RouteKind>('partial_product');
  const [hasConsumeRow, setHasConsumeRow] = useState(false);
  const [hasCleanupReplay, setHasCleanupReplay] = useState(false);
  const [hasGuardPredicateControls, setHasGuardPredicateControls] = useState(false);

  const isGuard = routeKind === 'zero_lift_guard';
  const sourceControlsVisible = !isGuard || hasGuardPredicateControls;
  const lifecyclePass = hasConsumeRow && hasCleanupReplay && sourceControlsVisible;
  const routeCount = isGuard
    ? lifecycle.currentStream.nonPartialProductScratchObservationCount
    : lifecycle.currentStream.partialProductScratchObservationCount;
  const cleanupStatus = isGuard
    ? 'missing_source_controls_for_cleanup'
    : 'source_uncompute_cleanup_ccx_proven';
  const cleanupCount = sourceUncompute.cleanupStatusCounts[cleanupStatus] ?? 0;

  const timeline = useMemo(() => [
    {
      title: 'Compute temporary',
      state: 'present',
      detail: isGuard
        ? 'predicate ladder creates a one-bit guard target'
        : 'CCX(left_bit, right_bit -> scratch)',
    },
    {
      title: 'Consume into accumulator',
      state: hasConsumeRow ? 'present' : 'missing',
      detail: hasConsumeRow
        ? 'scratch controls a counted accumulator update'
        : 'producer-only scratch remains unused by counted state',
    },
    {
      title: 'Replay cleanup',
      state: hasCleanupReplay && sourceControlsVisible ? 'present' : 'missing',
      detail: sourceControlsVisible
        ? 'same source controls return scratch to |0>'
        : 'guard predicate controls are not exposed yet',
    },
  ], [hasCleanupReplay, hasConsumeRow, isGuard, sourceControlsVisible]);

  return (
    <section className="wide-panel" data-testid="accumulator-scratch-lifecycle-lab">
      <div className="panel-heading">
        <RotateCcw size={20} />
        <h3>Scratch lifecycle lab</h3>
      </div>
      <p>
        The current modular primitive stream has {formatInt(lifecycle.currentStream.scratchObservationCount)}
        {' '}temporary-AND scratch observations, {formatInt(lifecycle.currentStream.scratchCleanupObservationCount)}
        {' '}cleanup observations, and {formatInt(lifecycle.currentStream.scratchAbandonedGarbageCount)}
        {' '}abandoned targets. Current stream status: {readable(lifecycle.currentStream.physicalLifecycleStatus)}.
      </p>
      <section className="scratch-contract-grid" aria-label="Scratch lifecycle contract">
        <article>
          <strong>Temporary AND</strong>
          <p>A one-bit scratch target produced from two source controls.</p>
        </article>
        <article>
          <strong>Consume row</strong>
          <p>The row that uses the scratch bit to update counted accumulator state.</p>
        </article>
        <article>
          <strong>Source-uncompute</strong>
          <p>Replay the same source controls so the scratch target returns to zero.</p>
        </article>
        <article>
          <strong>Guard route</strong>
          <p>A predicate-cleanup route is blocked until its source controls are explicit.</p>
        </article>
      </section>

      <div className="scratch-summary">
        <div>
          <span>Partial-product temporary ANDs</span>
          <strong>{formatInt(lifecycle.currentStream.partialProductScratchObservationCount)}</strong>
        </div>
        <div>
          <span>Zero-lift guard rows</span>
          <strong>{formatInt(lifecycle.currentStream.nonPartialProductScratchObservationCount)}</strong>
        </div>
        <div>
          <span>Proven source-uncompute cleanup</span>
          <strong>{formatInt(sourceUncompute.cleanupStatusCounts.source_uncompute_cleanup_ccx_proven ?? 0)}</strong>
        </div>
        <div>
          <span>Serialized temporary peak</span>
          <strong>{formatInt(lifecycle.streamedCandidate.peakTemporaryAndWiresIfSerialized)}</strong>
        </div>
      </div>

      <div className="scratch-lifecycle-grid">
        <article>
          <h4>Route under review</h4>
          <label className="assignment-control">
            <span>Scratch route</span>
            <select
              aria-label="Scratch lifecycle route"
              onChange={(event) => setRouteKind(event.currentTarget.value as RouteKind)}
              value={routeKind}
            >
              <option value="partial_product">Partial-product row</option>
              <option value="zero_lift_guard">Zero-lift guard row</option>
            </select>
          </label>
          <dl className="metric-pair">
            <div>
              <dt>Route</dt>
              <dd>{routeLabels[routeKind]}</dd>
            </div>
            <div>
              <dt>Rows</dt>
              <dd>{formatInt(routeCount)}</dd>
            </div>
            <div>
              <dt>Cleanup status</dt>
              <dd>{readable(cleanupStatus)}</dd>
            </div>
            <div>
              <dt>Status rows</dt>
              <dd>{formatInt(cleanupCount)}</dd>
            </div>
          </dl>
        </article>

        <article>
          <h4>Lifecycle controls</h4>
          <label className="toggle-row">
            <input
              aria-label="Add consume row"
              checked={hasConsumeRow}
              onChange={(event) => setHasConsumeRow(event.currentTarget.checked)}
              type="checkbox"
            />
            <span>Add consume row</span>
          </label>
          <label className="toggle-row">
            <input
              aria-label="Replay cleanup controls"
              checked={hasCleanupReplay}
              onChange={(event) => setHasCleanupReplay(event.currentTarget.checked)}
              type="checkbox"
            />
            <span>Replay cleanup controls</span>
          </label>
          <label className="toggle-row">
            <input
              aria-label="Expose guard predicate controls"
              checked={hasGuardPredicateControls}
              onChange={(event) => setHasGuardPredicateControls(event.currentTarget.checked)}
              type="checkbox"
            />
            <span>Expose guard predicate controls</span>
          </label>
          <p className={lifecyclePass ? 'audit-pass' : 'audit-fail'}>
            Lifecycle audit: {lifecyclePass ? 'pass' : 'blocked'}
          </p>
        </article>
      </div>

      <div className="scratch-timeline">
        {timeline.map((stage, index) => (
          <article className={stage.state === 'present' ? 'present' : 'missing'} key={stage.title}>
            <span>{index + 1}</span>
            <strong>{stage.title}</strong>
            <p>{stage.detail}</p>
          </article>
        ))}
      </div>

      <div className="scratch-lifecycle-grid">
        <article>
          <h4>Why this blocks promotion</h4>
          <p>
            The candidate lifecycle model is {readable(lifecycle.streamedCandidate.model)}
            {' '}with {formatInt(lifecycle.streamedCandidate.requiredConsumeEvents)} consume events and
            {' '}{formatInt(lifecycle.streamedCandidate.requiredCleanupEvents)} cleanup events. It has
            {' '}{formatInt(lifecycle.candidateStream.eventCount)} generated events over
            {' '}{formatInt(lifecycle.candidateStream.segmentCount)} segments, but its status is
            {' '}{readable(lifecycle.streamedCandidate.status)}.
          </p>
        </article>
        <article>
          <h4>Open edge</h4>
          <p className="warning-note">
            <AlertTriangle size={18} />
            <span>
              Guard cleanup rows still missing source controls:
              {' '}{formatInt(sourceUncompute.cleanupStatusCounts.missing_source_controls_for_cleanup ?? 0)}.
            </span>
          </p>
          <div className="obligation-step-list">
            {sourceUncompute.requiredToPromote.map((step) => {
              const card = promotionStepCard(step);
              return (
                <article key={step}>
                  <strong>{card.title}</strong>
                  <p>{card.detail}</p>
                </article>
              );
            })}
          </div>
        </article>
      </div>
    </section>
  );
}
