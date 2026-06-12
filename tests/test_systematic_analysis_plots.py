import csv
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class SystematicAnalysisPlotTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
