# Systematic Simulation Analysis

## Wireless Environment and Realization Bank

- reference_config: `configs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_batch_pdb050_bg200.json`
- scene_bank_counts: `{'medium': 24, 'good': 24, 'poor': 16}`
- realization_bank_total_users: `64`
- repeat_count_per_scene_point: `5`

## Load-Ratio Scan Matrix

- `scan_mode = load_ratio`
- `rho_bg_values = [0.2]`
- `rho_pdb_values = [0.3, 0.4, 0.45]`
- `pdb_ms_values = [50]`
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
- Proposed improves `11` points, ties `0` points, and regresses `7` points.
- Mean scene-level delta PDB satisfaction: `0.001`
- Mean scene-level center throughput retention: `1.004`

| case_label | target_rho_bg | target_rho_pdb | actual_rho_bg | actual_rho_pdb | prb_share_pdb | background_mapping_policy | pdb_mapping_policy | background_user_count | background_packet_kb | background_period_ms | pdb_user_count | pdb_ms | pdb_packet_kb | baseline_pdb_satisfaction | proposed_pdb_satisfaction | delta_pdb_satisfaction | center_retention |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L01 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 50 | 4.1 | 0.831 | 0.832 | 0.001 | 1.000 |
| L02 | 0.200 | 0.300 | 0.200 | 0.293 | 0.594 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 50 | 2 | 0.893 | 0.897 | 0.004 | 1.000 |
| L03 | 0.200 | 0.400 | 0.200 | 0.403 | 0.668 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 50 | 5.5 | 0.589 | 0.590 | 0.000 | 0.998 |
| L04 | 0.200 | 0.400 | 0.200 | 0.395 | 0.664 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 50 | 2.7 | 0.525 | 0.530 | 0.005 | 0.998 |
| L05 | 0.200 | 0.450 | 0.200 | 0.447 | 0.691 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 50 | 6.1 | 0.504 | 0.509 | 0.005 | 1.008 |
| L06 | 0.200 | 0.450 | 0.200 | 0.454 | 0.694 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 50 | 3.1 | 0.316 | 0.325 | 0.009 | 1.000 |
| L07 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 50 | 4.1 | 0.794 | 0.792 | -0.002 | 1.000 |
| L08 | 0.200 | 0.300 | 0.200 | 0.293 | 0.594 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 50 | 2 | 0.819 | 0.817 | -0.001 | 1.000 |
| L09 | 0.200 | 0.400 | 0.200 | 0.403 | 0.668 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 50 | 5.5 | 0.536 | 0.532 | -0.005 | 1.001 |
| L10 | 0.200 | 0.400 | 0.200 | 0.395 | 0.664 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 50 | 2.7 | 0.477 | 0.476 | -0.002 | 1.000 |
| L11 | 0.200 | 0.450 | 0.200 | 0.447 | 0.691 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 50 | 6.1 | 0.476 | 0.478 | 0.003 | 1.032 |
| L12 | 0.200 | 0.450 | 0.200 | 0.454 | 0.694 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 50 | 3.1 | 0.270 | 0.275 | 0.005 | 1.004 |
| L13 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 50 | 4.1 | 0.761 | 0.765 | 0.004 | 1.000 |
| L14 | 0.200 | 0.300 | 0.200 | 0.293 | 0.594 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 50 | 2 | 0.750 | 0.742 | -0.008 | 1.000 |
| L15 | 0.200 | 0.400 | 0.200 | 0.403 | 0.668 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 50 | 5.5 | 0.504 | 0.501 | -0.003 | 1.002 |
| L16 | 0.200 | 0.400 | 0.200 | 0.395 | 0.664 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 50 | 2.7 | 0.428 | 0.428 | 0.000 | 0.999 |
| L17 | 0.200 | 0.450 | 0.200 | 0.447 | 0.691 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 50 | 6.1 | 0.457 | 0.459 | 0.002 | 1.031 |
| L18 | 0.200 | 0.450 | 0.200 | 0.454 | 0.694 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 50 | 3.1 | 0.245 | 0.242 | -0.003 | 1.004 |

## Insight Summary

- Positive-gain scene points: `11`
- Zero-gain scene points: `0`
- Negative-gain scene points: `7`
- Best gain scene: `case=`L06` rho_bg=`0.200` rho_pdb=`0.454` prb_share_pdb=`0.694` pdb_ms=`50` pdb_packet_kb=`3.1``
- Lowest center-retention scene: `case=`L04` rho_bg=`0.200` rho_pdb=`0.395` prb_share_pdb=`0.664` pdb_ms=`50` pdb_packet_kb=`2.7``

## Background Cost and Resource Analysis

- Mean center throughput retention across scene points: `1.004`
- Mean PRB utilization delta (proposed - baseline): `0.000`
- Mean center PRB share delta: `0.001`
- Mean edge PRB share delta: `-0.001`

| Region | Scene Points | Share | Win Rate | Mean Delta PDB Satisfaction | Mean Center Retention | Mean Delta PRB Utilization |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| critical | 11 | 0.61 | 0.55 | 0.000 | 1.001 | 0.000 |
| overloaded | 7 | 0.39 | 0.71 | 0.002 | 1.010 | -0.000 |

## Feasible Boundary Snapshot

- Boundary feasibility snapshots remain available at the 95% and 90% thresholds.

| Threshold | Baseline Feasible Points | Proposed Feasible Points | Expanded Points | Regressed Points |
| ---: | ---: | ---: | ---: | ---: |
| 0.95 | 0 | 0 | 0 | 0 |
| 0.90 | 0 | 0 | 0 | 0 |

## Representative Case Mechanism Analysis

- Representative cases selected: `2`
- Representative detail rows: `4`
- `typical_case_details.csv` is the renderer-facing mechanism table for these cases.

| Label | target_rho_bg | target_rho_pdb | actual_rho_bg | actual_rho_pdb | prb_share_pdb | pdb_ms | pdb_packet_kb | Mean Delta PDB Satisfaction | Center Retention |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| critical | 0.200 | 0.400 | 0.200 | 0.395 | 0.664 | 50 | 2.7 | 0.005 | 0.998 |
| overloaded | 0.200 | 0.450 | 0.200 | 0.454 | 0.694 | 50 | 3.1 | 0.009 | 1.000 |

| Label | baseline_satisfaction | proposed_satisfaction | baseline_queue_ms | proposed_queue_ms | baseline_completion_ms | proposed_completion_ms | baseline_center_rate_bps | proposed_center_rate_bps | center_retention |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| critical | 0.525 | 0.530 | 19.6 | 19.6 | 21.4 | 21.4 | 13028506.5 | 13007457.1 | 0.998 |
| overloaded | 0.316 | 0.325 | 20.0 | 20.2 | 22.4 | 22.4 | 12448796.7 | 12451216.2 | 1.000 |

## Summary

- Proposed improves `11/18` load-ratio scene points; best gain is `0.009`.
- Mean center throughput retention is `1.004`; worst retained point is `0.998`.
- Boundary expansion adds `0` points at 95% and `0` points at 90%.