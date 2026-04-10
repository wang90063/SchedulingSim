import os
import subprocess
import unittest
from pathlib import Path


class CliSmokeTests(unittest.TestCase):
    def test_run_command_writes_report_file(self) -> None:
        result = subprocess.run(
            ["python", "-m", "scheduling_sim.cli", "run", "configs/edge_compare.json"],
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ, "PYTHONPATH": "src"},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("report.json", result.stdout)


if __name__ == "__main__":
    unittest.main()
