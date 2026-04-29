# Edge Delay Throughput Tradeoff Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a polished Markdown experiment report plus five PNG charts from `outputs/center_pdb_null_rerun_prb273_20260421_000000`, showing edge-delay sensitivity, center-rate/PRB-util sensitivity, and the latency-throughput tradeoff anchors.

**Architecture:** Keep the simulator and existing sensitivity scripts unchanged. Add one standalone report-rendering script that reads the already-generated `sensitivity_rows.csv` and `config_rerun.json`, derives paired baseline/ours metrics, writes four main charts plus one tradeoff anchor chart with `matplotlib`, and renders a new Markdown report into the root results directory. Cover the work with focused unit tests for parsing/derivation/report rendering and one CLI smoke test that runs the new script against a temporary miniature fixture directory.

**Tech Stack:** Python 3.12, `unittest`, stdlib `csv/json/pathlib`, existing `matplotlib>=3.9`, subprocess-based CLI smoke tests

---

## File Map

- `scripts/render_edge_delay_throughput_tradeoff_report.py`
  - Owns CSV/config loading, derived metric helpers, four sensitivity plots, one tradeoff anchor plot, Markdown rendering, and CLI entry.
- `tests/test_edge_delay_throughput_tradeoff_report.py`
  - Owns focused unit coverage for CSV parsing, row pairing, derived metric formulas, plot writers, and Markdown rendering.
- `tests/test_cli.py`
  - Owns the subprocess smoke test that builds a tiny fixture results directory and verifies the new script writes the expected report and PNG artifacts.

## Task 1: Lock the script surface with failing tests

**Files:**
- Create: `tests/test_edge_delay_throughput_tradeoff_report.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write focused unit tests for row pairing and tradeoff formulas**

Create `tests/test_edge_delay_throughput_tradeoff_report.py` with this content:

```python
import csv
import tempfile
import unittest
from pathlib import Path

from scripts.render_edge_delay_throughput_tradeoff_report import (
    _build_dimension_pairs,
    _build_tradeoff_anchor_rows,
    _center_prb_util_percent,
    _edge_prb_util_percent,
    _latency_gain_percent,
    _load_rows,
    _throughput_retention_percent,
)


CSV_FIELDNAMES = [
    "edge_packet_kb",
    "edge_packet_bits",
    "dimension",
    "value",
    "policy",
    "total_prb_per_u_slot",
    "center_pdb_ms",
    "edge_per_u_slot_prb_cap",
    "target_edge_finished",
    "target_edge_completion_delay_ms",
    "target_edge_queue_wait_ms",
    "target_edge_service_time_ms",
    "target_edge_control_phase_wait_ms",
    "target_edge_pre_first_service_wait_ms",
    "target_edge_inter_service_gap_wait_ms",
    "target_edge_time_to_first_service_ms",
    "target_edge_pdb_met",
    "target_edge_remaining_bits",
    "center_avg_rate_bps",
    "prb_utilization",
    "analysis_window_ms",
    "center_total_bits",
    "edge_total_bits",
    "target_edge_total_bits",
    "system_total_bits",
    "center_agg_rate_bps",
    "edge_agg_rate_bps",
    "target_edge_rate_bps",
    "system_agg_rate_bps",
    "center_used_prb",
    "edge_used_prb",
    "center_prb_share",
    "edge_prb_share",
    "center_bits_per_used_prb",
    "edge_bits_per_used_prb",
]


def _row(
    *,
    dimension: str,
    value: int,
    policy: str,
    completion_ms: float,
    queue_ms: float,
    service_ms: float,
    center_avg_bps: float,
    prb_util: float,
    center_share: float,
    edge_share: float,
    system_rate_bps: float,
) -> dict[str, object]:
    return {
        "edge_packet_kb": 400,
        "edge_packet_bits": 3200000,
        "dimension": dimension,
        "value": value,
        "policy": policy,
        "total_prb_per_u_slot": 273,
        "center_pdb_ms": "null",
        "edge_per_u_slot_prb_cap": 273,
        "target_edge_finished": True,
        "target_edge_completion_delay_ms": completion_ms,
        "target_edge_queue_wait_ms": queue_ms,
        "target_edge_service_time_ms": service_ms,
        "target_edge_control_phase_wait_ms": 100.0,
        "target_edge_pre_first_service_wait_ms": 4.0,
        "target_edge_inter_service_gap_wait_ms": max(queue_ms - 104.0, 0.0),
        "target_edge_time_to_first_service_ms": 8.0,
        "target_edge_pdb_met": True,
        "target_edge_remaining_bits": 0.0,
        "center_avg_rate_bps": center_avg_bps,
        "prb_utilization": prb_util,
        "analysis_window_ms": completion_ms,
        "center_total_bits": center_avg_bps * completion_ms / 1000.0,
        "edge_total_bits": 3200000.0,
        "target_edge_total_bits": 3200000.0,
        "system_total_bits": system_rate_bps * completion_ms / 1000.0,
        "center_agg_rate_bps": center_avg_bps * 63.0,
        "edge_agg_rate_bps": max(system_rate_bps - (center_avg_bps * 63.0), 1.0),
        "target_edge_rate_bps": max(system_rate_bps - (center_avg_bps * 63.0), 1.0),
        "system_agg_rate_bps": system_rate_bps,
        "center_used_prb": 1000.0 * center_share,
        "edge_used_prb": 1000.0 * edge_share,
        "center_prb_share": center_share,
        "edge_prb_share": edge_share,
        "center_bits_per_used_prb": 450.0,
        "edge_bits_per_used_prb": 75.0,
    }


SAMPLE_ROWS = [
    _row(
        dimension="center_user_count",
        value=31,
        policy="tail_append",
        completion_ms=553.0,
        queue_ms=278.0,
        service_ms=275.0,
        center_avg_bps=93790.93507554103,
        prb_util=0.771643261069243,
        center_share=0.06278682882055989,
        edge_share=0.9372131711794401,
        system_rate_bps=8694137.432188064,
    ),
    _row(
        dimension="center_user_count",
        value=31,
        policy="business_aware_constrained_insert",
        completion_ms=453.0,
        queue_ms=186.0,
        service_ms=267.0,
        center_avg_bps=97483.44370860927,
        prb_util=0.9768865820526337,
        center_share=0.051485340306891926,
        edge_share=0.9485146596931081,
        system_rate_bps=10086004.415011037,
    ),
    _row(
        dimension="center_user_count",
        value=63,
        policy="tail_append",
        completion_ms=890.0,
        queue_ms=712.0,
        service_ms=178.0,
        center_avg_bps=86601.9796682718,
        prb_util=0.31521038262611295,
        center_share=0.24196988161559888,
        edge_share=0.7580301183844012,
        system_rate_bps=9051430.337078651,
    ),
    _row(
        dimension="center_user_count",
        value=63,
        policy="business_aware_constrained_insert",
        completion_ms=490.0,
        queue_ms=297.0,
        service_ms=193.0,
        center_avg_bps=94448.36410754778,
        prb_util=0.6405646507687324,
        center_share=0.1197168031431739,
        edge_share=0.8802831968568261,
        system_rate_bps=12480859.18367347,
    ),
    _row(
        dimension="center_packet_load_per_6_slots",
        value=6400,
        policy="tail_append",
        completion_ms=1089.0,
        queue_ms=919.0,
        service_ms=170.0,
        center_avg_bps=556904.9951171164,
        prb_util=0.6601540368768546,
        center_share=0.7046097633513192,
        edge_share=0.2953902366486808,
        system_rate_bps=38023490.35812672,
    ),
    _row(
        dimension="center_packet_load_per_6_slots",
        value=6400,
        policy="business_aware_constrained_insert",
        completion_ms=490.0,
        queue_ms=201.0,
        service_ms=289.0,
        center_avg_bps=610147.5866537091,
        prb_util=0.9928733398121153,
        center_share=0.49829338687413727,
        edge_share=0.5017066131258627,
        system_rate_bps=44969910.20408163,
    ),
    _row(
        dimension="center_packet_load_per_6_slots",
        value=12000,
        policy="tail_append",
        completion_ms=1170.0,
        queue_ms=979.0,
        service_ms=191.0,
        center_avg_bps=999252.9236195904,
        prb_util=0.9557204428999301,
        center_share=0.8254476960034942,
        edge_share=0.1745523039965058,
        system_rate_bps=65687976.92307693,
    ),
    _row(
        dimension="center_packet_load_per_6_slots",
        value=12000,
        policy="business_aware_constrained_insert",
        completion_ms=623.0,
        queue_ms=427.0,
        service_ms=196.0,
        center_avg_bps=879365.181278504,
        prb_util=0.9796619823429474,
        center_share=0.6982698129473326,
        edge_share=0.30173018705266746,
        system_rate_bps=60536443.0176565,
    ),
    _row(
        dimension="edge_pdb_ms",
        value=100,
        policy="tail_append",
        completion_ms=869.0,
        queue_ms=696.0,
        service_ms=173.0,
        center_avg_bps=76658.11825305496,
        prb_util=0.3140269838926269,
        center_share=0.2170155602821001,
        edge_share=0.7829844397178999,
        system_rate_bps=8511855.00575374,
    ),
    _row(
        dimension="edge_pdb_ms",
        value=100,
        policy="business_aware_constrained_insert",
        completion_ms=268.0,
        queue_ms=112.0,
        service_ms=156.0,
        center_avg_bps=36174.07012556266,
        prb_util=0.9728250915750916,
        center_share=0.03111100651872073,
        edge_share=0.9688889934812792,
        system_rate_bps=14219264.925373133,
    ),
    _row(
        dimension="edge_pdb_ms",
        value=500,
        policy="tail_append",
        completion_ms=890.0,
        queue_ms=712.0,
        service_ms=178.0,
        center_avg_bps=86601.9796682718,
        prb_util=0.31521038262611295,
        center_share=0.24196988161559888,
        edge_share=0.7580301183844012,
        system_rate_bps=9051430.337078651,
    ),
    _row(
        dimension="edge_pdb_ms",
        value=500,
        policy="business_aware_constrained_insert",
        completion_ms=490.0,
        queue_ms=297.0,
        service_ms=193.0,
        center_avg_bps=94448.36410754778,
        prb_util=0.6405646507687324,
        center_share=0.1197168031431739,
        edge_share=0.8802831968568261,
        system_rate_bps=12480859.18367347,
    ),
]


class EdgeDelayThroughputTradeoffReportTests(unittest.TestCase):
    def test_load_rows_and_build_dimension_pairs_sort_numeric_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "rows.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=CSV_FIELDNAMES)
                writer.writeheader()
                writer.writerows(SAMPLE_ROWS)

            rows = _load_rows(csv_path)

        pairs = _build_dimension_pairs(rows, "center_user_count")
        self.assertEqual([pair["value"] for pair in pairs], [31, 63])
        self.assertEqual(pairs[0]["baseline"]["policy"], "tail_append")
        self.assertEqual(pairs[0]["ours"]["policy"], "business_aware_constrained_insert")
        self.assertEqual(pairs[1]["baseline"]["target_edge_completion_delay_ms"], 890.0)
        self.assertEqual(pairs[1]["ours"]["target_edge_completion_delay_ms"], 490.0)

    def test_tradeoff_helpers_follow_expected_formulas(self) -> None:
        pairs = _build_dimension_pairs(SAMPLE_ROWS, "center_user_count")
        baseline = pairs[1]["baseline"]
        ours = pairs[1]["ours"]

        self.assertAlmostEqual(_latency_gain_percent(baseline, ours), 44.9438202247, places=3)
        self.assertAlmostEqual(
            _throughput_retention_percent(baseline, ours, "system_agg_rate_bps"),
            137.8882532249,
            places=3,
        )
        self.assertAlmostEqual(
            _throughput_retention_percent(baseline, ours, "center_avg_rate_bps"),
            109.0602829973,
            places=3,
        )
        self.assertAlmostEqual(_center_prb_util_percent(ours), 7.6686352196, places=3)
        self.assertAlmostEqual(_edge_prb_util_percent(ours), 56.3878298572, places=3)

    def test_build_tradeoff_anchor_rows_uses_expected_labels(self) -> None:
        anchors = _build_tradeoff_anchor_rows(SAMPLE_ROWS)
        self.assertEqual(
            [anchor["label"] for anchor in anchors],
            [
                "PDB = 100 ms",
                "PDB = 500 ms",
                "High Load = 12000 bit / 6 slots",
            ],
        )
        self.assertGreater(anchors[0]["latency_gain_pct"], anchors[1]["latency_gain_pct"])
        self.assertLess(anchors[2]["system_retention_pct"], 100.0)
```

- [ ] **Step 2: Add the failing CLI smoke test**

Update `tests/test_cli.py` imports at the top:

```python
import csv
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
```

Then add this helper and test near the other CLI smoke tests:

```python
TRADEOFF_CSV_FIELDNAMES = [
    "edge_packet_kb",
    "edge_packet_bits",
    "dimension",
    "value",
    "policy",
    "total_prb_per_u_slot",
    "center_pdb_ms",
    "edge_per_u_slot_prb_cap",
    "target_edge_finished",
    "target_edge_completion_delay_ms",
    "target_edge_queue_wait_ms",
    "target_edge_service_time_ms",
    "target_edge_control_phase_wait_ms",
    "target_edge_pre_first_service_wait_ms",
    "target_edge_inter_service_gap_wait_ms",
    "target_edge_time_to_first_service_ms",
    "target_edge_pdb_met",
    "target_edge_remaining_bits",
    "center_avg_rate_bps",
    "prb_utilization",
    "analysis_window_ms",
    "center_total_bits",
    "edge_total_bits",
    "target_edge_total_bits",
    "system_total_bits",
    "center_agg_rate_bps",
    "edge_agg_rate_bps",
    "target_edge_rate_bps",
    "system_agg_rate_bps",
    "center_used_prb",
    "edge_used_prb",
    "center_prb_share",
    "edge_prb_share",
    "center_bits_per_used_prb",
    "edge_bits_per_used_prb",
]


def _tradeoff_row(
    *,
    dimension: str,
    value: int,
    policy: str,
    completion_ms: float,
    queue_ms: float,
    service_ms: float,
    center_avg_bps: float,
    prb_util: float,
    center_share: float,
    edge_share: float,
    system_rate_bps: float,
) -> dict[str, object]:
    return {
        "edge_packet_kb": 400,
        "edge_packet_bits": 3200000,
        "dimension": dimension,
        "value": value,
        "policy": policy,
        "total_prb_per_u_slot": 273,
        "center_pdb_ms": "null",
        "edge_per_u_slot_prb_cap": 273,
        "target_edge_finished": True,
        "target_edge_completion_delay_ms": completion_ms,
        "target_edge_queue_wait_ms": queue_ms,
        "target_edge_service_time_ms": service_ms,
        "target_edge_control_phase_wait_ms": 100.0,
        "target_edge_pre_first_service_wait_ms": 4.0,
        "target_edge_inter_service_gap_wait_ms": max(queue_ms - 104.0, 0.0),
        "target_edge_time_to_first_service_ms": 8.0,
        "target_edge_pdb_met": True,
        "target_edge_remaining_bits": 0.0,
        "center_avg_rate_bps": center_avg_bps,
        "prb_utilization": prb_util,
        "analysis_window_ms": completion_ms,
        "center_total_bits": center_avg_bps * completion_ms / 1000.0,
        "edge_total_bits": 3200000.0,
        "target_edge_total_bits": 3200000.0,
        "system_total_bits": system_rate_bps * completion_ms / 1000.0,
        "center_agg_rate_bps": center_avg_bps * 63.0,
        "edge_agg_rate_bps": max(system_rate_bps - (center_avg_bps * 63.0), 1.0),
        "target_edge_rate_bps": max(system_rate_bps - (center_avg_bps * 63.0), 1.0),
        "system_agg_rate_bps": system_rate_bps,
        "center_used_prb": 1000.0 * center_share,
        "edge_used_prb": 1000.0 * edge_share,
        "center_prb_share": center_share,
        "edge_prb_share": edge_share,
        "center_bits_per_used_prb": 450.0,
        "edge_bits_per_used_prb": 75.0,
    }


def _write_tradeoff_fixture(root: Path) -> None:
    fixture_dir = root / "target_edge_packet_size_sensitivity_400kb"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "simulation": {
            "cycles": 1000,
            "slot_duration_ms": 1,
            "tdd_pattern": "DSUUU",
            "random_seed": 7,
            "stop_when_target_edge_finished": True,
            "deadline_guard_ms": 10,
        },
        "resources": {"total_prb_per_u_slot": 273, "max_ue_per_slot": 16},
        "traffic": {
            "center": {
                "count": 63,
                "period_slots": 6,
                "packet_bits": 960,
                "pdb_ms": None,
                "gbr_bps": 7000,
            },
            "edge": {"count": 1, "packet_bits": 3200000, "pdb_ms": 500},
        },
        "radio": {
            "environment": {
                "scenario_type": "uma",
                "center_distance_range_m": [50, 150],
                "edge_distance_range_m": [375, 475],
            },
            "edge": {"edge_per_u_slot_prb_cap": 273},
        },
    }
    (fixture_dir / "config_rerun.json").write_text(json.dumps(payload), encoding="utf-8")
    rows = [
        _tradeoff_row(
            dimension="center_user_count",
            value=31,
            policy="tail_append",
            completion_ms=553.0,
            queue_ms=278.0,
            service_ms=275.0,
            center_avg_bps=93790.93507554103,
            prb_util=0.771643261069243,
            center_share=0.06278682882055989,
            edge_share=0.9372131711794401,
            system_rate_bps=8694137.432188064,
        ),
        _tradeoff_row(
            dimension="center_user_count",
            value=31,
            policy="business_aware_constrained_insert",
            completion_ms=453.0,
            queue_ms=186.0,
            service_ms=267.0,
            center_avg_bps=97483.44370860927,
            prb_util=0.9768865820526337,
            center_share=0.051485340306891926,
            edge_share=0.9485146596931081,
            system_rate_bps=10086004.415011037,
        ),
        _tradeoff_row(
            dimension="center_user_count",
            value=63,
            policy="tail_append",
            completion_ms=890.0,
            queue_ms=712.0,
            service_ms=178.0,
            center_avg_bps=86601.9796682718,
            prb_util=0.31521038262611295,
            center_share=0.24196988161559888,
            edge_share=0.7580301183844012,
            system_rate_bps=9051430.337078651,
        ),
        _tradeoff_row(
            dimension="center_user_count",
            value=63,
            policy="business_aware_constrained_insert",
            completion_ms=490.0,
            queue_ms=297.0,
            service_ms=193.0,
            center_avg_bps=94448.36410754778,
            prb_util=0.6405646507687324,
            center_share=0.1197168031431739,
            edge_share=0.8802831968568261,
            system_rate_bps=12480859.18367347,
        ),
        _tradeoff_row(
            dimension="center_packet_load_per_6_slots",
            value=6400,
            policy="tail_append",
            completion_ms=1089.0,
            queue_ms=919.0,
            service_ms=170.0,
            center_avg_bps=556904.9951171164,
            prb_util=0.6601540368768546,
            center_share=0.7046097633513192,
            edge_share=0.2953902366486808,
            system_rate_bps=38023490.35812672,
        ),
        _tradeoff_row(
            dimension="center_packet_load_per_6_slots",
            value=6400,
            policy="business_aware_constrained_insert",
            completion_ms=490.0,
            queue_ms=201.0,
            service_ms=289.0,
            center_avg_bps=610147.5866537091,
            prb_util=0.9928733398121153,
            center_share=0.49829338687413727,
            edge_share=0.5017066131258627,
            system_rate_bps=44969910.20408163,
        ),
        _tradeoff_row(
            dimension="center_packet_load_per_6_slots",
            value=12000,
            policy="tail_append",
            completion_ms=1170.0,
            queue_ms=979.0,
            service_ms=191.0,
            center_avg_bps=999252.9236195904,
            prb_util=0.9557204428999301,
            center_share=0.8254476960034942,
            edge_share=0.1745523039965058,
            system_rate_bps=65687976.92307693,
        ),
        _tradeoff_row(
            dimension="center_packet_load_per_6_slots",
            value=12000,
            policy="business_aware_constrained_insert",
            completion_ms=623.0,
            queue_ms=427.0,
            service_ms=196.0,
            center_avg_bps=879365.181278504,
            prb_util=0.9796619823429474,
            center_share=0.6982698129473326,
            edge_share=0.30173018705266746,
            system_rate_bps=60536443.0176565,
        ),
        _tradeoff_row(
            dimension="edge_pdb_ms",
            value=100,
            policy="tail_append",
            completion_ms=869.0,
            queue_ms=696.0,
            service_ms=173.0,
            center_avg_bps=76658.11825305496,
            prb_util=0.3140269838926269,
            center_share=0.2170155602821001,
            edge_share=0.7829844397178999,
            system_rate_bps=8511855.00575374,
        ),
        _tradeoff_row(
            dimension="edge_pdb_ms",
            value=100,
            policy="business_aware_constrained_insert",
            completion_ms=268.0,
            queue_ms=112.0,
            service_ms=156.0,
            center_avg_bps=36174.07012556266,
            prb_util=0.9728250915750916,
            center_share=0.03111100651872073,
            edge_share=0.9688889934812792,
            system_rate_bps=14219264.925373133,
        ),
        _tradeoff_row(
            dimension="edge_pdb_ms",
            value=500,
            policy="tail_append",
            completion_ms=890.0,
            queue_ms=712.0,
            service_ms=178.0,
            center_avg_bps=86601.9796682718,
            prb_util=0.31521038262611295,
            center_share=0.24196988161559888,
            edge_share=0.7580301183844012,
            system_rate_bps=9051430.337078651,
        ),
        _tradeoff_row(
            dimension="edge_pdb_ms",
            value=500,
            policy="business_aware_constrained_insert",
            completion_ms=490.0,
            queue_ms=297.0,
            service_ms=193.0,
            center_avg_bps=94448.36410754778,
            prb_util=0.6405646507687324,
            center_share=0.1197168031431739,
            edge_share=0.8802831968568261,
            system_rate_bps=12480859.18367347,
        ),
    ]
    with (fixture_dir / "sensitivity_rows.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRADEOFF_CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


class CliSmokeTests(unittest.TestCase):
    def test_edge_delay_throughput_tradeoff_report_script_runs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            result_root = Path(temp_dir) / "results"
            _write_tradeoff_fixture(result_root)

            result = subprocess.run(
                [
                    "python",
                    "scripts/render_edge_delay_throughput_tradeoff_report.py",
                    str(result_root),
                ],
                cwd=repo_root,
                env={**os.environ, "PYTHONPATH": "src"},
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=f"stderr:\\n{result.stderr}")
            self.assertIn("uplink_scheduler_edge_delay_throughput_tradeoff_report.md", result.stdout)

            self.assertTrue(
                (result_root / "uplink_scheduler_edge_delay_throughput_tradeoff_report.md").exists()
            )
            self.assertTrue((result_root / "user_count_sensitivity_edge_delay_breakdown.png").exists())
            self.assertTrue((result_root / "user_count_sensitivity_center_rate_prb_util.png").exists())
            self.assertTrue((result_root / "center_load_sensitivity_edge_delay_breakdown.png").exists())
            self.assertTrue((result_root / "center_load_sensitivity_center_rate_prb_util.png").exists())
            self.assertTrue((result_root / "latency_throughput_tradeoff_pdb_anchors.png").exists())

            report_text = (
                result_root / "uplink_scheduler_edge_delay_throughput_tradeoff_report.md"
            ).read_text(encoding="utf-8")
            self.assertIn("系统实现结构、系统参数与业务模型", report_text)
            self.assertIn("边缘时延收益与整体吞吐代价的权衡分析", report_text)
            self.assertIn("Latency Gain (%)", report_text)
            self.assertIn("System Throughput Retention (%)", report_text)
            self.assertIn("user_count_sensitivity_edge_delay_breakdown.png", report_text)
            self.assertIn("latency_throughput_tradeoff_pdb_anchors.png", report_text)
```

- [ ] **Step 3: Run the new tests to verify they fail**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest \
  tests.test_edge_delay_throughput_tradeoff_report \
  tests.test_cli.CliSmokeTests.test_edge_delay_throughput_tradeoff_report_script_runs -v
```

Expected: FAIL with `ModuleNotFoundError` because `scripts/render_edge_delay_throughput_tradeoff_report.py` does not exist yet.

- [ ] **Step 4: Commit**

```bash
git add tests/test_edge_delay_throughput_tradeoff_report.py tests/test_cli.py
git commit -m "test: define edge delay throughput report surface"
```

## Task 2: Implement CSV loading, row pairing, and formula helpers

**Files:**
- Create: `scripts/render_edge_delay_throughput_tradeoff_report.py`

- [ ] **Step 1: Create the script with parsing and metric helpers only**

Create `scripts/render_edge_delay_throughput_tradeoff_report.py` with this content:

```python
import csv
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")


RowValue = str | int | float | bool | None
Row = dict[str, RowValue]

INPUT_SUBDIR = "target_edge_packet_size_sensitivity_400kb"
REPORT_FILENAME = "uplink_scheduler_edge_delay_throughput_tradeoff_report.md"

BASELINE_POLICY = "tail_append"
OURS_POLICY = "business_aware_constrained_insert"


def _coerce_csv_value(value: str) -> RowValue:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null" or value == "":
        return None
    try:
        if any(marker in value for marker in [".", "e", "E"]):
            return float(value)
        return int(value)
    except ValueError:
        return value


def _load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_rows(path: Path) -> list[Row]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [{key: _coerce_csv_value(value) for key, value in row.items()} for row in reader]


def _build_dimension_pairs(rows: list[Row], dimension: str) -> list[dict[str, Row | int]]:
    grouped: dict[int, dict[str, Row]] = {}
    for row in rows:
        if row["dimension"] != dimension:
            continue
        grouped.setdefault(int(row["value"]), {})[str(row["policy"])] = row

    pairs: list[dict[str, Row | int]] = []
    for value in sorted(grouped):
        policies = grouped[value]
        pairs.append(
            {
                "value": value,
                "baseline": policies[BASELINE_POLICY],
                "ours": policies[OURS_POLICY],
            }
        )
    return pairs


def _center_prb_util_percent(row: Row) -> float:
    return float(row["prb_utilization"]) * float(row["center_prb_share"]) * 100.0


def _edge_prb_util_percent(row: Row) -> float:
    return float(row["prb_utilization"]) * float(row["edge_prb_share"]) * 100.0


def _latency_gain_percent(baseline: Row, ours: Row) -> float:
    baseline_completion = float(baseline["target_edge_completion_delay_ms"])
    ours_completion = float(ours["target_edge_completion_delay_ms"])
    return (baseline_completion - ours_completion) / baseline_completion * 100.0


def _throughput_retention_percent(baseline: Row, ours: Row, key: str) -> float:
    return float(ours[key]) / float(baseline[key]) * 100.0


def _find_row(rows: list[Row], *, dimension: str, value: int, policy: str) -> Row:
    for row in rows:
        if row["dimension"] == dimension and int(row["value"]) == value and row["policy"] == policy:
            return row
    raise ValueError(f"missing row for {dimension=} {value=} {policy=}")


def _build_tradeoff_anchor_rows(rows: list[Row]) -> list[dict[str, float | str]]:
    anchors: list[tuple[str, Row, Row]] = [
        (
            "PDB = 100 ms",
            _find_row(rows, dimension="edge_pdb_ms", value=100, policy=BASELINE_POLICY),
            _find_row(rows, dimension="edge_pdb_ms", value=100, policy=OURS_POLICY),
        ),
        (
            "PDB = 500 ms",
            _find_row(rows, dimension="edge_pdb_ms", value=500, policy=BASELINE_POLICY),
            _find_row(rows, dimension="edge_pdb_ms", value=500, policy=OURS_POLICY),
        ),
        (
            "High Load = 12000 bit / 6 slots",
            _find_row(
                rows,
                dimension="center_packet_load_per_6_slots",
                value=12000,
                policy=BASELINE_POLICY,
            ),
            _find_row(
                rows,
                dimension="center_packet_load_per_6_slots",
                value=12000,
                policy=OURS_POLICY,
            ),
        ),
    ]
    return [
        {
            "label": label,
            "latency_gain_pct": _latency_gain_percent(baseline, ours),
            "system_retention_pct": _throughput_retention_percent(
                baseline, ours, "system_agg_rate_bps"
            ),
            "center_retention_pct": _throughput_retention_percent(
                baseline, ours, "center_avg_rate_bps"
            ),
        }
        for label, baseline, ours in anchors
    ]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(
            "usage: render_edge_delay_throughput_tradeoff_report.py RESULT_ROOT",
            file=sys.stderr,
        )
        return 1
    raise NotImplementedError("plotting and markdown rendering are added in Task 4")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 2: Run the focused helper tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest \
  tests.test_edge_delay_throughput_tradeoff_report.EdgeDelayThroughputTradeoffReportTests.test_load_rows_and_build_dimension_pairs_sort_numeric_values \
  tests.test_edge_delay_throughput_tradeoff_report.EdgeDelayThroughputTradeoffReportTests.test_tradeoff_helpers_follow_expected_formulas \
  tests.test_edge_delay_throughput_tradeoff_report.EdgeDelayThroughputTradeoffReportTests.test_build_tradeoff_anchor_rows_uses_expected_labels -v
```

Expected: PASS. The CLI smoke test should still fail because the script raises `NotImplementedError`.

- [ ] **Step 3: Confirm the CLI test still fails for the right reason**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest \
  tests.test_cli.CliSmokeTests.test_edge_delay_throughput_tradeoff_report_script_runs -v
```

Expected: FAIL with `NotImplementedError`, proving the parsing/formula helpers are ready but plotting/reporting are not.

- [ ] **Step 4: Commit**

```bash
git add scripts/render_edge_delay_throughput_tradeoff_report.py
git commit -m "feat: add tradeoff report parsing helpers"
```

## Task 3: Extend the test module to lock plot and Markdown outputs

**Files:**
- Modify: `tests/test_edge_delay_throughput_tradeoff_report.py`

- [ ] **Step 1: Add failing plot and report rendering tests**

Append these imports to the existing import list in `tests/test_edge_delay_throughput_tradeoff_report.py`:

```python
from scripts.render_edge_delay_throughput_tradeoff_report import (
    _plot_center_rate_prb_util,
    _plot_edge_delay_breakdown,
    _plot_tradeoff_anchors,
    _render_report,
)
```

Then append these tests to the class:

```python
    def test_plot_writers_create_png_artifacts(self) -> None:
        user_pairs = _build_dimension_pairs(SAMPLE_ROWS, "center_user_count")
        load_pairs = _build_dimension_pairs(SAMPLE_ROWS, "center_packet_load_per_6_slots")
        anchors = _build_tradeoff_anchor_rows(SAMPLE_ROWS)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            _plot_edge_delay_breakdown(
                user_pairs,
                title="User Count Sensitivity",
                xlabel="center_user_count",
                output_path=output_dir / "user_count_sensitivity_edge_delay_breakdown.png",
            )
            _plot_center_rate_prb_util(
                user_pairs,
                title="User Count Sensitivity",
                xlabel="center_user_count",
                output_path=output_dir / "user_count_sensitivity_center_rate_prb_util.png",
            )
            _plot_edge_delay_breakdown(
                load_pairs,
                title="Center Load Sensitivity",
                xlabel="center_packet_load_per_6_slots",
                output_path=output_dir / "center_load_sensitivity_edge_delay_breakdown.png",
            )
            _plot_center_rate_prb_util(
                load_pairs,
                title="Center Load Sensitivity",
                xlabel="center_packet_load_per_6_slots",
                output_path=output_dir / "center_load_sensitivity_center_rate_prb_util.png",
            )
            _plot_tradeoff_anchors(
                anchors,
                output_path=output_dir / "latency_throughput_tradeoff_pdb_anchors.png",
            )

            self.assertTrue((output_dir / "user_count_sensitivity_edge_delay_breakdown.png").exists())
            self.assertTrue((output_dir / "user_count_sensitivity_center_rate_prb_util.png").exists())
            self.assertTrue((output_dir / "center_load_sensitivity_edge_delay_breakdown.png").exists())
            self.assertTrue((output_dir / "center_load_sensitivity_center_rate_prb_util.png").exists())
            self.assertTrue((output_dir / "latency_throughput_tradeoff_pdb_anchors.png").exists())

    def test_render_report_includes_sections_formulas_and_image_references(self) -> None:
        payload = {
            "simulation": {
                "slot_duration_ms": 1,
                "tdd_pattern": "DSUUU",
                "deadline_guard_ms": 10,
            },
            "resources": {"total_prb_per_u_slot": 273, "max_ue_per_slot": 16},
            "traffic": {
                "center": {"count": 63, "period_slots": 6, "packet_bits": 960, "pdb_ms": None},
                "edge": {"count": 1, "packet_bits": 3200000, "pdb_ms": 500},
            },
            "radio": {
                "environment": {"scenario_type": "uma", "center_distance_range_m": [50, 150], "edge_distance_range_m": [375, 475]},
                "edge": {"edge_per_u_slot_prb_cap": 273},
            },
        }
        report = _render_report(
            payload=payload,
            user_count_pairs=_build_dimension_pairs(SAMPLE_ROWS, "center_user_count"),
            center_load_pairs=_build_dimension_pairs(SAMPLE_ROWS, "center_packet_load_per_6_slots"),
            anchor_rows=_build_tradeoff_anchor_rows(SAMPLE_ROWS),
        )
        self.assertIn("# 上行调度边缘时延-吞吐权衡实验报告", report)
        self.assertIn("## 2. 系统实现结构、系统参数与业务模型", report)
        self.assertIn("## 3. 指标定义与公式说明", report)
        self.assertIn("Latency Gain (%)", report)
        self.assertIn("System Throughput Retention (%)", report)
        self.assertIn("Center Throughput Retention (%)", report)
        self.assertIn("PRB_available,total = N_u_slots × PRB_per_u_slot", report)
        self.assertIn("user_count_sensitivity_edge_delay_breakdown.png", report)
        self.assertIn("center_load_sensitivity_center_rate_prb_util.png", report)
        self.assertIn("latency_throughput_tradeoff_pdb_anchors.png", report)
        self.assertIn("PDB = 100 ms", report)
        self.assertIn("PDB = 500 ms", report)
        self.assertIn("High Load = 12000 bit / 6 slots", report)
```

- [ ] **Step 2: Run the updated unit test module to verify the new tests fail**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest \
  tests.test_edge_delay_throughput_tradeoff_report -v
```

Expected: FAIL because `_plot_edge_delay_breakdown`, `_plot_center_rate_prb_util`, `_plot_tradeoff_anchors`, and `_render_report` do not exist yet.

- [ ] **Step 3: Commit**

```bash
git add tests/test_edge_delay_throughput_tradeoff_report.py
git commit -m "test: lock tradeoff report plots and markdown"
```

## Task 4: Implement plotting, Markdown rendering, and the CLI entrypoint

**Files:**
- Modify: `scripts/render_edge_delay_throughput_tradeoff_report.py`

- [ ] **Step 1: Replace the placeholder script with the full report generator**

Update `scripts/render_edge_delay_throughput_tradeoff_report.py` to this final content:

```python
import csv
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


RowValue = str | int | float | bool | None
Row = dict[str, RowValue]

INPUT_SUBDIR = "target_edge_packet_size_sensitivity_400kb"
REPORT_FILENAME = "uplink_scheduler_edge_delay_throughput_tradeoff_report.md"
USER_COUNT_DELAY_PLOT = "user_count_sensitivity_edge_delay_breakdown.png"
USER_COUNT_RATE_PLOT = "user_count_sensitivity_center_rate_prb_util.png"
CENTER_LOAD_DELAY_PLOT = "center_load_sensitivity_edge_delay_breakdown.png"
CENTER_LOAD_RATE_PLOT = "center_load_sensitivity_center_rate_prb_util.png"
ANCHOR_PLOT = "latency_throughput_tradeoff_pdb_anchors.png"

BASELINE_POLICY = "tail_append"
OURS_POLICY = "business_aware_constrained_insert"


def _coerce_csv_value(value: str) -> RowValue:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null" or value == "":
        return None
    try:
        if any(marker in value for marker in [".", "e", "E"]):
            return float(value)
        return int(value)
    except ValueError:
        return value


def _load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_rows(path: Path) -> list[Row]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [{key: _coerce_csv_value(value) for key, value in row.items()} for row in reader]


def _build_dimension_pairs(rows: list[Row], dimension: str) -> list[dict[str, Row | int]]:
    grouped: dict[int, dict[str, Row]] = {}
    for row in rows:
        if row["dimension"] != dimension:
            continue
        grouped.setdefault(int(row["value"]), {})[str(row["policy"])] = row

    pairs: list[dict[str, Row | int]] = []
    for value in sorted(grouped):
        policies = grouped[value]
        pairs.append(
            {
                "value": value,
                "baseline": policies[BASELINE_POLICY],
                "ours": policies[OURS_POLICY],
            }
        )
    return pairs


def _center_prb_util_percent(row: Row) -> float:
    return float(row["prb_utilization"]) * float(row["center_prb_share"]) * 100.0


def _edge_prb_util_percent(row: Row) -> float:
    return float(row["prb_utilization"]) * float(row["edge_prb_share"]) * 100.0


def _latency_gain_percent(baseline: Row, ours: Row) -> float:
    baseline_completion = float(baseline["target_edge_completion_delay_ms"])
    ours_completion = float(ours["target_edge_completion_delay_ms"])
    return (baseline_completion - ours_completion) / baseline_completion * 100.0


def _throughput_retention_percent(baseline: Row, ours: Row, key: str) -> float:
    return float(ours[key]) / float(baseline[key]) * 100.0


def _find_row(rows: list[Row], *, dimension: str, value: int, policy: str) -> Row:
    for row in rows:
        if row["dimension"] == dimension and int(row["value"]) == value and row["policy"] == policy:
            return row
    raise ValueError(f"missing row for {dimension=} {value=} {policy=}")


def _build_tradeoff_anchor_rows(rows: list[Row]) -> list[dict[str, float | str]]:
    anchors: list[tuple[str, Row, Row]] = [
        (
            "PDB = 100 ms",
            _find_row(rows, dimension="edge_pdb_ms", value=100, policy=BASELINE_POLICY),
            _find_row(rows, dimension="edge_pdb_ms", value=100, policy=OURS_POLICY),
        ),
        (
            "PDB = 500 ms",
            _find_row(rows, dimension="edge_pdb_ms", value=500, policy=BASELINE_POLICY),
            _find_row(rows, dimension="edge_pdb_ms", value=500, policy=OURS_POLICY),
        ),
        (
            "High Load = 12000 bit / 6 slots",
            _find_row(
                rows,
                dimension="center_packet_load_per_6_slots",
                value=12000,
                policy=BASELINE_POLICY,
            ),
            _find_row(
                rows,
                dimension="center_packet_load_per_6_slots",
                value=12000,
                policy=OURS_POLICY,
            ),
        ),
    ]
    return [
        {
            "label": label,
            "latency_gain_pct": _latency_gain_percent(baseline, ours),
            "system_retention_pct": _throughput_retention_percent(
                baseline, ours, "system_agg_rate_bps"
            ),
            "center_retention_pct": _throughput_retention_percent(
                baseline, ours, "center_avg_rate_bps"
            ),
            "baseline_completion_ms": float(baseline["target_edge_completion_delay_ms"]),
            "ours_completion_ms": float(ours["target_edge_completion_delay_ms"]),
        }
        for label, baseline, ours in anchors
    ]


def _delay_series(pair_rows: list[dict[str, Row | int]], key: str, policy_key: str) -> list[float]:
    return [float(pair[policy_key][key]) for pair in pair_rows]


def _plot_edge_delay_breakdown(
    pair_rows: list[dict[str, Row | int]],
    *,
    title: str,
    xlabel: str,
    output_path: Path,
) -> None:
    xs = [int(pair["value"]) for pair in pair_rows]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(xs, _delay_series(pair_rows, "target_edge_completion_delay_ms", "baseline"), color="#444444", linewidth=2.0, label="Baseline Completion")
    ax.plot(xs, _delay_series(pair_rows, "target_edge_completion_delay_ms", "ours"), color="#1f77b4", linewidth=2.0, label="Ours Completion")
    ax.plot(xs, _delay_series(pair_rows, "target_edge_queue_wait_ms", "baseline"), color="#777777", linestyle="--", linewidth=1.8, label="Baseline Queue Wait")
    ax.plot(xs, _delay_series(pair_rows, "target_edge_queue_wait_ms", "ours"), color="#4fa3ff", linestyle="--", linewidth=1.8, label="Ours Queue Wait")
    ax.plot(xs, _delay_series(pair_rows, "target_edge_service_time_ms", "baseline"), color="#999999", linestyle=":", linewidth=1.8, label="Baseline Service Time")
    ax.plot(xs, _delay_series(pair_rows, "target_edge_service_time_ms", "ours"), color="#7fc7ff", linestyle=":", linewidth=1.8, label="Ours Service Time")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Delay (ms)")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _plot_center_rate_prb_util(
    pair_rows: list[dict[str, Row | int]],
    *,
    title: str,
    xlabel: str,
    output_path: Path,
) -> None:
    xs = [int(pair["value"]) for pair in pair_rows]
    fig, ax_left = plt.subplots(figsize=(9, 4.5))
    ax_right = ax_left.twinx()

    baseline_rows = [pair["baseline"] for pair in pair_rows]
    ours_rows = [pair["ours"] for pair in pair_rows]

    ax_left.plot(
        xs,
        [float(row["center_avg_rate_bps"]) / 1000.0 for row in baseline_rows],
        color="#222222",
        linewidth=2.0,
        label="Baseline Center Avg Rate",
    )
    ax_left.plot(
        xs,
        [float(row["center_avg_rate_bps"]) / 1000.0 for row in ours_rows],
        color="#0055cc",
        linewidth=2.0,
        label="Ours Center Avg Rate",
    )

    ax_right.plot(
        xs,
        [float(row["prb_utilization"]) * 100.0 for row in baseline_rows],
        color="#666666",
        linestyle="-",
        linewidth=1.8,
        label="Baseline Total PRB Util",
    )
    ax_right.plot(
        xs,
        [float(row["prb_utilization"]) * 100.0 for row in ours_rows],
        color="#3399ff",
        linestyle="-",
        linewidth=1.8,
        label="Ours Total PRB Util",
    )
    ax_right.plot(
        xs,
        [_center_prb_util_percent(row) for row in baseline_rows],
        color="#888888",
        linestyle="--",
        linewidth=1.6,
        label="Baseline Center PRB Util",
    )
    ax_right.plot(
        xs,
        [_center_prb_util_percent(row) for row in ours_rows],
        color="#66b3ff",
        linestyle="--",
        linewidth=1.6,
        label="Ours Center PRB Util",
    )
    ax_right.plot(
        xs,
        [_edge_prb_util_percent(row) for row in baseline_rows],
        color="#aaaaaa",
        linestyle=":",
        linewidth=1.6,
        label="Baseline Edge PRB Util",
    )
    ax_right.plot(
        xs,
        [_edge_prb_util_percent(row) for row in ours_rows],
        color="#99d6ff",
        linestyle=":",
        linewidth=1.6,
        label="Ours Edge PRB Util",
    )

    ax_left.set_title(title)
    ax_left.set_xlabel(xlabel)
    ax_left.set_ylabel("Center Avg Rate (kbps)")
    ax_right.set_ylabel("PRB Utilization (%)")
    ax_left.grid(True, alpha=0.25)

    left_handles, left_labels = ax_left.get_legend_handles_labels()
    right_handles, right_labels = ax_right.get_legend_handles_labels()
    ax_left.legend(left_handles + right_handles, left_labels + right_labels, fontsize=7, ncol=2, loc="upper left")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _plot_tradeoff_anchors(anchor_rows: list[dict[str, float | str]], *, output_path: Path) -> None:
    labels = [str(anchor["label"]) for anchor in anchor_rows]
    xs = list(range(len(anchor_rows)))

    fig, ax_left = plt.subplots(figsize=(8.5, 4.5))
    ax_right = ax_left.twinx()

    ax_left.bar(
        xs,
        [float(anchor["latency_gain_pct"]) for anchor in anchor_rows],
        color="#5b9bd5",
        alpha=0.85,
        width=0.55,
        label="Latency Gain (%)",
    )
    ax_right.plot(
        xs,
        [float(anchor["system_retention_pct"]) for anchor in anchor_rows],
        color="#d62728",
        marker="o",
        linewidth=2.0,
        label="System Throughput Retention (%)",
    )
    ax_right.plot(
        xs,
        [float(anchor["center_retention_pct"]) for anchor in anchor_rows],
        color="#ff7f0e",
        marker="s",
        linestyle="--",
        linewidth=1.8,
        label="Center Throughput Retention (%)",
    )

    ax_left.set_title("Latency Gain vs Throughput Retention Anchors")
    ax_left.set_xticks(xs)
    ax_left.set_xticklabels(labels)
    ax_left.set_ylabel("Latency Gain (%)")
    ax_right.set_ylabel("Throughput Retention (%)")
    ax_left.grid(True, axis="y", alpha=0.25)

    left_handles, left_labels = ax_left.get_legend_handles_labels()
    right_handles, right_labels = ax_right.get_legend_handles_labels()
    ax_left.legend(left_handles + right_handles, left_labels + right_labels, fontsize=8, loc="upper right")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _pair_summary_line(pair_rows: list[dict[str, Row | int]], value: int) -> tuple[Row, Row]:
    for pair in pair_rows:
        if int(pair["value"]) == value:
            return pair["baseline"], pair["ours"]
    raise ValueError(f"missing pair summary for {value}")


def _render_report(
    *,
    payload: dict[str, Any],
    user_count_pairs: list[dict[str, Row | int]],
    center_load_pairs: list[dict[str, Row | int]],
    anchor_rows: list[dict[str, float | str]],
) -> str:
    user_63_baseline, user_63_ours = _pair_summary_line(user_count_pairs, 63)
    load_12000_baseline, load_12000_ours = _pair_summary_line(center_load_pairs, 12000)
    anchor_100 = anchor_rows[0]
    anchor_500 = anchor_rows[1]
    anchor_load = anchor_rows[2]

    resources = payload["resources"]
    traffic = payload["traffic"]
    radio_edge = payload["radio"]["edge"]
    simulation = payload["simulation"]
    environment = payload["radio"]["environment"]

    return "\n".join(
        [
            "# 上行调度边缘时延-吞吐权衡实验报告",
            "",
            "## 1. 实验背景与目标",
            "",
            "- 本报告关注在 `DSUUU` 高负载上行调度场景下，业务感知回插算法是否能在压缩边缘大包时延的同时，尽量控制对整体吞吐的影响。",
            "- 与原始敏感性表相比，这里把结果重新组织为可展示的结构：先说明系统与指标，再给出用户数/中心数据量敏感度主图，最后用 `PDB=100 ms`、`PDB=500 ms` 和高负载锚点总结收益-代价权衡。",
            "",
            "## 2. 系统实现结构、系统参数与业务模型",
            "",
            "### 2.1 系统实现结构",
            "",
            "- 业务到达：中心背景用户按固定周期生成小包，目标边缘用户持有单个 `400 KB` 大包。",
            "- 排序与候选：每个 `D/S` 决策阶段基于 `ePF` 从最多 `16` 个候选用户中排序。",
            "- 回插策略：baseline 采用 `tail_append`，ours 采用 `business_aware_constrained_insert`。",
            "- 资源分配：每个 `U-slot` 按顺序分配最多 `273 PRB`。",
            "- 指标统计：在 `stop_when_target_edge_finished = true` 的窗口内统计时延、吞吐与 `PRB` 利用率。",
            "",
            "### 2.2 系统参数",
            "",
            f"- `TDD` 配比：`{simulation['tdd_pattern']}`，每个 slot `1 ms`。",
            f"- 调度资源：每个 `U-slot` ` {resources['total_prb_per_u_slot']} PRB`，候选上限 `{resources['max_ue_per_slot']}` 个 UE。",
            f"- 安全裕量：`deadline_guard_ms = {simulation['deadline_guard_ms']} ms`。",
            f"- 无线环境：`{environment['scenario_type']}`，中心距离 `{environment['center_distance_range_m'][0]}-{environment['center_distance_range_m'][1]} m`，边缘距离 `{environment['edge_distance_range_m'][0]}-{environment['edge_distance_range_m'][1]} m`。",
            "",
            "### 2.3 业务模型",
            "",
            f"- 中心背景：`{traffic['center']['count']}` 个用户，`{traffic['center']['packet_bits']} bit / every {traffic['center']['period_slots']} slots`，`pdb_ms = null`。",
            f"- 目标边缘：`{traffic['edge']['count']}` 个用户，`{traffic['edge']['packet_bits']} bit`，默认 `PDB = {traffic['edge']['pdb_ms']} ms`。",
            f"- 边缘 `PRB` 上限：`edge_per_u_slot_prb_cap = {radio_edge['edge_per_u_slot_prb_cap']}`。",
            "",
            "## 3. 指标定义与公式说明",
            "",
            "### 3.1 时延类指标",
            "",
            "- `Completion Delay`: `T_completion = T_finish - T_arrival`。",
            "- `Queue Wait`: `T_queue = T_completion - T_service`。",
            "- `Service Time`: `T_service = N_service_slots × T_slot`。",
            "- `Control Phase Wait`: `T_control`。",
            "- `Pre-First-Service Wait`: `T_pre-first = T_first_service_start - T_arrival`。",
            "- `Inter-Service Gap Wait`: `T_gap`。",
            "- `Time to First Service`: `T_first = T_first_service_start - T_arrival`。",
            "- `PDB Met`: `1(T_completion ≤ PDB)`。",
            "",
            "### 3.2 吞吐类指标",
            "",
            "- `Center Avg Rate`: `R_center,avg = B_center / T_window`。",
            "- `Edge Aggregate Rate`: `R_edge,agg = B_edge / T_window`。",
            "- `Target Edge Rate`: `R_target = B_target / T_window`。",
            "- `System Aggregate Rate`: `R_sys = (B_center + B_edge) / T_window`。",
            "- `Analysis Window`: `T_window = target_edge_completion_delay_ms`。",
            "",
            "### 3.3 PRB 利用类指标",
            "",
            "- `Total PRB Utilization`: `U_total = PRB_used,total / PRB_available,total`。",
            "- `Center PRB Utilization`: `U_center = U_total × Share_center`。",
            "- `Edge PRB Utilization`: `U_edge = U_total × Share_edge`。",
            "- `PRB_available,total = N_u_slots × PRB_per_u_slot`。",
            "",
            "### 3.4 派生 tradeoff 指标",
            "",
            "- `Latency Gain (%) = (Baseline Completion - Ours Completion) / Baseline Completion × 100%`。",
            "- `System Throughput Retention (%) = Ours System Agg Rate / Baseline System Agg Rate × 100%`。",
            "- `Center Throughput Retention (%) = Ours Center Avg Rate / Baseline Center Avg Rate × 100%`。",
            "- `Center PRB Util (%) = prb_utilization × center_prb_share × 100%`。",
            "- `Edge PRB Util (%) = prb_utilization × edge_prb_share × 100%`。",
            "",
            "## 4. 敏感度分析结果",
            "",
            "### 4.1 用户数敏感度",
            "",
            f"![User Count Delay Breakdown]({USER_COUNT_DELAY_PLOT})",
            "",
            f"![User Count Center Rate and PRB Util]({USER_COUNT_RATE_PLOT})",
            "",
            f"- 以 `63` 个中心用户为例，边缘完成时延由 `{float(user_63_baseline['target_edge_completion_delay_ms']):.0f} ms` 降到 `{float(user_63_ours['target_edge_completion_delay_ms']):.0f} ms`，主要来自排队等待由 `{float(user_63_baseline['target_edge_queue_wait_ms']):.0f} ms` 压缩到 `{float(user_63_ours['target_edge_queue_wait_ms']):.0f} ms`。",
            f"- 同一档位下，中心平均速率从 `{float(user_63_baseline['center_avg_rate_bps']) / 1000.0:.1f} kbps` 变为 `{float(user_63_ours['center_avg_rate_bps']) / 1000.0:.1f} kbps`，而总 `PRB` 利用率从 `{float(user_63_baseline['prb_utilization']) * 100.0:.1f}%` 提高到 `{float(user_63_ours['prb_utilization']) * 100.0:.1f}%`。",
            "",
            "### 4.2 中心用户数据量敏感度",
            "",
            f"![Center Load Delay Breakdown]({CENTER_LOAD_DELAY_PLOT})",
            "",
            f"![Center Load Center Rate and PRB Util]({CENTER_LOAD_RATE_PLOT})",
            "",
            f"- 在 `12000 bit / 6 slots` 高负载点，边缘完成时延由 `{float(load_12000_baseline['target_edge_completion_delay_ms']):.0f} ms` 降到 `{float(load_12000_ours['target_edge_completion_delay_ms']):.0f} ms`，但系统已经接近满载，总 `PRB` 利用率分别达到 `{float(load_12000_baseline['prb_utilization']) * 100.0:.1f}%` 和 `{float(load_12000_ours['prb_utilization']) * 100.0:.1f}%`。",
            "",
            "## 5. 边缘时延收益与整体吞吐代价的权衡分析",
            "",
            f"![Tradeoff Anchors]({ANCHOR_PLOT})",
            "",
            f"- `PDB = 100 ms`：`Latency Gain = {float(anchor_100['latency_gain_pct']):.1f}%`，`System Throughput Retention = {float(anchor_100['system_retention_pct']):.1f}%`，说明强 deadline 下虽然中心资源被主动压缩，但系统总吞吐并未恶化。",
            f"- `PDB = 500 ms`：`Latency Gain = {float(anchor_500['latency_gain_pct']):.1f}%`，`System Throughput Retention = {float(anchor_500['system_retention_pct']):.1f}%`，对应默认主场景下更均衡的收益-代价点。",
            f"- `High Load = 12000 bit / 6 slots`：`Latency Gain = {float(anchor_load['latency_gain_pct']):.1f}%`，`System Throughput Retention = {float(anchor_load['system_retention_pct']):.1f}%`，显示整体吞吐代价主要发生在接近满载时。",
            "",
            "## 6. 结论",
            "",
            "- 收益主要来自 `Queue Wait` 压缩，而不是 `Service Time` 大幅降低。",
            "- 随着中心用户数或中心单用户负载升高，baseline 更容易出现排队等待放大。",
            "- 我们的算法通常会提高总 `PRB` 利用率，并把更大的已用 `PRB` 比例分配给边缘目标用户。",
            "- 默认主场景下，边缘时延改善与整体吞吐保持率可以同时成立；明显的整体吞吐代价主要集中在近饱和区。",
            "",
        ]
    )


def _write_report(output_root: Path, report_text: str) -> Path:
    report_path = output_root / REPORT_FILENAME
    report_path.write_text(report_text, encoding="utf-8")
    return report_path


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(
            "usage: render_edge_delay_throughput_tradeoff_report.py RESULT_ROOT",
            file=sys.stderr,
        )
        return 1

    output_root = Path(argv[1])
    input_dir = output_root / INPUT_SUBDIR
    payload = _load_payload(input_dir / "config_rerun.json")
    rows = _load_rows(input_dir / "sensitivity_rows.csv")

    user_count_pairs = _build_dimension_pairs(rows, "center_user_count")
    center_load_pairs = _build_dimension_pairs(rows, "center_packet_load_per_6_slots")
    anchor_rows = _build_tradeoff_anchor_rows(rows)

    _plot_edge_delay_breakdown(
        user_count_pairs,
        title="User Count Sensitivity: Edge Delay Breakdown",
        xlabel="center_user_count",
        output_path=output_root / USER_COUNT_DELAY_PLOT,
    )
    _plot_center_rate_prb_util(
        user_count_pairs,
        title="User Count Sensitivity: Center Rate and PRB Utilization",
        xlabel="center_user_count",
        output_path=output_root / USER_COUNT_RATE_PLOT,
    )
    _plot_edge_delay_breakdown(
        center_load_pairs,
        title="Center Load Sensitivity: Edge Delay Breakdown",
        xlabel="center_packet_load_per_6_slots",
        output_path=output_root / CENTER_LOAD_DELAY_PLOT,
    )
    _plot_center_rate_prb_util(
        center_load_pairs,
        title="Center Load Sensitivity: Center Rate and PRB Utilization",
        xlabel="center_packet_load_per_6_slots",
        output_path=output_root / CENTER_LOAD_RATE_PLOT,
    )
    _plot_tradeoff_anchors(anchor_rows, output_path=output_root / ANCHOR_PLOT)

    report_text = _render_report(
        payload=payload,
        user_count_pairs=user_count_pairs,
        center_load_pairs=center_load_pairs,
        anchor_rows=anchor_rows,
    )
    report_path = _write_report(output_root, report_text)
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 2: Run the focused unit tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest \
  tests.test_edge_delay_throughput_tradeoff_report -v
```

Expected: PASS. The plot files are created in temporary directories and the rendered report contains all required sections and formulas.

- [ ] **Step 3: Run the CLI smoke test**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest \
  tests.test_cli.CliSmokeTests.test_edge_delay_throughput_tradeoff_report_script_runs -v
```

Expected: PASS. The subprocess run writes the report and all five PNGs into the temporary results root.

- [ ] **Step 4: Commit**

```bash
git add scripts/render_edge_delay_throughput_tradeoff_report.py
git commit -m "feat: render edge delay throughput tradeoff report"
```

## Task 5: Verify against the real results directory and protect nearby report behavior

**Files:**
- Test: `tests/test_edge_delay_throughput_tradeoff_report.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_packet_size_sensitivity_report.py`
- Output: `outputs/center_pdb_null_rerun_prb273_20260421_000000/`

- [ ] **Step 1: Run the new renderer on the real results directory**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python \
  scripts/render_edge_delay_throughput_tradeoff_report.py \
  outputs/center_pdb_null_rerun_prb273_20260421_000000
```

Expected: stdout prints `outputs/center_pdb_null_rerun_prb273_20260421_000000/uplink_scheduler_edge_delay_throughput_tradeoff_report.md`.

- [ ] **Step 2: Verify the generated artifacts exist**

Run:

```bash
ls \
  outputs/center_pdb_null_rerun_prb273_20260421_000000/uplink_scheduler_edge_delay_throughput_tradeoff_report.md \
  outputs/center_pdb_null_rerun_prb273_20260421_000000/user_count_sensitivity_edge_delay_breakdown.png \
  outputs/center_pdb_null_rerun_prb273_20260421_000000/user_count_sensitivity_center_rate_prb_util.png \
  outputs/center_pdb_null_rerun_prb273_20260421_000000/center_load_sensitivity_edge_delay_breakdown.png \
  outputs/center_pdb_null_rerun_prb273_20260421_000000/center_load_sensitivity_center_rate_prb_util.png \
  outputs/center_pdb_null_rerun_prb273_20260421_000000/latency_throughput_tradeoff_pdb_anchors.png
```

Expected: all six paths are listed with no `No such file or directory` errors.

- [ ] **Step 3: Re-run the focused automated checks**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest \
  tests.test_edge_delay_throughput_tradeoff_report \
  tests.test_cli.CliSmokeTests.test_edge_delay_throughput_tradeoff_report_script_runs \
  tests.test_packet_size_sensitivity_report -v
```

Expected: PASS. The new report path is covered and the neighboring packet-size report tests still pass.

- [ ] **Step 4: Spot-check the final Markdown for the required sections**

Run:

```bash
rg -n \
  "系统实现结构、系统参数与业务模型|指标定义与公式说明|敏感度分析结果|边缘时延收益与整体吞吐代价的权衡分析|Latency Gain|System Throughput Retention" \
  outputs/center_pdb_null_rerun_prb273_20260421_000000/uplink_scheduler_edge_delay_throughput_tradeoff_report.md
```

Expected: one or more matches for each required section/metric phrase.
