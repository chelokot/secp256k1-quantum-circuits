import { useMemo, useState } from 'react';
import * as d3 from 'd3';
import { Factory } from 'lucide-react';

type RoleCounts = Record<string, number>;

type CarryLayer = {
  layer_index: number;
  full_adder_count: number;
  max_column_height_after_layer: number;
  live_column_bits_after_layer: number;
};

type ProjectData = {
  modularAccumulator: {
    rowStream: {
      status: string;
      rowCount: number;
      segmentCount: number;
      roleCounts: RoleCounts;
      requiredToPromote: string[];
    };
    carrySave: {
      status: string;
      schoolbookGridCount: number;
      singleGrid: {
        inputColumnCount: number;
        initialPartialProductBits: number;
        layerCount: number;
        fullAdderCount: number;
        finalLiveColumnBits: number;
        finalMaxColumnHeight: number;
        finalCarryPropagateBits: number;
        layers: CarryLayer[];
      };
      allGrids: {
        partial_product_rows: number;
        carry_save_full_adder_count: number;
        final_carry_propagate_bits: number;
        candidate_touch_count: number;
        naive_carry_obligation_rows: number;
      };
    };
    fullAdderContract: {
      status: string;
      totals: {
        full_adder_cell_count: number;
        embedded_full_adder_primitive_counts: {
          ccx: number;
          cx: number;
        };
        retained_input_obligation_bits: number;
        output_obligation_bits: number;
      };
      primitiveCountsPerCell: {
        ccx: number;
        cx: number;
      };
      irreversibleCollisionCount: number;
    };
    fullAdderStream: {
      status: string;
      nonCliffordCount: number;
      operationCount: number;
      retainedInputObligationBits: number;
      outputObligationBits: number;
      segmentCount: number;
    };
    sourceUncompute: {
      status: string;
      rowCount: number;
      routeKindCounts: RoleCounts;
      cleanupStatusCounts: RoleCounts;
    };
  };
};

const formatInt = (value: number) => new Intl.NumberFormat('en-US').format(value);
const readable = (value: string) => value.replaceAll('_', ' ');
const promotionStepCard = (step: string) => {
  if (step.startsWith('Lower partial_product_accumulator_consume')) {
    return {
      title: 'Lower product-consume rows',
      detail: 'Turn product-to-accumulator obligations into concrete reversible update gates.',
    };
  }
  if (step.startsWith('Lower pseudo_mersenne')) {
    return {
      title: 'Lower field-fold rows',
      detail: 'Make the modular fold gates explicit, including carry and cleanup owner assignment.',
    };
  }
  if (step.startsWith('Lower temporary_and_cleanup')) {
    return {
      title: 'Lower temporary cleanup',
      detail: 'Replace cleanup obligations with exact uncompute or measurement-cleanup primitives.',
    };
  }
  if (step.startsWith('Rebuild scheduled_modular_primitive_netlist')) {
    return {
      title: 'Rebuild the scheduled stream',
      detail: 'Regenerate the primitive netlist and derive gates, measurements, and peak liveness from it.',
    };
  }
  return {
    title: readable(step),
    detail: 'Promotion evidence required before this row family can be counted as public primitive stream work.',
  };
};

const stageOrder = [
  'partial_product_accumulator_consume',
  'pseudo_mersenne_high_column_fold',
  'pseudo_mersenne_low_column_fold',
  'temporary_and_cleanup',
  'zero_lift_guard_consume_cleanup',
];

export function AccumulatorLoweringLab({ projectData }: { projectData: ProjectData }) {
  const accumulator = projectData.modularAccumulator;
  const [selectedRole, setSelectedRole] = useState(stageOrder[0]);
  const [showPromotedOnly, setShowPromotedOnly] = useState(false);

  const roleRows = stageOrder.map((role) => ({
    role,
    count: accumulator.rowStream.roleCounts[role] ?? 0,
  }));
  const maxRoleCount = d3.max(roleRows, (row) => row.count) ?? 1;
  const roleScale = d3.scaleLinear([0, maxRoleCount], [8, 100]);
  const selectedCount = accumulator.rowStream.roleCounts[selectedRole] ?? 0;

  const layerBars = useMemo(() => {
    const maxLiveBits = d3.max(accumulator.carrySave.singleGrid.layers, (layer) => layer.live_column_bits_after_layer) ?? 1;
    const scale = d3.scaleLinear([0, maxLiveBits], [6, 100]);
    return accumulator.carrySave.singleGrid.layers.map((layer) => ({
      ...layer,
      width: scale(layer.live_column_bits_after_layer),
    }));
  }, [accumulator]);

  const promoted = false;
  const visibleRequiredSteps = showPromotedOnly ? [] : accumulator.rowStream.requiredToPromote;

  return (
    <section className="wide-panel" data-testid="accumulator-lowering-lab">
      <div className="panel-heading">
        <Factory size={20} />
        <h3>Modular accumulator lowering</h3>
      </div>
      <p>
        This lab reads the modular-multiply artifact as a set of unpaid work orders.
        Each work order names a row family the engine still has to lower into primitive
        gates, owners, lifetimes, and cleanup before it can become a public resource row.
      </p>
      <section className="accumulator-vocab-grid" aria-label="Accumulator lowering vocabulary">
        <article>
          <strong>Accumulator</strong>
          <p>A running column structure that receives many one-bit product effects.</p>
        </article>
        <article>
          <strong>Carry-save</strong>
          <p>A compression method that lowers column height without erasing obligations.</p>
        </article>
        <article>
          <strong>Full-adder cell</strong>
          <p>A reversible 3-bit-to-2-bit compressor with explicit CCX and CX cost.</p>
        </article>
        <article>
          <strong>Promotion</strong>
          <p>The step from side artifact to the scheduled primitive stream everyone counts.</p>
        </article>
      </section>
      <div className="accumulator-summary">
        <div>
          <span>Row obligations</span>
          <strong>{formatInt(accumulator.rowStream.rowCount)}</strong>
        </div>
        <div>
          <span>Full-adder cells</span>
          <strong>{formatInt(accumulator.fullAdderContract.totals.full_adder_cell_count)}</strong>
        </div>
        <div>
          <span>Full-adder CCX</span>
          <strong>{formatInt(accumulator.fullAdderStream.nonCliffordCount)}</strong>
        </div>
        <div>
          <span>Source cleanup rows</span>
          <strong>{formatInt(accumulator.sourceUncompute.rowCount)}</strong>
        </div>
      </div>

      <div className="accumulator-grid">
        <article>
          <h4>Obligation stream</h4>
          <div className="role-bars">
            {roleRows.map((row) => (
              <button
                className={row.role === selectedRole ? 'selected' : ''}
                key={row.role}
                onClick={() => setSelectedRole(row.role)}
                type="button"
              >
                <span>{readable(row.role)}</span>
                <div style={{ width: `${roleScale(row.count)}%` }} />
                <strong>{formatInt(row.count)}</strong>
              </button>
            ))}
          </div>
          <p>
            Selected role: {readable(selectedRole)}. It contributes {formatInt(selectedCount)}
            {' '}rows before promotion into exact primitive gates.
          </p>
        </article>

        <article>
          <h4>Carry-save compression feel</h4>
          <div className="carry-layer-bars">
            {layerBars.map((layer) => (
              <div key={layer.layer_index}>
                <span>L{layer.layer_index}</span>
                <div style={{ width: `${layer.width}%` }} />
                <strong>{formatInt(layer.live_column_bits_after_layer)}</strong>
              </div>
            ))}
          </div>
          <p>
            One 256-bit grid starts with {formatInt(accumulator.carrySave.singleGrid.initialPartialProductBits)}
            {' '}partial-product bits and ends with max column height {accumulator.carrySave.singleGrid.finalMaxColumnHeight}.
          </p>
        </article>
      </div>

      <div className="accumulator-grid">
        <article>
          <h4>Why the full adder is not magic</h4>
          <dl className="metric-pair">
            <div>
              <dt>Per cell</dt>
              <dd>{accumulator.fullAdderContract.primitiveCountsPerCell.ccx} CCX + {accumulator.fullAdderContract.primitiveCountsPerCell.cx} CX</dd>
            </div>
            <div>
              <dt>Irreversible collisions</dt>
              <dd>{accumulator.fullAdderContract.irreversibleCollisionCount}</dd>
            </div>
            <div>
              <dt>Retained inputs</dt>
              <dd>{formatInt(accumulator.fullAdderStream.retainedInputObligationBits)}</dd>
            </div>
            <div>
              <dt>Output bits</dt>
              <dd>{formatInt(accumulator.fullAdderStream.outputObligationBits)}</dd>
            </div>
          </dl>
          <p>
            A 3-to-2 compressor saves column height only if the old inputs and
            new sum/carry wires have a counted owner or a proven cleanup route.
          </p>
        </article>

        <article>
          <h4>Promotion gate</h4>
          <label className="toggle-row">
            <input
              aria-label="Show only promoted accumulator facts"
              checked={showPromotedOnly}
              onChange={(event) => setShowPromotedOnly(event.currentTarget.checked)}
              type="checkbox"
            />
            <span>hide unpromoted obligations</span>
          </label>
          <p className={promoted ? 'audit-pass' : 'audit-fail'}>
            Accumulator promotion: {promoted ? 'promoted' : 'not promoted'}
          </p>
          <div className="obligation-step-list">
            {visibleRequiredSteps.length === 0 ? (
              <article>
                <strong>No hidden promotion steps displayed.</strong>
                <p>The toggle hides unpromoted obligations; it does not make the candidate promoted.</p>
              </article>
            ) : visibleRequiredSteps.map((step) => {
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
