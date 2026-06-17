# Systematic Simulation Analysis

## Wireless Environment and Realization Bank

- reference_config: `configs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_batch_pdb050_bg120.json`
- scene_bank_counts: `{'medium': 24, 'good': 24, 'poor': 16}`
- realization_bank_total_users: `64`
- repeat_count_per_scene_point: `5`

## Load-Ratio Scan Matrix

- `scan_mode = load_ratio`
- `rho_bg_values = [0.12]`
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
- Proposed improves `5` points, ties `7` points, and regresses `6` points.
- Mean scene-level delta PDB satisfaction: `0.001`
- Mean scene-level center throughput retention: `1.000`

| case_label | target_rho_bg | target_rho_pdb | actual_rho_bg | actual_rho_pdb | prb_share_pdb | background_mapping_policy | pdb_mapping_policy | background_user_count | background_packet_kb | background_period_ms | pdb_user_count | pdb_ms | pdb_packet_kb | baseline_pdb_satisfaction | proposed_pdb_satisfaction | delta_pdb_satisfaction | center_retention |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L01 | 0.120 | 0.300 | 0.120 | 0.300 | 0.714 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 50 | 4.1 | 0.996 | 0.996 | 0.000 | 1.000 |
| L02 | 0.120 | 0.300 | 0.120 | 0.293 | 0.709 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 50 | 2 | 0.996 | 0.996 | 0.000 | 1.000 |
| L03 | 0.120 | 0.400 | 0.120 | 0.403 | 0.770 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 50 | 5.5 | 0.810 | 0.806 | -0.004 | 1.000 |
| L04 | 0.120 | 0.400 | 0.120 | 0.395 | 0.767 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 50 | 2.7 | 0.848 | 0.846 | -0.002 | 1.000 |
| L05 | 0.120 | 0.450 | 0.120 | 0.447 | 0.788 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 50 | 6.1 | 0.774 | 0.774 | 0.000 | 0.998 |
| L06 | 0.120 | 0.450 | 0.120 | 0.454 | 0.791 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 50 | 3.1 | 0.483 | 0.481 | -0.002 | 1.000 |
| L07 | 0.120 | 0.300 | 0.120 | 0.300 | 0.715 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 50 | 4.1 | 0.978 | 0.978 | 0.000 | 1.000 |
| L08 | 0.120 | 0.300 | 0.120 | 0.293 | 0.709 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 50 | 2 | 0.978 | 0.978 | 0.000 | 1.000 |
| L09 | 0.120 | 0.400 | 0.120 | 0.403 | 0.771 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 50 | 5.5 | 0.803 | 0.803 | 0.000 | 1.000 |
| L10 | 0.120 | 0.400 | 0.120 | 0.395 | 0.767 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 50 | 2.7 | 0.822 | 0.822 | -0.000 | 1.000 |
| L11 | 0.120 | 0.450 | 0.120 | 0.447 | 0.788 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 50 | 6.1 | 0.738 | 0.739 | 0.001 | 1.001 |
| L12 | 0.120 | 0.450 | 0.120 | 0.454 | 0.791 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 50 | 3.1 | 0.476 | 0.484 | 0.008 | 1.000 |
| L13 | 0.120 | 0.300 | 0.120 | 0.300 | 0.714 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 50 | 4.1 | 0.997 | 0.997 | 0.000 | 1.000 |
| L14 | 0.120 | 0.300 | 0.120 | 0.293 | 0.709 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 50 | 2 | 0.984 | 0.984 | 0.000 | 1.000 |
| L15 | 0.120 | 0.400 | 0.120 | 0.403 | 0.770 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 50 | 5.5 | 0.807 | 0.807 | -0.001 | 1.000 |
| L16 | 0.120 | 0.400 | 0.120 | 0.395 | 0.767 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 50 | 2.7 | 0.772 | 0.788 | 0.016 | 1.000 |
| L17 | 0.120 | 0.450 | 0.120 | 0.447 | 0.788 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 50 | 6.1 | 0.725 | 0.724 | -0.001 | 1.000 |
| L18 | 0.120 | 0.450 | 0.120 | 0.454 | 0.791 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 50 | 3.1 | 0.418 | 0.420 | 0.001 | 0.999 |

## Insight Summary

- Positive-gain scene points: `5`
- Zero-gain scene points: `7`
- Negative-gain scene points: `6`
- Best gain scene: `case=`L16` rho_bg=`0.120` rho_pdb=`0.395` prb_share_pdb=`0.767` pdb_ms=`50` pdb_packet_kb=`2.7``
- Lowest center-retention scene: `case=`L05` rho_bg=`0.120` rho_pdb=`0.447` prb_share_pdb=`0.788` pdb_ms=`50` pdb_packet_kb=`6.1``

## Background Cost and Resource Analysis

- Mean center throughput retention across scene points: `1.000`
- Mean PRB utilization delta (proposed - baseline): `0.000`
- Mean center PRB share delta: `0.000`
- Mean edge PRB share delta: `-0.000`

| Region | Scene Points | Share | Win Rate | Mean Delta PDB Satisfaction | Mean Center Retention | Mean Delta PRB Utilization |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| critical | 9 | 0.50 | 0.33 | 0.001 | 1.000 | -0.000 |
| feasible | 6 | 0.33 | 0.00 | 0.000 | 1.000 | 0.000 |
| overloaded | 3 | 0.17 | 0.67 | 0.003 | 1.000 | 0.000 |

## Feasible Boundary Snapshot

- Boundary feasibility snapshots remain available at the 95% and 90% thresholds.

| Threshold | Baseline Feasible Points | Proposed Feasible Points | Expanded Points | Regressed Points |
| ---: | ---: | ---: | ---: | ---: |
| 0.95 | 6 | 6 | 0 | 0 |
| 0.90 | 6 | 6 | 0 | 0 |

## Representative Case Mechanism Analysis

- Representative cases selected: `4`
- Representative detail rows: `8`
- `typical_case_details.csv` is the renderer-facing mechanism table for these cases.

| Label | target_rho_bg | target_rho_pdb | actual_rho_bg | actual_rho_pdb | prb_share_pdb | pdb_ms | pdb_packet_kb | Mean Delta PDB Satisfaction | Center Retention |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| easy | 0.120 | 0.300 | 0.120 | 0.300 | 0.714 | 50 | 4.1 | 0.000 | 1.000 |
| critical | 0.120 | 0.400 | 0.120 | 0.395 | 0.767 | 50 | 2.7 | 0.016 | 1.000 |
| overloaded | 0.120 | 0.450 | 0.120 | 0.454 | 0.791 | 50 | 3.1 | 0.008 | 1.000 |
| high_cost | 0.120 | 0.450 | 0.120 | 0.454 | 0.791 | 50 | 3.1 | 0.001 | 0.999 |

| Label | baseline_satisfaction | proposed_satisfaction | baseline_queue_ms | proposed_queue_ms | baseline_completion_ms | proposed_completion_ms | baseline_center_rate_bps | proposed_center_rate_bps | center_retention |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| easy | 0.997 | 0.997 | 28.0 | 28.0 | 31.6 | 31.6 | 8006400.0 | 8006400.0 | 1.000 |
| critical | 0.772 | 0.788 | 21.0 | 21.0 | 23.2 | 23.2 | 8003852.9 | 8004359.4 | 1.000 |
| overloaded | 0.476 | 0.484 | 19.2 | 19.2 | 21.0 | 21.0 | 7986858.9 | 7986192.1 | 1.000 |
| high_cost | 0.418 | 0.420 | 22.6 | 22.6 | 25.2 | 25.2 | 7993569.2 | 7988631.0 | 0.999 |

## Summary

- Proposed improves `5/18` load-ratio scene points; best gain is `0.016`.
- Mean center throughput retention is `1.000`; worst retained point is `0.998`.
- Boundary expansion adds `0` points at 95% and `0` points at 90%.