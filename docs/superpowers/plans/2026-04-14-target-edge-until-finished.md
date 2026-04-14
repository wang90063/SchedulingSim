# Target Edge Until Finished Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Subagent dispatch is not used here because the user asked to start inline, and the current workspace already contains uncommitted experiment files this task depends on.

**Goal:** Let `target_edge_sensitivity_main_400kbit_pdb500` run until the target edge packet finishes instead of stopping at a fixed `500 ms` window.

**Architecture:** Add an optional `SimulationConfig.stop_when_target_edge_finished` flag, defaulting to `False`. `UlSimulator.run()` keeps `cycles` as a safety cap, but records the real stop time when the tracked target edge packet finishes and passes that to metrics/reporting.

**Tech Stack:** Python dataclasses, `unittest`, existing CLI report script.

---

### Task 1: Configuration Flag

**Files:**
- Modify: `tests/test_config.py`
- Modify: `src/scheduling_sim/config.py`

- [ ] **Step 1: Write failing config tests**

Add assertions that omitted configs default `stop_when_target_edge_finished` to `False` and explicit configs load it as `True`.

- [ ] **Step 2: Run config tests to verify RED**

Run: `PYTHONPATH=src python -m unittest tests.test_config.ConfigLoaderTests -v`

Expected: fails with `AttributeError` or unexpected constructor argument for `stop_when_target_edge_finished`.

- [ ] **Step 3: Implement config flag**

Add `stop_when_target_edge_finished: bool = False` to `SimulationConfig`, and normalize missing JSON values to that default in `load_config()`.

- [ ] **Step 4: Run config tests to verify GREEN**

Run: `PYTHONPATH=src python -m unittest tests.test_config.ConfigLoaderTests -v`

Expected: all `ConfigLoaderTests` pass.

### Task 2: Simulator Stop Condition

**Files:**
- Modify: `tests/test_simulator.py`
- Modify: `src/scheduling_sim/simulator.py`
- Modify: `src/scheduling_sim/metrics.py`

- [ ] **Step 1: Write failing simulator test**

Add a small scenario where `cycles = 4` would normally run `20 ms`, but the target edge packet finishes in the first U-slot. Assert `simulation_duration_ms == 3.0`, `target_edge_finished is True`, and `target_edge_completion_delay_ms == 3.0`.

- [ ] **Step 2: Run simulator test to verify RED**

Run: `PYTHONPATH=src python -m unittest tests.test_simulator.SimulatorCycleTests.test_run_stops_after_target_edge_packet_finishes_when_configured -v`

Expected: fails because the simulator still reports the full fixed window or metrics omit `simulation_duration_ms`.

- [ ] **Step 3: Implement stop condition**

Track whether a target edge packet completed after each U-slot when `config.simulation.stop_when_target_edge_finished` is `True`. Break out of the simulation loop and pass the actual stop time to `MetricsCollector.build_summary()`. Include `simulation_duration_ms` in the metrics summary.

- [ ] **Step 4: Run simulator test to verify GREEN**

Run: `PYTHONPATH=src python -m unittest tests.test_simulator.SimulatorCycleTests.test_run_stops_after_target_edge_packet_finishes_when_configured -v`

Expected: the new simulator test passes.

### Task 3: Experiment Report

**Files:**
- Modify: `configs/target_edge_sensitivity_report_main_400k_pdb500.json`
- Modify: `scripts/run_target_edge_sensitivity_report.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing report test**

Update `test_target_edge_sensitivity_main_400k_report_includes_breakdown_differences` to expect the new “run until target edge packet finishes” wording and no longer require `unfinished -> 499 ms`.

- [ ] **Step 2: Run report test to verify RED**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_sensitivity_main_400k_report_includes_breakdown_differences -v`

Expected: fails because the config/report still use fixed-window wording.

- [ ] **Step 3: Enable experiment stop condition and report wording**

Set `"stop_when_target_edge_finished": true` in `configs/target_edge_sensitivity_report_main_400k_pdb500.json`. Update `_build_report()` so enabled configs say `cycles` is a safety cap and the experiment runs until the target edge packet finishes.

- [ ] **Step 4: Run report test to verify GREEN**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_target_edge_sensitivity_main_400k_report_includes_breakdown_differences -v`

Expected: the report test passes.

### Task 4: Final Verification

**Files:**
- No new files beyond this plan and the design spec.

- [ ] **Step 1: Run focused tests**

Run: `PYTHONPATH=src python -m unittest tests.test_config.ConfigLoaderTests tests.test_simulator.SimulatorCycleTests.test_run_stops_after_target_edge_packet_finishes_when_configured tests.test_cli.CliSmokeTests.test_target_edge_sensitivity_main_400k_report_includes_breakdown_differences -v`

Expected: focused tests pass.

- [ ] **Step 2: Review diff**

Run: `git diff -- src/scheduling_sim/config.py src/scheduling_sim/simulator.py src/scheduling_sim/metrics.py scripts/run_target_edge_sensitivity_report.py tests/test_config.py tests/test_simulator.py tests/test_cli.py configs/target_edge_sensitivity_report_main_400k_pdb500.json docs/superpowers/specs/2026-04-14-target-edge-until-finished-design.md docs/superpowers/plans/2026-04-14-target-edge-until-finished.md`

Expected: diff is limited to the target-edge until-finished change and associated tests/docs.
