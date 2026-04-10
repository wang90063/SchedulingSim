import unittest

from scheduling_sim.models import LogicalChannel, Packet, RadioProfile, UserEquipment
from scheduling_sim.queue import ActiveQueue


class ActiveQueueTests(unittest.TestCase):
    def make_ue(self, ue_id: str) -> UserEquipment:
        packet = Packet(
            packet_id=f"{ue_id}-pkt",
            arrival_time=0,
            size_bits=100,
            remaining_bits=100,
            pdb_ms=15,
            completion_time=None,
        )
        lc = LogicalChannel(lc_id=f"{ue_id}-lc", packets=[packet], eligible_cycle=0)
        radio = RadioProfile(bits_per_prb=10, per_u_slot_prb_cap=8)
        return UserEquipment(
            ue_id=ue_id,
            lc=lc,
            is_edge_user=True,
            radio_profile=radio,
            average_throughput=1.0,
        )

    def test_activate_only_once_for_same_user(self) -> None:
        queue = ActiveQueue()
        ue = self.make_ue("ue-1")
        queue.activate(ue)
        queue.activate(ue)
        self.assertEqual(queue.size, 1)

    def test_peek_head_k_preserves_order(self) -> None:
        queue = ActiveQueue()
        for index in range(4):
            queue.activate(self.make_ue(f"ue-{index}"))
        head = queue.peek_head_k(2)
        self.assertEqual([ue.ue_id for ue in head], ["ue-0", "ue-1"])


if __name__ == "__main__":
    unittest.main()
