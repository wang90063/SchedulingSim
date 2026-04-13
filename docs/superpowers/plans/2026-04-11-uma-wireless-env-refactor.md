# UMa Wireless Environment Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current hand-tuned radio model with a configurable `UMa` large-scale uplink environment, enforce edge `PRB cap` at the physical `U`-slot level, and add grouped metrics so edge behavior is directly observable.

**Architecture:** Keep the simulator orchestration and scheduling interfaces stable. Move radio realism into `config -> scenario -> wireless_env`, let `ranking/planning/reinsert` continue consuming `CurrentRadioState`, and enforce the true physical-slot cap during `U` execution where `D` and `S` plans merge.

**Tech Stack:** Python 3, `dataclasses`, `unittest`, repo-local CLI `python -m scheduling_sim.cli`

---

## File Structure

- Modify: `src/scheduling_sim/config.py`
  - Add `UMa` radio config schema, distance ranges, and compatibility helpers.
- Modify: `src/scheduling_sim/models.py`
  - Add geometry-bearing radio fields and optional grouped metric helpers.
- Modify: `src/scheduling_sim/scenario.py`
  - Assign fixed `distance_to_bs_m` for center/edge users from configured ranges.
- Modify: `src/scheduling_sim/wireless_env.py`
  - Replace base-`SNR`-driven refresh with `UMa` path-loss + shadowing + slow fading + `SINR -> MCS` flow.
- Modify: `src/scheduling_sim/planning.py`
  - Keep phase budgeting intact but avoid pretending phase-local cap equals physical-slot cap.
- Modify: `src/scheduling_sim/simulator.py`
  - Enforce per-edge-user physical `U`-slot `PRB` cap after merging `D/S` grants, and track served bits.
- Modify: `src/scheduling_sim/metrics.py`
  - Add `served_bits`, grouped `center/edge` counters, and grouped delay / PDB summaries.
- Modify: `src/scheduling_sim/reporting.py`
  - Persist new summary fields without changing report flow.
- Modify: `configs/edge_compare.json`
  - Move demo config onto the new `UMa` schema and use more realistic defaults.
- Modify: `tests/test_config.py`
  - Cover new schema loading and backward compatibility.
- Modify: `tests/test_wireless_env.py`
  - Cover geometry-driven `SINR/MCS/bits_per_prb` updates.
- Modify: `tests/test_planning.py`
  - Cover cap semantics that remain planner-local versus physical-slot enforcement.
- Modify: `tests/test_simulator.py`
  - Cover merged `U`-slot cap enforcement and grouped metric output.

### Task 1: Add UMa radio schema and geometry-aware users

**Files:**
- Modify: `src/scheduling_sim/config.py`
- Modify: `src/scheduling_sim/models.py`
- Modify: `src/scheduling_sim/scenario.py`
- Test: `tests/test_config.py`
- Test: `tests/test_simulator.py`

- [ ] **Step 1: Write the failing config and scenario tests**

```python
def test_load_config_supports_uma_geometry_schema(self) -> None:
    payload = {
        "simulation": {"cycles": 1, "slot_duration_ms": 1, "tdd_pattern": "DSUUU"},
        "resources": {"total_prb_per_u_slot": 20, "max_ue_per_slot": 4},
        "traffic": {
            "center": {"count": 1, "period_slots": 1, "packet_bits": 100, "pdb_ms": 30},
            "edge": {"count": 1, "burst_cycle_interval": 1, "packet_bits": 40000, "pdb_ms": 15},
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
                "edge_distance_range_m": [425, 500],
                "mcs_table": [
                    {"sinr_db": -5.0, "mcs_index": 0, "bits_per_prb": 24},
                    {"sinr_db": 0.0, "mcs_index": 1, "bits_per_prb": 48},
                ],
            },
            "center": {},
            "edge": {"edge_per_u_slot_prb_cap": 18},
        },
        "scheduler": {"ranking": "epf", "reinsert_policy": "tail_append"},
        "report": {"output_dir": "outputs/test", "keep_slot_trace": False},
    }
```

```python
def test_scenario_factory_assigns_distances_inside_ranges(self) -> None:
    users = ScenarioFactory(config).build_users()
    center_user = next(user for user in users if not user.is_edge_user)
    edge_user = next(user for user in users if user.is_edge_user)
    self.assertGreaterEqual(center_user.radio_profile.distance_to_bs_m, 50.0)
    self.assertLessEqual(center_user.radio_profile.distance_to_bs_m, 150.0)
    self.assertGreaterEqual(edge_user.radio_profile.distance_to_bs_m, 425.0)
    self.assertLessEqual(edge_user.radio_profile.distance_to_bs_m, 500.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python -m unittest tests.test_config tests.test_simulator -v`

Expected: failures for missing `UMa` config fields and missing `distance_to_bs_m` on `RadioProfile`.

- [ ] **Step 3: Add minimal schema, model, and factory support**

```python
@dataclass(frozen=True)
class WirelessEnvConfig:
    scenario_type: str = "legacy"
    cell_radius_m: float = 0.0
    carrier_frequency_ghz: float = 0.0
    noise_figure_db: float = 0.0
    interference_margin_db: float = 0.0
    shadow_std_db: float = 0.0
    slow_fading_alpha: float = 1.0
    slot_jitter_std_db: float = 0.0
    center_distance_range_m: tuple[float, float] = (0.0, 0.0)
    edge_distance_range_m: tuple[float, float] = (0.0, 0.0)
    mcs_table: list[McsEntryConfig] = field(default_factory=list)
```

```python
@dataclass(frozen=True)
class RadioProfile:
    user_class: str = "center"
    distance_to_bs_m: float = 0.0
    edge_per_u_slot_prb_cap: int | None = None
    bits_per_prb: int = 0
    per_u_slot_prb_cap: int = 0
```

```python
def _sample_distance(self, is_edge_user: bool, index: int) -> float:
    low, high = (
        self.config.radio.environment.edge_distance_range_m
        if is_edge_user
        else self.config.radio.environment.center_distance_range_m
    )
    rng = random.Random(self.config.simulation.random_seed + index)
    return rng.uniform(low, high)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python -m unittest tests.test_config tests.test_simulator -v`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add src/scheduling_sim/config.py src/scheduling_sim/models.py src/scheduling_sim/scenario.py tests/test_config.py tests/test_simulator.py
git commit -m "feat: add uma radio geometry schema"
```

### Task 2: Replace base-SNR refresh with UMa large-scale radio updates

**Files:**
- Modify: `src/scheduling_sim/wireless_env.py`
- Modify: `src/scheduling_sim/simulator.py`
- Test: `tests/test_wireless_env.py`
- Test: `tests/test_simulator.py`

- [ ] **Step 1: Write the failing wireless-env tests**

```python
def test_reset_maps_distance_to_stable_sinr_and_mcs(self) -> None:
    env = StableWirelessEnv(
        WirelessEnvConfigView(
            scenario_type="uma",
            cell_radius_m=500.0,
            carrier_frequency_ghz=3.5,
            noise_figure_db=7.0,
            interference_margin_db=3.0,
            shadow_std_db=0.0,
            slow_fading_alpha=1.0,
            slot_jitter_std_db=0.0,
            mcs_table=[
                McsEntryView(sinr_db=-5.0, mcs_index=0, bits_per_prb=24),
                McsEntryView(sinr_db=0.0, mcs_index=1, bits_per_prb=48),
            ],
            seed=7,
        )
    )
    edge_user = make_user("edge-0", is_edge=True, distance_to_bs_m=500.0)
    env.reset([edge_user])
    self.assertLess(edge_user.current_radio_state.sinr_db, 0.0)
    self.assertEqual(edge_user.current_radio_state.mcs_index, 0)
```

```python
def test_refresh_slot_changes_sinr_smoothly(self) -> None:
    env.reset([center_user])
    first = center_user.current_radio_state.sinr_db
    env.refresh_slot([center_user], slot_index=0, slot_name="D")
    second = center_user.current_radio_state.sinr_db
    self.assertLess(abs(second - first), 3.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python -m unittest tests.test_wireless_env tests.test_simulator -v`

Expected: failures for missing `sinr_db`-driven `UMa` calculations.

- [ ] **Step 3: Implement UMa path-loss + shadowing + slow fading**

```python
def _uma_path_loss_db(self, distance_to_bs_m: float) -> float:
    distance_m = max(distance_to_bs_m, 10.0)
    frequency_ghz = self._config.carrier_frequency_ghz
    return 32.4 + 20.0 * math.log10(frequency_ghz) + 30.0 * math.log10(distance_m)
```

```python
def _resolve_sinr_db(self, user: UserEquipment, previous_sinr_db: float | None) -> float:
    path_loss_db = self._uma_path_loss_db(user.radio_profile.distance_to_bs_m)
    shadow_db = self._shadow_cache.setdefault(
        user.ue_id,
        self._rng.gauss(0.0, self._config.shadow_std_db),
    )
    mean_sinr_db = self._uplink_budget_db - path_loss_db - shadow_db - self._config.interference_margin_db
    base = mean_sinr_db if previous_sinr_db is None else previous_sinr_db
    jitter = self._rng.gauss(0.0, self._config.slot_jitter_std_db)
    return self._config.slow_fading_alpha * base + (1.0 - self._config.slow_fading_alpha) * mean_sinr_db + jitter
```

```python
user.current_radio_state = CurrentRadioState(
    sinr_db=sinr_db,
    mcs_index=mcs_entry.mcs_index,
    bits_per_prb=mcs_entry.bits_per_prb,
    per_u_slot_prb_cap=self._resolve_prb_cap(user),
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python -m unittest tests.test_wireless_env tests.test_simulator -v`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add src/scheduling_sim/wireless_env.py src/scheduling_sim/simulator.py tests/test_wireless_env.py tests/test_simulator.py
git commit -m "feat: add uma large-scale wireless environment"
```

### Task 3: Enforce edge PRB cap at the physical U-slot level

**Files:**
- Modify: `src/scheduling_sim/simulator.py`
- Modify: `src/scheduling_sim/planning.py`
- Test: `tests/test_planning.py`
- Test: `tests/test_simulator.py`

- [ ] **Step 1: Write the failing cap-enforcement tests**

```python
def test_phase_planner_can_emit_two_phase_grants_but_simulator_caps_physical_u_slot(self) -> None:
    # D gives 18 on U2, S gives 18 on U2, but execution must clamp to 18 total.
    ...
    self.assertEqual(bits_consumed_in_u2, 18 * bits_per_prb)
```

```python
def test_edge_user_never_uses_more_than_cap_after_merging_d_and_s(self) -> None:
    summary = simulator.run()
    self.assertEqual(observed_edge_u2_prbs, 18)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python -m unittest tests.test_planning tests.test_simulator -v`

Expected: failure showing merged `U2` grants can exceed the configured edge cap.

- [ ] **Step 3: Clamp merged grants before U-slot consumption**

```python
def _merge_u_slot_grants(self, slot_index: int, d_plan, s_plan) -> tuple[dict[str, int], dict[str, int]]:
    prb_count_by_user: dict[str, int] = {}
    bits_by_user: dict[str, int] = {}
    for plan in (d_plan, s_plan):
        for grant in plan.slot_grants.get(slot_index, []):
            prb_count_by_user[grant.ue_id] = prb_count_by_user.get(grant.ue_id, 0) + grant.prb_count
            bits_by_user[grant.ue_id] = bits_by_user.get(grant.ue_id, 0) + grant.bits_planned
    for user in self.users:
        cap = None if not user.is_edge_user else user.current_radio_state.per_u_slot_prb_cap
        if cap is None or prb_count_by_user.get(user.ue_id, 0) <= cap:
            continue
        effective_prbs = cap
        bits_per_prb = user.current_radio_state.bits_per_prb
        prb_count_by_user[user.ue_id] = effective_prbs
        bits_by_user[user.ue_id] = effective_prbs * bits_per_prb
    return bits_by_user, prb_count_by_user
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python -m unittest tests.test_planning tests.test_simulator -v`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add src/scheduling_sim/planning.py src/scheduling_sim/simulator.py tests/test_planning.py tests/test_simulator.py
git commit -m "fix: enforce physical u-slot prb cap"
```

### Task 4: Add served/completed bits and center-edge grouped metrics

**Files:**
- Modify: `src/scheduling_sim/metrics.py`
- Modify: `src/scheduling_sim/reporting.py`
- Modify: `src/scheduling_sim/simulator.py`
- Test: `tests/test_simulator.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing grouped-metrics tests**

```python
def test_metrics_report_contains_served_and_grouped_edge_fields(self) -> None:
    summary = collector.build_summary(total_prb_used=12, total_prb_available=30)
    self.assertIn("served_bits", summary)
    self.assertIn("edge_completed_packets", summary)
    self.assertIn("center_avg_delay_ms", summary)
```

```python
def test_simulator_records_served_bits_even_when_packet_is_not_completed(self) -> None:
    simulator.run()
    self.assertGreater(summary["served_bits"], summary["throughput_bits"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python -m unittest tests.test_simulator tests.test_cli -v`

Expected: missing grouped metrics and missing served-bit accounting.

- [ ] **Step 3: Implement grouped accounting**

```python
class MetricsCollector:
    def __init__(self) -> None:
        self.completed_packets: list[dict[str, int | str]] = []
        self.served_bits_total = 0
        self.served_bits_by_group = {"center": 0, "edge": 0}

    def record_bits_served(self, user_class: str, bits_sent: int) -> None:
        self.served_bits_total += bits_sent
        self.served_bits_by_group[user_class] += bits_sent
```

```python
return {
    "throughput_bits": completed_bits_total,
    "served_bits": self.served_bits_total,
    "center_served_bits": self.served_bits_by_group["center"],
    "edge_served_bits": self.served_bits_by_group["edge"],
    "center_completed_packets": len(center_packets),
    "edge_completed_packets": len(edge_packets),
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python -m unittest tests.test_simulator tests.test_cli -v`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add src/scheduling_sim/metrics.py src/scheduling_sim/reporting.py src/scheduling_sim/simulator.py tests/test_simulator.py tests/test_cli.py
git commit -m "feat: add grouped radio metrics"
```

### Task 5: Update the business-like demo config and verify end to end

**Files:**
- Modify: `configs/edge_compare.json`
- Modify: `docs/superpowers/specs/2026-04-11-uma-wireless-env-design.md`
- Test: `tests/test_config.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing config/CLI expectations**

```python
def test_cli_run_accepts_uma_config(self) -> None:
    exit_code = main(["run", "configs/edge_compare.json"])
    self.assertEqual(exit_code, 0)
```

```python
def test_load_config_preserves_edge_cap_and_radius(self) -> None:
    config = load_config(Path("configs/edge_compare.json"))
    self.assertEqual(config.radio.environment.cell_radius_m, 500)
    self.assertEqual(config.radio.edge.edge_per_u_slot_prb_cap, 18)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python -m unittest tests.test_config tests.test_cli -v`

Expected: failures until demo config is migrated to the new schema.

- [ ] **Step 3: Update the example config and spec references**

```json
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
    "edge_distance_range_m": [425, 500],
    "mcs_table": [
      {"sinr_db": -5.0, "mcs_index": 0, "bits_per_prb": 24},
      {"sinr_db": 0.0, "mcs_index": 1, "bits_per_prb": 48},
      {"sinr_db": 5.0, "mcs_index": 2, "bits_per_prb": 84}
    ]
  },
  "center": {},
  "edge": {"edge_per_u_slot_prb_cap": 18}
}
```

- [ ] **Step 4: Run focused and full verification**

Run: `PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py' -v`

Expected: `OK`

Run: `PYTHONPATH=src python -m scheduling_sim.cli run configs/edge_compare.json`

Expected: `Report written to outputs/edge_compare/report.json using constrained_insert`

- [ ] **Step 5: Commit**

```bash
git add configs/edge_compare.json docs/superpowers/specs/2026-04-11-uma-wireless-env-design.md tests/test_config.py tests/test_cli.py
git commit -m "chore: update uma demo configuration"
```

## Self-Review

- Spec coverage: covered `UMa` schema, geometry-driven users, large-scale wireless refresh, physical `U`-slot cap, grouped metrics, and demo config migration.
- Placeholder scan: each task lists files, commands, expected outcomes, and code direction; no `TODO/TBD` placeholders remain.
- Type consistency: this plan uses `sinr_db` as the dynamic radio field and `distance_to_bs_m` as the geometry field across config, models, wireless environment, and tests.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-11-uma-wireless-env-refactor.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
