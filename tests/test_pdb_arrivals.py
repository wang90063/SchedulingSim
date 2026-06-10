import unittest

from scheduling_sim.models import LogicalChannel, RadioProfile, TrafficProfile, UserEquipment
from scheduling_sim.pdb_arrivals import build_periodic_pdb_schedule


class PeriodicPdbArrivalTests(unittest.TestCase):
    def _make_edge_user(
        self,
        ue_id: str,
        *,
        pdb_ms: int,
        initial_phase_mode: str,
    ) -> UserEquipment:
        return UserEquipment(
            ue_id=ue_id,
            lc=LogicalChannel(lc_id=f"{ue_id}-lc", packets=[]),
            is_edge_user=True,
            radio_profile=RadioProfile(user_class="edge", bits_per_prb=10, per_u_slot_prb_cap=18),
            average_throughput=1.0,
            traffic_profile=TrafficProfile(
                packet_bits=80000,
                pdb_ms=pdb_ms,
                arrival_mode="periodic_by_pdb",
                initial_phase_mode=initial_phase_mode,
            ),
        )

    def test_none_phase_builds_exact_pdb_multiples(self) -> None:
        user = self._make_edge_user("edge-0", pdb_ms=200, initial_phase_mode="none")

        schedule = build_periodic_pdb_schedule([user], random_seed=7, analysis_window_ms=1000)

        self.assertEqual(schedule[user.ue_id], [0, 200, 400, 600, 800])

    def test_uniform_phase_is_seeded_and_first_offset_stays_within_pdb(self) -> None:
        user = self._make_edge_user("edge-0", pdb_ms=200, initial_phase_mode="uniform_0_to_pdb")

        first = build_periodic_pdb_schedule([user], random_seed=11, analysis_window_ms=1000)
        second = build_periodic_pdb_schedule([user], random_seed=11, analysis_window_ms=1000)

        self.assertEqual(first, second)
        self.assertGreaterEqual(first[user.ue_id][0], 0)
        self.assertLess(first[user.ue_id][0], 200)


if __name__ == "__main__":
    unittest.main()
