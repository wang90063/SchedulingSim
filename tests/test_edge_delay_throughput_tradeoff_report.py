import csv
import tempfile
import unittest
from pathlib import Path

from scripts.render_edge_delay_throughput_tradeoff_report import (
    _build_dimension_pairs,
    _build_tradeoff_anchor_rows,
    _center_prb_util_percent,
    _delay_line_specs,
    _edge_prb_util_percent,
    _latency_gain_percent,
    _load_rows,
    _plot_center_rate_prb_util,
    _plot_edge_delay_breakdown,
    _plot_tradeoff_anchors,
    _rate_line_specs,
    _render_report,
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
    center_count: int | None = None,
) -> dict[str, object]:
    if center_count is not None:
        resolved_center_count = center_count
    elif dimension == "center_user_count":
        resolved_center_count = value
    else:
        resolved_center_count = 63
    center_agg_rate_bps = center_avg_bps * float(resolved_center_count)
    edge_agg_rate_bps = max(system_rate_bps - center_agg_rate_bps, 1.0)
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
        "center_total_bits": center_agg_rate_bps * completion_ms / 1000.0,
        "edge_total_bits": 3200000.0,
        "target_edge_total_bits": 3200000.0,
        "system_total_bits": system_rate_bps * completion_ms / 1000.0,
        "center_agg_rate_bps": center_agg_rate_bps,
        "edge_agg_rate_bps": edge_agg_rate_bps,
        "target_edge_rate_bps": edge_agg_rate_bps,
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
        dimension="center_packet_load_per_6_slots",
        value=16000,
        policy="tail_append",
        completion_ms=1350.0,
        queue_ms=1140.0,
        service_ms=210.0,
        center_avg_bps=1180000.0,
        prb_util=0.982,
        center_share=0.861,
        edge_share=0.139,
        system_rate_bps=70100000.0,
    ),
    _row(
        dimension="center_packet_load_per_6_slots",
        value=16000,
        policy="business_aware_constrained_insert",
        completion_ms=820.0,
        queue_ms=608.0,
        service_ms=212.0,
        center_avg_bps=1025000.0,
        prb_util=0.991,
        center_share=0.752,
        edge_share=0.248,
        system_rate_bps=64800000.0,
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
        self.assertLess(anchors[2]["center_retention_pct"], 100.0)
        self.assertNotIn("system_retention_pct", anchors[0])

    def test_line_specs_use_two_policy_colors_and_metric_linestyles(self) -> None:
        delay_specs = _delay_line_specs()
        self.assertEqual(len({spec["color"] for spec in delay_specs if spec["policy_key"] == "baseline"}), 1)
        self.assertEqual(len({spec["color"] for spec in delay_specs if spec["policy_key"] == "ours"}), 1)
        self.assertNotEqual(
            {spec["color"] for spec in delay_specs if spec["policy_key"] == "baseline"},
            {spec["color"] for spec in delay_specs if spec["policy_key"] == "ours"},
        )
        self.assertEqual(
            {spec["metric_key"]: spec["linestyle"] for spec in delay_specs if spec["policy_key"] == "baseline"},
            {
                "target_edge_completion_delay_ms": "-",
                "target_edge_queue_wait_ms": "--",
                "target_edge_service_time_ms": ":",
            },
        )

        rate_specs = _rate_line_specs()
        self.assertEqual(len({spec["color"] for spec in rate_specs if spec["policy_key"] == "baseline"}), 1)
        self.assertEqual(len({spec["color"] for spec in rate_specs if spec["policy_key"] == "ours"}), 1)
        self.assertEqual(
            {spec["metric_key"]: spec["linestyle"] for spec in rate_specs if spec["policy_key"] == "baseline"},
            {
                "center_avg_rate_bps": "-",
                "prb_utilization": "--",
                "center": ":",
                "edge": "-.",
            },
        )

    def test_plot_writers_create_png_artifacts(self) -> None:
        user_pairs = _build_dimension_pairs(SAMPLE_ROWS, "center_user_count")
        load_pairs = _build_dimension_pairs(SAMPLE_ROWS, "center_packet_load_per_6_slots")
        anchors = _build_tradeoff_anchor_rows(SAMPLE_ROWS)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            user_count_edge_delay_path = output_dir / "user_count_sensitivity_edge_delay_breakdown.png"
            user_count_center_rate_prb_path = (
                output_dir / "user_count_sensitivity_center_rate_prb_util.png"
            )
            center_load_edge_delay_path = output_dir / "center_load_sensitivity_edge_delay_breakdown.png"
            center_load_center_rate_prb_path = (
                output_dir / "center_load_sensitivity_center_rate_prb_util.png"
            )
            anchor_plot_path = output_dir / "latency_throughput_tradeoff_pdb_anchors.png"

            _plot_edge_delay_breakdown(
                user_pairs,
                title="User Count Sensitivity",
                xlabel="center_user_count",
                output_path=user_count_edge_delay_path,
            )
            _plot_center_rate_prb_util(
                user_pairs,
                title="User Count Sensitivity",
                xlabel="center_user_count",
                output_path=user_count_center_rate_prb_path,
            )
            _plot_edge_delay_breakdown(
                load_pairs,
                title="Center Load Sensitivity",
                xlabel="center_packet_load_per_6_slots",
                output_path=center_load_edge_delay_path,
            )
            _plot_center_rate_prb_util(
                load_pairs,
                title="Center Load Sensitivity",
                xlabel="center_packet_load_per_6_slots",
                output_path=center_load_center_rate_prb_path,
            )
            _plot_tradeoff_anchors(anchors, output_path=anchor_plot_path)

            expected_paths = [
                user_count_edge_delay_path,
                user_count_center_rate_prb_path,
                center_load_edge_delay_path,
                center_load_center_rate_prb_path,
                anchor_plot_path,
            ]
            for path in expected_paths:
                with self.subTest(path=path.name):
                    self.assertTrue(path.exists())
                    self.assertGreater(path.stat().st_size, 0)
                    with path.open("rb") as handle:
                        self.assertEqual(handle.read(8), b"\x89PNG\r\n\x1a\n")

    def test_render_report_includes_sections_formulas_and_image_references(self) -> None:
        payload = {
            "simulation": {
                "slot_duration_ms": 1,
                "tdd_pattern": "DSUUU",
                "deadline_guard_ms": 10,
            },
            "resources": {
                "total_prb_per_u_slot": 273,
                "max_ue_per_slot": 16,
            },
            "traffic": {
                "center": {
                    "count": 63,
                    "period_slots": 6,
                    "packet_bits": 960,
                    "pdb_ms": None,
                },
                "edge": {
                    "count": 1,
                    "packet_bits": 3200000,
                    "pdb_ms": 500,
                },
            },
            "radio": {
                "environment": {
                    "scenario_type": "uma",
                    "center_distance_range_m": [50, 150],
                    "edge_distance_range_m": [375, 475],
                },
                "edge": {
                    "edge_per_u_slot_prb_cap": 273,
                },
            },
        }

        report = _render_report(
            payload=payload,
            user_count_pairs=_build_dimension_pairs(SAMPLE_ROWS, "center_user_count"),
            center_load_pairs=_build_dimension_pairs(SAMPLE_ROWS, "center_packet_load_per_6_slots"),
            anchor_rows=_build_tradeoff_anchor_rows(SAMPLE_ROWS),
        )

        expected_snippets = [
            "# 上行调度边缘时延-吞吐权衡实验报告",
            "## 1. 实验背景与目标",
            "## 2. 系统实现结构、系统参数与业务模型",
            "## 3. 指标定义与公式说明",
            "## 4. 敏感度分析结果",
            "## 6. 结论",
            "Completion Delay",
            "Queue Wait",
            "Service Time",
            "Analysis Window",
            "Control Phase Wait",
            "Pre-First-Service Wait",
            "Inter-Service Gap Wait",
            "Latency Gain (%)",
            "Center Throughput Retention (%)",
            "PRB_available,total",
            "Center PRB Utilization",
            "Edge PRB Utilization",
            "PRB_per_u_slot",
            "user_count_sensitivity_edge_delay_breakdown.png",
            "center_load_sensitivity_center_rate_prb_util.png",
            "latency_throughput_tradeoff_pdb_anchors.png",
            "PDB = 100 ms",
            "PDB = 500 ms",
            "High Load = 12000 bit / 6 slots",
            "图 1 横坐标：center_user_count",
            "图 1 纵坐标：边缘用户时延（ms）",
            "图 2 横坐标：center_user_count",
            "图 2 左纵坐标：中心用户平均速率（kbps）",
            "图 2 右纵坐标：PRB Utilization（%）",
            "图 3 横坐标：center_packet_load_per_6_slots",
            "图 3 纵坐标：边缘用户时延（ms）",
            "图 4 横坐标：center_packet_load_per_6_slots",
            "图 4 左纵坐标：中心用户平均速率（kbps）",
            "图 4 右纵坐标：PRB Utilization（%）",
            "变化上看",
            "增益上看",
            "| Value | Baseline Delay (ms) | Baseline Queue (ms) | Baseline Service (ms) | Ours Delay (ms) | Ours Queue (ms) | Ours Service (ms) | Latency Gain (%) | Center Throughput Retention (%) |",
            "图 4 数据表（中心速率与 PRB 利用率）",
            "| Value | Baseline Center Avg Rate (kbps) | Ours Center Avg Rate (kbps) | Baseline Total PRB Util (%) | Ours Total PRB Util (%) | Baseline Center PRB Util (%) | Ours Center PRB Util (%) | Baseline Edge PRB Util (%) | Ours Edge PRB Util (%) |",
            "| Anchor | Latency Gain (%) | Center Throughput Retention (%) |",
            "代表点 center_user_count = 63: 基线 Completion Delay 890.0 ms（Queue Wait 712.0 ms，Service Time 178.0 ms），本策略 Completion Delay 490.0 ms（Queue Wait 297.0 ms，Service Time 193.0 ms）",
            "High Load = 12000 bit / 6 slots: 基线 Completion Delay 1170.0 ms（Queue Wait 979.0 ms，Service Time 191.0 ms），本策略 Completion Delay 623.0 ms（Queue Wait 427.0 ms，Service Time 196.0 ms）",
        ]
        for snippet in expected_snippets:
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, report)
        self.assertNotIn("High Load = 16000 bit / 6 slots", report)
        self.assertNotIn("System Throughput Retention (%)", report)
        self.assertNotIn("系统吞吐保持率", report)


if __name__ == "__main__":
    unittest.main()
