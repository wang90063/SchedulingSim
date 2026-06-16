# Hopeless Tail-Append Full-Scan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the `hopeless_tail_append` reinsertion policy, wire it through the simulator and CLI, add a checked-in rho-first config for the new policy, then rerun the full 60-scene load-ratio matrix on `main`.

**Architecture:** Keep the scheduler change strictly local to reinsertion. Reuse the current two-policy systematic-analysis runner by creating a second rho-first config with `baseline_policy=tail_append` and `ours_policy=hopeless_tail_append`, then compare its outputs against the existing `hopeless_front_insert` full-scan results after the run.

**Tech Stack:** Python, `unittest`, existing `UlSimulator` and systematic-analysis runner scripts, JSON configs, CSV/Markdown outputs, non-interactive `git`.

---

## Proposed File Structure

- Modify: `src/scheduling_sim/reinsert.py`
  - Add `HopelessTailAppendPolicy` by reusing the current hopeless-detection path and changing only the final fallback to queue tail.
- Modify: `src/scheduling_sim/simulator.py`
  - Recognize `scheduler.reinsert_policy == "hopeless_tail_append"` and instantiate the new class.
- Modify: `src/scheduling_sim/cli.py`
  - Accept `hopeless_tail_append` in `run --reinsert-policy`.
- Modify: `tests/test_reinsert.py`
  - Add the regression test that proves a hopeless packet falls back to queue tail rather than front insertion.
- Modify: `tests/test_simulator.py`
  - Add coverage that `UlSimulator` selects the new policy.
- Modify: `tests/test_cli.py`
  - Add CLI override coverage and a systematic-runner smoke test for `ours_policy = hopeless_tail_append`.
- Create: `configs/systematic_simulation_analysis_load_ratio_rho_first_hopeless_tail_append.json`
  - Clone the current rho-first config, point `ours_policy` at `hopeless_tail_append`, and set a dedicated output directory.

## Task 1: Add Failing Tests for the New Policy Surface

**Files:**
- Modify: `tests/test_reinsert.py`
- Modify: `tests/test_simulator.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing reinsertion test**

```python
from scheduling_sim.reinsert import (
    ConstrainedInsertPolicy,
    HopelessTailAppendPolicy,
    TailAppendPolicy,
    TargetOnlyConstrainedInsertPolicy,
)

    def test_hopeless_tail_append_moves_hopeless_packet_to_queue_tail(self) -> None:
        queue = ActiveQueue()
        users = [self.make_ue(f"ue-{index}") for index in range(5)]
        for user in users:
            queue.activate(user)
        policy = HopelessTailAppendPolicy()
        policy.apply(
            queue,
            users[0],
            queue_wait_size=queue.size,
            service_bits_per_decision=0,
            now_ms=12,
            current_phase="S",
            max_ue_per_slot=2,
        )
        ordered = [user.ue_id for user in queue.ordered_users()]
        self.assertEqual(ordered[-1], users[0].ue_id)
```

- [ ] **Step 2: Write the failing simulator-selection test**

```python
    def test_supports_hopeless_tail_append_policy(self) -> None:
        config = self._legacy_config(center_count=1, max_ue_per_slot=1)
        config = AppConfig(
            simulation=config.simulation,
            resources=config.resources,
            traffic=config.traffic,
            radio=config.radio,
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="hopeless_tail_append"),
            report=config.report,
        )
        users = ScenarioFactory(config).build_users()
        simulator = UlSimulator(config, users, DummyMetrics())
        self.assertIsInstance(simulator.reinsert, HopelessTailAppendPolicy)
```

- [ ] **Step 3: Write the failing CLI tests**

```python
    def test_run_command_supports_hopeless_tail_append_override(self) -> None:
        result = subprocess.run(
            [
                "python",
                "-m",
                "scheduling_sim.cli",
                "run",
                "configs/target_edge_compare.json",
                "--reinsert-policy",
                "hopeless_tail_append",
            ],
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ, "PYTHONPATH": "src"},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("hopeless_tail_append", result.stdout)

    def test_systematic_simulation_analysis_runner_supports_hopeless_tail_append_ours_policy(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "systematic_hopeless_tail.json"
            output_dir = Path(tmp) / "systematic-hopeless-tail-output"
            _write_nr_ul_main_table(Path(tmp), repo_root)
            payload = json.loads(
                (repo_root / "configs" / "systematic_simulation_analysis_option1.json").read_text(encoding="utf-8")
            )
            payload["report"]["output_dir"] = str(output_dir)
            payload["systematic_analysis"]["background_user_count_values"] = [24]
            payload["systematic_analysis"]["pdb_user_count_values"] = [4]
            payload["systematic_analysis"]["pdb_ms_values"] = [100]
            payload["systematic_analysis"]["pdb_packet_kb_values"] = [50]
            payload["systematic_analysis"]["repeat_count"] = 1
            payload["systematic_analysis"]["ours_policy"] = "hopeless_tail_append"
            config_path.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                ["python", "scripts/run_systematic_simulation_analysis.py", str(config_path)],
                cwd=repo_root,
                env={**os.environ, "PYTHONPATH": "src"},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            manifest = json.loads((output_dir / "experiment_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["ours_policy"], "hopeless_tail_append")
```

- [ ] **Step 4: Run the focused RED tests**

Run: `PYTHONPATH=src python -m unittest tests.test_reinsert.ReinsertionPolicyTests.test_hopeless_tail_append_moves_hopeless_packet_to_queue_tail tests.test_simulator.SimulatorCycleTests.test_supports_hopeless_tail_append_policy tests.test_cli.CliSmokeTests.test_run_command_supports_hopeless_tail_append_override tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_supports_hopeless_tail_append_ours_policy -v`

Expected: FAIL because `HopelessTailAppendPolicy` and the new CLI choice do not exist yet.

## Task 2: Implement the New Policy and Wire It Through the Existing Surfaces

**Files:**
- Modify: `src/scheduling_sim/reinsert.py`
- Modify: `src/scheduling_sim/simulator.py`
- Modify: `src/scheduling_sim/cli.py`
- Modify: `tests/test_reinsert.py`
- Modify: `tests/test_simulator.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add the minimal policy implementation**

```python
class HopelessTailAppendPolicy(ConstrainedInsertPolicy):
    def apply(
        self,
        queue: ActiveQueue,
        ue: UserEquipment,
        queue_wait_size: int,
        service_bits_per_decision: int,
        now_ms: int,
        current_phase: str,
        max_ue_per_slot: int,
    ) -> None:
        tail_index = max(queue_wait_size - 1, 0)
        if self._position_is_safe(
            ue,
            queue_index=tail_index,
            service_bits_per_decision=service_bits_per_decision,
            now_ms=now_ms,
            current_phase=current_phase,
            max_ue_per_slot=max_ue_per_slot,
        ):
            queue.append_tail(ue)
            return
        for queue_index in range(tail_index, -1, -1):
            if self._position_is_safe(
                ue,
                queue_index=queue_index,
                service_bits_per_decision=service_bits_per_decision,
                now_ms=now_ms,
                current_phase=current_phase,
                max_ue_per_slot=max_ue_per_slot,
            ):
                queue.insert_at(queue_index, ue)
                return
        queue.append_tail(ue)
```

- [ ] **Step 2: Wire simulator and CLI selection**

```python
from scheduling_sim.reinsert import (
    ConstrainedInsertPolicy,
    HopelessFrontInsertPolicy,
    HopelessTailAppendPolicy,
    TailAppendPolicy,
    TargetOnlyConstrainedInsertPolicy,
)

        elif config.scheduler.reinsert_policy == "hopeless_front_insert":
            self.reinsert = HopelessFrontInsertPolicy(deadline_guard_ms=deadline_guard_ms)
        elif config.scheduler.reinsert_policy == "hopeless_tail_append":
            self.reinsert = HopelessTailAppendPolicy(deadline_guard_ms=deadline_guard_ms)
```

```python
        choices=[
            "tail_append",
            "constrained_insert",
            "target_only_constrained_insert",
            "business_aware_constrained_insert",
            "hopeless_front_insert",
            "hopeless_tail_append",
        ],
```

- [ ] **Step 3: Run the focused GREEN tests**

Run: `PYTHONPATH=src python -m unittest tests.test_reinsert.ReinsertionPolicyTests.test_hopeless_tail_append_moves_hopeless_packet_to_queue_tail tests.test_simulator.SimulatorCycleTests.test_supports_hopeless_tail_append_policy tests.test_cli.CliSmokeTests.test_run_command_supports_hopeless_tail_append_override tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_supports_hopeless_tail_append_ours_policy -v`

Expected: PASS

- [ ] **Step 4: Run the broader regression slice**

Run: `PYTHONPATH=src python -m unittest tests.test_reinsert tests.test_simulator tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_supports_hopeless_front_insert_ours_policy tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_supports_hopeless_tail_append_ours_policy -v`

Expected: PASS

- [ ] **Step 5: Commit the policy wiring**

```bash
git add src/scheduling_sim/reinsert.py src/scheduling_sim/simulator.py src/scheduling_sim/cli.py tests/test_reinsert.py tests/test_simulator.py tests/test_cli.py
git commit -m "feat: add hopeless tail-append reinsertion policy"
```

## Task 3: Add the Full-Scan Config and Run the Mainline Experiment

**Files:**
- Create: `configs/systematic_simulation_analysis_load_ratio_rho_first_hopeless_tail_append.json`

- [ ] **Step 1: Add the checked-in rho-first config**

```json
{
  "simulation": {
    "cycles": 2400,
    "slot_duration_ms": 1,
    "tdd_pattern": "DSUUU",
    "random_seed": 7,
    "analysis_window_ms": 10000
  },
  "resources": {
    "total_prb_per_u_slot": 273,
    "max_ue_per_slot": 16
  },
  "traffic": {
    "center": {
      "count": 48,
      "period_slots": 10,
      "packet_bits": 16000,
      "pdb_ms": null,
      "gbr_bps": 0.0
    },
    "edge": {
      "count": 16,
      "packet_bits": 400000,
      "pdb_ms": 100,
      "arrival_mode": "periodic_by_pdb",
      "initial_phase_mode": "uniform_0_to_pdb"
    }
  },
  "radio": {
    "environment": {
      "scenario_type": "uma",
      "cell_radius_m": 500.0,
      "carrier_frequency_ghz": 3.5,
      "per_prb_tx_power_dbm": 5.0,
      "noise_figure_db": 7.0,
      "interference_margin_db": 3.0,
      "shadow_std_db": 4.0,
      "slow_fading_alpha": 0.95,
      "slot_jitter_std_db": 0.5,
      "mcs_table_path": "mcs/nr_ul_main.json"
    },
    "center": {
      "base_snr_db": 12.0,
      "snr_min_db": 0.0,
      "snr_max_db": 20.0
    },
    "edge": {
      "base_snr_db": -2.0,
      "snr_min_db": -8.0,
      "snr_max_db": 4.0,
      "edge_per_u_slot_prb_cap": 273
    }
  },
  "scheduler": {
    "ranking": "epf",
    "reinsert_policy": "tail_append"
  },
  "report": {
    "output_dir": "outputs/systematic_simulation_analysis_load_ratio_rho_first_hopeless_tail_append",
    "keep_slot_trace": false
  },
  "systematic_analysis": {
    "mode": "load_ratio",
    "rho_bg_values": [0.388, 0.582, 0.775, 0.969],
    "rho_pdb_values": [0.183, 0.366, 0.549],
    "pdb_ms_values": [20, 50, 100, 300, 500],
    "capacity_reference": {
      "background_capacity_mbps": 66.03,
      "pdb_capacity_mbps": 8.74
    },
    "mapping_policy": {
      "background": {
        "kind": "candidate_domain_solve_period",
        "background_user_count_values": [32, 40, 48],
        "background_packet_kb_values": [1.0, 1.5, 2.0],
        "background_period_ms_range": [4.0, 30.0],
        "anchor_background_user_count": 40,
        "anchor_background_packet_kb": 2.0
      },
      "pdb": {
        "kind": "candidate_domain_solve_packet",
        "pdb_user_count_values": [4, 8],
        "pdb_packet_kb_range": [0.5, 80.0],
        "anchor_pdb_user_count": 4
      }
    },
    "repeat_count": 10,
    "random_seed_base": 7,
    "baseline_policy": "tail_append",
    "ours_policy": "hopeless_tail_append",
    "scene_bank": {
      "medium_distance_range_m": [170.0, 230.0],
      "good_distance_range_m": [80.0, 140.0],
      "poor_distance_range_m": [390.0, 470.0]
    }
  }
}
```

- [ ] **Step 2: Commit the config and planning docs**

```bash
git add docs/superpowers/specs/2026-06-16-hopeless-tail-append-policy-design.md docs/superpowers/plans/2026-06-16-hopeless-tail-append-fullscan-implementation.md configs/systematic_simulation_analysis_load_ratio_rho_first_hopeless_tail_append.json
git commit -m "docs: plan hopeless tail-append full scan"
```

- [ ] **Step 3: Merge the implementation branch back to `main`**

```bash
git -C /Users/wangran/Desktop/code/scheduling-sim merge hopeless-tail-append-fullscan
```

- [ ] **Step 4: Run the full rho-first scan on `main`**

Run: `PYTHONPATH=src python scripts/run_systematic_simulation_analysis.py configs/systematic_simulation_analysis_load_ratio_rho_first_hopeless_tail_append.json`

Expected: writes `outputs/systematic_simulation_analysis_load_ratio_rho_first_hopeless_tail_append/` with `scene_summary.csv`, `paired_rows.csv`, `per_run_rows.csv`, `summary_report.md`, and representative-case tables.

- [ ] **Step 5: Compare the new full-scan output against the existing front-insert output**

Run: `PYTHONPATH=src python - <<'PY'\nimport csv\nfrom pathlib import Path\nold = Path('outputs/systematic_simulation_analysis_load_ratio_rho_first/scene_summary.csv')\nnew = Path('outputs/systematic_simulation_analysis_load_ratio_rho_first_hopeless_tail_append/scene_summary.csv')\nwith old.open() as f:\n    old_rows = {row['case_label']: row for row in csv.DictReader(f)}\nwith new.open() as f:\n    new_rows = {row['case_label']: row for row in csv.DictReader(f)}\nfor label in sorted(new_rows):\n    front = old_rows[label]\n    tail = new_rows[label]\n    print(','.join([\n        label,\n        front['mean_delta_pdb_satisfaction_rate'],\n        front['mean_center_throughput_retention'],\n        tail['mean_delta_pdb_satisfaction_rate'],\n        tail['mean_center_throughput_retention'],\n    ]))\nPY`

Expected: a scene-by-scene comparison stream that makes the `high_cost` and other tradeoff points easy to summarize.
