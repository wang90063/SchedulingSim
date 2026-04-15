import unittest

from scheduling_sim.models import LogicalChannel, Packet, RadioProfile, TrafficProfile, UserEquipment
from scheduling_sim.queue import ActiveQueue
from scheduling_sim.reinsert import ConstrainedInsertPolicy, TailAppendPolicy, TargetOnlyConstrainedInsertPolicy


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

    def test_constrained_insert_chooses_farthest_safe_position(self) -> None:
        queue = ActiveQueue()
        users = [self.make_ue(f"ue-{index}", remaining_bits=120) for index in range(5)]
        users[0].lc.head_packet.pdb_ms = 12
        for user in users:
            queue.activate(user)
        policy = ConstrainedInsertPolicy()
        policy.apply(
            queue,
            users[0],
            queue_wait_size=queue.size,
            service_bits_per_decision=120,
            now_ms=8,
            current_phase="S",
            max_ue_per_slot=2,
        )
        ordered = [user.ue_id for user in queue.ordered_users()]
        self.assertEqual(ordered.index(users[0].ue_id), 3)

    def test_constrained_insert_uses_deadline_guard_to_move_target_earlier(self) -> None:
        queue = ActiveQueue()
        users = [self.make_ue(f"ue-{index}", remaining_bits=120) for index in range(5)]
        users[0].lc.head_packet.pdb_ms = 12
        for user in users:
            queue.activate(user)
        policy = ConstrainedInsertPolicy(deadline_guard_ms=5)
        policy.apply(
            queue,
            users[0],
            queue_wait_size=queue.size,
            service_bits_per_decision=120,
            now_ms=8,
            current_phase="S",
            max_ue_per_slot=2,
        )
        ordered = [user.ue_id for user in queue.ordered_users()]
        self.assertEqual(ordered.index(users[0].ue_id), 1)

    def test_constrained_insert_treats_no_pdb_packet_as_tail_safe(self) -> None:
        queue = ActiveQueue()
        users = [self.make_ue(f"ue-{index}", remaining_bits=120) for index in range(3)]
        users[0].lc.head_packet.pdb_ms = None
        users[0].traffic_profile = TrafficProfile(packet_bits=120, pdb_ms=None)
        for user in users:
            queue.activate(user)
        ConstrainedInsertPolicy().apply(
            queue,
            users[0],
            queue_wait_size=queue.size,
            service_bits_per_decision=120,
            now_ms=8,
            current_phase="S",
            max_ue_per_slot=2,
        )
        self.assertEqual(queue.ordered_users()[-1].ue_id, users[0].ue_id)

    def test_target_only_constrained_insert_falls_back_to_tail_for_non_target_packets(self) -> None:
        queue = ActiveQueue()
        users = [self.make_ue(f"ue-{index}") for index in range(5)]
        for user in users:
            queue.activate(user)
        policy = TargetOnlyConstrainedInsertPolicy()
        policy.apply(
            queue,
            users[0],
            queue_wait_size=queue.size,
            service_bits_per_decision=40,
            now_ms=12,
            current_phase="S",
            max_ue_per_slot=2,
        )
        ordered = [user.ue_id for user in queue.ordered_users()]
        self.assertEqual(ordered[-1], users[0].ue_id)


if __name__ == "__main__":
    unittest.main()
