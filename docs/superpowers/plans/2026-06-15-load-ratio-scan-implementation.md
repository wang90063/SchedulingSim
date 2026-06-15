# Load-Ratio Scan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a load-ratio-driven systematic scan that runs the approved 36-point business matrix, records ratio metadata alongside simulator results, and renders outputs in the new `rho_bg / rho_pdb / prb_share_pdb` coordinate system.

**Architecture:** Reuse the existing systematic-analysis pipeline instead of creating a parallel experiment stack. Extend the existing config, case-generation, runner, and plot layers so the old `option1` path still works while the new load-ratio scan can be selected via a dedicated config. Keep the realization-bank and paired-run machinery unchanged; only the business matrix definition, metadata propagation, and report/plot framing need to change.

**Tech Stack:** Python, `unittest`, existing `systematic_analysis` and runner scripts, JSON configs, CSV/JSON/Markdown outputs, `matplotlib`.

---

## Proposed File Structure

- Modify: `src/scheduling_sim/systematic_analysis.py`
  - Add explicit load-ratio scene metadata, support fixed `background_user_count` / `pdb_user_count` with packet-size vectors, and expose helper functions for ratio calculations.
- Modify: `scripts/run_systematic_simulation_analysis.py`
  - Accept the new load-ratio config shape, build the 36-point grid, write ratio metadata into manifests and rows, and generate a ratio-oriented markdown report.
- Modify: `scripts/render_systematic_simulation_analysis_plots.py`
  - Render plots using `rho_bg`, `rho_pdb`, and `prb_share_pdb` labels instead of the old `background_user_count × pdb_packet_kb` framing when the output directory contains the new manifest shape.
- Create: `configs/systematic_simulation_analysis_load_ratio.json`
  - Checked-in config for the approved 36-point scan.
- Modify: `tests/test_systematic_analysis.py`
  - Cover load-ratio scene expansion, ratio math, and mixed compatibility with the old case builder.
- Modify: `tests/test_cli.py`
  - Add runner smoke coverage for the new config and confirm ratio metadata lands in manifest and output rows.
- Modify: `tests/test_systematic_analysis_plots.py`
  - Add renderer coverage for the ratio-based manifest and label selection.

## Task 1: Extend Case Modeling for Load-Ratio Scenes

**Files:**
- Modify: `src/scheduling_sim/systematic_analysis.py`
- Test: `tests/test_systematic_analysis.py`

- [ ] **Step 1: Write failing tests for load-ratio case expansion**

```python
    def test_load_ratio_cases_expand_to_expected_business_points(self) -> None:
        cases = load_ratio_cases(
            background_user_count=40,
            background_period_ms=10,
            background_packet_kb_values=[0.8, 1.2],
            pdb_user_count=4,
            pdb_shapes=[
                {"pdb_ms": 100, "pdb_packet_kb_values": [5.0, 10.0]},
                {"pdb_ms": 300, "pdb_packet_kb_values": [15.0]},
            ],
            background_capacity_mbps=66.03,
            pdb_capacity_mbps=8.74,
        )

        self.assertEqual(len(cases), 6)
        self.assertEqual(cases[0].background_user_count, 40)
        self.assertEqual(cases[0].background_packet_kb, 0.8)
        self.assertEqual(cases[0].pdb_user_count, 4)
        self.assertEqual(cases[0].pdb_ms, 100)
        self.assertEqual(cases[0].pdb_packet_kb, 5.0)
        self.assertAlmostEqual(cases[0].rho_bg, 0.388, places=3)
        self.assertAlmostEqual(cases[0].rho_pdb, 0.183, places=3)
        self.assertAlmostEqual(cases[0].prb_share_pdb, 0.3206, places=3)
        self.assertAlmostEqual(cases[0].g_pdb_mbps, 0.4, places=3)

    def test_load_ratio_case_scene_key_remains_compatible_with_existing_pairing(self) -> None:
        case = LoadRatioCase(
            case_label="L01",
            background_user_count=40,
            background_packet_kb=0.8,
            background_period_ms=10,
            pdb_user_count=4,
            pdb_packet_kb=5.0,
            pdb_ms=100,
            rho_bg=0.388,
            rho_pdb=0.183,
            prb_share_pdb=0.321,
            g_pdb_mbps=0.4,
        )

        self.assertEqual(
            load_ratio_scene_key(case),
            (40, 4, 100, 5.0, 0.8, 10),
        )
```

- [ ] **Step 2: Run the targeted tests to confirm failure**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis.SystematicAnalysisTests.test_load_ratio_cases_expand_to_expected_business_points tests.test_systematic_analysis.SystematicAnalysisTests.test_load_ratio_case_scene_key_remains_compatible_with_existing_pairing -v`

Expected: FAIL with `NameError` or `AttributeError` because `load_ratio_cases`, `LoadRatioCase`, and `load_ratio_scene_key` do not exist yet.

- [ ] **Step 3: Add the minimal load-ratio dataclass and helper functions**

```python
@dataclass(frozen=True)
class LoadRatioCase:
    case_label: str
    background_user_count: int
    background_packet_kb: float
    background_period_ms: int
    pdb_user_count: int
    pdb_packet_kb: float
    pdb_ms: int
    rho_bg: float
    rho_pdb: float
    prb_share_pdb: float
    g_pdb_mbps: float


def _background_offered_load_mbps(*, background_user_count: int, background_packet_kb: float, background_period_ms: int) -> float:
    return (float(background_user_count) * float(background_packet_kb) * 8.0) / float(background_period_ms)


def _pdb_offered_load_mbps(*, pdb_user_count: int, pdb_packet_kb: float, pdb_ms: int) -> float:
    return (float(pdb_user_count) * float(pdb_packet_kb) * 8.0) / float(pdb_ms)


def load_ratio_cases(
    *,
    background_user_count: int,
    background_period_ms: int,
    background_packet_kb_values: list[float],
    pdb_user_count: int,
    pdb_shapes: list[dict[str, object]],
    background_capacity_mbps: float,
    pdb_capacity_mbps: float,
) -> list[LoadRatioCase]:
    cases: list[LoadRatioCase] = []
    case_index = 1
    for background_packet_kb in background_packet_kb_values:
        rho_bg = _background_offered_load_mbps(
            background_user_count=background_user_count,
            background_packet_kb=background_packet_kb,
            background_period_ms=background_period_ms,
        ) / float(background_capacity_mbps)
        for shape in pdb_shapes:
            pdb_ms = int(shape["pdb_ms"])
            for pdb_packet_kb in [float(value) for value in shape["pdb_packet_kb_values"]]:
                rho_pdb = _pdb_offered_load_mbps(
                    pdb_user_count=pdb_user_count,
                    pdb_packet_kb=pdb_packet_kb,
                    pdb_ms=pdb_ms,
                ) / float(pdb_capacity_mbps)
                prb_share_pdb = rho_pdb / (rho_bg + rho_pdb) if (rho_bg + rho_pdb) > 0.0 else 0.0
                g_pdb_mbps = (float(pdb_packet_kb) * 8.0) / float(pdb_ms)
                cases.append(
                    LoadRatioCase(
                        case_label=f"L{case_index:02d}",
                        background_user_count=background_user_count,
                        background_packet_kb=float(background_packet_kb),
                        background_period_ms=background_period_ms,
                        pdb_user_count=pdb_user_count,
                        pdb_packet_kb=float(pdb_packet_kb),
                        pdb_ms=pdb_ms,
                        rho_bg=rho_bg,
                        rho_pdb=rho_pdb,
                        prb_share_pdb=prb_share_pdb,
                        g_pdb_mbps=g_pdb_mbps,
                    )
                )
                case_index += 1
    return cases


def load_ratio_scene_key(case: LoadRatioCase) -> tuple[int, int, int, float, float, int]:
    return (
        int(case.background_user_count),
        int(case.pdb_user_count),
        int(case.pdb_ms),
        float(case.pdb_packet_kb),
        float(case.background_packet_kb),
        int(case.background_period_ms),
    )
```

- [ ] **Step 4: Re-run the targeted tests and verify they pass**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis.SystematicAnalysisTests.test_load_ratio_cases_expand_to_expected_business_points tests.test_systematic_analysis.SystematicAnalysisTests.test_load_ratio_case_scene_key_remains_compatible_with_existing_pairing -v`

Expected: PASS

- [ ] **Step 5: Commit the load-ratio case helpers**

```bash
git add src/scheduling_sim/systematic_analysis.py tests/test_systematic_analysis.py
git commit -m "Add load-ratio case expansion helpers"
```

## Task 2: Support the New Config Shape in the Runner

**Files:**
- Modify: `scripts/run_systematic_simulation_analysis.py`
- Modify: `tests/test_cli.py`
- Create: `configs/systematic_simulation_analysis_load_ratio.json`

- [ ] **Step 1: Write a failing runner smoke test for the load-ratio config**

```python
    def test_systematic_simulation_analysis_runner_supports_load_ratio_config(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repo_root = Path(__file__).resolve().parents[1]
            payload = json.loads(
                (repo_root / "configs" / "systematic_simulation_analysis_option1.json").read_text(encoding="utf-8")
            )
            payload["report"]["output_dir"] = str(Path(tmpdir) / "outputs")
            payload["systematic_analysis"] = {
                "mode": "load_ratio",
                "background_user_count": 40,
                "background_period_ms": 10,
                "background_packet_kb_values": [0.8],
                "pdb_user_count": 4,
                "pdb_shapes": [
                    {"pdb_ms": 100, "pdb_packet_kb_values": [5.0, 10.0]},
                ],
                "repeat_count": 1,
                "random_seed_base": 7,
                "baseline_policy": "tail_append",
                "ours_policy": "hopeless_front_insert",
                "scene_bank": {
                    "medium_distance_range_m": [170.0, 230.0],
                    "good_distance_range_m": [80.0, 140.0],
                    "poor_distance_range_m": [390.0, 470.0],
                },
                "capacity_reference": {
                    "background_capacity_mbps": 66.03,
                    "pdb_capacity_mbps": 8.74,
                },
            }
            config_path = Path(tmpdir) / "load_ratio.json"
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            subprocess.run(
                ["python", "scripts/run_systematic_simulation_analysis.py", str(config_path)],
                cwd=repo_root,
                check=True,
            )

            manifest = json.loads((Path(tmpdir) / "outputs" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["scan_mode"], "load_ratio")
            self.assertEqual(manifest["background_packet_kb_values"], [0.8])
            self.assertEqual(manifest["pdb_shapes"], [{"pdb_ms": 100, "pdb_packet_kb_values": [5.0, 10.0]}])
            detail_rows = list(csv.DictReader((Path(tmpdir) / "outputs" / "per_run_rows.csv").open()))
            self.assertEqual({row["case_label"] for row in detail_rows}, {"L01", "L02"})
            self.assertEqual({row["rho_bg"] for row in detail_rows}, {"0.3876963591192605"})
```

- [ ] **Step 2: Run the CLI smoke test and confirm failure**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_supports_load_ratio_config -v`

Expected: FAIL because the runner only understands the legacy `background_user_count_values / pdb_packet_kb_values` config shape.

- [ ] **Step 3: Add config parsing and manifest support for `mode = load_ratio`**

```python
    scan_mode = str(sweep.get("mode", "legacy_grid"))
    if scan_mode == "load_ratio":
        cases = load_ratio_cases(
            background_user_count=int(sweep["background_user_count"]),
            background_period_ms=int(sweep["background_period_ms"]),
            background_packet_kb_values=[float(value) for value in sweep["background_packet_kb_values"]],
            pdb_user_count=int(sweep["pdb_user_count"]),
            pdb_shapes=list(sweep["pdb_shapes"]),
            background_capacity_mbps=float(sweep["capacity_reference"]["background_capacity_mbps"]),
            pdb_capacity_mbps=float(sweep["capacity_reference"]["pdb_capacity_mbps"]),
        )
        background_packet_bits_by_case = {
            case.case_label: int(round(case.background_packet_kb * 1000.0 * 8.0))
            for case in cases
        }
    else:
        cases = systematic_cases(...)
```

```python
        manifest = {
            "scan_mode": scan_mode,
            "background_packet_kb_values": [float(case.background_packet_kb) for case in cases] if scan_mode == "load_ratio" else list(sweep["background_packet_kb_values"]),
            "pdb_shapes": sweep.get("pdb_shapes", []),
            ...
        }
```

- [ ] **Step 4: Add the checked-in load-ratio config**

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
      "mcs_table_path": "mcs/nr_ul_main.json"
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
    "output_dir": "outputs/systematic_simulation_analysis_load_ratio",
    "keep_slot_trace": false
  },
  "systematic_analysis": {
    "mode": "load_ratio",
    "background_user_count": 40,
    "background_period_ms": 10,
    "background_packet_kb_values": [0.8, 1.2, 1.6, 2.0],
    "pdb_user_count": 4,
    "pdb_shapes": [
      { "pdb_ms": 100, "pdb_packet_kb_values": [5.0, 10.0, 15.0] },
      { "pdb_ms": 300, "pdb_packet_kb_values": [15.0, 30.0, 45.0] },
      { "pdb_ms": 500, "pdb_packet_kb_values": [25.0, 50.0, 75.0] }
    ],
    "capacity_reference": {
      "background_capacity_mbps": 66.03,
      "pdb_capacity_mbps": 8.74
    },
    "repeat_count": 10,
    "random_seed_base": 7,
    "baseline_policy": "tail_append",
    "ours_policy": "hopeless_front_insert",
    "scene_bank": {
      "medium_distance_range_m": [170.0, 230.0],
      "good_distance_range_m": [80.0, 140.0],
      "poor_distance_range_m": [390.0, 470.0]
    }
  }
}
```

- [ ] **Step 5: Re-run the CLI smoke test and verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_supports_load_ratio_config -v`

Expected: PASS

- [ ] **Step 6: Commit the runner/config support**

```bash
git add scripts/run_systematic_simulation_analysis.py configs/systematic_simulation_analysis_load_ratio.json tests/test_cli.py
git commit -m "Add load-ratio systematic analysis config support"
```

## Task 3: Propagate Ratio Metadata Through Per-Run and Aggregated Outputs

**Files:**
- Modify: `src/scheduling_sim/systematic_analysis.py`
- Modify: `scripts/run_systematic_simulation_analysis.py`
- Modify: `tests/test_systematic_analysis.py`

- [ ] **Step 1: Write failing tests for ratio metadata in rows**

```python
    def test_per_run_metric_row_includes_load_ratio_metadata(self) -> None:
        row = per_run_metric_row(
            scenario_id="load-ratio-case",
            seed=7,
            policy="tail_append",
            case=LoadRatioCase(
                case_label="L01",
                background_user_count=40,
                background_packet_kb=0.8,
                background_period_ms=10,
                pdb_user_count=4,
                pdb_packet_kb=5.0,
                pdb_ms=100,
                rho_bg=0.388,
                rho_pdb=0.183,
                prb_share_pdb=0.321,
                g_pdb_mbps=0.4,
            ),
            summary={"edge_pdb_satisfaction_rate": 0.5, "center_agg_rate_bps": 1.0, "center_avg_rate_bps": 1.0, "prb_utilization": 0.5, "center_prb_share": 0.4, "edge_prb_share": 0.6, "pdb_arrivals_in_window": 4.0, "pdb_violation_rate": 0.5, "target_edge_completion_delay_ms": 80.0, "target_edge_queue_wait_ms": 60.0, "target_edge_service_time_ms": 20.0, "edge_backlog_bits": 0.0},
        )

        self.assertEqual(row["case_label"], "L01")
        self.assertEqual(row["background_packet_kb"], 0.8)
        self.assertEqual(row["background_period_ms"], 10)
        self.assertEqual(row["rho_bg"], 0.388)
        self.assertEqual(row["rho_pdb"], 0.183)
        self.assertEqual(row["prb_share_pdb"], 0.321)
        self.assertEqual(row["g_pdb_mbps"], 0.4)
```

- [ ] **Step 2: Run the targeted unit test and confirm failure**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis.SystematicAnalysisTests.test_per_run_metric_row_includes_load_ratio_metadata -v`

Expected: FAIL because the legacy row builder only writes `background_user_count / pdb_user_count / pdb_ms / pdb_packet_kb`.

- [ ] **Step 3: Extend row builders to accept both legacy and load-ratio cases**

```python
def _case_metadata(case: SystematicCase | LoadRatioCase) -> dict[str, float | int | str]:
    base = {
        "background_user_count": int(case.background_user_count),
        "pdb_user_count": int(case.pdb_user_count),
        "pdb_ms": int(case.pdb_ms),
        "pdb_packet_kb": float(case.pdb_packet_kb),
    }
    if isinstance(case, LoadRatioCase):
        base.update(
            {
                "case_label": case.case_label,
                "background_packet_kb": float(case.background_packet_kb),
                "background_period_ms": int(case.background_period_ms),
                "rho_bg": float(case.rho_bg),
                "rho_pdb": float(case.rho_pdb),
                "prb_share_pdb": float(case.prb_share_pdb),
                "g_pdb_mbps": float(case.g_pdb_mbps),
            }
        )
    return base
```

```python
def per_run_metric_row(...):
    return {
        "seed": int(seed),
        "scenario_id": scenario_id,
        "policy": str(policy),
        **_case_metadata(case),
        ...
    }
```

- [ ] **Step 4: Re-run the targeted unit test and verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis.SystematicAnalysisTests.test_per_run_metric_row_includes_load_ratio_metadata -v`

Expected: PASS

- [ ] **Step 5: Commit the ratio metadata propagation**

```bash
git add src/scheduling_sim/systematic_analysis.py scripts/run_systematic_simulation_analysis.py tests/test_systematic_analysis.py
git commit -m "Propagate load-ratio metadata through analysis rows"
```

## Task 4: Update Markdown Reporting for the New Coordinate System

**Files:**
- Modify: `scripts/run_systematic_simulation_analysis.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write a failing report-content smoke test**

```python
    def test_systematic_simulation_analysis_runner_writes_load_ratio_summary_report(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repo_root = Path(__file__).resolve().parents[1]
            config_path = repo_root / "configs" / "systematic_simulation_analysis_load_ratio.json"

            subprocess.run(
                ["python", "scripts/run_systematic_simulation_analysis.py", str(config_path)],
                cwd=repo_root,
                check=True,
            )

            report_text = (repo_root / "outputs" / "systematic_simulation_analysis_load_ratio" / "summary_report.md").read_text(encoding="utf-8")
            self.assertIn("`scan_mode = load_ratio`", report_text)
            self.assertIn("| case_label | rho_bg | rho_pdb | prb_share_pdb |", report_text)
            self.assertIn("`PDB` packet shape remains a secondary axis", report_text)
```

- [ ] **Step 2: Run the report smoke test and confirm failure**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_writes_load_ratio_summary_report -v`

Expected: FAIL because the current report generator only writes the old `background_user_count / pdb_user_count / pdb_ms / pdb_packet_kb` framing.

- [ ] **Step 3: Add a load-ratio report branch**

```python
    if manifest.get("scan_mode") == "load_ratio":
        lines.extend(
            [
                "## Load-Ratio Grid",
                "",
                f"- `scan_mode = {manifest['scan_mode']}`",
                f"- `background_user_count = {manifest['background_user_count']}`",
                f"- `background_period_ms = {manifest['background_period_ms']}`",
                f"- `pdb_user_count = {manifest['pdb_user_count']}`",
                "",
                "| case_label | rho_bg | rho_pdb | prb_share_pdb | baseline_pdb_satisfaction | proposed_pdb_satisfaction | center_retention |",
                "|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
```

- [ ] **Step 4: Re-run the report smoke test and verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_writes_load_ratio_summary_report -v`

Expected: PASS

- [ ] **Step 5: Commit the report update**

```bash
git add scripts/run_systematic_simulation_analysis.py tests/test_cli.py
git commit -m "Report load-ratio systematic analysis results"
```

## Task 5: Update Plot Rendering for Ratio-Based Labels

**Files:**
- Modify: `scripts/render_systematic_simulation_analysis_plots.py`
- Modify: `tests/test_systematic_analysis_plots.py`

- [ ] **Step 1: Write a failing renderer test for ratio-axis labels**

```python
    def test_renderer_uses_ratio_manifest_axes_for_load_ratio_outputs(self) -> None:
        output_dir = Path(self.tempdir.name)
        (output_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "scan_mode": "load_ratio",
                    "background_packet_kb_values": [0.8, 1.2],
                    "pdb_shapes": [{"pdb_ms": 100, "pdb_packet_kb_values": [5.0, 10.0]}],
                }
            ),
            encoding="utf-8",
        )
        (output_dir / "scene_summary.csv").write_text(
            "case_label,rho_bg,rho_pdb,prb_share_pdb,background_packet_kb,pdb_ms,pdb_packet_kb,baseline_edge_pdb_satisfaction_rate,proposed_edge_pdb_satisfaction_rate,mean_delta_pdb_satisfaction_rate,mean_center_throughput_retention\n"
            "L01,0.388,0.183,0.321,0.8,100,5.0,0.1,0.2,0.1,1.0\n"
            "L02,0.582,0.366,0.386,1.2,100,10.0,0.1,0.3,0.2,0.9\n",
            encoding="utf-8",
        )

        labels = ratio_axis_labels(output_dir)
        self.assertEqual(labels["x_label"], "rho_bg")
        self.assertEqual(labels["y_label"], "rho_pdb")
```

- [ ] **Step 2: Run the renderer test and confirm failure**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis_plots.SystematicAnalysisPlotTests.test_renderer_uses_ratio_manifest_axes_for_load_ratio_outputs -v`

Expected: FAIL because the renderer has no load-ratio label branch.

- [ ] **Step 3: Add the minimal manifest-driven label and grouping branch**

```python
def ratio_axis_labels(output_dir: Path) -> dict[str, str]:
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("scan_mode") == "load_ratio":
        return {"x_label": "rho_bg", "y_label": "rho_pdb", "panel_label": "pdb_ms / pdb_packet_kb"}
    return {"x_label": "background_user_count", "y_label": "pdb_user_count", "panel_label": "pdb_ms / pdb_packet_kb"}
```

- [ ] **Step 4: Re-run the renderer test and verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis_plots.SystematicAnalysisPlotTests.test_renderer_uses_ratio_manifest_axes_for_load_ratio_outputs -v`

Expected: PASS

- [ ] **Step 5: Commit the renderer update**

```bash
git add scripts/render_systematic_simulation_analysis_plots.py tests/test_systematic_analysis_plots.py
git commit -m "Render systematic analysis plots in load-ratio space"
```

## Task 6: Run Focused Regression Verification

**Files:**
- Modify: none
- Test: `tests/test_systematic_analysis.py`, `tests/test_cli.py`, `tests/test_systematic_analysis_plots.py`

- [ ] **Step 1: Run the focused systematic-analysis test set**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis tests.test_systematic_analysis_plots tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_supports_load_ratio_config tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_writes_load_ratio_summary_report tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_renderer_runs_on_runner_output -v`

Expected: PASS

- [ ] **Step 2: Run the existing legacy runner regression tests**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_writes_manifest_and_tables tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_reuses_existing_scene_keys_and_merges_outputs tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_supports_hopeless_front_insert_ours_policy -v`

Expected: PASS

- [ ] **Step 3: Commit any final test-only adjustments**

```bash
git add tests/test_systematic_analysis.py tests/test_systematic_analysis_plots.py tests/test_cli.py
git commit -m "Verify load-ratio systematic analysis coverage"
```
