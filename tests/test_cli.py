import json
import os
import subprocess
import unittest
from pathlib import Path


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
        self.assertIn("edge_pdb_ms,policy,target_edge_completion_delay_ms", result.stdout)
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
        self.assertIn("### 中心用户数趋势分析", report_text)
        self.assertIn("## 跨包大小趋势总结", report_text)
        self.assertIn("`edge_per_u_slot_prb_cap = 237`", report_text)

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


if __name__ == "__main__":
    unittest.main()
