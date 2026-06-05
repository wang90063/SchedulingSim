import csv
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


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
    csv_path = fixture_dir / "sensitivity_rows.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRADEOFF_CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


class CliSmokeTests(unittest.TestCase):
    def test_run_command_writes_report_file(self) -> None:
        result = subprocess.run(
            ["python", "-m", "scheduling_sim.cli", "run", "configs/edge_compare.json"],
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ, "PYTHONPATH": "src"},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("report.json", result.stdout)

    def test_run_command_supports_baseline_override(self) -> None:
        result = subprocess.run(
            [
                "python",
                "-m",
                "scheduling_sim.cli",
                "run",
                "configs/edge_compare.json",
                "--reinsert-policy",
                "tail_append",
            ],
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ, "PYTHONPATH": "src"},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("tail_append", result.stdout)

    def test_run_command_supports_target_only_override(self) -> None:
        result = subprocess.run(
            [
                "python",
                "-m",
                "scheduling_sim.cli",
                "run",
                "configs/target_edge_compare.json",
                "--reinsert-policy",
                "target_only_constrained_insert",
            ],
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ, "PYTHONPATH": "src"},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("target_only_constrained_insert", result.stdout)

    def test_run_command_supports_business_aware_override(self) -> None:
        result = subprocess.run(
            [
                "python",
                "-m",
                "scheduling_sim.cli",
                "run",
                "configs/target_edge_compare.json",
                "--reinsert-policy",
                "business_aware_constrained_insert",
            ],
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ, "PYTHONPATH": "src"},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("business_aware_constrained_insert", result.stdout)

    def test_target_edge_pdb_sweep_script_runs(self) -> None:
        result = subprocess.run(
            [
                "python",
                "scripts/run_target_edge_pdb_sweep.py",
                "configs/target_edge_business_aware_pdb_sweep.json",
            ],
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ, "PYTHONPATH": "src"},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("edge_pdb_ms,policy,center_user_gbr_satisfaction_rate", result.stdout)
        self.assertIn("analysis_window_ms", result.stdout)
        self.assertIn("center_used_prb", result.stdout)
        self.assertIn("100,business_aware_constrained_insert", result.stdout)
        self.assertIn("200,tail_append", result.stdout)

    def test_target_edge_pdb_dominance_diagnostic_script_runs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [
                "python",
                "scripts/run_target_edge_pdb_dominance_diagnostic.py",
                "configs/target_edge_pdb_dominance_diagnostic.json",
            ],
            cwd=repo_root,
            env={**os.environ, "PYTHONPATH": "src"},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=f"stderr:\n{result.stderr}")
        self.assertIn("policy,time_ms,phase,queue_rank", result.stdout)
        self.assertIn("tail_append", result.stdout)
        self.assertIn("business_aware_constrained_insert", result.stdout)

        output_dir = repo_root / "outputs" / "target_edge_pdb_dominance_diagnostic"
        self.assertTrue((output_dir / "diagnostic_report.md").exists())
        self.assertTrue((output_dir / "decision_trace.csv").exists())
        self.assertTrue((output_dir / "decision_trace.json").exists())
        self.assertTrue((output_dir / "queue_position_vs_time.png").exists())
        self.assertTrue((output_dir / "epf_rank_vs_time.png").exists())
        self.assertTrue((output_dir / "epf_rank_vs_time_first_100ms.png").exists())
        self.assertTrue((output_dir / "dominance_terms_vs_time.png").exists())
        self.assertTrue((output_dir / "dominance_terms_tail_append.png").exists())
        self.assertTrue((output_dir / "dominance_terms_business_aware_constrained_insert.png").exists())
        self.assertTrue((output_dir / "dominance_timeline.png").exists())
        self.assertTrue((output_dir / "dominance_timeline_tail_append.png").exists())
        self.assertTrue((output_dir / "dominance_timeline_business_aware_constrained_insert.png").exists())

        report_text = (output_dir / "diagnostic_report.md").read_text(encoding="utf-8")
        self.assertIn("Target Edge PDB Dominance Diagnostic", report_text)
        self.assertIn("queue_position_vs_time.png", report_text)
        self.assertIn("epf_rank_vs_time.png", report_text)
        self.assertIn("epf_rank_vs_time_first_100ms.png", report_text)
        self.assertIn("dominance_terms_vs_time.png", report_text)
        self.assertIn("dominance_terms_tail_append.png", report_text)
        self.assertIn("dominance_terms_business_aware_constrained_insert.png", report_text)
        self.assertIn("dominance_timeline.png", report_text)
        self.assertIn("dominance_timeline_tail_append.png", report_text)
        self.assertIn("dominance_timeline_business_aware_constrained_insert.png", report_text)
        self.assertIn("queue_limited", report_text)
        self.assertIn("spectral_dominated", report_text)
        self.assertIn("pdb_dominated", report_text)

    def test_target_edge_sensitivity_report_script_runs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [
                "python",
                "scripts/run_target_edge_sensitivity_report.py",
                "configs/target_edge_sensitivity_report.json",
            ],
            cwd=repo_root,
            env={**os.environ, "PYTHONPATH": "src"},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("dimension,value,policy,target_edge_finished", result.stdout)
        self.assertIn("edge_per_u_slot_prb_cap,12,tail_append", result.stdout)
        self.assertIn("center_user_count,79,business_aware_constrained_insert", result.stdout)
        self.assertNotIn("center_user_gbr_satisfaction_rate", result.stdout)
        report_path = repo_root / "outputs" / "target_edge_sensitivity" / "sensitivity_report.md"
        self.assertTrue(report_path.exists())
        report_text = report_path.read_text(encoding="utf-8")
        self.assertIn("Target Edge 参数敏感性测试报告", report_text)
        self.assertIn("Service Time", report_text)
        self.assertIn("每个 `DSUUU` 周期里，`D` 先做一次调度决策", report_text)
        self.assertIn("Queue Wait Breakdown", report_text)
        self.assertIn("### 趋势分析", report_text)
        self.assertIn("### `Control Phase Wait` 和 `Inter-Service Gap Wait` 的区别与联系", report_text)
        self.assertIn("### 为什么 `Service Time` 往往是我们略高一点", report_text)
        self.assertIn("## PRB Cap 分段总结", report_text)

    def test_target_edge_sensitivity_main_config_report_uses_configured_prb_budget(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [
                "python",
                "scripts/run_target_edge_sensitivity_report.py",
                "configs/target_edge_sensitivity_report_main.json",
            ],
            cwd=repo_root,
            env={**os.environ, "PYTHONPATH": "src"},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        report_path = repo_root / "outputs" / "target_edge_sensitivity_main" / "sensitivity_report.md"
        self.assertTrue(report_path.exists())
        report_text = report_path.read_text(encoding="utf-8")
        self.assertIn("每个 U-slot `237 PRB`", report_text)
        self.assertIn("固定 `edge_per_u_slot_prb_cap = 24`", report_text)
        self.assertIn("固定 `center_user_count = 63`", report_text)
        self.assertIn("固定 `edge_pdb_ms = 120`", report_text)

    def test_target_edge_sensitivity_main_400k_report_includes_breakdown_differences(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [
                "python",
                "scripts/run_target_edge_sensitivity_report.py",
                "configs/target_edge_sensitivity_report_main_400k_pdb500.json",
            ],
            cwd=repo_root,
            env={**os.environ, "PYTHONPATH": "src"},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("center_user_count,16,tail_append", result.stdout)
        self.assertIn("center_user_count,16,business_aware_constrained_insert", result.stdout)
        self.assertIn("center_user_count,23,tail_append", result.stdout)
        self.assertIn("center_user_count,23,business_aware_constrained_insert", result.stdout)
        self.assertIn("center_user_count,24,tail_append", result.stdout)
        self.assertIn("center_user_count,31,business_aware_constrained_insert", result.stdout)
        self.assertIn("edge_pdb_ms,100,tail_append", result.stdout)
        self.assertIn("edge_per_u_slot_prb_cap,12,business_aware_constrained_insert", result.stdout)
        report_path = repo_root / "outputs" / "target_edge_sensitivity_main_400kbit_pdb500" / "sensitivity_report.md"
        self.assertTrue(report_path.exists())
        report_text = report_path.read_text(encoding="utf-8")
        self.assertIn("Queue Wait Difference", report_text)
        self.assertIn("Inter-Service Gap Difference", report_text)
        self.assertIn("Service Time Difference", report_text)
        self.assertIn("目标包发完即停", report_text)
        self.assertIn("最大 `1000` 个周期作为安全上限", report_text)
        self.assertIn("`deadline_guard_ms = 10 ms`", report_text)
        self.assertIn("实际累计", report_text)
        self.assertIn("16 center users（1+16=17 UE）低负载场景", report_text)
        self.assertIn("先看 `17` 用户场景，也就是 `1+16`", report_text)
        self.assertIn("## 固定 1+16 用户场景：Edge PDB 扫描", report_text)
        self.assertIn("## 固定 1+16 用户场景：Edge PRB 上限扫描", report_text)
        self.assertIn("固定 `center_user_count = 16`（即 `1+16=17 UE`）", report_text)
        self.assertIn("## 固定 1+23 用户场景：Edge PDB 扫描", report_text)
        self.assertIn("## 固定 1+23 用户场景：Edge PRB 上限扫描", report_text)
        self.assertIn("固定 `center_user_count = 23`（即 `1+23=24 UE`）", report_text)
        self.assertIn("## 细粒度中心用户数扫描（1+23 到 1+31）", report_text)
        self.assertIn("`24 center users`", report_text)
        self.assertIn("`31 center users`", report_text)
        self.assertNotIn("unfinished -> 499 ms", report_text)
        self.assertNotIn("窗口内累计 `300 ms queue wait + 200 ms service time`", report_text)
        self.assertNotIn("基线 `0 ms = 300 ms queue wait + 200 ms service time`", report_text)

    def test_target_edge_packet_size_sensitivity_report_script_runs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [
                "python",
                "scripts/run_target_edge_packet_size_sensitivity_report.py",
                "configs/target_edge_packet_size_sensitivity_main_uncapped.json",
            ],
            cwd=repo_root,
            env={**os.environ, "PYTHONPATH": "src"},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=f"stderr:\n{result.stderr}")
        self.assertIn("edge_packet_kb,400,edge_pdb_ms,100,tail_append", result.stdout)
        self.assertIn(
            "edge_packet_kb,400,center_packet_granularity,160_per_1,tail_append",
            result.stdout,
        )
        self.assertIn(
            "edge_packet_kb,400,center_packet_granularity,960_per_6,business_aware_constrained_insert",
            result.stdout,
        )
        self.assertIn(
            "edge_packet_kb,2000,center_user_count,79,business_aware_constrained_insert",
            result.stdout,
        )
        report_path = (
            repo_root
            / "outputs"
            / "target_edge_packet_size_sensitivity_main_uncapped"
            / "sensitivity_report.md"
        )
        self.assertTrue(report_path.exists())
        report_text = report_path.read_text(encoding="utf-8")
        self.assertIn("Target Edge 大包规模敏感性测试报告", report_text)
        self.assertIn("## `400 KB` 目标边缘大包场景", report_text)
        self.assertIn("## `2000 KB` 目标边缘大包场景", report_text)
        self.assertIn("### PDB 趋势分析", report_text)
        self.assertIn("### 中心业务颗粒度扫描", report_text)
        self.assertIn("`160 bit / every 1 slot`", report_text)
        self.assertIn("`960 bit / every 6 slots`", report_text)
        self.assertIn("平均 offered load 近似保持一致", report_text)
        self.assertIn("### 中心业务负载扫描（固定 every 6 slots）", report_text)
        self.assertIn(
            "edge_packet_kb,400,center_packet_load_per_6_slots,3200,business_aware_constrained_insert",
            result.stdout,
        )
        self.assertIn(
            "edge_packet_kb,400,center_packet_load_per_6_slots,8000,business_aware_constrained_insert",
            result.stdout,
        )
        self.assertIn(
            "edge_packet_kb,400,center_packet_load_per_6_slots,16000,business_aware_constrained_insert",
            result.stdout,
        )
        self.assertIn("`3200 bit / every 6 slots`", report_text)
        self.assertIn("`8000 bit / every 6 slots`", report_text)
        self.assertIn("`16000 bit / every 6 slots`", report_text)
        self.assertIn("总 offered load 增大", report_text)
        self.assertIn("Baseline PRB Util", report_text)
        self.assertIn("Ours PRB Util", report_text)
        self.assertIn("`PRB Utilization`：系统在当前统计窗口内的 `total_prb_used / total_prb_available`", report_text)
        self.assertIn("拐点", report_text)
        self.assertIn("`4800 bit / every 6 slots`", report_text)
        self.assertIn("### 中心用户数趋势分析", report_text)
        self.assertIn("## 跨包大小趋势总结", report_text)
        self.assertIn("`edge_per_u_slot_prb_cap = 237`", report_text)
        rows_path = (
            repo_root
            / "outputs"
            / "target_edge_packet_size_sensitivity_main_uncapped"
            / "sensitivity_rows.csv"
        )
        rows_text = rows_path.read_text(encoding="utf-8")
        self.assertIn("analysis_window_ms", rows_text)
        self.assertIn("center_total_bits", rows_text)
        self.assertIn("edge_total_bits", rows_text)
        self.assertIn("target_edge_total_bits", rows_text)
        self.assertIn("system_total_bits", rows_text)
        self.assertIn("center_agg_rate_bps", rows_text)
        self.assertIn("edge_agg_rate_bps", rows_text)
        self.assertIn("target_edge_rate_bps", rows_text)
        self.assertIn("system_agg_rate_bps", rows_text)
        self.assertIn("center_used_prb", rows_text)
        self.assertIn("edge_used_prb", rows_text)
        self.assertIn("center_prb_share", rows_text)
        self.assertIn("edge_prb_share", rows_text)
        self.assertIn("center_bits_per_used_prb", rows_text)
        self.assertIn("edge_bits_per_used_prb", rows_text)

    def test_edge_ratio_sinr_snapshot_script_runs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [
                "python",
                "scripts/render_edge_ratio_sinr_snapshot.py",
                "outputs/edge_ratio_random_pdb_32users_packet_sweep_avg10_20260423_190938",
            ],
            cwd=repo_root,
            env={**os.environ, "PYTHONPATH": "src"},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("sinr_snapshot_report.md", result.stdout)

    def test_edge_ratio_packet_sweep_report_script_runs_on_small_random_fixture(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "edge_ratio_random_small.json"
            config_path.write_text(
                json.dumps(
                    {
                        "simulation": {
                            "cycles": 20,
                            "slot_duration_ms": 1,
                            "tdd_pattern": "DSUUU",
                            "random_seed": 7,
                            "stop_when_target_edge_finished": True,
                            "deadline_guard_ms": 10,
                        },
                        "resources": {"total_prb_per_u_slot": 273, "max_ue_per_slot": 16},
                        "traffic": {
                            "center": {
                                "count": 29,
                                "period_slots": 6,
                                "packet_bits": 960,
                                "pdb_ms": None,
                                "gbr_bps": 7000,
                            },
                            "edge": {"count": 3, "packet_bits": 80000, "pdb_ms": 800},
                        },
                        "radio": {
                            "environment": {
                                "scenario_type": "uma",
                                "cell_radius_m": 500,
                                "carrier_frequency_ghz": 3.5,
                                "noise_figure_db": 7.0,
                                "interference_margin_db": 3.0,
                                "shadow_std_db": 4.0,
                                "slow_fading_alpha": 0.95,
                                "slot_jitter_std_db": 0.5,
                                "center_distance_range_m": [50, 150],
                                "edge_distance_range_m": [375, 475],
                                "mcs_table": [
                                    {"sinr_db": -7.0, "mcs_index": 1, "bits_per_prb": 27},
                                    {"sinr_db": 4.0, "mcs_index": 6, "bits_per_prb": 212},
                                ],
                            },
                            "center": {},
                            "edge": {"edge_per_u_slot_prb_cap": 273},
                        },
                        "scheduler": {"ranking": "epf", "reinsert_policy": "business_aware_constrained_insert"},
                        "report": {"output_dir": str(Path(tmp) / "edge-ratio-random"), "keep_slot_trace": False},
                        "edge_ratio_sweep": {
                            "total_users": 32,
                            "requested_edge_ratio_pct": [10],
                            "repeat_count": 1,
                            "pdb_mode": "random",
                            "pdb_choices": [None, 200, 400],
                            "pdb_packet_kb_values": [10, 200],
                            "non_pdb_packet_bits": 960,
                            "non_pdb_period_slots": 6,
                            "policies": ["tail_append", "business_aware_constrained_insert"],
                            "random_seed_base": 7,
                            "reference_config": "outputs/center_pdb_null_rerun_prb273_20260421_000000/target_edge_packet_size_sensitivity_400kb/config_rerun.json",
                        },
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                ["python", "scripts/run_edge_ratio_packet_sweep_report.py", str(config_path)],
                cwd=repo_root,
                env={**os.environ, "PYTHONPATH": "src"},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("summary_report.md", result.stdout)

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
            self.assertEqual(result.returncode, 0, msg=f"stderr:\n{result.stderr}")
            self.assertIn(
                "uplink_scheduler_edge_delay_throughput_tradeoff_report.md",
                result.stdout,
            )

            artifacts = [
                result_root / "uplink_scheduler_edge_delay_throughput_tradeoff_report.md",
                result_root / "user_count_sensitivity_edge_delay_breakdown.png",
                result_root / "user_count_sensitivity_center_rate_prb_util.png",
                result_root / "center_load_sensitivity_edge_delay_breakdown.png",
                result_root / "center_load_sensitivity_center_rate_prb_util.png",
                result_root / "latency_throughput_tradeoff_pdb_anchors.png",
            ]
            for artifact in artifacts:
                self.assertTrue(artifact.exists(), msg=f"missing: {artifact}")
                self.assertGreater(artifact.stat().st_size, 0, msg=f"empty: {artifact}")

            report_text = (result_root / "uplink_scheduler_edge_delay_throughput_tradeoff_report.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("系统实现结构、系统参数与业务模型", report_text)
            self.assertIn("边缘时延收益与中心吞吐代价的权衡分析", report_text)
            self.assertIn("Latency Gain (%)", report_text)
            self.assertIn("Center Throughput Retention (%)", report_text)
            self.assertIn("Baseline Queue (ms)", report_text)
            self.assertIn("Ours Service (ms)", report_text)
            self.assertNotIn("System Throughput Retention (%)", report_text)
            self.assertIn("user_count_sensitivity_edge_delay_breakdown.png", report_text)
            self.assertIn("latency_throughput_tradeoff_pdb_anchors.png", report_text)

    def test_run_command_report_contains_grouped_metrics(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            ["python", "-m", "scheduling_sim.cli", "run", "configs/edge_compare.json"],
            cwd=repo_root,
            env={**os.environ, "PYTHONPATH": "src"},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        report_path = repo_root / "outputs" / "edge_compare" / "report.json"
        summary = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertIn("served_bits", summary)
        self.assertIn("center_completed_packets", summary)
        self.assertIn("edge_completed_packets", summary)
        self.assertIn("center_user_gbr_satisfaction_rate", summary)
        self.assertIn("edge_avg_hol_ms", summary)
        self.assertIn("target_edge_completion_delay_ms", summary)
        self.assertIn("target_edge_queue_wait_ms", summary)
        self.assertIn("analysis_window_ms", summary)
        self.assertIn("center_total_bits", summary)
        self.assertIn("edge_total_bits", summary)
        self.assertIn("target_edge_total_bits", summary)
        self.assertIn("system_total_bits", summary)
        self.assertIn("center_agg_rate_bps", summary)
        self.assertIn("edge_agg_rate_bps", summary)
        self.assertIn("target_edge_rate_bps", summary)
        self.assertIn("system_agg_rate_bps", summary)
        self.assertIn("center_used_prb", summary)
        self.assertIn("edge_used_prb", summary)
        self.assertIn("center_prb_share", summary)
        self.assertIn("edge_prb_share", summary)
        self.assertIn("center_bits_per_used_prb", summary)
        self.assertIn("edge_bits_per_used_prb", summary)


if __name__ == "__main__":
    unittest.main()
