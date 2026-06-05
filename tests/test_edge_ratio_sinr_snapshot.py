import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class EdgeRatioSinrSnapshotScriptTests(unittest.TestCase):
    def test_render_script_writes_snapshot_artifacts_for_existing_output_dir(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        source_output_dir = (
            repo_root
            / "outputs"
            / "edge_ratio_random_pdb_32users_packet_sweep_avg10_20260423_190938"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / source_output_dir.name
            shutil.copytree(source_output_dir, output_dir)

            result = subprocess.run(
                [
                    "python",
                    "scripts/render_edge_ratio_sinr_snapshot.py",
                    str(output_dir),
                ],
                cwd=repo_root,
                env={**os.environ, "PYTHONPATH": "src"},
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=f"stderr:\n{result.stderr}")

            csv_path = output_dir / "sinr_snapshot_by_ratio.csv"
            json_path = output_dir / "sinr_snapshot_by_ratio.json"
            report_path = output_dir / "sinr_snapshot_report.md"
            self.assertTrue(csv_path.exists(), msg=f"missing: {csv_path}")
            self.assertTrue(json_path.exists(), msg=f"missing: {json_path}")
            self.assertTrue(report_path.exists(), msg=f"missing: {report_path}")
            self.assertIn(str(report_path), result.stdout)

            report_text = report_path.read_text(encoding="utf-8")
            self.assertIn("10% Edge Ratio", report_text)
            self.assertIn("50% Edge Ratio", report_text)

            csv_text = csv_path.read_text(encoding="utf-8")
            self.assertIn("initial_sinr_db", csv_text)


if __name__ == "__main__":
    unittest.main()
