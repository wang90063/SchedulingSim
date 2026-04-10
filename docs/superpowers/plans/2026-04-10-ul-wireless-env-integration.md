# UL Wireless Environment Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a slot-updated but stable wireless environment to the uplink simulator so `ePF` uses current `SNR/MCS`-derived instantaneous rate, while only edge users keep a configurable single-`U`-slot `PRB` cap.

**Architecture:** Keep the current `DSUUU` simulator loop and reinsertion logic intact, and insert a new `wireless_env` module that refreshes per-UE radio snapshots before `D` and `S`. Static `RadioProfile` stores long-lived user identity and radio bounds, `CurrentRadioState` stores slot-level `SNR/MCS/bits_per_prb`, `ranking` and `planning` consume the current snapshot, and `reinsert` continues to depend only on planned service bits.

**Tech Stack:** Python 3.12+, standard library only (`dataclasses`, `json`, `pathlib`, `random`, `unittest`)

---

## File Structure

### Create

- `src/scheduling_sim/wireless_env.py` — wireless environment registry, stable slot-updated environment, and `SNR -> MCS -> bits_per_prb` mapping
- `tests/test_wireless_env.py` — unit tests for snapshot refresh, bounds, and edge-only `PRB` cap behavior

### Modify

- `src/scheduling_sim/config.py` — replace static `bits_per_prb` radio config with base `SNR` radio config and wireless environment parameters
- `src/scheduling_sim/models.py` — add `CurrentRadioState`; reshape `RadioProfile` to store user class, `SNR` bounds, and edge-only cap
- `src/scheduling_sim/scenario.py` — build `RadioProfile` values from the new config and seed initial radio state
- `src/scheduling_sim/ranking.py` — read instantaneous rate from `CurrentRadioState`
- `src/scheduling_sim/planning.py` — use `CurrentRadioState.bits_per_prb` and only apply cap to edge users
- `src/scheduling_sim/simulator.py` — refresh wireless snapshots before `D` and `S`, accept optional injected wireless environment for tests
- `configs/edge_compare.json` — migrate example config to the new radio schema
- `tests/test_config.py` — cover new radio schema and MCS table loading
- `tests/test_ranking.py` — verify `ePF` uses current slot rate instead of static profile rate
- `tests/test_planning.py` — verify edge-only cap behavior in grant planning
- `tests/test_simulator.py` — verify simulator refreshes snapshots at `D/S` and planned bits reflect the refreshed state
- `tests/test_cli.py` — update CLI fixture config to the new schema

### Responsibilities

- `config.py` owns the new radio schema, including environment tuning knobs and MCS table loading.
- `wireless_env.py` owns slot-level radio state evolution and `SNR/MCS` lookup, never queue mutation.
- `models.py` owns pure data structures for static and dynamic radio attributes.
- `scenario.py` creates users with fixed center/edge identity and initial current radio state.
- `ranking.py` uses only current slot state plus historical throughput for `ePF`.
- `planning.py` turns ranked users into grants, using edge-only `PRB` cap enforcement.
- `simulator.py` orchestrates refresh timing: update radio state before `D` and before `S`, never inside `reinsert`.

### Cross-Module Rules

- Center and edge identity are fixed for the full run.
- Only edge users carry `edge_per_u_slot_prb_cap`; center users remain constrained only by remaining slot budget.
- Wireless state may refresh every slot, but first implementation uses it only for `D` and `S` decisions.
- `reinsert` continues to read only `service_bits_per_decision`, not raw `SNR` or `MCS`.
- `U` slots execute already planned grants and do not trigger new ranking or planning.

## Task 1: Expand config and radio data models

**Files:**
- Modify: `src/scheduling_sim/config.py`
- Modify: `src/scheduling_sim/models.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing config loader test**

```python
# tests/test_config.py
import json
import tempfile
import unittest
from pathlib import Path

from scheduling_sim.config import load_config


class ConfigLoaderTests(unittest.TestCase):
    def test_loads_radio_environment_and_edge_only_cap(self) -> None:
        payload = {
            "simulation": {"cycles": 2, "slot_duration_ms": 1, "tdd_pattern": "DSUUU", "random_seed": 7},
            "resources": {"total_prb_per_u_slot": 24, "max_ue_per_slot": 8},
            "traffic": {
                "center": {"count": 2, "period_slots": 1, "packet_bits": 120, "pdb_ms": 30},
                "edge": {"count": 1, "burst_cycle_interval": 2, "packet_bits": 2400, "pdb_ms": 15}
            },
            "radio": {
                "environment": {
                    "alpha": 0.9,
                    "jitter_std_db": 0.5,
                    "mcs_table": [
                        {"snr_db": 0.0, "mcs_index": 0, "bits_per_prb": 4},
                        {"snr_db": 6.0, "mcs_index": 1, "bits_per_prb": 8},
                        {"snr_db": 12.0, "mcs_index": 2, "bits_per_prb": 14}
                    ]
                },
                "center": {"base_snr_db": 16.0, "snr_min_db": 10.0, "snr_max_db": 22.0},
                "edge": {
                    "base_snr_db": 4.0,
                    "snr_min_db": -2.0,
                    "snr_max_db": 8.0,
                    "edge_per_u_slot_prb_cap": 6
                }
            },
            "scheduler": {"ranking": "epf", "reinsert_policy": "constrained_insert"},
            "report": {"output_dir": "outputs/demo", "keep_slot_trace": False}
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            config = load_config(path)
        self.assertEqual(config.radio.environment.alpha, 0.9)
        self.assertEqual(config.radio.center.base_snr_db, 16.0)
        self.assertIsNone(config.radio.center.edge_per_u_slot_prb_cap)
        self.assertEqual(config.radio.edge.edge_per_u_slot_prb_cap, 6)
        self.assertEqual(config.radio.environment.mcs_table[-1].bits_per_prb, 14)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_config.ConfigLoaderTests.test_loads_radio_environment_and_edge_only_cap -v`

Expected: FAIL with `TypeError` because `RadioConfig` does not yet accept `base_snr_db`, `edge_per_u_slot_prb_cap`, or `environment`.

- [ ] **Step 3: Write the minimal config and model implementation**

```python
# src/scheduling_sim/config.py
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class McsEntryConfig:
    snr_db: float
    mcs_index: int
    bits_per_prb: int


@dataclass(frozen=True)
class WirelessEnvConfig:
    alpha: float
    jitter_std_db: float
    mcs_table: list[McsEntryConfig]


@dataclass(frozen=True)
class RadioClassConfig:
    base_snr_db: float
    snr_min_db: float
    snr_max_db: float
    edge_per_u_slot_prb_cap: int | None = None


@dataclass(frozen=True)
class RadioSection:
    environment: WirelessEnvConfig
    center: RadioClassConfig
    edge: RadioClassConfig


@dataclass(frozen=True)
class SimulationConfig:
    cycles: int
    slot_duration_ms: int
    tdd_pattern: str
    random_seed: int = 0


def load_config(path: Path) -> AppConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    radio_payload = payload["radio"]
    env_payload = radio_payload["environment"]
    return AppConfig(
        simulation=SimulationConfig(**payload["simulation"]),
        resources=ResourcesConfig(**payload["resources"]),
        traffic=TrafficSection(
            center=TrafficConfig(**payload["traffic"]["center"]),
            edge=TrafficConfig(**payload["traffic"]["edge"]),
        ),
        radio=RadioSection(
            environment=WirelessEnvConfig(
                alpha=env_payload["alpha"],
                jitter_std_db=env_payload["jitter_std_db"],
                mcs_table=[McsEntryConfig(**item) for item in env_payload["mcs_table"]],
            ),
            center=RadioClassConfig(**radio_payload["center"]),
            edge=RadioClassConfig(**radio_payload["edge"]),
        ),
        scheduler=SchedulerConfig(**payload["scheduler"]),
        report=ReportConfig(**payload["report"]),
    )
```

```python
# src/scheduling_sim/models.py
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RadioProfile:
    user_class: str
    base_snr_db: float
    snr_min_db: float
    snr_max_db: float
    edge_per_u_slot_prb_cap: int | None


@dataclass
class CurrentRadioState:
    snr_db: float
    mcs_index: int
    bits_per_prb: int
    per_u_slot_prb_cap: int | None


@dataclass
class UserEquipment:
    ue_id: str
    lc: LogicalChannel
    is_edge_user: bool
    radio_profile: RadioProfile
    average_throughput: float
    traffic_profile: "TrafficProfile | None" = None
    hol_ms: int = 0
    current_radio_state: CurrentRadioState | None = None
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_config.ConfigLoaderTests.test_loads_radio_environment_and_edge_only_cap -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/scheduling_sim/config.py src/scheduling_sim/models.py tests/test_config.py
git commit -m "feat: add wireless radio config schema"
```

## Task 2: Add a stable slot-updated wireless environment

**Files:**
- Create: `src/scheduling_sim/wireless_env.py`
- Test: `tests/test_wireless_env.py`

- [ ] **Step 1: Write the failing wireless environment tests**

```python
# tests/test_wireless_env.py
import unittest

from scheduling_sim.models import CurrentRadioState, LogicalChannel, RadioProfile, UserEquipment
from scheduling_sim.wireless_env import StableWirelessEnv, WirelessEnvConfigView, McsEntryView


def make_user(name: str, is_edge: bool) -> UserEquipment:
    return UserEquipment(
        ue_id=name,
        lc=LogicalChannel(lc_id=f"{name}-lc"),
        is_edge_user=is_edge,
        radio_profile=RadioProfile(
            user_class="edge" if is_edge else "center",
            base_snr_db=4.0 if is_edge else 16.0,
            snr_min_db=-2.0 if is_edge else 10.0,
            snr_max_db=8.0 if is_edge else 22.0,
            edge_per_u_slot_prb_cap=6 if is_edge else None,
        ),
        average_throughput=1.0,
        current_radio_state=CurrentRadioState(0.0, 0, 4, 6 if is_edge else None),
    )


class StableWirelessEnvTests(unittest.TestCase):
    def test_refresh_keeps_snr_in_bounds_and_sets_edge_cap_only(self) -> None:
        env = StableWirelessEnv(
            WirelessEnvConfigView(
                alpha=0.95,
                jitter_std_db=0.2,
                mcs_table=[
                    McsEntryView(snr_db=0.0, mcs_index=0, bits_per_prb=4),
                    McsEntryView(snr_db=6.0, mcs_index=1, bits_per_prb=8),
                    McsEntryView(snr_db=12.0, mcs_index=2, bits_per_prb=14),
                ],
                seed=7,
            )
        )
        center = make_user("center-0", is_edge=False)
        edge = make_user("edge-0", is_edge=True)
        env.reset([center, edge])
        env.refresh_slot([center, edge], slot_index=0, slot_name="D")
        self.assertGreaterEqual(center.current_radio_state.snr_db, center.radio_profile.snr_min_db)
        self.assertLessEqual(center.current_radio_state.snr_db, center.radio_profile.snr_max_db)
        self.assertIsNone(center.current_radio_state.per_u_slot_prb_cap)
        self.assertEqual(edge.current_radio_state.per_u_slot_prb_cap, 6)

    def test_refresh_is_stable_between_adjacent_slots(self) -> None:
        env = StableWirelessEnv(
            WirelessEnvConfigView(
                alpha=0.95,
                jitter_std_db=0.2,
                mcs_table=[McsEntryView(snr_db=0.0, mcs_index=0, bits_per_prb=4)],
                seed=11,
            )
        )
        user = make_user("edge-0", is_edge=True)
        env.reset([user])
        env.refresh_slot([user], slot_index=0, slot_name="D")
        first = user.current_radio_state.snr_db
        env.refresh_slot([user], slot_index=1, slot_name="S")
        second = user.current_radio_state.snr_db
        self.assertLess(abs(second - first), 2.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONPATH=src python -m unittest tests.test_wireless_env -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'scheduling_sim.wireless_env'`

- [ ] **Step 3: Write the minimal wireless environment implementation**

```python
# src/scheduling_sim/wireless_env.py
from dataclasses import dataclass
from random import Random

from scheduling_sim.models import CurrentRadioState, UserEquipment


@dataclass(frozen=True)
class McsEntryView:
    snr_db: float
    mcs_index: int
    bits_per_prb: int


@dataclass(frozen=True)
class WirelessEnvConfigView:
    alpha: float
    jitter_std_db: float
    mcs_table: list[McsEntryView]
    seed: int = 0


class StableWirelessEnv:
    def __init__(self, config: WirelessEnvConfigView) -> None:
        self.config = config
        self.random = Random(config.seed)
        self.current_snr: dict[str, float] = {}

    def reset(self, users: list[UserEquipment]) -> None:
        self.current_snr = {user.ue_id: user.radio_profile.base_snr_db for user in users}
        for user in users:
            self._apply_state(user, user.radio_profile.base_snr_db)

    def refresh_slot(self, users: list[UserEquipment], slot_index: int, slot_name: str) -> None:
        for user in users:
            previous = self.current_snr.get(user.ue_id, user.radio_profile.base_snr_db)
            noise = self.random.gauss(0.0, self.config.jitter_std_db)
            snr_db = self.config.alpha * previous + (1.0 - self.config.alpha) * user.radio_profile.base_snr_db + noise
            snr_db = min(user.radio_profile.snr_max_db, max(user.radio_profile.snr_min_db, snr_db))
            self.current_snr[user.ue_id] = snr_db
            self._apply_state(user, snr_db)

    def _apply_state(self, user: UserEquipment, snr_db: float) -> None:
        mcs = self._resolve_mcs(snr_db)
        user.current_radio_state = CurrentRadioState(
            snr_db=snr_db,
            mcs_index=mcs.mcs_index,
            bits_per_prb=mcs.bits_per_prb,
            per_u_slot_prb_cap=user.radio_profile.edge_per_u_slot_prb_cap if user.is_edge_user else None,
        )

    def _resolve_mcs(self, snr_db: float) -> McsEntryView:
        chosen = self.config.mcs_table[0]
        for entry in self.config.mcs_table:
            if snr_db >= entry.snr_db:
                chosen = entry
        return chosen
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `PYTHONPATH=src python -m unittest tests.test_wireless_env -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/scheduling_sim/wireless_env.py tests/test_wireless_env.py
git commit -m "feat: add stable wireless environment"
```

## Task 3: Wire current radio state into scenario, ranking, and planning

**Files:**
- Modify: `src/scheduling_sim/scenario.py`
- Modify: `src/scheduling_sim/ranking.py`
- Modify: `src/scheduling_sim/planning.py`
- Test: `tests/test_ranking.py`
- Test: `tests/test_planning.py`

- [ ] **Step 1: Write the failing ranking and planning tests**

```python
# tests/test_ranking.py
import unittest

from scheduling_sim.models import CurrentRadioState, LogicalChannel, Packet, RadioProfile, UserEquipment
from scheduling_sim.ranking import EpfRankingPolicy


class EpfRankingPolicyTests(unittest.TestCase):
    def test_uses_current_radio_state_bits_per_prb_for_inst_rate(self) -> None:
        policy = EpfRankingPolicy()
        slow = UserEquipment(
            ue_id="slow",
            lc=LogicalChannel("slow-lc", packets=[Packet("p1", 0, 100, 100, 20, None)]),
            is_edge_user=False,
            radio_profile=RadioProfile("center", 16.0, 10.0, 22.0, None),
            average_throughput=5.0,
            hol_ms=10,
            current_radio_state=CurrentRadioState(10.0, 0, 6, None),
        )
        fast = UserEquipment(
            ue_id="fast",
            lc=LogicalChannel("fast-lc", packets=[Packet("p2", 0, 100, 100, 20, None)]),
            is_edge_user=False,
            radio_profile=RadioProfile("center", 16.0, 10.0, 22.0, None),
            average_throughput=5.0,
            hol_ms=10,
            current_radio_state=CurrentRadioState(16.0, 2, 18, None),
        )
        ranked = policy.rank([slow, fast])
        self.assertEqual([user.ue_id for user in ranked], ["fast", "slow"])
```

```python
# tests/test_planning.py
import unittest

from scheduling_sim.models import CurrentRadioState, LogicalChannel, RadioProfile, UserEquipment
from scheduling_sim.planning import PhasePrbPlanner


class PhasePrbPlannerTests(unittest.TestCase):
    def test_edge_user_cap_applies_only_to_edge_users(self) -> None:
        planner = PhasePrbPlanner(total_prb_per_u_slot=10)
        center = UserEquipment(
            ue_id="center-0",
            lc=LogicalChannel("center-lc"),
            is_edge_user=False,
            radio_profile=RadioProfile("center", 16.0, 10.0, 22.0, None),
            average_throughput=1.0,
            current_radio_state=CurrentRadioState(16.0, 2, 12, None),
        )
        edge = UserEquipment(
            ue_id="edge-0",
            lc=LogicalChannel("edge-lc"),
            is_edge_user=True,
            radio_profile=RadioProfile("edge", 4.0, -2.0, 8.0, 3),
            average_throughput=1.0,
            current_radio_state=CurrentRadioState(4.0, 0, 4, 3),
        )
        plan = planner.plan_phase("D", [center, edge])
        self.assertEqual(plan.slot_grants[0][0].ue_id, "center-0")
        self.assertEqual(plan.slot_grants[0][0].prb_count, 10)
        self.assertEqual(plan.slot_grants[0][0].bits_planned, 120)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONPATH=src python -m unittest tests.test_ranking tests.test_planning -v`

Expected: FAIL because `ranking.py` still reads `ue.radio_profile.bits_per_prb` and `planning.py` still applies one cap model to every user.

- [ ] **Step 3: Write the minimal scenario, ranking, and planning implementation**

```python
# src/scheduling_sim/scenario.py
from scheduling_sim.models import CurrentRadioState, LogicalChannel, RadioProfile, TrafficProfile, UserEquipment


def _build_radio_profile(user_class: str, section) -> RadioProfile:
    return RadioProfile(
        user_class=user_class,
        base_snr_db=section.base_snr_db,
        snr_min_db=section.snr_min_db,
        snr_max_db=section.snr_max_db,
        edge_per_u_slot_prb_cap=section.edge_per_u_slot_prb_cap,
    )


def _build_initial_state(profile: RadioProfile, is_edge_user: bool) -> CurrentRadioState:
    return CurrentRadioState(
        snr_db=profile.base_snr_db,
        mcs_index=0,
        bits_per_prb=1,
        per_u_slot_prb_cap=profile.edge_per_u_slot_prb_cap if is_edge_user else None,
    )
```

```python
# src/scheduling_sim/ranking.py
class EpfRankingPolicy:
    def _weight(self, ue: UserEquipment) -> float:
        head = ue.lc.head_packet
        if head is None:
            return 0.0
        inst_rate = 1.0
        if ue.current_radio_state is not None:
            inst_rate = max(1.0, float(ue.current_radio_state.bits_per_prb))
        avg_rate = max(ue.average_throughput, 1.0)
        if ue.hol_ms >= head.pdb_ms:
            return 100.0
        hol_factor = ue.hol_ms / max(1, head.pdb_ms - ue.hol_ms)
        return (inst_rate / avg_rate) * hol_factor
```

```python
# src/scheduling_sim/planning.py
class PhasePrbPlanner:
    def _grant_prbs_for_user(self, user: UserEquipment, remaining: int) -> int:
        if user.current_radio_state is None:
            return 0
        cap = user.current_radio_state.per_u_slot_prb_cap
        return remaining if cap is None else min(remaining, cap)

    def plan_phase(self, phase: str, ranked_users: list[UserEquipment]) -> PhasePlan:
        half = self.total_prb_per_u_slot // 2
        budgets = [self.total_prb_per_u_slot, half, 0] if phase == "D" else [0, self.total_prb_per_u_slot - half, self.total_prb_per_u_slot]
        slot_grants = {0: [], 1: [], 2: []}
        for slot_index, budget in enumerate(budgets):
            remaining = budget
            for user in ranked_users:
                if remaining <= 0:
                    break
                grant_prbs = self._grant_prbs_for_user(user, remaining)
                if grant_prbs <= 0:
                    continue
                bits_per_prb = user.current_radio_state.bits_per_prb if user.current_radio_state else 0
                slot_grants[slot_index].append(
                    SchedulingGrant(
                        ue_id=user.ue_id,
                        slot_index=slot_index,
                        prb_count=grant_prbs,
                        bits_planned=grant_prbs * bits_per_prb,
                    )
                )
                remaining -= grant_prbs
        return PhasePlan(phase=phase, slot_prb_budgets=budgets, slot_grants=slot_grants)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `PYTHONPATH=src python -m unittest tests.test_ranking tests.test_planning -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/scheduling_sim/scenario.py src/scheduling_sim/ranking.py src/scheduling_sim/planning.py tests/test_ranking.py tests/test_planning.py
git commit -m "feat: use slot radio state in ranking and planning"
```

## Task 4: Refresh wireless state inside the simulator before `D` and `S`

**Files:**
- Modify: `src/scheduling_sim/simulator.py`
- Test: `tests/test_simulator.py`

- [ ] **Step 1: Write the failing simulator integration test**

```python
# tests/test_simulator.py
import unittest

from scheduling_sim.config import AppConfig, RadioClassConfig, RadioSection, ReportConfig, ResourcesConfig, SchedulerConfig, SimulationConfig, TrafficConfig, TrafficSection, WirelessEnvConfig, McsEntryConfig
from scheduling_sim.metrics import MetricsCollector
from scheduling_sim.models import CurrentRadioState, LogicalChannel, Packet, RadioProfile, TrafficProfile, UserEquipment
from scheduling_sim.simulator import UlSimulator


class FakeWirelessEnv:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def reset(self, users) -> None:
        for user in users:
            user.current_radio_state = CurrentRadioState(0.0, 0, 1, 3 if user.is_edge_user else None)

    def refresh_slot(self, users, slot_index: int, slot_name: str) -> None:
        self.calls.append(slot_name)
        bits_per_prb = 5 if slot_name == "D" else 9
        for user in users:
            user.current_radio_state = CurrentRadioState(
                snr_db=5.0 if slot_name == "D" else 9.0,
                mcs_index=0 if slot_name == "D" else 1,
                bits_per_prb=bits_per_prb,
                per_u_slot_prb_cap=3 if user.is_edge_user else None,
            )


def build_simulator_with_one_edge_user(wireless_env):
    config = AppConfig(
        simulation=SimulationConfig(cycles=1, slot_duration_ms=1, tdd_pattern="DSUUU", random_seed=7),
        resources=ResourcesConfig(total_prb_per_u_slot=6, max_ue_per_slot=4),
        traffic=TrafficSection(
            center=TrafficConfig(count=0, packet_bits=80, pdb_ms=30, period_slots=1),
            edge=TrafficConfig(count=1, packet_bits=120, pdb_ms=15, burst_cycle_interval=1),
        ),
        radio=RadioSection(
            environment=WirelessEnvConfig(
                alpha=0.95,
                jitter_std_db=0.2,
                mcs_table=[McsEntryConfig(snr_db=0.0, mcs_index=0, bits_per_prb=4)],
            ),
            center=RadioClassConfig(base_snr_db=16.0, snr_min_db=10.0, snr_max_db=22.0),
            edge=RadioClassConfig(base_snr_db=4.0, snr_min_db=-2.0, snr_max_db=8.0, edge_per_u_slot_prb_cap=3),
        ),
        scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
        report=ReportConfig(output_dir="outputs/test", keep_slot_trace=False),
    )
    user = UserEquipment(
        ue_id="edge-0",
        lc=LogicalChannel(lc_id="edge-0-lc", packets=[Packet("pkt", 0, 100, 100, 15, None)]),
        is_edge_user=True,
        radio_profile=RadioProfile("edge", 4.0, -2.0, 8.0, 3),
        average_throughput=1.0,
        traffic_profile=TrafficProfile(packet_bits=120, pdb_ms=15, burst_cycle_interval=1),
        hol_ms=5,
        current_radio_state=CurrentRadioState(4.0, 0, 1, 3),
    )
    metrics = MetricsCollector()
    simulator = UlSimulator(config, [user], metrics, wireless_env=wireless_env)
    return simulator, [user]


class SimulatorWirelessRefreshTests(unittest.TestCase):
    def test_finish_phase_refreshes_radio_state_before_planning(self) -> None:
        simulator, users = build_simulator_with_one_edge_user(wireless_env=FakeWirelessEnv())
        simulator.queue.activate(users[0])
        d_plan = simulator.finish_phase("D", now_ms=0, slot_index=0)
        s_plan = simulator.finish_phase("S", now_ms=1, slot_index=1)
        self.assertEqual(simulator.wireless_env.calls, ["D", "S"])
        self.assertEqual(d_plan.slot_grants[0][0].bits_planned, 15)
        self.assertEqual(s_plan.slot_grants[1][0].bits_planned, 27)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_simulator.SimulatorWirelessRefreshTests.test_finish_phase_refreshes_radio_state_before_planning -v`

Expected: FAIL because `UlSimulator.finish_phase()` does not accept `slot_index` and never refreshes wireless state.

- [ ] **Step 3: Write the minimal simulator implementation**

```python
# src/scheduling_sim/simulator.py
from scheduling_sim.wireless_env import McsEntryView, StableWirelessEnv, WirelessEnvConfigView


class UlSimulator:
    def __init__(self, config, users, metrics, wireless_env=None) -> None:
        self.config = config
        self.users = users
        self.metrics = metrics
        self.wireless_env = wireless_env or StableWirelessEnv(
            WirelessEnvConfigView(
                alpha=config.radio.environment.alpha,
                jitter_std_db=config.radio.environment.jitter_std_db,
                mcs_table=[
                    McsEntryView(item.snr_db, item.mcs_index, item.bits_per_prb)
                    for item in config.radio.environment.mcs_table
                ],
                seed=getattr(config.simulation, "random_seed", 0),
            )
        )
        self.wireless_env.reset(self.users)

    def finish_phase(self, phase: str, now_ms: int = 0, slot_index: int = 0):
        self.wireless_env.refresh_slot(self.users, slot_index=slot_index, slot_name=phase)
        candidates = self.collect_candidates(phase)
        ranked = self.ranking.rank(candidates)
        plan = self.planner.plan_phase(phase, ranked)
        for user in ranked:
            service_bits = sum(
                grant.bits_planned
                for slot_grants in plan.slot_grants.values()
                for grant in slot_grants
                if grant.ue_id == user.ue_id
            )
            self.reinsert.apply(
                self.queue,
                user,
                queue_wait_size=self.queue.size,
                service_bits_per_decision=service_bits,
                now_ms=now_ms,
                current_phase=phase,
                max_ue_per_slot=self.config.resources.max_ue_per_slot,
            )
        return plan

    def run(self) -> dict[str, float]:
        d_plan = self.finish_phase("D", now_ms=cycle_start_ms, slot_index=cycle_index * 5)
        s_plan = self.finish_phase("S", now_ms=cycle_start_ms + self.config.simulation.slot_duration_ms, slot_index=cycle_index * 5 + 1)
```

- [ ] **Step 4: Run the simulator test and adjacent regression tests**

Run: `PYTHONPATH=src python -m unittest tests.test_simulator tests.test_reinsert -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/scheduling_sim/simulator.py tests/test_simulator.py
git commit -m "feat: refresh wireless state before ds planning"
```

## Task 5: Update example config and run full regression

**Files:**
- Modify: `configs/edge_compare.json`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_simulator.py`
- Modify: `tests/test_wireless_env.py`

- [ ] **Step 1: Write the failing CLI fixture update**

```python
# tests/test_cli.py
payload = {
    "simulation": {"cycles": 1, "slot_duration_ms": 1, "tdd_pattern": "DSUUU"},
    "resources": {"total_prb_per_u_slot": 10, "max_ue_per_slot": 4},
    "traffic": {
        "center": {"count": 1, "period_slots": 1, "packet_bits": 40, "pdb_ms": 30},
        "edge": {"count": 1, "burst_cycle_interval": 1, "packet_bits": 100, "pdb_ms": 15}
    },
    "radio": {
        "environment": {
            "alpha": 0.95,
            "jitter_std_db": 0.2,
            "mcs_table": [
                {"snr_db": 0.0, "mcs_index": 0, "bits_per_prb": 4},
                {"snr_db": 8.0, "mcs_index": 1, "bits_per_prb": 10}
            ]
        },
        "center": {"base_snr_db": 16.0, "snr_min_db": 10.0, "snr_max_db": 22.0},
        "edge": {"base_snr_db": 4.0, "snr_min_db": -2.0, "snr_max_db": 8.0, "edge_per_u_slot_prb_cap": 4}
    },
    "scheduler": {"ranking": "epf", "reinsert_policy": "tail_append"},
    "report": {"output_dir": "outputs/smoke", "keep_slot_trace": False}
}
```

- [ ] **Step 2: Run the full test suite to capture remaining failures**

Run: `PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py' -v`

Expected: FAIL in any tests or fixtures that still reference static `bits_per_prb` config.

- [ ] **Step 3: Update the example config and remaining fixtures**

```json
// configs/edge_compare.json
{
  "simulation": {
    "cycles": 20,
    "slot_duration_ms": 1,
    "tdd_pattern": "DSUUU",
    "random_seed": 7
  },
  "resources": {
    "total_prb_per_u_slot": 106,
    "max_ue_per_slot": 16
  },
  "traffic": {
    "center": {
      "count": 60,
      "period_slots": 1,
      "packet_bits": 160,
      "pdb_ms": 30
    },
    "edge": {
      "count": 4,
      "burst_cycle_interval": 2,
      "packet_bits": 40000,
      "pdb_ms": 15
    }
  },
  "radio": {
    "environment": {
      "alpha": 0.95,
      "jitter_std_db": 0.25,
      "mcs_table": [
        {"snr_db": -2.0, "mcs_index": 0, "bits_per_prb": 3},
        {"snr_db": 2.0, "mcs_index": 1, "bits_per_prb": 5},
        {"snr_db": 6.0, "mcs_index": 2, "bits_per_prb": 8},
        {"snr_db": 10.0, "mcs_index": 3, "bits_per_prb": 12},
        {"snr_db": 14.0, "mcs_index": 4, "bits_per_prb": 16}
      ]
    },
    "center": {
      "base_snr_db": 16.0,
      "snr_min_db": 10.0,
      "snr_max_db": 22.0
    },
    "edge": {
      "base_snr_db": 3.0,
      "snr_min_db": -3.0,
      "snr_max_db": 8.0,
      "edge_per_u_slot_prb_cap": 18
    }
  },
  "scheduler": {
    "ranking": "epf",
    "reinsert_policy": "constrained_insert"
  },
  "report": {
    "output_dir": "outputs/edge_compare",
    "keep_slot_trace": false
  }
}
```

- [ ] **Step 4: Run regression and smoke verification**

Run: `PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py' -v`
Expected: PASS

Run: `PYTHONPATH=src python -m scheduling_sim.cli run configs/edge_compare.json`
Expected: `Report written to outputs/edge_compare/report.json using constrained_insert`

- [ ] **Step 5: Commit**

```bash
git add configs/edge_compare.json tests/test_cli.py tests/test_config.py tests/test_simulator.py tests/test_wireless_env.py
git commit -m "feat: integrate wireless environment into ul simulator"
```
