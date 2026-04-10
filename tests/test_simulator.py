import unittest

from scheduling_sim.config import (
    AppConfig,
    RadioConfig,
    RadioSection,
    ReportConfig,
    ResourcesConfig,
    SchedulerConfig,
    SimulationConfig,
    TrafficConfig,
    TrafficSection,
)
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


if __name__ == "__main__":
    unittest.main()


class DummyMetrics:
    pass


class SimulatorCycleTests(unittest.TestCase):
    def test_u_slot_arrivals_become_eligible_next_cycle(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(cycles=1, slot_duration_ms=1, tdd_pattern="DSUUU"),
            resources=ResourcesConfig(total_prb_per_u_slot=10, max_ue_per_slot=2),
            traffic=TrafficSection(
                center=TrafficConfig(count=1, period_slots=1, packet_bits=30, pdb_ms=30),
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
        simulator.inject_packet(users[0], packet_bits=50, cycle_index=0, slot_name="U1")
        self.assertEqual(users[0].lc.eligible_cycle, 1)

    def test_d_then_s_use_fresh_head_k_after_reinsert(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(cycles=1, slot_duration_ms=1, tdd_pattern="DSUUU"),
            resources=ResourcesConfig(total_prb_per_u_slot=10, max_ue_per_slot=2),
            traffic=TrafficSection(
                center=TrafficConfig(count=3, period_slots=1, packet_bits=30, pdb_ms=30),
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
        for user in users:
            simulator.inject_packet(user, packet_bits=50, cycle_index=0, slot_name="D")
            simulator.queue.activate(user)
        d_candidates = [ue.ue_id for ue in simulator.collect_candidates("D")]
        simulator.finish_phase("D")
        s_candidates = [ue.ue_id for ue in simulator.collect_candidates("S")]
        self.assertNotEqual(d_candidates, s_candidates)
