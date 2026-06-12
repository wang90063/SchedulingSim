import csv
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


def _load_render_module():
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "render_systematic_simulation_analysis_plots.py"
    spec = importlib.util.spec_from_file_location("render_systematic_simulation_analysis_plots", script_path)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load render script module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SystematicAnalysisPlotTests(unittest.TestCase):
    def test_representative_metric_specs_keep_one_metric_per_axis(self) -> None:
        module = _load_render_module()
        metric_specs = module._representative_case_metric_specs()
        self.assertEqual(len(metric_specs), 9)
        self.assertTrue(all(len(spec["metrics"]) == 1 for spec in metric_specs))

    def test_render_script_writes_overview_cost_and_boundary_plots(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            (output_dir / "experiment_manifest.json").write_text(
                json.dumps(
                    {
                        "background_user_count_values": [24, 36, 48],
                        "pdb_user_count_values": [4, 10, 16],
                        "pdb_ms_values": [100, 300, 500],
                        "pdb_packet_kb_values": [50, 150, 300],
                    }
                ),
                encoding="utf-8",
            )
            with (output_dir / "scene_summary.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "background_user_count",
                        "pdb_user_count",
                        "pdb_ms",
                        "pdb_packet_kb",
                        "mean_delta_pdb_satisfaction_rate",
                        "mean_center_throughput_retention",
                        "baseline_edge_pdb_satisfaction_rate",
                        "proposed_edge_pdb_satisfaction_rate",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "background_user_count": 24,
                        "pdb_user_count": 4,
                        "pdb_ms": 100,
                        "pdb_packet_kb": 50,
                        "mean_delta_pdb_satisfaction_rate": 0.20,
                        "mean_center_throughput_retention": 0.95,
                        "baseline_edge_pdb_satisfaction_rate": 0.80,
                        "proposed_edge_pdb_satisfaction_rate": 1.00,
                    }
                )
            for threshold in ("95", "90"):
                with (output_dir / f"capacity_summary_{threshold}.csv").open(
                    "w",
                    encoding="utf-8",
                    newline="",
                ) as handle:
                    writer = csv.DictWriter(
                        handle,
                        fieldnames=[
                            "dimension",
                            "background_user_count",
                            "pdb_user_count",
                            "pdb_ms",
                            "pdb_packet_kb",
                            "threshold",
                            "capacity_gain_pdb_users",
                            "capacity_gain_background_users",
                        ],
                    )
                    writer.writeheader()
                    writer.writerow(
                        {
                            "dimension": "fixed_background_user_count",
                            "background_user_count": 24,
                            "pdb_user_count": "",
                            "pdb_ms": 100,
                            "pdb_packet_kb": 50,
                            "threshold": float(f"0.{threshold}"),
                            "capacity_gain_pdb_users": 6,
                            "capacity_gain_background_users": "",
                        }
                    )
            with (output_dir / "boundary_feasibility_95.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "background_user_count",
                        "pdb_user_count",
                        "pdb_ms",
                        "pdb_packet_kb",
                        "threshold",
                        "baseline_feasible",
                        "proposed_feasible",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "background_user_count": 24,
                        "pdb_user_count": 4,
                        "pdb_ms": 100,
                        "pdb_packet_kb": 50,
                        "threshold": 0.95,
                        "baseline_feasible": 0,
                        "proposed_feasible": 1,
                    }
                )
            with (output_dir / "boundary_feasibility_90.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "background_user_count",
                        "pdb_user_count",
                        "pdb_ms",
                        "pdb_packet_kb",
                        "threshold",
                        "baseline_feasible",
                        "proposed_feasible",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "background_user_count": 24,
                        "pdb_user_count": 4,
                        "pdb_ms": 100,
                        "pdb_packet_kb": 50,
                        "threshold": 0.90,
                        "baseline_feasible": 1,
                        "proposed_feasible": 1,
                    }
                )
            with (output_dir / "typical_case_details.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "case_label",
                        "policy",
                        "background_user_count",
                        "pdb_user_count",
                        "pdb_ms",
                        "pdb_packet_kb",
                        "edge_pdb_satisfaction_rate",
                        "center_agg_rate_bps",
                        "center_avg_rate_bps",
                        "prb_utilization",
                        "center_prb_share",
                        "edge_prb_share",
                        "pdb_arrivals_in_window",
                        "pdb_violation_rate",
                        "target_edge_completion_delay_ms",
                        "target_edge_queue_wait_ms",
                        "target_edge_service_time_ms",
                        "edge_backlog_bits",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "case_label": "critical",
                        "policy": "tail_append",
                        "background_user_count": 24,
                        "pdb_user_count": 4,
                        "pdb_ms": 100,
                        "pdb_packet_kb": 50,
                        "edge_pdb_satisfaction_rate": 0.80,
                        "center_agg_rate_bps": 1000.0,
                        "center_avg_rate_bps": 50.0,
                        "prb_utilization": 0.70,
                        "center_prb_share": 0.60,
                        "edge_prb_share": 0.40,
                        "pdb_arrivals_in_window": 8.0,
                        "pdb_violation_rate": 0.20,
                        "target_edge_completion_delay_ms": 90.0,
                        "target_edge_queue_wait_ms": 55.0,
                        "target_edge_service_time_ms": 35.0,
                        "edge_backlog_bits": 0.0,
                    }
                )
                writer.writerow(
                    {
                        "case_label": "critical",
                        "policy": "hopeless_front_insert",
                        "background_user_count": 24,
                        "pdb_user_count": 4,
                        "pdb_ms": 100,
                        "pdb_packet_kb": 50,
                        "edge_pdb_satisfaction_rate": 0.95,
                        "center_agg_rate_bps": 950.0,
                        "center_avg_rate_bps": 47.5,
                        "prb_utilization": 0.75,
                        "center_prb_share": 0.55,
                        "edge_prb_share": 0.45,
                        "pdb_arrivals_in_window": 8.0,
                        "pdb_violation_rate": 0.05,
                        "target_edge_completion_delay_ms": 80.0,
                        "target_edge_queue_wait_ms": 45.0,
                        "target_edge_service_time_ms": 35.0,
                        "edge_backlog_bits": 0.0,
                    }
                )
                writer.writerow(
                    {
                        "case_label": "overloaded",
                        "policy": "tail_append",
                        "background_user_count": 36,
                        "pdb_user_count": 10,
                        "pdb_ms": 300,
                        "pdb_packet_kb": 150,
                        "edge_pdb_satisfaction_rate": 0.10,
                        "center_agg_rate_bps": 700.0,
                        "center_avg_rate_bps": 29.2,
                        "prb_utilization": 0.92,
                        "center_prb_share": 0.30,
                        "edge_prb_share": 0.70,
                        "pdb_arrivals_in_window": 8.0,
                        "pdb_violation_rate": 0.90,
                        "target_edge_completion_delay_ms": 430.0,
                        "target_edge_queue_wait_ms": 300.0,
                        "target_edge_service_time_ms": 130.0,
                        "edge_backlog_bits": 120000.0,
                    }
                )
                writer.writerow(
                    {
                        "case_label": "overloaded",
                        "policy": "hopeless_front_insert",
                        "background_user_count": 36,
                        "pdb_user_count": 10,
                        "pdb_ms": 300,
                        "pdb_packet_kb": 150,
                        "edge_pdb_satisfaction_rate": 0.25,
                        "center_agg_rate_bps": 640.0,
                        "center_avg_rate_bps": 26.7,
                        "prb_utilization": 0.95,
                        "center_prb_share": 0.25,
                        "edge_prb_share": 0.75,
                        "pdb_arrivals_in_window": 8.0,
                        "pdb_violation_rate": 0.75,
                        "target_edge_completion_delay_ms": 390.0,
                        "target_edge_queue_wait_ms": 270.0,
                        "target_edge_service_time_ms": 120.0,
                        "edge_backlog_bits": 90000.0,
                    }
                )
            result = subprocess.run(
                ["python", "scripts/render_systematic_simulation_analysis_plots.py", str(output_dir)],
                cwd=repo_root,
                env={**os.environ, "PYTHONPATH": "src"},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue((output_dir / "overview_delta_pdb_satisfaction.png").exists())
            self.assertTrue((output_dir / "center_throughput_retention.png").exists())
            self.assertTrue((output_dir / "capacity_boundary_95.png").exists())
            self.assertTrue((output_dir / "capacity_boundary_90.png").exists())
            self.assertTrue((output_dir / "typical_case_critical.png").exists())
            self.assertTrue((output_dir / "typical_case_overloaded.png").exists())


if __name__ == "__main__":
    unittest.main()
