# Target Edge Packet Size Sensitivity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a packet-size-first target-edge sensitivity experiment that scans `PDB` and center-user load for `400 KB` through `2000 KB`, then writes a detailed markdown report in the same style as the existing `400kbit pdb500` study.

**Architecture:** Introduce a dedicated config and a dedicated report script rather than overloading `scripts/run_target_edge_sensitivity_report.py`, so the existing single-size report remains stable. Keep the existing simulator/metrics pipeline unchanged, collect one flat row per `(packet_size, dimension, value, policy)` case, then render a new markdown structure with one section per packet size plus cross-size trend analysis.

**Tech Stack:** Python, `unittest`, existing `dataclasses.replace` config mutation helpers, markdown/CSV/JSON file output

---

### Task 1: Add failing config and smoke tests for the new packet-size report

**Files:**
- Modify: `tests/test_config.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing config-loader test**

```python
    def test_load_config_supports_packet_size_sensitivity_sweep(self) -> None:
        payload = {
            "simulation": {
                "cycles": 1000,
                "slot_duration_ms": 1,
                "tdd_pattern": "DSUUU",
                "random_seed": 7,
                "stop_when_target_edge_finished": True,
                "deadline_guard_ms": 10,
            },
            "resources": {"total_prb_per_u_slot": 237, "max_ue_per_slot": 16},
            "traffic": {
                "center": {"count": 63, "period_slots": 1, "packet_bits": 160, "pdb_ms": 1000000000, "gbr_bps": 7000},
                "edge": {"count": 1, "packet_bits": 3200000, "pdb_ms": 500},
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
                    "mcs_table_path": "mcs/nr_ul_main.json",
                },
                "center": {},
                "edge": {"edge_per_u_slot_prb_cap": 237},
            },
            "scheduler": {"ranking": "epf", "reinsert_policy": "business_aware_constrained_insert"},
            "report": {"output_dir": "outputs/packet-size-test", "keep_slot_trace": False},
            "sweep": {
                "policies": ["tail_append", "business_aware_constrained_insert"],
                "edge_packet_kb": [400, 800, 1200, 1600, 2000],
                "edge_pdb_ms": [100, 150, 200, 300, 400, 500],
                "center_user_count": [16, 23, 31, 47, 63, 79],
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            (config_dir / "mcs").mkdir()
            (config_dir / "mcs" / "nr_ul_main.json").write_text(
                json.dumps([{"sinr_db": -5.0, "mcs_index": 0, "spectral_efficiency": 1.0}]),
                encoding="utf-8",
            )
            path = config_dir / "config.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            config = load_config(path)
        self.assertEqual(config.radio.edge.edge_per_u_slot_prb_cap, 237)
        self.assertEqual(config.traffic.edge.packet_bits, 3200000)
```

- [ ] **Step 2: Run the config test to verify it passes or fails for the right reason**

Run: `PYTHONPATH=src python -m unittest tests.test_config.ConfigLoaderTests.test_load_config_supports_packet_size_sensitivity_sweep -v`
Expected: PASS if generic config loading already accepts the new sweep keys untouched; if it fails, the failure should point to config-shape assumptions that must be relaxed.

- [ ] **Step 3: Write the failing packet-size report smoke test**

```python
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
        self.assertEqual(result.returncode, 0)
        self.assertIn("edge_packet_kb,400,edge_pdb_ms,100,tail_append", result.stdout)
        self.assertIn("edge_packet_kb,2000,center_user_count,79,business_aware_constrained_insert", result.stdout)
        report_path = repo_root / "outputs" / "target_edge_packet_size_sensitivity_main_uncapped" / "sensitivity_report.md"
        self.assertTrue(report_path.exists())
        report_text = report_path.read_text(encoding="utf-8")
        self.assertIn("Target Edge 大包规模敏感性测试报告", report_text)
        self.assertIn("## `400 KB` 目标边缘大包场景", report_text)
        self.assertIn("## `2000 KB` 目标边缘大包场景", report_text)
        self.assertIn("### PDB 趋势分析", report_text)
        self.assertIn("### 中心用户数趋势分析", report_text)
        self.assertIn("## 跨包大小趋势总结", report_text)
        self.assertIn("`edge_per_u_slot_prb_cap = 237`", report_text)
```

- [ ] **Step 4: Run the smoke test to verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_packet_size_sensitivity_report_script_runs -v`
Expected: FAIL because `scripts/run_target_edge_packet_size_sensitivity_report.py` and the dedicated config do not exist yet.

- [ ] **Step 5: Commit the red tests**

```bash
git add tests/test_cli.py tests/test_config.py
git commit -m "test: add packet size sensitivity report coverage"
```

### Task 2: Add the dedicated packet-size experiment config

**Files:**
- Create: `configs/target_edge_packet_size_sensitivity_main_uncapped.json`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Add the new experiment config**

```json
{
  "simulation": {
    "cycles": 1000,
    "slot_duration_ms": 1,
    "tdd_pattern": "DSUUU",
    "random_seed": 7,
    "stop_when_target_edge_finished": true,
    "deadline_guard_ms": 10
  },
  "resources": { "total_prb_per_u_slot": 237, "max_ue_per_slot": 16 },
  "traffic": {
    "center": { "count": 63, "period_slots": 1, "packet_bits": 160, "pdb_ms": 1000000000, "gbr_bps": 7000 },
    "edge": { "count": 1, "packet_bits": 3200000, "pdb_ms": 500 }
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
      "mcs_table_path": "mcs/nr_ul_main.json"
    },
    "center": {},
    "edge": { "edge_per_u_slot_prb_cap": 237 }
  },
  "scheduler": { "ranking": "epf", "reinsert_policy": "business_aware_constrained_insert" },
  "report": { "output_dir": "outputs/target_edge_packet_size_sensitivity_main_uncapped", "keep_slot_trace": false },
  "sweep": {
    "policies": ["tail_append", "business_aware_constrained_insert"],
    "edge_packet_kb": [400, 800, 1200, 1600, 2000],
    "edge_pdb_ms": [100, 150, 200, 300, 400, 500],
    "center_user_count": [16, 23, 31, 47, 63, 79]
  }
}
```

- [ ] **Step 2: Run the config smoke test to verify the new config is loadable**

Run: `PYTHONPATH=src python -m unittest tests.test_config.ConfigLoaderTests.test_load_config_supports_packet_size_sensitivity_sweep -v`
Expected: PASS

- [ ] **Step 3: Commit the config**

```bash
git add configs/target_edge_packet_size_sensitivity_main_uncapped.json
git commit -m "config: add uncapped packet size sensitivity sweep"
```

### Task 3: Implement row collection for packet-size-first sweeps

**Files:**
- Create: `scripts/run_target_edge_packet_size_sensitivity_report.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Start the new script with load/run helpers**

```python
import csv
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from scheduling_sim.config import load_config
from scheduling_sim.metrics import MetricsCollector
from scheduling_sim.scenario import ScenarioFactory
from scheduling_sim.simulator import UlSimulator


def _load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_summary(config) -> dict[str, float]:
    users = ScenarioFactory(config).build_users()
    return UlSimulator(config, users, MetricsCollector()).run()
```

- [ ] **Step 2: Add packet-size-aware case mutation**

```python
def _packet_bits_from_kb(edge_packet_kb: int) -> int:
    return int(edge_packet_kb) * 1000 * 8


def _case_config(config, *, edge_packet_kb: int, dimension: str, value: int, policy: str):
    updated = replace(
        config,
        scheduler=replace(config.scheduler, reinsert_policy=policy),
        traffic=replace(
            config.traffic,
            edge=replace(config.traffic.edge, packet_bits=_packet_bits_from_kb(edge_packet_kb)),
        ),
    )
    if dimension == "edge_pdb_ms":
        return replace(
            updated,
            traffic=replace(updated.traffic, edge=replace(updated.traffic.edge, pdb_ms=value)),
        )
    if dimension == "center_user_count":
        return replace(
            updated,
            traffic=replace(updated.traffic, center=replace(updated.traffic.center, count=value)),
        )
    raise ValueError(f"unsupported dimension: {dimension}")
```

- [ ] **Step 3: Collect one row per `(packet size, dimension, value, policy)`**

```python
def _collect_rows(config, sweep_spec: dict[str, Any]) -> list[dict[str, float | int | str | bool]]:
    rows: list[dict[str, float | int | str | bool]] = []
    policies = tuple(sweep_spec.get("policies", ("tail_append", "business_aware_constrained_insert")))
    for edge_packet_kb in sweep_spec.get("edge_packet_kb", []):
        for edge_pdb_ms in sweep_spec.get("edge_pdb_ms", []):
            for policy in policies:
                summary = _run_summary(
                    _case_config(
                        config,
                        edge_packet_kb=int(edge_packet_kb),
                        dimension="edge_pdb_ms",
                        value=int(edge_pdb_ms),
                        policy=policy,
                    )
                )
                rows.append(
                    {
                        "edge_packet_kb": int(edge_packet_kb),
                        "edge_packet_bits": _packet_bits_from_kb(int(edge_packet_kb)),
                        "dimension": "edge_pdb_ms",
                        "value": int(edge_pdb_ms),
                        "policy": policy,
                        "target_edge_finished": bool(summary["target_edge_finished"]),
                        "target_edge_completion_delay_ms": summary["target_edge_completion_delay_ms"],
                        "target_edge_queue_wait_ms": summary["target_edge_queue_wait_ms"],
                        "target_edge_service_time_ms": summary["target_edge_service_time_ms"],
                        "target_edge_control_phase_wait_ms": summary["target_edge_control_phase_wait_ms"],
                        "target_edge_pre_first_service_wait_ms": summary["target_edge_pre_first_service_wait_ms"],
                        "target_edge_inter_service_gap_wait_ms": summary["target_edge_inter_service_gap_wait_ms"],
                        "target_edge_time_to_first_service_ms": summary["target_edge_time_to_first_service_ms"],
                        "target_edge_pdb_met": bool(summary["target_edge_pdb_met"]),
                        "target_edge_remaining_bits": summary["target_edge_remaining_bits"],
                        "center_avg_rate_bps": summary["center_avg_rate_bps"],
                    }
                )
        for center_user_count in sweep_spec.get("center_user_count", []):
            for policy in policies:
                summary = _run_summary(
                    _case_config(
                        config,
                        edge_packet_kb=int(edge_packet_kb),
                        dimension="center_user_count",
                        value=int(center_user_count),
                        policy=policy,
                    )
                )
                rows.append(
                    {
                        "edge_packet_kb": int(edge_packet_kb),
                        "edge_packet_bits": _packet_bits_from_kb(int(edge_packet_kb)),
                        "dimension": "center_user_count",
                        "value": int(center_user_count),
                        "policy": policy,
                        "target_edge_finished": bool(summary["target_edge_finished"]),
                        "target_edge_completion_delay_ms": summary["target_edge_completion_delay_ms"],
                        "target_edge_queue_wait_ms": summary["target_edge_queue_wait_ms"],
                        "target_edge_service_time_ms": summary["target_edge_service_time_ms"],
                        "target_edge_control_phase_wait_ms": summary["target_edge_control_phase_wait_ms"],
                        "target_edge_pre_first_service_wait_ms": summary["target_edge_pre_first_service_wait_ms"],
                        "target_edge_inter_service_gap_wait_ms": summary["target_edge_inter_service_gap_wait_ms"],
                        "target_edge_time_to_first_service_ms": summary["target_edge_time_to_first_service_ms"],
                        "target_edge_pdb_met": bool(summary["target_edge_pdb_met"]),
                        "target_edge_remaining_bits": summary["target_edge_remaining_bits"],
                        "center_avg_rate_bps": summary["center_avg_rate_bps"],
                    }
                )
    return rows
```

- [ ] **Step 4: Write the CSV/JSON outputs and print CSV rows to stdout**

```python
def _write_outputs(output_dir: Path, rows: list[dict[str, float | int | str | bool]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    csv_path = output_dir / "sensitivity_report.csv"
    json_path = output_dir / "sensitivity_report.json"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
```

- [ ] **Step 5: Run the smoke test to verify the script now fails later in report rendering**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_packet_size_sensitivity_report_script_runs -v`
Expected: FAIL because the script should now exist and emit CSV rows, but the markdown report content and file are still missing.

- [ ] **Step 6: Commit the row-collection script**

```bash
git add scripts/run_target_edge_packet_size_sensitivity_report.py
git commit -m "feat: collect packet size sensitivity rows"
```

### Task 4: Render packet-size-first markdown sections with trend explanations

**Files:**
- Modify: `scripts/run_target_edge_packet_size_sensitivity_report.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Add packet-size grouping and section rendering helpers**

```python
def _rows_for(rows, *, edge_packet_kb: int, dimension: str) -> list[dict[str, float | int | str | bool]]:
    return [
        row
        for row in rows
        if int(row["edge_packet_kb"]) == edge_packet_kb and row["dimension"] == dimension
    ]


def _value_label(dimension: str, value: int) -> str:
    return {
        "edge_pdb_ms": f"{value} ms",
        "center_user_count": f"{value} center users",
    }[dimension]
```

- [ ] **Step 2: Render the per-dimension comparison table**

```python
def _build_table(rows: list[dict[str, float | int | str | bool]], *, dimension: str) -> list[str]:
    lines = [
        "| 参数值 | Baseline Completion | Ours Completion | Baseline Queue Wait | Ours Queue Wait | Baseline Service | Ours Service | Baseline PDB | Ours PDB | Baseline Center Avg | Ours Center Avg | 结论 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | --- |",
    ]
    values = sorted({int(row["value"]) for row in rows})
    for value in values:
        baseline = next(row for row in rows if int(row["value"]) == value and row["policy"] == "tail_append")
        ours = next(
            row
            for row in rows
            if int(row["value"]) == value and row["policy"] == "business_aware_constrained_insert"
        )
        delta_ms = float(baseline["target_edge_completion_delay_ms"]) - float(ours["target_edge_completion_delay_ms"])
        ratio = 0.0 if float(baseline["target_edge_completion_delay_ms"]) == 0.0 else (
            delta_ms / float(baseline["target_edge_completion_delay_ms"]) * 100.0
        )
        lines.append(
            "| "
            f"`{_value_label(dimension, value)}` | "
            f"`{float(baseline['target_edge_completion_delay_ms']):.0f} ms` | "
            f"`{float(ours['target_edge_completion_delay_ms']):.0f} ms` | "
            f"`{float(baseline['target_edge_queue_wait_ms']):.0f} ms` | "
            f"`{float(ours['target_edge_queue_wait_ms']):.0f} ms` | "
            f"`{float(baseline['target_edge_service_time_ms']):.0f} ms` | "
            f"`{float(ours['target_edge_service_time_ms']):.0f} ms` | "
            f"`{bool(baseline['target_edge_pdb_met'])}` | "
            f"`{bool(ours['target_edge_pdb_met'])}` | "
            f"`{float(baseline['center_avg_rate_bps']):.0f} bps` | "
            f"`{float(ours['center_avg_rate_bps']):.0f} bps` | "
            f"{delta_ms:.0f} ms ({ratio:.1f}%) |"
        )
    return lines
```

- [ ] **Step 3: Add section-level trend text and cross-size summary**

```python
def _packet_size_heading(edge_packet_kb: int) -> str:
    return f"## `{edge_packet_kb} KB` 目标边缘大包场景"


def _build_packet_size_section(edge_packet_kb: int, rows: list[dict[str, float | int | str | bool]]) -> str:
    pdb_rows = _rows_for(rows, edge_packet_kb=edge_packet_kb, dimension="edge_pdb_ms")
    center_rows = _rows_for(rows, edge_packet_kb=edge_packet_kb, dimension="center_user_count")
    return "\n".join(
        [
            _packet_size_heading(edge_packet_kb),
            "",
            f"- 固定 `edge_packet_kb = {edge_packet_kb}`",
            "- 固定 `edge_per_u_slot_prb_cap = 237`",
            "",
            "### PDB 扫描",
            "- 固定 `center_user_count = 63`",
            "",
            *_build_table(pdb_rows, dimension="edge_pdb_ms"),
            "",
            "### PDB 趋势分析",
            "- 重点解释 `PDB` 收紧或放松时，完成时延收益主要来自 `Queue Wait` 还是 `Service Time`。",
            "- 重点解释在当前包大小下，deadline 压力是否让 `business_aware_constrained_insert` 更容易压缩 `Inter-Service Gap Wait`。",
            "",
            "### 中心用户数扫描",
            "- 固定 `edge_pdb_ms = 500`",
            "",
            *_build_table(center_rows, dimension="center_user_count"),
            "",
            "### 中心用户数趋势分析",
            "- 重点解释负载升高后，baseline 队尾轮转等待如何放大，以及我们的收益与中心吞吐代价是否同步扩大。",
            "",
            "### 小结",
            "- 总结该包大小下的主要收益区间、主要代价和是否出现策略收敛。",
        ]
    )
```

- [ ] **Step 4: Build the full markdown report**

```python
def _write_markdown_report(payload: dict[str, Any], output_dir: Path, rows: list[dict[str, float | int | str | bool]]) -> None:
    sections = [
        "# Target Edge 大包规模敏感性测试报告",
        "",
        "## 场景设置",
        "",
        "- TDD：`DSUUU`，每 slot `1 ms`，目标包发完即停；最大 `1000` 个周期作为安全上限（`5000 ms`）",
        "- 调度资源：每个 U-slot `237 PRB`，边缘目标用户固定 `edge_per_u_slot_prb_cap = 237`，即边缘无额外 cap 限制",
        "- 对比策略：`tail_append` 与 `business_aware_constrained_insert`",
        "- 扫描维度：`400 / 800 / 1200 / 1600 / 2000 KB`，每档下再扫描 `PDB` 与中心用户数",
        "",
        "## 指标说明",
        "",
        "- `Completion Delay`：目标边缘大包从到达到完成的总时延",
        "- `Queue Wait`：目标包总时延中未真正传 bit 的累计等待时间",
        "- `Service Time`：目标包实际占用的 `U` slot 数量 × `1 ms`",
        "- `Center Avg Rate`：目标包完成前中心背景用户的平均吞吐",
        "",
    ]
    for edge_packet_kb in payload.get("sweep", {}).get("edge_packet_kb", []):
        sections.extend([_build_packet_size_section(int(edge_packet_kb), rows), ""])
    sections.extend(
        [
            "## 跨包大小趋势总结",
            "",
            "- 重点总结包越大时，完成时延绝对收益与相对收益是否同步扩大。",
            "- 重点总结收益是否继续主要来自 `Queue Wait` 与 `Inter-Service Gap Wait` 的下降。",
            "- 重点总结边缘无 cap 条件下中心吞吐代价是否随包大小放大。",
            "",
            "## 结论",
            "",
            "- 用 3-5 条结论总结大包规模、PDB 压力、系统负载和中心代价之间的关系。",
        ]
    )
    (output_dir / "sensitivity_report.md").write_text("\n".join(sections), encoding="utf-8")
```

- [ ] **Step 5: Wire the script entrypoint**

```python
def main() -> int:
    config_path = Path(sys.argv[1])
    payload = _load_payload(config_path)
    config = load_config(config_path)
    rows = _collect_rows(config, payload.get("sweep", {}))
    output_dir = Path(config.report.output_dir)
    _write_outputs(output_dir, rows)
    _write_markdown_report(payload, output_dir, rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Run the new report smoke test to verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_packet_size_sensitivity_report_script_runs -v`
Expected: PASS

- [ ] **Step 7: Commit the markdown report renderer**

```bash
git add scripts/run_target_edge_packet_size_sensitivity_report.py tests/test_cli.py
git commit -m "feat: render packet size sensitivity report"
```

### Task 5: Run the full experiment and verify output artifacts

**Files:**
- Modify: `scripts/run_target_edge_packet_size_sensitivity_report.py` (if report text needs one final adjustment after reviewing real outputs)
- Output: `outputs/target_edge_packet_size_sensitivity_main_uncapped/sensitivity_report.csv`
- Output: `outputs/target_edge_packet_size_sensitivity_main_uncapped/sensitivity_report.json`
- Output: `outputs/target_edge_packet_size_sensitivity_main_uncapped/sensitivity_report.md`

- [ ] **Step 1: Run the dedicated packet-size report script**

Run: `PYTHONPATH=src python scripts/run_target_edge_packet_size_sensitivity_report.py configs/target_edge_packet_size_sensitivity_main_uncapped.json`
Expected: exit `0`, CSV rows printed to stdout, and all three output files created under `outputs/target_edge_packet_size_sensitivity_main_uncapped/`

- [ ] **Step 2: Run the focused regression suite**

Run: `PYTHONPATH=src python -m unittest tests.test_config.ConfigLoaderTests.test_load_config_supports_packet_size_sensitivity_sweep tests.test_cli.CliSmokeTests.test_target_edge_packet_size_sensitivity_report_script_runs -v`
Expected: PASS

- [ ] **Step 3: Run the broader CLI/config regression suite**

Run: `PYTHONPATH=src python -m unittest tests.test_cli tests.test_config -v`
Expected: PASS

- [ ] **Step 4: Spot-check report contents**

Run: `rg -n "Target Edge 大包规模敏感性测试报告|## \`400 KB\`|## \`2000 KB\`|### PDB 趋势分析|### 中心用户数趋势分析|## 跨包大小趋势总结|edge_per_u_slot_prb_cap = 237" outputs/target_edge_packet_size_sensitivity_main_uncapped/sensitivity_report.md`
Expected: all required headings and the uncapped-cap statement are present

- [ ] **Step 5: Commit the finished experiment pipeline**

```bash
git add configs/target_edge_packet_size_sensitivity_main_uncapped.json \
    scripts/run_target_edge_packet_size_sensitivity_report.py \
    tests/test_cli.py tests/test_config.py
git commit -m "feat: add packet size sensitivity experiment"
```
