import unittest

from scripts.run_target_edge_pdb_dominance_diagnostic import _decision_axis


class PdbDominanceDiagnosticReportTests(unittest.TestCase):
    def test_decision_axis_uses_contiguous_ds_decisions_not_real_time_gaps(self) -> None:
        rows = [
            {"time_ms": 0, "phase": "D"},
            {"time_ms": 1, "phase": "S"},
            {"time_ms": 5, "phase": "D"},
            {"time_ms": 6, "phase": "S"},
        ]

        xs, labels = _decision_axis(rows)

        self.assertEqual(xs, [0, 1, 2, 3])
        self.assertEqual(labels, ["D@0", "S@1", "D@5", "S@6"])
