# Systematic Simulation Analysis

## Wireless Environment and Realization Bank

- reference_config: `configs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_small_merge.json`
- scene_bank_counts: `{'medium': 24, 'good': 24, 'poor': 16}`
- realization_bank_total_users: `64`
- repeat_count_per_scene_point: `5`

## Load-Ratio Scan Matrix

- `scan_mode = load_ratio`
- `rho_bg_values = [0.03, 0.07, 0.12, 0.2]`
- `rho_pdb_values = [0.03, 0.18, 0.55]`
- `pdb_ms_values = [50, 100, 300]`
- `mapping_policy = {'background': {'kind': 'candidate_domain_solve_period', 'background_user_count_values': [32, 40, 48], 'background_packet_kb_values': [1.0, 1.5, 2.0], 'background_period_ms_range': [4.0, 400.0], 'anchor_background_user_count': 40, 'anchor_background_packet_kb': 2.0}, 'pdb': {'kind': 'candidate_domain_solve_packet', 'pdb_user_count_values': [4, 8], 'pdb_packet_kb_range': [0.1, 80.0], 'anchor_pdb_user_count': 4}}`
- `repeat_count = 5`
- Scene points evaluated: `216`
- Paired realization rows: `1080`
- Policy runs executed: `2160`

## Reporting Semantics

- `scene_summary.csv` aggregates policy-paired results at each rho-first scene point.
- Target `rho` values define the scan; actual `rho` values are recomputed after mapping and rounding.
- `PDB` timing shape remains a secondary axis, so equal target `rho_pdb` values can still be compared across different `pdb_ms` realizations.
- `background_mapping_policy` and `pdb_mapping_policy` record the candidate-domain solver used for each scene.
- capacity summaries are omitted for load-ratio outputs because the legacy feasible-range tables assume user-count axes rather than ratio coordinates.
- boundary_feasibility_files: `['boundary_feasibility_95.csv', 'boundary_feasibility_90.csv']`
- Aggregated scene points: `216`

## Panoramic PDB Gain Overview

- Scene points evaluated: `216`
- Proposed improves `27` points, ties `167` points, and regresses `22` points.
- Mean scene-level delta PDB satisfaction: `0.001`
- Mean scene-level center throughput retention: `1.009`

| case_label | target_rho_bg | target_rho_pdb | actual_rho_bg | actual_rho_pdb | prb_share_pdb | background_mapping_policy | pdb_mapping_policy | background_user_count | background_packet_kb | background_period_ms | pdb_user_count | pdb_ms | pdb_packet_kb | baseline_pdb_satisfaction | proposed_pdb_satisfaction | delta_pdb_satisfaction | center_retention |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L01 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 50 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 50 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 50 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 50 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 100 | 0.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 100 | 0.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 100 | 0.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 100 | 0.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.200 | 0.030 | 0.200 | 0.031 | 0.132 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 300 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.120 | 0.030 | 0.120 | 0.031 | 0.203 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 300 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.070 | 0.030 | 0.070 | 0.031 | 0.304 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 300 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.030 | 0.030 | 0.030 | 0.031 | 0.504 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 300 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 50 | 0.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 50 | 0.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 50 | 0.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 50 | 0.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 100 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 100 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 100 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 100 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 300 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 300 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 300 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 300 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.200 | 0.180 | 0.200 | 0.183 | 0.478 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 50 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.120 | 0.180 | 0.120 | 0.183 | 0.604 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 50 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.070 | 0.180 | 0.070 | 0.183 | 0.723 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 50 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.030 | 0.180 | 0.030 | 0.183 | 0.859 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 50 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.200 | 0.180 | 0.200 | 0.179 | 0.473 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 100 | 4.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.120 | 0.180 | 0.120 | 0.179 | 0.599 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 100 | 4.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.070 | 0.180 | 0.070 | 0.179 | 0.719 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 100 | 4.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.030 | 0.180 | 0.030 | 0.179 | 0.857 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 100 | 4.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.200 | 0.180 | 0.200 | 0.179 | 0.473 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 300 | 14.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.120 | 0.180 | 0.120 | 0.179 | 0.599 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 300 | 14.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.070 | 0.180 | 0.070 | 0.179 | 0.719 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 300 | 14.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.030 | 0.180 | 0.030 | 0.179 | 0.857 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 300 | 14.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.200 | 0.180 | 0.200 | 0.176 | 0.468 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 50 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.120 | 0.180 | 0.120 | 0.176 | 0.594 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 50 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.070 | 0.180 | 0.070 | 0.176 | 0.715 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 50 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.030 | 0.180 | 0.030 | 0.176 | 0.854 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 50 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.200 | 0.180 | 0.200 | 0.183 | 0.478 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 100 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.120 | 0.180 | 0.120 | 0.183 | 0.604 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 100 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.070 | 0.180 | 0.070 | 0.183 | 0.723 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 100 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.030 | 0.180 | 0.030 | 0.183 | 0.859 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 100 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.200 | 0.180 | 0.200 | 0.181 | 0.475 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 300 | 7.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.120 | 0.180 | 0.120 | 0.181 | 0.601 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 300 | 7.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.070 | 0.180 | 0.070 | 0.181 | 0.721 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 300 | 7.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.030 | 0.180 | 0.030 | 0.181 | 0.858 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 300 | 7.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L05 | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 50 | 7.5 | 0.354 | 0.358 | 0.005 | 0.940 |
| L05 | 0.120 | 0.550 | 0.120 | 0.549 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 50 | 7.5 | 0.541 | 0.546 | 0.005 | 0.973 |
| L05 | 0.070 | 0.550 | 0.070 | 0.549 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 50 | 7.5 | 0.690 | 0.688 | -0.002 | 0.941 |
| L05 | 0.030 | 0.550 | 0.030 | 0.549 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 50 | 7.5 | 0.799 | 0.799 | 0.000 | 1.016 |
| L05 | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 100 | 15 | 0.422 | 0.426 | 0.004 | 0.979 |
| L05 | 0.120 | 0.550 | 0.120 | 0.549 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 100 | 15 | 0.614 | 0.613 | -0.001 | 1.234 |
| L05 | 0.070 | 0.550 | 0.070 | 0.549 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 100 | 15 | 0.796 | 0.796 | 0.000 | 1.007 |
| L05 | 0.030 | 0.550 | 0.030 | 0.549 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 100 | 15 | 0.810 | 0.810 | 0.000 | 0.996 |
| L05 | 0.200 | 0.550 | 0.200 | 0.550 | 0.734 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 300 | 45.1 | 0.492 | 0.502 | 0.010 | 0.985 |
| L05 | 0.120 | 0.550 | 0.120 | 0.550 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 300 | 45.1 | 0.676 | 0.676 | 0.000 | 1.060 |
| L05 | 0.070 | 0.550 | 0.070 | 0.550 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 300 | 45.1 | 0.811 | 0.811 | 0.000 | 1.026 |
| L05 | 0.030 | 0.550 | 0.030 | 0.550 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 300 | 45.1 | 0.847 | 0.847 | 0.000 | 0.990 |
| L06 | 0.200 | 0.550 | 0.200 | 0.557 | 0.736 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 50 | 3.8 | 0.105 | 0.122 | 0.016 | 0.942 |
| L06 | 0.120 | 0.550 | 0.120 | 0.557 | 0.823 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 50 | 3.8 | 0.220 | 0.221 | 0.002 | 1.122 |
| L06 | 0.070 | 0.550 | 0.070 | 0.557 | 0.888 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 50 | 3.8 | 0.346 | 0.336 | -0.010 | 1.016 |
| L06 | 0.030 | 0.550 | 0.030 | 0.557 | 0.949 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 50 | 3.8 | 0.605 | 0.601 | -0.004 | 0.999 |
| L06 | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 100 | 7.5 | 0.227 | 0.238 | 0.011 | 1.075 |
| L06 | 0.120 | 0.550 | 0.120 | 0.549 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 100 | 7.5 | 0.317 | 0.315 | -0.002 | 1.008 |
| L06 | 0.070 | 0.550 | 0.070 | 0.549 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 100 | 7.5 | 0.536 | 0.525 | -0.011 | 1.027 |
| L06 | 0.030 | 0.550 | 0.030 | 0.549 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 100 | 7.5 | 0.826 | 0.826 | 0.000 | 1.000 |
| L06 | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 300 | 22.5 | 0.304 | 0.321 | 0.016 | 1.073 |
| L06 | 0.120 | 0.550 | 0.120 | 0.549 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 300 | 22.5 | 0.454 | 0.449 | -0.005 | 1.052 |
| L06 | 0.070 | 0.550 | 0.070 | 0.549 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 300 | 22.5 | 0.834 | 0.834 | 0.000 | 1.007 |
| L06 | 0.030 | 0.550 | 0.030 | 0.549 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 300 | 22.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 50 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 50 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 50 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 50 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 100 | 0.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 100 | 0.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 100 | 0.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 100 | 0.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.200 | 0.030 | 0.200 | 0.031 | 0.132 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 300 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.120 | 0.030 | 0.120 | 0.031 | 0.203 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 300 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.070 | 0.030 | 0.070 | 0.031 | 0.304 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 300 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.030 | 0.030 | 0.030 | 0.031 | 0.504 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 300 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 50 | 0.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 50 | 0.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 50 | 0.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 50 | 0.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 100 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 100 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 100 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 100 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 300 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 300 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 300 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 300 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.200 | 0.180 | 0.200 | 0.183 | 0.478 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 50 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.120 | 0.180 | 0.120 | 0.183 | 0.604 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 50 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.070 | 0.180 | 0.070 | 0.183 | 0.723 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 50 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.030 | 0.180 | 0.030 | 0.183 | 0.859 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 50 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.200 | 0.180 | 0.200 | 0.179 | 0.473 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 100 | 4.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.120 | 0.180 | 0.120 | 0.179 | 0.599 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 100 | 4.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.070 | 0.180 | 0.070 | 0.179 | 0.719 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 100 | 4.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.030 | 0.180 | 0.030 | 0.179 | 0.857 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 100 | 4.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.200 | 0.180 | 0.200 | 0.179 | 0.473 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 300 | 14.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.120 | 0.180 | 0.120 | 0.179 | 0.599 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 300 | 14.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.070 | 0.180 | 0.070 | 0.179 | 0.719 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 300 | 14.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.030 | 0.180 | 0.030 | 0.179 | 0.857 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 300 | 14.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.200 | 0.180 | 0.200 | 0.176 | 0.468 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 50 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.120 | 0.180 | 0.120 | 0.176 | 0.594 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 50 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.070 | 0.180 | 0.070 | 0.176 | 0.715 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 50 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.030 | 0.180 | 0.030 | 0.176 | 0.854 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 50 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.200 | 0.180 | 0.200 | 0.183 | 0.478 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 100 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.120 | 0.180 | 0.120 | 0.183 | 0.604 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 100 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.070 | 0.180 | 0.070 | 0.183 | 0.723 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 100 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.030 | 0.180 | 0.030 | 0.183 | 0.859 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 100 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.200 | 0.180 | 0.200 | 0.181 | 0.475 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 300 | 7.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.120 | 0.180 | 0.120 | 0.181 | 0.601 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 300 | 7.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.070 | 0.180 | 0.070 | 0.181 | 0.721 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 300 | 7.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.030 | 0.180 | 0.030 | 0.181 | 0.858 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 300 | 7.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L11 | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 50 | 7.5 | 0.330 | 0.332 | 0.002 | 1.079 |
| L11 | 0.120 | 0.550 | 0.120 | 0.549 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 50 | 7.5 | 0.505 | 0.509 | 0.004 | 1.048 |
| L11 | 0.070 | 0.550 | 0.070 | 0.549 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 50 | 7.5 | 0.663 | 0.661 | -0.003 | 1.014 |
| L11 | 0.030 | 0.550 | 0.030 | 0.549 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 50 | 7.5 | 0.786 | 0.786 | 0.000 | 1.003 |
| L11 | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 100 | 15 | 0.388 | 0.383 | -0.005 | 1.060 |
| L11 | 0.120 | 0.550 | 0.120 | 0.549 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 100 | 15 | 0.582 | 0.582 | 0.000 | 0.983 |
| L11 | 0.070 | 0.550 | 0.070 | 0.549 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 100 | 15 | 0.788 | 0.788 | 0.000 | 1.001 |
| L11 | 0.030 | 0.550 | 0.030 | 0.549 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 100 | 15 | 0.810 | 0.810 | 0.000 | 0.996 |
| L11 | 0.200 | 0.550 | 0.200 | 0.550 | 0.734 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 300 | 45.1 | 0.468 | 0.471 | 0.003 | 1.006 |
| L11 | 0.120 | 0.550 | 0.120 | 0.550 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 300 | 45.1 | 0.673 | 0.667 | -0.006 | 1.006 |
| L11 | 0.070 | 0.550 | 0.070 | 0.550 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 300 | 45.1 | 0.808 | 0.808 | 0.000 | 1.067 |
| L11 | 0.030 | 0.550 | 0.030 | 0.550 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 300 | 45.1 | 0.838 | 0.838 | 0.000 | 0.997 |
| L12 | 0.200 | 0.550 | 0.200 | 0.557 | 0.736 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 50 | 3.8 | 0.089 | 0.102 | 0.014 | 1.188 |
| L12 | 0.120 | 0.550 | 0.120 | 0.557 | 0.823 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 50 | 3.8 | 0.200 | 0.206 | 0.007 | 1.091 |
| L12 | 0.070 | 0.550 | 0.070 | 0.557 | 0.888 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 50 | 3.8 | 0.330 | 0.342 | 0.011 | 1.015 |
| L12 | 0.030 | 0.550 | 0.030 | 0.557 | 0.949 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 50 | 3.8 | 0.586 | 0.595 | 0.009 | 1.003 |
| L12 | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 100 | 7.5 | 0.186 | 0.209 | 0.022 | 1.036 |
| L12 | 0.120 | 0.550 | 0.120 | 0.549 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 100 | 7.5 | 0.285 | 0.288 | 0.003 | 1.063 |
| L12 | 0.070 | 0.550 | 0.070 | 0.549 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 100 | 7.5 | 0.523 | 0.528 | 0.005 | 1.019 |
| L12 | 0.030 | 0.550 | 0.030 | 0.549 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 100 | 7.5 | 0.826 | 0.821 | -0.005 | 1.000 |
| L12 | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 300 | 22.5 | 0.284 | 0.281 | -0.003 | 0.969 |
| L12 | 0.120 | 0.550 | 0.120 | 0.549 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 300 | 22.5 | 0.405 | 0.419 | 0.014 | 1.020 |
| L12 | 0.070 | 0.550 | 0.070 | 0.549 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 300 | 22.5 | 0.833 | 0.833 | 0.000 | 0.989 |
| L12 | 0.030 | 0.550 | 0.030 | 0.549 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 300 | 22.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 50 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 50 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 50 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 50 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 100 | 0.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 100 | 0.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 100 | 0.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 100 | 0.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.120 | 0.030 | 0.120 | 0.031 | 0.203 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 300 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.030 | 0.030 | 0.030 | 0.031 | 0.504 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 300 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.200 | 0.030 | 0.200 | 0.031 | 0.132 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 300 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.070 | 0.030 | 0.070 | 0.031 | 0.304 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 300 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 50 | 0.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 50 | 0.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 50 | 0.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 50 | 0.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 100 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 100 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 100 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 100 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 300 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 300 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 300 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 300 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.120 | 0.180 | 0.120 | 0.183 | 0.604 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 50 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.030 | 0.180 | 0.030 | 0.183 | 0.859 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 50 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.200 | 0.180 | 0.200 | 0.183 | 0.478 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 50 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.070 | 0.180 | 0.070 | 0.183 | 0.723 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 50 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.120 | 0.180 | 0.120 | 0.179 | 0.599 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 100 | 4.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.030 | 0.180 | 0.030 | 0.179 | 0.857 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 100 | 4.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.200 | 0.180 | 0.200 | 0.179 | 0.473 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 100 | 4.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.070 | 0.180 | 0.070 | 0.179 | 0.719 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 100 | 4.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.120 | 0.180 | 0.120 | 0.179 | 0.599 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 300 | 14.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.030 | 0.180 | 0.030 | 0.179 | 0.857 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 300 | 14.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.200 | 0.180 | 0.200 | 0.179 | 0.473 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 300 | 14.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.070 | 0.180 | 0.070 | 0.179 | 0.719 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 300 | 14.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.120 | 0.180 | 0.120 | 0.176 | 0.594 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 50 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.030 | 0.180 | 0.030 | 0.176 | 0.854 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 50 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.200 | 0.180 | 0.200 | 0.176 | 0.468 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 50 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.070 | 0.180 | 0.070 | 0.176 | 0.715 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 50 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.120 | 0.180 | 0.120 | 0.183 | 0.604 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 100 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.030 | 0.180 | 0.030 | 0.183 | 0.859 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 100 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.200 | 0.180 | 0.200 | 0.183 | 0.478 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 100 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.070 | 0.180 | 0.070 | 0.183 | 0.723 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 100 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.120 | 0.180 | 0.120 | 0.181 | 0.601 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 300 | 7.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.030 | 0.180 | 0.030 | 0.181 | 0.858 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 300 | 7.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.200 | 0.180 | 0.200 | 0.181 | 0.475 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 300 | 7.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.070 | 0.180 | 0.070 | 0.181 | 0.721 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 300 | 7.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L17 | 0.120 | 0.550 | 0.120 | 0.549 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 50 | 7.5 | 0.513 | 0.510 | -0.003 | 1.016 |
| L17 | 0.030 | 0.550 | 0.030 | 0.549 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 50 | 7.5 | 0.790 | 0.790 | 0.000 | 1.014 |
| L17 | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 50 | 7.5 | 0.320 | 0.317 | -0.004 | 1.058 |
| L17 | 0.070 | 0.550 | 0.070 | 0.549 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 50 | 7.5 | 0.638 | 0.633 | -0.004 | 0.980 |
| L17 | 0.120 | 0.550 | 0.120 | 0.549 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 100 | 15 | 0.584 | 0.580 | -0.004 | 1.021 |
| L17 | 0.030 | 0.550 | 0.030 | 0.549 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 100 | 15 | 0.811 | 0.811 | 0.000 | 1.004 |
| L17 | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 100 | 15 | 0.390 | 0.390 | -0.000 | 1.153 |
| L17 | 0.070 | 0.550 | 0.070 | 0.549 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 100 | 15 | 0.751 | 0.759 | 0.008 | 0.992 |
| L17 | 0.120 | 0.550 | 0.120 | 0.550 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 300 | 45.1 | 0.666 | 0.657 | -0.009 | 0.969 |
| L17 | 0.030 | 0.550 | 0.030 | 0.550 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 300 | 45.1 | 0.848 | 0.848 | 0.000 | 1.001 |
| L17 | 0.200 | 0.550 | 0.200 | 0.550 | 0.734 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 300 | 45.1 | 0.467 | 0.465 | -0.001 | 0.925 |
| L17 | 0.070 | 0.550 | 0.070 | 0.550 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 300 | 45.1 | 0.811 | 0.811 | 0.000 | 1.003 |
| L18 | 0.120 | 0.550 | 0.120 | 0.557 | 0.823 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 50 | 3.8 | 0.208 | 0.216 | 0.008 | 1.074 |
| L18 | 0.030 | 0.550 | 0.030 | 0.557 | 0.949 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 50 | 3.8 | 0.568 | 0.571 | 0.002 | 1.000 |
| L18 | 0.200 | 0.550 | 0.200 | 0.557 | 0.736 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 50 | 3.8 | 0.077 | 0.090 | 0.013 | 1.259 |
| L18 | 0.070 | 0.550 | 0.070 | 0.557 | 0.888 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 50 | 3.8 | 0.322 | 0.318 | -0.003 | 1.021 |
| L18 | 0.120 | 0.550 | 0.120 | 0.549 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 100 | 7.5 | 0.267 | 0.272 | 0.005 | 1.095 |
| L18 | 0.030 | 0.550 | 0.030 | 0.549 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 100 | 7.5 | 0.823 | 0.827 | 0.004 | 1.001 |
| L18 | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 100 | 7.5 | 0.169 | 0.189 | 0.019 | 1.168 |
| L18 | 0.070 | 0.550 | 0.070 | 0.549 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 100 | 7.5 | 0.458 | 0.456 | -0.001 | 1.036 |
| L18 | 0.120 | 0.550 | 0.120 | 0.549 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 300 | 22.5 | 0.382 | 0.379 | -0.004 | 1.080 |
| L18 | 0.030 | 0.550 | 0.030 | 0.549 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 300 | 22.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L18 | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 300 | 22.5 | 0.257 | 0.267 | 0.010 | 1.003 |
| L18 | 0.070 | 0.550 | 0.070 | 0.549 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 300 | 22.5 | 0.811 | 0.811 | 0.000 | 0.990 |

## Insight Summary

- Positive-gain scene points: `27`
- Zero-gain scene points: `167`
- Negative-gain scene points: `22`
- Best gain scene: `case=`L12` rho_bg=`0.200` rho_pdb=`0.549` prb_share_pdb=`0.733` pdb_ms=`100` pdb_packet_kb=`7.5``
- Lowest center-retention scene: `case=`L17` rho_bg=`0.200` rho_pdb=`0.550` prb_share_pdb=`0.734` pdb_ms=`300` pdb_packet_kb=`45.1``

## Background Cost and Resource Analysis

- Mean center throughput retention across scene points: `1.009`
- Mean PRB utilization delta (proposed - baseline): `-0.000`
- Mean center PRB share delta: `0.001`
- Mean edge PRB share delta: `-0.001`

| Region | Scene Points | Share | Win Rate | Mean Delta PDB Satisfaction | Mean Center Retention | Mean Delta PRB Utilization |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| critical | 38 | 0.18 | 0.18 | -0.000 | 1.010 | -0.000 |
| feasible | 147 | 0.68 | 0.00 | 0.000 | 1.000 | -0.000 |
| overloaded | 31 | 0.14 | 0.65 | 0.005 | 1.051 | -0.000 |

## Feasible Boundary Snapshot

- Boundary feasibility snapshots remain available at the 95% and 90% thresholds.

| Threshold | Baseline Feasible Points | Proposed Feasible Points | Expanded Points | Regressed Points |
| ---: | ---: | ---: | ---: | ---: |
| 0.95 | 147 | 147 | 0 | 0 |
| 0.90 | 147 | 147 | 0 | 0 |

## Summary

- Proposed improves `27/216` load-ratio scene points; best gain is `0.022`.
- Mean center throughput retention is `1.009`; worst retained point is `0.925`.
- Boundary expansion adds `0` points at 95% and `0` points at 90%.
