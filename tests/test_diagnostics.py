import unittest
from types import SimpleNamespace

from scheduling_sim.diagnostics import (
    TargetEdgeDiagnosticCollector,
    build_target_row,
    classify_dominance_label,
)
from scheduling_sim.models import CurrentRadioState, LogicalChannel, Packet, RadioProfile, UserEquipment
from scheduling_sim.simulator import UlSimulator


class TestClassifyDominanceLabel(unittest.TestCase):
    def test_not_pending_when_target_absent(self) -> None:
        self.assertEqual(
            classify_dominance_label(
                is_pending=False,
                in_candidate_window=False,
                hol_ms=0,
                pdb_ms=None,
            ),
            "not_pending",
        )

    def test_queue_limited_before_candidate_window(self) -> None:
        self.assertEqual(
            classify_dominance_label(
                is_pending=True,
                in_candidate_window=False,
                hol_ms=0,
                pdb_ms=None,
            ),
            "queue_limited",
        )

    def test_spectral_dominated_before_half_pdb(self) -> None:
        self.assertEqual(
            classify_dominance_label(
                is_pending=True,
                in_candidate_window=True,
                hol_ms=200,
                pdb_ms=500,
            ),
            "spectral_dominated",
        )

    def test_pdb_dominated_from_half_pdb(self) -> None:
        self.assertEqual(
            classify_dominance_label(
                is_pending=True,
                in_candidate_window=True,
                hol_ms=250,
                pdb_ms=500,
            ),
            "pdb_dominated",
        )

    def test_overdue_pdb_forced_when_hol_reaches_pdb(self) -> None:
        self.assertEqual(
            classify_dominance_label(
                is_pending=True,
                in_candidate_window=True,
                hol_ms=500,
                pdb_ms=500,
            ),
            "overdue_pdb_forced",
        )


def _make_target(
    *,
    hol_ms: int = 0,
    arrival_time: int = 0,
    pdb_ms: int | None = 100,
    bits_per_prb: int = 8,
    avg_rate: float = 4.0,
) -> UserEquipment:
    packet = Packet(
        packet_id="target-pkt",
        arrival_time=arrival_time,
        size_bits=1000,
        remaining_bits=1000,
        pdb_ms=pdb_ms,
        completion_time=None,
        is_target=True,
    )
    return UserEquipment(
        ue_id="target-ue",
        lc=LogicalChannel(lc_id="target-lc", packets=[packet], eligible_cycle=0),
        is_edge_user=True,
        radio_profile=RadioProfile(user_class="edge", bits_per_prb=bits_per_prb, per_u_slot_prb_cap=16),
        average_throughput=avg_rate,
        current_radio_state=CurrentRadioState(
            snr_db=10.0,
            mcs_index=1,
            bits_per_prb=bits_per_prb,
            per_u_slot_prb_cap=16,
        ),
        hol_ms=hol_ms,
    )


class TestBuildTargetRow(unittest.TestCase):
    def test_queue_limited_when_target_is_outside_candidate_window(self) -> None:
        target = _make_target()
        row = build_target_row(
            policy="epf",
            time_ms=0,
            phase="D",
            target_ue=target,
            ordered_queue=[object(), target],
            candidates=[],
            ranked=[],
            ranking_policy=None,
        )

        self.assertEqual(row.queue_rank, 2)
        self.assertIs(row.in_candidate_window, False)
        self.assertEqual(row.dominance_label, "queue_limited")


class TestUlSimulatorDiagnostics(unittest.TestCase):
    def test_finish_phase_invokes_diagnostic_collector_capture(self) -> None:
        target = _make_target(bits_per_prb=1000)
        config = SimpleNamespace(
            resources=SimpleNamespace(total_prb_per_u_slot=1, max_ue_per_slot=1),
            simulation=SimpleNamespace(deadline_guard_ms=0, slot_duration_ms=1),
            scheduler=SimpleNamespace(reinsert_policy="tail_append"),
        )
        collector = TargetEdgeDiagnosticCollector(policy="tail_append")
        sim = UlSimulator(config, [target], metrics=SimpleNamespace(), diagnostic_collector=collector)
        sim.queue.activate(target)

        sim.finish_phase("D", now_ms=123, slot_index=0)

        self.assertEqual(len(collector.rows), 1)
        row = collector.rows[0]
        self.assertEqual(row.time_ms, 123)
        self.assertEqual(row.phase, "D")
        self.assertTrue(row.in_candidate_window)
        self.assertEqual(row.candidate_rank_epf, 1)


if __name__ == "__main__":
    unittest.main()
