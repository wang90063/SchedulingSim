# Systematic Analysis Expanded Merge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reuse the finished `option 1` systematic-analysis rows, run only the newly added expanded scene points, then merge and regenerate one combined canonical output directory with correct tables, report, and plots.

**Architecture:** Extend the existing systematic-analysis runner instead of adding a second analysis stack. The runner will gain scene-key filtering, reuse-aware incremental execution, and raw-row merge support; the aggregation path stays single-source by regenerating all summaries from merged `per_run_rows` and `paired_rows`. The renderer will be updated so filtered scene matrices render missing points as missing rather than incorrectly painting them as zero-valued cells.

**Tech Stack:** Python, unittest, CSV/JSON file I/O, existing simulator pipeline, matplotlib

---

### Task 1: Add filtered-scene enumeration helpers and merge-ready row utilities

**Files:**
- Modify: `src/scheduling_sim/systematic_analysis.py`
- Test: `tests/test_systematic_analysis.py`

- [ ] **Step 1: Write the failing tests for filtered enumeration and row merge helpers**

```python
    def test_systematic_cases_supports_scene_filters(self) -> None:
        cases = systematic_cases(
            background_user_counts=[16, 24],
            pdb_user_counts=[4, 16],
            pdb_ms_values=[100],
            pdb_packet_kb_values=[20],
            include_case=lambda case: (case.background_user_count + case.pdb_user_count) >= 32,
        )
        self.assertEqual(
            [
                (case.background_user_count, case.pdb_user_count, case.pdb_ms, case.pdb_packet_kb)
                for case in cases
            ],
            [(16, 16, 100, 20), (24, 16, 100, 20)],
        )

    def test_scene_key_helpers_deduplicate_scene_rows(self) -> None:
        rows = [
            {"background_user_count": 24, "pdb_user_count": 4, "pdb_ms": 100, "pdb_packet_kb": 50, "seed": 7},
            {"background_user_count": 24, "pdb_user_count": 4, "pdb_ms": 100, "pdb_packet_kb": 50, "seed": 8},
            {"background_user_count": 32, "pdb_user_count": 8, "pdb_ms": 200, "pdb_packet_kb": 70, "seed": 7},
        ]
        self.assertEqual(
            scene_key_set(rows),
            {
                (24, 4, 100, 50),
                (32, 8, 200, 70),
            },
        )

    def test_merge_row_sets_appends_without_losing_existing_rows(self) -> None:
        merged = merge_row_sets(
            existing_rows=[{"seed": 7, "background_user_count": 24, "pdb_user_count": 4, "pdb_ms": 100, "pdb_packet_kb": 50}],
            new_rows=[{"seed": 8, "background_user_count": 32, "pdb_user_count": 8, "pdb_ms": 200, "pdb_packet_kb": 70}],
        )
        self.assertEqual(len(merged), 2)
        self.assertEqual(
            [row["background_user_count"] for row in merged],
            [24, 32],
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis.SystematicAnalysisTests.test_systematic_cases_supports_scene_filters tests.test_systematic_analysis.SystematicAnalysisTests.test_scene_key_helpers_deduplicate_scene_rows tests.test_systematic_analysis.SystematicAnalysisTests.test_merge_row_sets_appends_without_losing_existing_rows -v`

Expected: FAIL with missing `include_case`, `scene_key_set`, or `merge_row_sets` support.

- [ ] **Step 3: Write minimal implementation for filtered enumeration and row helpers**

```python
from collections.abc import Callable


SceneFilter = Callable[[SystematicCase], bool]


def systematic_cases(
    *,
    background_user_counts: list[int],
    pdb_user_counts: list[int],
    pdb_ms_values: list[int],
    pdb_packet_kb_values: list[int],
    include_case: SceneFilter | None = None,
) -> list[SystematicCase]:
    cases = [
        SystematicCase(
            background_user_count=background_user_count,
            pdb_user_count=pdb_user_count,
            pdb_ms=pdb_ms,
            pdb_packet_kb=pdb_packet_kb,
        )
        for background_user_count in background_user_counts
        for pdb_user_count in pdb_user_counts
        for pdb_ms in pdb_ms_values
        for pdb_packet_kb in pdb_packet_kb_values
    ]
    if include_case is None:
        return cases
    return [case for case in cases if include_case(case)]


def scene_key(row: dict[str, float | int | str]) -> tuple[int, int, int, int]:
    return (
        int(row["background_user_count"]),
        int(row["pdb_user_count"]),
        int(row["pdb_ms"]),
        int(row["pdb_packet_kb"]),
    )


def scene_key_set(rows: list[dict[str, float | int | str]]) -> set[tuple[int, int, int, int]]:
    return {scene_key(row) for row in rows}


def merge_row_sets(
    *,
    existing_rows: list[dict[str, float | int | str]],
    new_rows: list[dict[str, float | int | str]],
) -> list[dict[str, float | int | str]]:
    return [*existing_rows, *new_rows]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis.SystematicAnalysisTests.test_systematic_cases_supports_scene_filters tests.test_systematic_analysis.SystematicAnalysisTests.test_scene_key_helpers_deduplicate_scene_rows tests.test_systematic_analysis.SystematicAnalysisTests.test_merge_row_sets_appends_without_losing_existing_rows -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/scheduling_sim/systematic_analysis.py tests/test_systematic_analysis.py
git commit -m "Add systematic-analysis scene filtering helpers"
```

### Task 2: Add reuse-aware incremental execution and merged-output regeneration

**Files:**
- Modify: `scripts/run_systematic_simulation_analysis.py`
- Modify: `src/scheduling_sim/systematic_analysis.py`
- Modify: `tests/test_cli.py`
- Test: `tests/test_systematic_analysis.py`

- [ ] **Step 1: Write the failing tests for reuse-aware runner behavior**

```python
    def test_systematic_simulation_analysis_runner_reuses_existing_scene_keys_and_merges_outputs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            reused_dir = Path(tmp) / "reused"
            reused_dir.mkdir(parents=True, exist_ok=True)
            (reused_dir / "per_run_rows.csv").write_text(
                "seed,scenario_id,policy,background_user_count,pdb_user_count,pdb_ms,pdb_packet_kb,edge_pdb_satisfaction_rate,center_agg_rate_bps,center_avg_rate_bps,prb_utilization,center_prb_share,edge_prb_share,pdb_arrivals_in_window,pdb_violation_rate,target_edge_completion_delay_ms,target_edge_queue_wait_ms,target_edge_service_time_ms,edge_backlog_bits\\n"
                "7,bg24_pdb4_d100_k50_seed00,tail_append,24,4,100,50,0.0,1000.0,50.0,1.0,0.4,0.6,8.0,1.0,100.0,70.0,30.0,0.0\\n"
                "7,bg24_pdb4_d100_k50_seed00,hopeless_front_insert,24,4,100,50,0.1,900.0,45.0,1.0,0.35,0.65,8.0,0.9,90.0,60.0,30.0,0.0\\n",
                encoding="utf-8",
            )
            (reused_dir / "paired_rows.csv").write_text(
                "seed,background_user_count,pdb_user_count,pdb_ms,pdb_packet_kb,baseline_edge_pdb_satisfaction_rate,proposed_edge_pdb_satisfaction_rate,delta_pdb_satisfaction_rate,center_throughput_retention,delta_prb_utilization,delta_center_prb_share,delta_edge_prb_share\\n"
                "7,24,4,100,50,0.0,0.1,0.1,0.9,0.0,-0.05,0.05\\n",
                encoding="utf-8",
            )
            config_path = Path(tmp) / "expanded.json"
            incremental_output_dir = Path(tmp) / "incremental"
            merged_output_dir = Path(tmp) / "merged"
            payload = json.loads((repo_root / "configs" / "systematic_simulation_analysis_option1.json").read_text(encoding="utf-8"))
            payload["report"]["output_dir"] = str(incremental_output_dir)
            payload["systematic_analysis"]["background_user_count_values"] = [24, 32]
            payload["systematic_analysis"]["pdb_user_count_values"] = [4, 8]
            payload["systematic_analysis"]["pdb_ms_values"] = [100]
            payload["systematic_analysis"]["pdb_packet_kb_values"] = [50]
            payload["systematic_analysis"]["repeat_count"] = 1
            payload["systematic_analysis"]["minimum_total_users"] = 32
            payload["systematic_analysis"]["reuse_output_dirs"] = [str(reused_dir)]
            payload["systematic_analysis"]["merged_output_dir"] = str(merged_output_dir)
            config_path.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                ["python", "scripts/run_systematic_simulation_analysis.py", str(config_path)],
                cwd=repo_root,
                env={**os.environ, "PYTHONPATH": "src"},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            merged_scene_rows = list(csv.DictReader((merged_output_dir / "scene_summary.csv").open(encoding="utf-8")))
            self.assertEqual(len(merged_scene_rows), 2)
            merged_manifest = json.loads((merged_output_dir / "experiment_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(merged_manifest["reused_scene_point_count"], 1)
            self.assertEqual(merged_manifest["new_scene_point_count"], 1)
            self.assertEqual(merged_manifest["final_scene_point_count"], 2)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_reuses_existing_scene_keys_and_merges_outputs -v`

Expected: FAIL because the runner does not yet support `minimum_total_users`, `reuse_output_dirs`, or `merged_output_dir`.

- [ ] **Step 3: Write minimal implementation for incremental execution and merged regeneration**

```python
def _load_csv_rows(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _include_case_from_sweep(sweep: dict[str, object]):
    minimum_total_users = int(sweep.get("minimum_total_users", 0) or 0)
    if minimum_total_users <= 0:
        return None
    return lambda case: (case.background_user_count + case.pdb_user_count) >= minimum_total_users


def _reuse_scene_key_set(reuse_output_dirs: list[str]) -> set[tuple[int, int, int, int]]:
    reused: set[tuple[int, int, int, int]] = set()
    for directory in reuse_output_dirs:
        reused |= scene_key_set(_load_csv_rows(Path(directory) / "paired_rows.csv"))
    return reused


all_cases = systematic_cases(
    background_user_counts=list(sweep["background_user_count_values"]),
    pdb_user_counts=list(sweep["pdb_user_count_values"]),
    pdb_ms_values=list(sweep["pdb_ms_values"]),
    pdb_packet_kb_values=list(sweep["pdb_packet_kb_values"]),
    include_case=_include_case_from_sweep(sweep),
)
reused_keys = _reuse_scene_key_set([str(value) for value in sweep.get("reuse_output_dirs", [])])
new_cases = [case for case in all_cases if (case.background_user_count, case.pdb_user_count, case.pdb_ms, case.pdb_packet_kb) not in reused_keys]

# simulate only new_cases into output_dir

existing_per_run_rows = []
existing_paired_rows = []
for reuse_dir in [str(value) for value in sweep.get("reuse_output_dirs", [])]:
    existing_per_run_rows.extend(_load_csv_rows(Path(reuse_dir) / "per_run_rows.csv"))
    existing_paired_rows.extend(_load_csv_rows(Path(reuse_dir) / "paired_rows.csv"))

merged_per_run_rows = merge_row_sets(existing_rows=existing_per_run_rows, new_rows=per_run_rows)
merged_paired_rows = merge_row_sets(existing_rows=existing_paired_rows, new_rows=paired_rows)

final_output_dir = Path(str(sweep.get("merged_output_dir", output_dir)))
scene_rows = aggregate_scene_rows(merged_paired_rows)
region_rows = summarize_regions(scene_rows)
capacity_rows_95 = capacity_summary_rows(scene_rows, threshold=0.95)
capacity_rows_90 = capacity_summary_rows(scene_rows, threshold=0.90)
typical_case_rows = select_typical_case_rows(scene_rows)
typical_case_detail_rows = build_typical_case_detail_rows(
    scene_rows=scene_rows,
    per_run_rows=merged_per_run_rows,
    baseline_policy=baseline_policy,
    proposed_policy=ours_policy,
)
boundary_rows_95 = build_boundary_feasibility_rows(scene_rows, threshold=0.95)
boundary_rows_90 = build_boundary_feasibility_rows(scene_rows, threshold=0.90)
manifest = {
    **sweep,
    "reference_config": str(config_path),
    "scene_bank_counts": {...},
    "reuse_output_dirs": [str(value) for value in sweep.get("reuse_output_dirs", [])],
    "reused_scene_point_count": len(reused_keys),
    "new_scene_point_count": len(new_cases),
    "final_scene_point_count": len(scene_rows),
}
```

- [ ] **Step 4: Run targeted tests to verify runner behavior passes**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_reuses_existing_scene_keys_and_merges_outputs tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_supports_hopeless_front_insert_ours_policy tests.test_systematic_analysis -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/scheduling_sim/systematic_analysis.py scripts/run_systematic_simulation_analysis.py tests/test_systematic_analysis.py tests/test_cli.py
git commit -m "Add reuse-aware systematic-analysis execution"
```

### Task 3: Make renderer treat filtered-out scene points as missing instead of zero

**Files:**
- Modify: `scripts/render_systematic_simulation_analysis_plots.py`
- Modify: `tests/test_systematic_analysis_plots.py`

- [ ] **Step 1: Write the failing renderer test for sparse scene grids**

```python
    def test_grid_value_returns_nan_for_missing_scene_points(self) -> None:
        module = _load_render_module()
        rows = [
            {
                "background_user_count": "24",
                "pdb_user_count": "4",
                "pdb_ms": "100",
                "pdb_packet_kb": "50",
                "mean_delta_pdb_satisfaction_rate": "0.2",
            }
        ]
        value = module._scene_value(
            rows,
            pdb_ms=100,
            pdb_packet_kb=50,
            background_user_count=36,
            pdb_user_count=8,
            field_name="mean_delta_pdb_satisfaction_rate",
        )
        self.assertTrue(math.isnan(value))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis_plots.SystematicAnalysisPlotTests.test_grid_value_returns_nan_for_missing_scene_points -v`

Expected: FAIL because `_scene_value` currently returns `0.0`.

- [ ] **Step 3: Write minimal implementation for missing-cell rendering**

```python
import math


def _scene_value(...):
    for row in rows:
        ...
            return float(row[field_name])
    return math.nan


def _grid_value(...):
    for row in rows:
        ...
            return float(row[field_name])
    return math.nan


image = ax.imshow(matrix, aspect="auto", origin="lower", vmin=vmin, vmax=vmax)
image.cmap.set_bad(color="#d9d9d9")
```

- [ ] **Step 4: Run renderer tests**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis_plots tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_renderer_runs_on_runner_output -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/render_systematic_simulation_analysis_plots.py tests/test_systematic_analysis_plots.py tests/test_cli.py
git commit -m "Render sparse systematic-analysis grids correctly"
```

### Task 4: Add expanded config and run the incremental expanded sweep

**Files:**
- Create: `configs/systematic_simulation_analysis_option1_expanded.json`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing config-smoke test**

```python
    def test_expanded_systematic_analysis_config_declares_reuse_and_total_user_filter(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        payload = json.loads(
            (repo_root / "configs" / "systematic_simulation_analysis_option1_expanded.json").read_text(encoding="utf-8")
        )
        sweep = payload["systematic_analysis"]
        self.assertEqual(sweep["background_user_count_values"], [16, 24, 32, 36, 40, 48])
        self.assertEqual(sweep["pdb_user_count_values"], [4, 8, 10, 12, 16])
        self.assertEqual(sweep["pdb_ms_values"], [100, 200, 300, 500, 600])
        self.assertEqual(sweep["pdb_packet_kb_values"], [20, 30, 40, 50, 70, 100, 150, 300])
        self.assertEqual(sweep["repeat_count"], 10)
        self.assertEqual(sweep["minimum_total_users"], 32)
        self.assertEqual(sweep["reuse_output_dirs"], ["outputs/systematic_simulation_analysis_option1"])
        self.assertEqual(sweep["merged_output_dir"], "outputs/systematic_simulation_analysis_option1_expanded")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_expanded_systematic_analysis_config_declares_reuse_and_total_user_filter -v`

Expected: FAIL because the config file does not exist yet.

- [ ] **Step 3: Add the expanded config**

```json
{
  "simulation": {
    "cycles": 2400,
    "slot_duration_ms": 1,
    "tdd_pattern": "DSUUU",
    "random_seed": 7,
    "analysis_window_ms": 10000
  },
  "resources": {
    "total_prb_per_u_slot": 273,
    "max_ue_per_slot": 16
  },
  "traffic": {
    "center": {
      "count": 48,
      "period_slots": 10,
      "packet_bits": 16000,
      "pdb_ms": null,
      "gbr_bps": 0.0
    },
    "edge": {
      "count": 16,
      "packet_bits": 400000,
      "pdb_ms": 100,
      "arrival_mode": "periodic_by_pdb",
      "initial_phase_mode": "uniform_0_to_pdb"
    }
  },
  "radio": {
    "environment": {
      "scenario_type": "uma",
      "cell_radius_m": 500.0,
      "carrier_frequency_ghz": 3.5,
      "per_prb_tx_power_dbm": 5.0,
      "noise_figure_db": 7.0,
      "interference_margin_db": 3.0,
      "shadow_std_db": 4.0,
      "slow_fading_alpha": 0.95,
      "slot_jitter_std_db": 0.5,
      "mcs_table": [
        {"sinr_db": -5.0, "mcs_index": 0, "bits_per_prb": 24},
        {"sinr_db": 0.0, "mcs_index": 1, "bits_per_prb": 48},
        {"sinr_db": 10.0, "mcs_index": 2, "bits_per_prb": 96}
      ]
    },
    "center": {
      "base_snr_db": 12.0,
      "snr_min_db": 0.0,
      "snr_max_db": 20.0
    },
    "edge": {
      "base_snr_db": -2.0,
      "snr_min_db": -8.0,
      "snr_max_db": 4.0,
      "edge_per_u_slot_prb_cap": 273
    }
  },
  "scheduler": {
    "ranking": "epf",
    "reinsert_policy": "tail_append"
  },
  "report": {
    "output_dir": "outputs/systematic_simulation_analysis_option1_expanded_incremental",
    "keep_slot_trace": false
  },
  "systematic_analysis": {
    "background_user_count_values": [16, 24, 32, 36, 40, 48],
    "pdb_user_count_values": [4, 8, 10, 12, 16],
    "pdb_ms_values": [100, 200, 300, 500, 600],
    "pdb_packet_kb_values": [20, 30, 40, 50, 70, 100, 150, 300],
    "repeat_count": 10,
    "random_seed_base": 7,
    "baseline_policy": "tail_append",
    "ours_policy": "hopeless_front_insert",
    "background_packet_kb": 2,
    "minimum_total_users": 32,
    "reuse_output_dirs": ["outputs/systematic_simulation_analysis_option1"],
    "merged_output_dir": "outputs/systematic_simulation_analysis_option1_expanded",
    "scene_bank": {
      "medium_distance_range_m": [170.0, 230.0],
      "good_distance_range_m": [80.0, 140.0],
      "poor_distance_range_m": [390.0, 470.0]
    }
  }
}
```

- [ ] **Step 4: Run config test**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_expanded_systematic_analysis_config_declares_reuse_and_total_user_filter -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add configs/systematic_simulation_analysis_option1_expanded.json tests/test_cli.py
git commit -m "Add expanded systematic-analysis config"
```

### Task 5: Verify the codebase and execute the expanded run

**Files:**
- Create: `outputs/systematic_simulation_analysis_option1_expanded_incremental/`
- Create: `outputs/systematic_simulation_analysis_option1_expanded/`

- [ ] **Step 1: Run the focused verification suite**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis tests.test_systematic_analysis_plots tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_writes_manifest_and_tables tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_supports_hopeless_front_insert_ours_policy tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_reuses_existing_scene_keys_and_merges_outputs tests.test_cli.CliSmokeTests.test_expanded_systematic_analysis_config_declares_reuse_and_total_user_filter tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_renderer_runs_on_runner_output -v`

Expected: PASS

- [ ] **Step 2: Run the expanded incremental analysis**

Run: `PYTHONPATH=src python scripts/run_systematic_simulation_analysis.py configs/systematic_simulation_analysis_option1_expanded.json`

Expected: stdout prints `outputs/systematic_simulation_analysis_option1_expanded/summary_report.md` after the incremental run and merged regeneration complete.

- [ ] **Step 3: Re-render the final merged figures explicitly**

Run: `PYTHONPATH=src python scripts/render_systematic_simulation_analysis_plots.py outputs/systematic_simulation_analysis_option1_expanded`

Expected: stdout prints `outputs/systematic_simulation_analysis_option1_expanded`

- [ ] **Step 4: Verify final merged artifacts exist**

Run: `find outputs/systematic_simulation_analysis_option1_expanded -maxdepth 1 -type f | sort`

Expected: includes `experiment_manifest.json`, `per_run_rows.csv`, `paired_rows.csv`, `scene_summary.csv`, `region_summary.csv`, `capacity_summary_95.csv`, `capacity_summary_90.csv`, `boundary_feasibility_95.csv`, `boundary_feasibility_90.csv`, `typical_case_candidates.csv`, `typical_case_details.csv`, `summary_report.md`, and plot PNGs.

- [ ] **Step 5: Commit**

```bash
git add outputs/systematic_simulation_analysis_option1_expanded_incremental outputs/systematic_simulation_analysis_option1_expanded
git commit -m "Run expanded systematic-analysis merge experiment"
```
