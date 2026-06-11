import json
import tempfile
import unittest
from pathlib import Path

from scheduling_sim.config import (
    AppConfig,
    McsEntryConfig,
    RadioClassConfig,
    RadioConfig,
    RadioSection,
    ReportConfig,
    ResourcesConfig,
    SchedulerConfig,
    SimulationConfig,
    TrafficConfig,
    TrafficSection,
    WirelessEnvConfig,
    load_config,
)
from scheduling_sim.metrics import MetricsCollector
from scheduling_sim.models import CurrentRadioState, LogicalChannel, Packet, PhasePlan, RadioProfile, TrafficProfile, UserEquipment
from scheduling_sim.reporting import write_report
from scheduling_sim.reinsert import ConstrainedInsertPolicy, TargetOnlyConstrainedInsertPolicy
from scheduling_sim.scenario import ScenarioFactory
from scheduling_sim.simulator import UlSimulator


class ScenarioFactoryTests(unittest.TestCase):
    def test_builds_center_and_edge_users(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(cycles=2, slot_duration_ms=1, tdd_pattern="DSUUU"),
            resources=ResourcesConfig(total_prb_per_u_slot=106, max_ue_per_slot=16),
            traffic=TrafficSection(
                center=TrafficConfig(count=2, period_slots=1, packet_bits=200, pdb_ms=30),
                edge=TrafficConfig(count=1, burst_cycle_interval=2, packet_bits=40000, pdb_ms=15),
            ),
            radio=RadioSection(
                center=RadioConfig(bits_per_prb=20, per_u_slot_prb_cap=106),
                edge=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=18),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/demo", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()
        self.assertEqual(len(users), 3)
        self.assertEqual(sum(1 for user in users if user.is_edge_user), 1)

    def test_scenario_factory_assigns_distances_inside_ranges(self) -> None:
        payload = {
            "simulation": {"cycles": 1, "slot_duration_ms": 1, "tdd_pattern": "DSUUU", "random_seed": 11},
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
        users = ScenarioFactory(config).build_users()
        center_user = next(user for user in users if not user.is_edge_user)
        edge_user = next(user for user in users if user.is_edge_user)
        self.assertGreaterEqual(center_user.radio_profile.distance_to_bs_m, 50.0)
        self.assertLessEqual(center_user.radio_profile.distance_to_bs_m, 150.0)
        self.assertGreaterEqual(edge_user.radio_profile.distance_to_bs_m, 425.0)
        self.assertLessEqual(edge_user.radio_profile.distance_to_bs_m, 500.0)

    def test_scenario_factory_carries_periodic_pdb_metadata(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(
                cycles=2,
                slot_duration_ms=1,
                tdd_pattern="DSUUU",
                random_seed=7,
                analysis_window_ms=10000,
            ),
            resources=ResourcesConfig(total_prb_per_u_slot=20, max_ue_per_slot=4),
            traffic=TrafficSection(
                center=TrafficConfig(
                    count=1,
                    period_slots=6,
                    packet_bits=960,
                    pdb_ms=None,
                    gbr_bps=7000,
                ),
                edge=TrafficConfig(
                    count=1,
                    packet_bits=80000,
                    pdb_ms=200,
                    arrival_mode="periodic_by_pdb",
                    initial_phase_mode="uniform_0_to_pdb",
                ),
            ),
            radio=RadioSection(
                center=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=20),
                edge=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=20),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/test", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()
        edge_user = next(user for user in users if user.is_edge_user)
        self.assertEqual(edge_user.traffic_profile.arrival_mode, "periodic_by_pdb")
        self.assertEqual(edge_user.traffic_profile.initial_phase_mode, "uniform_0_to_pdb")
        self.assertEqual(edge_user.traffic_profile.pdb_ms, 200)

    def test_scenario_factory_defaults_periodic_pdb_metadata_for_legacy_configs(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(cycles=2, slot_duration_ms=1, tdd_pattern="DSUUU", random_seed=7),
            resources=ResourcesConfig(total_prb_per_u_slot=20, max_ue_per_slot=4),
            traffic=TrafficSection(
                center=TrafficConfig(
                    count=1,
                    period_slots=6,
                    packet_bits=960,
                    pdb_ms=None,
                    gbr_bps=7000,
                ),
                edge=TrafficConfig(
                    count=1,
                    packet_bits=80000,
                    pdb_ms=200,
                ),
            ),
            radio=RadioSection(
                center=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=20),
                edge=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=20),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/test", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()
        edge_user = next(user for user in users if user.is_edge_user)
        self.assertEqual(edge_user.traffic_profile.arrival_mode, "single_burst")
        self.assertEqual(edge_user.traffic_profile.initial_phase_mode, "none")

class DummyMetrics:
    def build_summary(
        self,
        total_prb_used: int,
        total_prb_available: int,
        users=None,
        simulation_duration_ms: int = 0,
        analysis_window_ms: int = 0,
        window_total_prb_used: int = 0,
        window_total_prb_available: int = 0,
        slot_duration_ms: int = 1,
        tdd_pattern: str = "DSUUU",
    ) -> dict[str, float]:
        return {
            "total_prb_used": float(total_prb_used),
            "total_prb_available": float(total_prb_available),
            "user_count": float(len(list(users or []))),
            "simulation_duration_ms": float(simulation_duration_ms),
            "slot_duration_ms": float(slot_duration_ms),
            "tdd_pattern_len": float(len(tdd_pattern)),
        }


class RecordingWirelessEnv:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str]] = []

    def reset(self, users) -> None:
        for user in users:
            current_state = user.current_radio_state
            user.current_radio_state = CurrentRadioState(
                snr_db=0.0 if current_state is None else current_state.snr_db,
                mcs_index=0,
                bits_per_prb=1,
                per_u_slot_prb_cap=None if current_state is None else current_state.per_u_slot_prb_cap,
            )

    def refresh_slot(self, users, slot_index: int, slot_name: str) -> None:
        self.calls.append((slot_index, slot_name))
        bits_per_prb = 5 if slot_name == "D" else 9
        for user in users:
            current_state = user.current_radio_state
            user.current_radio_state = CurrentRadioState(
                snr_db=0.0 if current_state is None else current_state.snr_db,
                mcs_index=0 if current_state is None else current_state.mcs_index,
                bits_per_prb=bits_per_prb,
                per_u_slot_prb_cap=None if current_state is None else current_state.per_u_slot_prb_cap,
            )


class RadioSnapshotWirelessEnv:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str]] = []

    def reset(self, users) -> None:
        for user in users:
            current = user.current_radio_state
            user.current_radio_state = CurrentRadioState(
                snr_db=4.0,
                mcs_index=1,
                bits_per_prb=10,
                per_u_slot_prb_cap=None if current is None else current.per_u_slot_prb_cap,
            )

    def refresh_slot(self, users, slot_index: int, slot_name: str) -> None:
        self.calls.append((slot_index, slot_name))
        snr_db = 6.0 if slot_name == "D" else 8.0
        bits_per_prb = 12 if slot_name == "D" else 14
        for user in users:
            current = user.current_radio_state
            user.current_radio_state = CurrentRadioState(
                snr_db=snr_db,
                mcs_index=2 if slot_name == "D" else 3,
                bits_per_prb=bits_per_prb,
                per_u_slot_prb_cap=None if current is None else current.per_u_slot_prb_cap,
            )


class RefreshOnlyWirelessEnv:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str]] = []

    def refresh_slot(self, users, slot_index: int, slot_name: str) -> None:
        self.calls.append((slot_index, slot_name))
        for user in users:
            current = user.current_radio_state
            user.current_radio_state = CurrentRadioState(
                snr_db=6.0 if slot_name == "D" else 8.0,
                mcs_index=2 if slot_name == "D" else 3,
                bits_per_prb=12 if slot_name == "D" else 14,
                per_u_slot_prb_cap=None if current is None else current.per_u_slot_prb_cap,
            )


class RecordingPlanner:
    def __init__(self) -> None:
        self.bits_per_prb_by_phase: dict[str, int] = {}

    def plan_phase(self, phase: str, ranked_users) -> PhasePlan:
        if ranked_users and ranked_users[0].current_radio_state is not None:
            self.bits_per_prb_by_phase[phase] = ranked_users[0].current_radio_state.bits_per_prb
        return PhasePlan(phase=phase, slot_prb_budgets=[0, 0, 0], slot_grants={0: [], 1: [], 2: []})


class ReverseRanking:
    def rank(self, users):
        return list(reversed(users))


class SimulatorCycleTests(unittest.TestCase):
    def _legacy_config(self, center_count: int = 1, max_ue_per_slot: int = 2) -> AppConfig:
        return AppConfig(
            simulation=SimulationConfig(cycles=1, slot_duration_ms=1, tdd_pattern="DSUUU"),
            resources=ResourcesConfig(total_prb_per_u_slot=10, max_ue_per_slot=max_ue_per_slot),
            traffic=TrafficSection(
                center=TrafficConfig(count=center_count, period_slots=1, packet_bits=30, pdb_ms=30),
                edge=TrafficConfig(count=0, burst_cycle_interval=1, packet_bits=0, pdb_ms=15),
            ),
            radio=RadioSection(
                center=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=10),
                edge=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=10),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/demo", keep_slot_trace=False),
        )

    def test_u_slot_arrivals_become_eligible_next_cycle(self) -> None:
        config = self._legacy_config(center_count=1, max_ue_per_slot=2)
        users = ScenarioFactory(config).build_users()
        simulator = UlSimulator(config, users, DummyMetrics())
        simulator.inject_packet(users[0], packet_bits=50, cycle_index=0, slot_name="U1")
        self.assertEqual(users[0].lc.eligible_cycle, 1)

    def test_periodic_mode_does_not_preload_single_burst_packet(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(cycles=1, slot_duration_ms=1, tdd_pattern="DSUUU", random_seed=7),
            resources=ResourcesConfig(total_prb_per_u_slot=10, max_ue_per_slot=1),
            traffic=TrafficSection(
                center=TrafficConfig(count=0, period_slots=1, packet_bits=0, pdb_ms=30),
                edge=TrafficConfig(
                    count=1,
                    packet_bits=80000,
                    pdb_ms=200,
                    arrival_mode="periodic_by_pdb",
                    initial_phase_mode="none",
                ),
            ),
            radio=RadioSection(
                center=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=10),
                edge=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=10),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/test", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()
        edge_user = users[0]
        simulator = UlSimulator(config, users, DummyMetrics())

        simulator._preload_initial_backlog()

        self.assertEqual(edge_user.lc.packets, [])

    def test_u_slot_arrivals_do_not_materialize_periodic_edge_packets_mid_cycle(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(cycles=1, slot_duration_ms=1, tdd_pattern="DSUUU", random_seed=7),
            resources=ResourcesConfig(total_prb_per_u_slot=10, max_ue_per_slot=2),
            traffic=TrafficSection(
                center=TrafficConfig(count=0, period_slots=1, packet_bits=0, pdb_ms=30),
                edge=TrafficConfig(
                    count=1,
                    packet_bits=80000,
                    pdb_ms=200,
                    arrival_mode="periodic_by_pdb",
                    initial_phase_mode="none",
                ),
            ),
            radio=RadioSection(
                center=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=10),
                edge=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=10),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/test", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()
        edge_user = users[0]
        simulator = UlSimulator(config, users, DummyMetrics())

        simulator._inject_u_slot_arrivals(cycle_index=0, u_slot_index=0, now_ms=2)

        self.assertEqual(edge_user.lc.packets, [])

    def test_periodic_cycle_start_arrivals_are_eligible_in_same_cycle(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(
                cycles=1,
                slot_duration_ms=1,
                tdd_pattern="DSUUU",
                random_seed=7,
                analysis_window_ms=5,
            ),
            resources=ResourcesConfig(total_prb_per_u_slot=1, max_ue_per_slot=1),
            traffic=TrafficSection(
                center=TrafficConfig(count=0, period_slots=1, packet_bits=0, pdb_ms=30),
                edge=TrafficConfig(
                    count=1,
                    packet_bits=10,
                    pdb_ms=5,
                    arrival_mode="periodic_by_pdb",
                    initial_phase_mode="none",
                ),
            ),
            radio=RadioSection(
                center=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=1),
                edge=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=1),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/test", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()

        summary = UlSimulator(config, users, MetricsCollector()).run()

        self.assertTrue(summary["target_edge_finished"])
        self.assertEqual(summary["target_edge_time_to_first_service_ms"], 2.0)
        self.assertEqual(summary["target_edge_completion_delay_ms"], 3.0)

    def test_periodic_mode_uses_analysis_window_for_prb_and_extends_runtime_for_tail(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(
                cycles=2,
                slot_duration_ms=1,
                tdd_pattern="DSUUU",
                random_seed=7,
                analysis_window_ms=12,
            ),
            resources=ResourcesConfig(total_prb_per_u_slot=1, max_ue_per_slot=1),
            traffic=TrafficSection(
                center=TrafficConfig(count=0, period_slots=1, packet_bits=0, pdb_ms=30),
                edge=TrafficConfig(
                    count=1,
                    packet_bits=10,
                    pdb_ms=5,
                    arrival_mode="periodic_by_pdb",
                    initial_phase_mode="none",
                ),
            ),
            radio=RadioSection(
                center=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=1),
                edge=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=1),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/test", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()

        summary = UlSimulator(config, users, MetricsCollector()).run()

        self.assertEqual(summary["analysis_window_ms"], 12.0)
        self.assertEqual(summary["simulation_duration_ms"], 17.0)
        self.assertEqual(summary["completed_packets"], 3)
        self.assertEqual(summary["edge_total_bits"], 20.0)
        self.assertEqual(summary["throughput_bits"], 20)
        self.assertEqual(summary["edge_used_prb"], 4.0)
        self.assertEqual(summary["prb_utilization"], 4.0 / 6.0)

    def test_periodic_mode_excludes_post_window_arrivals_from_satisfaction_denominator(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(
                cycles=5,
                slot_duration_ms=1,
                tdd_pattern="DSUUU",
                random_seed=7,
                analysis_window_ms=12,
            ),
            resources=ResourcesConfig(total_prb_per_u_slot=1, max_ue_per_slot=1),
            traffic=TrafficSection(
                center=TrafficConfig(count=0, period_slots=1, packet_bits=0, pdb_ms=30),
                edge=TrafficConfig(
                    count=1,
                    packet_bits=10,
                    pdb_ms=10,
                    arrival_mode="periodic_by_pdb",
                    initial_phase_mode="none",
                ),
            ),
            radio=RadioSection(
                center=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=1),
                edge=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=1),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/test", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()

        summary = UlSimulator(config, users, MetricsCollector()).run()

        self.assertEqual(summary["pdb_arrivals_in_window"], 2)
        self.assertEqual(summary["pdb_packets_completed_in_window_set"], 2)
        self.assertEqual(summary["edge_pdb_satisfaction_rate"], 1.0)

    def test_u_slot_arrivals_preserve_center_periodic_injection(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(cycles=1, slot_duration_ms=1, tdd_pattern="DSUUU", random_seed=7),
            resources=ResourcesConfig(total_prb_per_u_slot=10, max_ue_per_slot=2),
            traffic=TrafficSection(
                center=TrafficConfig(count=1, period_slots=2, packet_bits=30, pdb_ms=30),
                edge=TrafficConfig(
                    count=0,
                    packet_bits=80000,
                    pdb_ms=200,
                ),
            ),
            radio=RadioSection(
                center=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=10),
                edge=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=10),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/test", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()
        center_user = users[0]
        simulator = UlSimulator(config, users, DummyMetrics())

        simulator._inject_u_slot_arrivals(cycle_index=0, u_slot_index=0, now_ms=2)

        self.assertEqual(len(center_user.lc.packets), 1)
        self.assertEqual(center_user.lc.head_packet.arrival_time, 0)
        self.assertEqual(center_user.lc.head_packet.eligible_cycle, 1)

    def test_u_slot_arrivals_preserve_legacy_edge_burst_injection(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(cycles=2, slot_duration_ms=1, tdd_pattern="DSUUU", random_seed=7),
            resources=ResourcesConfig(total_prb_per_u_slot=10, max_ue_per_slot=2),
            traffic=TrafficSection(
                center=TrafficConfig(count=0, period_slots=1, packet_bits=0, pdb_ms=30),
                edge=TrafficConfig(
                    count=1,
                    packet_bits=80000,
                    pdb_ms=200,
                    burst_cycle_interval=2,
                    arrival_mode="single_burst",
                ),
            ),
            radio=RadioSection(
                center=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=10),
                edge=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=10),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/test", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()
        edge_user = users[0]
        simulator = UlSimulator(config, users, DummyMetrics())

        simulator._inject_u_slot_arrivals(cycle_index=1, u_slot_index=0, now_ms=7)

        self.assertEqual(len(edge_user.lc.packets), 1)
        self.assertEqual(edge_user.lc.head_packet.arrival_time, 5)
        self.assertEqual(edge_user.lc.head_packet.eligible_cycle, 2)
        self.assertFalse(edge_user.lc.head_packet.is_target)

    def test_u_slot_arrival_does_not_make_existing_hol_ineligible(self) -> None:
        config = self._legacy_config(center_count=1, max_ue_per_slot=1)
        users = ScenarioFactory(config).build_users()
        simulator = UlSimulator(config, users, DummyMetrics())
        center_user = users[0]
        simulator.inject_packet(center_user, packet_bits=100, cycle_index=0, slot_name="D")
        simulator.queue.activate(center_user)
        simulator.inject_packet(center_user, packet_bits=100, cycle_index=0, slot_name="U1")
        simulator.seed_active_queue(0)
        self.assertTrue(simulator.queue.contains(center_user))
        self.assertEqual(center_user.lc.head_packet.arrival_time, 0)
        self.assertEqual(center_user.lc.eligible_cycle, 0)
        simulator._consume_user_bits(center_user, bits_budget=100, now_ms=2)
        simulator.seed_active_queue(0)
        self.assertFalse(simulator.queue.contains(center_user))
        self.assertIsNotNone(center_user.lc.head_packet)
        simulator.seed_active_queue(1)
        self.assertTrue(simulator.queue.contains(center_user))

    def test_finish_phase_tail_append_preserves_candidate_relative_order(self) -> None:
        config = self._legacy_config(center_count=3, max_ue_per_slot=2)
        users = ScenarioFactory(config).build_users()
        simulator = UlSimulator(config, users, DummyMetrics())
        for user in users:
            simulator.inject_packet(user, packet_bits=50, cycle_index=0, slot_name="D")
            simulator.queue.activate(user)
        simulator.ranking = ReverseRanking()
        simulator.finish_phase("D")
        after = [ue.ue_id for ue in simulator.queue.ordered_users()]
        self.assertEqual(after, ["center-2", "center-0", "center-1"])

    def test_refreshes_wireless_snapshots_before_d_and_s_only(self) -> None:
        config = self._legacy_config(center_count=1, max_ue_per_slot=1)
        users = ScenarioFactory(config).build_users()
        wireless_env = RecordingWirelessEnv()
        simulator = UlSimulator(config, users, DummyMetrics(), wireless_env=wireless_env)
        simulator.run()
        self.assertEqual(wireless_env.calls, [(0, "D"), (1, "S")])

    def test_finish_phase_refreshes_radio_state_before_planning(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(cycles=1, slot_duration_ms=1, tdd_pattern="DSUUU", random_seed=7),
            resources=ResourcesConfig(total_prb_per_u_slot=6, max_ue_per_slot=4),
            traffic=TrafficSection(
                center=TrafficConfig(count=0, period_slots=1, packet_bits=80, pdb_ms=30),
                edge=TrafficConfig(count=1, burst_cycle_interval=1, packet_bits=120, pdb_ms=15),
            ),
            radio=RadioSection(
                environment=WirelessEnvConfig(
                    alpha=0.95,
                    jitter_std_db=0.2,
                    mcs_table=[McsEntryConfig(snr_db=0.0, mcs_index=0, bits_per_prb=4)],
                ),
                center=RadioClassConfig(base_snr_db=16.0, snr_min_db=10.0, snr_max_db=22.0),
                edge=RadioClassConfig(base_snr_db=4.0, snr_min_db=-2.0, snr_max_db=8.0, edge_per_u_slot_prb_cap=3),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/test", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()
        wireless_env = RecordingWirelessEnv()
        simulator = UlSimulator(config, users, DummyMetrics(), wireless_env=wireless_env)
        simulator.inject_packet(users[0], packet_bits=120, cycle_index=0, slot_name="D")
        simulator.queue.activate(users[0])
        d_plan = simulator.finish_phase("D", now_ms=0, slot_index=0)
        s_plan = simulator.finish_phase("S", now_ms=1, slot_index=1)
        self.assertEqual(wireless_env.calls, [(0, "D"), (1, "S")])
        self.assertEqual(d_plan.slot_grants[0][0].bits_planned, 15)
        self.assertEqual(s_plan.slot_grants[1][0].bits_planned, 27)

    def test_finish_phase_does_not_refresh_wireless_state_for_u_phase(self) -> None:
        config = self._legacy_config(center_count=1, max_ue_per_slot=1)
        users = ScenarioFactory(config).build_users()
        wireless_env = RecordingWirelessEnv()
        simulator = UlSimulator(config, users, DummyMetrics(), wireless_env=wireless_env)
        simulator.queue.activate(users[0])
        simulator.finish_phase("U", now_ms=2, slot_index=2)
        self.assertEqual(wireless_env.calls, [])

    def test_run_refreshes_d_and_s_planning_with_current_radio_state(self) -> None:
        config = self._legacy_config(center_count=1, max_ue_per_slot=1)
        users = ScenarioFactory(config).build_users()
        wireless_env = RecordingWirelessEnv()
        simulator = UlSimulator(config, users, DummyMetrics(), wireless_env=wireless_env)
        planner = RecordingPlanner()
        simulator.planner = planner
        simulator.run()
        self.assertEqual(planner.bits_per_prb_by_phase.get("D"), 5)
        self.assertEqual(planner.bits_per_prb_by_phase.get("S"), 9)

    def test_metrics_build_user_radio_rows_tracks_initial_mean_and_extrema(self) -> None:
        collector = MetricsCollector()
        user = UserEquipment(
            ue_id="edge-0",
            lc=LogicalChannel(lc_id="edge-0-lc", packets=[]),
            is_edge_user=True,
            radio_profile=RadioProfile(
                user_class="edge",
                base_snr_db=0.0,
                snr_min_db=-10.0,
                snr_max_db=20.0,
                distance_to_bs_m=432.5,
                edge_per_u_slot_prb_cap=6,
                bits_per_prb=10,
                per_u_slot_prb_cap=6,
            ),
            average_throughput=1.0,
            traffic_profile=TrafficProfile(packet_bits=80000, pdb_ms=400),
            current_radio_state=CurrentRadioState(snr_db=4.0, mcs_index=1, bits_per_prb=10, per_u_slot_prb_cap=6),
        )
        collector.record_radio_state(user)
        user.current_radio_state = CurrentRadioState(snr_db=6.0, mcs_index=2, bits_per_prb=12, per_u_slot_prb_cap=6)
        collector.record_radio_state(user)
        user.current_radio_state = CurrentRadioState(snr_db=8.0, mcs_index=3, bits_per_prb=14, per_u_slot_prb_cap=6)
        collector.record_radio_state(user)

        rows = collector.build_user_radio_rows([user])

        self.assertEqual(rows[0]["distance_to_bs_m"], 432.5)
        self.assertEqual(rows[0]["initial_sinr_db"], 4.0)
        self.assertEqual(rows[0]["sinr_mean_db"], 6.0)
        self.assertEqual(rows[0]["sinr_min_db"], 4.0)
        self.assertEqual(rows[0]["sinr_max_db"], 8.0)
        self.assertEqual(rows[0]["initial_mcs_index"], 1)
        self.assertEqual(rows[0]["initial_bits_per_prb"], 10)

    def test_run_records_initial_and_refreshed_radio_snapshots(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(cycles=1, slot_duration_ms=1, tdd_pattern="DSUUU", random_seed=7),
            resources=ResourcesConfig(total_prb_per_u_slot=6, max_ue_per_slot=1),
            traffic=TrafficSection(
                center=TrafficConfig(count=0, period_slots=1, packet_bits=960, pdb_ms=None),
                edge=TrafficConfig(count=1, packet_bits=80000, pdb_ms=400),
            ),
            radio=RadioSection(
                center=RadioClassConfig(base_snr_db=16.0, snr_min_db=10.0, snr_max_db=22.0),
                edge=RadioClassConfig(base_snr_db=4.0, snr_min_db=-5.0, snr_max_db=10.0, edge_per_u_slot_prb_cap=6),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/test", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()
        collector = MetricsCollector()
        simulator = UlSimulator(config, users, collector, wireless_env=RadioSnapshotWirelessEnv())

        simulator.run()
        stats = collector.radio_stats_by_user[users[0].ue_id]
        rows = collector.build_user_radio_rows(users)

        self.assertEqual(stats["sinr_count"], 3)
        self.assertEqual(stats["sinr_sum_db"], 18.0)
        self.assertEqual(rows[0]["initial_sinr_db"], 4.0)
        self.assertEqual(rows[0]["sinr_mean_db"], 6.0)
        self.assertEqual(rows[0]["sinr_min_db"], 4.0)
        self.assertEqual(rows[0]["sinr_max_db"], 8.0)

    def test_run_does_not_record_initial_radio_snapshot_without_reset(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(cycles=1, slot_duration_ms=1, tdd_pattern="DSUUU", random_seed=7),
            resources=ResourcesConfig(total_prb_per_u_slot=6, max_ue_per_slot=1),
            traffic=TrafficSection(
                center=TrafficConfig(count=0, period_slots=1, packet_bits=960, pdb_ms=None),
                edge=TrafficConfig(count=1, packet_bits=80000, pdb_ms=400),
            ),
            radio=RadioSection(
                center=RadioClassConfig(base_snr_db=16.0, snr_min_db=10.0, snr_max_db=22.0),
                edge=RadioClassConfig(base_snr_db=4.0, snr_min_db=-5.0, snr_max_db=10.0, edge_per_u_slot_prb_cap=6),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/test", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()
        collector = MetricsCollector()
        simulator = UlSimulator(config, users, collector, wireless_env=RefreshOnlyWirelessEnv())

        simulator.run()
        stats = collector.radio_stats_by_user[users[0].ue_id]
        rows = collector.build_user_radio_rows(users)

        self.assertEqual(stats["sinr_count"], 2)
        self.assertEqual(stats["sinr_sum_db"], 14.0)
        self.assertEqual(rows[0]["initial_sinr_db"], 6.0)
        self.assertEqual(rows[0]["sinr_mean_db"], 7.0)

    def test_execute_u_slot_caps_merged_edge_prbs_at_physical_slot(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(cycles=1, slot_duration_ms=1, tdd_pattern="DSUUU"),
            resources=ResourcesConfig(total_prb_per_u_slot=36, max_ue_per_slot=1),
            traffic=TrafficSection(
                center=TrafficConfig(count=0, period_slots=1, packet_bits=0, pdb_ms=30),
                edge=TrafficConfig(count=1, burst_cycle_interval=1, packet_bits=40000, pdb_ms=15),
            ),
            radio=RadioSection(
                center=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=36),
                edge=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=18),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/test", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()
        edge_user = users[0]
        simulator = UlSimulator(config, users, DummyMetrics())
        simulator.inject_packet(edge_user, packet_bits=10000, cycle_index=0, slot_name="D")
        d_plan = simulator.planner.plan_phase("D", [edge_user])
        s_plan = simulator.planner.plan_phase("S", [edge_user])
        used_prbs = simulator._execute_u_slot(
            cycle_index=0,
            slot_index=1,
            now_ms=2,
            d_plan=d_plan,
            s_plan=s_plan,
        )
        self.assertEqual(used_prbs, 18)
        self.assertEqual(edge_user.lc.head_packet.remaining_bits, 10000 - 180)

    def test_run_records_served_bits_even_when_packet_is_not_completed(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(cycles=1, slot_duration_ms=1, tdd_pattern="DSUUU"),
            resources=ResourcesConfig(total_prb_per_u_slot=18, max_ue_per_slot=1),
            traffic=TrafficSection(
                center=TrafficConfig(count=0, period_slots=1, packet_bits=0, pdb_ms=30),
                edge=TrafficConfig(count=1, burst_cycle_interval=10, packet_bits=40000, pdb_ms=15),
            ),
            radio=RadioSection(
                center=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=18),
                edge=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=18),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/test", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()
        summary = UlSimulator(config, users, MetricsCollector()).run()
        self.assertEqual(summary["served_bits"], summary["throughput_bits"])

    def test_run_updates_average_throughput_from_cycle_rate(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(
                cycles=1,
                slot_duration_ms=1,
                tdd_pattern="DSUUU",
                avg_rate_ewma_beta=0.5,
            ),
            resources=ResourcesConfig(total_prb_per_u_slot=10, max_ue_per_slot=1),
            traffic=TrafficSection(
                center=TrafficConfig(count=1, period_slots=10, packet_bits=30, pdb_ms=None),
                edge=TrafficConfig(count=0, burst_cycle_interval=1, packet_bits=0, pdb_ms=15),
            ),
            radio=RadioSection(
                center=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=10),
                edge=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=10),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/demo", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()
        simulator = UlSimulator(config, users, DummyMetrics())
        simulator.run()
        self.assertEqual(users[0].average_throughput, 6000.5)

    def test_run_decays_average_throughput_when_cycle_has_no_service(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(
                cycles=1,
                slot_duration_ms=1,
                tdd_pattern="DSUUU",
                avg_rate_ewma_beta=0.8,
            ),
            resources=ResourcesConfig(total_prb_per_u_slot=10, max_ue_per_slot=1),
            traffic=TrafficSection(
                center=TrafficConfig(count=1, period_slots=10, packet_bits=0, pdb_ms=None),
                edge=TrafficConfig(count=0, burst_cycle_interval=1, packet_bits=0, pdb_ms=15),
            ),
            radio=RadioSection(
                center=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=10),
                edge=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=10),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/demo", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()
        users[0].average_throughput = 10.0
        simulator = UlSimulator(config, users, DummyMetrics())
        simulator.run()
        self.assertEqual(users[0].average_throughput, 8.0)

    def test_run_stops_after_target_edge_packet_finishes_when_configured(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(
                cycles=4,
                slot_duration_ms=1,
                tdd_pattern="DSUUU",
                stop_when_target_edge_finished=True,
            ),
            resources=ResourcesConfig(total_prb_per_u_slot=1, max_ue_per_slot=1),
            traffic=TrafficSection(
                center=TrafficConfig(count=0, period_slots=1, packet_bits=0, pdb_ms=30),
                edge=TrafficConfig(count=1, burst_cycle_interval=10, packet_bits=10, pdb_ms=15),
            ),
            radio=RadioSection(
                center=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=1),
                edge=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=1),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/test", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()
        summary = UlSimulator(config, users, MetricsCollector()).run()
        self.assertTrue(summary["target_edge_finished"])
        self.assertEqual(summary["target_edge_completion_delay_ms"], 3.0)
        self.assertEqual(summary["simulation_duration_ms"], 3.0)
        self.assertLess(summary["simulation_duration_ms"], 20.0)

    def test_constructs_wireless_env_from_new_radio_schema_when_not_injected(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(cycles=1, slot_duration_ms=1, tdd_pattern="DSUUU"),
            resources=ResourcesConfig(total_prb_per_u_slot=10, max_ue_per_slot=1),
            traffic=TrafficSection(
                center=TrafficConfig(count=1, period_slots=1, packet_bits=30, pdb_ms=30),
                edge=TrafficConfig(count=0, burst_cycle_interval=1, packet_bits=0, pdb_ms=15),
            ),
            radio=RadioSection(
                environment=WirelessEnvConfig(
                    alpha=1.0,
                    jitter_std_db=0.0,
                    mcs_table=[
                        McsEntryConfig(snr_db=0.0, mcs_index=0, bits_per_prb=3),
                        McsEntryConfig(snr_db=10.0, mcs_index=4, bits_per_prb=14),
                    ],
                ),
                center=RadioClassConfig(base_snr_db=12.0, snr_min_db=-10.0, snr_max_db=25.0),
                edge=RadioClassConfig(base_snr_db=0.0, snr_min_db=-10.0, snr_max_db=10.0, edge_per_u_slot_prb_cap=4),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/demo", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()
        self.assertEqual(users[0].current_radio_state.mcs_index, 0)
        simulator = UlSimulator(config, users, DummyMetrics())
        simulator.run()
        self.assertEqual(users[0].current_radio_state.mcs_index, 4)

    def test_mixed_schema_keeps_legacy_fixed_rate_and_prb_cap(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(cycles=1, slot_duration_ms=1, tdd_pattern="DSUUU"),
            resources=ResourcesConfig(total_prb_per_u_slot=10, max_ue_per_slot=1),
            traffic=TrafficSection(
                center=TrafficConfig(count=0, period_slots=1, packet_bits=30, pdb_ms=30),
                edge=TrafficConfig(count=1, burst_cycle_interval=1, packet_bits=30, pdb_ms=15),
            ),
            radio=RadioSection(
                environment=WirelessEnvConfig(
                    alpha=1.0,
                    jitter_std_db=0.0,
                    mcs_table=[McsEntryConfig(snr_db=0.0, mcs_index=0, bits_per_prb=3)],
                ),
                center=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=10),
                edge=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=4),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/demo", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()
        simulator = UlSimulator(config, users, DummyMetrics())
        self.assertIsNone(simulator.wireless_env)
        self.assertEqual(users[0].current_radio_state.bits_per_prb, 10)
        self.assertEqual(users[0].current_radio_state.per_u_slot_prb_cap, 4)

    def test_mixed_schema_refreshes_only_dynamic_users(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(cycles=1, slot_duration_ms=1, tdd_pattern="DSUUU"),
            resources=ResourcesConfig(total_prb_per_u_slot=10, max_ue_per_slot=2),
            traffic=TrafficSection(
                center=TrafficConfig(count=1, period_slots=1, packet_bits=30, pdb_ms=30),
                edge=TrafficConfig(count=1, burst_cycle_interval=1, packet_bits=30, pdb_ms=15),
            ),
            radio=RadioSection(
                environment=WirelessEnvConfig(
                    alpha=1.0,
                    jitter_std_db=0.0,
                    mcs_table=[
                        McsEntryConfig(snr_db=0.0, mcs_index=0, bits_per_prb=3),
                        McsEntryConfig(snr_db=10.0, mcs_index=4, bits_per_prb=14),
                    ],
                ),
                center=RadioClassConfig(base_snr_db=12.0, snr_min_db=-10.0, snr_max_db=25.0),
                edge=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=4),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/demo", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()
        simulator = UlSimulator(config, users, DummyMetrics())
        self.assertIsNotNone(simulator.wireless_env)
        center_user = next(user for user in users if not user.is_edge_user)
        edge_user = next(user for user in users if user.is_edge_user)
        self.assertEqual(center_user.current_radio_state.mcs_index, 4)
        self.assertEqual(edge_user.current_radio_state.bits_per_prb, 10)
        self.assertEqual(edge_user.current_radio_state.per_u_slot_prb_cap, 4)

    def test_supports_target_only_constrained_insert_policy(self) -> None:
        config = self._legacy_config(center_count=1, max_ue_per_slot=1)
        config = AppConfig(
            simulation=config.simulation,
            resources=config.resources,
            traffic=config.traffic,
            radio=config.radio,
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="target_only_constrained_insert"),
            report=config.report,
        )
        users = ScenarioFactory(config).build_users()
        simulator = UlSimulator(config, users, DummyMetrics())
        self.assertIsInstance(simulator.reinsert, TargetOnlyConstrainedInsertPolicy)

    def test_supports_business_aware_constrained_insert_policy(self) -> None:
        config = self._legacy_config(center_count=1, max_ue_per_slot=1)
        config = AppConfig(
            simulation=config.simulation,
            resources=config.resources,
            traffic=config.traffic,
            radio=config.radio,
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="business_aware_constrained_insert"),
            report=config.report,
        )
        users = ScenarioFactory(config).build_users()
        simulator = UlSimulator(config, users, DummyMetrics())
        self.assertIsInstance(simulator.reinsert, ConstrainedInsertPolicy)


class MetricsTests(unittest.TestCase):
    def _make_user(
        self,
        ue_id: str,
        *,
        is_edge_user: bool,
        gbr_bps: float = 0.0,
        hol_ms: int = 0,
        pdb_ms: int = 15,
    ) -> UserEquipment:
        packets = []
        if hol_ms > 0:
            packets.append(
                Packet(
                    packet_id=f"{ue_id}-hol",
                    arrival_time=0,
                    size_bits=1000,
                    remaining_bits=1000,
                    pdb_ms=pdb_ms,
                    completion_time=None,
                )
            )
        return UserEquipment(
            ue_id=ue_id,
            lc=LogicalChannel(lc_id=f"{ue_id}-lc", packets=packets, eligible_cycle=0),
            is_edge_user=is_edge_user,
            radio_profile=RadioProfile(
                user_class="edge" if is_edge_user else "center",
                bits_per_prb=10,
                per_u_slot_prb_cap=18,
            ),
            average_throughput=1.0,
            traffic_profile=TrafficProfile(
                packet_bits=1000,
                pdb_ms=pdb_ms,
                gbr_bps=gbr_bps,
            ),
            hol_ms=hol_ms,
        )

    def test_build_user_radio_rows_omits_users_without_recorded_snapshots(self) -> None:
        collector = MetricsCollector()
        user = self._make_user("edge-0", is_edge_user=True)
        user.current_radio_state = CurrentRadioState(
            snr_db=4.0,
            mcs_index=1,
            bits_per_prb=10,
            per_u_slot_prb_cap=6,
        )

        rows = collector.build_user_radio_rows([user])

        self.assertEqual(rows, [])

    def test_metrics_report_contains_pdb_and_throughput_keys(self) -> None:
        collector = MetricsCollector()
        collector.record_packet_completed(
            packet_id="pkt-1",
            completion_time=12,
            arrival_time=0,
            pdb_ms=15,
            bits_sent=120,
        )
        summary = collector.build_summary(total_prb_used=12, total_prb_available=30)
        self.assertIn("pdb_violation_rate", summary)
        self.assertIn("throughput_bits", summary)
        self.assertTrue(callable(write_report))

    def test_metrics_report_contains_served_and_grouped_fields(self) -> None:
        collector = MetricsCollector()
        collector.record_packet_completed(
            packet_id="center-0-pkt-1",
            completion_time=12,
            arrival_time=0,
            pdb_ms=15,
            bits_sent=120,
            user_class="center",
        )
        summary = collector.build_summary(total_prb_used=12, total_prb_available=30)
        self.assertIn("served_bits", summary)
        self.assertIn("center_completed_packets", summary)
        self.assertIn("edge_completed_packets", summary)
        self.assertIn("center_avg_delay_ms", summary)

    def test_metrics_report_contains_business_kpis(self) -> None:
        collector = MetricsCollector()
        center_fast = self._make_user("center-fast", is_edge_user=False, gbr_bps=12000.0)
        center_slow = self._make_user("center-slow", is_edge_user=False, gbr_bps=12000.0)
        edge_waiting = self._make_user("edge-waiting", is_edge_user=True, hol_ms=20, pdb_ms=15)
        collector.record_bits_served(user_class="center", bits_sent=200, ue_id=center_fast.ue_id)
        collector.record_bits_served(user_class="center", bits_sent=100, ue_id=center_slow.ue_id)
        collector.record_bits_served(user_class="edge", bits_sent=80, ue_id=edge_waiting.ue_id)
        collector.record_packet_completed(
            packet_id="edge-done-1",
            completion_time=10,
            arrival_time=0,
            pdb_ms=15,
            bits_sent=80,
            user_class="edge",
        )
        summary = collector.build_summary(
            total_prb_used=12,
            total_prb_available=30,
            users=[center_fast, center_slow, edge_waiting],
            simulation_duration_ms=10,
        )
        self.assertEqual(summary["center_user_gbr_satisfaction_rate"], 0.5)
        self.assertEqual(summary["center_avg_rate_bps"], 15000.0)
        self.assertEqual(summary["center_min_rate_bps"], 10000.0)
        self.assertEqual(summary["edge_pdb_satisfaction_rate"], 1.0)
        self.assertEqual(summary["edge_avg_hol_ms"], 20.0)
        self.assertEqual(summary["edge_overdue_hol_ratio"], 1.0)

    def test_metrics_report_contains_target_edge_breakdown(self) -> None:
        collector = MetricsCollector()
        collector.record_packet_completed(
            packet_id="edge-0-target",
            completion_time=3,
            arrival_time=0,
            pdb_ms=15,
            bits_sent=180,
            user_class="edge",
            ue_id="edge-0",
            is_target=True,
            first_service_time=2,
            service_slot_count=1,
            control_slot_count_while_pending=2,
            waiting_u_slot_count_before_first_service=0,
            waiting_u_slot_count_after_first_service=0,
        )
        summary = collector.build_summary(
            total_prb_used=6,
            total_prb_available=12,
            users=[],
            simulation_duration_ms=5,
            slot_duration_ms=1,
        )
        self.assertTrue(summary["target_edge_tracked"])
        self.assertTrue(summary["target_edge_finished"])
        self.assertEqual(summary["target_edge_completion_delay_ms"], 3.0)
        self.assertEqual(summary["target_edge_queue_wait_ms"], 2.0)
        self.assertEqual(summary["target_edge_service_time_ms"], 1.0)
        self.assertEqual(summary["target_edge_control_phase_wait_ms"], 2.0)
        self.assertEqual(summary["target_edge_pre_first_service_wait_ms"], 0.0)
        self.assertEqual(summary["target_edge_inter_service_gap_wait_ms"], 0.0)
        self.assertEqual(summary["target_edge_time_to_first_service_ms"], 2.0)
        self.assertTrue(summary["target_edge_pdb_met"])

    def test_metrics_report_contains_window_and_prb_breakdown(self) -> None:
        collector = MetricsCollector()
        center_user = self._make_user("center-0", is_edge_user=False, gbr_bps=12000.0)
        edge_user = self._make_user("edge-0", is_edge_user=True, gbr_bps=0.0)
        collector.record_bits_served(user_class="center", bits_sent=200, ue_id=center_user.ue_id)
        collector.record_bits_served(user_class="edge", bits_sent=80, ue_id=edge_user.ue_id)
        collector.record_prb_used(user_class="center", prb_count=5)
        collector.record_prb_used(user_class="edge", prb_count=3)
        collector.record_packet_completed(
            packet_id="edge-0-target",
            completion_time=10,
            arrival_time=0,
            pdb_ms=15,
            bits_sent=80,
            user_class="edge",
            ue_id=edge_user.ue_id,
            is_target=True,
            first_service_time=2,
            service_slot_count=1,
            control_slot_count_while_pending=2,
            waiting_u_slot_count_before_first_service=0,
            waiting_u_slot_count_after_first_service=0,
        )
        summary = collector.build_summary(
            total_prb_used=8,
            total_prb_available=10,
            users=[center_user, edge_user],
            simulation_duration_ms=10,
            slot_duration_ms=1,
        )
        self.assertEqual(summary["analysis_window_ms"], 10.0)
        self.assertEqual(summary["center_total_bits"], 200.0)
        self.assertEqual(summary["edge_total_bits"], 80.0)
        self.assertEqual(summary["target_edge_total_bits"], 80.0)
        self.assertEqual(summary["system_total_bits"], 280.0)
        self.assertEqual(summary["center_agg_rate_bps"], 20000.0)
        self.assertEqual(summary["edge_agg_rate_bps"], 8000.0)
        self.assertEqual(summary["target_edge_rate_bps"], 8000.0)
        self.assertEqual(summary["system_agg_rate_bps"], 28000.0)
        self.assertEqual(summary["center_used_prb"], 5.0)
        self.assertEqual(summary["edge_used_prb"], 3.0)
        self.assertEqual(summary["center_prb_share"], 0.625)
        self.assertEqual(summary["edge_prb_share"], 0.375)
        self.assertEqual(summary["center_bits_per_used_prb"], 40.0)
        self.assertEqual(summary["edge_bits_per_used_prb"], 80.0 / 3.0)

    def test_metrics_ignore_packets_without_pdb_in_deadline_kpis(self) -> None:
        collector = MetricsCollector()
        collector.record_packet_completed(
            packet_id="pkt-no-pdb",
            completion_time=10,
            arrival_time=0,
            pdb_ms=None,
            bits_sent=100,
            user_class="edge",
        )
        summary = collector.build_summary(total_prb_used=1, total_prb_available=1, users=[])
        self.assertEqual(summary["pdb_violation_rate"], 0.0)
        self.assertEqual(summary["edge_pdb_satisfaction_rate"], 0.0)

    def test_periodic_mode_excludes_post_window_arrivals_from_satisfaction_denominator(self) -> None:
        collector = MetricsCollector()
        collector.record_packet_completed(
            packet_id="edge-window",
            completion_time=15,
            arrival_time=10,
            pdb_ms=5,
            bits_sent=80,
            user_class="edge",
            ue_id="edge-0",
        )
        collector.record_packet_completed(
            packet_id="edge-post-window",
            completion_time=17,
            arrival_time=15,
            pdb_ms=1,
            bits_sent=80,
            user_class="edge",
            ue_id="edge-0",
            arrival_in_analysis_window=False,
        )

        summary = collector.build_summary(
            total_prb_used=3,
            total_prb_available=6,
            users=[],
            simulation_duration_ms=20,
            analysis_window_ms=12,
        )

        self.assertEqual(summary["pdb_arrivals_in_window"], 1)
        self.assertEqual(summary["pdb_packets_completed_in_window_set"], 1)
        self.assertEqual(summary["edge_pdb_satisfaction_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
