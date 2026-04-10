import unittest

from scheduling_sim.models import LogicalChannel, Packet, RadioProfile, TrafficProfile, UserEquipment
from scheduling_sim.queue import ActiveQueue
from scheduling_sim.reinsert import ConstrainedInsertPolicy, TailAppendPolicy


class ReinsertionPolicyTests(unittest.TestCase):
    def make_ue(self, ue_id: str, remaining_bits: int = 600) -> UserEquipment:
        return UserEquipment(
            ue_id=ue_id,
            lc=LogicalChannel(
                ue_id + "-lc",
                [Packet(ue_id + "-pkt", 0, remaining_bits, remaining_bits, 15, None)],
                eligible_cycle=0,
            ),
            is_edge_user=True,
            radio_profile=RadioProfile(bits_per_prb=10, per_u_slot_prb_cap=4),
            average_throughput=1.0,
            traffic_profile=TrafficProfile(packet_bits=remaining_bits, pdb_ms=15),
            hol_ms=8,
        )

    def test_tail_append_moves_user_to_end(self) -> None:
        queue = ActiveQueue()
        ue0 = self.make_ue("ue-0")
        ue1 = self.make_ue("ue-1")
        queue.activate(ue0)
        queue.activate(ue1)
        TailAppendPolicy().apply(
            queue,
            ue0,
            queue_wait_size=queue.size,
            service_bits_per_decision=120,
            now_ms=8,
            current_phase="D",
            max_ue_per_slot=2,
        )
        self.assertEqual([user.ue_id for user in queue.peek_head_k(2)], ["ue-1", "ue-0"])

    def test_constrained_insert_places_user_inside_next_candidate_window_when_tail_is_unsafe(self) -> None:
        queue = ActiveQueue()
        users = [self.make_ue(f"ue-{index}") for index in range(5)]
        for user in users:
            queue.activate(user)
        policy = ConstrainedInsertPolicy()
        policy.apply(
            queue,
            users[0],
            queue_wait_size=queue.size,
            service_bits_per_decision=40,
            now_ms=12,
            current_phase="S",
            max_ue_per_slot=2,
        )
        self.assertIn(users[0], queue.peek_head_k(2))


if __name__ == "__main__":
    unittest.main()
