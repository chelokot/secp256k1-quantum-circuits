import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
const readJson = (relativePath) => JSON.parse(readFileSync(resolve(root, relativePath), 'utf8'));

const baselineStatus = readJson('compiler_verification_project/artifacts/current_baseline_status.json');
const strictHeadline = readJson('compiler_verification_project/artifacts/strict_replayed_tail_headline.json');
const engineCompletion = readJson('compiler_verification_project/artifacts/engine_completion_audit.json');
const zeroLiftGuard = readJson('compiler_verification_project/artifacts/zero_lift_guard_resource_audit.json');
const tailMacroEngine = readJson('compiler_verification_project/artifacts/tail_macro_engine.json');
const publicHeadlineResult = readJson('compiler_verification_project/artifacts/public_headline_result.json');
const googleBaseline = readJson('data/public_google_baseline.json');
const mainlineScaffold = readJson('artifacts/circuits/ecdlp_scaffold_optimized.json');
const fullRaw32Oracle = readJson('compiler_verification_project/artifacts/full_raw32_oracle.json');
const familyFrontier = readJson('compiler_verification_project/artifacts/family_frontier.json');
const proofPublicationStatus = readJson('compiler_verification_project/artifacts/proof_publication_status.json');
const proofCorpusProfiles = readJson('compiler_verification_project/artifacts/proof_corpus_profiles.json');
const modularAccumulatorRowStream = readJson('compiler_verification_project/artifacts/modular_accumulator_row_stream.json');
const modularAccumulatorCarrySave = readJson('compiler_verification_project/artifacts/modular_accumulator_carry_save_candidate.json');
const modularAccumulatorFullAdderContract = readJson('compiler_verification_project/artifacts/modular_accumulator_full_adder_contract.json');
const modularAccumulatorFullAdderStream = readJson('compiler_verification_project/artifacts/modular_accumulator_full_adder_stream.json');
const modularAccumulatorSourceUncompute = readJson('compiler_verification_project/artifacts/modular_accumulator_source_uncompute.json');
const modularMultiplierLifecycle = readJson('compiler_verification_project/artifacts/modular_multiplier_lifecycle.json');
const hybridBridgeSearch = readJson('compiler_verification_project/artifacts/hybrid_bridge_search.json');
const lookupFedLeafEquivalence = readJson('compiler_verification_project/artifacts/lookup_fed_leaf_equivalence.json');
const streamedLookupTailLeafEquivalence = readJson('compiler_verification_project/artifacts/streamed_lookup_tail_leaf_equivalence.json');

const frontierReference = familyFrontier.best_qubit_family;

const payload = {
  generatedFrom: {
    baselineStatus: 'compiler_verification_project/artifacts/current_baseline_status.json',
    strictHeadline: 'compiler_verification_project/artifacts/strict_replayed_tail_headline.json',
    engineCompletion: 'compiler_verification_project/artifacts/engine_completion_audit.json',
    zeroLiftGuard: 'compiler_verification_project/artifacts/zero_lift_guard_resource_audit.json',
    tailMacroEngine: 'compiler_verification_project/artifacts/tail_macro_engine.json',
    publicHeadlineResult: 'compiler_verification_project/artifacts/public_headline_result.json',
    googleBaseline: 'data/public_google_baseline.json',
    mainlineScaffold: 'artifacts/circuits/ecdlp_scaffold_optimized.json',
    fullRaw32Oracle: 'compiler_verification_project/artifacts/full_raw32_oracle.json',
    proofPublicationStatus: 'compiler_verification_project/artifacts/proof_publication_status.json',
    proofCorpusProfiles: 'compiler_verification_project/artifacts/proof_corpus_profiles.json',
    modularAccumulatorRowStream: 'compiler_verification_project/artifacts/modular_accumulator_row_stream.json',
    modularAccumulatorCarrySave: 'compiler_verification_project/artifacts/modular_accumulator_carry_save_candidate.json',
    modularAccumulatorFullAdderContract: 'compiler_verification_project/artifacts/modular_accumulator_full_adder_contract.json',
    modularAccumulatorFullAdderStream: 'compiler_verification_project/artifacts/modular_accumulator_full_adder_stream.json',
    modularAccumulatorSourceUncompute: 'compiler_verification_project/artifacts/modular_accumulator_source_uncompute.json',
    modularMultiplierLifecycle: 'compiler_verification_project/artifacts/modular_multiplier_lifecycle.json',
    hybridBridgeSearch: 'compiler_verification_project/artifacts/hybrid_bridge_search.json',
    lookupFedLeafEquivalence: 'compiler_verification_project/artifacts/lookup_fed_leaf_equivalence.json',
    streamedLookupTailLeafEquivalence: 'compiler_verification_project/artifacts/streamed_lookup_tail_leaf_equivalence.json',
  },
  acceptedPhysicalBaseline: baselineStatus.accepted_physical_baseline,
  currentStrictCandidate: baselineStatus.current_strict_candidate,
  guardCorrectedNoAliasCandidate: baselineStatus.guard_corrected_no_alias_candidate,
  acceptedBaselineGate: baselineStatus.accepted_baseline_gate,
  strictFormula: strictHeadline.logical_qubit_formula,
  strictNonCliffordFormula: strictHeadline.non_clifford_formula,
  activeBlockers: baselineStatus.remaining_physical_baseline_blockers,
  engineCompletion: {
    cliffordCompleteGoalAchieved: engineCompletion.clifford_complete_goal_achieved,
    remainingMacroBoundaries: engineCompletion.remaining_macro_boundaries.map((boundary) => ({
      name: boundary.name,
      status: boundary.status,
      requiredToClose: boundary.required_to_close,
    })),
  },
  zeroLiftGuard: {
    current: zeroLiftGuard.current_guard_owner_capacity,
    cleanLadder: zeroLiftGuard.standard_clean_ladder_requirement,
    gap: zeroLiftGuard.capacity_gap,
  },
  reversibleOverwrite: {
    status: tailMacroEngine.fused_output_lowering_contract.status,
    overwrittenOutputRowCount: tailMacroEngine.fused_output_lowering_contract.overwritten_output_row_count,
    allOutputOverwritesHaveBoundaryPermutationContract:
      tailMacroEngine.fused_output_lowering_contract.all_output_overwrites_have_boundary_permutation_contract,
    costMatchesRows: tailMacroEngine.fused_output_lowering_contract.cost_matches_rows,
    guardOwnerCapacity: tailMacroEngine.fused_output_lowering_contract.guard_owner_capacity,
    overwriteRow: tailMacroEngine.fused_output_lowering_contract.rows.find((row) => row.overwrite_contract !== null),
    replay: {
      checkedNonInfinityPairs: tailMacroEngine.fused_output_replay_certificate.checked_non_infinity_pairs,
      checkedLookupInfinityPairs: tailMacroEngine.fused_output_replay_certificate.checked_lookup_infinity_pairs,
      ownerCapacityPass: tailMacroEngine.fused_output_replay_certificate.owner_capacity_pass,
      pass: tailMacroEngine.fused_output_replay_certificate.pass,
    },
  },
  attackScaffold: {
    publicGoogle: {
      windowSize: googleBaseline.window_size,
      retainedWindowAdditions: googleBaseline.retained_window_additions,
      lowQubitLogicalQubits: googleBaseline.lines.low_qubit.logical_qubits,
      lowQubitNonClifford: googleBaseline.lines.low_qubit.non_clifford,
      lowGateLogicalQubits: googleBaseline.lines.low_gate.logical_qubits,
      lowGateNonClifford: googleBaseline.lines.low_gate.non_clifford,
    },
    mainline: {
      windowSize: mainlineScaffold.window_size,
      rawWindowCount: mainlineScaffold.raw_window_count,
      directSeedWindowIndex: mainlineScaffold.direct_lookup_seed.raw_window_index,
      retainedWindowAdditions: mainlineScaffold.retained_window_additions.length,
      retainedWindows: mainlineScaffold.retained_window_additions.map((call) => call.raw_window_index),
      classicalTailElisions: mainlineScaffold.classical_tail_elisions.map((row) => row.raw_window_index),
      formulaRelation: mainlineScaffold.formula_check.appendix_relation,
      formulaValue: mainlineScaffold.formula_check.value,
      notes: mainlineScaffold.notes,
    },
    compilerRaw32: {
      windowSize: fullRaw32Oracle.raw_window_bits,
      rawWindowCount: fullRaw32Oracle.raw_window_count,
      phaseRegisterBitsTotal: fullRaw32Oracle.phase_register_bits_total,
      directSeedWindowIndex: fullRaw32Oracle.direct_seed.window_index_within_register,
      leafCallCount: fullRaw32Oracle.leaf_calls.length,
      leafWindows: fullRaw32Oracle.leaf_calls.map((call) => ({
        callIndex: call.call_index,
        phaseRegister: call.phase_register,
        windowIndexWithinRegister: call.window_index_within_register,
        bitStart: call.bit_start,
        bitWidth: call.bit_width,
      })),
    },
  },
  proofPublication: {
    publicationReady: proofPublicationStatus.publication_ready,
    allCurrent: proofPublicationStatus.proof_status.all_current,
    staleSystems: proofPublicationStatus.proof_status.stale_systems,
    systems: Object.values(proofPublicationStatus.proof_status.systems).map((system) => ({
      system: system.system,
      current: system.current,
      publicValuesMatchCurrent: system.public_values_match_current,
      resourceDigestMatchesInput: system.resource_digest_matches_input,
      proofFileExists: system.proof_file_exists,
      verifierKeyFileExists: system.verifier_key_file_exists,
      staleReasons: system.stale_reasons,
    })),
    blockers: proofPublicationStatus.publication_blockers.map((blocker) => ({
      system: blocker.system,
      inputBindingStatus: blocker.input_binding_status,
      staleReasons: blocker.stale_reasons,
      requiredToClose: blocker.required_to_close ?? null,
    })),
    gateCommands: proofPublicationStatus.publication_gate_commands.map((command) => ({
      name: command.name,
      phase: command.phase,
    })),
  },
  proofCorpusProfiles: {
    selectedPublicProfile: proofCorpusProfiles.selected_public_profile,
    releaseProfile: proofCorpusProfiles.release_profile,
    publicCaseCount: proofCorpusProfiles.profiles[proofCorpusProfiles.selected_public_profile].case_count,
    releaseCaseCount: proofCorpusProfiles.profiles[proofCorpusProfiles.release_profile].case_count,
    publicReleaseGrade: proofCorpusProfiles.profiles[proofCorpusProfiles.selected_public_profile].release_grade,
    releaseGrade: proofCorpusProfiles.profiles[proofCorpusProfiles.release_profile].release_grade,
    boundary: proofCorpusProfiles.boundary,
  },
  modularAccumulator: {
    rowStream: {
      pass: modularAccumulatorRowStream.pass,
      status: modularAccumulatorRowStream.promotion_status.status,
      rowCount: modularAccumulatorRowStream.row_stream.row_count,
      segmentCount: modularAccumulatorRowStream.row_stream.segment_count,
      roleCounts: modularAccumulatorRowStream.row_stream.role_counts,
      routeKindCounts: modularAccumulatorRowStream.row_stream.route_kind_counts,
      capacityOwnerCounts: modularAccumulatorRowStream.row_stream.capacity_owner_counts,
      expandedCounts: modularAccumulatorRowStream.expanded_counts,
      knownCostStatus: modularAccumulatorRowStream.known_cost_status,
      requiredToPromote: modularAccumulatorRowStream.promotion_status.required_to_promote,
    },
    carrySave: {
      pass: modularAccumulatorCarrySave.pass,
      status: modularAccumulatorCarrySave.promotion_status.status,
      schoolbookGridCount: modularAccumulatorCarrySave.schoolbook_grid_count,
      singleGrid: {
        inputColumnCount: modularAccumulatorCarrySave.single_grid.input_column_count,
        initialPartialProductBits: modularAccumulatorCarrySave.single_grid.initial_partial_product_bits,
        layerCount: modularAccumulatorCarrySave.single_grid.layer_count,
        fullAdderCount: modularAccumulatorCarrySave.single_grid.full_adder_count,
        finalLiveColumnBits: modularAccumulatorCarrySave.single_grid.final_live_column_bits,
        finalMaxColumnHeight: modularAccumulatorCarrySave.single_grid.final_max_column_height,
        finalCarryPropagateBits: modularAccumulatorCarrySave.single_grid.final_carry_propagate_bits,
        layers: modularAccumulatorCarrySave.single_grid.layers.slice(0, 16),
      },
      allGrids: modularAccumulatorCarrySave.all_grids,
      requiredToPromote: modularAccumulatorCarrySave.promotion_status.required_to_promote,
    },
    fullAdderContract: {
      pass: modularAccumulatorFullAdderContract.pass,
      status: modularAccumulatorFullAdderContract.promotion_status.status,
      totals: modularAccumulatorFullAdderContract.candidate_totals,
      primitiveCountsPerCell: modularAccumulatorFullAdderContract.cell_contract.primitive_counts_per_cell,
      irreversibleCollisionCount: modularAccumulatorFullAdderContract.cell_contract.irreversible_three_to_two_collision_count,
      requiredToPromote: modularAccumulatorFullAdderContract.promotion_status.required_to_promote,
    },
    fullAdderStream: {
      pass: modularAccumulatorFullAdderStream.pass,
      status: modularAccumulatorFullAdderStream.promotion_status.status,
      fullAdderCellCount: modularAccumulatorFullAdderStream.full_adder_cell_count,
      nonCliffordCount: modularAccumulatorFullAdderStream.non_clifford_count,
      operationCount: modularAccumulatorFullAdderStream.operation_count,
      retainedInputObligationBits: modularAccumulatorFullAdderStream.retained_input_obligation_bits,
      outputObligationBits: modularAccumulatorFullAdderStream.output_obligation_bits,
      segmentCount: modularAccumulatorFullAdderStream.segment_count,
      requiredToPromote: modularAccumulatorFullAdderStream.promotion_status.required_to_promote,
    },
    sourceUncompute: {
      pass: modularAccumulatorSourceUncompute.pass,
      status: modularAccumulatorSourceUncompute.promotion_status.status,
      rowCount: modularAccumulatorSourceUncompute.source_uncompute_stream.row_count,
      segmentCount: modularAccumulatorSourceUncompute.source_uncompute_stream.segment_count,
      routeKindCounts: modularAccumulatorSourceUncompute.source_uncompute_stream.route_kind_counts,
      cleanupStatusCounts: modularAccumulatorSourceUncompute.source_uncompute_stream.cleanup_status_counts,
      requiredToPromote: modularAccumulatorSourceUncompute.promotion_status.required_to_promote,
    },
  },
  modularMultiplierLifecycle: {
    pass: modularMultiplierLifecycle.pass,
    currentStream: {
      operationCount: modularMultiplierLifecycle.current_stream.operation_count,
      nonCliffordCount: modularMultiplierLifecycle.current_stream.non_clifford_count,
      scratchObservationCount: modularMultiplierLifecycle.current_stream.scratch_observation_count,
      scratchUniqueWireCount: modularMultiplierLifecycle.current_stream.scratch_unique_wire_count,
      scratchSingleUseWireCount: modularMultiplierLifecycle.current_stream.scratch_single_use_wire_count,
      scratchCleanupObservationCount: modularMultiplierLifecycle.current_stream.scratch_cleanup_observation_count,
      scratchAbandonedGarbageCount: modularMultiplierLifecycle.current_stream.scratch_abandoned_garbage_count,
      partialProductScratchObservationCount: modularMultiplierLifecycle.current_stream.partial_product_scratch_observation_count,
      nonPartialProductScratchObservationCount: modularMultiplierLifecycle.current_stream.non_partial_product_scratch_observation_count,
      physicalLifecycleStatus: modularMultiplierLifecycle.current_stream.physical_lifecycle_status,
    },
    streamedCandidate: {
      model: modularMultiplierLifecycle.streamed_lifecycle_candidate.model,
      status: modularMultiplierLifecycle.streamed_lifecycle_candidate.status,
      temporaryAndComputeEvents: modularMultiplierLifecycle.streamed_lifecycle_candidate.temporary_and_compute_events,
      requiredConsumeEvents: modularMultiplierLifecycle.streamed_lifecycle_candidate.required_consume_events,
      requiredCleanupEvents: modularMultiplierLifecycle.streamed_lifecycle_candidate.required_cleanup_events,
      peakTemporaryAndWiresIfSerialized: modularMultiplierLifecycle.streamed_lifecycle_candidate.peak_temporary_and_wires_if_serialized,
      additionalMeasurementsForMeasuredCleanup: modularMultiplierLifecycle.streamed_lifecycle_candidate.additional_measurements_for_measured_cleanup,
      notes: modularMultiplierLifecycle.streamed_lifecycle_candidate.notes,
    },
    candidateStream: {
      eventCount: modularMultiplierLifecycle.candidate_lifecycle_stream.event_count,
      temporaryAndComputeEvents: modularMultiplierLifecycle.candidate_lifecycle_stream.temporary_and_compute_events,
      consumeEvents: modularMultiplierLifecycle.candidate_lifecycle_stream.consume_events,
      cleanupEvents: modularMultiplierLifecycle.candidate_lifecycle_stream.cleanup_events,
      segmentCount: modularMultiplierLifecycle.candidate_lifecycle_stream.segment_count,
      routeKindCounts: modularMultiplierLifecycle.candidate_lifecycle_stream.route_kind_counts,
      routeStatusCounts: modularMultiplierLifecycle.candidate_lifecycle_stream.route_status_counts,
      routeSummary: modularMultiplierLifecycle.candidate_lifecycle_stream.route_summary,
    },
  },
  optimizationMission: {
    target: hybridBridgeSearch.target,
    status: hybridBridgeSearch.status,
    sourceStrictResult: hybridBridgeSearch.source_strict_result,
    candidateRows: hybridBridgeSearch.candidate_rows,
    sixSlotLookupTradeoff: hybridBridgeSearch.strict_lookup_chunk_tradeoff_for_six_slots,
    nextRequiredBreakthrough: hybridBridgeSearch.next_required_breakthrough,
  },
  pointAddBoundary: {
    lookupFedLeaf: {
      total: lookupFedLeafEquivalence.summary.total,
      pass: lookupFedLeafEquivalence.summary.pass,
      categories: lookupFedLeafEquivalence.summary.categories,
    },
    streamedLookupTailLeaf: {
      total: streamedLookupTailLeafEquivalence.summary.total,
      pass: streamedLookupTailLeafEquivalence.summary.pass,
      categories: streamedLookupTailLeafEquivalence.summary.categories,
    },
  },
  googleBaseline: googleBaseline.lines,
  baselineRows: [
    {
      id: 'google_low_qubit',
      label: 'Google low-qubit public line',
      status: 'external_public_baseline',
      logicalQubits: googleBaseline.lines.low_qubit.logical_qubits,
      nonClifford: googleBaseline.lines.low_qubit.non_clifford,
      note: 'Rounded public Google/Babbush et al. 2026 comparison line.',
    },
    {
      id: 'google_low_gate',
      label: 'Google low-gate public line',
      status: 'external_public_baseline',
      logicalQubits: googleBaseline.lines.low_gate.logical_qubits,
      nonClifford: googleBaseline.lines.low_gate.non_clifford,
      note: 'Rounded public Google/Babbush et al. 2026 comparison line.',
    },
    {
      id: 'repo_frontier_reference',
      label: 'Repo older exact-family reference',
      status: 'reference_boundary_not_accepted',
      logicalQubits: frontierReference.total_logical_qubits,
      nonClifford: frontierReference.full_oracle_non_clifford,
      note: 'Interesting exact-family boundary retained for study; not the accepted physical baseline.',
    },
    {
      id: 'repo_macro_wrapper_reference',
      label: 'Repo macro/ZKP wrapper reference',
      status: publicHeadlineResult.legacy_wrapper_reference.status,
      logicalQubits: publicHeadlineResult.legacy_wrapper_reference.selected_result.logical_qubits,
      nonClifford: publicHeadlineResult.legacy_wrapper_reference.selected_result.non_clifford,
      note: publicHeadlineResult.legacy_wrapper_reference.reason,
    },
    {
      id: 'repo_strict_candidate',
      label: 'Current strict candidate',
      status: baselineStatus.current_strict_candidate.status,
      logicalQubits: baselineStatus.current_strict_candidate.logical_qubits,
      nonClifford: baselineStatus.current_strict_candidate.non_clifford,
      note: 'Strict replayed-tail candidate; not accepted as physical baseline.',
    },
    {
      id: 'repo_guard_corrected',
      label: 'Guard-corrected no-alias consequence',
      status: baselineStatus.guard_corrected_no_alias_candidate.status,
      logicalQubits: baselineStatus.guard_corrected_no_alias_candidate.logical_qubits,
      nonClifford: baselineStatus.guard_corrected_no_alias_candidate.non_clifford,
      note: 'Conservative consequence if the zero-lift guard clean-ladder workspace is not aliased.',
    },
  ],
};

const output = resolve(root, 'education/src/generated/project-data.json');
mkdirSync(dirname(output), { recursive: true });
writeFileSync(output, `${JSON.stringify(payload, null, 2)}\n`);
