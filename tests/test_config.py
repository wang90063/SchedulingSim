import json
import tempfile
import unittest
from pathlib import Path

from scheduling_sim.config import load_config


class ConfigLoaderTests(unittest.TestCase):
    def test_loads_edge_compare_config(self) -> None:
        payload = {
            "simulation": {"cycles": 2, "slot_duration_ms": 1, "tdd_pattern": "DSUUU"},
            "resources": {"total_prb_per_u_slot": 106, "max_ue_per_slot": 16},
            "traffic": {
                "center": {"count": 60, "period_slots": 1, "packet_bits": 200, "pdb_ms": 30},
                "edge": {"count": 4, "burst_cycle_interval": 3, "packet_bits": 40000, "pdb_ms": 15},
            },
            "radio": {
                "center": {"bits_per_prb": 20, "per_u_slot_prb_cap": 106},
                "edge": {"bits_per_prb": 10, "per_u_slot_prb_cap": 18},
            },
            "scheduler": {"ranking": "epf", "reinsert_policy": "tail_append"},
            "report": {"output_dir": "outputs/demo", "keep_slot_trace": True},
        }
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            config_path.write_text(json.dumps(payload), encoding="utf-8")
            config = load_config(config_path)
        self.assertEqual(config.simulation.tdd_pattern, "DSUUU")
        self.assertEqual(config.traffic.edge.count, 4)
        self.assertEqual(config.radio.edge.per_u_slot_prb_cap, 18)


if __name__ == "__main__":
    unittest.main()
