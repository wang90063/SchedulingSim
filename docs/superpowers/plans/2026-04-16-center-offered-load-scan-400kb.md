# Center Offered Load Scan at 400KB Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Change the default center-traffic baseline to `960 bit / every 6 slots` and add a `400 KB`-only center-offered-load scan to the existing packet-size sensitivity report.

**Architecture:** Keep the existing packet-size report pipeline and extend it surgically. Update the shared default center traffic in the JSON config, add a new `center_offered_load_packet_bits` sweep that only runs inside the `400 KB` chapter, reuse the existing row/table/report pipeline with one extra dimension, and keep the previously added `center_packet_granularity` section intact so the report shows both fragmentation and offered-load views.

**Tech Stack:** Python 3, JSON experiment configs, dataclasses `replace(...)`, existing `UlSimulator`/`ScenarioFactory` flow, `unittest` CLI smoke tests

---

## File Map

- `configs/target_edge_packet_size_sensitivity_main_uncapped.json`
  - Owns the default packet-size sensitivity experiment baseline and sweep matrix.
  - Will change the default center traffic from `160/1` to `960/6` and add the new `center_offered_load_packet_bits` list.
- `scripts/run_target_edge_packet_size_sensitivity_report.py`
  - Owns row collection, dimension labeling, stdout/CSV/JSON serialization, and markdown report rendering.
  - Will gain a new `center_offered_load` dimension and a new `400 KB`-only markdown subsection.
- `tests/test_cli.py`
  - Owns smoke coverage for the report script.
  - Will lock the new stdout row keys, the new section title, and the new labels/wording in the markdown report.

### Task 1: Lock the new default baseline and report surface in config/tests

**Files:**
- Modify: `configs/target_edge_packet_size_sensitivity_main_uncapped.json`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test expectations**

Inside `tests/test_cli.py`, update `test_target_edge_packet_size_sensitivity_report_script_runs` so it asserts the new default/load-scan surface:

```python
        self.assertIn(
            "edge_packet_kb,400,center_offered_load,960,business_aware_constrained_insert",
            result.stdout,
        )
        self.assertIn(
            "edge_packet_kb,400,center_offered_load,2880,tail_append",
            result.stdout,
        )
        self.assertIn("### 中心业务负载扫描", report_text)
        self.assertIn("`960 bit / every 6 slots`", report_text)
        self.assertIn("`1440 bit / every 6 slots`", report_text)
        self.assertIn("`1920 bit / every 6 slots`", report_text)
        self.assertIn("`2880 bit / every 6 slots`", report_text)
        self.assertIn("中心 offered load 增加后", report_text)
```

Also keep the existing assertions for:

```python
        self.assertIn("### 中心业务颗粒度扫描", report_text)
        self.assertIn("### 中心用户数趋势分析", report_text)
        self.assertIn("## 跨包大小趋势总结", report_text)
```

This preserves the expectation that the new scan is additive, not a replacement.

- [ ] **Step 2: Run the focused test to verify it fails first**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_packet_size_sensitivity_report_script_runs -v`

Expected: FAIL because the current script does not emit any `center_offered_load` rows and the report does not yet contain the new section.

- [ ] **Step 3: Update the config baseline and add the new sweep list**

Edit `configs/target_edge_packet_size_sensitivity_main_uncapped.json` so the `traffic.center` baseline becomes:

```json
    "center": {
      "count": 63,
      "period_slots": 6,
      "packet_bits": 960,
      "pdb_ms": 1000000000,
      "gbr_bps": 7000
    },
```

Then add a new list under `"sweep"`:

```json
    "center_offered_load_packet_bits": [960, 1440, 1920, 2880],
```

Keep the existing `center_packet_granularity` sweep unchanged so the previous fragmentation study still renders.

- [ ] **Step 4: Re-run the focused test to confirm the failure is now script-side only**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_packet_size_sensitivity_report_script_runs -v`

Expected: FAIL again, but now the config is valid and the remaining failure is that the script/report do not yet consume `center_offered_load_packet_bits`.

- [ ] **Step 5: Commit**

```bash
git add configs/target_edge_packet_size_sensitivity_main_uncapped.json tests/test_cli.py
git commit -m "test: define 400kb center offered load expectations"
```

### Task 2: Extend row generation for the new center-offered-load dimension

**Files:**
- Modify: `scripts/run_target_edge_packet_size_sensitivity_report.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Keep the stdout expectations as the failing contract**

The focused test should continue to require these rows:

```python
        self.assertIn(
            "edge_packet_kb,400,center_offered_load,960,business_aware_constrained_insert",
            result.stdout,
        )
        self.assertIn(
            "edge_packet_kb,400,center_offered_load,2880,tail_append",
            result.stdout,
        )
```

This locks in the new dimension name as `center_offered_load` and the row value format as a plain integer packet-bit count.

- [ ] **Step 2: Run the focused test to verify the row expectations still fail**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_packet_size_sensitivity_report_script_runs -v`

Expected: FAIL because `_collect_rows()` only emits `edge_pdb_ms`, `center_user_count`, and `center_packet_granularity`.

- [ ] **Step 3: Implement minimal row-generation support**

In `scripts/run_target_edge_packet_size_sensitivity_report.py`, update `_case_config()` so it handles the new dimension by changing only `config.traffic.center.packet_bits` while leaving `period_slots` untouched at the config baseline:

```python
def _case_config(config, *, edge_packet_kb: int, dimension: str, value: int | str, policy: str):
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
            traffic=replace(updated.traffic, edge=replace(updated.traffic.edge, pdb_ms=int(value))),
        )
    if dimension == "center_user_count":
        return replace(
            updated,
            traffic=replace(updated.traffic, center=replace(updated.traffic.center, count=int(value))),
        )
    if dimension == "center_packet_granularity":
        packet_bits, period_slots = _parse_granularity_value(str(value))
        return replace(
            updated,
            traffic=replace(
                updated.traffic,
                center=replace(updated.traffic.center, packet_bits=packet_bits, period_slots=period_slots),
            ),
        )
    if dimension == "center_offered_load":
        return replace(
            updated,
            traffic=replace(
                updated.traffic,
                center=replace(updated.traffic.center, packet_bits=int(value)),
            ),
        )
    raise ValueError(f"unsupported dimension: {dimension}")
```

Then extend `_collect_rows()` with a `400 KB`-only branch:

```python
        if int(edge_packet_kb) == CENTER_PACKET_GRANULARITY_EDGE_PACKET_KB:
            for center_packet_bits in sweep_spec.get("center_offered_load_packet_bits", []):
                for policy in policies:
                    summary = _run_summary(
                        _case_config(
                            config,
                            edge_packet_kb=int(edge_packet_kb),
                            dimension="center_offered_load",
                            value=int(center_packet_bits),
                            policy=policy,
                        )
                    )
                    rows.append(
                        _build_row(
                            edge_packet_kb=int(edge_packet_kb),
                            dimension="center_offered_load",
                            value=int(center_packet_bits),
                            policy=policy,
                            summary=summary,
                        )
                    )
```

Do not change the stdout serializer shape; it already writes `row["value"]` directly and can handle integer values for this new dimension.

- [ ] **Step 4: Teach labels/sorting to recognize the new dimension**

Add a new branch in `_value_label()`:

```python
    if dimension == "center_offered_load":
        center_period_slots = 6
        slot_label = "slot" if center_period_slots == 1 else "slots"
        return f"{value} bit / every {center_period_slots} {slot_label}"
```

The existing numeric sort path in `_build_table()` should continue to work because `center_offered_load` uses integer values.

- [ ] **Step 5: Re-run the focused test to verify stdout now passes**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_packet_size_sensitivity_report_script_runs -v`

Expected: still FAIL, but now the stdout assertions should pass and the remaining failure should be the missing markdown subsection/content.

- [ ] **Step 6: Commit**

```bash
git add scripts/run_target_edge_packet_size_sensitivity_report.py tests/test_cli.py
git commit -m "feat: collect 400kb center offered load rows"
```

### Task 3: Render the new 400 KB markdown subsection and update baseline wording

**Files:**
- Modify: `scripts/run_target_edge_packet_size_sensitivity_report.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Keep the markdown assertions as the failing contract**

The focused test should continue to require:

```python
        self.assertIn("### 中心业务负载扫描", report_text)
        self.assertIn("`960 bit / every 6 slots`", report_text)
        self.assertIn("`1440 bit / every 6 slots`", report_text)
        self.assertIn("`1920 bit / every 6 slots`", report_text)
        self.assertIn("`2880 bit / every 6 slots`", report_text)
        self.assertIn("中心 offered load 增加后", report_text)
```

- [ ] **Step 2: Run the focused test and confirm the report assertions still fail**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_packet_size_sensitivity_report_script_runs -v`

Expected: FAIL because `_build_packet_size_section()` does not yet render the new subsection.

- [ ] **Step 3: Add the new subsection inside `_build_packet_size_section()`**

Collect the rows alongside the existing section data:

```python
    offered_load_rows = _rows_for(
        rows,
        edge_packet_kb=edge_packet_kb,
        dimension="center_offered_load",
    )
```

Then, inside the `if edge_packet_kb == CENTER_PACKET_GRANULARITY_EDGE_PACKET_KB:` block, append a second `400 KB`-only subsection after the existing granularity section:

```python
    if edge_packet_kb == CENTER_PACKET_GRANULARITY_EDGE_PACKET_KB and offered_load_rows:
        lines.extend(
            [
                "### 中心业务负载扫描",
                "- 固定 `edge_pdb_ms = 500`",
                "- 固定 `center_user_count = 63`",
                "- 固定 `center_period_slots = 6`，只提升每次到达的 `packet_bits`，观察中心 offered load 增加后边缘完成时延是否同步变长。",
                "",
                *_build_table(offered_load_rows, dimension="center_offered_load"),
                "",
                "### 中心业务负载趋势分析",
                "- 重点观察中心 offered load 增加后，目标边缘包的 `Completion Delay` 是否单调增长。",
                "- 重点区分增长主要来自 `Queue Wait` 拉长，还是 `Service Time` 被切碎。",
                "- 重点比较更高中心负载下，两种策略是否仍能保持相对收益。",
                "",
            ]
        )
```

- [ ] **Step 4: Refresh the scene-setting text so the baseline matches the new default**

In `_write_markdown_report()`, expand the scenario bullets so the report states the new default center-traffic baseline explicitly:

```python
        "- 默认中心背景业务：`63` 个中心用户，基线口径为 `960 bit / every 6 slots`",
```

Also update the scan summary bullet from:

```python
        "- 扫描维度：`400 / 800 / 1200 / 1600 / 2000 KB`，每档下再扫描 `PDB` 与中心用户数",
```

to:

```python
        "- 扫描维度：`400 / 800 / 1200 / 1600 / 2000 KB`，每档下扫描 `PDB` 与中心用户数；`400 KB` 章节额外包含中心业务颗粒度与中心业务负载扫描",
```

This keeps the top-level report honest after the default baseline changes.

- [ ] **Step 5: Re-run the focused test to verify the report now passes**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_packet_size_sensitivity_report_script_runs -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add scripts/run_target_edge_packet_size_sensitivity_report.py tests/test_cli.py
git commit -m "feat: add 400kb center offered load section"
```

### Task 4: Run broader verification and inspect the generated report

**Files:**
- Verify: `tests/test_cli.py`
- Verify output: `outputs/target_edge_packet_size_sensitivity_main_uncapped/sensitivity_report.md`

- [ ] **Step 1: Run the packet-size-related CLI coverage set**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_packet_size_sensitivity_report_script_runs tests.test_cli.CliSmokeTests.test_target_edge_sensitivity_main_400k_report_includes_breakdown_differences tests.test_cli.CliSmokeTests.test_target_edge_sensitivity_main_config_report_uses_configured_prb_budget -v`

Expected:

```text
... ok
... ok
... ok

----------------------------------------------------------------------
Ran 3 tests in <time>

OK
```

- [ ] **Step 2: Run the full CLI smoke suite**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_cli -v`

Expected: all tests PASS.

- [ ] **Step 3: Inspect the generated report for the new section and updated baseline wording**

Run: `rg -n "960 bit / every 6 slots|1440 bit / every 6 slots|1920 bit / every 6 slots|2880 bit / every 6 slots|中心业务负载扫描|中心业务负载趋势分析|默认中心背景业务" outputs/target_edge_packet_size_sensitivity_main_uncapped/sensitivity_report.md`

Expected output contains lines matching:

```text
<line>:### 中心业务负载扫描
<line>:| `960 bit / every 6 slots` | ...
<line>:| `2880 bit / every 6 slots` | ...
<line>:### 中心业务负载趋势分析
<line>:- 默认中心背景业务：`63` 个中心用户，基线口径为 `960 bit / every 6 slots`
```

- [ ] **Step 4: Commit**

```bash
git add configs/target_edge_packet_size_sensitivity_main_uncapped.json scripts/run_target_edge_packet_size_sensitivity_report.py tests/test_cli.py
git commit -m "feat: add 400kb center offered load scan"
```
