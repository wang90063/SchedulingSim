# Systematic Simulation Analysis

## Wireless Environment and Realization Bank

- reference_config: `configs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_batch_pdb100_bg120.json`
- scene_bank_counts: `{'medium': 24, 'good': 24, 'poor': 16}`
- realization_bank_total_users: `64`
- repeat_count_per_scene_point: `5`

## Load-Ratio Scan Matrix

- `scan_mode = load_ratio`
- `rho_bg_values = [0.12]`
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
- Proposed improves `3` points, ties `10` points, and regresses `5` points.
- Mean scene-level delta PDB satisfaction: `-0.000`
- Mean scene-level center throughput retention: `1.000`

| case_label | target_rho_bg | target_rho_pdb | actual_rho_bg | actual_rho_pdb | prb_share_pdb | background_mapping_policy | pdb_mapping_policy | background_user_count | background_packet_kb | background_period_ms | pdb_user_count | pdb_ms | pdb_packet_kb | baseline_pdb_satisfaction | proposed_pdb_satisfaction | delta_pdb_satisfaction | center_retention |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L01 | 0.120 | 0.300 | 0.120 | 0.300 | 0.714 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 100 | 8.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.120 | 0.300 | 0.120 | 0.300 | 0.714 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 100 | 4.1 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.120 | 0.400 | 0.120 | 0.399 | 0.769 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 100 | 10.9 | 0.853 | 0.857 | 0.004 | 1.000 |
| L04 | 0.120 | 0.400 | 0.120 | 0.403 | 0.770 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 100 | 5.5 | 0.939 | 0.933 | -0.006 | 1.000 |
| L05 | 0.120 | 0.450 | 0.120 | 0.450 | 0.790 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 100 | 12.3 | 0.804 | 0.804 | 0.000 | 0.999 |
| L06 | 0.120 | 0.450 | 0.120 | 0.447 | 0.788 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 100 | 6.1 | 0.803 | 0.802 | -0.001 | 1.000 |
| L07 | 0.120 | 0.300 | 0.120 | 0.300 | 0.715 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 100 | 8.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.120 | 0.300 | 0.120 | 0.300 | 0.715 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 100 | 4.1 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.120 | 0.400 | 0.120 | 0.399 | 0.769 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 100 | 10.9 | 0.834 | 0.832 | -0.002 | 1.000 |
| L10 | 0.120 | 0.400 | 0.120 | 0.403 | 0.771 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 100 | 5.5 | 0.933 | 0.947 | 0.014 | 1.000 |
| L11 | 0.120 | 0.450 | 0.120 | 0.450 | 0.790 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 100 | 12.3 | 0.800 | 0.800 | 0.000 | 1.000 |
| L12 | 0.120 | 0.450 | 0.120 | 0.447 | 0.788 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 100 | 6.1 | 0.756 | 0.756 | 0.000 | 1.000 |
| L13 | 0.120 | 0.300 | 0.120 | 0.300 | 0.714 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 100 | 8.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.120 | 0.300 | 0.120 | 0.300 | 0.714 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 100 | 4.1 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.120 | 0.400 | 0.120 | 0.399 | 0.769 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 100 | 10.9 | 0.863 | 0.863 | 0.000 | 1.000 |
| L16 | 0.120 | 0.400 | 0.120 | 0.403 | 0.770 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 100 | 5.5 | 0.961 | 0.957 | -0.004 | 1.000 |
| L17 | 0.120 | 0.450 | 0.120 | 0.450 | 0.790 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 100 | 12.3 | 0.798 | 0.798 | 0.000 | 1.000 |
| L18 | 0.120 | 0.450 | 0.120 | 0.447 | 0.788 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 100 | 6.1 | 0.669 | 0.658 | -0.010 | 1.000 |

## Insight Summary

- Positive-gain scene points: `3`
- Zero-gain scene points: `10`
- Negative-gain scene points: `5`
- Best gain scene: `case=`L10` rho_bg=`0.120` rho_pdb=`0.403` prb_share_pdb=`0.771` pdb_ms=`100` pdb_packet_kb=`5.5``
- Lowest center-retention scene: `case=`L05` rho_bg=`0.120` rho_pdb=`0.450` prb_share_pdb=`0.790` pdb_ms=`100` pdb_packet_kb=`12.3``

## Background Cost and Resource Analysis

- Mean center throughput retention across scene points: `1.000`
- Mean PRB utilization delta (proposed - baseline): `0.000`
- Mean center PRB share delta: `-0.000`
- Mean edge PRB share delta: `0.000`

| Region | Scene Points | Share | Win Rate | Mean Delta PDB Satisfaction | Mean Center Retention | Mean Delta PRB Utilization |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| critical | 11 | 0.61 | 0.27 | 0.000 | 1.000 | 0.000 |
| feasible | 7 | 0.39 | 0.00 | -0.001 | 1.000 | 0.000 |

## Feasible Boundary Snapshot

- Boundary feasibility snapshots remain available at the 95% and 90% thresholds.

| Threshold | Baseline Feasible Points | Proposed Feasible Points | Expanded Points | Regressed Points |
| ---: | ---: | ---: | ---: | ---: |
| 0.95 | 7 | 7 | 0 | 0 |
| 0.90 | 9 | 9 | 0 | 0 |

## Representative Case Mechanism Analysis

- Representative cases selected: `2`
- Representative detail rows: `4`
- `typical_case_details.csv` is the renderer-facing mechanism table for these cases.

| Label | target_rho_bg | target_rho_pdb | actual_rho_bg | actual_rho_pdb | prb_share_pdb | pdb_ms | pdb_packet_kb | Mean Delta PDB Satisfaction | Center Retention |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| easy | 0.120 | 0.300 | 0.120 | 0.300 | 0.714 | 100 | 8.2 | 0.000 | 1.000 |
| critical | 0.120 | 0.400 | 0.120 | 0.403 | 0.771 | 100 | 5.5 | 0.014 | 1.000 |

| Label | baseline_satisfaction | proposed_satisfaction | baseline_queue_ms | proposed_queue_ms | baseline_completion_ms | proposed_completion_ms | baseline_center_rate_bps | proposed_center_rate_bps | center_retention |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| easy | 1.000 | 1.000 | 22.4 | 22.4 | 26.8 | 26.8 | 7987200.0 | 7987200.0 | 1.000 |
| critical | 0.933 | 0.947 | 19.4 | 19.4 | 22.8 | 22.8 | 8000000.0 | 8000000.0 | 1.000 |

## Summary

- Proposed improves `3/18` load-ratio scene points; best gain is `0.014`.
- Mean center throughput retention is `1.000`; worst retained point is `0.999`.
- Boundary expansion adds `0` points at 95% and `0` points at 90%.