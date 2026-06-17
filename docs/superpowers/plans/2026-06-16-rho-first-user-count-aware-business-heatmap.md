# Rho-First User-Count-Aware Mapping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the rho-first systematic-analysis pipeline so `background_user_count` and `pdb_user_count` become explicit scan axes while preserving rho-defined load targets, enabling business-parameter heatmaps that do not collapse to a single user-count pair and reusing existing scene results whenever the generated business tuple already matches prior outputs.

**Architecture:** Keep rho-first as the load-definition layer, but split scene construction into two stages: an outer scene grid that explicitly enumerates `N_bg × N_pdb × rho_bg × rho_pdb × pdb_ms`, and an inner solver that only maps the remaining continuous business knobs (`background_period_ms`, optionally constrained `background_packet_kb`, and `pdb_packet_kb`). Reuse remains runner-level: scene keys already encode the concrete business tuple, so once the generator emits the new tuples deterministically, existing outputs can be merged in without rerunning unchanged points.

**Tech Stack:** Python, `unittest`, existing `systematic_analysis`/runner/plot renderer modules, JSON/CSV/Markdown outputs, matplotlib.

---

## Proposed File Structure

- Modify: `src/scheduling_sim/systematic_analysis.py`
  - Add explicit user-count-aware rho-first case generation and constrained solvers that accept fixed `background_user_count` / `pdb_user_count`.
- Modify: `scripts/run_systematic_simulation_analysis.py`
  - Parse the new config shape, record the explicit scan axes in the manifest, keep reuse/merge semantics unchanged, and improve the rho-first summary report wording so it explains the business-axis expansion.
- Modify: `scripts/render_systematic_simulation_analysis_plots.py`
  - Add business-parameter heatmaps for rho-first outputs and keep existing rho-space plots.
- Create: `configs/systematic_simulation_analysis_load_ratio_rho_first_user_count_axes.json`
  - Checked-in reference config for the user-count-aware rho-first scan.
- Modify: `tests/test_systematic_analysis.py`
  - Cover explicit user-count rho-first case generation and solver constraints.
- Modify: `tests/test_cli.py`
  - Cover config parsing, manifest fields, summary-report wording, and reuse behavior for the new scan shape.
- Modify: `tests/test_systematic_analysis_plots.py`
  - Cover business-parameter plot rendering for rho-first outputs.
- Create: `docs/superpowers/specs/2026-06-16-rho-first-user-count-aware-business-heatmap-design.md`
  - Design doc for the scan-shape change and reuse strategy.

### Task 1: Write the spec for user-count-aware rho-first mapping

**Files:**
- Create: `docs/superpowers/specs/2026-06-16-rho-first-user-count-aware-business-heatmap-design.md`

- [ ] **Step 1: Write the spec document**

```md
# Rho-First User-Count-Aware Business Heatmap Design

## Goal

Preserve rho-first load definitions while making `background_user_count` and `pdb_user_count` explicit business scan axes so the resulting systematic-analysis outputs can support both rho-space heatmaps and business-parameter heatmaps.

## Problem

The current rho-first candidate-domain solver can legally choose:

- `background_user_count ∈ {32, 40, 48}`
- `pdb_user_count ∈ {4, 8}`

but its tie-breaking prefers the anchor values:

- `anchor_background_user_count = 40`
- `anchor_pdb_user_count = 4`

As a result, the finished 60-point output collapses to one realized user-count pair:

- `background_user_count = 40`
- `pdb_user_count = 4`

That is acceptable for rho-space analysis, but it is too narrow for business-parameter heatmaps.

## Chosen Direction

Split the rho-first scene definition into:

1. explicit discrete business axes
   - `background_user_count_values`
   - `pdb_user_count_values`
2. rho-space load targets
   - `rho_bg_values`
   - `rho_pdb_values`
3. a small PDB timing-shape axis
   - `pdb_ms_values`

For each scene point, solve only the remaining continuous business parameters:

- background: solve `background_period_ms` under a bounded candidate `background_packet_kb` domain
- PDB: solve `pdb_packet_kb` for the fixed `pdb_user_count` and `pdb_ms`

## Reuse Requirement

Reuse existing outputs whenever the generated concrete business tuple already exists in a previous output directory. Reuse is determined by the existing concrete scene key:

- `(background_user_count, pdb_user_count, pdb_ms, pdb_packet_kb, background_packet_kb, background_period_ms)`

The new scan should therefore be designed to make overlaps visible rather than forcing a full rerun.

## Reporting

The report should include both:

- rho-space heatmaps
- business-parameter heatmaps

For business heatmaps, use:

- x-axis: `background_user_count`
- y-axis: `pdb_user_count`
- panel split: fixed `(rho_bg, rho_pdb, pdb_ms)`
- color: metric value

This lets readers compare different user-count realizations under the same target load ratios.
```

- [ ] **Step 2: Commit the spec**

```bash
git add docs/superpowers/specs/2026-06-16-rho-first-user-count-aware-business-heatmap-design.md
git commit -m "docs: design user-count-aware rho-first scan"
```

### Task 2: Add failing tests for explicit user-count rho-first generation

**Files:**
- Modify: `tests/test_systematic_analysis.py`
- Test: `tests/test_systematic_analysis.py`

- [ ] **Step 1: Write the failing case-generation tests**

```python
    def test_rho_first_cases_expand_over_explicit_user_count_axes(self) -> None:
        cases = load_ratio_cases(
            rho_bg_values=[0.388],
            rho_pdb_values=[0.183],
            pdb_ms_values=[20],
            background_capacity_mbps=66.03,
            pdb_capacity_mbps=8.74,
            mapping_policy=systematic_analysis.LoadRatioMappingPolicy(
                background=systematic_analysis.BackgroundMappingPolicy(
                    background_user_count_values=[32, 40],
                    background_packet_kb_values=[1.5, 2.0],
                    background_period_ms_range=(4.0, 30.0),
                    anchor_background_user_count=40,
                    anchor_background_packet_kb=2.0,
                ),
                pdb=systematic_analysis.PdbMappingPolicy(
                    pdb_user_count_values=[4, 8],
                    pdb_packet_kb_range=(0.5, 80.0),
                    anchor_pdb_user_count=4,
                ),
            ),
            explicit_background_user_count_values=[32, 40],
            explicit_pdb_user_count_values=[4, 8],
        )

        realized_pairs = {(case.background_user_count, case.pdb_user_count) for case in cases}
        self.assertEqual(realized_pairs, {(32, 4), (32, 8), (40, 4), (40, 8)})
        self.assertEqual(len(cases), 4)

    def test_rho_first_explicit_user_count_solver_holds_counts_fixed(self) -> None:
        result = systematic_analysis.solve_background_mapping_for_fixed_user_count(
            target_rho_bg=0.582,
            background_capacity_mbps=66.03,
            background_user_count=32,
            policy=systematic_analysis.BackgroundMappingPolicy(
                background_user_count_values=[32, 40, 48],
                background_packet_kb_values=[1.5, 2.0],
                background_period_ms_range=(4.0, 30.0),
                anchor_background_user_count=40,
                anchor_background_packet_kb=2.0,
            ),
        )

        self.assertEqual(result.background_user_count, 32)
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis.SystematicAnalysisTests.test_rho_first_cases_expand_over_explicit_user_count_axes tests.test_systematic_analysis.SystematicAnalysisTests.test_rho_first_explicit_user_count_solver_holds_counts_fixed -v`
Expected: FAIL because `load_ratio_cases(...)` does not accept explicit user-count axes and there is no fixed-count solver.

- [ ] **Step 3: Implement the minimal explicit-user-count rho-first generation**

```python
def solve_background_mapping_for_fixed_user_count(
    *,
    target_rho_bg: float,
    background_capacity_mbps: float,
    background_user_count: int,
    policy: BackgroundMappingPolicy,
) -> BackgroundMappingResult:
    if float(background_capacity_mbps) <= 0.0:
        raise ValueError("background_capacity_mbps must be > 0")
    if float(target_rho_bg) <= 0.0:
        raise ValueError("target_rho_bg must be > 0")

    target_load_mbps = float(target_rho_bg) * float(background_capacity_mbps)
    min_period_ms, max_period_ms = policy.background_period_ms_range
    candidates: list[tuple[float, float, BackgroundMappingResult]] = []
    for background_packet_kb in policy.background_packet_kb_values:
        solved_period_ms = (float(background_user_count) * float(background_packet_kb) * 8.0) / target_load_mbps
        if not min_period_ms <= solved_period_ms <= max_period_ms:
            continue
        rounded_period_ms = _round_to_tenth(solved_period_ms)
        if not min_period_ms <= rounded_period_ms <= max_period_ms:
            continue
        actual_rho_bg = _background_offered_load_mbps(
            background_user_count=background_user_count,
            background_packet_kb=background_packet_kb,
            background_period_ms=rounded_period_ms,
        ) / float(background_capacity_mbps)
        candidates.append(
            (
                abs(actual_rho_bg - float(target_rho_bg)),
                abs(float(background_packet_kb) - float(policy.anchor_background_packet_kb)),
                BackgroundMappingResult(
                    background_user_count=int(background_user_count),
                    background_packet_kb=float(background_packet_kb),
                    background_period_ms=rounded_period_ms,
                    actual_rho_bg=actual_rho_bg,
                    mapping_policy="fixed_user_count_solve_period",
                ),
            )
        )
    if not candidates:
        raise ValueError(
            f"no valid background mapping for target_rho_bg={target_rho_bg} background_user_count={background_user_count}"
        )
    candidates.sort(key=lambda item: (item[0], item[1], item[2].background_packet_kb, item[2].background_period_ms))
    return candidates[0][2]
```

```python
def solve_pdb_mapping_for_fixed_user_count(
    *,
    target_rho_pdb: float,
    pdb_ms: int,
    pdb_capacity_mbps: float,
    pdb_user_count: int,
    policy: PdbMappingPolicy,
) -> PdbMappingResult:
    if int(pdb_ms) <= 0:
        raise ValueError("pdb_ms must be > 0")
    if float(pdb_capacity_mbps) <= 0.0:
        raise ValueError("pdb_capacity_mbps must be > 0")
    if float(target_rho_pdb) <= 0.0:
        raise ValueError("target_rho_pdb must be > 0")

    target_load_mbps = float(target_rho_pdb) * float(pdb_capacity_mbps)
    min_packet_kb, max_packet_kb = policy.pdb_packet_kb_range
    solved_packet_kb = (target_load_mbps * float(pdb_ms)) / (float(pdb_user_count) * 8.0)
    rounded_packet_kb = _round_to_tenth(solved_packet_kb)
    if not min_packet_kb <= rounded_packet_kb <= max_packet_kb:
        raise ValueError(
            f"no valid pdb mapping for target_rho_pdb={target_rho_pdb} pdb_ms={pdb_ms} pdb_user_count={pdb_user_count}"
        )
    actual_rho_pdb = _pdb_offered_load_mbps(
        pdb_user_count=pdb_user_count,
        pdb_packet_kb=rounded_packet_kb,
        pdb_ms=pdb_ms,
    ) / float(pdb_capacity_mbps)
    return PdbMappingResult(
        pdb_user_count=int(pdb_user_count),
        pdb_packet_kb=rounded_packet_kb,
        pdb_ms=int(pdb_ms),
        actual_rho_pdb=actual_rho_pdb,
        mapping_policy="fixed_user_count_solve_packet",
    )
```

```python
def _rho_first_load_ratio_cases(
    *,
    rho_bg_values: list[float],
    rho_pdb_values: list[float],
    pdb_ms_values: list[int],
    background_capacity_mbps: float,
    pdb_capacity_mbps: float,
    mapping_policy: LoadRatioMappingPolicy,
    explicit_background_user_count_values: list[int] | None = None,
    explicit_pdb_user_count_values: list[int] | None = None,
) -> list[LoadRatioCase]:
    background_user_counts = (
        [int(value) for value in explicit_background_user_count_values]
        if explicit_background_user_count_values is not None
        else [None]
    )
    pdb_user_counts = (
        [int(value) for value in explicit_pdb_user_count_values]
        if explicit_pdb_user_count_values is not None
        else [None]
    )

    cases: list[LoadRatioCase] = []
    case_index = 1
    for target_rho_bg in rho_bg_values:
        for fixed_background_user_count in background_user_counts:
            background_mapping = (
                solve_background_mapping_for_fixed_user_count(
                    target_rho_bg=float(target_rho_bg),
                    background_capacity_mbps=float(background_capacity_mbps),
                    background_user_count=int(fixed_background_user_count),
                    policy=mapping_policy.background,
                )
                if fixed_background_user_count is not None
                else solve_background_mapping(
                    target_rho_bg=float(target_rho_bg),
                    background_capacity_mbps=float(background_capacity_mbps),
                    policy=mapping_policy.background,
                )
            )
            for target_rho_pdb in rho_pdb_values:
                for fixed_pdb_user_count in pdb_user_counts:
                    for pdb_ms in pdb_ms_values:
                        pdb_mapping = (
                            solve_pdb_mapping_for_fixed_user_count(
                                target_rho_pdb=float(target_rho_pdb),
                                pdb_ms=int(pdb_ms),
                                pdb_capacity_mbps=float(pdb_capacity_mbps),
                                pdb_user_count=int(fixed_pdb_user_count),
                                policy=mapping_policy.pdb,
                            )
                            if fixed_pdb_user_count is not None
                            else solve_pdb_mapping(
                                target_rho_pdb=float(target_rho_pdb),
                                pdb_ms=int(pdb_ms),
                                pdb_capacity_mbps=float(pdb_capacity_mbps),
                                policy=mapping_policy.pdb,
                            )
                        )
                        prb_share_pdb = (
                            pdb_mapping.actual_rho_pdb / (background_mapping.actual_rho_bg + pdb_mapping.actual_rho_pdb)
                            if (background_mapping.actual_rho_bg + pdb_mapping.actual_rho_pdb) > 0.0
                            else 0.0
                        )
                        cases.append(
                            LoadRatioCase(
                                case_label=f"L{case_index:02d}",
                                background_user_count=background_mapping.background_user_count,
                                background_packet_kb=background_mapping.background_packet_kb,
                                background_period_ms=background_mapping.background_period_ms,
                                pdb_user_count=pdb_mapping.pdb_user_count,
                                pdb_packet_kb=pdb_mapping.pdb_packet_kb,
                                pdb_ms=pdb_mapping.pdb_ms,
                                target_rho_bg=float(target_rho_bg),
                                target_rho_pdb=float(target_rho_pdb),
                                actual_rho_bg=background_mapping.actual_rho_bg,
                                actual_rho_pdb=pdb_mapping.actual_rho_pdb,
                                rho_bg=background_mapping.actual_rho_bg,
                                rho_pdb=pdb_mapping.actual_rho_pdb,
                                prb_share_pdb=prb_share_pdb,
                                g_pdb_mbps=(float(pdb_mapping.pdb_packet_kb) * 8.0) / float(pdb_mapping.pdb_ms),
                                background_mapping_policy=background_mapping.mapping_policy,
                                pdb_mapping_policy=pdb_mapping.mapping_policy,
                            )
                        )
                        case_index += 1
    return cases
```

- [ ] **Step 4: Run the focused tests and verify they pass**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis.SystematicAnalysisTests.test_rho_first_cases_expand_over_explicit_user_count_axes tests.test_systematic_analysis.SystematicAnalysisTests.test_rho_first_explicit_user_count_solver_holds_counts_fixed -v`
Expected: PASS

- [ ] **Step 5: Commit the explicit-user-count generator**

```bash
git add src/scheduling_sim/systematic_analysis.py tests/test_systematic_analysis.py
git commit -m "feat: add explicit user-count rho-first mapping"
```

### Task 3: Expose the new scan shape in config parsing, manifest, and reuse flow

**Files:**
- Modify: `scripts/run_systematic_simulation_analysis.py`
- Modify: `tests/test_cli.py`
- Create: `configs/systematic_simulation_analysis_load_ratio_rho_first_user_count_axes.json`

- [ ] **Step 1: Write the failing CLI smoke test for the new config shape**

```python
    def test_systematic_simulation_analysis_runner_supports_rho_first_user_count_axes_config(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "out"
            config_path = Path(tmpdir) / "config.json"
            _write_nr_ul_main_table(Path(tmpdir), repo_root)
            payload = json.loads(
                (repo_root / "configs" / "systematic_simulation_analysis_load_ratio_rho_first_hopeless_tail_append.json").read_text(encoding="utf-8")
            )
            payload["report"]["output_dir"] = str(output_dir)
            payload["systematic_analysis"]["rho_bg_values"] = [0.388]
            payload["systematic_analysis"]["rho_pdb_values"] = [0.183]
            payload["systematic_analysis"]["pdb_ms_values"] = [20]
            payload["systematic_analysis"]["background_user_count_values"] = [32, 40]
            payload["systematic_analysis"]["pdb_user_count_values"] = [4, 8]
            payload["systematic_analysis"]["repeat_count"] = 1
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
            manifest = json.loads((output_dir / "experiment_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["explicit_background_user_count_values"], [32, 40])
            self.assertEqual(manifest["explicit_pdb_user_count_values"], [4, 8])
```

- [ ] **Step 2: Run the CLI smoke test and verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_supports_rho_first_user_count_axes_config -v`
Expected: FAIL because the config parser ignores the explicit user-count scan axes.

- [ ] **Step 3: Wire the config fields through the runner and manifest**

```python
if scan_mode == "load_ratio":
    explicit_background_user_count_values = (
        [int(value) for value in sweep["background_user_count_values"]]
        if "rho_bg_values" in sweep and "background_user_count_values" in sweep
        else None
    )
    explicit_pdb_user_count_values = (
        [int(value) for value in sweep["pdb_user_count_values"]]
        if "rho_pdb_values" in sweep and "pdb_user_count_values" in sweep
        else None
    )
    all_cases = load_ratio_cases(
        rho_bg_values=[float(value) for value in sweep["rho_bg_values"]],
        rho_pdb_values=[float(value) for value in sweep["rho_pdb_values"]],
        pdb_ms_values=[int(value) for value in sweep["pdb_ms_values"]],
        background_capacity_mbps=float(sweep["capacity_reference"]["background_capacity_mbps"]),
        pdb_capacity_mbps=float(sweep["capacity_reference"]["pdb_capacity_mbps"]),
        mapping_policy=load_ratio_mapping_policy,
        explicit_background_user_count_values=explicit_background_user_count_values,
        explicit_pdb_user_count_values=explicit_pdb_user_count_values,
    )
```

```python
manifest_sweep.update(
    {
        "rho_bg_values": [float(value) for value in sweep["rho_bg_values"]],
        "rho_pdb_values": [float(value) for value in sweep["rho_pdb_values"]],
        "pdb_ms_values": [int(value) for value in sweep["pdb_ms_values"]],
        "explicit_background_user_count_values": explicit_background_user_count_values,
        "explicit_pdb_user_count_values": explicit_pdb_user_count_values,
        "mapping_policy": {...},
    }
)
```

```json
{
  "systematic_analysis": {
    "mode": "load_ratio",
    "rho_bg_values": [0.388, 0.775, 0.969],
    "rho_pdb_values": [0.183, 0.549],
    "pdb_ms_values": [50, 300],
    "background_user_count_values": [32, 40, 48],
    "pdb_user_count_values": [4, 8],
    "capacity_reference": {
      "background_capacity_mbps": 66.03,
      "pdb_capacity_mbps": 8.74
    },
    "mapping_policy": {
      "background": {
        "kind": "candidate_domain_solve_period",
        "background_user_count_values": [32, 40, 48],
        "background_packet_kb_values": [1.5, 2.0],
        "background_period_ms_range": [4.0, 30.0],
        "anchor_background_user_count": 40,
        "anchor_background_packet_kb": 2.0
      },
      "pdb": {
        "kind": "candidate_domain_solve_packet",
        "pdb_user_count_values": [4, 8],
        "pdb_packet_kb_range": [0.5, 80.0],
        "anchor_pdb_user_count": 4
      }
    }
  }
}
```

- [ ] **Step 4: Re-run the CLI smoke test and verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_supports_rho_first_user_count_axes_config -v`
Expected: PASS

- [ ] **Step 5: Commit the runner/config changes**

```bash
git add scripts/run_systematic_simulation_analysis.py configs/systematic_simulation_analysis_load_ratio_rho_first_user_count_axes.json tests/test_cli.py
git commit -m "feat: support user-count-aware rho-first scan config"
```

### Task 4: Add business-parameter heatmaps for rho-first outputs

**Files:**
- Modify: `scripts/render_systematic_simulation_analysis_plots.py`
- Modify: `tests/test_systematic_analysis_plots.py`

- [ ] **Step 1: Write the failing plot test**

```python
    def test_renderer_writes_business_heatmaps_for_rho_first_user_count_axes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            (output_dir / "experiment_manifest.json").write_text(
                json.dumps(
                    {
                        "scan_mode": "load_ratio",
                        "rho_bg_values": [0.388],
                        "rho_pdb_values": [0.183],
                        "pdb_ms_values": [20],
                        "explicit_background_user_count_values": [32, 40],
                        "explicit_pdb_user_count_values": [4, 8],
                    }
                ),
                encoding="utf-8",
            )
            with (output_dir / "scene_summary.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "background_user_count",
                        "pdb_user_count",
                        "pdb_ms",
                        "pdb_packet_kb",
                        "target_rho_bg",
                        "target_rho_pdb",
                        "mean_delta_pdb_satisfaction_rate",
                        "mean_center_throughput_retention",
                        "prb_share_pdb",
                    ],
                )
                writer.writeheader()
                writer.writerow({"background_user_count": 32, "pdb_user_count": 4, "pdb_ms": 20, "pdb_packet_kb": 1.0, "target_rho_bg": 0.388, "target_rho_pdb": 0.183, "mean_delta_pdb_satisfaction_rate": 0.01, "mean_center_throughput_retention": 0.99, "prb_share_pdb": 0.3})
                writer.writerow({"background_user_count": 40, "pdb_user_count": 4, "pdb_ms": 20, "pdb_packet_kb": 1.0, "target_rho_bg": 0.388, "target_rho_pdb": 0.183, "mean_delta_pdb_satisfaction_rate": 0.02, "mean_center_throughput_retention": 0.98, "prb_share_pdb": 0.3})
                writer.writerow({"background_user_count": 32, "pdb_user_count": 8, "pdb_ms": 20, "pdb_packet_kb": 0.5, "target_rho_bg": 0.388, "target_rho_pdb": 0.183, "mean_delta_pdb_satisfaction_rate": 0.03, "mean_center_throughput_retention": 0.97, "prb_share_pdb": 0.3})
                writer.writerow({"background_user_count": 40, "pdb_user_count": 8, "pdb_ms": 20, "pdb_packet_kb": 0.5, "target_rho_bg": 0.388, "target_rho_pdb": 0.183, "mean_delta_pdb_satisfaction_rate": 0.04, "mean_center_throughput_retention": 0.96, "prb_share_pdb": 0.3})

            exit_code = render_main([str(output_dir)])
            self.assertEqual(exit_code, 0)
            self.assertTrue((output_dir / "business_delta_pdb_satisfaction.png").exists())
            self.assertTrue((output_dir / "business_center_throughput_retention.png").exists())
```

- [ ] **Step 2: Run the plot test and verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis_plots.SystematicAnalysisPlotTests.test_renderer_writes_business_heatmaps_for_rho_first_user_count_axes -v`
Expected: FAIL because the renderer does not emit business-space plots.

- [ ] **Step 3: Implement business-space heatmap rendering**

```python
def _business_scene_value(
    rows: list[dict[str, str]],
    *,
    target_rho_bg: float,
    target_rho_pdb: float,
    pdb_ms: int,
    background_user_count: int,
    pdb_user_count: int,
    field_name: str,
) -> float:
    for row in rows:
        if (
            int(row["background_user_count"]) == background_user_count
            and int(row["pdb_user_count"]) == pdb_user_count
            and int(row["pdb_ms"]) == pdb_ms
            and math.isclose(float(row["target_rho_bg"]), target_rho_bg, rel_tol=0.0, abs_tol=1e-9)
            and math.isclose(float(row["target_rho_pdb"]), target_rho_pdb, rel_tol=0.0, abs_tol=1e-9)
        ):
            return float(row[field_name])
    return math.nan
```

```python
def _business_grid(
    rows: list[dict[str, str]],
    manifest: dict[str, object],
    *,
    field_name: str,
    title: str,
    output_path: Path,
) -> None:
    rho_bg_values = [float(value) for value in manifest["rho_bg_values"]]
    rho_pdb_values = [float(value) for value in manifest["rho_pdb_values"]]
    pdb_ms_values = [int(value) for value in manifest["pdb_ms_values"]]
    background_values = [int(value) for value in manifest["explicit_background_user_count_values"]]
    pdb_user_values = [int(value) for value in manifest["explicit_pdb_user_count_values"]]
    fig, axes = plt.subplots(
        len(rho_bg_values) * len(rho_pdb_values),
        len(pdb_ms_values),
        figsize=(4 * len(pdb_ms_values), 3.5 * len(rho_bg_values) * len(rho_pdb_values)),
        constrained_layout=True,
        squeeze=False,
    )
    row_index = 0
    for target_rho_bg in rho_bg_values:
        for target_rho_pdb in rho_pdb_values:
            for col_index, pdb_ms in enumerate(pdb_ms_values):
                ax = axes[row_index][col_index]
                matrix = [
                    [
                        _business_scene_value(
                            rows,
                            target_rho_bg=target_rho_bg,
                            target_rho_pdb=target_rho_pdb,
                            pdb_ms=pdb_ms,
                            background_user_count=background_user_count,
                            pdb_user_count=pdb_user_count,
                            field_name=field_name,
                        )
                        for background_user_count in background_values
                    ]
                    for pdb_user_count in pdb_user_values
                ]
                image = ax.imshow(matrix, aspect="auto", origin="lower")
                image.cmap.set_bad(color="#d9d9d9")
                ax.set_title(f"rho_bg={target_rho_bg:.3f} rho_pdb={target_rho_pdb:.3f} / PDB {pdb_ms} ms")
                ax.set_xticks(range(len(background_values)), labels=[str(value) for value in background_values])
                ax.set_yticks(range(len(pdb_user_values)), labels=[str(value) for value in pdb_user_values])
                ax.set_xlabel("background_user_count")
                ax.set_ylabel("pdb_user_count")
                fig.colorbar(image, ax=ax, shrink=0.75)
            row_index += 1
    fig.suptitle(title)
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
```

```python
if (
    str(manifest.get("scan_mode", "")) == "load_ratio"
    and "explicit_background_user_count_values" in manifest
    and "explicit_pdb_user_count_values" in manifest
):
    _business_grid(
        scene_rows,
        manifest,
        field_name="mean_delta_pdb_satisfaction_rate",
        title="Business-Space Mean Paired Delta PDB Satisfaction",
        output_path=output_dir / "business_delta_pdb_satisfaction.png",
    )
    _business_grid(
        scene_rows,
        manifest,
        field_name="mean_center_throughput_retention",
        title="Business-Space Mean Center Throughput Retention",
        output_path=output_dir / "business_center_throughput_retention.png",
    )
```

- [ ] **Step 4: Re-run the plot test and verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis_plots.SystematicAnalysisPlotTests.test_renderer_writes_business_heatmaps_for_rho_first_user_count_axes -v`
Expected: PASS

- [ ] **Step 5: Commit the plot changes**

```bash
git add scripts/render_systematic_simulation_analysis_plots.py tests/test_systematic_analysis_plots.py
git commit -m "feat: render business heatmaps for rho-first outputs"
```

### Task 5: Update summary-report wording for user-count-aware rho-first outputs

**Files:**
- Modify: `scripts/run_systematic_simulation_analysis.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing summary-report test**

```python
    def test_systematic_simulation_analysis_runner_writes_user_count_aware_rho_first_summary_report(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "out"
            config_path = repo_root / "configs" / "systematic_simulation_analysis_load_ratio_rho_first_user_count_axes.json"
            _write_nr_ul_main_table(Path(tmpdir), repo_root)
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["report"]["output_dir"] = str(output_dir)
            payload["systematic_analysis"]["repeat_count"] = 1
            local_config_path = Path(tmpdir) / "local.json"
            local_config_path.write_text(json.dumps(payload), encoding="utf-8")

            result = subprocess.run(
                ["python", "scripts/run_systematic_simulation_analysis.py", str(local_config_path)],
                cwd=repo_root,
                env={**os.environ, "PYTHONPATH": "src"},
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            report_text = (output_dir / "summary_report.md").read_text(encoding="utf-8")
            self.assertIn("`explicit_background_user_count_values = [32, 40, 48]`", report_text)
            self.assertIn("`explicit_pdb_user_count_values = [4, 8]`", report_text)
            self.assertIn("business-parameter heatmaps", report_text)
            self.assertIn("arrival_time < 10 s", report_text)
```

- [ ] **Step 2: Run the summary-report test and verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_writes_user_count_aware_rho_first_summary_report -v`
Expected: FAIL because the report does not mention the explicit user-count axes or business-space outputs.

- [ ] **Step 3: Update `_load_ratio_summary_report(...)` for the new manifest shape**

```python
if is_rho_first:
    lines = [
        "# Systematic Simulation Analysis",
        "",
        "## Wireless Environment and Realization Bank",
        ...,
        "## Load-Ratio Scan Matrix",
        "",
        f"- `scan_mode = {manifest['scan_mode']}`",
        f"- `rho_bg_values = {manifest['rho_bg_values']}`",
        f"- `rho_pdb_values = {manifest['rho_pdb_values']}`",
        f"- `pdb_ms_values = {manifest['pdb_ms_values']}`",
    ]
    if manifest.get("explicit_background_user_count_values") is not None:
        lines.append(
            f"- `explicit_background_user_count_values = {manifest['explicit_background_user_count_values']}`"
        )
    if manifest.get("explicit_pdb_user_count_values") is not None:
        lines.append(
            f"- `explicit_pdb_user_count_values = {manifest['explicit_pdb_user_count_values']}`"
        )
    lines.extend(
        [
            f"- `mapping_policy = {manifest['mapping_policy']}`",
            ...,
            "## Reporting Semantics",
            "",
            "- `scene_summary.csv` aggregates policy-paired results at each rho-first scene point.",
            "- Fixed-window KPI semantics remain: the main PDB satisfaction metric uses the 10 s reporting window and counts only arrivals with `arrival_time < 10 s` in the denominator.",
            "- When explicit user-count axes are present, complementary business-parameter heatmaps are rendered alongside rho-space heatmaps.",
        ]
    )
```

- [ ] **Step 4: Re-run the summary-report test and verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_writes_user_count_aware_rho_first_summary_report -v`
Expected: PASS

- [ ] **Step 5: Commit the report update**

```bash
git add scripts/run_systematic_simulation_analysis.py tests/test_cli.py
git commit -m "docs: report user-count-aware rho-first scans"
```

### Task 6: Verify reuse behavior with existing outputs

**Files:**
- Modify: `tests/test_cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing reuse test for overlapping concrete business tuples**

```python
    def test_user_count_aware_rho_first_scan_reuses_existing_matching_scene_points(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            reused_dir = Path(tmp) / "reused-load-ratio"
            reused_dir.mkdir(parents=True, exist_ok=True)
            _write_nr_ul_main_table(Path(tmp), repo_root)
            (reused_dir / "raw_summaries.json").write_text(
                json.dumps(
                    [
                        {
                            "seed": 7,
                            "scenario_id": "bg40_pdb4_d50_k2.5_seed00_L01",
                            "policy": "tail_append",
                            "summary": {"edge_pdb_satisfaction_rate": 0.75},
                        },
                        {
                            "seed": 7,
                            "scenario_id": "bg40_pdb4_d50_k2.5_seed00_L01",
                            "policy": "hopeless_tail_append",
                            "summary": {"edge_pdb_satisfaction_rate": 0.79},
                        },
                    ]
                ),
                encoding="utf-8",
            )
            (reused_dir / "per_run_rows.csv").write_text(
                "seed,scenario_id,policy,case_label,background_user_count,pdb_user_count,pdb_ms,pdb_packet_kb,background_packet_kb,background_period_ms,edge_pdb_satisfaction_rate,center_agg_rate_bps,center_avg_rate_bps,prb_utilization,center_prb_share,edge_prb_share,pdb_arrivals_in_window,pdb_violation_rate,target_edge_completion_delay_ms,target_edge_queue_wait_ms,target_edge_service_time_ms,edge_backlog_bits\n"
                "7,bg40_pdb4_d50_k2.5_seed00_L01,tail_append,L01,40,4,50,2.5,2.0,25.0,0.75,1000.0,25.0,0.9,0.7,0.3,4.0,0.25,70.0,40.0,30.0,0.0\n"
                "7,bg40_pdb4_d50_k2.5_seed00_L01,hopeless_tail_append,L01,40,4,50,2.5,2.0,25.0,0.79,990.0,24.75,0.9,0.69,0.31,4.0,0.21,66.0,36.0,30.0,0.0\n",
                encoding="utf-8",
            )
            (reused_dir / "paired_rows.csv").write_text(
                "seed,case_label,background_user_count,pdb_user_count,pdb_ms,pdb_packet_kb,background_packet_kb,background_period_ms,baseline_edge_pdb_satisfaction_rate,proposed_edge_pdb_satisfaction_rate,delta_pdb_satisfaction_rate,center_throughput_retention,delta_prb_utilization,delta_center_prb_share,delta_edge_prb_share\n"
                "7,L01,40,4,50,2.5,2.0,25.0,0.75,0.79,0.04,0.99,0.0,-0.01,0.01\n",
                encoding="utf-8",
            )
            config_path = Path(tmp) / "load_ratio_reuse.json"
            output_dir = Path(tmp) / "load-ratio-reuse-output"
            payload = json.loads(
                (repo_root / "configs" / "systematic_simulation_analysis_load_ratio_rho_first_hopeless_tail_append.json").read_text(encoding="utf-8")
            )
            payload["report"]["output_dir"] = str(output_dir)
            payload["systematic_analysis"]["rho_bg_values"] = [0.388]
            payload["systematic_analysis"]["rho_pdb_values"] = [0.183]
            payload["systematic_analysis"]["pdb_ms_values"] = [50]
            payload["systematic_analysis"]["background_user_count_values"] = [40, 48]
            payload["systematic_analysis"]["pdb_user_count_values"] = [4]
            payload["systematic_analysis"]["repeat_count"] = 1
            payload["systematic_analysis"]["reuse_output_dirs"] = [str(reused_dir)]
            payload["systematic_analysis"]["merged_output_dir"] = str(output_dir)
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
            manifest = json.loads((output_dir / "experiment_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["reused_scene_point_count"], 1)
            self.assertEqual(manifest["new_scene_point_count"], 1)
            self.assertEqual(manifest["final_scene_point_count"], 2)
            with (output_dir / "scene_summary.csv").open("r", encoding="utf-8", newline="") as handle:
                scene_rows = list(csv.DictReader(handle))
            self.assertEqual(len(scene_rows), 2)
```

- [ ] **Step 2: Run the reuse test and verify it fails if the new scene keys do not merge correctly**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_user_count_aware_rho_first_scan_reuses_existing_matching_scene_points -v`
Expected: FAIL if the new config shape breaks reuse accounting or scene-key matching.

- [ ] **Step 3: Reuse the existing concrete scene-key merge path without changing key semantics**

```python
# keep scene_key(...) unchanged for load-ratio rows
return (
    int(row["background_user_count"]),
    int(row["pdb_user_count"]),
    int(row["pdb_ms"]),
    float(row["pdb_packet_kb"]),
    float(row["background_packet_kb"]),
    int(row["background_period_ms"]),
)
```

```python
manifest = {
    ...,
    "reuse_output_dirs": reuse_output_dirs,
    "reused_scene_point_count": len(reused_scene_keys),
    "new_scene_point_count": len(cases_to_run),
    "final_scene_point_count": len(scene_rows),
}
```

- [ ] **Step 4: Re-run the reuse test and verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_user_count_aware_rho_first_scan_reuses_existing_matching_scene_points -v`
Expected: PASS

- [ ] **Step 5: Commit the reuse verification coverage**

```bash
git add tests/test_cli.py
git commit -m "test: cover reuse for user-count-aware rho-first scans"
```

### Task 7: Run focused verification and then the first user-count-aware scan with reuse

**Files:**
- No code changes

- [ ] **Step 1: Run the focused test bundle**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis tests.test_systematic_analysis_plots tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_supports_rho_first_user_count_axes_config tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_writes_user_count_aware_rho_first_summary_report tests.test_cli.CliSmokeTests.test_user_count_aware_rho_first_scan_reuses_existing_matching_scene_points -v`
Expected: PASS

- [ ] **Step 2: Run the renderer smoke pass on the existing hopeless-tail output**

Run: `PYTHONPATH=src python scripts/render_systematic_simulation_analysis_plots.py outputs/systematic_simulation_analysis_load_ratio_rho_first_hopeless_tail_append`
Expected: PASS and, for current outputs without explicit user-count axes, the existing rho-space plots remain unchanged.

- [ ] **Step 3: Run the new user-count-aware scan with reuse enabled**

Run: `PYTHONPATH=src python scripts/run_systematic_simulation_analysis.py configs/systematic_simulation_analysis_load_ratio_rho_first_user_count_axes.json outputs/systematic_simulation_analysis_load_ratio_rho_first outputs/systematic_simulation_analysis_load_ratio_rho_first_hopeless_tail_append`
Expected: writes a new output directory, reuses any overlapping concrete scene tuples from the provided directories, and only simulates the remaining new points.

- [ ] **Step 4: Render plots for the new output**

Run: `PYTHONPATH=src python scripts/render_systematic_simulation_analysis_plots.py outputs/systematic_simulation_analysis_load_ratio_rho_first_user_count_axes`
Expected: PASS and writes both rho-space and business-space heatmaps.

- [ ] **Step 5: Commit final implementation and checked-in config**

```bash
git add src/scheduling_sim/systematic_analysis.py scripts/run_systematic_simulation_analysis.py scripts/render_systematic_simulation_analysis_plots.py configs/systematic_simulation_analysis_load_ratio_rho_first_user_count_axes.json tests/test_systematic_analysis.py tests/test_systematic_analysis_plots.py tests/test_cli.py docs/superpowers/specs/2026-06-16-rho-first-user-count-aware-business-heatmap-design.md
git commit -m "feat: add user-count-aware rho-first business heatmaps"
```
