import json
import tempfile
import unittest
from pathlib import Path

from scheduling_sim.config import load_config
from scheduling_sim.planning import PhasePrbPlanner
from scheduling_sim.scenario import ScenarioFactory


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
        self.assertEqual(config.radio.center.bits_per_prb, 20)
        self.assertEqual(config.radio.edge.per_u_slot_prb_cap, 18)

    def test_loads_radio_environment_and_edge_only_cap(self) -> None:
        payload = {
            "simulation": {"cycles": 2, "slot_duration_ms": 1, "tdd_pattern": "DSUUU", "random_seed": 7},
            "resources": {"total_prb_per_u_slot": 24, "max_ue_per_slot": 8},
            "traffic": {
                "center": {"count": 2, "period_slots": 1, "packet_bits": 120, "pdb_ms": 30},
                "edge": {"count": 1, "burst_cycle_interval": 2, "packet_bits": 2400, "pdb_ms": 15}
            },
            "radio": {
                "environment": {
                    "alpha": 0.9,
                    "jitter_std_db": 0.5,
                    "mcs_table": [
                        {"snr_db": 0.0, "mcs_index": 0, "bits_per_prb": 4},
                        {"snr_db": 6.0, "mcs_index": 1, "bits_per_prb": 8},
                        {"snr_db": 12.0, "mcs_index": 2, "bits_per_prb": 14}
                    ]
                },
                "center": {"base_snr_db": 16.0, "snr_min_db": 10.0, "snr_max_db": 22.0},
                "edge": {
                    "base_snr_db": 4.0,
                    "snr_min_db": -2.0,
                    "snr_max_db": 8.0,
                    "edge_per_u_slot_prb_cap": 6,
                },
            },
            "scheduler": {"ranking": "epf", "reinsert_policy": "constrained_insert"},
            "report": {"output_dir": "outputs/demo", "keep_slot_trace": False},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            config = load_config(path)
        self.assertEqual(config.radio.environment.alpha, 0.9)
        self.assertEqual(config.radio.center.base_snr_db, 16.0)
        self.assertIsNone(config.radio.center.edge_per_u_slot_prb_cap)
        self.assertEqual(config.radio.edge.edge_per_u_slot_prb_cap, 6)
        self.assertEqual(config.radio.environment.mcs_table[-1].bits_per_prb, 14)

        users = ScenarioFactory(config).build_users()
        center_user = next(user for user in users if not user.is_edge_user)
        edge_user = next(user for user in users if user.is_edge_user)
        self.assertIsInstance(center_user.radio_profile.bits_per_prb, int)
        self.assertIsInstance(edge_user.radio_profile.bits_per_prb, int)
        self.assertGreater(center_user.radio_profile.per_u_slot_prb_cap, 0)
        self.assertEqual(edge_user.radio_profile.per_u_slot_prb_cap, 6)
        center_plan = PhasePrbPlanner(total_prb_per_u_slot=8).plan_phase("D", [center_user])
        edge_plan = PhasePrbPlanner(total_prb_per_u_slot=8).plan_phase("D", [edge_user])
        self.assertEqual(center_plan.slot_grants[0][0].bits_planned, center_user.radio_profile.bits_per_prb * 8)
        self.assertEqual(edge_plan.slot_grants[0][0].bits_planned, edge_user.radio_profile.bits_per_prb * 6)


if __name__ == "__main__":
    unittest.main()
