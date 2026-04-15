import json
import tempfile
import unittest
from pathlib import Path

from scheduling_sim.config import load_config
from scheduling_sim.models import Packet
from scheduling_sim.planning import PhasePrbPlanner
from scheduling_sim.scenario import ScenarioFactory


class ConfigLoaderTests(unittest.TestCase):
    def test_loads_edge_compare_config(self) -> None:
        config_path = Path(__file__).resolve().parents[1] / "configs" / "edge_compare.json"
        config = load_config(config_path)
        self.assertEqual(config.simulation.tdd_pattern, "DSUUU")
        self.assertEqual(config.simulation.random_seed, 7)
        self.assertFalse(config.simulation.stop_when_target_edge_finished)
        self.assertEqual(config.simulation.deadline_guard_ms, 0)
        self.assertEqual(config.traffic.edge.count, 4)
        self.assertEqual(config.traffic.center.gbr_bps, 20000.0)
        self.assertEqual(config.radio.environment.mcs_table[-1].bits_per_prb, 120)
        self.assertEqual(config.radio.environment.scenario_type, "uma")
        self.assertEqual(config.radio.environment.cell_radius_m, 500.0)
        self.assertEqual(config.radio.environment.center_distance_range_m, (50.0, 150.0))
        self.assertEqual(config.radio.environment.edge_distance_range_m, (425.0, 500.0))
        self.assertEqual(config.radio.edge.edge_per_u_slot_prb_cap, 18)

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
        center_user.lc.packets.append(Packet("center-pkt", 0, 120, 120, 30, None))
        edge_user.lc.packets.append(Packet("edge-pkt", 0, 2400, 2400, 15, None))
        center_plan = PhasePrbPlanner(total_prb_per_u_slot=8).plan_phase("D", [center_user])
        edge_plan = PhasePrbPlanner(total_prb_per_u_slot=8).plan_phase("D", [edge_user])
        self.assertEqual(center_plan.slot_grants[0][0].bits_planned, center_user.radio_profile.bits_per_prb * 8)
        self.assertEqual(edge_plan.slot_grants[0][0].bits_planned, edge_user.radio_profile.bits_per_prb * 6)

    def test_load_config_supports_uma_geometry_schema(self) -> None:
        payload = {
            "simulation": {"cycles": 1, "slot_duration_ms": 1, "tdd_pattern": "DSUUU", "random_seed": 7},
            "resources": {"total_prb_per_u_slot": 20, "max_ue_per_slot": 4},
            "traffic": {
                "center": {"count": 1, "period_slots": 1, "packet_bits": 100, "pdb_ms": 30},
                "edge": {"count": 1, "burst_cycle_interval": 1, "packet_bits": 40000, "pdb_ms": 15},
            },
            "radio": {
                "environment": {
                    "scenario_type": "uma",
                    "cell_radius_m": 500,
                    "carrier_frequency_ghz": 3.5,
                    "noise_figure_db": 7.0,
                    "interference_margin_db": 3.0,
                    "shadow_std_db": 4.0,
                    "slow_fading_alpha": 0.95,
                    "slot_jitter_std_db": 0.5,
                    "center_distance_range_m": [50, 150],
                    "edge_distance_range_m": [425, 500],
                    "mcs_table": [
                        {"sinr_db": -5.0, "mcs_index": 0, "bits_per_prb": 24},
                        {"sinr_db": 0.0, "mcs_index": 1, "bits_per_prb": 48},
                    ],
                },
                "center": {},
                "edge": {"edge_per_u_slot_prb_cap": 18},
            },
            "scheduler": {"ranking": "epf", "reinsert_policy": "tail_append"},
            "report": {"output_dir": "outputs/test", "keep_slot_trace": False},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            config = load_config(path)
        self.assertEqual(config.traffic.center.gbr_bps, 0.0)
        self.assertEqual(config.radio.environment.scenario_type, "uma")
        self.assertEqual(config.radio.environment.cell_radius_m, 500.0)
        self.assertEqual(config.radio.environment.center_distance_range_m, (50.0, 150.0))
        self.assertEqual(config.radio.environment.edge_distance_range_m, (425.0, 500.0))
        self.assertEqual(config.radio.environment.mcs_table[-1].bits_per_prb, 48)
        self.assertEqual(config.radio.edge.edge_per_u_slot_prb_cap, 18)

    def test_load_config_supports_external_mcs_table_with_spectral_efficiency(self) -> None:
        payload = {
            "simulation": {
                "cycles": 1,
                "slot_duration_ms": 1,
                "tdd_pattern": "DSUUU",
                "random_seed": 7,
                "stop_when_target_edge_finished": True,
            },
            "resources": {"total_prb_per_u_slot": 237, "max_ue_per_slot": 16},
            "traffic": {
                "center": {"count": 1, "period_slots": 1, "packet_bits": 160, "pdb_ms": 30},
                "edge": {"count": 1, "burst_cycle_interval": 1, "packet_bits": 400000, "pdb_ms": 500},
            },
            "radio": {
                "environment": {
                    "scenario_type": "uma",
                    "carrier_frequency_ghz": 3.5,
                    "mcs_table_path": "mcs/nr_ul_main.json",
                },
                "center": {"base_snr_db": 8.0, "snr_min_db": 0.0, "snr_max_db": 20.0},
                "edge": {
                    "base_snr_db": 1.0,
                    "snr_min_db": -5.0,
                    "snr_max_db": 10.0,
                    "edge_per_u_slot_prb_cap": 30,
                },
            },
            "scheduler": {"ranking": "epf", "reinsert_policy": "business_aware_constrained_insert"},
            "report": {"output_dir": "outputs/test-main", "keep_slot_trace": False},
        }
        mcs_payload = [
            {"sinr_db": -5.0, "mcs_index": 0, "spectral_efficiency": 1.0},
            {"sinr_db": 0.0, "mcs_index": 1, "spectral_efficiency": 2.0},
            {"sinr_db": 6.0, "mcs_index": 2, "spectral_efficiency": 3.0},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            (config_dir / "mcs").mkdir()
            (config_dir / "mcs" / "nr_ul_main.json").write_text(json.dumps(mcs_payload), encoding="utf-8")
            path = config_dir / "config.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            config = load_config(path)
        self.assertEqual(config.resources.total_prb_per_u_slot, 237)
        self.assertEqual(config.radio.environment.mcs_table[0].bits_per_prb, 180)
        self.assertEqual(config.radio.environment.mcs_table[1].bits_per_prb, 360)
        self.assertEqual(config.radio.environment.mcs_table[2].bits_per_prb, 540)
        self.assertEqual(config.radio.center.bits_per_prb, 540)
        self.assertEqual(config.radio.edge.bits_per_prb, 360)
        self.assertTrue(config.simulation.stop_when_target_edge_finished)

    def test_load_config_supports_packet_size_sensitivity_sweep(self) -> None:
        payload = {
            "simulation": {
                "cycles": 1000,
                "slot_duration_ms": 1,
                "tdd_pattern": "DSUUU",
                "random_seed": 7,
                "stop_when_target_edge_finished": True,
                "deadline_guard_ms": 10,
            },
            "resources": {"total_prb_per_u_slot": 237, "max_ue_per_slot": 16},
            "traffic": {
                "center": {
                    "count": 63,
                    "period_slots": 1,
                    "packet_bits": 160,
                    "pdb_ms": 1000000000,
                    "gbr_bps": 7000,
                },
                "edge": {"count": 1, "packet_bits": 3200000, "pdb_ms": 500},
            },
            "radio": {
                "environment": {
                    "scenario_type": "uma",
                    "cell_radius_m": 500,
                    "carrier_frequency_ghz": 3.5,
                    "noise_figure_db": 7.0,
                    "interference_margin_db": 3.0,
                    "shadow_std_db": 4.0,
                    "slow_fading_alpha": 0.95,
                    "slot_jitter_std_db": 0.5,
                    "center_distance_range_m": [50, 150],
                    "edge_distance_range_m": [375, 475],
                    "mcs_table_path": "mcs/nr_ul_main.json",
                },
                "center": {},
                "edge": {"edge_per_u_slot_prb_cap": 237},
            },
            "scheduler": {"ranking": "epf", "reinsert_policy": "business_aware_constrained_insert"},
            "report": {"output_dir": "outputs/packet-size-test", "keep_slot_trace": False},
            "sweep": {
                "policies": ["tail_append", "business_aware_constrained_insert"],
                "edge_packet_kb": [400, 800, 1200, 1600, 2000],
                "edge_pdb_ms": [100, 150, 200, 300, 400, 500],
                "center_user_count": [16, 23, 31, 47, 63, 79],
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            (config_dir / "mcs").mkdir()
            (config_dir / "mcs" / "nr_ul_main.json").write_text(
                json.dumps([{"sinr_db": -5.0, "mcs_index": 0, "spectral_efficiency": 1.0}]),
                encoding="utf-8",
            )
            path = config_dir / "config.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            config = load_config(path)
        self.assertEqual(config.radio.edge.edge_per_u_slot_prb_cap, 237)
        self.assertEqual(config.traffic.edge.packet_bits, 3200000)

    def test_load_config_supports_null_pdb_and_avg_rate_ewma_beta(self) -> None:
        payload = {
            "simulation": {
                "cycles": 2,
                "slot_duration_ms": 1,
                "tdd_pattern": "DSUUU",
                "avg_rate_ewma_beta": 0.8,
            },
            "resources": {"total_prb_per_u_slot": 10, "max_ue_per_slot": 2},
            "traffic": {
                "center": {"count": 1, "period_slots": 1, "packet_bits": 100, "pdb_ms": None},
                "edge": {"count": 1, "burst_cycle_interval": 1, "packet_bits": 200, "pdb_ms": 15},
            },
            "radio": {
                "center": {"bits_per_prb": 10, "per_u_slot_prb_cap": 10},
                "edge": {"bits_per_prb": 10, "per_u_slot_prb_cap": 4},
            },
            "scheduler": {"ranking": "epf", "reinsert_policy": "tail_append"},
            "report": {"output_dir": "outputs/test", "keep_slot_trace": False},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            config = load_config(path)
        self.assertEqual(config.simulation.avg_rate_ewma_beta, 0.8)
        self.assertIsNone(config.traffic.center.pdb_ms)

    def test_load_config_reads_deadline_guard_ms(self) -> None:
        payload = {
            "simulation": {
                "cycles": 1,
                "slot_duration_ms": 1,
                "tdd_pattern": "DSUUU",
                "deadline_guard_ms": 5,
            },
            "resources": {"total_prb_per_u_slot": 10, "max_ue_per_slot": 2},
            "traffic": {
                "center": {"count": 1, "period_slots": 1, "packet_bits": 100, "pdb_ms": 30},
                "edge": {"count": 1, "burst_cycle_interval": 1, "packet_bits": 100, "pdb_ms": 15},
            },
            "radio": {
                "center": {"bits_per_prb": 10, "per_u_slot_prb_cap": 10},
                "edge": {"bits_per_prb": 10, "per_u_slot_prb_cap": 4},
            },
            "scheduler": {"ranking": "epf", "reinsert_policy": "business_aware_constrained_insert"},
            "report": {"output_dir": "outputs/test", "keep_slot_trace": False},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            config = load_config(path)
        self.assertEqual(config.simulation.deadline_guard_ms, 5)


if __name__ == "__main__":
    unittest.main()
