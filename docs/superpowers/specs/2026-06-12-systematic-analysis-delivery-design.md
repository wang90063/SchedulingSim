# Systematic Analysis Delivery Completion Design

## Goal

Close the delivery gap between the implemented `option 1` systematic-analysis pipeline and the intended deliverables in `2026-06-11-systematic-simulation-analysis-design.md`.

This follow-up does not redesign the experiment matrix or simulator semantics. It completes the missing output semantics and runs the formal first-pass experiment so `option 1` has one canonical result directory.

The concrete goals are:

1. make the boundary figure match the original feasible-region comparison intent
2. add representative-case mechanism figures instead of only exporting candidate rows
3. expand the summary report into the intended chapter structure
4. run the full `81 x 10 x 2 = 1620` reference experiment and render the final artifacts

## Background

The current codebase already contains the core `option 1` pipeline:

- reusable realization-bank generation
- nested business slicing
- paired `baseline/proposed` aggregation
- region summaries
- capacity summaries
- overview and cost heatmaps

However, the current delivery is still incomplete in three important ways:

1. the checked-in pipeline has not yet been run with the full reference config into its canonical output directory
2. the boundary figure currently shows capacity-gain bars instead of `baseline` versus `proposed` feasible regions
3. the report and representative-case outputs are still too thin relative to the original design intent

## Non-Goals

This completion pass does **not**:

- change the fixed wireless foundation
- change the `81`-point business grid
- change periodic fixed-window reporting semantics
- add new sweep dimensions
- introduce heavier statistical modeling

## Gap Statement

### Gap 1: Formal Experiment Output Missing

The checked-in reference config already defines the intended first-pass scan:

- `background_user_count = [24, 36, 48]`
- `pdb_user_count = [4, 10, 16]`
- `pdb_ms = [100, 300, 500]`
- `pdb_packet_kb = [50, 150, 300]`
- `repeat_count = 10`

But the canonical output directory does not yet exist. That means the implementation has been validated by smoke tests, but the actual first-pass experiment has not been delivered.

### Gap 2: Boundary Figure Semantics Too Weak

The original design asks for a boundary view that compares feasible regions for `baseline` and `proposed` at `95%` and `90%` satisfaction thresholds.

The current renderer only shows capacity-gain bars derived from boundary summaries. Those bars are useful supporting data, but they are not the primary feasible-region visualization the design asked for.

### Gap 3: Representative-Case Explanation Too Thin

The current runner selects representative scene points and writes `typical_case_candidates.csv`, but it does not yet produce representative-case mechanism figures.

The delivery should make the selected `easy`, `critical`, `overloaded`, and `high_cost` scenes interpretable through direct side-by-side mechanism metrics for `baseline` and `proposed`.

### Gap 4: Summary Report Structure Too Thin

The current `summary_report.md` gives a compact scan summary, but it does not yet follow the intended final chapter structure:

1. wireless environment and realization-bank construction
2. business scan matrix
3. reporting semantics
4. panoramic `PDB` gain overview
5. background-throughput and resource-cost analysis
6. feasible-boundary expansion analysis
7. representative-case mechanism analysis
8. summary

## Recommended Completion Strategy

Use a two-stage completion flow:

1. complete the missing delivery semantics in the existing runner and renderer
2. after those semantics are stable and tested, run the formal reference experiment once and render the canonical outputs

This avoids wasting time on a long full-grid run whose plots or report structure would need to be regenerated after code changes anyway.

## Data Model Additions

The current runner already computes enough aggregated information to support gain, cost, and boundary summaries. The missing piece is richer representative-case export.

Add one new output table:

- `typical_case_details.csv`

This table should contain one row per selected representative case and per policy, with at least:

- `case_label`
- `policy`
- `background_user_count`
- `pdb_user_count`
- `pdb_ms`
- `pdb_packet_kb`
- `edge_pdb_satisfaction_rate`
- `center_agg_rate_bps`
- `center_avg_rate_bps`
- `prb_utilization`
- `center_prb_share`
- `edge_prb_share`
- `pdb_arrivals_in_window`
- `pdb_violation_rate`
- `target_edge_completion_delay_ms`
- `target_edge_queue_wait_ms`
- `target_edge_service_time_ms`
- `edge_backlog_bits`

This table should be derived from existing per-run or aggregated data without introducing a second simulator path.

## Figure Plan

### Overview Figure

Keep the existing `3 x 3` panel layout:

- rows: `pdb_ms = [100, 300, 500]`
- columns: `pdb_packet_kb = [50, 150, 300]`
- x-axis inside each panel: `background_user_count = [24, 36, 48]`
- y-axis inside each panel: `pdb_user_count = [4, 10, 16]`
- color: mean paired `delta_pdb_satisfaction_rate`

This remains the first headline figure.

### Cost Figure

Keep the mirrored `3 x 3` panel layout:

- color: `mean_center_throughput_retention`

This remains the second headline figure.

### Boundary Figures

Replace the current capacity-gain bar interpretation as the primary boundary view.

For each threshold, render a `3 x 3` panel matrix:

- one figure for `95%`
- one figure for `90%`

Inside each panel:

- x-axis: `background_user_count`
- y-axis: `pdb_user_count`
- show whether each grid point is feasible under `baseline`
- show whether each grid point is feasible under `proposed`

The implementation may use either:

- overlaid contours, or
- side-by-side feasible masks inside the same panel

The key requirement is that a reader can directly see whether `proposed` expands the feasible region relative to `baseline`.

Capacity-summary tables remain useful supporting data and should still be written.

### Representative-Case Figures

For each selected representative case, render one compact policy-comparison figure.

Each figure should compare `baseline` and `proposed` on the mechanism metrics most relevant to explanation:

- `edge_pdb_satisfaction_rate`
- `target_edge_queue_wait_ms`
- `target_edge_service_time_ms`
- `target_edge_completion_delay_ms`
- `edge_backlog_bits`
- `prb_utilization`
- `center_prb_share`
- `edge_prb_share`
- `center_agg_rate_bps`

The intent is not to make visually elaborate figures. The intent is to make the selected case interpretable enough to support the mechanism section of the report.

## Report Structure

Expand `summary_report.md` into a proper final artifact with the following sections:

1. `Wireless Environment and Realization Bank`
2. `Business Scan Matrix`
3. `Reporting Semantics`
4. `Panoramic PDB Gain Overview`
5. `Background Cost and Resource Analysis`
6. `Feasible Boundary Expansion`
7. `Representative Case Mechanism Analysis`
8. `Summary`

The report should explicitly answer:

1. where `proposed` helps
2. what background cost it causes
3. whether it materially expands feasible `PDB` load

The report may stay concise, but it must follow this structure and reference the generated tables and figures coherently.

## Canonical Experiment Run

After code completion and focused verification, run the formal reference configuration:

`PYTHONPATH=src python scripts/run_systematic_simulation_analysis.py configs/systematic_simulation_analysis_option1.json`

Then render the figures:

`PYTHONPATH=src python scripts/render_systematic_simulation_analysis_plots.py outputs/systematic_simulation_analysis_option1`

The canonical output directory is:

- `outputs/systematic_simulation_analysis_option1`

This directory becomes the standard first-pass `option 1` result set.

## Output Acceptance Criteria

The completion is not done unless the canonical output directory contains the expected tables, report, and figures.

Required tables:

- `experiment_manifest.json`
- `raw_summaries.json`
- `per_run_rows.csv`
- `paired_rows.csv`
- `scene_summary.csv`
- `region_summary.csv`
- `capacity_summary_95.csv`
- `capacity_summary_90.csv`
- `typical_case_candidates.csv`
- `typical_case_details.csv`

Required report:

- `summary_report.md`

Required figures:

- `overview_delta_pdb_satisfaction.png`
- `center_throughput_retention.png`
- `capacity_boundary_95.png`
- `capacity_boundary_90.png`
- one representative-case figure per selected case label

Expected row counts for the formal reference experiment:

- `per_run_rows.csv`: `1620` data rows
- `paired_rows.csv`: `810` data rows
- `scene_summary.csv`: `81` data rows
- `capacity_summary_95.csv`: `54` data rows
- `capacity_summary_90.csv`: `54` data rows

`typical_case_candidates.csv` and `typical_case_details.csv` may contain fewer rows depending on deduplication among selected representative labels.

## Verification Strategy

Before the full experiment:

- extend unit coverage for new boundary and representative-case helpers
- extend CLI smoke coverage for the richer runner output and renderer output

After the full experiment:

- verify the canonical output directory exists
- verify the required files exist
- verify the required row counts match the reference matrix
- verify the report contains the intended major sections
- verify the representative-case figures were emitted

## Recommended Implementation Order

1. enrich representative-case export in the runner
2. upgrade the report structure
3. replace boundary plotting semantics
4. add representative-case mechanism plots
5. extend tests
6. run focused verification
7. run the full reference experiment
8. render final figures
9. verify final output directory contents and row counts

## Risks and Mitigations

### Long Runtime

The formal run is intentionally large. Do not shrink the reference config to make the run feel easier. Instead, treat it as a deliberate long-running batch step after code correctness is established.

### Plot Ambiguity

Boundary figures can become visually confusing if `baseline` and `proposed` overlays are not distinguishable. Prefer a simple and explicit visual encoding over a dense or decorative one.

### Representative-Case Drift

Representative cases must come from the already aggregated scene summaries and paired comparisons. Do not create a separate ad hoc selection path that can diverge from the main panoramic results.
