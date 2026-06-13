# Systematic Simulation Analysis

## Wireless Environment and Realization Bank

- reference_config: `configs/systematic_simulation_analysis_option1_batch_bg48.json`
- scene_bank_counts: `{'medium': 24, 'good': 24, 'poor': 16}`
- realization_bank_total_users: `64`
- repeat_count_per_scene_point: `10`

## Business Scan Matrix

- background_user_count_values: `[48]`
- pdb_user_count_values: `[4, 10, 16]`
- pdb_ms_values: `[100, 300, 500]`
- pdb_packet_kb_values: `[50, 150, 300]`
- repeat_count: `10`
- Scene points evaluated: `81`
- Paired realization rows: `810`
- Policy runs executed: `1620`

## Reporting Semantics

- `scene_summary.csv` aggregates policy-paired results at each business scan point.
- `capacity_summary_95.csv` and `capacity_summary_90.csv` summarize feasible operating ranges at two thresholds.
- boundary_feasibility_files: `['boundary_feasibility_95.csv', 'boundary_feasibility_90.csv']`
- representative_case_files: `['typical_case_candidates.csv', 'typical_case_details.csv']`
- Aggregated scene points: `81`

## Panoramic PDB Gain Overview

- Scene points evaluated: `81`
- Proposed improves `10` points, ties `64` points, and regresses `7` points.
- Mean scene-level delta PDB satisfaction: `0.004`
- Mean scene-level center throughput retention: `0.639`

| background_user_count | pdb_user_count | pdb_ms | pdb_packet_kb | baseline_pdb_satisfaction | proposed_pdb_satisfaction | delta_pdb_satisfaction | center_retention |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 48 | 4 | 500 | 50 | 0.151 | 0.246 | 0.095 | 1.018 |
| 36 | 4 | 300 | 50 | 0.028 | 0.097 | 0.069 | 0.706 |
| 48 | 4 | 300 | 50 | 0.008 | 0.063 | 0.054 | 0.732 |

## Background Cost and Resource Analysis

- Mean center throughput retention across scene points: `0.639`
- Mean PRB utilization delta (proposed - baseline): `0.000`
- Mean center PRB share delta: `-0.039`
- Mean edge PRB share delta: `0.039`

| Region | Scene Points | Share | Win Rate | Mean Delta PDB Satisfaction | Mean Center Retention | Mean Delta PRB Utilization |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| overloaded | 81 | 1.00 | 0.12 | 0.004 | 0.639 | 0.000 |

- Lowest center-retention scene point:
  - bg=`36`, pdb_users=`16`, pdb_ms=`100`, pdb_packet_kb=`300`
  - delta_pdb_satisfaction=`0.000`, center_retention=`0.151`

## Feasible Boundary Expansion

- Threshold snapshots are exported in `boundary_feasibility_95.csv` and `boundary_feasibility_90.csv`.

| Threshold | Baseline Feasible Points | Proposed Feasible Points | Expanded Points | Regressed Points |
| ---: | ---: | ---: | ---: | ---: |
| 0.95 | 0 | 0 | 0 | 0 |
| 0.90 | 0 | 0 | 0 | 0 |

## Representative Case Mechanism Analysis

- Representative cases selected: `2`
- Representative detail rows: `4`
- `typical_case_details.csv` is the renderer-facing mechanism table for these cases.

| Label | background_user_count | pdb_user_count | pdb_ms | pdb_packet_kb | Mean Delta PDB Satisfaction | Center Retention |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| overloaded | 48 | 4 | 500 | 50 | 0.095 | 1.018 |
| high_cost | 48 | 4 | 300 | 150 | 0.001 | 0.295 |

| Label | baseline_satisfaction | proposed_satisfaction | baseline_queue_ms | proposed_queue_ms | baseline_completion_ms | proposed_completion_ms | baseline_center_rate_bps | proposed_center_rate_bps | center_retention |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| overloaded | 0.151 | 0.246 | 505.3 | 454.9 | 563.6 | 508.0 | 28576306.5 | 29070864.7 | 1.017 |
| high_cost | 0.000 | 0.001 | 1563.9 | 2605.9 | 444.4 | 289.4 | 10833704.7 | 2729554.9 | 0.252 |

| Label | baseline_prb_utilization | proposed_prb_utilization | baseline_center_prb_share | proposed_center_prb_share | baseline_edge_prb_share | proposed_edge_prb_share | baseline_backlog_bits | proposed_backlog_bits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| overloaded | 1.000 | 1.000 | 0.549 | 0.543 | 0.451 | 0.457 | 0.0 | 0.0 |
| high_cost | 1.000 | 1.000 | 0.200 | 0.058 | 0.800 | 0.942 | 81879619.2 | 70825887.6 |

## Summary

- Proposed improves `10/81` scene points; best gain is `0.095`.
- Mean center throughput retention is `0.639`; worst retained point is `0.151`.
- Feasible-region expansion adds `0` points at 95% and `0` points at 90%.