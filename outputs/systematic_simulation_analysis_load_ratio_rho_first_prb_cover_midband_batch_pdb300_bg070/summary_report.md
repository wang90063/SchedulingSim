# Systematic Simulation Analysis

## Wireless Environment and Realization Bank

- reference_config: `configs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_batch_pdb300_bg070.json`
- scene_bank_counts: `{'medium': 24, 'good': 24, 'poor': 16}`
- realization_bank_total_users: `64`
- repeat_count_per_scene_point: `5`

## Load-Ratio Scan Matrix

- `scan_mode = load_ratio`
- `rho_bg_values = [0.07]`
- `rho_pdb_values = [0.3, 0.4, 0.45]`
- `pdb_ms_values = [300]`
- `mapping_policy = {'background': {'kind': 'candidate_domain_solve_period', 'background_user_count_values': [32, 40, 48], 'background_packet_kb_values': [1.0, 1.5, 2.0], 'background_period_ms_range': [4.0, 400.0], 'anchor_background_user_count': 40, 'anchor_background_packet_kb': 2.0}, 'pdb': {'kind': 'candidate_domain_solve_packet', 'pdb_user_count_values': [4, 8], 'pdb_packet_kb_range': [0.1, 80.0], 'anchor_pdb_user_count': 4}}`
- `repeat_count = 5`
- Scene points evaluated: `18`
- Paired realization rows: `90`
- Policy runs executed: `180`

## Reporting Semantics

- `scene_summary.csv` aggregates policy-paired results at each rho-first scene point.
- Target `rho` values define the scan; actual `rho` values are recomputed after mapping and rounding.
- `PDB` timing shape remains a secondary axis, so equal target `rho_pdb` values can still be compared across different `pdb_ms` realizations.
- `background_mapping_policy` and `pdb_mapping_policy` record the candidate-domain solver used for each scene.
- capacity summaries are omitted for load-ratio outputs because the legacy feasible-range tables assume user-count axes rather than ratio coordinates.
- boundary_feasibility_files: `['boundary_feasibility_95.csv', 'boundary_feasibility_90.csv']`
- representative_case_files: `['typical_case_candidates.csv', 'typical_case_details.csv']`
- Aggregated scene points: `18`

## Panoramic PDB Gain Overview

- Scene points evaluated: `18`
- Proposed improves `0` points, ties `18` points, and regresses `0` points.
- Mean scene-level delta PDB satisfaction: `0.000`
- Mean scene-level center throughput retention: `1.000`

| case_label | target_rho_bg | target_rho_pdb | actual_rho_bg | actual_rho_pdb | prb_share_pdb | background_mapping_policy | pdb_mapping_policy | background_user_count | background_packet_kb | background_period_ms | pdb_user_count | pdb_ms | pdb_packet_kb | baseline_pdb_satisfaction | proposed_pdb_satisfaction | delta_pdb_satisfaction | center_retention |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L01 | 0.070 | 0.300 | 0.070 | 0.300 | 0.811 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 300 | 24.6 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.070 | 0.300 | 0.070 | 0.300 | 0.811 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 300 | 12.3 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.070 | 0.400 | 0.070 | 0.400 | 0.851 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 300 | 32.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.070 | 0.400 | 0.070 | 0.400 | 0.851 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 300 | 16.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L05 | 0.070 | 0.450 | 0.070 | 0.450 | 0.866 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 300 | 36.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L06 | 0.070 | 0.450 | 0.070 | 0.449 | 0.865 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 300 | 18.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.070 | 0.300 | 0.070 | 0.300 | 0.811 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 300 | 24.6 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.070 | 0.300 | 0.070 | 0.300 | 0.811 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 300 | 12.3 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.070 | 0.400 | 0.070 | 0.400 | 0.851 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 300 | 32.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.070 | 0.400 | 0.070 | 0.400 | 0.851 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 300 | 16.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L11 | 0.070 | 0.450 | 0.070 | 0.450 | 0.866 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 300 | 36.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L12 | 0.070 | 0.450 | 0.070 | 0.449 | 0.865 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 300 | 18.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.070 | 0.300 | 0.070 | 0.300 | 0.811 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 300 | 24.6 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.070 | 0.300 | 0.070 | 0.300 | 0.811 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 300 | 12.3 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.070 | 0.400 | 0.070 | 0.400 | 0.851 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 300 | 32.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.070 | 0.400 | 0.070 | 0.400 | 0.851 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 300 | 16.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L17 | 0.070 | 0.450 | 0.070 | 0.450 | 0.866 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 300 | 36.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L18 | 0.070 | 0.450 | 0.070 | 0.449 | 0.865 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 300 | 18.4 | 1.000 | 1.000 | 0.000 | 1.000 |

## Insight Summary

- Positive-gain scene points: `0`
- Zero-gain scene points: `18`
- Negative-gain scene points: `0`
- Best gain scene: `case=`L01` rho_bg=`0.070` rho_pdb=`0.300` prb_share_pdb=`0.811` pdb_ms=`300` pdb_packet_kb=`24.6``
- Lowest center-retention scene: `case=`L01` rho_bg=`0.070` rho_pdb=`0.300` prb_share_pdb=`0.811` pdb_ms=`300` pdb_packet_kb=`24.6``

## Background Cost and Resource Analysis

- Mean center throughput retention across scene points: `1.000`
- Mean PRB utilization delta (proposed - baseline): `0.000`
- Mean center PRB share delta: `-0.000`
- Mean edge PRB share delta: `0.000`

| Region | Scene Points | Share | Win Rate | Mean Delta PDB Satisfaction | Mean Center Retention | Mean Delta PRB Utilization |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| feasible | 18 | 1.00 | 0.00 | 0.000 | 1.000 | 0.000 |

## Feasible Boundary Snapshot

- Boundary feasibility snapshots remain available at the 95% and 90% thresholds.

| Threshold | Baseline Feasible Points | Proposed Feasible Points | Expanded Points | Regressed Points |
| ---: | ---: | ---: | ---: | ---: |
| 0.95 | 18 | 18 | 0 | 0 |
| 0.90 | 18 | 18 | 0 | 0 |

## Representative Case Mechanism Analysis

- Representative cases selected: `1`
- Representative detail rows: `2`
- `typical_case_details.csv` is the renderer-facing mechanism table for these cases.

| Label | target_rho_bg | target_rho_pdb | actual_rho_bg | actual_rho_pdb | prb_share_pdb | pdb_ms | pdb_packet_kb | Mean Delta PDB Satisfaction | Center Retention |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| easy | 0.070 | 0.300 | 0.070 | 0.300 | 0.811 | 300 | 24.6 | 0.000 | 1.000 |

| Label | baseline_satisfaction | proposed_satisfaction | baseline_queue_ms | proposed_queue_ms | baseline_completion_ms | proposed_completion_ms | baseline_center_rate_bps | proposed_center_rate_bps | center_retention |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| easy | 1.000 | 1.000 | 40.8 | 40.8 | 52.0 | 52.0 | 4710400.0 | 4710400.0 | 1.000 |

## Summary

- Proposed improves `0/18` load-ratio scene points; best gain is `0.000`.
- Mean center throughput retention is `1.000`; worst retained point is `1.000`.
- Boundary expansion adds `0` points at 95% and `0` points at 90%.