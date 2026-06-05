import tempfile
import unittest
from pathlib import Path

from scripts.run_edge_ratio_packet_sweep_report import (
    _aggregate_policy_rows,
    _build_edge_user_rows,
    _write_outputs,
)
from scheduling_sim.metrics import MetricsCollector
from scheduling_sim.models import CurrentRadioState, LogicalChannel, RadioProfile, TrafficProfile, UserEquipment


class EdgeRatioPacketSweepReportTests(unittest.TestCase):
    def test_build_edge_user_rows_appends_radio_fields_and_leaves_null_pdb_blank(self) -> None:
        collector = MetricsCollector()
        pdb_user = UserEquipment(
            ue_id="edge-0",
            lc=LogicalChannel(lc_id="edge-0-lc", packets=[]),
            is_edge_user=True,
            radio_profile=RadioProfile(
                user_class="edge",
                base_snr_db=0.0,
                snr_min_db=-10.0,
                snr_max_db=10.0,
                distance_to_bs_m=420.0,
                edge_per_u_slot_prb_cap=273,
                bits_per_prb=10,
                per_u_slot_prb_cap=273,
            ),
            average_throughput=1.0,
            traffic_profile=TrafficProfile(packet_bits=80000, pdb_ms=400),
            current_radio_state=CurrentRadioState(snr_db=3.5, mcs_index=5, bits_per_prb=158, per_u_slot_prb_cap=273),
        )
        null_user = UserEquipment(
            ue_id="edge-1",
            lc=LogicalChannel(lc_id="edge-1-lc", packets=[]),
            is_edge_user=True,
            radio_profile=RadioProfile(
                user_class="edge",
                base_snr_db=0.0,
                snr_min_db=-10.0,
                snr_max_db=10.0,
                distance_to_bs_m=460.0,
                edge_per_u_slot_prb_cap=273,
                bits_per_prb=10,
                per_u_slot_prb_cap=273,
            ),
            average_throughput=1.0,
            traffic_profile=TrafficProfile(packet_bits=80000, pdb_ms=None),
            current_radio_state=CurrentRadioState(snr_db=-2.0, mcs_index=3, bits_per_prb=68, per_u_slot_prb_cap=273),
        )
        collector.record_radio_state(pdb_user)
        collector.record_radio_state(null_user)
        collector.record_packet_completed(
            packet_id="edge-0-target",
            completion_time=55,
            arrival_time=0,
            pdb_ms=400,
            bits_sent=80000,
            user_class="edge",
            ue_id="edge-0",
            is_target=False,
            first_service_time=12,
            service_slot_count=14,
            control_slot_count_while_pending=22,
            waiting_u_slot_count_before_first_service=6,
            waiting_u_slot_count_after_first_service=13,
        )
        collector.record_bits_served(user_class="edge", bits_sent=80000, ue_id="edge-0")
        collector.record_bits_served(user_class="edge", bits_sent=480960, ue_id="edge-1")

        rows = _build_edge_user_rows(
            users=[pdb_user, null_user],
            collector=collector,
            requested_edge_ratio_pct=10,
            total_users=32,
            repeat_index=0,
            policy="tail_append",
            pdb_packet_kb=10,
            pdb_mode="random",
            uniform_pdb_ms=None,
        )

        self.assertEqual(rows[0]["initial_sinr_db"], 3.5)
        self.assertEqual(rows[0]["sinr_mean_db"], 3.5)
        self.assertEqual(rows[0]["distance_to_bs_m"], 420.0)
        self.assertEqual(rows[0]["queue_time_ms"], 41)
        self.assertEqual(rows[1]["pdb_setting"], "null")
        self.assertEqual(rows[1]["completed"], "")
        self.assertEqual(rows[1]["delay_ms"], "")
        self.assertEqual(rows[1]["served_bits"], 480960)

    def test_aggregate_policy_rows_preserves_mode_specific_columns(self) -> None:
        rows = [
            {
                "pdb_mode": "uniform",
                "uniform_pdb_ms": 200,
                "pdb_packet_kb": 200,
                "pdb_packet_bits": 1600000,
                "requested_edge_ratio_pct": 20,
                "actual_scanned_edge_ratio_pct": 18.75,
                "total_users": 32,
                "scanned_edge_user_count": 6,
                "non_pdb_user_count": 26,
                "pdb_user_count": 6,
                "repeat_index": 0,
                "policy": "tail_append",
                "pdb_user_satisfaction_rate": 0.5,
                "non_pdb_agg_throughput_bps": 2500000.0,
                "non_pdb_avg_user_throughput_bps": 96153.8,
                "cell_total_throughput_bps": 2600000.0,
                "pdb_edge_agg_throughput_bps": 100000.0,
                "prb_utilization": 0.3,
                "analysis_window_ms": 5000.0,
                "assigned_null_count": 0,
                "assigned_200_count": 6,
                "assigned_400_count": 0,
                "assigned_600_count": 0,
                "assigned_800_count": 0,
            },
            {
                "pdb_mode": "uniform",
                "uniform_pdb_ms": 200,
                "pdb_packet_kb": 200,
                "pdb_packet_bits": 1600000,
                "requested_edge_ratio_pct": 20,
                "actual_scanned_edge_ratio_pct": 18.75,
                "total_users": 32,
                "scanned_edge_user_count": 6,
                "non_pdb_user_count": 26,
                "pdb_user_count": 6,
                "repeat_index": 1,
                "policy": "tail_append",
                "pdb_user_satisfaction_rate": 0.75,
                "non_pdb_agg_throughput_bps": 2550000.0,
                "non_pdb_avg_user_throughput_bps": 98076.9,
                "cell_total_throughput_bps": 2650000.0,
                "pdb_edge_agg_throughput_bps": 100000.0,
                "prb_utilization": 0.32,
                "analysis_window_ms": 5000.0,
                "assigned_null_count": 0,
                "assigned_200_count": 6,
                "assigned_400_count": 0,
                "assigned_600_count": 0,
                "assigned_800_count": 0,
            },
        ]

        averaged = _aggregate_policy_rows(rows)

        self.assertEqual(averaged[0]["pdb_mode"], "uniform")
        self.assertEqual(averaged[0]["uniform_pdb_ms"], 200)
        self.assertEqual(averaged[0]["repeat_count"], 2)
        self.assertEqual(averaged[0]["assigned_200_count_mean"], 6.0)

    def test_write_outputs_creates_summary_and_user_files(self) -> None:
        summary_policy_per_repeat = [
            {
                "pdb_mode": "random",
                "uniform_pdb_ms": "",
                "pdb_packet_kb": 200,
                "pdb_packet_bits": 1600000,
                "requested_edge_ratio_pct": 20,
                "actual_scanned_edge_ratio_pct": 18.75,
                "total_users": 32,
                "scanned_edge_user_count": 6,
                "non_pdb_user_count": 27,
                "pdb_user_count": 5,
                "repeat_index": 0,
                "policy": "tail_append",
                "pdb_user_satisfaction_rate": 0.4,
                "non_pdb_agg_throughput_bps": 2500000.0,
                "non_pdb_avg_user_throughput_bps": 92592.59,
                "cell_total_throughput_bps": 2600000.0,
                "pdb_edge_agg_throughput_bps": 100000.0,
                "prb_utilization": 0.3,
                "analysis_window_ms": 5000.0,
                "assigned_null_count": 1,
                "assigned_200_count": 2,
                "assigned_400_count": 1,
                "assigned_600_count": 1,
                "assigned_800_count": 1,
            }
        ]
        summary_policy_average = [
            {
                "pdb_mode": "random",
                "uniform_pdb_ms": "",
                "pdb_packet_kb": 200,
                "pdb_packet_bits": 1600000,
                "requested_edge_ratio_pct": 20,
                "actual_scanned_edge_ratio_pct": 18.75,
                "total_users": 32,
                "scanned_edge_user_count": 6,
                "non_pdb_user_count_mean": 27.0,
                "pdb_user_count_mean": 5.0,
                "repeat_count": 1,
                "policy": "tail_append",
                "pdb_user_satisfaction_rate_mean": 0.4,
                "non_pdb_agg_throughput_bps_mean": 2500000.0,
                "non_pdb_avg_user_throughput_bps_mean": 92592.59,
                "cell_total_throughput_bps_mean": 2600000.0,
                "pdb_edge_agg_throughput_bps_mean": 100000.0,
                "prb_utilization_mean": 0.3,
                "analysis_window_ms_mean": 5000.0,
                "assigned_null_count_mean": 1.0,
                "assigned_200_count_mean": 2.0,
                "assigned_400_count_mean": 1.0,
                "assigned_600_count_mean": 1.0,
                "assigned_800_count_mean": 1.0,
            }
        ]
        summary_gain_average = [
            {
                "pdb_mode": "random",
                "uniform_pdb_ms": "",
                "pdb_packet_kb": 200,
                "pdb_packet_bits": 1600000,
                "requested_edge_ratio_pct": 20,
                "actual_scanned_edge_ratio_pct": 18.75,
                "total_users": 32,
                "scanned_edge_user_count": 6,
                "non_pdb_user_count_mean": 27.0,
                "pdb_user_count_mean": 5.0,
                "repeat_count": 1,
                "baseline_policy": "tail_append",
                "ours_policy": "business_aware_constrained_insert",
                "baseline_pdb_satisfaction_rate_mean": 0.4,
                "ours_pdb_satisfaction_rate_mean": 0.6,
                "pdb_satisfaction_delta_pct_points_mean": 20.0,
                "baseline_non_pdb_agg_throughput_bps_mean": 2500000.0,
                "ours_non_pdb_agg_throughput_bps_mean": 2450000.0,
                "non_pdb_agg_throughput_delta_bps_mean": -50000.0,
                "non_pdb_agg_throughput_delta_pct_mean": -2.0,
                "baseline_cell_total_throughput_bps_mean": 2600000.0,
                "ours_cell_total_throughput_bps_mean": 2550000.0,
                "cell_total_throughput_gain_bps_mean": -50000.0,
                "cell_total_throughput_gain_pct_mean": -1.92,
            }
        ]
        user_rows = [
            {
                "pdb_mode": "random",
                "uniform_pdb_ms": "",
                "pdb_packet_kb": 200,
                "requested_edge_ratio_pct": 20,
                "actual_scanned_edge_ratio_pct": 18.75,
                "total_users": 32,
                "scanned_edge_user_count": 6,
                "non_pdb_user_count": 27,
                "repeat_index": 0,
                "policy": "tail_append",
                "ue_id": "edge-0",
                "pdb_setting": "200",
                "pdb_ms": 200,
                "completed": True,
                "delay_ms": 120,
                "queue_time_ms": 90,
                "service_time_ms": 30,
                "pdb_met": True,
                "served_bits": 1600000,
                "remaining_bits": 0,
                "distance_to_bs_m": 420.0,
                "initial_sinr_db": 3.5,
                "sinr_mean_db": 4.1,
                "sinr_min_db": 3.5,
                "sinr_max_db": 4.8,
                "initial_mcs_index": 5,
                "initial_bits_per_prb": 158,
            }
        ]

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            _write_outputs(
                output_dir=output_dir,
                manifest={"pdb_mode": "random", "pdb_packet_kb_values": [200]},
                pdb_assignments={"200": {"20": {"0": {"pdb_by_ue": {"edge-0": 200}}}}},
                raw_summaries=[
                    {
                        "pdb_packet_kb": 200,
                        "requested_edge_ratio_pct": 20,
                        "repeat_index": 0,
                        "policy": "tail_append",
                        "summary": {"analysis_window_ms": 5000.0},
                    }
                ],
                summary_policy_per_repeat=summary_policy_per_repeat,
                summary_policy_average=summary_policy_average,
                summary_gain_average=summary_gain_average,
                user_rows=user_rows,
            )
            self.assertTrue((output_dir / "experiment_manifest.json").exists())
            self.assertTrue((output_dir / "pdb_assignments.json").exists())
            self.assertTrue((output_dir / "raw_simulator_summaries.json").exists())
            self.assertTrue((output_dir / "summary_policy_per_repeat.csv").exists())
            self.assertTrue((output_dir / "summary_policy_average.csv").exists())
            self.assertTrue((output_dir / "summary_gain_average.csv").exists())
            self.assertTrue((output_dir / "user_report.csv").exists())
            self.assertTrue((output_dir / "user_reports_by_repeat" / "repeat_00.csv").exists())


if __name__ == "__main__":
    unittest.main()
