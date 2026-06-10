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
from scheduling_sim.models import LogicalChannel, RadioProfile, TrafficProfile, UserEquipment
from scheduling_sim.pdb_arrivals import build_periodic_pdb_schedule, resolve_analysis_window_ms


class PeriodicPdbArrivalTests(unittest.TestCase):
    def _make_user(
        self,
        ue_id: str,
        *,
        is_edge_user: bool,
        pdb_ms: int,
        arrival_mode: str = "periodic_by_pdb",
        initial_phase_mode: str,
    ) -> UserEquipment:
        return UserEquipment(
            ue_id=ue_id,
            lc=LogicalChannel(lc_id=f"{ue_id}-lc", packets=[]),
            is_edge_user=is_edge_user,
            radio_profile=RadioProfile(
                user_class="edge" if is_edge_user else "center",
                bits_per_prb=10,
                per_u_slot_prb_cap=18,
            ),
            average_throughput=1.0,
            traffic_profile=TrafficProfile(
                packet_bits=80000,
                pdb_ms=pdb_ms,
                arrival_mode=arrival_mode,
                initial_phase_mode=initial_phase_mode,
            ),
        )

    def _make_config(
        self,
        *,
        cycles: int = 2,
        slot_duration_ms: int = 1,
        tdd_pattern: str = "DSUUU",
        analysis_window_ms: int | None = None,
        edge_arrival_mode: str = "single_burst",
    ) -> AppConfig:
        return AppConfig(
            simulation=SimulationConfig(
                cycles=cycles,
                slot_duration_ms=slot_duration_ms,
                tdd_pattern=tdd_pattern,
                analysis_window_ms=analysis_window_ms,
            ),
            resources=ResourcesConfig(total_prb_per_u_slot=10, max_ue_per_slot=2),
            traffic=TrafficSection(
                center=TrafficConfig(count=1, period_slots=1, packet_bits=30, pdb_ms=30),
                edge=TrafficConfig(
                    count=1,
                    packet_bits=80000,
                    pdb_ms=200,
                    arrival_mode=edge_arrival_mode,
                ),
            ),
            radio=RadioSection(
                center=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=10),
                edge=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=10),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/test", keep_slot_trace=False),
        )

    def test_explicit_analysis_window_ms_wins(self) -> None:
        config = self._make_config(analysis_window_ms=4321, edge_arrival_mode="periodic_by_pdb")

        self.assertEqual(resolve_analysis_window_ms(config), 4321)

    def test_periodic_by_pdb_defaults_analysis_window_to_10000_ms(self) -> None:
        config = self._make_config(analysis_window_ms=None, edge_arrival_mode="periodic_by_pdb")

        self.assertEqual(resolve_analysis_window_ms(config), 10000)

    def test_legacy_analysis_window_falls_back_to_configured_runtime(self) -> None:
        config = self._make_config(cycles=4, slot_duration_ms=2, analysis_window_ms=None, edge_arrival_mode="single_burst")

        self.assertEqual(resolve_analysis_window_ms(config), 40)

    def test_none_phase_builds_exact_pdb_multiples(self) -> None:
        user = self._make_user("edge-0", is_edge_user=True, pdb_ms=200, initial_phase_mode="none")

        schedule = build_periodic_pdb_schedule([user], random_seed=7, analysis_window_ms=1000)

        self.assertEqual(schedule[user.ue_id], [0, 200, 400, 600, 800])
        self.assertNotIn(1000, schedule[user.ue_id])

    def test_uniform_phase_is_seeded_and_first_offset_stays_within_pdb(self) -> None:
        user = self._make_user("edge-0", is_edge_user=True, pdb_ms=200, initial_phase_mode="uniform_0_to_pdb")

        first = build_periodic_pdb_schedule([user], random_seed=11, analysis_window_ms=1000)
        second = build_periodic_pdb_schedule([user], random_seed=11, analysis_window_ms=1000)

        self.assertEqual(first, second)
        self.assertGreaterEqual(first[user.ue_id][0], 0)
        self.assertLess(first[user.ue_id][0], 200)

    def test_schedule_includes_only_edge_users_in_periodic_mode(self) -> None:
        periodic_edge = self._make_user("edge-0", is_edge_user=True, pdb_ms=200, initial_phase_mode="none")
        center_user = self._make_user("center-0", is_edge_user=False, pdb_ms=200, initial_phase_mode="none")
        burst_edge = self._make_user(
            "edge-1",
            is_edge_user=True,
            pdb_ms=200,
            arrival_mode="single_burst",
            initial_phase_mode="none",
        )

        schedule = build_periodic_pdb_schedule(
            [periodic_edge, center_user, burst_edge],
            random_seed=7,
            analysis_window_ms=1000,
        )

        self.assertEqual(schedule, {"edge-0": [0, 200, 400, 600, 800]})

    def test_schedule_arrivals_stay_strictly_before_analysis_window(self) -> None:
        user = self._make_user("edge-0", is_edge_user=True, pdb_ms=300, initial_phase_mode="none")

        schedule = build_periodic_pdb_schedule([user], random_seed=7, analysis_window_ms=1000)

        self.assertEqual(schedule[user.ue_id], [0, 300, 600, 900])
        self.assertTrue(all(arrival_ms < 1000 for arrival_ms in schedule[user.ue_id]))


if __name__ == "__main__":
    unittest.main()
