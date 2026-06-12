# Systematic Analysis Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the missing `option 1` delivery semantics for systematic analysis, then run the formal `81 x 10 x 2` reference experiment and produce the canonical output directory.

**Architecture:** Keep the existing `systematic_analysis` core and extend the current runner and renderer rather than introducing new entrypoints. First enrich exported representative-case and report data, then upgrade boundary and representative-case figures, then run focused verification, and only after that run the full reference experiment and render the final artifacts.

**Tech Stack:** Python, `unittest`, existing simulator/config/metrics modules, `matplotlib`, JSON/CSV/Markdown outputs.

---

## Proposed File Structure

- Modify: `src/scheduling_sim/systematic_analysis.py`
  - Add helpers to build representative-case detail rows and reusable boundary-feasibility grids from aggregated scene rows and paired results.
- Modify: `scripts/run_systematic_simulation_analysis.py`
  - Export `typical_case_details.csv`, expand `summary_report.md` into the intended chapter structure, and include the richer representative-case information.
- Modify: `scripts/render_systematic_simulation_analysis_plots.py`
  - Replace the boundary gain-bar rendering with feasible-region comparison panels and add representative-case mechanism figures.
- Modify: `tests/test_systematic_analysis.py`
  - Cover the new representative-case detail and boundary helper outputs.
- Modify: `tests/test_systematic_analysis_plots.py`
  - Cover the richer boundary rendering semantics and representative-case figure emission.
- Modify: `tests/test_cli.py`
  - Extend runner and renderer smokes for the new files and report sections.
- Create: `outputs/systematic_simulation_analysis_option1/`
  - Canonical output directory for the formal first-pass experiment.

## Task 1: Extend Systematic-Analysis Data Exports

**Files:**
- Modify: `src/scheduling_sim/systematic_analysis.py`
- Modify: `tests/test_systematic_analysis.py`

- [x] **Step 1: Write failing unit tests for representative-case detail export and boundary feasibility summaries**

```python
# tests/test_systematic_analysis.py
    def test_build_typical_case_detail_rows_expands_each_selected_case_to_per_policy_rows(self) -> None:
        scene_rows = [
            {
                "background_user_count": 24,
                "pdb_user_count": 4,
                "pdb_ms": 100,
                "pdb_packet_kb": 50,
                "baseline_edge_pdb_satisfaction_rate": 0.96,
                "proposed_edge_pdb_satisfaction_rate": 0.99,
                "mean_delta_pdb_satisfaction_rate": 0.03,
                "mean_center_throughput_retention": 0.97,
            }
        ]
        per_run_rows = [
            {
                "seed": 7,
                "scenario_id": "bg24_pdb4_d100_k50_seed00",
                "policy": "tail_append",
                "background_user_count": 24,
                "pdb_user_count": 4,
                "pdb_ms": 100,
                "pdb_packet_kb": 50,
                "edge_pdb_satisfaction_rate": 0.96,
                "center_agg_rate_bps": 1000.0,
                "center_avg_rate_bps": 50.0,
                "prb_utilization": 0.70,
                "center_prb_share": 0.60,
                "edge_prb_share": 0.40,
                "pdb_arrivals_in_window": 8.0,
                "pdb_violation_rate": 0.04,
                "target_edge_completion_delay_ms": 90.0,
                "target_edge_queue_wait_ms": 50.0,
                "target_edge_service_time_ms": 40.0,
                "edge_backlog_bits": 0.0,
            },
            {
                "seed": 7,
                "scenario_id": "bg24_pdb4_d100_k50_seed00",
                "policy": "hopeless_front_insert",
                "background_user_count": 24,
                "pdb_user_count": 4,
                "pdb_ms": 100,
                "pdb_packet_kb": 50,
                "edge_pdb_satisfaction_rate": 0.99,
                "center_agg_rate_bps": 970.0,
                "center_avg_rate_bps": 48.5,
                "prb_utilization": 0.73,
                "center_prb_share": 0.56,
                "edge_prb_share": 0.44,
                "pdb_arrivals_in_window": 8.0,
                "pdb_violation_rate": 0.01,
                "target_edge_completion_delay_ms": 80.0,
                "target_edge_queue_wait_ms": 42.0,
                "target_edge_service_time_ms": 38.0,
                "edge_backlog_bits": 0.0,
            },
        ]
        rows = build_typical_case_detail_rows(
            scene_rows=scene_rows,
            per_run_rows=per_run_rows,
            baseline_policy="tail_append",
            proposed_policy="hopeless_front_insert",
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual({row["policy"] for row in rows}, {"tail_append", "hopeless_front_insert"})
        self.assertEqual({row["case_label"] for row in rows}, {"easy"})

    def test_boundary_feasibility_rows_builds_baseline_and_proposed_masks(self) -> None:
        rows = build_boundary_feasibility_rows(
            [
                {
                    "background_user_count": 24,
                    "pdb_user_count": 4,
                    "pdb_ms": 100,
                    "pdb_packet_kb": 50,
                    "baseline_edge_pdb_satisfaction_rate": 0.96,
                    "proposed_edge_pdb_satisfaction_rate": 0.98,
                },
                {
                    "background_user_count": 36,
                    "pdb_user_count": 4,
                    "pdb_ms": 100,
                    "pdb_packet_kb": 50,
                    "baseline_edge_pdb_satisfaction_rate": 0.88,
                    "proposed_edge_pdb_satisfaction_rate": 0.95,
                },
            ],
            threshold=0.95,
        )
        self.assertEqual(len(rows), 2)
        second = next(row for row in rows if row["background_user_count"] == 36)
        self.assertEqual(second["baseline_feasible"], 0)
        self.assertEqual(second["proposed_feasible"], 1)
```

- [x] **Step 2: Run the systematic-analysis unit file and verify the new tests fail**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis -v`

Expected: FAIL with missing helper names for `build_typical_case_detail_rows` and `build_boundary_feasibility_rows`.

- [x] **Step 3: Add representative-case detail and boundary-feasibility helpers**

```python
# src/scheduling_sim/systematic_analysis.py
def build_typical_case_detail_rows(
    *,
    scene_rows: list[dict[str, float | int]],
    per_run_rows: list[dict[str, float | int | str]],
    baseline_policy: str,
    proposed_policy: str,
) -> list[dict[str, float | int | str]]:
    detail_rows: list[dict[str, float | int | str]] = []
    for typical_row in select_typical_case_rows(scene_rows):
        for policy in (baseline_policy, proposed_policy):
            matching_rows = [
                row
                for row in per_run_rows
                if str(row["policy"]) == policy
                and int(row["background_user_count"]) == int(typical_row["background_user_count"])
                and int(row["pdb_user_count"]) == int(typical_row["pdb_user_count"])
                and int(row["pdb_ms"]) == int(typical_row["pdb_ms"])
                and int(row["pdb_packet_kb"]) == int(typical_row["pdb_packet_kb"])
            ]
            if not matching_rows:
                continue
            mean_fields = (
                "edge_pdb_satisfaction_rate",
                "center_agg_rate_bps",
                "center_avg_rate_bps",
                "prb_utilization",
                "center_prb_share",
                "edge_prb_share",
                "pdb_arrivals_in_window",
                "pdb_violation_rate",
                "target_edge_completion_delay_ms",
                "target_edge_queue_wait_ms",
                "target_edge_service_time_ms",
                "edge_backlog_bits",
            )
            aggregated = {
                field_name: _mean([float(row[field_name]) for row in matching_rows])
                for field_name in mean_fields
            }
            detail_rows.append(
                {
                    "case_label": str(typical_row["case_label"]),
                    "policy": policy,
                    "background_user_count": int(typical_row["background_user_count"]),
                    "pdb_user_count": int(typical_row["pdb_user_count"]),
                    "pdb_ms": int(typical_row["pdb_ms"]),
                    "pdb_packet_kb": int(typical_row["pdb_packet_kb"]),
                    **aggregated,
                }
            )
    return detail_rows


def build_boundary_feasibility_rows(
    scene_rows: list[dict[str, float | int]],
    *,
    threshold: float,
) -> list[dict[str, float | int]]:
    rows: list[dict[str, float | int]] = []
    for row in scene_rows:
        rows.append(
            {
                "background_user_count": int(row["background_user_count"]),
                "pdb_user_count": int(row["pdb_user_count"]),
                "pdb_ms": int(row["pdb_ms"]),
                "pdb_packet_kb": int(row["pdb_packet_kb"]),
                "threshold": float(threshold),
                "baseline_feasible": int(float(row["baseline_edge_pdb_satisfaction_rate"]) >= threshold),
                "proposed_feasible": int(float(row["proposed_edge_pdb_satisfaction_rate"]) >= threshold),
            }
        )
    return rows
```

- [x] **Step 4: Run the systematic-analysis unit file and verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis -v`

Expected: PASS

- [x] **Step 5: Commit the helper-layer extension**

```bash
git add src/scheduling_sim/systematic_analysis.py tests/test_systematic_analysis.py
git commit -m "feat: add systematic analysis delivery helpers"
```

## Task 2: Enrich Runner Outputs and Report Structure

**Files:**
- Modify: `scripts/run_systematic_simulation_analysis.py`
- Modify: `tests/test_cli.py`

- [x] **Step 1: Write failing CLI assertions for the richer output set**

```python
# tests/test_cli.py
            self.assertTrue((output_dir / "typical_case_details.csv").exists())
            summary_report = (output_dir / "summary_report.md").read_text(encoding="utf-8")
            self.assertIn("## Wireless Environment and Realization Bank", summary_report)
            self.assertIn("## Business Scan Matrix", summary_report)
            self.assertIn("## Reporting Semantics", summary_report)
            self.assertIn("## Panoramic PDB Gain Overview", summary_report)
            self.assertIn("## Feasible Boundary Expansion", summary_report)
            self.assertIn("## Representative Case Mechanism Analysis", summary_report)
            self.assertIn("## Summary", summary_report)
```

- [x] **Step 2: Run the runner smoke test and verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_writes_manifest_and_tables -v`

Expected: FAIL because `typical_case_details.csv` and the expanded section headers do not exist yet.

- [x] **Step 3: Export `typical_case_details.csv` and expand `summary_report.md`**

```python
# scripts/run_systematic_simulation_analysis.py
from scheduling_sim.systematic_analysis import (
    SceneBankSpec,
    aggregate_scene_rows,
    build_boundary_feasibility_rows,
    build_realization_bank,
    build_systematic_case_users,
    build_typical_case_detail_rows,
    capacity_summary_rows,
    paired_metric_row,
    per_run_metric_row,
    select_typical_case_rows,
    summarize_regions,
    systematic_cases,
)


def _summary_report(
    *,
    manifest: dict[str, object],
    scene_rows: list[dict[str, object]],
    region_rows: list[dict[str, object]],
    typical_case_rows: list[dict[str, object]],
    typical_case_detail_rows: list[dict[str, object]],
) -> str:
    lines = [
        "# Systematic Simulation Analysis",
        "",
        "## Wireless Environment and Realization Bank",
        "",
        f"- scenario_type: `{manifest['scene_bank_counts']}`",
        f"- scene_bank_counts: `{manifest['scene_bank_counts']}`",
        "",
        "## Business Scan Matrix",
        "",
        f"- background_user_count: `{manifest['background_user_count_values']}`",
        f"- pdb_user_count: `{manifest['pdb_user_count_values']}`",
        f"- pdb_ms: `{manifest['pdb_ms_values']}`",
        f"- pdb_packet_kb: `{manifest['pdb_packet_kb_values']}`",
        f"- repeat_count: `{manifest['repeat_count']}`",
        "",
        "## Reporting Semantics",
        "",
        "- reporting window: fixed `10 s`",
        "- primary KPI: `edge_pdb_satisfaction_rate`",
        "- main cost KPI: `center_throughput_retention`",
        "",
        "## Panoramic PDB Gain Overview",
        "",
        f"- Aggregated scene points: `{len(scene_rows)}`",
        "",
        "## Background Cost and Resource Analysis",
        "",
        "| Region | Scene Points | Share | Win Rate | Mean Delta PDB Satisfaction | Mean Center Retention |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in region_rows:
        lines.append(
            f"| {row['region']} | {row['scene_point_count']} | {float(row['scene_point_share']):.2f} | "
            f"{float(row['proposed_win_rate']):.2f} | {float(row['mean_delta_pdb_satisfaction_rate']):.3f} | "
            f"{float(row['mean_center_throughput_retention']):.3f} |"
        )
    lines.extend(
        [
            "",
            "## Feasible Boundary Expansion",
            "",
            "- See `capacity_summary_95.csv`, `capacity_summary_90.csv`, and the boundary figures for baseline/proposed feasible-region comparisons.",
        ]
    )
    if typical_case_rows:
        lines.extend(
            [
                "",
                "## Representative Case Mechanism Analysis",
                "",
                "| Label | background_user_count | pdb_user_count | pdb_ms | pdb_packet_kb | Mean Delta PDB Satisfaction | Center Retention |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in typical_case_rows:
            lines.append(
                f"| {row['case_label']} | {row['background_user_count']} | {row['pdb_user_count']} | "
                f"{row['pdb_ms']} | {row['pdb_packet_kb']} | "
                f"{float(row['mean_delta_pdb_satisfaction_rate']):.3f} | "
                f"{float(row['mean_center_throughput_retention']):.3f} |"
            )
        lines.extend(
            [
                "",
                f"- Representative detail rows: `{len(typical_case_detail_rows)}`",
                "",
                "## Summary",
                "",
                "- Summarize where the proposed policy helps, what center cost it causes, and whether the feasible PDB region expands materially.",
            ]
        )
    return "\n".join(lines)
```

- [x] **Step 4: Wire the new output table into the runner**

```python
# scripts/run_systematic_simulation_analysis.py
    typical_case_rows = select_typical_case_rows(scene_rows)
    typical_case_detail_rows = build_typical_case_detail_rows(
        scene_rows=scene_rows,
        per_run_rows=per_run_rows,
        baseline_policy=baseline_policy,
        proposed_policy=ours_policy,
    )
    boundary_rows_95 = build_boundary_feasibility_rows(scene_rows, threshold=0.95)
    boundary_rows_90 = build_boundary_feasibility_rows(scene_rows, threshold=0.90)
    manifest = {
        **sweep,
        "reference_config": str(config_path),
        "scene_bank_counts": {
            "medium": scene_bank_spec.medium_count,
            "good": scene_bank_spec.good_count,
            "poor": scene_bank_spec.poor_count,
        },
        "boundary_feasibility_files": [
            "boundary_feasibility_95.csv",
            "boundary_feasibility_90.csv",
        ],
    }

    _write_table(output_dir / "capacity_summary_95.csv", capacity_rows_95)
    _write_table(output_dir / "capacity_summary_90.csv", capacity_rows_90)
    _write_table(output_dir / "boundary_feasibility_95.csv", boundary_rows_95)
    _write_table(output_dir / "boundary_feasibility_90.csv", boundary_rows_90)
    _write_table(output_dir / "typical_case_candidates.csv", typical_case_rows)
    _write_table(output_dir / "typical_case_details.csv", typical_case_detail_rows)
    (output_dir / "summary_report.md").write_text(
        _summary_report(
            manifest=manifest,
            scene_rows=scene_rows,
            region_rows=region_rows,
            typical_case_rows=typical_case_rows,
            typical_case_detail_rows=typical_case_detail_rows,
        ),
        encoding="utf-8",
    )
```

- [x] **Step 5: Re-run the runner smoke test and verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_writes_manifest_and_tables -v`

Expected: PASS

- [x] **Step 6: Commit the richer runner outputs**

```bash
git add scripts/run_systematic_simulation_analysis.py tests/test_cli.py
git commit -m "feat: enrich systematic analysis delivery outputs"
```

## Task 3: Replace Boundary Rendering and Add Representative-Case Figures

**Files:**
- Modify: `scripts/render_systematic_simulation_analysis_plots.py`
- Modify: `tests/test_systematic_analysis_plots.py`
- Modify: `tests/test_cli.py`

- [x] **Step 1: Write failing plot tests for feasible-region boundary rendering and representative-case figures**

```python
# tests/test_systematic_analysis_plots.py
            with (output_dir / "boundary_feasibility_95.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "background_user_count",
                        "pdb_user_count",
                        "pdb_ms",
                        "pdb_packet_kb",
                        "threshold",
                        "baseline_feasible",
                        "proposed_feasible",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "background_user_count": 24,
                        "pdb_user_count": 4,
                        "pdb_ms": 100,
                        "pdb_packet_kb": 50,
                        "threshold": 0.95,
                        "baseline_feasible": 0,
                        "proposed_feasible": 1,
                    }
                )
            with (output_dir / "boundary_feasibility_90.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "background_user_count",
                        "pdb_user_count",
                        "pdb_ms",
                        "pdb_packet_kb",
                        "threshold",
                        "baseline_feasible",
                        "proposed_feasible",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "background_user_count": 24,
                        "pdb_user_count": 4,
                        "pdb_ms": 100,
                        "pdb_packet_kb": 50,
                        "threshold": 0.90,
                        "baseline_feasible": 1,
                        "proposed_feasible": 1,
                    }
                )
            with (output_dir / "typical_case_details.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "case_label",
                        "policy",
                        "background_user_count",
                        "pdb_user_count",
                        "pdb_ms",
                        "pdb_packet_kb",
                        "edge_pdb_satisfaction_rate",
                        "center_agg_rate_bps",
                        "center_avg_rate_bps",
                        "prb_utilization",
                        "center_prb_share",
                        "edge_prb_share",
                        "pdb_arrivals_in_window",
                        "pdb_violation_rate",
                        "target_edge_completion_delay_ms",
                        "target_edge_queue_wait_ms",
                        "target_edge_service_time_ms",
                        "edge_backlog_bits",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "case_label": "critical",
                        "policy": "tail_append",
                        "background_user_count": 24,
                        "pdb_user_count": 4,
                        "pdb_ms": 100,
                        "pdb_packet_kb": 50,
                        "edge_pdb_satisfaction_rate": 0.8,
                        "center_agg_rate_bps": 1000.0,
                        "center_avg_rate_bps": 50.0,
                        "prb_utilization": 0.7,
                        "center_prb_share": 0.6,
                        "edge_prb_share": 0.4,
                        "pdb_arrivals_in_window": 8.0,
                        "pdb_violation_rate": 0.2,
                        "target_edge_completion_delay_ms": 90.0,
                        "target_edge_queue_wait_ms": 55.0,
                        "target_edge_service_time_ms": 35.0,
                        "edge_backlog_bits": 0.0,
                    }
                )
                writer.writerow(
                    {
                        "case_label": "critical",
                        "policy": "hopeless_front_insert",
                        "background_user_count": 24,
                        "pdb_user_count": 4,
                        "pdb_ms": 100,
                        "pdb_packet_kb": 50,
                        "edge_pdb_satisfaction_rate": 0.95,
                        "center_agg_rate_bps": 950.0,
                        "center_avg_rate_bps": 47.5,
                        "prb_utilization": 0.75,
                        "center_prb_share": 0.55,
                        "edge_prb_share": 0.45,
                        "pdb_arrivals_in_window": 8.0,
                        "pdb_violation_rate": 0.05,
                        "target_edge_completion_delay_ms": 80.0,
                        "target_edge_queue_wait_ms": 45.0,
                        "target_edge_service_time_ms": 35.0,
                        "edge_backlog_bits": 0.0,
                    }
                )
            self.assertTrue((output_dir / "typical_case_critical.png").exists())
```

- [x] **Step 2: Run the plot test file and verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis_plots -v`

Expected: FAIL because the renderer does not yet read the new boundary-feasibility and representative-case detail files.

- [x] **Step 3: Replace boundary gain bars with feasible-region comparison panels**

```python
# scripts/render_systematic_simulation_analysis_plots.py
def _boundary_value(
    rows: list[dict[str, str]],
    *,
    pdb_ms: int,
    pdb_packet_kb: int,
    background_user_count: int,
    pdb_user_count: int,
    field_name: str,
) -> float:
    for row in rows:
        if (
            int(row["pdb_ms"]) == pdb_ms
            and int(row["pdb_packet_kb"]) == pdb_packet_kb
            and int(row["background_user_count"]) == background_user_count
            and int(row["pdb_user_count"]) == pdb_user_count
        ):
            return float(row[field_name])
    return 0.0


def _boundary_plot(
    manifest: dict[str, object],
    *,
    boundary_rows: list[dict[str, str]],
    threshold: float,
    output_path: Path,
) -> None:
    pdb_ms_values = [int(value) for value in manifest["pdb_ms_values"]]
    packet_values = [int(value) for value in manifest["pdb_packet_kb_values"]]
    background_values = [int(value) for value in manifest["background_user_count_values"]]
    pdb_user_values = [int(value) for value in manifest["pdb_user_count_values"]]
    fig, axes = plt.subplots(len(pdb_ms_values), len(packet_values), figsize=(12, 10), constrained_layout=True, squeeze=False)
    for row_index, pdb_ms in enumerate(pdb_ms_values):
        for col_index, packet_kb in enumerate(packet_values):
            ax = axes[row_index][col_index]
            baseline_matrix = [
                [
                    _boundary_value(
                        boundary_rows,
                        pdb_ms=pdb_ms,
                        pdb_packet_kb=packet_kb,
                        background_user_count=background_user_count,
                        pdb_user_count=pdb_user_count,
                        field_name="baseline_feasible",
                    )
                    for background_user_count in background_values
                ]
                for pdb_user_count in pdb_user_values
            ]
            proposed_matrix = [
                [
                    _boundary_value(
                        boundary_rows,
                        pdb_ms=pdb_ms,
                        pdb_packet_kb=packet_kb,
                        background_user_count=background_user_count,
                        pdb_user_count=pdb_user_count,
                        field_name="proposed_feasible",
                    )
                    for background_user_count in background_values
                ]
                for pdb_user_count in pdb_user_values
            ]
            ax.imshow(baseline_matrix, origin="lower", aspect="auto", cmap="Blues", alpha=0.55, vmin=0.0, vmax=1.0)
            ax.imshow(proposed_matrix, origin="lower", aspect="auto", cmap="Oranges", alpha=0.35, vmin=0.0, vmax=1.0)
            ax.set_title(f"PDB {pdb_ms} ms / {packet_kb} KB")
            ax.set_xticks(range(len(background_values)), labels=[str(value) for value in background_values])
            ax.set_yticks(range(len(pdb_user_values)), labels=[str(value) for value in pdb_user_values])
            ax.set_xlabel("background_user_count")
            ax.set_ylabel("pdb_user_count")
    fig.suptitle(f"Feasible Region Comparison @ {threshold:.0%} (blue=baseline, orange=proposed)")
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
```

- [x] **Step 4: Add representative-case mechanism figure rendering**

```python
# scripts/render_systematic_simulation_analysis_plots.py
def _render_typical_case_figures(output_dir: Path, detail_rows: list[dict[str, str]]) -> None:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in detail_rows:
        grouped.setdefault(str(row["case_label"]), []).append(row)
    metric_fields = [
        "edge_pdb_satisfaction_rate",
        "target_edge_queue_wait_ms",
        "target_edge_service_time_ms",
        "target_edge_completion_delay_ms",
        "edge_backlog_bits",
        "prb_utilization",
        "center_prb_share",
        "edge_prb_share",
        "center_agg_rate_bps",
    ]
    for case_label, rows in grouped.items():
        policies = [str(row["policy"]) for row in rows]
        fig, ax = plt.subplots(figsize=(12, 5), constrained_layout=True)
        x_positions = range(len(metric_fields))
        width = 0.35
        for index, row in enumerate(rows):
            values = [float(row[field_name]) for field_name in metric_fields]
            shifted = [value + (index - 0.5) * width for value in x_positions]
            ax.bar(shifted, values, width=width, label=str(row["policy"]))
        ax.set_xticks(list(x_positions), labels=metric_fields, rotation=35, ha="right")
        ax.set_title(f"Representative Case: {case_label}")
        ax.legend()
        fig.savefig(output_dir / f"typical_case_{case_label}.png", dpi=200)
        plt.close(fig)
```

- [x] **Step 5: Wire the new files into `main()`**

```python
# scripts/render_systematic_simulation_analysis_plots.py
    boundary_rows_95 = _rows(output_dir / "boundary_feasibility_95.csv")
    boundary_rows_90 = _rows(output_dir / "boundary_feasibility_90.csv")
    typical_case_detail_rows = _rows(output_dir / "typical_case_details.csv")
    _boundary_plot(
        manifest,
        boundary_rows=boundary_rows_95,
        threshold=0.95,
        output_path=output_dir / "capacity_boundary_95.png",
    )
    _boundary_plot(
        manifest,
        boundary_rows=boundary_rows_90,
        threshold=0.90,
        output_path=output_dir / "capacity_boundary_90.png",
    )
    _render_typical_case_figures(output_dir, typical_case_detail_rows)
```

- [x] **Step 6: Re-run plot and renderer CLI tests**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis_plots tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_renderer_runs_on_runner_output -v`

Expected: PASS

- [ ] **Step 7: Commit the renderer delivery upgrade**

```bash
git add scripts/render_systematic_simulation_analysis_plots.py tests/test_systematic_analysis_plots.py tests/test_cli.py
git commit -m "feat: complete systematic analysis delivery plots"
```

## Task 4: Run Focused Verification and Produce the Canonical Experiment Output

**Files:**
- Create: `outputs/systematic_simulation_analysis_option1/`

- [x] **Step 1: Run the focused verification slice for touched code**

Run: `PYTHONPATH=src python -m unittest tests.test_wireless_env tests.test_systematic_analysis tests.test_systematic_analysis_plots tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_writes_manifest_and_tables tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_supports_hopeless_front_insert_ours_policy tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_renderer_runs_on_runner_output tests.test_reinsert tests.test_simulator tests.test_config tests.test_cli.CliSmokeTests.test_run_command_supports_hopeless_front_insert_override tests.test_cli.CliSmokeTests.test_run_command_report_contains_grouped_metrics -v`

Expected: PASS

- [x] **Step 2: Run the full reference experiment**

Run: `PYTHONPATH=src python scripts/run_systematic_simulation_analysis.py configs/systematic_simulation_analysis_option1.json`

Expected: `outputs/systematic_simulation_analysis_option1/summary_report.md` printed to stdout after the run completes.

- [x] **Step 3: Render the full reference figures**

Run: `PYTHONPATH=src python scripts/render_systematic_simulation_analysis_plots.py outputs/systematic_simulation_analysis_option1`

Expected: `outputs/systematic_simulation_analysis_option1` printed to stdout after figure generation.

- [x] **Step 4: Verify row counts and file completeness**

Run: `python - <<'PY'
from pathlib import Path
import csv

root = Path("outputs/systematic_simulation_analysis_option1")
required = [
    "experiment_manifest.json",
    "raw_summaries.json",
    "per_run_rows.csv",
    "paired_rows.csv",
    "scene_summary.csv",
    "region_summary.csv",
    "capacity_summary_95.csv",
    "capacity_summary_90.csv",
    "boundary_feasibility_95.csv",
    "boundary_feasibility_90.csv",
    "typical_case_candidates.csv",
    "typical_case_details.csv",
    "summary_report.md",
    "overview_delta_pdb_satisfaction.png",
    "center_throughput_retention.png",
    "capacity_boundary_95.png",
    "capacity_boundary_90.png",
]
for name in required:
    path = root / name
    assert path.exists(), f"missing {name}"

def count_rows(name: str) -> int:
    with (root / name).open(encoding="utf-8", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))

assert count_rows("per_run_rows.csv") == 1620
assert count_rows("paired_rows.csv") == 810
assert count_rows("scene_summary.csv") == 81
assert count_rows("capacity_summary_95.csv") == 54
assert count_rows("capacity_summary_90.csv") == 54

report_text = (root / "summary_report.md").read_text(encoding="utf-8")
for heading in [
    "## Wireless Environment and Realization Bank",
    "## Business Scan Matrix",
    "## Reporting Semantics",
    "## Panoramic PDB Gain Overview",
    "## Background Cost and Resource Analysis",
    "## Feasible Boundary Expansion",
    "## Representative Case Mechanism Analysis",
    "## Summary",
]:
    assert heading in report_text, f"missing heading {heading}"

typical_pngs = list(root.glob("typical_case_*.png"))
assert typical_pngs, "missing representative-case figures"
print("systematic analysis option1 artifacts verified")
PY`

Expected: `systematic analysis option1 artifacts verified`

- [ ] **Step 5: Commit the canonical experiment outputs if requested, otherwise leave them as generated artifacts**

```bash
git status --short
```

Expected: only the intended code/doc changes plus generated `outputs/systematic_simulation_analysis_option1/` artifacts if outputs are meant to be versioned.

## Self-Review Checklist

- Spec coverage:
  - representative-case detail export is covered by Task 1 and Task 2;
  - expanded report structure is covered by Task 2;
  - feasible-region boundary figures are covered by Task 3;
  - representative-case mechanism figures are covered by Task 3;
  - formal reference experiment execution and artifact acceptance are covered by Task 4.
- Placeholder scan:
  - no task says merely “improve output” or “add plots” without explicit assertions, code, or commands;
  - final acceptance includes exact file names and exact expected row counts.
- Type consistency:
  - `background_user_count`, `pdb_user_count`, `pdb_ms`, and `pdb_packet_kb` are used consistently across helper outputs, runner outputs, renderer inputs, and artifact checks;
  - `typical_case_details.csv`, `boundary_feasibility_95.csv`, and `boundary_feasibility_90.csv` are introduced before later tasks depend on them.
