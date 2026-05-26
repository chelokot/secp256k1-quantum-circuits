from __future__ import annotations

CANONICAL_MATERIALIZED_FLAT_NETLIST = 'canonical_materialized_flat_netlist'
LEGACY_WRAPPER_MATERIALIZED_FLAT_NETLIST = 'legacy_wrapper_materialized_flat_netlist'
STRICT_REPLAYED_TAIL_MATERIALIZED_FLAT_NETLIST = 'strict_replayed_tail_materialized_flat_netlist'
LEGACY_MATERIALIZED_FLAT_NETLIST = 'materialized_flat_netlist'

PUBLIC_CANDIDATE_CANONICAL_TOTALS_SOURCE = (
    'public_candidate_materialized.canonical_materialized_flat_netlist.non_clifford_count + '
    'canonical_materialized_flat_netlist.peak_live_qubits'
)
PUBLIC_ENGINE_CANONICAL_TOTALS_SOURCE = 'public_candidate_materialized_circuit_manifest.canonical_materialized_flat_netlist'
PUBLIC_ENGINE_LEGACY_TOTALS_SOURCE = 'public_candidate_materialized_circuit_manifest.materialized_flat_netlist'

PUBLIC_TOTALS_DERIVE_FROM_CANONICAL_CHECK = 'public_totals_derive_from_canonical_materialized_flat_netlist'
CANONICAL_FLAT_NETLIST_IS_STRICT_REPLAY_CHECK = 'canonical_materialized_flat_netlist_is_strict_replayed_tail_stream'
PUBLIC_TOTALS_MATCH_CANONICAL_ENGINE_CHECK = 'public_totals_match_canonical_materialized_flat_engine'


__all__ = [
    'CANONICAL_FLAT_NETLIST_IS_STRICT_REPLAY_CHECK',
    'CANONICAL_MATERIALIZED_FLAT_NETLIST',
    'LEGACY_MATERIALIZED_FLAT_NETLIST',
    'LEGACY_WRAPPER_MATERIALIZED_FLAT_NETLIST',
    'PUBLIC_CANDIDATE_CANONICAL_TOTALS_SOURCE',
    'PUBLIC_ENGINE_CANONICAL_TOTALS_SOURCE',
    'PUBLIC_ENGINE_LEGACY_TOTALS_SOURCE',
    'PUBLIC_TOTALS_DERIVE_FROM_CANONICAL_CHECK',
    'PUBLIC_TOTALS_MATCH_CANONICAL_ENGINE_CHECK',
    'STRICT_REPLAYED_TAIL_MATERIALIZED_FLAT_NETLIST',
]
