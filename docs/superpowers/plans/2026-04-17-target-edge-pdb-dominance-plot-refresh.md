# Target Edge PDB Dominance Plot Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the existing diagnostic plots unchanged while adding a 0-100 ms EPF zoom view and separate dominance plots for each policy.

**Architecture:** Extend the existing plotting helpers in the diagnostic runner so the same trace data emits both the legacy overview images and the new focused images. Update the markdown report and CLI smoke test in an additive way so the current workflow keeps working.

**Tech Stack:** Python, `matplotlib`, `unittest`

---

### Task 1: Extend plot generation

**Files:**
- Modify: `scripts/run_target_edge_pdb_dominance_diagnostic.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Add the new output names to the smoke test expectation**

```python
self.assertTrue((output_dir / "epf_rank_vs_time_first_100ms.png").exists())
self.assertTrue((output_dir / "dominance_terms_tail_append.png").exists())
self.assertTrue((output_dir / "dominance_terms_business_aware_constrained_insert.png").exists())
self.assertTrue((output_dir / "dominance_timeline_tail_append.png").exists())
self.assertTrue((output_dir / "dominance_timeline_business_aware_constrained_insert.png").exists())
```

- [ ] **Step 2: Run the targeted smoke test to confirm the new assertions fail before implementation**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_pdb_dominance_diagnostic_script_runs -v`
Expected: `FAIL` because the new PNG files are not generated yet.

- [ ] **Step 3: Implement additive plot helpers**

```python
def _plot_epf_rank(..., *, filename: str = "epf_rank_vs_time.png", max_time_ms: int | None = None) -> None:
    ...

def _plot_dominance_terms_by_policy(rows_by_policy: dict[str, list[dict[str, object]]], output_dir: Path) -> None:
    ...

def _plot_dominance_timeline_by_policy(rows_by_policy: dict[str, list[dict[str, object]]], output_dir: Path) -> None:
    ...
```

- [ ] **Step 4: Update the report to reference the new images in a dedicated section**

```python
"## 局部放大 / 分策略视图",
"![EPF Rank First 100ms](epf_rank_vs_time_first_100ms.png)",
"![Dominance Terms Tail Append](dominance_terms_tail_append.png)",
"![Dominance Terms Business Aware](dominance_terms_business_aware_constrained_insert.png)",
"![Dominance Timeline Tail Append](dominance_timeline_tail_append.png)",
"![Dominance Timeline Business Aware](dominance_timeline_business_aware_constrained_insert.png)",
```

- [ ] **Step 5: Run the targeted smoke test to verify the new files pass**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_pdb_dominance_diagnostic_script_runs -v`
Expected: `OK`

### Task 2: Regenerate diagnostic artifacts

**Files:**
- Modify: `outputs/target_edge_pdb_dominance_diagnostic/diagnostic_report.md`
- Create: `outputs/target_edge_pdb_dominance_diagnostic/epf_rank_vs_time_first_100ms.png`
- Create: `outputs/target_edge_pdb_dominance_diagnostic/dominance_terms_tail_append.png`
- Create: `outputs/target_edge_pdb_dominance_diagnostic/dominance_terms_business_aware_constrained_insert.png`
- Create: `outputs/target_edge_pdb_dominance_diagnostic/dominance_timeline_tail_append.png`
- Create: `outputs/target_edge_pdb_dominance_diagnostic/dominance_timeline_business_aware_constrained_insert.png`

- [ ] **Step 1: Run the diagnostic generator**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python scripts/run_target_edge_pdb_dominance_diagnostic.py configs/target_edge_pdb_dominance_diagnostic.json`
Expected: stdout still prints the decision trace CSV header and both policy names.

- [ ] **Step 2: Verify the new artifacts are present alongside the old ones**

Run: `ls outputs/target_edge_pdb_dominance_diagnostic`
Expected: the original four PNGs plus the five new PNGs and the markdown/json/csv files.

- [ ] **Step 3: Verify report references**

Run: `rg -n "epf_rank_vs_time_first_100ms|dominance_terms_tail_append|dominance_terms_business_aware_constrained_insert|dominance_timeline_tail_append|dominance_timeline_business_aware_constrained_insert" outputs/target_edge_pdb_dominance_diagnostic/diagnostic_report.md`
Expected: one hit per new image reference.
