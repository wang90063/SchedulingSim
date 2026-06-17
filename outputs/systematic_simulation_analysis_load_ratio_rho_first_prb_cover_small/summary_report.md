# Systematic Simulation Analysis

## Wireless Environment and Realization Bank

- reference_config: `configs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_merge.json`
- scene_bank_counts: `{'medium': 24, 'good': 24, 'poor': 16}`
- realization_bank_total_users: `64`
- repeat_count_per_scene_point: `5`

## Load-Ratio Scan Matrix

- `scan_mode = load_ratio`
- `rho_bg_values = [0.03, 0.07, 0.12, 0.2]`
- `rho_pdb_values = [0.03, 0.18, 0.3, 0.4, 0.45, 0.55]`
- `pdb_ms_values = [50, 100, 300]`
- `mapping_policy = {'background': {'kind': 'candidate_domain_solve_period', 'background_user_count_values': [32, 40, 48], 'background_packet_kb_values': [1.0, 1.5, 2.0], 'background_period_ms_range': [4.0, 400.0], 'anchor_background_user_count': 40, 'anchor_background_packet_kb': 2.0}, 'pdb': {'kind': 'candidate_domain_solve_packet', 'pdb_user_count_values': [4, 8], 'pdb_packet_kb_range': [0.1, 80.0], 'anchor_pdb_user_count': 4}}`
- `repeat_count = 5`
- Scene points evaluated: `432`
- Paired realization rows: `2160`
- Policy runs executed: `4320`

## Reporting Semantics

- `scene_summary.csv` aggregates policy-paired results at each rho-first scene point.
- Target `rho` values define the scan; actual `rho` values are recomputed after mapping and rounding.
- `PDB` timing shape remains a secondary axis, so equal target `rho_pdb` values can still be compared across different `pdb_ms` realizations.
- `background_mapping_policy` and `pdb_mapping_policy` record the candidate-domain solver used for each scene.
- capacity summaries are omitted for load-ratio outputs because the legacy feasible-range tables assume user-count axes rather than ratio coordinates.
- boundary_feasibility_files: `['boundary_feasibility_95.csv', 'boundary_feasibility_90.csv']`
- representative_case_files: `['typical_case_candidates.csv', 'typical_case_details.csv']`
- Aggregated scene points: `432`

## Panoramic PDB Gain Overview

- Scene points evaluated: `432`
- Proposed improves `65` points, ties `306` points, and regresses `61` points.
- Mean scene-level delta PDB satisfaction: `0.000`
- Mean scene-level center throughput retention: `1.005`

| case_label | target_rho_bg | target_rho_pdb | actual_rho_bg | actual_rho_pdb | prb_share_pdb | background_mapping_policy | pdb_mapping_policy | background_user_count | background_packet_kb | background_period_ms | pdb_user_count | pdb_ms | pdb_packet_kb | baseline_pdb_satisfaction | proposed_pdb_satisfaction | delta_pdb_satisfaction | center_retention |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L01 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 50 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 50 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 50 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 50 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 50 | 4.1 | 0.831 | 0.832 | 0.001 | 1.000 |
| L01 | 0.120 | 0.300 | 0.120 | 0.300 | 0.714 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 50 | 4.1 | 0.996 | 0.996 | 0.000 | 1.000 |
| L01 | 0.070 | 0.300 | 0.070 | 0.300 | 0.811 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 50 | 4.1 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.030 | 0.300 | 0.030 | 0.300 | 0.909 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 50 | 4.1 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 100 | 0.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 100 | 0.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 100 | 0.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 100 | 0.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 100 | 8.2 | 0.916 | 0.915 | -0.001 | 1.000 |
| L01 | 0.120 | 0.300 | 0.120 | 0.300 | 0.714 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 100 | 8.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.070 | 0.300 | 0.070 | 0.300 | 0.811 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 100 | 8.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.030 | 0.300 | 0.030 | 0.300 | 0.909 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 100 | 8.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.200 | 0.030 | 0.200 | 0.031 | 0.132 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 300 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.120 | 0.030 | 0.120 | 0.031 | 0.203 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 300 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.070 | 0.030 | 0.070 | 0.031 | 0.304 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 300 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.030 | 0.030 | 0.030 | 0.031 | 0.504 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 300 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 300 | 24.6 | 0.995 | 0.995 | 0.000 | 1.000 |
| L01 | 0.120 | 0.300 | 0.120 | 0.300 | 0.714 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 300 | 24.6 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.070 | 0.300 | 0.070 | 0.300 | 0.811 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 300 | 24.6 | 1.000 | 1.000 | 0.000 | 1.000 |
| L01 | 0.030 | 0.300 | 0.030 | 0.300 | 0.909 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 300 | 24.6 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 50 | 0.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 50 | 0.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 50 | 0.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 50 | 0.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.200 | 0.300 | 0.200 | 0.293 | 0.594 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 50 | 2 | 0.893 | 0.897 | 0.004 | 1.000 |
| L02 | 0.120 | 0.300 | 0.120 | 0.293 | 0.709 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 50 | 2 | 0.996 | 0.996 | 0.000 | 1.000 |
| L02 | 0.070 | 0.300 | 0.070 | 0.293 | 0.807 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 50 | 2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.030 | 0.300 | 0.030 | 0.293 | 0.907 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 50 | 2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 100 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 100 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 100 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 100 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 100 | 4.1 | 0.998 | 1.000 | 0.001 | 1.000 |
| L02 | 0.120 | 0.300 | 0.120 | 0.300 | 0.714 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 100 | 4.1 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.070 | 0.300 | 0.070 | 0.300 | 0.811 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 100 | 4.1 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.030 | 0.300 | 0.030 | 0.300 | 0.909 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 100 | 4.1 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 300 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 300 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 300 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 300 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 300 | 12.3 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.120 | 0.300 | 0.120 | 0.300 | 0.714 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 300 | 12.3 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.070 | 0.300 | 0.070 | 0.300 | 0.811 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 300 | 12.3 | 1.000 | 1.000 | 0.000 | 1.000 |
| L02 | 0.030 | 0.300 | 0.030 | 0.300 | 0.909 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 300 | 12.3 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.200 | 0.180 | 0.200 | 0.183 | 0.478 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 50 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.120 | 0.180 | 0.120 | 0.183 | 0.604 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 50 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.070 | 0.180 | 0.070 | 0.183 | 0.723 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 50 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.030 | 0.180 | 0.030 | 0.183 | 0.859 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 50 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.200 | 0.400 | 0.200 | 0.403 | 0.668 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 50 | 5.5 | 0.589 | 0.590 | 0.000 | 0.998 |
| L03 | 0.120 | 0.400 | 0.120 | 0.403 | 0.770 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 50 | 5.5 | 0.810 | 0.806 | -0.004 | 1.000 |
| L03 | 0.070 | 0.400 | 0.070 | 0.403 | 0.852 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 50 | 5.5 | 0.995 | 0.995 | 0.000 | 1.000 |
| L03 | 0.030 | 0.400 | 0.030 | 0.403 | 0.931 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 50 | 5.5 | 0.998 | 0.998 | 0.000 | 1.000 |
| L03 | 0.200 | 0.180 | 0.200 | 0.179 | 0.473 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 100 | 4.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.120 | 0.180 | 0.120 | 0.179 | 0.599 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 100 | 4.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.070 | 0.180 | 0.070 | 0.179 | 0.719 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 100 | 4.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.030 | 0.180 | 0.030 | 0.179 | 0.857 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 100 | 4.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.200 | 0.400 | 0.200 | 0.399 | 0.666 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 100 | 10.9 | 0.679 | 0.679 | 0.001 | 1.001 |
| L03 | 0.120 | 0.400 | 0.120 | 0.399 | 0.769 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 100 | 10.9 | 0.853 | 0.857 | 0.004 | 1.000 |
| L03 | 0.070 | 0.400 | 0.070 | 0.399 | 0.851 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 100 | 10.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.030 | 0.400 | 0.030 | 0.399 | 0.930 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 100 | 10.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.200 | 0.180 | 0.200 | 0.179 | 0.473 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 300 | 14.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.120 | 0.180 | 0.120 | 0.179 | 0.599 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 300 | 14.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.070 | 0.180 | 0.070 | 0.179 | 0.719 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 300 | 14.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.030 | 0.180 | 0.030 | 0.179 | 0.857 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 300 | 14.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.200 | 0.400 | 0.200 | 0.400 | 0.667 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 300 | 32.8 | 0.758 | 0.758 | 0.000 | 1.000 |
| L03 | 0.120 | 0.400 | 0.120 | 0.400 | 0.769 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 300 | 32.8 | 0.964 | 0.964 | 0.000 | 1.000 |
| L03 | 0.070 | 0.400 | 0.070 | 0.400 | 0.851 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 300 | 32.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L03 | 0.030 | 0.400 | 0.030 | 0.400 | 0.930 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 300 | 32.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.200 | 0.180 | 0.200 | 0.176 | 0.468 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 50 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.120 | 0.180 | 0.120 | 0.176 | 0.594 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 50 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.070 | 0.180 | 0.070 | 0.176 | 0.715 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 50 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.030 | 0.180 | 0.030 | 0.176 | 0.854 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 50 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.200 | 0.400 | 0.200 | 0.395 | 0.664 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 50 | 2.7 | 0.525 | 0.530 | 0.005 | 0.998 |
| L04 | 0.120 | 0.400 | 0.120 | 0.395 | 0.767 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 50 | 2.7 | 0.848 | 0.846 | -0.002 | 1.000 |
| L04 | 0.070 | 0.400 | 0.070 | 0.395 | 0.850 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 50 | 2.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.030 | 0.400 | 0.030 | 0.395 | 0.929 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 50 | 2.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.200 | 0.180 | 0.200 | 0.183 | 0.478 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 100 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.120 | 0.180 | 0.120 | 0.183 | 0.604 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 100 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.070 | 0.180 | 0.070 | 0.183 | 0.723 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 100 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.030 | 0.180 | 0.030 | 0.183 | 0.859 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 100 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.200 | 0.400 | 0.200 | 0.403 | 0.668 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 100 | 5.5 | 0.662 | 0.677 | 0.015 | 1.001 |
| L04 | 0.120 | 0.400 | 0.120 | 0.403 | 0.770 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 100 | 5.5 | 0.939 | 0.933 | -0.006 | 1.000 |
| L04 | 0.070 | 0.400 | 0.070 | 0.403 | 0.852 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 100 | 5.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.030 | 0.400 | 0.030 | 0.403 | 0.931 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 100 | 5.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.200 | 0.180 | 0.200 | 0.181 | 0.475 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 300 | 7.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.120 | 0.180 | 0.120 | 0.181 | 0.601 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 300 | 7.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.070 | 0.180 | 0.070 | 0.181 | 0.721 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 300 | 7.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.030 | 0.180 | 0.030 | 0.181 | 0.858 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 300 | 7.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.200 | 0.400 | 0.200 | 0.400 | 0.667 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 300 | 16.4 | 0.871 | 0.862 | -0.009 | 1.000 |
| L04 | 0.120 | 0.400 | 0.120 | 0.400 | 0.769 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 300 | 16.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.070 | 0.400 | 0.070 | 0.400 | 0.851 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 300 | 16.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L04 | 0.030 | 0.400 | 0.030 | 0.400 | 0.930 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 300 | 16.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L05 | 0.200 | 0.450 | 0.200 | 0.447 | 0.691 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 50 | 6.1 | 0.504 | 0.509 | 0.005 | 1.008 |
| L05 | 0.120 | 0.450 | 0.120 | 0.447 | 0.788 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 50 | 6.1 | 0.774 | 0.774 | 0.000 | 0.998 |
| L05 | 0.070 | 0.450 | 0.070 | 0.447 | 0.865 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 50 | 6.1 | 0.854 | 0.855 | 0.002 | 1.000 |
| L05 | 0.030 | 0.450 | 0.030 | 0.447 | 0.937 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 50 | 6.1 | 0.981 | 0.981 | 0.000 | 1.000 |
| L05 | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 50 | 7.5 | 0.354 | 0.358 | 0.005 | 0.940 |
| L05 | 0.120 | 0.550 | 0.120 | 0.549 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 50 | 7.5 | 0.541 | 0.546 | 0.005 | 0.973 |
| L05 | 0.070 | 0.550 | 0.070 | 0.549 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 50 | 7.5 | 0.690 | 0.688 | -0.002 | 0.941 |
| L05 | 0.030 | 0.550 | 0.030 | 0.549 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 50 | 7.5 | 0.799 | 0.799 | 0.000 | 1.016 |
| L05 | 0.200 | 0.450 | 0.200 | 0.450 | 0.693 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 100 | 12.3 | 0.559 | 0.554 | -0.006 | 1.001 |
| L05 | 0.120 | 0.450 | 0.120 | 0.450 | 0.790 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 100 | 12.3 | 0.804 | 0.804 | 0.000 | 0.999 |
| L05 | 0.070 | 0.450 | 0.070 | 0.450 | 0.866 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 100 | 12.3 | 0.882 | 0.885 | 0.003 | 1.000 |
| L05 | 0.030 | 0.450 | 0.030 | 0.450 | 0.938 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 100 | 12.3 | 1.000 | 1.000 | 0.000 | 1.000 |
| L05 | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 100 | 15 | 0.422 | 0.426 | 0.004 | 0.979 |
| L05 | 0.120 | 0.550 | 0.120 | 0.549 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 100 | 15 | 0.614 | 0.613 | -0.001 | 1.234 |
| L05 | 0.070 | 0.550 | 0.070 | 0.549 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 100 | 15 | 0.796 | 0.796 | 0.000 | 1.007 |
| L05 | 0.030 | 0.550 | 0.030 | 0.549 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 100 | 15 | 0.810 | 0.810 | 0.000 | 0.996 |
| L05 | 0.200 | 0.450 | 0.200 | 0.450 | 0.693 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 300 | 36.9 | 0.655 | 0.654 | -0.001 | 1.003 |
| L05 | 0.120 | 0.450 | 0.120 | 0.450 | 0.790 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 300 | 36.9 | 0.815 | 0.815 | 0.000 | 1.000 |
| L05 | 0.070 | 0.450 | 0.070 | 0.450 | 0.866 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 300 | 36.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L05 | 0.030 | 0.450 | 0.030 | 0.450 | 0.938 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 300 | 36.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L05 | 0.200 | 0.550 | 0.200 | 0.550 | 0.734 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 4 | 300 | 45.1 | 0.492 | 0.502 | 0.010 | 0.985 |
| L05 | 0.120 | 0.550 | 0.120 | 0.550 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 4 | 300 | 45.1 | 0.676 | 0.676 | 0.000 | 1.060 |
| L05 | 0.070 | 0.550 | 0.070 | 0.550 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 4 | 300 | 45.1 | 0.811 | 0.811 | 0.000 | 1.026 |
| L05 | 0.030 | 0.550 | 0.030 | 0.550 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 4 | 300 | 45.1 | 0.847 | 0.847 | 0.000 | 0.990 |
| L06 | 0.200 | 0.450 | 0.200 | 0.454 | 0.694 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 50 | 3.1 | 0.316 | 0.325 | 0.009 | 1.000 |
| L06 | 0.120 | 0.450 | 0.120 | 0.454 | 0.791 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 50 | 3.1 | 0.483 | 0.481 | -0.002 | 1.000 |
| L06 | 0.070 | 0.450 | 0.070 | 0.454 | 0.866 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 50 | 3.1 | 0.858 | 0.852 | -0.006 | 1.000 |
| L06 | 0.030 | 0.450 | 0.030 | 0.454 | 0.938 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 50 | 3.1 | 0.997 | 0.997 | 0.000 | 1.000 |
| L06 | 0.200 | 0.550 | 0.200 | 0.557 | 0.736 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 50 | 3.8 | 0.105 | 0.122 | 0.016 | 0.942 |
| L06 | 0.120 | 0.550 | 0.120 | 0.557 | 0.823 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 50 | 3.8 | 0.220 | 0.221 | 0.002 | 1.122 |
| L06 | 0.070 | 0.550 | 0.070 | 0.557 | 0.888 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 50 | 3.8 | 0.346 | 0.336 | -0.010 | 1.016 |
| L06 | 0.030 | 0.550 | 0.030 | 0.557 | 0.949 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 50 | 3.8 | 0.605 | 0.601 | -0.004 | 0.999 |
| L06 | 0.200 | 0.450 | 0.200 | 0.447 | 0.691 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 100 | 6.1 | 0.480 | 0.488 | 0.008 | 1.000 |
| L06 | 0.120 | 0.450 | 0.120 | 0.447 | 0.788 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 100 | 6.1 | 0.803 | 0.802 | -0.001 | 1.000 |
| L06 | 0.070 | 0.450 | 0.070 | 0.447 | 0.865 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 100 | 6.1 | 0.997 | 0.997 | 0.000 | 1.000 |
| L06 | 0.030 | 0.450 | 0.030 | 0.447 | 0.937 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 100 | 6.1 | 1.000 | 1.000 | 0.000 | 1.000 |
| L06 | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 100 | 7.5 | 0.227 | 0.238 | 0.011 | 1.075 |
| L06 | 0.120 | 0.550 | 0.120 | 0.549 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 100 | 7.5 | 0.317 | 0.315 | -0.002 | 1.008 |
| L06 | 0.070 | 0.550 | 0.070 | 0.549 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 100 | 7.5 | 0.536 | 0.525 | -0.011 | 1.027 |
| L06 | 0.030 | 0.550 | 0.030 | 0.549 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 100 | 7.5 | 0.826 | 0.826 | 0.000 | 1.000 |
| L06 | 0.200 | 0.450 | 0.200 | 0.449 | 0.692 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 300 | 18.4 | 0.557 | 0.561 | 0.004 | 1.004 |
| L06 | 0.120 | 0.450 | 0.120 | 0.449 | 0.789 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 300 | 18.4 | 0.901 | 0.900 | -0.001 | 1.000 |
| L06 | 0.070 | 0.450 | 0.070 | 0.449 | 0.865 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 300 | 18.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L06 | 0.030 | 0.450 | 0.030 | 0.449 | 0.937 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 300 | 18.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L06 | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 38.8 | 8 | 300 | 22.5 | 0.304 | 0.321 | 0.016 | 1.073 |
| L06 | 0.120 | 0.550 | 0.120 | 0.549 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 64.6 | 8 | 300 | 22.5 | 0.454 | 0.449 | -0.005 | 1.052 |
| L06 | 0.070 | 0.550 | 0.070 | 0.549 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 110.8 | 8 | 300 | 22.5 | 0.834 | 0.834 | 0.000 | 1.007 |
| L06 | 0.030 | 0.550 | 0.030 | 0.549 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 32 | 2 | 258.5 | 8 | 300 | 22.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 50 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 50 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 50 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 50 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 50 | 4.1 | 0.794 | 0.792 | -0.002 | 1.000 |
| L07 | 0.120 | 0.300 | 0.120 | 0.300 | 0.715 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 50 | 4.1 | 0.978 | 0.978 | 0.000 | 1.000 |
| L07 | 0.070 | 0.300 | 0.070 | 0.300 | 0.811 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 50 | 4.1 | 0.993 | 0.993 | 0.000 | 1.000 |
| L07 | 0.030 | 0.300 | 0.030 | 0.300 | 0.909 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 50 | 4.1 | 0.997 | 0.997 | 0.000 | 1.000 |
| L07 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 100 | 0.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 100 | 0.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 100 | 0.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 100 | 0.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 100 | 8.2 | 0.858 | 0.856 | -0.002 | 1.000 |
| L07 | 0.120 | 0.300 | 0.120 | 0.300 | 0.715 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 100 | 8.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.070 | 0.300 | 0.070 | 0.300 | 0.811 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 100 | 8.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.030 | 0.300 | 0.030 | 0.300 | 0.909 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 100 | 8.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.200 | 0.030 | 0.200 | 0.031 | 0.132 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 300 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.120 | 0.030 | 0.120 | 0.031 | 0.203 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 300 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.070 | 0.030 | 0.070 | 0.031 | 0.304 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 300 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.030 | 0.030 | 0.030 | 0.031 | 0.504 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 300 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 300 | 24.6 | 0.918 | 0.918 | 0.000 | 1.000 |
| L07 | 0.120 | 0.300 | 0.120 | 0.300 | 0.715 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 300 | 24.6 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.070 | 0.300 | 0.070 | 0.300 | 0.811 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 300 | 24.6 | 1.000 | 1.000 | 0.000 | 1.000 |
| L07 | 0.030 | 0.300 | 0.030 | 0.300 | 0.909 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 300 | 24.6 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 50 | 0.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 50 | 0.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 50 | 0.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 50 | 0.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.200 | 0.300 | 0.200 | 0.293 | 0.594 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 50 | 2 | 0.819 | 0.817 | -0.001 | 1.000 |
| L08 | 0.120 | 0.300 | 0.120 | 0.293 | 0.709 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 50 | 2 | 0.978 | 0.978 | 0.000 | 1.000 |
| L08 | 0.070 | 0.300 | 0.070 | 0.293 | 0.807 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 50 | 2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.030 | 0.300 | 0.030 | 0.293 | 0.907 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 50 | 2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 100 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 100 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 100 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 100 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 100 | 4.1 | 0.992 | 0.994 | 0.002 | 1.000 |
| L08 | 0.120 | 0.300 | 0.120 | 0.300 | 0.715 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 100 | 4.1 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.070 | 0.300 | 0.070 | 0.300 | 0.811 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 100 | 4.1 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.030 | 0.300 | 0.030 | 0.300 | 0.909 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 100 | 4.1 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 300 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 300 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 300 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 300 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 300 | 12.3 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.120 | 0.300 | 0.120 | 0.300 | 0.715 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 300 | 12.3 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.070 | 0.300 | 0.070 | 0.300 | 0.811 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 300 | 12.3 | 1.000 | 1.000 | 0.000 | 1.000 |
| L08 | 0.030 | 0.300 | 0.030 | 0.300 | 0.909 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 300 | 12.3 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.200 | 0.180 | 0.200 | 0.183 | 0.478 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 50 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.120 | 0.180 | 0.120 | 0.183 | 0.604 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 50 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.070 | 0.180 | 0.070 | 0.183 | 0.723 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 50 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.030 | 0.180 | 0.030 | 0.183 | 0.859 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 50 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.200 | 0.400 | 0.200 | 0.403 | 0.668 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 50 | 5.5 | 0.536 | 0.532 | -0.005 | 1.001 |
| L09 | 0.120 | 0.400 | 0.120 | 0.403 | 0.771 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 50 | 5.5 | 0.803 | 0.803 | 0.000 | 1.000 |
| L09 | 0.070 | 0.400 | 0.070 | 0.403 | 0.852 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 50 | 5.5 | 0.973 | 0.973 | 0.000 | 1.000 |
| L09 | 0.030 | 0.400 | 0.030 | 0.403 | 0.931 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 50 | 5.5 | 0.987 | 0.987 | 0.000 | 1.000 |
| L09 | 0.200 | 0.180 | 0.200 | 0.179 | 0.473 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 100 | 4.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.120 | 0.180 | 0.120 | 0.179 | 0.599 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 100 | 4.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.070 | 0.180 | 0.070 | 0.179 | 0.719 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 100 | 4.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.030 | 0.180 | 0.030 | 0.179 | 0.857 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 100 | 4.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.200 | 0.400 | 0.200 | 0.399 | 0.666 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 100 | 10.9 | 0.622 | 0.625 | 0.003 | 1.000 |
| L09 | 0.120 | 0.400 | 0.120 | 0.399 | 0.769 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 100 | 10.9 | 0.834 | 0.832 | -0.002 | 1.000 |
| L09 | 0.070 | 0.400 | 0.070 | 0.399 | 0.851 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 100 | 10.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.030 | 0.400 | 0.030 | 0.399 | 0.930 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 100 | 10.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.200 | 0.180 | 0.200 | 0.179 | 0.473 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 300 | 14.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.120 | 0.180 | 0.120 | 0.179 | 0.599 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 300 | 14.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.070 | 0.180 | 0.070 | 0.179 | 0.719 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 300 | 14.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.030 | 0.180 | 0.030 | 0.179 | 0.857 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 300 | 14.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.200 | 0.400 | 0.200 | 0.400 | 0.667 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 300 | 32.8 | 0.714 | 0.714 | 0.000 | 1.002 |
| L09 | 0.120 | 0.400 | 0.120 | 0.400 | 0.769 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 300 | 32.8 | 0.883 | 0.883 | 0.000 | 1.000 |
| L09 | 0.070 | 0.400 | 0.070 | 0.400 | 0.851 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 300 | 32.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L09 | 0.030 | 0.400 | 0.030 | 0.400 | 0.930 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 300 | 32.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.200 | 0.180 | 0.200 | 0.176 | 0.468 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 50 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.120 | 0.180 | 0.120 | 0.176 | 0.594 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 50 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.070 | 0.180 | 0.070 | 0.176 | 0.715 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 50 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.030 | 0.180 | 0.030 | 0.176 | 0.854 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 50 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.200 | 0.400 | 0.200 | 0.395 | 0.664 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 50 | 2.7 | 0.477 | 0.476 | -0.002 | 1.000 |
| L10 | 0.120 | 0.400 | 0.120 | 0.395 | 0.767 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 50 | 2.7 | 0.822 | 0.822 | -0.000 | 1.000 |
| L10 | 0.070 | 0.400 | 0.070 | 0.395 | 0.850 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 50 | 2.7 | 0.999 | 0.999 | 0.000 | 1.000 |
| L10 | 0.030 | 0.400 | 0.030 | 0.395 | 0.929 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 50 | 2.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.200 | 0.180 | 0.200 | 0.183 | 0.478 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 100 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.120 | 0.180 | 0.120 | 0.183 | 0.604 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 100 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.070 | 0.180 | 0.070 | 0.183 | 0.723 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 100 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.030 | 0.180 | 0.030 | 0.183 | 0.859 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 100 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.200 | 0.400 | 0.200 | 0.403 | 0.668 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 100 | 5.5 | 0.596 | 0.601 | 0.006 | 1.000 |
| L10 | 0.120 | 0.400 | 0.120 | 0.403 | 0.771 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 100 | 5.5 | 0.933 | 0.947 | 0.014 | 1.000 |
| L10 | 0.070 | 0.400 | 0.070 | 0.403 | 0.852 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 100 | 5.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.030 | 0.400 | 0.030 | 0.403 | 0.931 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 100 | 5.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.200 | 0.180 | 0.200 | 0.181 | 0.475 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 300 | 7.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.120 | 0.180 | 0.120 | 0.181 | 0.601 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 300 | 7.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.070 | 0.180 | 0.070 | 0.181 | 0.721 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 300 | 7.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.030 | 0.180 | 0.030 | 0.181 | 0.858 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 300 | 7.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.200 | 0.400 | 0.200 | 0.400 | 0.667 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 300 | 16.4 | 0.775 | 0.771 | -0.004 | 1.000 |
| L10 | 0.120 | 0.400 | 0.120 | 0.400 | 0.769 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 300 | 16.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.070 | 0.400 | 0.070 | 0.400 | 0.851 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 300 | 16.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L10 | 0.030 | 0.400 | 0.030 | 0.400 | 0.930 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 300 | 16.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L11 | 0.200 | 0.450 | 0.200 | 0.447 | 0.691 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 50 | 6.1 | 0.476 | 0.478 | 0.003 | 1.032 |
| L11 | 0.120 | 0.450 | 0.120 | 0.447 | 0.788 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 50 | 6.1 | 0.738 | 0.739 | 0.001 | 1.001 |
| L11 | 0.070 | 0.450 | 0.070 | 0.447 | 0.865 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 50 | 6.1 | 0.835 | 0.836 | 0.001 | 1.000 |
| L11 | 0.030 | 0.450 | 0.030 | 0.447 | 0.937 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 50 | 6.1 | 0.970 | 0.970 | 0.000 | 1.000 |
| L11 | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 50 | 7.5 | 0.330 | 0.332 | 0.002 | 1.079 |
| L11 | 0.120 | 0.550 | 0.120 | 0.549 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 50 | 7.5 | 0.505 | 0.509 | 0.004 | 1.048 |
| L11 | 0.070 | 0.550 | 0.070 | 0.549 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 50 | 7.5 | 0.663 | 0.661 | -0.003 | 1.014 |
| L11 | 0.030 | 0.550 | 0.030 | 0.549 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 50 | 7.5 | 0.786 | 0.786 | 0.000 | 1.003 |
| L11 | 0.200 | 0.450 | 0.200 | 0.450 | 0.693 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 100 | 12.3 | 0.505 | 0.504 | -0.001 | 1.049 |
| L11 | 0.120 | 0.450 | 0.120 | 0.450 | 0.790 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 100 | 12.3 | 0.800 | 0.800 | 0.000 | 1.000 |
| L11 | 0.070 | 0.450 | 0.070 | 0.450 | 0.866 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 100 | 12.3 | 0.871 | 0.871 | 0.001 | 1.000 |
| L11 | 0.030 | 0.450 | 0.030 | 0.450 | 0.938 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 100 | 12.3 | 1.000 | 1.000 | 0.000 | 1.000 |
| L11 | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 100 | 15 | 0.388 | 0.383 | -0.005 | 1.060 |
| L11 | 0.120 | 0.550 | 0.120 | 0.549 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 100 | 15 | 0.582 | 0.582 | 0.000 | 0.983 |
| L11 | 0.070 | 0.550 | 0.070 | 0.549 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 100 | 15 | 0.788 | 0.788 | 0.000 | 1.001 |
| L11 | 0.030 | 0.550 | 0.030 | 0.549 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 100 | 15 | 0.810 | 0.810 | 0.000 | 0.996 |
| L11 | 0.200 | 0.450 | 0.200 | 0.450 | 0.693 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 300 | 36.9 | 0.584 | 0.584 | 0.000 | 0.992 |
| L11 | 0.120 | 0.450 | 0.120 | 0.450 | 0.790 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 300 | 36.9 | 0.814 | 0.814 | 0.000 | 1.000 |
| L11 | 0.070 | 0.450 | 0.070 | 0.450 | 0.866 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 300 | 36.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L11 | 0.030 | 0.450 | 0.030 | 0.450 | 0.938 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 300 | 36.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L11 | 0.200 | 0.550 | 0.200 | 0.550 | 0.734 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 4 | 300 | 45.1 | 0.468 | 0.471 | 0.003 | 1.006 |
| L11 | 0.120 | 0.550 | 0.120 | 0.550 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 4 | 300 | 45.1 | 0.673 | 0.667 | -0.006 | 1.006 |
| L11 | 0.070 | 0.550 | 0.070 | 0.550 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 4 | 300 | 45.1 | 0.808 | 0.808 | 0.000 | 1.067 |
| L11 | 0.030 | 0.550 | 0.030 | 0.550 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 4 | 300 | 45.1 | 0.838 | 0.838 | 0.000 | 0.997 |
| L12 | 0.200 | 0.450 | 0.200 | 0.454 | 0.694 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 50 | 3.1 | 0.270 | 0.275 | 0.005 | 1.004 |
| L12 | 0.120 | 0.450 | 0.120 | 0.454 | 0.791 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 50 | 3.1 | 0.476 | 0.484 | 0.008 | 1.000 |
| L12 | 0.070 | 0.450 | 0.070 | 0.454 | 0.866 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 50 | 3.1 | 0.844 | 0.844 | -0.000 | 1.000 |
| L12 | 0.030 | 0.450 | 0.030 | 0.454 | 0.938 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 50 | 3.1 | 0.993 | 0.993 | 0.000 | 1.000 |
| L12 | 0.200 | 0.550 | 0.200 | 0.557 | 0.736 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 50 | 3.8 | 0.089 | 0.102 | 0.014 | 1.188 |
| L12 | 0.120 | 0.550 | 0.120 | 0.557 | 0.823 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 50 | 3.8 | 0.200 | 0.206 | 0.007 | 1.091 |
| L12 | 0.070 | 0.550 | 0.070 | 0.557 | 0.888 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 50 | 3.8 | 0.330 | 0.342 | 0.011 | 1.015 |
| L12 | 0.030 | 0.550 | 0.030 | 0.557 | 0.949 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 50 | 3.8 | 0.586 | 0.595 | 0.009 | 1.003 |
| L12 | 0.200 | 0.450 | 0.200 | 0.447 | 0.691 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 100 | 6.1 | 0.429 | 0.426 | -0.003 | 1.003 |
| L12 | 0.120 | 0.450 | 0.120 | 0.447 | 0.788 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 100 | 6.1 | 0.756 | 0.756 | 0.000 | 1.000 |
| L12 | 0.070 | 0.450 | 0.070 | 0.447 | 0.865 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 100 | 6.1 | 0.986 | 0.986 | 0.000 | 1.000 |
| L12 | 0.030 | 0.450 | 0.030 | 0.447 | 0.937 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 100 | 6.1 | 1.000 | 1.000 | 0.000 | 1.000 |
| L12 | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 100 | 7.5 | 0.186 | 0.209 | 0.022 | 1.036 |
| L12 | 0.120 | 0.550 | 0.120 | 0.549 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 100 | 7.5 | 0.285 | 0.288 | 0.003 | 1.063 |
| L12 | 0.070 | 0.550 | 0.070 | 0.549 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 100 | 7.5 | 0.523 | 0.528 | 0.005 | 1.019 |
| L12 | 0.030 | 0.550 | 0.030 | 0.549 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 100 | 7.5 | 0.826 | 0.821 | -0.005 | 1.000 |
| L12 | 0.200 | 0.450 | 0.200 | 0.449 | 0.692 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 300 | 18.4 | 0.496 | 0.499 | 0.002 | 1.005 |
| L12 | 0.120 | 0.450 | 0.120 | 0.449 | 0.789 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 300 | 18.4 | 0.886 | 0.887 | 0.001 | 1.000 |
| L12 | 0.070 | 0.450 | 0.070 | 0.449 | 0.865 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 300 | 18.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L12 | 0.030 | 0.450 | 0.030 | 0.449 | 0.937 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 300 | 18.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L12 | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 48.5 | 8 | 300 | 22.5 | 0.284 | 0.281 | -0.003 | 0.969 |
| L12 | 0.120 | 0.550 | 0.120 | 0.549 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 80.8 | 8 | 300 | 22.5 | 0.405 | 0.419 | 0.014 | 1.020 |
| L12 | 0.070 | 0.550 | 0.070 | 0.549 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 138.5 | 8 | 300 | 22.5 | 0.833 | 0.833 | 0.000 | 0.989 |
| L12 | 0.030 | 0.550 | 0.030 | 0.549 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 40 | 2 | 323.1 | 8 | 300 | 22.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 50 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 50 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 50 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 50 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.120 | 0.300 | 0.120 | 0.300 | 0.714 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 50 | 4.1 | 0.997 | 0.997 | 0.000 | 1.000 |
| L13 | 0.030 | 0.300 | 0.030 | 0.300 | 0.909 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 50 | 4.1 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 50 | 4.1 | 0.761 | 0.765 | 0.004 | 1.000 |
| L13 | 0.070 | 0.300 | 0.070 | 0.300 | 0.811 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 50 | 4.1 | 0.984 | 0.984 | 0.000 | 1.000 |
| L13 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 100 | 0.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 100 | 0.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 100 | 0.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 100 | 0.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.120 | 0.300 | 0.120 | 0.300 | 0.714 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 100 | 8.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.030 | 0.300 | 0.030 | 0.300 | 0.909 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 100 | 8.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 100 | 8.2 | 0.838 | 0.833 | -0.004 | 1.000 |
| L13 | 0.070 | 0.300 | 0.070 | 0.300 | 0.811 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 100 | 8.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.120 | 0.030 | 0.120 | 0.031 | 0.203 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 300 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.030 | 0.030 | 0.030 | 0.031 | 0.504 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 300 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.200 | 0.030 | 0.200 | 0.031 | 0.132 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 300 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.070 | 0.030 | 0.070 | 0.031 | 0.304 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 300 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.120 | 0.300 | 0.120 | 0.300 | 0.714 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 300 | 24.6 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.030 | 0.300 | 0.030 | 0.300 | 0.909 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 300 | 24.6 | 1.000 | 1.000 | 0.000 | 1.000 |
| L13 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 300 | 24.6 | 0.912 | 0.903 | -0.009 | 1.000 |
| L13 | 0.070 | 0.300 | 0.070 | 0.300 | 0.811 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 300 | 24.6 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 50 | 0.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 50 | 0.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 50 | 0.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 50 | 0.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.120 | 0.300 | 0.120 | 0.293 | 0.709 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 50 | 2 | 0.984 | 0.984 | 0.000 | 1.000 |
| L14 | 0.030 | 0.300 | 0.030 | 0.293 | 0.907 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 50 | 2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.200 | 0.300 | 0.200 | 0.293 | 0.594 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 50 | 2 | 0.750 | 0.742 | -0.008 | 1.000 |
| L14 | 0.070 | 0.300 | 0.070 | 0.293 | 0.807 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 50 | 2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 100 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 100 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 100 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 100 | 0.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.120 | 0.300 | 0.120 | 0.300 | 0.714 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 100 | 4.1 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.030 | 0.300 | 0.030 | 0.300 | 0.909 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 100 | 4.1 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 100 | 4.1 | 0.966 | 0.970 | 0.004 | 1.000 |
| L14 | 0.070 | 0.300 | 0.070 | 0.300 | 0.811 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 100 | 4.1 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.120 | 0.030 | 0.120 | 0.029 | 0.196 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 300 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.030 | 0.030 | 0.030 | 0.029 | 0.494 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 300 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 300 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.070 | 0.030 | 0.070 | 0.029 | 0.295 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 300 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.120 | 0.300 | 0.120 | 0.300 | 0.714 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 300 | 12.3 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.030 | 0.300 | 0.030 | 0.300 | 0.909 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 300 | 12.3 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.200 | 0.300 | 0.200 | 0.300 | 0.600 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 300 | 12.3 | 1.000 | 1.000 | 0.000 | 1.000 |
| L14 | 0.070 | 0.300 | 0.070 | 0.300 | 0.811 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 300 | 12.3 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.120 | 0.180 | 0.120 | 0.183 | 0.604 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 50 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.030 | 0.180 | 0.030 | 0.183 | 0.859 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 50 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.200 | 0.180 | 0.200 | 0.183 | 0.478 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 50 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.070 | 0.180 | 0.070 | 0.183 | 0.723 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 50 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.120 | 0.400 | 0.120 | 0.403 | 0.770 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 50 | 5.5 | 0.807 | 0.807 | -0.001 | 1.000 |
| L15 | 0.030 | 0.400 | 0.030 | 0.403 | 0.931 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 50 | 5.5 | 0.997 | 0.997 | 0.000 | 1.000 |
| L15 | 0.200 | 0.400 | 0.200 | 0.403 | 0.668 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 50 | 5.5 | 0.504 | 0.501 | -0.003 | 1.002 |
| L15 | 0.070 | 0.400 | 0.070 | 0.403 | 0.852 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 50 | 5.5 | 0.959 | 0.959 | 0.000 | 1.000 |
| L15 | 0.120 | 0.180 | 0.120 | 0.179 | 0.599 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 100 | 4.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.030 | 0.180 | 0.030 | 0.179 | 0.857 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 100 | 4.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.200 | 0.180 | 0.200 | 0.179 | 0.473 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 100 | 4.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.070 | 0.180 | 0.070 | 0.179 | 0.719 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 100 | 4.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.120 | 0.400 | 0.120 | 0.399 | 0.769 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 100 | 10.9 | 0.863 | 0.863 | 0.000 | 1.000 |
| L15 | 0.030 | 0.400 | 0.030 | 0.399 | 0.930 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 100 | 10.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.200 | 0.400 | 0.200 | 0.399 | 0.666 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 100 | 10.9 | 0.547 | 0.546 | -0.002 | 1.001 |
| L15 | 0.070 | 0.400 | 0.070 | 0.399 | 0.851 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 100 | 10.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.120 | 0.180 | 0.120 | 0.179 | 0.599 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 300 | 14.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.030 | 0.180 | 0.030 | 0.179 | 0.857 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 300 | 14.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.200 | 0.180 | 0.200 | 0.179 | 0.473 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 300 | 14.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.070 | 0.180 | 0.070 | 0.179 | 0.719 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 300 | 14.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.120 | 0.400 | 0.120 | 0.400 | 0.769 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 300 | 32.8 | 0.997 | 0.997 | 0.000 | 1.000 |
| L15 | 0.030 | 0.400 | 0.030 | 0.400 | 0.930 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 300 | 32.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L15 | 0.200 | 0.400 | 0.200 | 0.400 | 0.667 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 300 | 32.8 | 0.657 | 0.654 | -0.003 | 1.002 |
| L15 | 0.070 | 0.400 | 0.070 | 0.400 | 0.851 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 300 | 32.8 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.120 | 0.180 | 0.120 | 0.176 | 0.594 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 50 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.030 | 0.180 | 0.030 | 0.176 | 0.854 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 50 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.200 | 0.180 | 0.200 | 0.176 | 0.468 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 50 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.070 | 0.180 | 0.070 | 0.176 | 0.715 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 50 | 1.2 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.120 | 0.400 | 0.120 | 0.395 | 0.767 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 50 | 2.7 | 0.772 | 0.788 | 0.016 | 1.000 |
| L16 | 0.030 | 0.400 | 0.030 | 0.395 | 0.929 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 50 | 2.7 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.200 | 0.400 | 0.200 | 0.395 | 0.664 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 50 | 2.7 | 0.428 | 0.428 | 0.000 | 0.999 |
| L16 | 0.070 | 0.400 | 0.070 | 0.395 | 0.850 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 50 | 2.7 | 0.999 | 0.999 | 0.000 | 1.000 |
| L16 | 0.120 | 0.180 | 0.120 | 0.183 | 0.604 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 100 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.030 | 0.180 | 0.030 | 0.183 | 0.859 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 100 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.200 | 0.180 | 0.200 | 0.183 | 0.478 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 100 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.070 | 0.180 | 0.070 | 0.183 | 0.723 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 100 | 2.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.120 | 0.400 | 0.120 | 0.403 | 0.770 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 100 | 5.5 | 0.961 | 0.957 | -0.004 | 1.000 |
| L16 | 0.030 | 0.400 | 0.030 | 0.403 | 0.931 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 100 | 5.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.200 | 0.400 | 0.200 | 0.403 | 0.668 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 100 | 5.5 | 0.515 | 0.519 | 0.003 | 0.999 |
| L16 | 0.070 | 0.400 | 0.070 | 0.403 | 0.852 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 100 | 5.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.120 | 0.180 | 0.120 | 0.181 | 0.601 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 300 | 7.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.030 | 0.180 | 0.030 | 0.181 | 0.858 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 300 | 7.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.200 | 0.180 | 0.200 | 0.181 | 0.475 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 300 | 7.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.070 | 0.180 | 0.070 | 0.181 | 0.721 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 300 | 7.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.120 | 0.400 | 0.120 | 0.400 | 0.769 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 300 | 16.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.030 | 0.400 | 0.030 | 0.400 | 0.930 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 300 | 16.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L16 | 0.200 | 0.400 | 0.200 | 0.400 | 0.667 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 300 | 16.4 | 0.620 | 0.619 | -0.001 | 0.999 |
| L16 | 0.070 | 0.400 | 0.070 | 0.400 | 0.851 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 300 | 16.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L17 | 0.120 | 0.450 | 0.120 | 0.447 | 0.788 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 50 | 6.1 | 0.725 | 0.724 | -0.001 | 1.000 |
| L17 | 0.030 | 0.450 | 0.030 | 0.447 | 0.937 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 50 | 6.1 | 0.980 | 0.980 | 0.000 | 1.000 |
| L17 | 0.200 | 0.450 | 0.200 | 0.447 | 0.691 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 50 | 6.1 | 0.457 | 0.459 | 0.002 | 1.031 |
| L17 | 0.070 | 0.450 | 0.070 | 0.447 | 0.865 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 50 | 6.1 | 0.823 | 0.824 | 0.001 | 1.000 |
| L17 | 0.120 | 0.550 | 0.120 | 0.549 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 50 | 7.5 | 0.513 | 0.510 | -0.003 | 1.016 |
| L17 | 0.030 | 0.550 | 0.030 | 0.549 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 50 | 7.5 | 0.790 | 0.790 | 0.000 | 1.014 |
| L17 | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 50 | 7.5 | 0.320 | 0.317 | -0.004 | 1.058 |
| L17 | 0.070 | 0.550 | 0.070 | 0.549 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 50 | 7.5 | 0.638 | 0.633 | -0.004 | 0.980 |
| L17 | 0.120 | 0.450 | 0.120 | 0.450 | 0.790 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 100 | 12.3 | 0.798 | 0.798 | 0.000 | 1.000 |
| L17 | 0.030 | 0.450 | 0.030 | 0.450 | 0.938 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 100 | 12.3 | 1.000 | 1.000 | 0.000 | 1.000 |
| L17 | 0.200 | 0.450 | 0.200 | 0.450 | 0.693 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 100 | 12.3 | 0.485 | 0.483 | -0.002 | 1.013 |
| L17 | 0.070 | 0.450 | 0.070 | 0.450 | 0.866 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 100 | 12.3 | 0.875 | 0.869 | -0.007 | 1.000 |
| L17 | 0.120 | 0.550 | 0.120 | 0.549 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 100 | 15 | 0.584 | 0.580 | -0.004 | 1.021 |
| L17 | 0.030 | 0.550 | 0.030 | 0.549 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 100 | 15 | 0.811 | 0.811 | 0.000 | 1.004 |
| L17 | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 100 | 15 | 0.390 | 0.390 | -0.000 | 1.153 |
| L17 | 0.070 | 0.550 | 0.070 | 0.549 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 100 | 15 | 0.751 | 0.759 | 0.008 | 0.992 |
| L17 | 0.120 | 0.450 | 0.120 | 0.450 | 0.790 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 300 | 36.9 | 0.818 | 0.818 | 0.000 | 1.002 |
| L17 | 0.030 | 0.450 | 0.030 | 0.450 | 0.938 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 300 | 36.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L17 | 0.200 | 0.450 | 0.200 | 0.450 | 0.693 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 300 | 36.9 | 0.562 | 0.560 | -0.001 | 1.013 |
| L17 | 0.070 | 0.450 | 0.070 | 0.450 | 0.866 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 300 | 36.9 | 1.000 | 1.000 | 0.000 | 1.000 |
| L17 | 0.120 | 0.550 | 0.120 | 0.550 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 4 | 300 | 45.1 | 0.666 | 0.657 | -0.009 | 0.969 |
| L17 | 0.030 | 0.550 | 0.030 | 0.550 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 4 | 300 | 45.1 | 0.848 | 0.848 | 0.000 | 1.001 |
| L17 | 0.200 | 0.550 | 0.200 | 0.550 | 0.734 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 4 | 300 | 45.1 | 0.467 | 0.465 | -0.001 | 0.925 |
| L17 | 0.070 | 0.550 | 0.070 | 0.550 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 4 | 300 | 45.1 | 0.811 | 0.811 | 0.000 | 1.003 |
| L18 | 0.120 | 0.450 | 0.120 | 0.454 | 0.791 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 50 | 3.1 | 0.418 | 0.420 | 0.001 | 0.999 |
| L18 | 0.030 | 0.450 | 0.030 | 0.454 | 0.938 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 50 | 3.1 | 0.998 | 0.998 | 0.000 | 1.000 |
| L18 | 0.200 | 0.450 | 0.200 | 0.454 | 0.694 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 50 | 3.1 | 0.245 | 0.242 | -0.003 | 1.004 |
| L18 | 0.070 | 0.450 | 0.070 | 0.454 | 0.866 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 50 | 3.1 | 0.820 | 0.819 | -0.002 | 1.000 |
| L18 | 0.120 | 0.550 | 0.120 | 0.557 | 0.823 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 50 | 3.8 | 0.208 | 0.216 | 0.008 | 1.074 |
| L18 | 0.030 | 0.550 | 0.030 | 0.557 | 0.949 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 50 | 3.8 | 0.568 | 0.571 | 0.002 | 1.000 |
| L18 | 0.200 | 0.550 | 0.200 | 0.557 | 0.736 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 50 | 3.8 | 0.077 | 0.090 | 0.013 | 1.259 |
| L18 | 0.070 | 0.550 | 0.070 | 0.557 | 0.888 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 50 | 3.8 | 0.322 | 0.318 | -0.003 | 1.021 |
| L18 | 0.120 | 0.450 | 0.120 | 0.447 | 0.788 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 100 | 6.1 | 0.669 | 0.658 | -0.010 | 1.000 |
| L18 | 0.030 | 0.450 | 0.030 | 0.447 | 0.937 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 100 | 6.1 | 1.000 | 1.000 | 0.000 | 1.000 |
| L18 | 0.200 | 0.450 | 0.200 | 0.447 | 0.691 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 100 | 6.1 | 0.386 | 0.386 | -0.001 | 1.001 |
| L18 | 0.070 | 0.450 | 0.070 | 0.447 | 0.865 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 100 | 6.1 | 0.988 | 0.988 | 0.000 | 1.000 |
| L18 | 0.120 | 0.550 | 0.120 | 0.549 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 100 | 7.5 | 0.267 | 0.272 | 0.005 | 1.095 |
| L18 | 0.030 | 0.550 | 0.030 | 0.549 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 100 | 7.5 | 0.823 | 0.827 | 0.004 | 1.001 |
| L18 | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 100 | 7.5 | 0.169 | 0.189 | 0.019 | 1.168 |
| L18 | 0.070 | 0.550 | 0.070 | 0.549 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 100 | 7.5 | 0.458 | 0.456 | -0.001 | 1.036 |
| L18 | 0.120 | 0.450 | 0.120 | 0.449 | 0.789 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 300 | 18.4 | 0.899 | 0.900 | 0.002 | 1.000 |
| L18 | 0.030 | 0.450 | 0.030 | 0.449 | 0.937 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 300 | 18.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L18 | 0.200 | 0.450 | 0.200 | 0.449 | 0.692 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 300 | 18.4 | 0.438 | 0.451 | 0.013 | 1.005 |
| L18 | 0.070 | 0.450 | 0.070 | 0.449 | 0.865 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 300 | 18.4 | 1.000 | 1.000 | 0.000 | 1.000 |
| L18 | 0.120 | 0.550 | 0.120 | 0.549 | 0.821 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 72.7 | 8 | 300 | 22.5 | 0.382 | 0.379 | -0.004 | 1.080 |
| L18 | 0.030 | 0.550 | 0.030 | 0.549 | 0.948 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 1.5 | 290.8 | 8 | 300 | 22.5 | 1.000 | 1.000 | 0.000 | 1.000 |
| L18 | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 58.2 | 8 | 300 | 22.5 | 0.257 | 0.267 | 0.010 | 1.003 |
| L18 | 0.070 | 0.550 | 0.070 | 0.549 | 0.887 | candidate_domain_solve_period | candidate_domain_solve_packet | 48 | 2 | 166.2 | 8 | 300 | 22.5 | 0.811 | 0.811 | 0.000 | 0.990 |

## Insight Summary

- Positive-gain scene points: `65`
- Zero-gain scene points: `306`
- Negative-gain scene points: `61`
- Best gain scene: `case=`L12` rho_bg=`0.200` rho_pdb=`0.549` prb_share_pdb=`0.733` pdb_ms=`100` pdb_packet_kb=`7.5``
- Lowest center-retention scene: `case=`L17` rho_bg=`0.200` rho_pdb=`0.550` prb_share_pdb=`0.734` pdb_ms=`300` pdb_packet_kb=`45.1``

## Background Cost and Resource Analysis

- Mean center throughput retention across scene points: `1.005`
- Mean PRB utilization delta (proposed - baseline): `0.000`
- Mean center PRB share delta: `0.001`
- Mean edge PRB share delta: `-0.001`

| Region | Scene Points | Share | Win Rate | Mean Delta PDB Satisfaction | Mean Center Retention | Mean Delta PRB Utilization |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| critical | 108 | 0.25 | 0.30 | -0.000 | 1.004 | 0.000 |
| feasible | 277 | 0.64 | 0.01 | 0.000 | 1.000 | -0.000 |
| overloaded | 47 | 0.11 | 0.64 | 0.004 | 1.036 | -0.000 |

## Feasible Boundary Snapshot

- Boundary feasibility snapshots remain available at the 95% and 90% thresholds.

| Threshold | Baseline Feasible Points | Proposed Feasible Points | Expanded Points | Regressed Points |
| ---: | ---: | ---: | ---: | ---: |
| 0.95 | 277 | 277 | 0 | 0 |
| 0.90 | 283 | 284 | 1 | 0 |

## Representative Case Mechanism Analysis

- Representative cases selected: `4`
- Representative detail rows: `8`
- `typical_case_details.csv` is the renderer-facing mechanism table for these cases.

| Label | target_rho_bg | target_rho_pdb | actual_rho_bg | actual_rho_pdb | prb_share_pdb | pdb_ms | pdb_packet_kb | Mean Delta PDB Satisfaction | Center Retention |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| easy | 0.200 | 0.030 | 0.200 | 0.029 | 0.128 | 50 | 0.4 | 0.000 | 1.000 |
| critical | 0.120 | 0.400 | 0.120 | 0.395 | 0.767 | 50 | 2.7 | 0.016 | 1.000 |
| overloaded | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | 100 | 7.5 | 0.022 | 1.036 |
| high_cost | 0.200 | 0.550 | 0.200 | 0.549 | 0.733 | 50 | 7.5 | 0.005 | 0.940 |

| Label | baseline_satisfaction | proposed_satisfaction | baseline_queue_ms | proposed_queue_ms | baseline_completion_ms | proposed_completion_ms | baseline_center_rate_bps | proposed_center_rate_bps | center_retention |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| easy | 1.000 | 1.000 | 11.6 | 11.6 | 12.6 | 12.6 | 13260800.0 | 13260800.0 | 1.000 |
| critical | 0.772 | 0.788 | 21.0 | 21.0 | 23.2 | 23.2 | 8003852.9 | 8004359.4 | 1.000 |
| overloaded | 0.186 | 0.209 | 43.0 | 43.0 | 47.6 | 47.6 | 10027009.2 | 10299843.3 | 1.027 |
| high_cost | 0.354 | 0.358 | 26.0 | 26.0 | 31.0 | 31.0 | 11275629.2 | 10941934.1 | 0.970 |

## Summary

- Proposed improves `65/432` load-ratio scene points; best gain is `0.022`.
- Mean center throughput retention is `1.005`; worst retained point is `0.925`.
- Boundary expansion adds `0` points at 95% and `1` points at 90%.