# Systematic Simulation Analysis

## Wireless Environment and Realization Bank

- reference_config: `configs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_batch_pdb100_bg200.json`
- scene_bank_counts: `{'medium': 24, 'good': 24, 'poor': 16}`
- realization_bank_total_users: `64`
- repeat_count_per_scene_point: `5`

## Load-Ratio Scan Matrix

- `scan_mode = load_ratio`
- `rho_bg_values = [0.2]`
- `rho_pdb_values = [0.3, 0.4, 0.45]`
- `pdb_ms_values = [100]`
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
- Proposed improves `9` points, ties `0` points, and regresses `9` points.
- Mean scene-level delta PDB satisfaction: `0.001`
- Mean scene-level center throughput retention: `1.004`

| case_label | target_rho_bg | target_rho_pdb | actual_rho_bg | actual_rho_pdb | prb_share_pdb | background_mapping_policy | pdb_mapping_policy | background_user_count | background_packet_kb | background_period_ms | pdb_user_count | pdb_ms | pdb_packet_kb | baseline_pdb_satisfaction | proposed_pdb_satisfaction | delta_pdb_satisfaction | center_retention |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L01 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 100 | 8.2 | 0.916 | 0.915 | -0.001 | 1.000 |
| L02 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 100 | 4.1 | 0.998 | 1.000 | 0.001 | 1.000 |
| L03 | 0.200 | 0.400 | 0.200 | 0.399 | 0.666 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 100 | 10.9 | 0.679 | 0.679 | 0.001 | 1.001 |
| L04 | 0.200 | 0.400 | 0.200 | 0.403 | 0.668 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 100 | 5.5 | 0.662 | 0.677 | 0.015 | 1.001 |
| L05 | 0.200 | 0.450 | 0.200 | 0.450 | 0.693 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 100 | 12.3 | 0.559 | 0.554 | -0.006 | 1.001 |
| L06 | 0.200 | 0.450 | 0.200 | 0.447 | 0.691 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 100 | 6.1 | 0.480 | 0.488 | 0.008 | 1.000 |
| L07 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 100 | 8.2 | 0.858 | 0.856 | -0.002 | 1.000 |
| L08 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 100 | 4.1 | 0.992 | 0.994 | 0.002 | 1.000 |
| L09 | 0.200 | 0.400 | 0.200 | 0.399 | 0.666 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 100 | 10.9 | 0.622 | 0.625 | 0.003 | 1.000 |
| L10 | 0.200 | 0.400 | 0.200 | 0.403 | 0.668 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 100 | 5.5 | 0.596 | 0.601 | 0.006 | 1.000 |
| L11 | 0.200 | 0.450 | 0.200 | 0.450 | 0.693 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 100 | 12.3 | 0.505 | 0.504 | -0.001 | 1.049 |
| L12 | 0.200 | 0.450 | 0.200 | 0.447 | 0.691 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 100 | 6.1 | 0.429 | 0.426 | -0.003 | 1.003 |
| L13 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 100 | 8.2 | 0.838 | 0.833 | -0.004 | 1.000 |
| L14 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 100 | 4.1 | 0.966 | 0.970 | 0.004 | 1.000 |
| L15 | 0.200 | 0.400 | 0.200 | 0.399 | 0.666 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 100 | 10.9 | 0.547 | 0.546 | -0.002 | 1.001 |
| L16 | 0.200 | 0.400 | 0.200 | 0.403 | 0.668 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 100 | 5.5 | 0.515 | 0.519 | 0.003 | 0.999 |
| L17 | 0.200 | 0.450 | 0.200 | 0.450 | 0.693 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 100 | 12.3 | 0.485 | 0.483 | -0.002 | 1.013 |
| L18 | 0.200 | 0.450 | 0.200 | 0.447 | 0.691 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 100 | 6.1 | 0.386 | 0.386 | -0.001 | 1.001 |

## Insight Summary

- Positive-gain scene points: `9`
- Zero-gain scene points: `0`
- Negative-gain scene points: `9`
- Best gain scene: `case=`L04` rho_bg=`0.200` rho_pdb=`0.403` prb_share_pdb=`0.668` pdb_ms=`100` pdb_packet_kb=`5.5``
- Lowest center-retention scene: `case=`L16` rho_bg=`0.200` rho_pdb=`0.403` prb_share_pdb=`0.668` pdb_ms=`100` pdb_packet_kb=`5.5``

## Background Cost and Resource Analysis

- Mean center throughput retention across scene points: `1.004`
- Mean PRB utilization delta (proposed - baseline): `0.000`
- Mean center PRB share delta: `0.001`
- Mean edge PRB share delta: `-0.001`

| Region | Scene Points | Share | Win Rate | Mean Delta PDB Satisfaction | Mean Center Retention | Mean Delta PRB Utilization |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| critical | 11 | 0.61 | 0.45 | 0.001 | 1.005 | 0.000 |
| feasible | 3 | 0.17 | 1.00 | 0.003 | 1.000 | 0.000 |
| overloaded | 4 | 0.22 | 0.25 | 0.000 | 1.004 | 0.000 |

## Feasible Boundary Snapshot

- Boundary feasibility snapshots remain available at the 95% and 90% thresholds.

| Threshold | Baseline Feasible Points | Proposed Feasible Points | Expanded Points | Regressed Points |
| ---: | ---: | ---: | ---: | ---: |
| 0.95 | 3 | 3 | 0 | 0 |
| 0.90 | 4 | 4 | 0 | 0 |

## Representative Case Mechanism Analysis

- Representative cases selected: `4`
- Representative detail rows: `8`
- `typical_case_details.csv` is the renderer-facing mechanism table for these cases.

| Label | target_rho_bg | target_rho_pdb | actual_rho_bg | actual_rho_pdb | prb_share_pdb | pdb_ms | pdb_packet_kb | Mean Delta PDB Satisfaction | Center Retention |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| easy | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | 100 | 4.1 | 0.001 | 1.000 |
| critical | 0.200 | 0.400 | 0.200 | 0.403 | 0.668 | 100 | 5.5 | 0.015 | 1.001 |
| overloaded | 0.200 | 0.450 | 0.200 | 0.447 | 0.691 | 100 | 6.1 | 0.008 | 1.000 |
| high_cost | 0.200 | 0.400 | 0.200 | 0.403 | 0.668 | 100 | 5.5 | 0.003 | 0.999 |

| Label | baseline_satisfaction | proposed_satisfaction | baseline_queue_ms | proposed_queue_ms | baseline_completion_ms | proposed_completion_ms | baseline_center_rate_bps | proposed_center_rate_bps | center_retention |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| easy | 0.998 | 1.000 | 25.8 | 25.8 | 28.6 | 28.6 | 13258692.9 | 13259035.5 | 1.000 |
| critical | 0.662 | 0.677 | 36.8 | 36.8 | 41.0 | 41.0 | 13082744.2 | 13095576.2 | 1.001 |
| overloaded | 0.480 | 0.488 | 38.4 | 38.4 | 43.0 | 43.0 | 12681590.1 | 12685023.6 | 1.000 |
| high_cost | 0.515 | 0.519 | 40.8 | 40.8 | 44.4 | 44.4 | 13117173.8 | 13100967.3 | 0.999 |

## Summary

- Proposed improves `9/18` load-ratio scene points; best gain is `0.015`.
- Mean center throughput retention is `1.004`; worst retained point is `0.999`.
- Boundary expansion adds `0` points at 95% and `0` points at 90%.