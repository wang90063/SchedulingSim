# Systematic Simulation Analysis Design

## Goal

Define the first version of `option 1: 系统性分析` for the periodic-`PDB`, fixed-window uplink simulator.

This analysis is not a broad wireless sweep. It is a controlled business-load sweep on top of a fixed wireless foundation. The primary questions are:

1. Under fixed wireless conditions, where does `proposed` improve `PDB` satisfaction over `baseline`?
2. Is that `PDB` gain achieved with acceptable `center` throughput cost?
3. Does `proposed` push out the system's feasible `PDB` load boundary?

## Scope

This design covers:

- scenario construction for `option 1`
- parameter matrix for the systematic scan
- fixed-window reporting semantics
- output tables and figures
- final report structure

This design does **not** include:

- scanning wireless parameters such as total `PRB`, candidate count, power, or cell radius
- changing the periodic fixed-window simulator semantics already defined in the `2026-06-10-periodic-pdb-fixed-window-design.md` spec
- the separate `option 2: 场景分析`

## Recommended Analysis Structure

Three approaches were considered:

1. flat full-grid reporting
2. layered panoramic scan
3. panoramic scan plus heavier statistical modeling

Use **approach 2**.

The analysis should run the full selected grid, then organize results in four layers:

1. overview layer: where `PDB` gain appears
2. cost layer: what `center` throughput cost is paid
3. boundary layer: whether feasible load regions expand
4. typical-case layer: why those outcomes happen

This keeps the experiment comprehensive without turning the report into a long list of raw tables.

## Fixed Wireless Foundation

### Wireless Parameters

`option 1` must keep the wireless-side parameters fixed to the document defaults:

- slot duration: `1 ms`
- frame pattern: `DSUUU`
- total uplink `PRB` per `U-slot`: `273`
- half-polling candidate count: `16`
- channel model: `UMA`
- cell radius: `500 m`
- `UE` transmit power: `23 dBm`

These are fixed conditions, not sweep dimensions.

### Class-Controlled SINR Design

The `SINR` structure is part of the scenario definition and must be controlled explicitly.

- `PDB` users belong to the `poor` class only
- background users belong to the `medium` and `good` classes only
- the scenario generator must control distance and large-scale conditions so resulting users fall into the intended class ranges

Target class ranges:

- poor: `-5 ~ 0 dB`
- medium: `0 ~ 10 dB`
- good: `10 ~ 20 dB`

The report must state clearly that these `SINR` ranges are induced jointly by geometry, path loss, power, and interference assumptions, not by arbitrary direct assignment.

### Realization Bank

To avoid mixing business-parameter effects with wireless-randomness effects, the analysis must use a pre-generated, reusable realization bank.

For each `seed`, generate one `64 UE` mother scenario with fixed user pools:

- `24` medium background candidates
- `24` good background candidates
- `16` poor `PDB` candidates

Each mother scenario stores at minimum:

- `ue_id`
- user class label: `medium`, `good`, `poor`
- distance to base station
- large-scale wireless state needed to reproduce the initial `SINR` realization
- any seed or cached state needed to reproduce slot evolution deterministically

The generator must validate that generated users fall into the intended class `SINR` ranges before the bank is accepted.

### Cross-Scenario Reuse

All business sweeps reuse the same realization bank.

Within one `seed`:

- `background_user_count = 24` uses a deterministic subset of the background pool
- `background_user_count = 36` uses a superset of the `24` case
- `background_user_count = 48` uses the full background pool
- `pdb_user_count = 4` uses a deterministic subset of the `PDB` pool
- `pdb_user_count = 10` uses a superset of the `4` case
- `pdb_user_count = 16` uses the full `PDB` pool

This nested slicing is required so load comparisons change traffic pressure rather than user geography.

### Algorithm Pairing

For any given scene point:

- `baseline` and `proposed` must run on the exact same realization-bank entry
- both algorithms must share the same geometry, class composition, and random wireless evolution inputs

This is a paired comparison, not two independent Monte Carlo experiments.

## Business Model for Systematic Analysis

### Background Traffic

The first systematic-analysis version fixes background traffic to:

- packet period: `10 ms`
- packet size: `2 KB`
- user distribution: medium and good classes only

Background packet size is intentionally fixed in this first pass to keep the panoramic scan tractable.

### PDB Traffic

The `PDB` business sweep uses:

- `PDB user count`: `[4, 10, 16]`
- `PDB`: `[100, 300, 500] ms`
- packet size: `[50, 150, 300] KB`
- user distribution: poor class only
- packet generation period: exactly equal to the configured `PDB`

Periodic packet generation follows the periodic fixed-window design:

- arrivals are defined in wall-clock milliseconds
- the reporting window is fixed to `10 s`
- for the first version, only packets with `arrival_time < 10 s` belong to the `PDB` satisfaction denominator

### Background Load Sweep

Background load is represented by background-user count:

- `background_user_count`: `[24, 36, 48]`

This yields a `3 x 3` load plane:

- horizontal load dimension: background pressure
- vertical load dimension: `PDB` pressure

The analysis no longer uses `total_user_count` as a primary scan axis.

## Experiment Matrix

The first panoramic grid is:

- `background_user_count`: `3` values
- `pdb_user_count`: `3` values
- `pdb_ms`: `3` values
- `pdb_packet_kb`: `3` values

Total scene points:

- `3 x 3 x 3 x 3 = 81`

Repeat policy:

- `10` paired seeds
- `2` algorithms: `baseline`, `proposed`

Total runs:

- `81 x 10 x 2 = 1620`

This is the intended first version. Expanding background packet size back into the sweep is deferred until this version is stable and interpretable.

## Reporting Semantics

### Main KPI

The primary KPI is:

- `edge_pdb_satisfaction_rate`

Definition:

- reporting window: fixed `10 s`
- denominator: all `PDB` packets with `arrival_time < 10 s`
- numerator: those packets that satisfy `completion_time <= arrival_time + pdb_ms`

The analysis must use the periodic fixed-window semantics consistently. It must not revert to target-packet-only or "until last target packet completes" semantics for the main panoramic conclusions.

### Cost KPI

The main cost KPI is:

- `center_throughput_retention = proposed_center_agg_rate_bps / baseline_center_agg_rate_bps`

This should be the main secondary figure because it normalizes background cost across different background-user loads better than absolute throughput alone.

Keep the absolute background throughput fields as supporting data:

- `center_agg_rate_bps`
- `center_avg_rate_bps`

### Resource KPIs

Keep these as explanatory resource metrics:

- `prb_utilization`
- `center_prb_share`
- `edge_prb_share`

These help distinguish "better scheduling efficiency" from "purely shifting resources away from background users."

### Supporting Explanation Metrics

Keep the following for typical-case interpretation, not as panoramic headline metrics:

- `pdb_arrivals_in_window`
- `pdb_violation_rate`
- `target_edge_completion_delay_ms`
- `target_edge_queue_wait_ms`
- `target_edge_service_time_ms`
- `edge_backlog_bits`

## Data Outputs

### Per-Run Row

Each run should produce one row containing at least:

- `seed`
- `scenario_id`
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
- realization metadata needed for traceability

### Paired Comparison Row

For each paired `seed` and scene point, derive:

- `delta_pdb_satisfaction_rate = proposed - baseline`
- `center_throughput_retention`
- `delta_prb_utilization = proposed - baseline`
- `delta_center_prb_share`
- `delta_edge_prb_share`

All primary statistical comparisons should be based on these paired rows.

### Aggregated Row

For each scene point aggregated across `10` seeds, report at minimum:

- mean paired `PDB` gain
- standard deviation of paired `PDB` gain
- `95%` confidence interval for paired `PDB` gain
- mean `center_throughput_retention`
- `95%` confidence interval for `center_throughput_retention`

## Figure Plan

### Overview Figure

Make a `3 x 3` small-multiple matrix:

- rows: `pdb_ms = [100, 300, 500]`
- columns: `pdb_packet_kb = [50, 150, 300]`
- inside each subplot:
  - x-axis: `background_user_count = [24, 36, 48]`
  - y-axis: `pdb_user_count = [4, 10, 16]`
  - color: mean paired `delta_pdb_satisfaction_rate`

This is the first main figure.

### Cost Figure

Mirror the overview figure layout, but color by:

- `center_throughput_retention`

This should immediately follow the overview figure so readers can compare gain and cost region by region.

### Boundary Figure

Use the same `3 x 3` panel layout and define feasible regions using at least:

- `95%` `PDB` satisfaction as the primary threshold
- `90%` `PDB` satisfaction as the secondary threshold

For each panel, compare feasible regions or contours for:

- `baseline`
- `proposed`

This figure answers whether `proposed` expands the feasible load region.

### Typical-Case Figures

Select `3 ~ 5` representative scene points:

1. easy region: both algorithms satisfy `PDB`
2. critical region: `proposed` shows the largest useful gain
3. overloaded region: both degrade, but `proposed` may still partially help
4. high-cost region: among scene points with positive `PDB` gain, choose the one with the lowest `center_throughput_retention`

For these points, use supporting metrics such as queue wait, completion delay, backlog, and `PRB` shares to explain why the panoramic patterns occur.

## Region Partitioning for Analysis

After the panoramic scan, partition the scene points by `baseline` `PDB` satisfaction:

- feasible region: `baseline >= 95%`
- critical region: `50% <= baseline < 95%`
- overloaded region: `baseline < 50%`

For each region, summarize:

- scene-point share
- `proposed` win rate
- mean paired `PDB` gain
- mean `center_throughput_retention`
- mean `PRB` deltas

This converts raw panoramic plots into compact system-level conclusions.

## Capacity-Oriented Boundary Metrics

To support the "system capacity" narrative, define two boundary summaries at a chosen `PDB` satisfaction threshold, with `95%` as the default:

1. at fixed background-user count, the maximum `pdb_user_count` that still satisfies the threshold
2. at fixed `pdb_user_count`, the maximum background-user count that still satisfies the threshold

Derived comparison metrics:

- `capacity_gain_pdb_users = proposed_max_pdb_users - baseline_max_pdb_users`
- `capacity_gain_background_users = proposed_max_background_users - baseline_max_background_users`

These should be reported in the boundary-analysis section, not as the first headline figure.

## Final Report Structure

The `option 1` systematic-analysis chapter should be organized as:

1. wireless environment and realization-bank construction
2. business scan matrix
3. reporting semantics
4. panoramic `PDB` gain overview
5. background-throughput and resource-cost analysis
6. feasible-boundary expansion analysis
7. representative-case mechanism analysis
8. summary

The summary should answer, in order:

1. where `proposed` helps
2. what background cost it causes
3. whether it materially expands feasible `PDB` load

## Non-Goals for Version 1

Do not add these to the first implementation:

- sweeping background packet size again
- sweeping wireless parameters
- heavier regression or ANOVA-style statistical modeling
- mixing this panoramic analysis with the separate `option 2` scene-analysis chapter

Those can be follow-up extensions once the first panoramic pipeline is stable.
