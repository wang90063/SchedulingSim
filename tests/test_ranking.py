import unittest

from scheduling_sim.models import (
    CurrentRadioState,
    LogicalChannel,
    Packet,
    RadioProfile,
    TrafficProfile,
    UserEquipment,
)
from scheduling_sim.ranking import EpfRankingPolicy


class EpfRankingTests(unittest.TestCase):
    def test_current_radio_state_bits_per_prb_drives_instantaneous_rate(self) -> None:
        ranking = EpfRankingPolicy()
        low_current_rate = UserEquipment(
            ue_id="ue-low-current",
            lc=LogicalChannel("lc-1", [Packet("pkt-1", 0, 300, 300, 30, None)], eligible_cycle=0),
            is_edge_user=False,
            radio_profile=RadioProfile(bits_per_prb=100, per_u_slot_prb_cap=10),
            average_throughput=4.0,
            traffic_profile=TrafficProfile(packet_bits=300, pdb_ms=30),
            current_radio_state=CurrentRadioState(snr_db=0.0, mcs_index=0, bits_per_prb=4, per_u_slot_prb_cap=None),
            hol_ms=5,
        )
        high_current_rate = UserEquipment(
            ue_id="ue-high-current",
            lc=LogicalChannel("lc-2", [Packet("pkt-2", 0, 300, 300, 30, None)], eligible_cycle=0),
            is_edge_user=False,
            radio_profile=RadioProfile(bits_per_prb=1, per_u_slot_prb_cap=10),
            average_throughput=4.0,
            traffic_profile=TrafficProfile(packet_bits=300, pdb_ms=30),
            current_radio_state=CurrentRadioState(snr_db=0.0, mcs_index=0, bits_per_prb=10, per_u_slot_prb_cap=None),
            hol_ms=5,
        )
        ranked = ranking.rank([low_current_rate, high_current_rate])
        self.assertEqual([ue.ue_id for ue in ranked], ["ue-high-current", "ue-low-current"])

    def test_falls_back_to_radio_profile_bits_per_prb_without_current_state(self) -> None:
        ranking = EpfRankingPolicy()
        low_profile_rate = UserEquipment(
            ue_id="ue-low-profile",
            lc=LogicalChannel("lc-3", [Packet("pkt-3", 0, 300, 300, 30, None)], eligible_cycle=0),
            is_edge_user=False,
            radio_profile=RadioProfile(bits_per_prb=4, per_u_slot_prb_cap=10),
            average_throughput=4.0,
            traffic_profile=TrafficProfile(packet_bits=300, pdb_ms=30),
            current_radio_state=None,
            hol_ms=5,
        )
        high_profile_rate = UserEquipment(
            ue_id="ue-high-profile",
            lc=LogicalChannel("lc-4", [Packet("pkt-4", 0, 300, 300, 30, None)], eligible_cycle=0),
            is_edge_user=False,
            radio_profile=RadioProfile(bits_per_prb=10, per_u_slot_prb_cap=10),
            average_throughput=4.0,
            traffic_profile=TrafficProfile(packet_bits=300, pdb_ms=30),
            current_radio_state=None,
            hol_ms=5,
        )
        ranked = ranking.rank([low_profile_rate, high_profile_rate])
        self.assertEqual([ue.ue_id for ue in ranked], ["ue-high-profile", "ue-low-profile"])

    def test_no_pdb_user_uses_pure_epf_ratio(self) -> None:
        ranking = EpfRankingPolicy()
        no_pdb_fast = UserEquipment(
            ue_id="ue-no-pdb-fast",
            lc=LogicalChannel("lc-fast", [Packet("pkt-fast", 0, 300, 300, None, None)], eligible_cycle=0),
            is_edge_user=False,
            radio_profile=RadioProfile(bits_per_prb=12, per_u_slot_prb_cap=10),
            average_throughput=3.0,
            traffic_profile=TrafficProfile(packet_bits=300, pdb_ms=None),
            current_radio_state=None,
            hol_ms=29,
        )
        no_pdb_slow = UserEquipment(
            ue_id="ue-no-pdb-slow",
            lc=LogicalChannel("lc-slow", [Packet("pkt-slow", 0, 300, 300, None, None)], eligible_cycle=0),
            is_edge_user=False,
            radio_profile=RadioProfile(bits_per_prb=8, per_u_slot_prb_cap=10),
            average_throughput=4.0,
            traffic_profile=TrafficProfile(packet_bits=300, pdb_ms=None),
            current_radio_state=None,
            hol_ms=1,
        )
        ranked = ranking.rank([no_pdb_slow, no_pdb_fast])
        self.assertEqual([ue.ue_id for ue in ranked], ["ue-no-pdb-fast", "ue-no-pdb-slow"])

    def test_pdb_user_keeps_overdue_priority(self) -> None:
        ranking = EpfRankingPolicy()
        overdue = UserEquipment(
            ue_id="ue-overdue",
            lc=LogicalChannel("lc-overdue", [Packet("pkt-overdue", 0, 300, 300, 15, None)], eligible_cycle=0),
            is_edge_user=False,
            radio_profile=RadioProfile(bits_per_prb=4, per_u_slot_prb_cap=10),
            average_throughput=100.0,
            traffic_profile=TrafficProfile(packet_bits=300, pdb_ms=15),
            current_radio_state=None,
            hol_ms=20,
        )
        fresh = UserEquipment(
            ue_id="ue-fresh",
            lc=LogicalChannel("lc-fresh", [Packet("pkt-fresh", 0, 300, 300, 30, None)], eligible_cycle=0),
            is_edge_user=False,
            radio_profile=RadioProfile(bits_per_prb=20, per_u_slot_prb_cap=10),
            average_throughput=1.0,
            traffic_profile=TrafficProfile(packet_bits=300, pdb_ms=30),
            current_radio_state=None,
            hol_ms=1,
        )
        ranked = ranking.rank([fresh, overdue])
        self.assertEqual([ue.ue_id for ue in ranked], ["ue-overdue", "ue-fresh"])


if __name__ == "__main__":
    unittest.main()
