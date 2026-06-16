import random
import unittest

from scheduling_sim.models import (
    CurrentRadioState,
    LogicalChannel,
    Packet,
    RadioProfile,
    UserEquipment,
)
from scheduling_sim.simulator import UlSimulator


class _NullMetrics:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class _StubQueue:
    def contains(self, user) -> bool:
        return False

    def deactivate(self, user) -> None:
        return None


def _edge_user_with_bler(bler: float, remaining: int = 1000) -> UserEquipment:
    packet = Packet(
        packet_id="p0",
        arrival_time=0,
        size_bits=remaining,
        remaining_bits=remaining,
        pdb_ms=100,
        completion_time=None,
        is_target=True,
    )
    lc = LogicalChannel(lc_id="lc0", packets=[packet])
    user = UserEquipment(
        ue_id="edge-0",
        lc=lc,
        is_edge_user=True,
        radio_profile=RadioProfile(user_class="edge"),
        average_throughput=0.0,
    )
    user.current_radio_state = CurrentRadioState(
        snr_db=0.0, mcs_index=4, bits_per_prb=48, per_u_slot_prb_cap=None, bler=bler
    )
    return user


class HarqConsumeTests(unittest.TestCase):
    def _make_sim(self) -> UlSimulator:
        sim = UlSimulator.__new__(UlSimulator)
        sim.metrics = _NullMetrics()
        sim.queue = _StubQueue()
        sim._harq_rng = random.Random(1)
        sim._cycle_served_bits_by_ue = {}
        sim.analysis_window_ms = 10**9
        return sim

    def test_bler_zero_always_delivers(self) -> None:
        sim = self._make_sim()
        user = _edge_user_with_bler(0.0, remaining=500)
        sim._consume_user_bits(user, bits_budget=500, now_ms=5, in_analysis_window=True)
        self.assertIsNone(user.lc.head_packet)

    def test_bler_one_never_delivers_and_counts_retx(self) -> None:
        sim = self._make_sim()
        user = _edge_user_with_bler(1.0, remaining=500)
        sim._consume_user_bits(user, bits_budget=500, now_ms=5, in_analysis_window=True)
        self.assertIsNotNone(user.lc.head_packet)
        self.assertEqual(user.lc.head_packet.remaining_bits, 500)
        self.assertEqual(user.lc.head_packet.retransmission_count, 1)

    def test_failed_tb_records_wasted_prb(self) -> None:
        sim = self._make_sim()
        recorded = []
        sim.metrics.record_tx_outcome = lambda **kw: recorded.append(kw)
        user = _edge_user_with_bler(1.0, remaining=480)
        sim._consume_user_bits(user, bits_budget=480, now_ms=5, in_analysis_window=True)
        self.assertEqual(len(recorded), 1)
        self.assertFalse(recorded[0]["success"])
        self.assertEqual(recorded[0]["prb_count"], 10)  # ceil(480 / 48)


if __name__ == "__main__":
    unittest.main()
