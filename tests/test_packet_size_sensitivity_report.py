import tempfile
import unittest
from pathlib import Path

from scripts.run_target_edge_packet_size_sensitivity_report import (
    _build_row,
    _write_outputs,
    _write_markdown_report,
)


SUMMARY = {
    "target_edge_finished": True,
    "target_edge_completion_delay_ms": 10.0,
    "target_edge_queue_wait_ms": 4.0,
    "target_edge_service_time_ms": 6.0,
    "target_edge_control_phase_wait_ms": 2.0,
    "target_edge_pre_first_service_wait_ms": 1.0,
    "target_edge_inter_service_gap_wait_ms": 1.0,
    "target_edge_time_to_first_service_ms": 3.0,
    "target_edge_pdb_met": True,
    "target_edge_remaining_bits": 0.0,
    "center_avg_rate_bps": 100.0,
    "prb_utilization": 0.5,
    "analysis_window_ms": 10.0,
    "center_total_bits": 1000.0,
    "edge_total_bits": 3200000.0,
    "target_edge_total_bits": 3200000.0,
    "system_total_bits": 3201000.0,
    "center_agg_rate_bps": 100000.0,
    "edge_agg_rate_bps": 320000000.0,
    "target_edge_rate_bps": 320000000.0,
    "system_agg_rate_bps": 320100000.0,
    "center_used_prb": 10.0,
    "edge_used_prb": 20.0,
    "center_prb_share": 0.33,
    "edge_prb_share": 0.67,
    "center_bits_per_used_prb": 100.0,
    "edge_bits_per_used_prb": 160000.0,
}


class PacketSizeSensitivityReportTests(unittest.TestCase):
    def test_report_and_rows_use_configured_prb_and_center_pdb_metadata(self) -> None:
        payload = {
            "resources": {"total_prb_per_u_slot": 273},
            "traffic": {
                "center": {"count": 63, "pdb_ms": None},
                "edge": {"pdb_ms": 500},
            },
            "radio": {"edge": {"edge_per_u_slot_prb_cap": 273}},
            "sweep": {"edge_packet_kb": [400]},
        }
        rows = [
            _build_row(
                edge_packet_kb=400,
                dimension="edge_pdb_ms",
                value=500,
                policy="tail_append",
                summary=SUMMARY,
                config_metadata={
                    "total_prb_per_u_slot": 273,
                    "center_pdb_ms": None,
                    "edge_per_u_slot_prb_cap": 273,
                },
            ),
            _build_row(
                edge_packet_kb=400,
                dimension="edge_pdb_ms",
                value=500,
                policy="business_aware_constrained_insert",
                summary=SUMMARY,
                config_metadata={
                    "total_prb_per_u_slot": 273,
                    "center_pdb_ms": None,
                    "edge_per_u_slot_prb_cap": 273,
                },
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            _write_markdown_report(payload, output_dir, rows)
            _write_outputs(output_dir, rows)
            report_text = (output_dir / "sensitivity_report.md").read_text(encoding="utf-8")
            rows_text = (output_dir / "sensitivity_rows.csv").read_text(encoding="utf-8")

        self.assertIn("每个 U-slot `273 PRB`", report_text)
        self.assertIn("`edge_per_u_slot_prb_cap = 273`", report_text)
        self.assertIn("中心用户 `pdb_ms = null`", report_text)
        self.assertIn("400,3200000,edge_pdb_ms,500,tail_append,273,null,273", rows_text)
        self.assertEqual(rows[0]["total_prb_per_u_slot"], 273)
        self.assertIsNone(rows[0]["center_pdb_ms"])
        self.assertEqual(rows[0]["edge_per_u_slot_prb_cap"], 273)
