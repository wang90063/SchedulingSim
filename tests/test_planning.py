import unittest

from scheduling_sim.config import (
    AppConfig,
    McsEntryConfig,
    RadioConfig,
    RadioClassConfig,
    RadioSection,
    ReportConfig,
    ResourcesConfig,
    SchedulerConfig,
    SimulationConfig,
    TrafficConfig,
    TrafficSection,
    WirelessEnvConfig,
)
from scheduling_sim.models import (
    CurrentRadioState,
    LogicalChannel,
    Packet,
    RadioProfile,
    TrafficProfile,
    UserEquipment,
)
from scheduling_sim.planning import PhasePrbPlanner
from scheduling_sim.scenario import ScenarioFactory


class PhasePrbPlannerTests(unittest.TestCase):
    def test_d_phase_applies_prb_cap_only_to_edge_users(self) -> None:
        edge = UserEquipment(
            ue_id="edge-0",
            lc=LogicalChannel("edge-lc", [Packet("pkt", 0, 1000, 1000, 15, None)], eligible_cycle=0),
            is_edge_user=True,
            radio_profile=RadioProfile(bits_per_prb=10, per_u_slot_prb_cap=1),
            average_throughput=1.0,
            traffic_profile=TrafficProfile(packet_bits=1000, pdb_ms=15),
            current_radio_state=CurrentRadioState(snr_db=0.0, mcs_index=0, bits_per_prb=10, per_u_slot_prb_cap=3),
            hol_ms=5,
        )
        center = UserEquipment(
            ue_id="center-0",
            lc=LogicalChannel("center-lc", [Packet("pkt", 0, 1000, 1000, 15, None)], eligible_cycle=0),
            is_edge_user=False,
            radio_profile=RadioProfile(bits_per_prb=10, per_u_slot_prb_cap=1),
            average_throughput=1.0,
            traffic_profile=TrafficProfile(packet_bits=1000, pdb_ms=15),
            current_radio_state=CurrentRadioState(snr_db=0.0, mcs_index=0, bits_per_prb=10, per_u_slot_prb_cap=1),
            hol_ms=5,
        )
        planner = PhasePrbPlanner(total_prb_per_u_slot=10)
        plan = planner.plan_phase("D", [edge, center])
        slot0 = {grant.ue_id: grant.prb_count for grant in plan.slot_grants[0]}
        self.assertEqual(slot0["edge-0"], 3)
        self.assertEqual(slot0["center-0"], 7)
        self.assertEqual(sum(slot0.values()), 10)

    def test_bits_planned_uses_current_radio_state_bits_per_prb(self) -> None:
        center = UserEquipment(
            ue_id="center-1",
            lc=LogicalChannel("center-lc-1", [Packet("pkt", 0, 1000, 1000, 15, None)], eligible_cycle=0),
            is_edge_user=False,
            radio_profile=RadioProfile(bits_per_prb=2, per_u_slot_prb_cap=10),
            average_throughput=1.0,
            traffic_profile=TrafficProfile(packet_bits=1000, pdb_ms=15),
            current_radio_state=CurrentRadioState(snr_db=0.0, mcs_index=0, bits_per_prb=9, per_u_slot_prb_cap=None),
            hol_ms=5,
        )
        plan = PhasePrbPlanner(total_prb_per_u_slot=10).plan_phase("D", [center])
        self.assertEqual(plan.slot_grants[0][0].bits_planned, 90)

    def test_falls_back_to_radio_profile_cap_without_current_state(self) -> None:
        edge = UserEquipment(
            ue_id="edge-1",
            lc=LogicalChannel("edge-lc-1", [Packet("pkt", 0, 1000, 1000, 15, None)], eligible_cycle=0),
            is_edge_user=True,
            radio_profile=RadioProfile(bits_per_prb=10, per_u_slot_prb_cap=6),
            average_throughput=1.0,
            traffic_profile=TrafficProfile(packet_bits=1000, pdb_ms=15),
            current_radio_state=None,
            hol_ms=5,
        )
        plan = PhasePrbPlanner(total_prb_per_u_slot=10).plan_phase("D", [edge])
        self.assertEqual(plan.slot_grants[0][0].prb_count, 6)

    def test_scenario_factory_accepts_legacy_radio_config(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(cycles=1, slot_duration_ms=1, tdd_pattern="DSUUU"),
            resources=ResourcesConfig(total_prb_per_u_slot=10, max_ue_per_slot=4),
            traffic=TrafficSection(
                center=TrafficConfig(count=1, period_slots=1, packet_bits=100, pdb_ms=30),
                edge=TrafficConfig(count=1, burst_cycle_interval=1, packet_bits=1000, pdb_ms=15),
            ),
            radio=RadioSection(
                center=RadioConfig(bits_per_prb=12, per_u_slot_prb_cap=10),
                edge=RadioConfig(bits_per_prb=6, per_u_slot_prb_cap=4),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/test", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()
        center_user = next(user for user in users if not user.is_edge_user)
        edge_user = next(user for user in users if user.is_edge_user)
        self.assertEqual(center_user.radio_profile.bits_per_prb, 12)
        self.assertEqual(edge_user.radio_profile.per_u_slot_prb_cap, 4)
        self.assertEqual(edge_user.current_radio_state.per_u_slot_prb_cap, 4)
        plan = PhasePrbPlanner(total_prb_per_u_slot=10).plan_phase("D", [edge_user])
        self.assertEqual(plan.slot_grants[0][0].prb_count, 4)

    def test_scenario_factory_seeds_current_radio_state_from_new_radio_schema(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(cycles=1, slot_duration_ms=1, tdd_pattern="DSUUU", random_seed=7),
            resources=ResourcesConfig(total_prb_per_u_slot=10, max_ue_per_slot=4),
            traffic=TrafficSection(
                center=TrafficConfig(count=1, period_slots=1, packet_bits=100, pdb_ms=30),
                edge=TrafficConfig(count=1, burst_cycle_interval=1, packet_bits=1000, pdb_ms=15),
            ),
            radio=RadioSection(
                environment=WirelessEnvConfig(
                    alpha=0.95,
                    jitter_std_db=0.2,
                    mcs_table=[
                        McsEntryConfig(snr_db=0.0, mcs_index=0, bits_per_prb=4),
                        McsEntryConfig(snr_db=6.0, mcs_index=1, bits_per_prb=8),
                    ],
                ),
                center=RadioClassConfig(base_snr_db=16.0, snr_min_db=10.0, snr_max_db=22.0, bits_per_prb=8),
                edge=RadioClassConfig(
                    base_snr_db=4.0,
                    snr_min_db=-2.0,
                    snr_max_db=8.0,
                    edge_per_u_slot_prb_cap=3,
                    bits_per_prb=4,
                ),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/test", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()
        center_user = next(user for user in users if not user.is_edge_user)
        edge_user = next(user for user in users if user.is_edge_user)
        self.assertEqual(center_user.current_radio_state.bits_per_prb, 8)
        self.assertIsNone(center_user.current_radio_state.per_u_slot_prb_cap)
        self.assertEqual(edge_user.current_radio_state.bits_per_prb, 4)
        self.assertEqual(edge_user.current_radio_state.per_u_slot_prb_cap, 3)


if __name__ == "__main__":
    unittest.main()
