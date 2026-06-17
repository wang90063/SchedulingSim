# Rho PDB Mid-Band PRB Cover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the missing `target_rho_pdb = 0.30 / 0.40 / 0.45` mid-band scan to the current `prb_cover_small` experiment, reuse existing `0.03 / 0.18 / 0.55` results, and update heatmaps plus `仿真分析.md`.

**Architecture:** Keep the existing rho-first load-ratio runner and wireless realization bank unchanged. Run only the missing mid-band scenes in 12 small batch configs split by `pdb_ms × target_rho_bg`, then merge them with the existing `outputs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_small` directory. Refresh plots and packet-level report tables from the merged data.

**Tech Stack:** Python stdlib JSON/CSV, `scripts/run_systematic_simulation_analysis.py`, `scripts/render_systematic_simulation_analysis_plots.py`, existing `scheduling_sim` package.

---

### Task 1: Add Mid-Band Configs

**Files:**
- Create: `configs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_batch_pdb{050,100,300}_bg{030,070,120,200}.json`
- Create: `configs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_merge.json`

- [ ] **Step 1: Generate batch configs**

Generate 12 configs copied from existing `prb_cover_small` batch configs with:

```json
"rho_pdb_values": [0.30, 0.40, 0.45]
```

Each config keeps exactly one `pdb_ms` value and one `rho_bg` value. Each output dir must use the prefix:

```text
outputs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_batch_pdb{050,100,300}_bg{030,070,120,200}
```

- [ ] **Step 2: Generate merge config**

Create `configs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_merge.json` with:

```json
"rho_pdb_values": [0.03, 0.18, 0.30, 0.40, 0.45, 0.55]
```

Use `reuse_output_dirs` for:

```text
outputs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_small
outputs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_batch_pdb050_bg030
outputs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_batch_pdb050_bg070
outputs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_batch_pdb050_bg120
outputs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_batch_pdb050_bg200
outputs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_batch_pdb100_bg030
outputs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_batch_pdb100_bg070
outputs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_batch_pdb100_bg120
outputs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_batch_pdb100_bg200
outputs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_batch_pdb300_bg030
outputs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_batch_pdb300_bg070
outputs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_batch_pdb300_bg120
outputs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_batch_pdb300_bg200
```

Set:

```json
"merged_output_dir": "outputs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_small"
```

- [ ] **Step 3: Validate config expansion**

Run:

```bash
PYTHONPATH=src python3 -c "import json, glob; files=glob.glob('configs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_batch_*.json'); print(len(files)); assert len(files)==12; [json.load(open(p)) for p in files]"
```

Expected: prints `12`.

### Task 2: Run Incremental Simulations

**Files:**
- Read: `configs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_batch_*.json`
- Create: `outputs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_batch_*`

- [ ] **Step 1: Run 12 batch configs in parallel**

Run each config with:

```bash
PYTHONPATH=src python3 scripts/run_systematic_simulation_analysis.py <config>
```

Expected per batch: `new_scene_point_count = 18`, because each batch has `3 background_user_count × 2 pdb_user_count × 3 rho_pdb`.

- [ ] **Step 2: Monitor until all finish**

For each batch output, verify:

```bash
python3 -c "import json; import sys; m=json.load(open(sys.argv[1])); print(m['new_scene_point_count'], m['final_scene_point_count'])" outputs/.../experiment_manifest.json
```

Expected per batch: `18 18`.

### Task 3: Merge and Plot

**Files:**
- Modify: `outputs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_small/*`

- [ ] **Step 1: Archive current merged key files**

Copy current merged `experiment_manifest.json`, `per_run_rows.csv`, `paired_rows.csv`, `scene_summary.csv`, `raw_summaries.json`, `summary_report.md`, `仿真分析.md`, and `packet_level_case_analysis.csv` into:

```text
outputs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_small/_archive_before_midband/
```

- [ ] **Step 2: Run merge config**

Run:

```bash
PYTHONPATH=src python3 scripts/run_systematic_simulation_analysis.py configs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_midband_merge.json
```

Expected manifest:

```text
reused_scene_point_count = 432
new_scene_point_count = 0
final_scene_point_count = 432
```

- [ ] **Step 3: Regenerate plots**

Run:

```bash
PYTHONPATH=src python3 scripts/render_systematic_simulation_analysis_plots.py outputs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_small
```

Expected: refreshed `baseline_prb_utilization_by_pdb_ms.png`, `faceted_business_delta_pdb_satisfaction_pdb*.png`, `faceted_business_center_throughput_retention_pdb*.png`, and `faceted_baseline_prb_utilization_pdb*.png`.

### Task 4: Update Packet-Level Analysis and Report

**Files:**
- Modify: `outputs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_small/packet_level_case_analysis.csv`
- Modify: `outputs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_small/仿真分析.md`

- [ ] **Step 1: Recompute scene distribution**

Summarize baseline satisfaction by `target_rho_pdb` and identify whether `0.30 / 0.40 / 0.45` contain the desired critical band.

- [ ] **Step 2: Refresh packet-level case table**

Keep columns:

```text
stable_satisfied_count
stable_missed_count
rescued_count
harmed_count
waiting_delay_ms
service_delay_ms
tx_airtime_ms
completion_delay_ms
```

Select representative cases from the merged data:

```text
best positive
positive mid-band
negative/harm case
easy case
heavy-overload case
```

- [ ] **Step 3: Rewrite conclusions**

Update `仿真分析.md` to state:

```text
0.03 and 0.18 are easy; 0.55 is often heavy-overload; the added 0.30/0.40/0.45 bands are the intended critical-band search space.
```

Explain whether the actual data confirms this and identify the best gain region by PRB load, `target_rho_pdb`, business parameters, and baseline satisfaction.

### Task 5: Verify

**Files:**
- Read: merged outputs and tests

- [ ] **Step 1: Verify merged row counts**

Run:

```bash
python3 -c "import csv,json; d='outputs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_small'; m=json.load(open(f'{d}/experiment_manifest.json')); print(m['final_scene_point_count']); print(len(list(csv.DictReader(open(f'{d}/scene_summary.csv'))))); print(len(list(csv.DictReader(open(f'{d}/paired_rows.csv'))))); print(len(list(csv.DictReader(open(f'{d}/per_run_rows.csv')))))"
```

Expected:

```text
432
432
2160
4320
```

- [ ] **Step 2: Verify packet delay formula**

Run:

```bash
python3 -c "import csv, sys; rows=list(csv.DictReader(open('outputs/systematic_simulation_analysis_load_ratio_rho_first_prb_cover_small/packet_level_case_analysis.csv', newline=''))); bad=[]; prefixes=('rescued_baseline','rescued_proposed','harmed_baseline','harmed_proposed'); [(bad.append((i,p,w,s,d,float(w)+float(s))) if w not in ('','NaN') and s not in ('','NaN') and d not in ('','NaN') and abs((float(w)+float(s))-float(d))>0.015 else None) for i,row in enumerate(rows, start=2) for p in prefixes for w,s,d in [(row.get(p+'_mean_waiting_delay_ms',''), row.get(p+'_mean_service_delay_ms',''), row.get(p+'_mean_completion_delay_ms',''))]]; print('rows', len(rows)); print('bad', bad[:10]); sys.exit(1 if bad else 0)"
```

Expected: `bad []`.

- [ ] **Step 3: Run simulator tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_simulator
```

Expected: all tests pass.
