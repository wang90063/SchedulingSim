# Business KPI Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add dual-objective business KPI reporting: center-user `GBR` satisfaction over the full simulation window and edge-user completed-delay plus unfinished-`HOL` metrics.

**Architecture:** Keep the simulator flow unchanged and add metric inputs at existing boundaries. `config/scenario/models` carry optional center `gbr_bps`; `simulator` passes `ue_id`, simulation duration, and final user state into `MetricsCollector`; `metrics` computes business KPIs while preserving old diagnostic fields.

**Tech Stack:** Python 3, `dataclasses`, `unittest`, repo-local CLI `python -m scheduling_sim.cli`

---

## File Structure

- Modify: `src/scheduling_sim/config.py`
  - Add optional `TrafficConfig.gbr_bps` defaulting to `0.0`.
- Modify: `src/scheduling_sim/models.py`
  - Add `TrafficProfile.gbr_bps` defaulting to `0.0`.
- Modify: `src/scheduling_sim/scenario.py`
  - Copy `gbr_bps` from center traffic config into center users.
- Modify: `src/scheduling_sim/simulator.py`
  - Pass `ue_id` to `record_bits_served`, compute simulation duration, refresh final `HOL`, and pass users into `build_summary`.
- Modify: `src/scheduling_sim/metrics.py`
  - Track served bits by user and compute center `GBR`, edge delay, and edge `HOL` KPIs.
- Modify: `configs/edge_compare.json`
  - Add a center `gbr_bps` target to the demo config.
- Modify: `tests/test_config.py`
  - Assert `gbr_bps` loads and defaults correctly.
- Modify: `tests/test_simulator.py`
  - Add focused metrics tests and simulator summary coverage.
- Modify: `tests/test_cli.py`
  - Assert generated report includes business KPI fields.

### Task 1: Add GBR config plumbing

**Files:**
- Modify: `src/scheduling_sim/config.py`
- Modify: `src/scheduling_sim/models.py`
- Modify: `src/scheduling_sim/scenario.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write failing tests**

Add assertions in `tests/test_config.py`:

```python
self.assertEqual(config.traffic.center.gbr_bps, 20000.0)
```

Add a default-value assertion in `test_load_config_supports_uma_geometry_schema`:

```python
self.assertEqual(config.traffic.center.gbr_bps, 0.0)
```

- [ ] **Step 2: Run test to verify failure**

Run: `PYTHONPATH=src python -m unittest tests.test_config.ConfigLoaderTests -v`

Expected: failure because `TrafficConfig` has no `gbr_bps`.

- [ ] **Step 3: Implement minimal config plumbing**

Add to `TrafficConfig` and `TrafficProfile`:

```python
gbr_bps: float = 0.0
```

Pass into center users in `ScenarioFactory.build_users`:

```python
gbr_bps=self.config.traffic.center.gbr_bps,
```

- [ ] **Step 4: Run test to verify pass**

Run: `PYTHONPATH=src python -m unittest tests.test_config.ConfigLoaderTests -v`

Expected: `OK`.

### Task 2: Add metrics unit coverage

**Files:**
- Modify: `tests/test_simulator.py`

- [ ] **Step 1: Write failing metrics tests**

Add a test that creates center and edge users, records served bits by `ue_id`, records one edge completed packet, leaves another edge packet unfinished, and asserts:

```python
self.assertEqual(summary["center_user_gbr_satisfaction_rate"], 0.5)
self.assertEqual(summary["center_avg_rate_bps"], 15000.0)
self.assertEqual(summary["center_min_rate_bps"], 10000.0)
self.assertEqual(summary["edge_pdb_satisfaction_rate"], 1.0)
self.assertEqual(summary["edge_avg_hol_ms"], 20.0)
self.assertEqual(summary["edge_overdue_hol_ratio"], 1.0)
```

- [ ] **Step 2: Run test to verify failure**

Run: `PYTHONPATH=src python -m unittest tests.test_simulator.MetricsTests -v`

Expected: failure because `record_bits_served` does not accept `ue_id` and `build_summary` does not accept users or duration.

### Task 3: Implement business KPI metrics

**Files:**
- Modify: `src/scheduling_sim/metrics.py`

- [ ] **Step 1: Update served-bit tracking**

Change `record_bits_served` to:

```python
def record_bits_served(self, user_class: str, bits_sent: int, ue_id: str | None = None) -> None:
    normalized_class = user_class if user_class in self.served_bits_by_group else "center"
    self.served_bits_total += bits_sent
    self.served_bits_by_group[normalized_class] += bits_sent
    if ue_id is not None:
        self.served_bits_by_user[ue_id] = self.served_bits_by_user.get(ue_id, 0) + bits_sent
```

- [ ] **Step 2: Update summary API**

Change `build_summary` signature to:

```python
def build_summary(
    self,
    total_prb_used: int,
    total_prb_available: int,
    users=None,
    simulation_duration_ms: int = 0,
) -> dict[str, float]:
```

Compute center rate and edge `HOL` helpers from `users or []`.

- [ ] **Step 3: Run metrics tests**

Run: `PYTHONPATH=src python -m unittest tests.test_simulator.MetricsTests -v`

Expected: `OK`.

### Task 4: Wire simulator and CLI report

**Files:**
- Modify: `src/scheduling_sim/simulator.py`
- Modify: `configs/edge_compare.json`
- Modify: `tests/test_simulator.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing simulator and CLI assertions**

In simulator summary tests, assert:

```python
self.assertIn("center_user_gbr_satisfaction_rate", summary)
self.assertIn("edge_avg_hol_ms", summary)
```

In CLI report test, assert the same keys are present in `report.json`.

- [ ] **Step 2: Run tests to verify failure**

Run: `PYTHONPATH=src python -m unittest tests.test_simulator.SimulatorCycleTests tests.test_cli.CliSmokeTests -v`

Expected: failure until simulator passes users and duration to metrics and CLI config includes `gbr_bps`.

- [ ] **Step 3: Implement simulator wiring**

Pass `ue_id` in `_consume_user_bits`:

```python
self.metrics.record_bits_served(user_class=user_class, bits_sent=bits_sent, ue_id=user.ue_id)
```

At the end of `run`:

```python
simulation_duration_ms = (
    self.config.simulation.cycles
    * len(self.config.simulation.tdd_pattern)
    * self.config.simulation.slot_duration_ms
)
self._refresh_hol(simulation_duration_ms)
return self.metrics.build_summary(
    total_prb_used=total_prb_used,
    total_prb_available=total_prb_available,
    users=self.users,
    simulation_duration_ms=simulation_duration_ms,
)
```

Add to `configs/edge_compare.json` center traffic:

```json
"gbr_bps": 20000
```

- [ ] **Step 4: Run targeted tests**

Run: `PYTHONPATH=src python -m unittest tests.test_simulator tests.test_cli tests.test_config -v`

Expected: `OK`.

### Task 5: Final verification

**Files:**
- No additional source edits expected.

- [ ] **Step 1: Run full unit suite**

Run: `PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py' -v`

Expected: `OK`.

- [ ] **Step 2: Run demo simulation**

Run: `PYTHONPATH=src python -m scheduling_sim.cli run configs/edge_compare.json`

Expected: exit code `0` and stdout containing `Report written to outputs/edge_compare/report.json`.

- [ ] **Step 3: Inspect report keys**

Run: `python -m json.tool outputs/edge_compare/report.json`

Expected: JSON includes `center_user_gbr_satisfaction_rate`, `edge_pdb_satisfaction_rate`, `edge_avg_hol_ms`, and old diagnostic fields such as `served_bits`.
