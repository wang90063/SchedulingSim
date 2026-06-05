import unittest

from scheduling_sim.config import (
    AppConfig,
    RadioClassConfig,
    RadioSection,
    ReportConfig,
    ResourcesConfig,
    SchedulerConfig,
    SimulationConfig,
    TrafficConfig,
    TrafficSection,
)
from scheduling_sim.edge_ratio_packet_sweep import (
    apply_edge_pdb_assignments,
    build_case_config,
    packet_bits_from_kb,
    random_pdb_by_ue,
    scanned_edge_user_count,
    uniform_pdb_by_ue,
)
from scheduling_sim.scenario import ScenarioFactory


class EdgeRatioPacketSweepHelpersTests(unittest.TestCase):
    def _base_config(self) -> AppConfig:
        return AppConfig(
            simulation=SimulationConfig(
                cycles=1000,
                slot_duration_ms=1,
                tdd_pattern="DSUUU",
                random_seed=7,
                stop_when_target_edge_finished=True,
                deadline_guard_ms=10,
            ),
            resources=ResourcesConfig(total_prb_per_u_slot=273, max_ue_per_slot=16),
            traffic=TrafficSection(
                center=TrafficConfig(count=29, period_slots=6, packet_bits=960, pdb_ms=None, gbr_bps=7000),
                edge=TrafficConfig(count=3, packet_bits=80000, pdb_ms=800),
            ),
            radio=RadioSection(
                center=RadioClassConfig(base_snr_db=16.0, snr_min_db=-10.0, snr_max_db=25.0),
                edge=RadioClassConfig(
                    base_snr_db=0.0,
                    snr_min_db=-10.0,
                    snr_max_db=10.0,
                    edge_per_u_slot_prb_cap=273,
                ),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="business_aware_constrained_insert"),
            report=ReportConfig(output_dir="outputs/test", keep_slot_trace=False),
        )

    def test_scanned_edge_user_count_matches_historical_rounding_rule(self) -> None:
        self.assertEqual(scanned_edge_user_count(total_users=32, requested_edge_ratio_pct=10), 3)
        self.assertEqual(scanned_edge_user_count(total_users=32, requested_edge_ratio_pct=50), 16)
        self.assertEqual(scanned_edge_user_count(total_users=32, requested_edge_ratio_pct=90), 29)

    def test_packet_bits_from_kb_uses_decimal_kilobytes(self) -> None:
        self.assertEqual(packet_bits_from_kb(10), 80000)
        self.assertEqual(packet_bits_from_kb(200), 1600000)

    def test_build_case_config_overrides_counts_policy_and_packet_size(self) -> None:
        config = build_case_config(
            self._base_config(),
            total_users=32,
            requested_edge_ratio_pct=20,
            pdb_packet_kb=200,
            policy="tail_append",
        )
        self.assertEqual(config.traffic.center.count, 26)
        self.assertEqual(config.traffic.edge.count, 6)
        self.assertEqual(config.traffic.edge.packet_bits, 1600000)
        self.assertEqual(config.scheduler.reinsert_policy, "tail_append")

    def test_apply_edge_pdb_assignments_updates_edge_profiles_only(self) -> None:
        users = ScenarioFactory(
            build_case_config(
                self._base_config(),
                total_users=32,
                requested_edge_ratio_pct=20,
                pdb_packet_kb=30,
                policy="tail_append",
            )
        ).build_users()
        apply_edge_pdb_assignments(
            users,
            {"edge-0": 200, "edge-1": None, "edge-2": 800, "edge-3": 600, "edge-4": 400, "edge-5": 200},
        )
        edge_pdbs = {user.ue_id: user.traffic_profile.pdb_ms for user in users if user.is_edge_user}
        center_pdbs = {user.ue_id: user.traffic_profile.pdb_ms for user in users if not user.is_edge_user}
        self.assertEqual(edge_pdbs["edge-0"], 200)
        self.assertIsNone(edge_pdbs["edge-1"])
        self.assertTrue(all(value is None for value in center_pdbs.values()))

    def test_random_and_uniform_assignment_helpers_are_deterministic(self) -> None:
        edge_ids = [f"edge-{index}" for index in range(4)]
        random_one = random_pdb_by_ue(edge_ids=edge_ids, pdb_choices=[None, 200, 400, 600, 800], seed=77)
        random_two = random_pdb_by_ue(edge_ids=edge_ids, pdb_choices=[None, 200, 400, 600, 800], seed=77)
        uniform = uniform_pdb_by_ue(edge_ids=edge_ids, pdb_ms=600)
        self.assertEqual(random_one, random_two)
        self.assertEqual(uniform, {"edge-0": 600, "edge-1": 600, "edge-2": 600, "edge-3": 600})
