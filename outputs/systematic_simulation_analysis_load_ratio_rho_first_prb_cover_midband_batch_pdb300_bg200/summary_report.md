# Systematic Simulation Analysis

## Wireless Environment and Realization Bank

- reference_config: `configs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_batch_pdb300_bg200.json`
- scene_bank_counts: `{'medium': 24, 'good': 24, 'poor': 16}`
- realization_bank_total_users: `64`
- repeat_count_per_scene_point: `5`

## Load-Ratio Scan Matrix

- `scan_mode = load_ratio`
- `rho_bg_values = [0.2]`
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
- Proposed improves `3` points, ties `8` points, and regresses `7` points.
- Mean scene-level delta PDB satisfaction: `-0.001`
- Mean scene-level center throughput retention: `1.001`

| case_label | target_rho_bg | target_rho_pdb | actual_rho_bg | actual_rho_pdb | prb_share_pdb | background_mapping_policy | pdb_mapping_policy | background_user_count | background_packet_kb | background_period_ms | pdb_user_count | pdb_ms | pdb_packet_kb | baseline_pdb_satisfaction | proposed_pdb_satisfaction | delta_pdb_satisfaction | center_retention |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L01 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 300 | 24.6 | 0.995 | 0.995 | 0.000 | 1.000 |
| L02 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 300 | 12.3 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.200 | 0.400 | 0.200 | 0.400 | 0.667 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 300 | 32.8 | 0.758 | 0.758 | 0.000 | 1.000 |
| L04 | 0.200 | 0.400 | 0.200 | 0.400 | 0.667 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 300 | 16.4 | 0.871 | 0.862 | -0.009 | 1.000 |
| L05 | 0.200 | 0.450 | 0.200 | 0.450 | 0.693 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 300 | 36.9 | 0.655 | 0.654 | -0.001 | 1.003 |
| L06 | 0.200 | 0.450 | 0.200 | 0.449 | 0.692 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 300 | 18.4 | 0.557 | 0.561 | 0.004 | 1.004 |
| L07 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 300 | 24.6 | 0.918 | 0.918 | 0.000 | 1.000 |
| L08 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 300 | 12.3 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.200 | 0.400 | 0.200 | 0.400 | 0.667 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 300 | 32.8 | 0.714 | 0.714 | 0.000 | 1.002 |
| L10 | 0.200 | 0.400 | 0.200 | 0.400 | 0.667 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 300 | 16.4 | 0.775 | 0.771 | -0.004 | 1.000 |
| L11 | 0.200 | 0.450 | 0.200 | 0.450 | 0.693 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 300 | 36.9 | 0.584 | 0.584 | 0.000 | 0.992 |
| L12 | 0.200 | 0.450 | 0.200 | 0.449 | 0.692 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 300 | 18.4 | 0.496 | 0.499 | 0.002 | 1.005 |
| L13 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 300 | 24.6 | 0.912 | 0.903 | -0.009 | 1.000 |
| L14 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 300 | 12.3 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.200 | 0.400 | 0.200 | 0.400 | 0.667 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 300 | 32.8 | 0.657 | 0.654 | -0.003 | 1.002 |
| L16 | 0.200 | 0.400 | 0.200 | 0.400 | 0.667 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 300 | 16.4 | 0.620 | 0.619 | -0.001 | 0.999 |
| L17 | 0.200 | 0.450 | 0.200 | 0.450 | 0.693 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 300 | 36.9 | 0.562 | 0.560 | -0.001 | 1.013 |
| L18 | 0.200 | 0.450 | 0.200 | 0.449 | 0.692 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 300 | 18.4 | 0.438 | 0.451 | 0.013 | 1.005 |

## Insight Summary

- Positive-gain scene points: `3`
- Zero-gain scene points: `8`
- Negative-gain scene points: `7`
- Best gain scene: `case=`L18` rho_bg=`0.200` rho_pdb=`0.449` prb_share_pdb=`0.692` pdb_ms=`300` pdb_packet_kb=`18.4``
- Lowest center-retention scene: `case=`L11` rho_bg=`0.200` rho_pdb=`0.450` prb_share_pdb=`0.693` pdb_ms=`300` pdb_packet_kb=`36.9``

## Background Cost and Resource Analysis

- Mean center throughput retention across scene points: `1.001`
- Mean PRB utilization delta (proposed - baseline): `0.000`
- Mean center PRB share delta: `0.000`
- Mean edge PRB share delta: `-0.000`

| Region | Scene Points | Share | Win Rate | Mean Delta PDB Satisfaction | Mean Center Retention | Mean Delta PRB Utilization |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| critical | 12 | 0.67 | 0.08 | -0.002 | 1.001 | -0.000 |
| feasible | 4 | 0.22 | 0.00 | 0.000 | 1.000 | 0.000 |
| overloaded | 2 | 0.11 | 1.00 | 0.007 | 1.005 | 0.000 |

## Feasible Boundary Snapshot

- Boundary feasibility snapshots remain available at the 95% and 90% thresholds.

| Threshold | Baseline Feasible Points | Proposed Feasible Points | Expanded Points | Regressed Points |
| ---: | ---: | ---: | ---: | ---: |
| 0.95 | 4 | 4 | 0 | 0 |
| 0.90 | 6 | 6 | 0 | 0 |

## Representative Case Mechanism Analysis

- Representative cases selected: `3`
- Representative detail rows: `6`
- `typical_case_details.csv` is the renderer-facing mechanism table for these cases.

| Label | target_rho_bg | target_rho_pdb | actual_rho_bg | actual_rho_pdb | prb_share_pdb | pdb_ms | pdb_packet_kb | Mean Delta PDB Satisfaction | Center Retention |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| easy | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | 300 | 12.3 | 0.000 | 1.000 |
| critical | 0.200 | 0.450 | 0.200 | 0.449 | 0.692 | 300 | 18.4 | 0.004 | 1.004 |
| overloaded | 0.200 | 0.450 | 0.200 | 0.449 | 0.692 | 300 | 18.4 | 0.013 | 1.005 |

| Label | baseline_satisfaction | proposed_satisfaction | baseline_queue_ms | proposed_queue_ms | baseline_completion_ms | proposed_completion_ms | baseline_center_rate_bps | proposed_center_rate_bps | center_retention |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| easy | 1.000 | 1.000 | 16.6 | 16.6 | 24.2 | 24.2 | 13260800.0 | 13260800.0 | 1.000 |
| critical | 0.557 | 0.561 | 36.6 | 36.6 | 48.0 | 48.0 | 12881030.1 | 12922724.3 | 1.003 |
| overloaded | 0.438 | 0.451 | 39.4 | 39.4 | 49.2 | 49.2 | 12814957.6 | 12869100.8 | 1.004 |

## Summary

- Proposed improves `3/18` load-ratio scene points; best gain is `0.013`.
- Mean center throughput retention is `1.001`; worst retained point is `0.992`.
- Boundary expansion adds `0` points at 95% and `0` points at 90%.