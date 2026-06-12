# Systematic Analysis Expanded Sweep and Merge Design

## Goal

Extend the existing `option 1` systematic-analysis experiment into a larger one-step sweep that:

1. keeps the same four business-scan dimensions
2. reuses already completed `option 1` scene points instead of rerunning them
3. runs only the newly added scene points
4. merges old and new rows into one canonical combined result directory

The purpose of this follow-up is to enlarge the scan toward lighter business-load combinations while preserving the current wireless foundation and the current `baseline` versus `hopeless_front_insert` comparison.

## Background

The current canonical output directory is:

- `outputs/systematic_simulation_analysis_option1`

Its scan matrix is:

- `background_user_count = [24, 36, 48]`
- `pdb_user_count = [4, 10, 16]`
- `pdb_ms = [100, 300, 500]`
- `pdb_packet_kb = [50, 150, 300]`
- `repeat_count = 10`

That run produced `81` scene points and already exported the raw rows needed for reuse:

- `per_run_rows.csv`
- `paired_rows.csv`
- `scene_summary.csv`
- `experiment_manifest.json`

Analysis of the finished run showed that all `81/81` scene points sit in the overloaded region, so the next experiment should enlarge the scan toward lighter load while still keeping total users at or above `32`.

## Design Constraints

This expanded sweep must satisfy all of the following:

1. keep the same four business dimensions:
   - `background_user_count`
   - `pdb_user_count`
   - `pdb_ms`
   - `pdb_packet_kb`
2. keep `repeat_count = 10`
3. keep the same wireless environment, realization-bank construction, and policy comparison semantics
4. keep total users constrained by:
   - `background_user_count + pdb_user_count >= 32`
5. reuse any already completed scene point from `outputs/systematic_simulation_analysis_option1`
6. produce one final merged output directory rather than separate analyst-facing final reports

## Recommended Scan Matrix

Use this expanded target matrix:

- `background_user_count_values = [16, 24, 32, 36, 40, 48]`
- `pdb_user_count_values = [4, 8, 10, 12, 16]`
- `pdb_ms_values = [100, 200, 300, 500, 600]`
- `pdb_packet_kb_values = [20, 30, 40, 50, 70, 100, 150, 300]`
- `repeat_count = 10`

Apply one combination filter before execution:

- keep only scene points where `background_user_count + pdb_user_count >= 32`

This yields:

- `25` valid `(background_user_count, pdb_user_count)` pairs
- `1000` total scene points after expanding over `pdb_ms` and `pdb_packet_kb`

## Reuse Plan

The old `option 1` matrix is a strict subset of the new matrix for these values:

- `background_user_count in [24, 36, 48]`
- `pdb_user_count in [4, 10, 16]`
- `pdb_ms in [100, 300, 500]`
- `pdb_packet_kb in [50, 150, 300]`

Therefore:

- reusable old scene points: `72`
- newly required scene points: `928`

The new workflow should not rerun those `72` old points. It should load the old raw rows directly and only simulate the remaining `928` scene points.

## Output Model

Use three output layers.

### Layer 1: Existing Canonical Historical Run

Keep the existing completed run unchanged:

- `outputs/systematic_simulation_analysis_option1`

This directory remains the immutable source of reusable rows.

### Layer 2: New Incremental Sweep Output

Write newly simulated points into a dedicated incremental directory:

- `outputs/systematic_simulation_analysis_option1_expanded_incremental`

This directory should contain the same raw export structure as a normal systematic-analysis run, but only for the newly added scene points.

### Layer 3: Final Combined Canonical Output

After the incremental run finishes, merge the old and new raw rows and regenerate one combined canonical analyst-facing directory:

- `outputs/systematic_simulation_analysis_option1_expanded`

This merged directory should contain:

- merged `per_run_rows.csv`
- merged `paired_rows.csv`
- merged `raw_summaries.json` if practical
- regenerated `scene_summary.csv`
- regenerated `region_summary.csv`
- regenerated `capacity_summary_95.csv`
- regenerated `capacity_summary_90.csv`
- regenerated `boundary_feasibility_95.csv`
- regenerated `boundary_feasibility_90.csv`
- regenerated `typical_case_candidates.csv`
- regenerated `typical_case_details.csv`
- regenerated `summary_report.md`
- regenerated figures
- a merged `experiment_manifest.json`

The final report and figures should be generated only from the merged rows, not by stitching together already-aggregated scene summaries.

## Merge Semantics

The merge must happen at raw-row level, not at scene-summary level.

### Raw rows to merge

Merge these files:

- old `per_run_rows.csv` + new `per_run_rows.csv`
- old `paired_rows.csv` + new `paired_rows.csv`

If `raw_summaries.json` is preserved, it should also be concatenated consistently. If that turns out to be operationally awkward, it may be omitted from the final merged directory as long as the CSV raw rows remain complete.

### Why raw-row merge is required

The downstream outputs derive from:

- grouped scene aggregation
- region partitioning
- capacity-boundary feasibility
- representative-case selection

Those depend on the full scene universe. Merging already-aggregated `scene_summary.csv` files would be brittle and would duplicate aggregation logic incorrectly if manifests or selection heuristics change.

## Manifest Semantics

The merged `experiment_manifest.json` should explicitly declare that it is a combined experiment artifact.

It should include at least:

- the expanded target value lists
- the total-user filter rule
- `repeat_count = 10`
- `baseline_policy = tail_append`
- `ours_policy = hopeless_front_insert`
- the source directories used in the merge:
  - `outputs/systematic_simulation_analysis_option1`
  - `outputs/systematic_simulation_analysis_option1_expanded_incremental`
- reusable scene-point count: `72`
- newly simulated scene-point count: `928`
- final combined scene-point count: `1000`

## Execution Flow

The recommended implementation flow is:

1. define the expanded target matrix and the total-user filter
2. enumerate all target scene points
3. load the old canonical raw rows and identify already covered scene keys
4. derive the missing scene-key set
5. run simulation only for the missing scene points into the incremental directory
6. merge old and new raw rows
7. regenerate all aggregated tables from merged rows
8. render all final figures from the regenerated merged tables
9. write the final combined report and manifest

## Scene-Key Definition

A scene point is uniquely identified by:

- `background_user_count`
- `pdb_user_count`
- `pdb_ms`
- `pdb_packet_kb`

Coverage detection should be based on that four-field scene key.

The old run uses `repeat_count = 10`, so if a scene key is present in the old run, it should be treated as fully covered and skipped entirely in the new incremental sweep.

## Non-Goals

This expansion pass does not:

- change simulator traffic semantics
- change `hopeless_front_insert` logic
- introduce new wireless dimensions
- resample or replace the existing `option 1` reused points
- recompute the historical run from scratch

## Risks and Tradeoffs

### Risk 1: Still mostly overloaded

Even with lighter business combinations, this matrix may still spend much of its area in overloaded territory because the fixed background traffic is heavy under the current wireless configuration.

This is acceptable for this pass. The goal is to enlarge the search on the same four business dimensions while keeping total users at or above `32`, not to redesign the wireless model.

### Risk 2: Merge complexity

The incremental-plus-merge flow is more complex than a single rerun. That complexity is justified because it avoids discarding a completed `81 x 10 x 2` historical run and preserves exact comparability for those already-finished points.

### Risk 3: Final directory ambiguity

If the incremental directory is treated as analyst-facing, readers may confuse it with the final combined result. To avoid that, only `outputs/systematic_simulation_analysis_option1_expanded` should be treated as the final reporting directory.

## Success Criteria

The expanded effort is successful if all of the following are true:

1. the old `option 1` run is reused without rerunning its covered scene points
2. only the missing `928` expanded scene points are newly simulated
3. the final combined directory contains `1000` merged scene points
4. all downstream tables and figures are regenerated from merged raw rows
5. the final report clearly reflects the expanded matrix rather than the old `81`-point matrix

## Final Recommendation

Proceed with an incremental expansion rather than a full rerun.

This preserves completed work, keeps exact comparability for the already-run subset, and produces one merged canonical output directory that can replace the smaller first-pass result for analysis purposes.
