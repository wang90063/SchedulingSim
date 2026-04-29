# Center Packet Granularity Scan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a center-packet-granularity scan to the existing `400 KB` packet-size sensitivity report while keeping center offered load approximately constant across granularity variants.

**Architecture:** Extend the existing packet-size report driver instead of creating a new experiment pipeline. Keep the new sweep local to the `400 KB` chapter by adding an explicit paired config list, emitting rows with enough metadata to isolate the new dimension, and rendering a dedicated markdown section without changing the existing PDB and center-user-count sections.

**Tech Stack:** Python 3, dataclasses-based config replacement, existing `UlSimulator`/`ScenarioFactory` flow, `unittest` CLI smoke tests

---

### Task 1: Add the new sweep config and lock in the expected report/test surface

**Files:**
- Modify: `configs/target_edge_packet_size_sensitivity_main_uncapped.json`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

Add assertions to `tests/test_cli.py` inside `test_target_edge_packet_size_sensitivity_report_script_runs` so the test expects:

```python
        self.assertIn(
            "edge_packet_kb,400,center_packet_granularity,160_per_1,tail_append",
            result.stdout,
        )
        self.assertIn(
            "edge_packet_kb,400,center_packet_granularity,960_per_6,business_aware_constrained_insert",
            result.stdout,
        )
        self.assertIn("### 中心业务颗粒度扫描", report_text)
        self.assertIn("`160 bit / every 1 slot`", report_text)
        self.assertIn("`960 bit / every 6 slots`", report_text)
        self.assertIn("平均 offered load 近似保持一致", report_text)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_packet_size_sensitivity_report_script_runs -v`

Expected: FAIL because the script does not yet print any `center_packet_granularity` rows and the markdown report does not yet contain the new section.

- [ ] **Step 3: Update the experiment config with explicit paired granularity entries**

Edit `configs/target_edge_packet_size_sensitivity_main_uncapped.json` and add a paired sweep list under `"sweep"`:

```json
    "center_packet_granularity": [
      { "packet_bits": 160, "period_slots": 1 },
      { "packet_bits": 320, "period_slots": 2 },
      { "packet_bits": 480, "period_slots": 3 },
      { "packet_bits": 800, "period_slots": 5 },
      { "packet_bits": 960, "period_slots": 6 }
    ]
```

Keep the existing `edge_packet_kb`, `edge_pdb_ms`, and `center_user_count` sweeps unchanged.

- [ ] **Step 4: Re-run the focused test to confirm it still fails for the right reason**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_packet_size_sensitivity_report_script_runs -v`

Expected: FAIL again, but now the config file is valid and the remaining failure is still that the script/report do not consume the new sweep.

- [ ] **Step 5: Commit**

```bash
git add configs/target_edge_packet_size_sensitivity_main_uncapped.json tests/test_cli.py
git commit -m "test: define center packet granularity sweep expectations"
```

### Task 2: Extend row generation to support paired center-packet-granularity cases

**Files:**
- Modify: `scripts/run_target_edge_packet_size_sensitivity_report.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test expectations for stdout row shape**

In `tests/test_cli.py`, keep the assertions from Task 1 and make sure the stdout expectations encode the intended scope/value format:

```python
        self.assertIn(
            "edge_packet_kb,400,center_packet_granularity,160_per_1,tail_append",
            result.stdout,
        )
        self.assertIn(
            "edge_packet_kb,400,center_packet_granularity,960_per_6,business_aware_constrained_insert",
            result.stdout,
        )
```

This locks in a single string value format for the new dimension: `<packet_bits>_per_<period_slots>`.

- [ ] **Step 2: Run the focused test to verify the row-shape expectations are still failing**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_packet_size_sensitivity_report_script_runs -v`

Expected: FAIL because `_collect_rows()` only emits `edge_pdb_ms` and `center_user_count`.

- [ ] **Step 3: Implement minimal script support for the new dimension**

In `scripts/run_target_edge_packet_size_sensitivity_report.py`, make these changes:

1. Expand `_case_config()` so it accepts a string `value` for the new dimension and applies both `packet_bits` and `period_slots` to `config.traffic.center`.
2. Add helpers that parse and format the paired value.
3. Extend `_collect_rows()` so it only scans `center_packet_granularity` when `edge_packet_kb == 400`.
4. Emit a string `value` for the new dimension while keeping numeric values for the existing dimensions.

Use code in this shape:

```python
def _granularity_value(packet_bits: int, period_slots: int) -> str:
    return f"{packet_bits}_per_{period_slots}"


def _parse_granularity_value(value: str) -> tuple[int, int]:
    packet_bits_text, period_slots_text = value.split("_per_")
    return int(packet_bits_text), int(period_slots_text)


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
                center=replace(
                    updated.traffic.center,
                    packet_bits=packet_bits,
                    period_slots=period_slots,
                ),
            ),
        )
    raise ValueError(f"unsupported dimension: {dimension}")
```

Extend `_collect_rows()` with a branch like:

```python
        if int(edge_packet_kb) == 400:
            for item in sweep_spec.get("center_packet_granularity", []):
                value = _granularity_value(
                    int(item["packet_bits"]),
                    int(item["period_slots"]),
                )
                for policy in policies:
                    summary = _run_summary(
                        _case_config(
                            config,
                            edge_packet_kb=int(edge_packet_kb),
                            dimension="center_packet_granularity",
                            value=value,
                            policy=policy,
                        )
                    )
                    rows.append(
                        _build_row(
                            edge_packet_kb=int(edge_packet_kb),
                            dimension="center_packet_granularity",
                            value=value,
                            policy=policy,
                            summary=summary,
                        )
                    )
```

Also update the row typing aliases so `value` can be `str`, and update `_write_outputs()` so stdout writes the new string value without coercing it through `int(...)`:

```python
            "value": str(row["value"]),
```

- [ ] **Step 4: Run the focused test to verify the new rows now appear**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_packet_size_sensitivity_report_script_runs -v`

Expected: still FAIL, but now the stdout assertions should pass and the remaining failure should be the missing markdown section/content.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_target_edge_packet_size_sensitivity_report.py tests/test_cli.py
git commit -m "feat: collect center packet granularity rows"
```

### Task 3: Render the new 400 KB-only markdown section

**Files:**
- Modify: `scripts/run_target_edge_packet_size_sensitivity_report.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing report-content expectations**

Keep the report assertions from Task 1 and make them the source of truth for the section title, labels, and explanatory sentence:

```python
        self.assertIn("### 中心业务颗粒度扫描", report_text)
        self.assertIn("`160 bit / every 1 slot`", report_text)
        self.assertIn("`960 bit / every 6 slots`", report_text)
        self.assertIn("平均 offered load 近似保持一致", report_text)
```

- [ ] **Step 2: Run the focused test to confirm the report section is still missing**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_packet_size_sensitivity_report_script_runs -v`

Expected: FAIL because `_build_packet_size_section()` only renders the PDB and center-user-count sections.

- [ ] **Step 3: Implement the report section with a dedicated label path**

In `scripts/run_target_edge_packet_size_sensitivity_report.py`:

1. Update `_rows_for()` to continue working with the new string-valued dimension.
2. Extend `_value_label()`:

```python
def _value_label(dimension: str, value: int | str) -> str:
    if dimension == "edge_pdb_ms":
        return f"{int(value)} ms"
    if dimension == "center_user_count":
        return f"{int(value)} center users"
    if dimension == "center_packet_granularity":
        packet_bits, period_slots = _parse_granularity_value(str(value))
        slot_label = "slot" if period_slots == 1 else "slots"
        return f"{packet_bits} bit / every {period_slots} {slot_label}"
    raise ValueError(f"unsupported dimension: {dimension}")
```

3. Update `_build_table()` so value ordering supports the new string dimension:

```python
    if dimension == "center_packet_granularity":
        values = sorted(
            {str(row["value"]) for row in rows},
            key=lambda item: _parse_granularity_value(item)[0],
        )
    else:
        values = sorted({int(row["value"]) for row in rows})
```

4. In `_build_packet_size_section()`, add a 400 KB-only subsection:

```python
    granularity_rows = _rows_for(
        rows,
        edge_packet_kb=edge_packet_kb,
        dimension="center_packet_granularity",
    )
```

and render it only for `edge_packet_kb == 400`:

```python
    granularity_section: list[str] = []
    if edge_packet_kb == 400 and granularity_rows:
        granularity_section = [
            "### 中心业务颗粒度扫描",
            "- 固定 `edge_pdb_ms = 500`",
            "- 固定 `center_user_count = 63`",
            "- 这些档位让中心平均 offered load 近似保持一致，只改变包颗粒度。",
            "",
            *_build_table(granularity_rows, dimension="center_packet_granularity"),
            "",
            "### 中心业务颗粒度趋势分析",
            "- 重点解释中心包越整块时，候选窗口轮转效应是否减弱。",
            "- 重点解释边缘大包进入候选窗口后，是否仍会因为权重较低而拿不到足够资源。",
            "",
        ]
```

Insert `*granularity_section` between the existing center-user-count section and `### 小结`.

- [ ] **Step 4: Run the focused test to verify the packet-size report passes**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_packet_size_sensitivity_report_script_runs -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/run_target_edge_packet_size_sensitivity_report.py tests/test_cli.py
git commit -m "feat: add center packet granularity report section"
```

### Task 4: Run the broader regression set for the packet-size/reporting path

**Files:**
- Modify: `tests/test_cli.py` (only if regressions reveal expectation drift)
- Verify: `scripts/run_target_edge_packet_size_sensitivity_report.py`
- Verify: `configs/target_edge_packet_size_sensitivity_main_uncapped.json`

- [ ] **Step 1: Run the packet-size report smoke test**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_packet_size_sensitivity_report_script_runs -v`

Expected: PASS

- [ ] **Step 2: Run adjacent target-edge report tests**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_sensitivity_main_400k_report_includes_breakdown_differences tests.test_cli.CliSmokeTests.test_target_edge_sensitivity_main_config_report_uses_configured_prb_budget -v`

Expected: PASS, confirming the new packet-size reporting change did not break the existing target-edge report scripts.

- [ ] **Step 3: Run the full CLI smoke suite**

Run: `PYTHONPATH=src python -m unittest tests.test_cli -v`

Expected: PASS

- [ ] **Step 4: Inspect the generated 400 KB section manually**

Run: `rg -n "中心业务颗粒度扫描|160 bit / every 1 slot|960 bit / every 6 slots|平均 offered load 近似保持一致" outputs/target_edge_packet_size_sensitivity_main_uncapped/sensitivity_report.md`

Expected:

```text
<line>:### 中心业务颗粒度扫描
<line>:| `160 bit / every 1 slot` | ...
<line>:| `960 bit / every 6 slots` | ...
<line>:- 这些档位让中心平均 offered load 近似保持一致，只改变包颗粒度。
```

- [ ] **Step 5: Commit**

```bash
git add configs/target_edge_packet_size_sensitivity_main_uncapped.json scripts/run_target_edge_packet_size_sensitivity_report.py tests/test_cli.py
git commit -m "feat: add center packet granularity scan to 400kb report"
```
