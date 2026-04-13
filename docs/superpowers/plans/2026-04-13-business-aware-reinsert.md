# Business-Aware Reinsert Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge the target-only and center-infinite-PDB experiment concepts into one business-aware constrained reinsertion policy and report a target edge PDB sweep.

**Architecture:** Keep one production policy path for the proposed algorithm: `business_aware_constrained_insert`. It uses the existing constrained insertion logic for delay-sensitive packets, while center/background traffic with loose PDB naturally remains tail-like because the tail position is safe. Keep `target_only_constrained_insert` available as a debug/ablation policy, not as the main proposed-algorithm result.

**Tech Stack:** Python standard library, `unittest`, existing `scheduling_sim` modules and JSON reports.

---

### Task 1: Add Policy Alias and CLI Support

**Files:**
- Modify: `src/scheduling_sim/simulator.py`
- Modify: `src/scheduling_sim/cli.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_simulator.py`

- [ ] **Step 1: Write the failing CLI test**

Add this test to `tests/test_cli.py`:

```python
    def test_run_command_supports_business_aware_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self._write_config(tmp)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "scheduling_sim.cli",
                    "run",
                    str(config_path),
                    "--reinsert-policy",
                    "business_aware_constrained_insert",
                ],
                check=True,
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
            )
        self.assertIn("business_aware_constrained_insert", result.stdout)
```

- [ ] **Step 2: Write the failing simulator test**

Add this test to `tests/test_simulator.py`:

```python
    def test_supports_business_aware_constrained_insert_policy(self) -> None:
        config = self._legacy_config(center_count=1, max_ue_per_slot=1)
        config = replace(
            config,
            scheduler=replace(config.scheduler, reinsert_policy="business_aware_constrained_insert"),
        )
        users = ScenarioFactory(config).build_users()
        simulator = UlSimulator(config, users, DummyMetrics())
        self.assertIsInstance(simulator.reinsert, ConstrainedInsertPolicy)
```

Ensure `replace` and `ConstrainedInsertPolicy` are imported if the file does not already import them:

```python
from dataclasses import replace
from scheduling_sim.reinsert import ConstrainedInsertPolicy, TargetOnlyConstrainedInsertPolicy
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_run_command_supports_business_aware_override tests.test_simulator.SimulatorCycleTests.test_supports_business_aware_constrained_insert_policy -v
```

Expected: both tests fail because `business_aware_constrained_insert` is not yet accepted by the CLI/simulator.

- [ ] **Step 4: Implement the alias**

In `src/scheduling_sim/cli.py`, extend `--reinsert-policy` choices:

```python
choices=[
    "tail_append",
    "constrained_insert",
    "target_only_constrained_insert",
    "business_aware_constrained_insert",
],
```

In `src/scheduling_sim/simulator.py`, map the policy to the existing constrained policy:

```python
elif config.scheduler.reinsert_policy == "target_only_constrained_insert":
    self.reinsert = TargetOnlyConstrainedInsertPolicy()
else:
    self.reinsert = ConstrainedInsertPolicy()
```

This keeps `business_aware_constrained_insert` semantically identical to constrained insertion; the business behavior comes from PDB configuration.

- [ ] **Step 5: Run tests to verify they pass**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_run_command_supports_business_aware_override tests.test_simulator.SimulatorCycleTests.test_supports_business_aware_constrained_insert_policy -v
```

Expected: both tests pass.

### Task 2: Add Business-Aware Target Edge Sweep

**Files:**
- Create: `configs/target_edge_business_aware_pdb_sweep.json`
- Create: `scripts/run_target_edge_pdb_sweep.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing smoke test**

Add this test to `tests/test_cli.py`:

```python
    def test_target_edge_pdb_sweep_script_runs(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/run_target_edge_pdb_sweep.py",
                "configs/target_edge_business_aware_pdb_sweep.json",
            ],
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
        )
        self.assertIn("edge_pdb_ms,policy,target_edge_completion_delay_ms", result.stdout)
        self.assertIn("100,business_aware_constrained_insert", result.stdout)
        self.assertIn("200,tail_append", result.stdout)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_pdb_sweep_script_runs -v
```

Expected: FAIL because the script/config does not exist yet.

- [ ] **Step 3: Add sweep config**

Create `configs/target_edge_business_aware_pdb_sweep.json` with the same base settings as `configs/target_edge_compare.json`, but set center `pdb_ms` to a large value:

```json
{
  "simulation": { "cycles": 40, "slot_duration_ms": 1, "tdd_pattern": "DSUUU", "random_seed": 7 },
  "resources": { "total_prb_per_u_slot": 106, "max_ue_per_slot": 16 },
  "traffic": {
    "center": { "count": 63, "period_slots": 1, "packet_bits": 160, "pdb_ms": 1000000000, "gbr_bps": 7000 },
    "edge": { "count": 1, "packet_bits": 40000, "pdb_ms": 120 }
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
      "mcs_table": [
        { "sinr_db": -8.0, "mcs_index": 0, "bits_per_prb": 24 },
        { "sinr_db": -2.0, "mcs_index": 1, "bits_per_prb": 48 },
        { "sinr_db": 4.0, "mcs_index": 2, "bits_per_prb": 72 },
        { "sinr_db": 10.0, "mcs_index": 3, "bits_per_prb": 96 },
        { "sinr_db": 16.0, "mcs_index": 4, "bits_per_prb": 120 }
      ]
    },
    "center": {},
    "edge": { "edge_per_u_slot_prb_cap": 24 }
  },
  "scheduler": { "ranking": "epf", "reinsert_policy": "business_aware_constrained_insert" },
  "report": { "output_dir": "outputs/target_edge_pdb_sweep", "keep_slot_trace": false }
}
```

- [ ] **Step 4: Add sweep script**

Create `scripts/run_target_edge_pdb_sweep.py`:

```python
import csv
import json
import sys
from dataclasses import replace
from pathlib import Path

from scheduling_sim.config import load_config
from scheduling_sim.metrics import MetricsCollector
from scheduling_sim.scenario import ScenarioFactory
from scheduling_sim.simulator import UlSimulator


EDGE_PDB_VALUES = (100, 150, 200)
POLICIES = ("tail_append", "business_aware_constrained_insert")


def run_case(config, edge_pdb_ms: int, policy: str) -> dict[str, float]:
    traffic = replace(
        config.traffic,
        edge=replace(config.traffic.edge, pdb_ms=edge_pdb_ms),
    )
    case_config = replace(
        config,
        traffic=traffic,
        scheduler=replace(config.scheduler, reinsert_policy=policy),
    )
    users = ScenarioFactory(case_config).build_users()
    return UlSimulator(case_config, users, MetricsCollector()).run()


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run_target_edge_pdb_sweep.py CONFIG", file=sys.stderr)
        return 2
    config = load_config(Path(sys.argv[1]))
    rows = []
    for edge_pdb_ms in EDGE_PDB_VALUES:
        for policy in POLICIES:
            summary = run_case(config, edge_pdb_ms=edge_pdb_ms, policy=policy)
            rows.append(
                {
                    "edge_pdb_ms": edge_pdb_ms,
                    "policy": policy,
                    "target_edge_completion_delay_ms": summary["target_edge_completion_delay_ms"],
                    "target_edge_queue_wait_ms": summary["target_edge_queue_wait_ms"],
                    "target_edge_service_time_ms": summary["target_edge_service_time_ms"],
                    "target_edge_pdb_met": summary["target_edge_pdb_met"],
                    "center_user_gbr_satisfaction_rate": summary["center_user_gbr_satisfaction_rate"],
                    "center_avg_rate_bps": summary["center_avg_rate_bps"],
                }
            )
    output_dir = Path(config.report.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "pdb_sweep.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_pdb_sweep_script_runs -v
```

Expected: PASS.

### Task 3: Refresh Reports and Documentation

**Files:**
- Modify: `outputs/target_edge_compare/policy_comparison.md`
- Create: `outputs/target_edge_pdb_sweep/pdb_sweep.json`
- Create: `outputs/target_edge_pdb_sweep/pdb_sweep.md`
- Modify: `docs/superpowers/specs/2026-04-13-target-edge-case-study.md`

- [ ] **Step 1: Run the sweep**

Run:

```bash
PYTHONPATH=src python scripts/run_target_edge_pdb_sweep.py configs/target_edge_business_aware_pdb_sweep.json > outputs/target_edge_pdb_sweep/pdb_sweep.csv
```

Expected: CSV includes rows for `edge_pdb_ms` values `100`, `150`, and `200` with both `tail_append` and `business_aware_constrained_insert`.

- [ ] **Step 2: Write the markdown report**

Create `outputs/target_edge_pdb_sweep/pdb_sweep.md` with a concise explanation:

```markdown
# Target Edge PDB Sweep

This experiment treats center traffic as non-delay-sensitive background traffic by setting center `pdb_ms` to a very large value. The proposed policy is `business_aware_constrained_insert`: center traffic naturally falls back to tail append when tail is safe, while the edge target packet moves forward only when tail append would miss its PDB.
```

Add the generated numeric table from `pdb_sweep.csv`.

- [ ] **Step 3: Update the target edge spec**

In `docs/superpowers/specs/2026-04-13-target-edge-case-study.md`, add:

```markdown
`target_only_constrained_insert` is now treated as a debug/ablation strategy. The main proposed policy is `business_aware_constrained_insert`, configured with loose center PDB and tighter target edge PDB.
```

- [ ] **Step 4: Run full verification**

Run:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py' -v
```

Expected: `Ran ... tests ... OK`.
