# Target Edge PDB Dominance Diagnostic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a standalone target-edge PDB dominance diagnostic report for the `400KB / PDB=500 / center=63 / 960 bit every 6 slots` case, with per-`D/S` decision traces and four comparison plots for `tail_append` vs `business_aware_constrained_insert`.

**Architecture:** Keep the existing simulator behavior unchanged by default and add an opt-in diagnostic collector that observes each `D/S` decision before PRB planning. Build a dedicated script/config pair for the fixed-case diagnostic, serialize decision traces to CSV/JSON, generate PNG plots with `matplotlib`, and render a standalone Markdown report that explains queue-limited, spectral-dominated, PDB-dominated, and overdue phases.

**Tech Stack:** Python 3.12, `unittest`, dataclasses-based simulator/config flow, `matplotlib` for PNG plots, JSON/CSV/Markdown outputs

---

## File Map

- `pyproject.toml`
  - Declares the project dependency on `matplotlib` so the plotting script is reproducible.
- `configs/target_edge_pdb_dominance_diagnostic.json`
  - Owns the fixed-case scenario and the two compared reinsert policies.
- `src/scheduling_sim/diagnostics.py`
  - Owns the diagnostic row model, dominance-label classification, trace collection, and summary helpers.
- `src/scheduling_sim/simulator.py`
  - Owns the simulator execution loop and will expose an opt-in `diagnostic_collector` hook at each `D/S` decision.
- `scripts/run_target_edge_pdb_dominance_diagnostic.py`
  - Owns config loading, two-policy runs, CSV/JSON writing, plot generation, and Markdown report rendering.
- `tests/test_diagnostics.py`
  - Owns focused unit coverage for dominance-label classification and rank/term extraction helpers.
- `tests/test_cli.py`
  - Owns smoke coverage for the new diagnostic script and generated artifacts.

### Task 1: Lock the diagnostic surface and plotting dependency in tests/config

**Files:**
- Modify: `pyproject.toml`
- Create: `configs/target_edge_pdb_dominance_diagnostic.json`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing CLI smoke test first**

Add a new test to `tests/test_cli.py` named `test_target_edge_pdb_dominance_diagnostic_script_runs` with assertions in this shape:

```python
    def test_target_edge_pdb_dominance_diagnostic_script_runs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [
                "python",
                "scripts/run_target_edge_pdb_dominance_diagnostic.py",
                "configs/target_edge_pdb_dominance_diagnostic.json",
            ],
            cwd=repo_root,
            env={**os.environ, "PYTHONPATH": "src"},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=f"stderr:\n{result.stderr}")
        self.assertIn("policy,time_ms,phase,queue_rank", result.stdout)
        self.assertIn("tail_append", result.stdout)
        self.assertIn("business_aware_constrained_insert", result.stdout)

        output_dir = repo_root / "outputs" / "target_edge_pdb_dominance_diagnostic"
        self.assertTrue((output_dir / "diagnostic_report.md").exists())
        self.assertTrue((output_dir / "decision_trace.csv").exists())
        self.assertTrue((output_dir / "decision_trace.json").exists())
        self.assertTrue((output_dir / "queue_position_vs_time.png").exists())
        self.assertTrue((output_dir / "epf_rank_vs_time.png").exists())
        self.assertTrue((output_dir / "dominance_terms_vs_time.png").exists())
        self.assertTrue((output_dir / "dominance_timeline.png").exists())

        report_text = (output_dir / "diagnostic_report.md").read_text(encoding="utf-8")
        self.assertIn("Target Edge PDB Dominance Diagnostic", report_text)
        self.assertIn("queue_position_vs_time.png", report_text)
        self.assertIn("epf_rank_vs_time.png", report_text)
        self.assertIn("dominance_terms_vs_time.png", report_text)
        self.assertIn("dominance_timeline.png", report_text)
        self.assertIn("queue_limited", report_text)
        self.assertIn("spectral_dominated", report_text)
        self.assertIn("pdb_dominated", report_text)
```

- [ ] **Step 2: Run the new smoke test to verify it fails**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_pdb_dominance_diagnostic_script_runs -v`

Expected: FAIL because the config file and script do not exist yet.

- [ ] **Step 3: Add the plotting dependency and fixed-case config**

Edit `pyproject.toml` so `[project]` includes:

```toml
[project]
name = "scheduling-sim"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "matplotlib>=3.9",
]
```

Create `configs/target_edge_pdb_dominance_diagnostic.json` with this payload:

```json
{
  "simulation": {
    "cycles": 1000,
    "slot_duration_ms": 1,
    "tdd_pattern": "DSUUU",
    "random_seed": 7,
    "stop_when_target_edge_finished": true,
    "deadline_guard_ms": 10
  },
  "resources": { "total_prb_per_u_slot": 237, "max_ue_per_slot": 16 },
  "traffic": {
    "center": { "count": 63, "period_slots": 6, "packet_bits": 960, "pdb_ms": 1000000000, "gbr_bps": 7000 },
    "edge": { "count": 1, "packet_bits": 3200000, "pdb_ms": 500 }
  },
  "radio": {
    "environment": {
      "scenario_type": "uma",
      "cell_radius_m": 500,
      "carrier_frequency_ghz": 3.5,
      "noise_figure_db": 7.0,
      "interference_margin_db": 3.0,
      "shadow_std_db": 4.0,
      "slow_fading_alpha": 0.95,
      "slot_jitter_std_db": 0.5,
      "center_distance_range_m": [50, 150],
      "edge_distance_range_m": [375, 475],
      "mcs_table_path": "mcs/nr_ul_main.json"
    },
    "center": {},
    "edge": { "edge_per_u_slot_prb_cap": 237 }
  },
  "scheduler": { "ranking": "epf", "reinsert_policy": "business_aware_constrained_insert" },
  "report": { "output_dir": "outputs/target_edge_pdb_dominance_diagnostic", "keep_slot_trace": false },
  "diagnostic": {
    "policies": ["tail_append", "business_aware_constrained_insert"]
  }
}
```

- [ ] **Step 4: Re-run the smoke test to confirm the remaining failure is script-side**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_pdb_dominance_diagnostic_script_runs -v`

Expected: FAIL because the script and collector are still missing, but the config file now loads.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml configs/target_edge_pdb_dominance_diagnostic.json tests/test_cli.py
git commit -m "test: define pdb dominance diagnostic surface"
```

### Task 2: Add the diagnostic collector and classification unit tests

**Files:**
- Create: `src/scheduling_sim/diagnostics.py`
- Create: `tests/test_diagnostics.py`

- [ ] **Step 1: Write the failing unit tests for the core classification helpers**

Create `tests/test_diagnostics.py` with tests in this shape:

```python
import unittest

from scheduling_sim.diagnostics import classify_dominance_label


class DominanceClassificationTests(unittest.TestCase):
    def test_not_pending_when_target_absent(self) -> None:
        self.assertEqual(
            classify_dominance_label(
                is_pending=False,
                in_candidate_window=False,
                hol_ms=0,
                pdb_ms=500,
            ),
            "not_pending",
        )

    def test_queue_limited_before_candidate_window(self) -> None:
        self.assertEqual(
            classify_dominance_label(
                is_pending=True,
                in_candidate_window=False,
                hol_ms=120,
                pdb_ms=500,
            ),
            "queue_limited",
        )

    def test_spectral_dominated_before_half_pdb(self) -> None:
        self.assertEqual(
            classify_dominance_label(
                is_pending=True,
                in_candidate_window=True,
                hol_ms=200,
                pdb_ms=500,
            ),
            "spectral_dominated",
        )

    def test_pdb_dominated_from_half_pdb(self) -> None:
        self.assertEqual(
            classify_dominance_label(
                is_pending=True,
                in_candidate_window=True,
                hol_ms=250,
                pdb_ms=500,
            ),
            "pdb_dominated",
        )

    def test_overdue_when_hol_reaches_pdb(self) -> None:
        self.assertEqual(
            classify_dominance_label(
                is_pending=True,
                in_candidate_window=True,
                hol_ms=500,
                pdb_ms=500,
            ),
            "overdue_pdb_forced",
        )
```

- [ ] **Step 2: Run the new diagnostics test module to verify it fails**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_diagnostics -v`

Expected: FAIL with `ModuleNotFoundError` because `scheduling_sim.diagnostics` does not yet exist.

- [ ] **Step 3: Implement the collector module minimally**

Create `src/scheduling_sim/diagnostics.py` with these building blocks:

```python
from dataclasses import dataclass
from typing import Any


def classify_dominance_label(*, is_pending: bool, in_candidate_window: bool, hol_ms: int, pdb_ms: int | None) -> str:
    if not is_pending:
        return "not_pending"
    if not in_candidate_window:
        return "queue_limited"
    if pdb_ms is None:
        return "spectral_dominated"
    if hol_ms >= pdb_ms:
        return "overdue_pdb_forced"
    if hol_ms * 2 >= pdb_ms:
        return "pdb_dominated"
    return "spectral_dominated"


@dataclass
class DecisionTraceRow:
    policy: str
    time_ms: int
    phase: str
    queue_rank: int | None
    in_candidate_window: bool
    candidate_rank_epf: int | None
    candidate_rank_spectral_only: int | None
    inst_rate_bits_per_prb: float
    average_throughput: float
    spectral_term: float
    hol_ms: int
    pdb_ms: int | None
    pdb_slack_ms: int | None
    hol_factor: float
    epf_weight: float
    dominance_label: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy": self.policy,
            "time_ms": self.time_ms,
            "phase": self.phase,
            "queue_rank": self.queue_rank,
            "in_candidate_window": self.in_candidate_window,
            "candidate_rank_epf": self.candidate_rank_epf,
            "candidate_rank_spectral_only": self.candidate_rank_spectral_only,
            "inst_rate_bits_per_prb": self.inst_rate_bits_per_prb,
            "average_throughput": self.average_throughput,
            "spectral_term": self.spectral_term,
            "hol_ms": self.hol_ms,
            "pdb_ms": self.pdb_ms,
            "pdb_slack_ms": self.pdb_slack_ms,
            "hol_factor": self.hol_factor,
            "epf_weight": self.epf_weight,
            "dominance_label": self.dominance_label,
        }


class TargetEdgeDiagnosticCollector:
    def __init__(self, policy: str) -> None:
        self.policy = policy
        self.rows: list[DecisionTraceRow] = []

    def record(self, row: DecisionTraceRow) -> None:
        self.rows.append(row)
```

Keep extraction helpers small and colocated in this file.

- [ ] **Step 4: Re-run the diagnostics tests to verify they pass**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_diagnostics -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/scheduling_sim/diagnostics.py tests/test_diagnostics.py
git commit -m "feat: add pdb dominance diagnostic helpers"
```

### Task 3: Hook the simulator into the diagnostic collector and expose decision traces

**Files:**
- Modify: `src/scheduling_sim/simulator.py`
- Modify: `src/scheduling_sim/ranking.py`
- Modify: `src/scheduling_sim/queue.py`
- Modify: `src/scheduling_sim/diagnostics.py`
- Test: `tests/test_diagnostics.py`

- [ ] **Step 1: Write the next failing unit test for collected ranks/terms**

Extend `tests/test_diagnostics.py` with a collector-level test that locks the expected ranking semantics:

```python
from scheduling_sim.diagnostics import build_target_row
from scheduling_sim.models import CurrentRadioState, LogicalChannel, Packet, RadioProfile, TrafficProfile, UserEquipment


def _make_target(hol_ms: int, average_throughput: float = 10.0) -> UserEquipment:
    packet = Packet(
        packet_id="edge-0-0-D",
        arrival_time=0,
        size_bits=3200000,
        remaining_bits=3200000,
        pdb_ms=500,
        completion_time=None,
        eligible_cycle=0,
        is_target=True,
    )
    ue = UserEquipment(
        ue_id="edge-0",
        lc=LogicalChannel(lc_id="edge-0-lc", packets=[packet], eligible_cycle=0),
        is_edge_user=True,
        radio_profile=RadioProfile(user_class="edge", bits_per_prb=1200, per_u_slot_prb_cap=237),
        average_throughput=average_throughput,
        traffic_profile=TrafficProfile(packet_bits=3200000, pdb_ms=500),
        current_radio_state=CurrentRadioState(snr_db=10.0, mcs_index=0, bits_per_prb=1200, per_u_slot_prb_cap=237),
        hol_ms=hol_ms,
    )
    return ue


class DominanceRowTests(unittest.TestCase):
    def test_build_target_row_marks_queue_limited_before_candidate_window(self) -> None:
        target = _make_target(hol_ms=120)
        row = build_target_row(
            policy="tail_append",
            time_ms=120,
            phase="D",
            ordered_queue=[object(), target],
            candidates=[],
            ranked=[],
            target_ue=target,
            max_ue_per_slot=1,
        )
        self.assertEqual(row.queue_rank, 2)
        self.assertFalse(row.in_candidate_window)
        self.assertEqual(row.dominance_label, "queue_limited")
```

- [ ] **Step 2: Run the diagnostics tests to verify the new helper is missing**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_diagnostics -v`

Expected: FAIL because `build_target_row` and/or queue/rank extraction support are not implemented yet.

- [ ] **Step 3: Add minimal extraction helpers and simulator hook**

In `src/scheduling_sim/queue.py`, add a rank helper:

```python
    def index_of(self, ue: UserEquipment) -> int | None:
        try:
            return self._users.index(ue)
        except ValueError:
            return None
```

In `src/scheduling_sim/ranking.py`, add a public helper so diagnostics and ranking share the same formula:

```python
    def weight(self, ue: UserEquipment) -> float:
        return self._weight(ue)
```

In `src/scheduling_sim/diagnostics.py`, add `build_target_row(...)` that computes:
- `queue_rank = index + 1` when present
- `in_candidate_window = target_ue in candidates`
- `candidate_rank_epf = ranked.index(target_ue) + 1` when present
- `candidate_rank_spectral_only` by sorting `candidates` on `inst_rate / avg_rate`
- `spectral_term`, `hol_factor`, `epf_weight`, and `dominance_label`

Then in `src/scheduling_sim/simulator.py`:

```python
class UlSimulator:
    def __init__(self, config, users, metrics, wireless_env=None, diagnostic_collector=None) -> None:
        ...
        self.diagnostic_collector = diagnostic_collector
```

and inside `finish_phase()` before `plan_phase(...)`:

```python
        if self.diagnostic_collector is not None:
            self.diagnostic_collector.capture(
                queue=self.queue,
                candidates=candidates,
                ranked=ranked,
                ranking_policy=self.ranking,
                time_ms=now_ms,
                phase=phase,
                max_ue_per_slot=self.config.resources.max_ue_per_slot,
            )
```

Implement `capture(...)` in the collector by locating the UE whose head packet has `is_target=True` and appending a `DecisionTraceRow`.

- [ ] **Step 4: Re-run the diagnostics tests to verify they pass**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_diagnostics -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/scheduling_sim/diagnostics.py src/scheduling_sim/queue.py src/scheduling_sim/ranking.py src/scheduling_sim/simulator.py tests/test_diagnostics.py
git commit -m "feat: capture target-edge decision diagnostics"
```

### Task 4: Add the standalone diagnostic script and trace serialization

**Files:**
- Create: `scripts/run_target_edge_pdb_dominance_diagnostic.py`
- Modify: `src/scheduling_sim/diagnostics.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Use the CLI smoke test as the failing contract**

Keep `tests.test_cli.CliSmokeTests.test_target_edge_pdb_dominance_diagnostic_script_runs` unchanged and run it again:

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_pdb_dominance_diagnostic_script_runs -v`

Expected: FAIL because the script still does not exist.

- [ ] **Step 2: Implement the script skeleton with CSV/JSON output first**

Create `scripts/run_target_edge_pdb_dominance_diagnostic.py` with this structure:

```python
import csv
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from scheduling_sim.config import load_config
from scheduling_sim.diagnostics import TargetEdgeDiagnosticCollector
from scheduling_sim.metrics import MetricsCollector
from scheduling_sim.scenario import ScenarioFactory
from scheduling_sim.simulator import UlSimulator


def _load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_policy(config, policy: str):
    updated = replace(config, scheduler=replace(config.scheduler, reinsert_policy=policy))
    users = ScenarioFactory(updated).build_users()
    collector = TargetEdgeDiagnosticCollector(policy=policy)
    summary = UlSimulator(updated, users, MetricsCollector(), diagnostic_collector=collector).run()
    return collector.rows, summary
```

Add `_write_trace_outputs(...)` that writes:
- `decision_trace.csv`
- `decision_trace.json`
- stdout CSV with headers beginning `policy,time_ms,phase,queue_rank`

Do not implement plots yet.

- [ ] **Step 3: Re-run the CLI smoke test to verify output files now fail only on plots/report**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_pdb_dominance_diagnostic_script_runs -v`

Expected: FAIL because the trace files exist, but the PNG plots and report are still missing.

- [ ] **Step 4: Commit**

```bash
git add scripts/run_target_edge_pdb_dominance_diagnostic.py src/scheduling_sim/diagnostics.py tests/test_cli.py
git commit -m "feat: add pdb dominance diagnostic trace script"
```

### Task 5: Generate plots, Markdown report, and final summary metrics

**Files:**
- Modify: `scripts/run_target_edge_pdb_dominance_diagnostic.py`
- Modify: `src/scheduling_sim/diagnostics.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Keep the CLI smoke test as the failing report/plot contract**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_pdb_dominance_diagnostic_script_runs -v`

Expected: FAIL because PNG plots and `diagnostic_report.md` are not yet generated.

- [ ] **Step 2: Add `matplotlib` plot generation helpers**

In `scripts/run_target_edge_pdb_dominance_diagnostic.py`, add four helpers with signatures like:

```python
def _plot_queue_position(rows_by_policy: dict[str, list[dict[str, Any]]], output_dir: Path) -> None: ...
def _plot_epf_rank(rows_by_policy: dict[str, list[dict[str, Any]]], output_dir: Path) -> None: ...
def _plot_dominance_terms(rows_by_policy: dict[str, list[dict[str, Any]]], output_dir: Path) -> None: ...
def _plot_dominance_timeline(rows_by_policy: dict[str, list[dict[str, Any]]], output_dir: Path) -> None: ...
```

Use `matplotlib.pyplot` and save files exactly as:
- `queue_position_vs_time.png`
- `epf_rank_vs_time.png`
- `dominance_terms_vs_time.png`
- `dominance_timeline.png`

For the timeline plot, map labels to colors with a dict like:

```python
DOMINANCE_COLORS = {
    "queue_limited": "#d62728",
    "spectral_dominated": "#1f77b4",
    "pdb_dominated": "#ff7f0e",
    "overdue_pdb_forced": "#9467bd",
    "not_pending": "#c7c7c7",
}
```

- [ ] **Step 3: Add summary helpers and Markdown rendering**

In `src/scheduling_sim/diagnostics.py`, add a summary helper like:

```python
def summarize_trace(rows: list[DecisionTraceRow]) -> dict[str, Any]:
    ...
```

It should compute, per policy:
- `first_candidate_time_ms`
- `first_rank1_time_ms`
- `first_pdb_dominated_time_ms`
- counts for `queue_limited`, `spectral_dominated`, `pdb_dominated`, `overdue_pdb_forced`

Then in the script, write `diagnostic_report.md` with sections:
- `# Target Edge PDB Dominance Diagnostic`
- `## 场景设置`
- `## 判定口径`
- `## 图形总览`
- `## 策略对比摘要`
- `## 解释结论`

Make sure the report includes Markdown image references in this shape:

```markdown
![Queue Position](queue_position_vs_time.png)
![EPF Rank](epf_rank_vs_time.png)
![Dominance Terms](dominance_terms_vs_time.png)
![Dominance Timeline](dominance_timeline.png)
```

- [ ] **Step 4: Re-run the CLI smoke test to verify it passes**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_pdb_dominance_diagnostic_script_runs -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_target_edge_pdb_dominance_diagnostic.py src/scheduling_sim/diagnostics.py tests/test_cli.py
git commit -m "feat: render pdb dominance diagnostic report"
```

### Task 6: Run full verification and inspect generated artifacts

**Files:**
- Verify: `tests/test_diagnostics.py`
- Verify: `tests/test_cli.py`
- Verify output: `outputs/target_edge_pdb_dominance_diagnostic/diagnostic_report.md`

- [ ] **Step 1: Run the diagnostics unit tests and new CLI smoke together**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_diagnostics tests.test_cli.CliSmokeTests.test_target_edge_pdb_dominance_diagnostic_script_runs -v`

Expected:

```text
... ok
... ok

----------------------------------------------------------------------
Ran <N> tests in <time>

OK
```

- [ ] **Step 2: Run the full CLI smoke suite**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_cli -v`

Expected: all tests PASS.

- [ ] **Step 3: Inspect the generated report and artifact list**

Run: `rg -n "Target Edge PDB Dominance Diagnostic|queue_limited|spectral_dominated|pdb_dominated|overdue_pdb_forced|queue_position_vs_time.png|epf_rank_vs_time.png|dominance_terms_vs_time.png|dominance_timeline.png" outputs/target_edge_pdb_dominance_diagnostic/diagnostic_report.md && ls outputs/target_edge_pdb_dominance_diagnostic`

Expected output contains the report title, dominance labels, and all four PNG filenames.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml configs/target_edge_pdb_dominance_diagnostic.json src/scheduling_sim/diagnostics.py src/scheduling_sim/queue.py src/scheduling_sim/ranking.py src/scheduling_sim/simulator.py scripts/run_target_edge_pdb_dominance_diagnostic.py tests/test_diagnostics.py tests/test_cli.py
git commit -m "feat: add target-edge pdb dominance diagnostic"
```
