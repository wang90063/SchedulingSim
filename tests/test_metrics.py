import unittest

from scheduling_sim.metrics import MetricsCollector


class RetxMetricsTests(unittest.TestCase):
    def test_tx_outcome_counts_nacks_and_wasted_prb(self) -> None:
        m = MetricsCollector()
        m.record_tx_outcome(user_class="edge", success=False, prb_count=10, in_analysis_window=True)
        m.record_tx_outcome(user_class="edge", success=True, prb_count=10, in_analysis_window=True)
        m.record_tx_outcome(user_class="center", success=False, prb_count=3, in_analysis_window=True)
        summary = m.build_summary(total_prb_used=23, total_prb_available=23)
        self.assertEqual(summary["edge_retransmission_count"], 1)
        self.assertEqual(summary["edge_wasted_prb"], 10)
        self.assertEqual(summary["center_retransmission_count"], 1)
        self.assertEqual(summary["center_wasted_prb"], 3)
        self.assertEqual(summary["retransmission_count"], 2)
        self.assertEqual(summary["wasted_prb"], 13)

    def test_success_only_keeps_counters_zero(self) -> None:
        m = MetricsCollector()
        m.record_tx_outcome(user_class="edge", success=True, prb_count=5, in_analysis_window=True)
        summary = m.build_summary(total_prb_used=5, total_prb_available=5)
        self.assertEqual(summary["retransmission_count"], 0)
        self.assertEqual(summary["wasted_prb"], 0)
        self.assertEqual(summary["target_edge_retransmission_count"], 0)

    def test_packet_completed_records_retransmission_count(self) -> None:
        m = MetricsCollector()
        m.record_packet_completed(
            packet_id="p0",
            completion_time=50,
            arrival_time=0,
            pdb_ms=100,
            bits_sent=1000,
            user_class="edge",
            ue_id="edge-0",
            is_target=True,
            retransmission_count=4,
        )
        summary = m.build_summary(total_prb_used=10, total_prb_available=10, slot_duration_ms=1)
        self.assertEqual(summary["target_edge_retransmission_count"], 4)


if __name__ == "__main__":
    unittest.main()
