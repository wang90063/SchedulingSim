import unittest

from scheduling_sim.models import LogicalChannel, Packet, RadioProfile, TrafficProfile, UserEquipment
from scheduling_sim.ranking import EpfRankingPolicy


class EpfRankingTests(unittest.TestCase):
    def test_higher_hol_and_lower_average_throughput_rank_first(self) -> None:
        ranking = EpfRankingPolicy()
        urgent = UserEquipment(
            ue_id="edge-urgent",
            lc=LogicalChannel("lc-1", [Packet("pkt-1", 0, 300, 300, 15, None)], eligible_cycle=0),
            is_edge_user=True,
            radio_profile=RadioProfile(bits_per_prb=10, per_u_slot_prb_cap=8),
            average_throughput=1.0,
            traffic_profile=TrafficProfile(packet_bits=300, pdb_ms=15),
            hol_ms=12,
        )
        relaxed = UserEquipment(
            ue_id="center-relaxed",
            lc=LogicalChannel("lc-2", [Packet("pkt-2", 0, 300, 300, 30, None)], eligible_cycle=0),
            is_edge_user=False,
            radio_profile=RadioProfile(bits_per_prb=20, per_u_slot_prb_cap=20),
            average_throughput=5.0,
            traffic_profile=TrafficProfile(packet_bits=300, pdb_ms=30),
            hol_ms=2,
        )
        ranked = ranking.rank([relaxed, urgent])
        self.assertEqual([ue.ue_id for ue in ranked], ["edge-urgent", "center-relaxed"])


if __name__ == "__main__":
    unittest.main()
