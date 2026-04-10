import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class CliSmokeTests(unittest.TestCase):
    def test_run_command_prints_output_path(self) -> None:
        payload = {
            "simulation": {"cycles": 1, "slot_duration_ms": 1, "tdd_pattern": "DSUUU"},
            "resources": {"total_prb_per_u_slot": 10, "max_ue_per_slot": 4},
            "traffic": {
                "center": {"count": 1, "period_slots": 1, "packet_bits": 40, "pdb_ms": 30},
                "edge": {"count": 1, "burst_cycle_interval": 1, "packet_bits": 100, "pdb_ms": 15},
            },
            "radio": {
                "center": {"bits_per_prb": 20, "per_u_slot_prb_cap": 10},
                "edge": {"bits_per_prb": 10, "per_u_slot_prb_cap": 4},
            },
            "scheduler": {"ranking": "epf", "reinsert_policy": "tail_append"},
            "report": {"output_dir": "outputs/smoke", "keep_slot_trace": False},
        }
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            config_path.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                ["python", "-m", "scheduling_sim.cli", "run", str(config_path)],
                cwd=Path(__file__).resolve().parents[1],
                env={**os.environ, "PYTHONPATH": "src"},
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Report written to", result.stdout)


if __name__ == "__main__":
    unittest.main()
