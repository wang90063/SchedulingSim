# Rho-First Load-Ratio Mapping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current business-first load-ratio construction with a rho-first scene generator that scans target `rho` points first, maps them into valid business parameters through a bounded candidate-domain solver, and reports both target and actual ratio coordinates throughout the systematic-analysis pipeline.

**Architecture:** Keep the existing systematic-analysis runner, realization-bank flow, and paired-policy aggregation pipeline. Replace only the load-ratio case-construction layer and the metadata schema that feeds manifests, CSV rows, reports, and plots. The implementation should treat target `rho` as the scan definition and business parameters as a derived realization selected by a deterministic solver.

**Tech Stack:** Python, `unittest`, existing `systematic_analysis` helpers, CLI runner scripts, JSON config, CSV/Markdown outputs, `matplotlib`.

---

## Proposed File Structure

- Modify: `src/scheduling_sim/systematic_analysis.py`
  - Replace the current load-ratio case builder with target-ratio scene definitions, mapping-policy dataclasses, candidate-domain solving helpers, and target/actual ratio metadata propagation.
- Modify: `scripts/run_systematic_simulation_analysis.py`
  - Parse the new rho-first config shape, emit the expanded manifest metadata, and update load-ratio report wording to surface target/actual coordinates and mapping policy choices.
- Modify: `scripts/render_systematic_simulation_analysis_plots.py`
  - Continue rendering ratio-space plots, but prefer target-ratio coordinates for layout and keep actual-ratio metadata available in tooltips/tables/labels where already represented by CSV rows.
- Create: `configs/systematic_simulation_analysis_load_ratio_rho_first.json`
  - Checked-in config for the `4 × 3 × 5 = 60` rho-first first pass.
- Modify: `tests/test_systematic_analysis.py`
  - Cover solver selection, validity filtering, ratio rounding, and target/actual metadata propagation.
- Modify: `tests/test_cli.py`
  - Cover the new config shape, updated manifest/report content, and row metadata.
- Modify: `tests/test_systematic_analysis_plots.py`
  - Cover the updated manifest shape and verify rendering still works on rho-first output.

## Task 1: Replace Load-Ratio Case Construction With Target-Ratio Case Solving

**Files:**
- Modify: `src/scheduling_sim/systematic_analysis.py`
- Test: `tests/test_systematic_analysis.py`

- [ ] **Step 1: Write failing tests for rho-first candidate solving**

```python
    def test_rho_first_load_ratio_cases_solve_background_and_pdb_parameters(self) -> None:
        cases = load_ratio_cases(
            rho_bg_values=[0.388],
            rho_pdb_values=[0.183],
            pdb_ms_values=[20, 100],
            background_capacity_mbps=66.03,
            pdb_capacity_mbps=8.74,
            mapping_policy=LoadRatioMappingPolicy(
                background=BackgroundMappingPolicy(
                    background_user_count_values=[32, 40, 48],
                    background_packet_kb_values=[1.0, 1.5, 2.0],
                    background_period_ms_range=(4.0, 30.0),
                    anchor_background_user_count=40,
                    anchor_background_packet_kb=2.0,
                ),
                pdb=PdbMappingPolicy(
                    pdb_user_count_values=[4, 8],
                    pdb_packet_kb_range=(0.5, 80.0),
                    anchor_pdb_user_count=4,
                ),
            ),
        )

        self.assertEqual(len(cases), 2)
        self.assertEqual(cases[0].target_rho_bg, 0.388)
        self.assertEqual(cases[0].target_rho_pdb, 0.183)
        self.assertEqual(cases[0].pdb_ms, 20)
        self.assertIn(cases[0].background_user_count, {32, 40, 48})
        self.assertIn(cases[0].background_packet_kb, {1.0, 1.5, 2.0})
        self.assertGreaterEqual(cases[0].background_period_ms, 4.0)
        self.assertLessEqual(cases[0].background_period_ms, 30.0)
        self.assertAlmostEqual(cases[0].actual_rho_bg, 0.388, places=3)
        self.assertAlmostEqual(cases[0].actual_rho_pdb, 0.183, places=3)

    def test_rho_first_solver_prefers_anchor_values_on_error_tie(self) -> None:
        selected = solve_background_mapping(
            target_rho_bg=0.582,
            background_capacity_mbps=66.03,
            policy=BackgroundMappingPolicy(
                background_user_count_values=[32, 40],
                background_packet_kb_values=[1.5, 2.0],
                background_period_ms_range=(4.0, 30.0),
                anchor_background_user_count=40,
                anchor_background_packet_kb=2.0,
            ),
        )

        self.assertEqual(selected.background_user_count, 40)
        self.assertEqual(selected.background_packet_kb, 2.0)
```

- [ ] **Step 2: Run the targeted tests to confirm failure**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis.SystematicAnalysisTests.test_rho_first_load_ratio_cases_solve_background_and_pdb_parameters tests.test_systematic_analysis.SystematicAnalysisTests.test_rho_first_solver_prefers_anchor_values_on_error_tie -v`

Expected: FAIL because `load_ratio_cases(...)` still expects business-first inputs and there are no mapping-policy dataclasses or solver helpers.

- [ ] **Step 3: Add rho-first case dataclasses and solving helpers**

```python
@dataclass(frozen=True)
class BackgroundMappingPolicy:
    background_user_count_values: list[int]
    background_packet_kb_values: list[float]
    background_period_ms_range: tuple[float, float]
    anchor_background_user_count: int
    anchor_background_packet_kb: float


@dataclass(frozen=True)
class PdbMappingPolicy:
    pdb_user_count_values: list[int]
    pdb_packet_kb_range: tuple[float, float]
    anchor_pdb_user_count: int


@dataclass(frozen=True)
class LoadRatioMappingPolicy:
    background: BackgroundMappingPolicy
    pdb: PdbMappingPolicy


@dataclass(frozen=True)
class LoadRatioCase:
    case_label: str
    target_rho_bg: float
    target_rho_pdb: float
    actual_rho_bg: float
    actual_rho_pdb: float
    prb_share_pdb: float
    background_mapping_policy: str
    pdb_mapping_policy: str
    background_user_count: int
    background_packet_kb: float
    background_period_ms: float
    pdb_user_count: int
    pdb_packet_kb: float
    pdb_ms: int
```

```python
def solve_background_mapping(...): ...
def solve_pdb_mapping(...): ...
def load_ratio_cases(
    *,
    rho_bg_values: list[float],
    rho_pdb_values: list[float],
    pdb_ms_values: list[int],
    background_capacity_mbps: float,
    pdb_capacity_mbps: float,
    mapping_policy: LoadRatioMappingPolicy,
) -> list[LoadRatioCase]:
    ...
```

- [ ] **Step 4: Re-run the targeted tests and verify they pass**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis.SystematicAnalysisTests.test_rho_first_load_ratio_cases_solve_background_and_pdb_parameters tests.test_systematic_analysis.SystematicAnalysisTests.test_rho_first_solver_prefers_anchor_values_on_error_tie -v`

Expected: PASS

- [ ] **Step 5: Commit the rho-first solver foundation**

```bash
git add src/scheduling_sim/systematic_analysis.py tests/test_systematic_analysis.py
git commit -m "Add rho-first load-ratio case solver"
```

## Task 2: Propagate Target And Actual Ratio Metadata Through Rows

**Files:**
- Modify: `src/scheduling_sim/systematic_analysis.py`
- Test: `tests/test_systematic_analysis.py`

- [ ] **Step 1: Write failing metadata tests**

```python
    def test_per_run_metric_row_includes_target_and_actual_ratio_metadata(self) -> None:
        row = per_run_metric_row(
            scenario_id="rho-first-case",
            seed=7,
            policy="tail_append",
            case=LoadRatioCase(
                case_label="L01",
                target_rho_bg=0.388,
                target_rho_pdb=0.183,
                actual_rho_bg=0.390,
                actual_rho_pdb=0.182,
                prb_share_pdb=0.318,
                background_mapping_policy="candidate_domain_solve_period",
                pdb_mapping_policy="candidate_domain_solve_packet",
                background_user_count=40,
                background_packet_kb=2.0,
                background_period_ms=25.0,
                pdb_user_count=4,
                pdb_packet_kb=5.0,
                pdb_ms=100,
            ),
            summary={...},
        )

        self.assertEqual(row["target_rho_bg"], 0.388)
        self.assertEqual(row["target_rho_pdb"], 0.183)
        self.assertEqual(row["actual_rho_bg"], 0.390)
        self.assertEqual(row["actual_rho_pdb"], 0.182)
        self.assertEqual(row["background_mapping_policy"], "candidate_domain_solve_period")
        self.assertEqual(row["pdb_mapping_policy"], "candidate_domain_solve_packet")
```

- [ ] **Step 2: Run the targeted test and confirm failure**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis.SystematicAnalysisTests.test_per_run_metric_row_includes_target_and_actual_ratio_metadata -v`

Expected: FAIL because the current row schema still uses only one ratio pair.

- [ ] **Step 3: Update `_case_metadata(...)`, `_row_metadata(...)`, and aggregate helpers**

```python
{
    "target_rho_bg": float(case.target_rho_bg),
    "target_rho_pdb": float(case.target_rho_pdb),
    "actual_rho_bg": float(case.actual_rho_bg),
    "actual_rho_pdb": float(case.actual_rho_pdb),
    "background_mapping_policy": case.background_mapping_policy,
    "pdb_mapping_policy": case.pdb_mapping_policy,
}
```

- [ ] **Step 4: Re-run the targeted test and verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis.SystematicAnalysisTests.test_per_run_metric_row_includes_target_and_actual_ratio_metadata -v`

Expected: PASS

- [ ] **Step 5: Commit the row-metadata update**

```bash
git add src/scheduling_sim/systematic_analysis.py tests/test_systematic_analysis.py
git commit -m "Propagate rho-first target and actual ratio metadata"
```

## Task 3: Replace The Config Shape And Runner Parsing

**Files:**
- Modify: `scripts/run_systematic_simulation_analysis.py`
- Create: `configs/systematic_simulation_analysis_load_ratio_rho_first.json`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write a failing CLI smoke test for the rho-first config**

```python
    def test_systematic_simulation_analysis_runner_supports_rho_first_load_ratio_config(self) -> None:
        ...
        payload["systematic_analysis"] = {
            "mode": "load_ratio",
            "rho_bg_values": [0.388],
            "rho_pdb_values": [0.183],
            "pdb_ms_values": [20, 100],
            "capacity_reference": {
                "background_capacity_mbps": 66.03,
                "pdb_capacity_mbps": 8.74,
            },
            "mapping_policy": {
                "background": {
                    "kind": "candidate_domain_solve_period",
                    "background_user_count_values": [32, 40, 48],
                    "background_packet_kb_values": [1.0, 1.5, 2.0],
                    "background_period_ms_range": [4.0, 30.0],
                    "anchor_background_user_count": 40,
                    "anchor_background_packet_kb": 2.0,
                },
                "pdb": {
                    "kind": "candidate_domain_solve_packet",
                    "pdb_user_count_values": [4, 8],
                    "pdb_packet_kb_range": [0.5, 80.0],
                    "anchor_pdb_user_count": 4,
                },
            },
            ...
        }
        ...
        self.assertEqual(manifest["rho_bg_values"], [0.388])
        self.assertEqual(manifest["rho_pdb_values"], [0.183])
        self.assertEqual(manifest["pdb_ms_values"], [20, 100])
```

- [ ] **Step 2: Run the CLI smoke test and confirm failure**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_supports_rho_first_load_ratio_config -v`

Expected: FAIL because the runner still expects `background_user_count` / `background_packet_kb_values` / `pdb_shapes`.

- [ ] **Step 3: Update runner parsing and add checked-in config**

```python
if scan_mode == "load_ratio":
    mapping_policy = LoadRatioMappingPolicy(...)
    all_cases = load_ratio_cases(
        rho_bg_values=[float(value) for value in sweep["rho_bg_values"]],
        rho_pdb_values=[float(value) for value in sweep["rho_pdb_values"]],
        pdb_ms_values=[int(value) for value in sweep["pdb_ms_values"]],
        background_capacity_mbps=float(...),
        pdb_capacity_mbps=float(...),
        mapping_policy=mapping_policy,
    )
```

- [ ] **Step 4: Re-run the CLI smoke test and verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_supports_rho_first_load_ratio_config -v`

Expected: PASS

- [ ] **Step 5: Commit the runner/config update**

```bash
git add scripts/run_systematic_simulation_analysis.py configs/systematic_simulation_analysis_load_ratio_rho_first.json tests/test_cli.py
git commit -m "Support rho-first load-ratio config"
```

## Task 4: Update Load-Ratio Reporting To Surface Mapping Results

**Files:**
- Modify: `scripts/run_systematic_simulation_analysis.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write a failing summary-report test for rho-first outputs**

```python
    def test_systematic_simulation_analysis_runner_writes_rho_first_summary_report(self) -> None:
        ...
        self.assertIn("| case_label | target_rho_bg | target_rho_pdb | actual_rho_bg | actual_rho_pdb |", report_text)
        self.assertIn("candidate-domain solver", report_text)
        self.assertIn("background_mapping_policy", report_text)
```

- [ ] **Step 2: Run the report smoke test and confirm failure**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_writes_rho_first_summary_report -v`

Expected: FAIL because the current load-ratio report branch does not expose target/actual split or mapping policy details.

- [ ] **Step 3: Update `_load_ratio_summary_report(...)`**

```python
| case_label | target_rho_bg | target_rho_pdb | actual_rho_bg | actual_rho_pdb | prb_share_pdb | background_user_count | background_packet_kb | background_period_ms | pdb_user_count | pdb_ms | pdb_packet_kb |
```

- [ ] **Step 4: Re-run the report smoke test and verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_writes_rho_first_summary_report -v`

Expected: PASS

- [ ] **Step 5: Commit the report update**

```bash
git add scripts/run_systematic_simulation_analysis.py tests/test_cli.py
git commit -m "Report rho-first load-ratio mapping results"
```

## Task 5: Update Ratio Plot Rendering For The New Manifest And Row Schema

**Files:**
- Modify: `scripts/render_systematic_simulation_analysis_plots.py`
- Modify: `tests/test_systematic_analysis_plots.py`

- [ ] **Step 1: Write failing plot tests for rho-first manifest fields**

```python
    def test_renderer_uses_target_ratio_axes_for_rho_first_outputs(self) -> None:
        ...
        self.assertEqual(labels["x_label"], "target_rho_bg")
        self.assertEqual(labels["y_label"], "target_rho_pdb")
```

- [ ] **Step 2: Run the plot tests and confirm failure**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis_plots.SystematicAnalysisPlotTests.test_renderer_uses_target_ratio_axes_for_rho_first_outputs -v`

Expected: FAIL because the current load-ratio plot branch still assumes `rho_bg / rho_pdb`.

- [ ] **Step 3: Update renderer helpers to prefer target-ratio coordinates**

```python
if manifest.get("scan_mode") == "load_ratio":
    x_field = "target_rho_bg" if "target_rho_bg" in rows[0] else "rho_bg"
    y_field = "target_rho_pdb" if "target_rho_pdb" in rows[0] else "rho_pdb"
```

- [ ] **Step 4: Re-run the targeted plot tests and verify they pass**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis_plots.SystematicAnalysisPlotTests.test_renderer_uses_target_ratio_axes_for_rho_first_outputs -v`

Expected: PASS

- [ ] **Step 5: Commit the plot update**

```bash
git add scripts/render_systematic_simulation_analysis_plots.py tests/test_systematic_analysis_plots.py
git commit -m "Render rho-first load-ratio plots"
```

## Task 6: Run Focused Regression Verification

**Files:**
- Test: `tests/test_systematic_analysis.py`
- Test: `tests/test_systematic_analysis_plots.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Run the focused verification commands**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis -v`

Expected: PASS

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis_plots -v`

Expected: PASS

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_supports_rho_first_load_ratio_config tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_writes_rho_first_summary_report tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_renderer_runs_on_runner_output -v`

Expected: PASS

- [ ] **Step 2: Commit the verification-only updates if any tests needed fixture adjustments**

```bash
git add tests/test_systematic_analysis.py tests/test_systematic_analysis_plots.py tests/test_cli.py
git commit -m "Verify rho-first load-ratio coverage"
```

- [ ] **Step 3: Stop and hand off for branch-integration choice**

At this point, implementation is complete and verified. Use the finishing workflow next instead of continuing ad hoc.
