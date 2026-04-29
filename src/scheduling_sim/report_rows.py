COMMON_SUMMARY_ROW_FIELDS: tuple[str, ...] = (
    "target_edge_finished",
    "target_edge_completion_delay_ms",
    "target_edge_queue_wait_ms",
    "target_edge_service_time_ms",
    "target_edge_control_phase_wait_ms",
    "target_edge_pre_first_service_wait_ms",
    "target_edge_inter_service_gap_wait_ms",
    "target_edge_time_to_first_service_ms",
    "target_edge_pdb_met",
    "target_edge_remaining_bits",
    "center_avg_rate_bps",
    "prb_utilization",
    "analysis_window_ms",
    "center_total_bits",
    "edge_total_bits",
    "target_edge_total_bits",
    "system_total_bits",
    "center_agg_rate_bps",
    "edge_agg_rate_bps",
    "target_edge_rate_bps",
    "system_agg_rate_bps",
    "center_used_prb",
    "edge_used_prb",
    "center_prb_share",
    "edge_prb_share",
    "center_bits_per_used_prb",
    "edge_bits_per_used_prb",
)

BOOLEAN_SUMMARY_ROW_FIELDS = frozenset({"target_edge_finished", "target_edge_pdb_met"})


def build_common_summary_row(summary: dict[str, float | int | bool]) -> dict[str, float | int | bool]:
    return {
        field: bool(summary[field]) if field in BOOLEAN_SUMMARY_ROW_FIELDS else summary[field]
        for field in COMMON_SUMMARY_ROW_FIELDS
    }
