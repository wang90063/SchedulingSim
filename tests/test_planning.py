import unittest

from scheduling_sim.models import LogicalChannel, Packet, RadioProfile, TrafficProfile, UserEquipment
from scheduling_sim.planning import PhasePrbPlanner


class PhasePrbPlannerTests(unittest.TestCase):
    def make_edge(self) -> UserEquipment:
        return UserEquipment(
            ue_id="edge-0",
            lc=LogicalChannel("edge-lc", [Packet("pkt", 0, 1000, 1000, 15, None)], eligible_cycle=0),
            is_edge_user=True,
            radio_profile=RadioProfile(bits_per_prb=10, per_u_slot_prb_cap=6),
            average_throughput=1.0,
            traffic_profile=TrafficProfile(packet_bits=1000, pdb_ms=15),
            hol_ms=5,
        )

    def test_d_phase_uses_first_one_point_five_u_windows(self) -> None:
        planner = PhasePrbPlanner(total_prb_per_u_slot=10)
        plan = planner.plan_phase("D", [self.make_edge()])
        self.assertEqual(plan.slot_prb_budgets, [10, 5, 0])
        self.assertEqual(sum(grant.prb_count for grant in plan.slot_grants[0]), 6)


if __name__ == "__main__":
    unittest.main()
