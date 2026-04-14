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
        report_path = repo_root / "outputs" / "target_edge_sensitivity_main_400kbit_pdb500" / "sensitivity_report.md"
        self.assertTrue(report_path.exists())
        report_text = report_path.read_text(encoding="utf-8")
        self.assertIn("Queue Wait Difference", report_text)
        self.assertIn("Inter-Service Gap Difference", report_text)
        self.assertIn("Service Time Difference", report_text)
        self.assertIn("目标包发完即停", report_text)
        self.assertIn("最大 `1000` 个周期作为安全上限", report_text)
        self.assertIn("实际累计", report_text)
        self.assertNotIn("unfinished -> 499 ms", report_text)
        self.assertNotIn("窗口内累计 `300 ms queue wait + 200 ms service time`", report_text)
        self.assertNotIn("基线 `0 ms = 300 ms queue wait + 200 ms service time`", report_text)

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
