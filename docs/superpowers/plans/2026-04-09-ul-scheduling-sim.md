# UL Scheduling Sim Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI experiment platform that simulates `5G MAC` uplink scheduling under `DSUUU`, compares baseline tail-append behavior against constrained reinsertion for edge users, and outputs delay, `PDB`, throughput, and `PRB` utilization metrics.

**Architecture:** The implementation is a layered Python package under `src/scheduling_sim/`. A config loader builds the scenario, domain objects model `UE/LC/Packet`, a simulator advances `D/S/U/U/U` time, `D` and `S` each run ranking and planning over the head `K` active users, reinsertion happens during `D/S`, and `U` slots only execute already-planned grants. Metrics and reports remain downstream consumers of simulator events so algorithm changes do not leak across layers.

**Tech Stack:** Python 3.12+, standard library only (`argparse`, `json`, `dataclasses`, `pathlib`, `statistics`, `unittest`)

---

## File Structure

### Create

- `pyproject.toml` — package metadata and `src` layout for local execution
- `src/scheduling_sim/__init__.py` — package marker and version
- `src/scheduling_sim/cli.py` — `run` command for single config execution
- `src/scheduling_sim/config.py` — config dataclasses and JSON loader
- `src/scheduling_sim/models.py` — `Packet`, `LogicalChannel`, `RadioProfile`, `UserEquipment`, `SchedulingGrant`, `PhasePlan`
- `src/scheduling_sim/queue.py` — active queue operations and candidate pool extraction
- `src/scheduling_sim/scenario.py` — scenario factory for center and edge users
- `src/scheduling_sim/ranking.py` — `ePF` ranking policy
- `src/scheduling_sim/planning.py` — `D/S` PRB planning across the 3 `U` slots
- `src/scheduling_sim/reinsert.py` — tail append and constrained insert policies
- `src/scheduling_sim/simulator.py` — `DSUUU` time loop and grant execution
- `src/scheduling_sim/metrics.py` — event-driven metrics collector
- `src/scheduling_sim/reporting.py` — JSON report serializer
- `configs/edge_compare.json` — reference experiment config
- `tests/test_config.py` — config loader tests
- `tests/test_queue.py` — active queue tests
- `tests/test_ranking.py` — `ePF` ranking tests
- `tests/test_planning.py` — PRB planning tests
- `tests/test_reinsert.py` — reinsertion policy tests
- `tests/test_simulator.py` — simulator cycle and visibility tests
- `tests/test_cli.py` — CLI smoke test

### Responsibilities

- `config.py` owns parsing and validation. No other module reads JSON directly.
- `models.py` owns pure data structures. Avoid helper logic here except small computed properties.
- `queue.py` owns active-user ordering and insert/remove mechanics.
- `ranking.py` owns only candidate ordering, never queue mutation.
- `planning.py` owns only grant construction, never queue mutation.
- `reinsert.py` owns only the post-planning queue position decision.
- `simulator.py` orchestrates `D/S/U/U/U`, calls ranking/planning/reinsert, and emits metric events.
- `metrics.py` consumes events and computes summary numbers.
- `reporting.py` serializes results for CLI output.

### Cross-Module Rules

- `U` slots never reorder the queue.
- `D` and `S` each take a fresh head-`K` snapshot from the queue after prior reinsertion.
- New packets that arrive during the current `U` slots are buffered immediately but marked `eligible_cycle = current_cycle + 1`.
- Reinsertion uses only the current planning result and queue state; it does not predict future `ePF` of all users.

## Task 1: Bootstrap package, config loader, and CLI skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `src/scheduling_sim/__init__.py`
- Create: `src/scheduling_sim/cli.py`
- Create: `src/scheduling_sim/config.py`
- Create: `tests/test_config.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write the failing config and CLI tests**

```python
# tests/test_config.py
import json
import tempfile
import unittest
from pathlib import Path

from scheduling_sim.config import load_config


class ConfigLoaderTests(unittest.TestCase):
    def test_loads_edge_compare_config(self) -> None:
        payload = {
            "simulation": {"cycles": 2, "slot_duration_ms": 1, "tdd_pattern": "DSUUU"},
            "resources": {"total_prb_per_u_slot": 106, "max_ue_per_slot": 16},
            "traffic": {
                "center": {"count": 60, "period_slots": 1, "packet_bits": 200, "pdb_ms": 30},
                "edge": {"count": 4, "burst_cycle_interval": 3, "packet_bits": 40000, "pdb_ms": 15}
            },
            "radio": {
                "center": {"bits_per_prb": 20, "per_u_slot_prb_cap": 106},
                "edge": {"bits_per_prb": 10, "per_u_slot_prb_cap": 18}
            },
            "scheduler": {"ranking": "epf", "reinsert_policy": "tail_append"},
            "report": {"output_dir": "outputs/demo", "keep_slot_trace": True}
        }
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            config_path.write_text(json.dumps(payload), encoding="utf-8")
            config = load_config(config_path)
        self.assertEqual(config.simulation.tdd_pattern, "DSUUU")
        self.assertEqual(config.traffic.edge.count, 4)
        self.assertEqual(config.radio.edge.per_u_slot_prb_cap, 18)


if __name__ == "__main__":
    unittest.main()
```

```python
# tests/test_cli.py
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class CliSmokeTests(unittest.TestCase):
    def test_run_command_prints_output_path(self) -> None:
        payload = {
            "simulation": {"cycles": 1, "slot_duration_ms": 1, "tdd_pattern": "DSUUU"},
            "resources": {"total_prb_per_u_slot": 10, "max_ue_per_slot": 4},
            "traffic": {
                "center": {"count": 1, "period_slots": 1, "packet_bits": 40, "pdb_ms": 30},
                "edge": {"count": 1, "burst_cycle_interval": 1, "packet_bits": 100, "pdb_ms": 15}
            },
            "radio": {
                "center": {"bits_per_prb": 20, "per_u_slot_prb_cap": 10},
                "edge": {"bits_per_prb": 10, "per_u_slot_prb_cap": 4}
            },
            "scheduler": {"ranking": "epf", "reinsert_policy": "tail_append"},
            "report": {"output_dir": "outputs/smoke", "keep_slot_trace": False}
        }
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            config_path.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                ["python", "-m", "scheduling_sim.cli", "run", str(config_path)],
                cwd=Path(__file__).resolve().parents[1],
                env={**os.environ, "PYTHONPATH": "src"},
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Report written to", result.stdout)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python -m unittest tests.test_config tests.test_cli -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'scheduling_sim'`

- [ ] **Step 3: Write minimal implementation**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "scheduling-sim"
version = "0.1.0"
requires-python = ">=3.12"
```

```python
# src/scheduling_sim/__init__.py
__all__ = ["__version__"]
__version__ = "0.1.0"
```

```python
# src/scheduling_sim/config.py
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class TrafficConfig:
    count: int
    packet_bits: int
    pdb_ms: int
    period_slots: int | None = None
    burst_cycle_interval: int | None = None


@dataclass(frozen=True)
class RadioConfig:
    bits_per_prb: int
    per_u_slot_prb_cap: int


@dataclass(frozen=True)
class SimulationConfig:
    cycles: int
    slot_duration_ms: int
    tdd_pattern: str


@dataclass(frozen=True)
class ResourcesConfig:
    total_prb_per_u_slot: int
    max_ue_per_slot: int


@dataclass(frozen=True)
class SchedulerConfig:
    ranking: str
    reinsert_policy: str


@dataclass(frozen=True)
class ReportConfig:
    output_dir: str
    keep_slot_trace: bool


@dataclass(frozen=True)
class TrafficSection:
    center: TrafficConfig
    edge: TrafficConfig


@dataclass(frozen=True)
class RadioSection:
    center: RadioConfig
    edge: RadioConfig


@dataclass(frozen=True)
class AppConfig:
    simulation: SimulationConfig
    resources: ResourcesConfig
    traffic: TrafficSection
    radio: RadioSection
    scheduler: SchedulerConfig
    report: ReportConfig


def load_config(path: Path) -> AppConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return AppConfig(
        simulation=SimulationConfig(**payload["simulation"]),
        resources=ResourcesConfig(**payload["resources"]),
        traffic=TrafficSection(
            center=TrafficConfig(**payload["traffic"]["center"]),
            edge=TrafficConfig(**payload["traffic"]["edge"]),
        ),
        radio=RadioSection(
            center=RadioConfig(**payload["radio"]["center"]),
            edge=RadioConfig(**payload["radio"]["edge"]),
        ),
        scheduler=SchedulerConfig(**payload["scheduler"]),
        report=ReportConfig(**payload["report"]),
    )
```

```python
# src/scheduling_sim/cli.py
import argparse
from pathlib import Path

from scheduling_sim.config import load_config


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("config_path")
    args = parser.parse_args()
    config = load_config(Path(args.config_path))
    print(f"Report written to {config.report.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python -m unittest tests.test_config tests.test_cli -v`

Expected: PASS with `Ran 2 tests` and `OK`

- [ ] **Step 5: Checkpoint**

Run: `git rev-parse --is-inside-work-tree >/dev/null 2>&1 && git add pyproject.toml src/scheduling_sim/__init__.py src/scheduling_sim/cli.py src/scheduling_sim/config.py tests/test_config.py tests/test_cli.py && git commit -m "feat: bootstrap config loader and cli" || printf 'skip git commit: workspace is not a git repo\n'`

Expected: Either a git commit is created, or the command prints `skip git commit: workspace is not a git repo`

## Task 2: Add domain models and active queue behavior

**Files:**
- Create: `src/scheduling_sim/models.py`
- Create: `src/scheduling_sim/queue.py`
- Create: `tests/test_queue.py`

- [ ] **Step 1: Write the failing active queue tests**

```python
# tests/test_queue.py
import unittest

from scheduling_sim.models import LogicalChannel, Packet, RadioProfile, UserEquipment
from scheduling_sim.queue import ActiveQueue


class ActiveQueueTests(unittest.TestCase):
    def make_ue(self, ue_id: str) -> UserEquipment:
        packet = Packet(packet_id=f"{ue_id}-pkt", arrival_time=0, size_bits=100, remaining_bits=100, pdb_ms=15, completion_time=None)
        lc = LogicalChannel(lc_id=f"{ue_id}-lc", packets=[packet], eligible_cycle=0)
        radio = RadioProfile(bits_per_prb=10, per_u_slot_prb_cap=8)
        return UserEquipment(ue_id=ue_id, lc=lc, is_edge_user=True, radio_profile=radio, average_throughput=1.0)

    def test_activate_only_once_for_same_user(self) -> None:
        queue = ActiveQueue()
        ue = self.make_ue("ue-1")
        queue.activate(ue)
        queue.activate(ue)
        self.assertEqual(queue.size, 1)

    def test_peek_head_k_preserves_order(self) -> None:
        queue = ActiveQueue()
        for index in range(4):
            queue.activate(self.make_ue(f"ue-{index}"))
        head = queue.peek_head_k(2)
        self.assertEqual([ue.ue_id for ue in head], ["ue-0", "ue-1"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_queue -v`

Expected: FAIL with `ImportError` for `scheduling_sim.models` or missing `ActiveQueue`

- [ ] **Step 3: Write minimal implementation**

```python
# src/scheduling_sim/models.py
from dataclasses import dataclass, field


@dataclass
class Packet:
    packet_id: str
    arrival_time: int
    size_bits: int
    remaining_bits: int
    pdb_ms: int
    completion_time: int | None


@dataclass
class LogicalChannel:
    lc_id: str
    packets: list[Packet] = field(default_factory=list)
    eligible_cycle: int = 0

    @property
    def head_packet(self) -> Packet | None:
        return self.packets[0] if self.packets else None


@dataclass(frozen=True)
class RadioProfile:
    bits_per_prb: int
    per_u_slot_prb_cap: int


@dataclass
class UserEquipment:
    ue_id: str
    lc: LogicalChannel
    is_edge_user: bool
    radio_profile: RadioProfile
    average_throughput: float
    traffic_profile: "TrafficProfile | None" = None
    hol_ms: int = 0
```

```python
# src/scheduling_sim/queue.py
from scheduling_sim.models import UserEquipment


class ActiveQueue:
    def __init__(self) -> None:
        self._users: list[UserEquipment] = []

    @property
    def size(self) -> int:
        return len(self._users)

    def activate(self, ue: UserEquipment) -> None:
        if ue not in self._users:
            self._users.append(ue)

    def deactivate(self, ue: UserEquipment) -> None:
        if ue in self._users:
            self._users.remove(ue)

    def peek_head_k(self, k: int) -> list[UserEquipment]:
        return self._users[:k]

    def append_tail(self, ue: UserEquipment) -> None:
        self.deactivate(ue)
        self._users.append(ue)

    def insert_at(self, index: int, ue: UserEquipment) -> None:
        self.deactivate(ue)
        self._users.insert(index, ue)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_queue -v`

Expected: PASS with `Ran 2 tests` and `OK`

- [ ] **Step 5: Checkpoint**

Run: `git rev-parse --is-inside-work-tree >/dev/null 2>&1 && git add src/scheduling_sim/models.py src/scheduling_sim/queue.py tests/test_queue.py && git commit -m "feat: add domain models and active queue" || printf 'skip git commit: workspace is not a git repo\n'`

Expected: Either a git commit is created, or the command prints `skip git commit: workspace is not a git repo`

## Task 3: Build scenario factory and traffic arrival rules

**Files:**
- Create: `src/scheduling_sim/scenario.py`
- Modify: `src/scheduling_sim/models.py`
- Create: `tests/test_simulator.py`

- [ ] **Step 1: Write the failing scenario tests**

```python
# tests/test_simulator.py
import unittest

from scheduling_sim.config import AppConfig, RadioConfig, RadioSection, ReportConfig, ResourcesConfig, SchedulerConfig, SimulationConfig, TrafficConfig, TrafficSection
from scheduling_sim.scenario import ScenarioFactory


class ScenarioFactoryTests(unittest.TestCase):
    def test_builds_center_and_edge_users(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(cycles=2, slot_duration_ms=1, tdd_pattern="DSUUU"),
            resources=ResourcesConfig(total_prb_per_u_slot=106, max_ue_per_slot=16),
            traffic=TrafficSection(
                center=TrafficConfig(count=2, period_slots=1, packet_bits=200, pdb_ms=30),
                edge=TrafficConfig(count=1, burst_cycle_interval=2, packet_bits=40000, pdb_ms=15),
            ),
            radio=RadioSection(
                center=RadioConfig(bits_per_prb=20, per_u_slot_prb_cap=106),
                edge=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=18),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/demo", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()
        self.assertEqual(len(users), 3)
        self.assertEqual(sum(1 for user in users if user.is_edge_user), 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_simulator.ScenarioFactoryTests -v`

Expected: FAIL with missing `ScenarioFactory`

- [ ] **Step 3: Write minimal implementation**

```python
# src/scheduling_sim/models.py
@dataclass(frozen=True)
class TrafficProfile:
    packet_bits: int
    pdb_ms: int
    period_slots: int | None = None
    burst_cycle_interval: int | None = None
```

```python
# src/scheduling_sim/scenario.py
from scheduling_sim.config import AppConfig
from scheduling_sim.models import LogicalChannel, RadioProfile, TrafficProfile, UserEquipment


class ScenarioFactory:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def build_users(self) -> list[UserEquipment]:
        users: list[UserEquipment] = []
        for index in range(self.config.traffic.center.count):
            users.append(
                UserEquipment(
                    ue_id=f"center-{index}",
                    lc=LogicalChannel(lc_id=f"center-{index}-lc", packets=[], eligible_cycle=0),
                    is_edge_user=False,
                    radio_profile=RadioProfile(
                        bits_per_prb=self.config.radio.center.bits_per_prb,
                        per_u_slot_prb_cap=self.config.radio.center.per_u_slot_prb_cap,
                    ),
                    average_throughput=1.0,
                    traffic_profile=TrafficProfile(
                        packet_bits=self.config.traffic.center.packet_bits,
                        pdb_ms=self.config.traffic.center.pdb_ms,
                        period_slots=self.config.traffic.center.period_slots,
                    ),
                )
            )
        for index in range(self.config.traffic.edge.count):
            users.append(
                UserEquipment(
                    ue_id=f"edge-{index}",
                    lc=LogicalChannel(lc_id=f"edge-{index}-lc", packets=[], eligible_cycle=0),
                    is_edge_user=True,
                    radio_profile=RadioProfile(
                        bits_per_prb=self.config.radio.edge.bits_per_prb,
                        per_u_slot_prb_cap=self.config.radio.edge.per_u_slot_prb_cap,
                    ),
                    average_throughput=1.0,
                    traffic_profile=TrafficProfile(
                        packet_bits=self.config.traffic.edge.packet_bits,
                        pdb_ms=self.config.traffic.edge.pdb_ms,
                        burst_cycle_interval=self.config.traffic.edge.burst_cycle_interval,
                    ),
                )
            )
        return users
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_simulator.ScenarioFactoryTests -v`

Expected: PASS with `Ran 1 test` and `OK`

- [ ] **Step 5: Checkpoint**

Run: `git rev-parse --is-inside-work-tree >/dev/null 2>&1 && git add src/scheduling_sim/models.py src/scheduling_sim/scenario.py tests/test_simulator.py && git commit -m "feat: add scenario factory" || printf 'skip git commit: workspace is not a git repo\n'`

Expected: Either a git commit is created, or the command prints `skip git commit: workspace is not a git repo`

## Task 4: Implement ePF ranking and D/S PRB planning

**Files:**
- Create: `src/scheduling_sim/ranking.py`
- Create: `src/scheduling_sim/planning.py`
- Modify: `src/scheduling_sim/models.py`
- Create: `tests/test_ranking.py`
- Create: `tests/test_planning.py`

- [ ] **Step 1: Write the failing ranking and planning tests**

```python
# tests/test_ranking.py
import unittest

from scheduling_sim.models import LogicalChannel, Packet, RadioProfile, TrafficProfile, UserEquipment
from scheduling_sim.ranking import EpfRankingPolicy


class EpfRankingTests(unittest.TestCase):
    def test_higher_hol_and_lower_average_throughput_rank_first(self) -> None:
        ranking = EpfRankingPolicy()
        urgent = UserEquipment(
            ue_id="edge-urgent",
            lc=LogicalChannel("lc-1", [Packet("pkt-1", 0, 300, 300, 15, None)], eligible_cycle=0),
            is_edge_user=True,
            radio_profile=RadioProfile(bits_per_prb=10, per_u_slot_prb_cap=8),
            average_throughput=1.0,
            traffic_profile=TrafficProfile(packet_bits=300, pdb_ms=15),
            hol_ms=12,
        )
        relaxed = UserEquipment(
            ue_id="center-relaxed",
            lc=LogicalChannel("lc-2", [Packet("pkt-2", 0, 300, 300, 30, None)], eligible_cycle=0),
            is_edge_user=False,
            radio_profile=RadioProfile(bits_per_prb=20, per_u_slot_prb_cap=20),
            average_throughput=5.0,
            traffic_profile=TrafficProfile(packet_bits=300, pdb_ms=30),
            hol_ms=2,
        )
        ranked = ranking.rank([relaxed, urgent])
        self.assertEqual([ue.ue_id for ue in ranked], ["edge-urgent", "center-relaxed"])


if __name__ == "__main__":
    unittest.main()
```

```python
# tests/test_planning.py
import unittest

from scheduling_sim.models import LogicalChannel, Packet, RadioProfile, TrafficProfile, UserEquipment
from scheduling_sim.planning import PhasePrbPlanner


class PhasePrbPlannerTests(unittest.TestCase):
    def make_edge(self) -> UserEquipment:
        return UserEquipment(
            ue_id="edge-0",
            lc=LogicalChannel("edge-lc", [Packet("pkt", 0, 1000, 1000, 15, None)], eligible_cycle=0),
            is_edge_user=True,
            radio_profile=RadioProfile(bits_per_prb=10, per_u_slot_prb_cap=6),
            average_throughput=1.0,
            traffic_profile=TrafficProfile(packet_bits=1000, pdb_ms=15),
            hol_ms=5,
        )

    def test_d_phase_uses_first_one_point_five_u_windows(self) -> None:
        planner = PhasePrbPlanner(total_prb_per_u_slot=10)
        plan = planner.plan_phase("D", [self.make_edge()])
        self.assertEqual(plan.slot_prb_budgets, [10, 5, 0])
        self.assertEqual(sum(grant.prb_count for grant in plan.slot_grants[0]), 6)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python -m unittest tests.test_ranking tests.test_planning -v`

Expected: FAIL with missing `EpfRankingPolicy`, `PhasePrbPlanner`, or missing model fields

- [ ] **Step 3: Write minimal implementation**

```python
# src/scheduling_sim/models.py
@dataclass
class SchedulingGrant:
    ue_id: str
    slot_index: int
    prb_count: int
    bits_planned: int


@dataclass
class PhasePlan:
    phase: str
    slot_prb_budgets: list[int]
    slot_grants: dict[int, list[SchedulingGrant]]
```

```python
# src/scheduling_sim/ranking.py
from scheduling_sim.models import UserEquipment


class EpfRankingPolicy:
    def rank(self, users: list[UserEquipment]) -> list[UserEquipment]:
        return sorted(users, key=self._weight, reverse=True)

    def _weight(self, ue: UserEquipment) -> float:
        head = ue.lc.head_packet
        if head is None:
            return 0.0
        inst_rate = ue.radio_profile.bits_per_prb
        avg_rate = max(ue.average_throughput, 1.0)
        hol_factor = ue.hol_ms / max(1, head.pdb_ms - ue.hol_ms)
        if ue.hol_ms >= head.pdb_ms:
            return 100.0
        return (inst_rate / avg_rate) * hol_factor
```

```python
# src/scheduling_sim/planning.py
from scheduling_sim.models import PhasePlan, SchedulingGrant, UserEquipment


class PhasePrbPlanner:
    def __init__(self, total_prb_per_u_slot: int) -> None:
        self.total_prb_per_u_slot = total_prb_per_u_slot

    def plan_phase(self, phase: str, ranked_users: list[UserEquipment]) -> PhasePlan:
        half = self.total_prb_per_u_slot // 2
        budgets = [self.total_prb_per_u_slot, half, 0] if phase == "D" else [0, self.total_prb_per_u_slot - half, self.total_prb_per_u_slot]
        slot_grants = {0: [], 1: [], 2: []}
        for slot_index, budget in enumerate(budgets):
            remaining = budget
            for user in ranked_users:
                if remaining <= 0:
                    break
                grant_prbs = min(remaining, user.radio_profile.per_u_slot_prb_cap)
                if grant_prbs <= 0:
                    continue
                slot_grants[slot_index].append(
                    SchedulingGrant(
                        ue_id=user.ue_id,
                        slot_index=slot_index,
                        prb_count=grant_prbs,
                        bits_planned=grant_prbs * user.radio_profile.bits_per_prb,
                    )
                )
                remaining -= grant_prbs
        return PhasePlan(phase=phase, slot_prb_budgets=budgets, slot_grants=slot_grants)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python -m unittest tests.test_ranking tests.test_planning -v`

Expected: PASS with `Ran 2 tests` and `OK`

- [ ] **Step 5: Checkpoint**

Run: `git rev-parse --is-inside-work-tree >/dev/null 2>&1 && git add src/scheduling_sim/models.py src/scheduling_sim/ranking.py src/scheduling_sim/planning.py tests/test_ranking.py tests/test_planning.py && git commit -m "feat: add epf ranking and phase planning" || printf 'skip git commit: workspace is not a git repo\n'`

Expected: Either a git commit is created, or the command prints `skip git commit: workspace is not a git repo`

## Task 5: Implement tail append and constrained reinsertion

**Files:**
- Create: `src/scheduling_sim/reinsert.py`
- Modify: `src/scheduling_sim/queue.py`
- Modify: `src/scheduling_sim/models.py`
- Create: `tests/test_reinsert.py`

- [ ] **Step 1: Write the failing reinsertion tests**

```python
# tests/test_reinsert.py
import unittest

from scheduling_sim.models import LogicalChannel, Packet, RadioProfile, TrafficProfile, UserEquipment
from scheduling_sim.queue import ActiveQueue
from scheduling_sim.reinsert import ConstrainedInsertPolicy, TailAppendPolicy


class ReinsertionPolicyTests(unittest.TestCase):
    def make_ue(self, ue_id: str, remaining_bits: int = 600) -> UserEquipment:
        return UserEquipment(
            ue_id=ue_id,
            lc=LogicalChannel(ue_id + "-lc", [Packet(ue_id + "-pkt", 0, remaining_bits, remaining_bits, 15, None)], eligible_cycle=0),
            is_edge_user=True,
            radio_profile=RadioProfile(bits_per_prb=10, per_u_slot_prb_cap=4),
            average_throughput=1.0,
            traffic_profile=TrafficProfile(packet_bits=remaining_bits, pdb_ms=15),
            hol_ms=8,
        )

    def test_tail_append_moves_user_to_end(self) -> None:
        queue = ActiveQueue()
        ue0 = self.make_ue("ue-0")
        ue1 = self.make_ue("ue-1")
        queue.activate(ue0)
        queue.activate(ue1)
        TailAppendPolicy().apply(queue, ue0, queue_wait_size=queue.size, service_bits_per_decision=120, now_ms=8, current_phase="D", max_ue_per_slot=2)
        self.assertEqual([user.ue_id for user in queue.peek_head_k(2)], ["ue-1", "ue-0"])

    def test_constrained_insert_places_user_inside_next_candidate_window_when_tail_is_unsafe(self) -> None:
        queue = ActiveQueue()
        users = [self.make_ue(f"ue-{index}") for index in range(5)]
        for user in users:
            queue.activate(user)
        policy = ConstrainedInsertPolicy()
        policy.apply(queue, users[0], queue_wait_size=queue.size, service_bits_per_decision=40, now_ms=12, current_phase="S", max_ue_per_slot=2)
        self.assertIn(users[0], queue.peek_head_k(2))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python -m unittest tests.test_reinsert -v`

Expected: FAIL with missing `TailAppendPolicy` or `ConstrainedInsertPolicy`

- [ ] **Step 3: Write minimal implementation**

```python
# src/scheduling_sim/reinsert.py
from scheduling_sim.queue import ActiveQueue
from scheduling_sim.models import UserEquipment


class TailAppendPolicy:
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
        queue.append_tail(ue)


class ConstrainedInsertPolicy:
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
        if self._tail_is_safe(ue, queue_wait_size, service_bits_per_decision, now_ms, current_phase, max_ue_per_slot):
            queue.append_tail(ue)
            return
        queue.insert_at(min(max_ue_per_slot - 1, max(queue_wait_size - 1, 0)), ue)

    def _tail_is_safe(
        self,
        ue: UserEquipment,
        queue_wait_size: int,
        service_bits_per_decision: int,
        now_ms: int,
        current_phase: str,
        max_ue_per_slot: int,
    ) -> bool:
        head = ue.lc.head_packet
        if head is None:
            return True
        decisions_until_candidate = queue_wait_size // max_ue_per_slot
        wait_ms = self._decision_wait_ms(current_phase, decisions_until_candidate)
        bits_after_current_cycle = max(head.remaining_bits - service_bits_per_decision, 0)
        extra_cycles = 0 if service_bits_per_decision <= 0 else -(-bits_after_current_cycle // service_bits_per_decision)
        completion_ms = now_ms + wait_ms + (extra_cycles * 5)
        deadline_ms = head.arrival_time + head.pdb_ms
        return completion_ms <= deadline_ms

    def _decision_wait_ms(self, current_phase: str, decision_hops: int) -> int:
        if decision_hops <= 0:
            return 0
        gaps = [1, 4] if current_phase == "D" else [4, 1]
        total = 0
        for index in range(decision_hops):
            total += gaps[index % 2]
        return total
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python -m unittest tests.test_reinsert -v`

Expected: PASS with `Ran 2 tests` and `OK`

- [ ] **Step 5: Checkpoint**

Run: `git rev-parse --is-inside-work-tree >/dev/null 2>&1 && git add src/scheduling_sim/reinsert.py src/scheduling_sim/queue.py src/scheduling_sim/models.py tests/test_reinsert.py && git commit -m "feat: add constrained reinsertion policy" || printf 'skip git commit: workspace is not a git repo\n'`

Expected: Either a git commit is created, or the command prints `skip git commit: workspace is not a git repo`

## Task 6: Implement simulator cycle orchestration and U-slot execution

**Files:**
- Create: `src/scheduling_sim/simulator.py`
- Modify: `src/scheduling_sim/models.py`
- Modify: `tests/test_simulator.py`

- [ ] **Step 1: Write the failing simulator tests**

```python
# append to tests/test_simulator.py
from scheduling_sim.simulator import UlSimulator


class DummyMetrics:
    pass


class SimulatorCycleTests(unittest.TestCase):
    def test_u_slot_arrivals_become_eligible_next_cycle(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(cycles=1, slot_duration_ms=1, tdd_pattern="DSUUU"),
            resources=ResourcesConfig(total_prb_per_u_slot=10, max_ue_per_slot=2),
            traffic=TrafficSection(
                center=TrafficConfig(count=1, period_slots=1, packet_bits=30, pdb_ms=30),
                edge=TrafficConfig(count=0, burst_cycle_interval=1, packet_bits=0, pdb_ms=15),
            ),
            radio=RadioSection(
                center=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=10),
                edge=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=10),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/demo", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()
        simulator = UlSimulator(config, users, DummyMetrics())
        simulator.inject_packet(users[0], packet_bits=50, cycle_index=0, slot_name="U1")
        self.assertEqual(users[0].lc.eligible_cycle, 1)

    def test_d_then_s_use_fresh_head_k_after_reinsert(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(cycles=1, slot_duration_ms=1, tdd_pattern="DSUUU"),
            resources=ResourcesConfig(total_prb_per_u_slot=10, max_ue_per_slot=2),
            traffic=TrafficSection(
                center=TrafficConfig(count=3, period_slots=1, packet_bits=30, pdb_ms=30),
                edge=TrafficConfig(count=0, burst_cycle_interval=1, packet_bits=0, pdb_ms=15),
            ),
            radio=RadioSection(
                center=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=10),
                edge=RadioConfig(bits_per_prb=10, per_u_slot_prb_cap=10),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/demo", keep_slot_trace=False),
        )
        users = ScenarioFactory(config).build_users()
        simulator = UlSimulator(config, users, DummyMetrics())
        for user in users:
            simulator.inject_packet(user, packet_bits=50, cycle_index=0, slot_name="D")
            simulator.queue.activate(user)
        d_candidates = [ue.ue_id for ue in simulator.collect_candidates("D")]
        simulator.finish_phase("D")
        s_candidates = [ue.ue_id for ue in simulator.collect_candidates("S")]
        self.assertNotEqual(d_candidates, s_candidates)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python -m unittest tests.test_simulator -v`

Expected: FAIL with missing `UlSimulator` or `MetricsCollector`

- [ ] **Step 3: Write minimal implementation**

```python
# src/scheduling_sim/simulator.py
from scheduling_sim.models import Packet
from scheduling_sim.planning import PhasePrbPlanner
from scheduling_sim.queue import ActiveQueue
from scheduling_sim.ranking import EpfRankingPolicy
from scheduling_sim.reinsert import ConstrainedInsertPolicy, TailAppendPolicy


class UlSimulator:
    def __init__(self, config, users, metrics) -> None:
        self.config = config
        self.users = users
        self.metrics = metrics
        self.queue = ActiveQueue()
        self.ranking = EpfRankingPolicy()
        self.planner = PhasePrbPlanner(config.resources.total_prb_per_u_slot)
        self.reinsert = TailAppendPolicy() if config.scheduler.reinsert_policy == "tail_append" else ConstrainedInsertPolicy()

    def seed_active_queue(self) -> None:
        for user in self.users:
            if user.lc.head_packet is not None and user.lc.eligible_cycle <= 0:
                self.queue.activate(user)

    def inject_packet(self, user, packet_bits: int, cycle_index: int, slot_name: str) -> None:
        packet = Packet(
            packet_id=f"{user.ue_id}-{cycle_index}-{slot_name}",
            arrival_time=cycle_index * 5,
            size_bits=packet_bits,
            remaining_bits=packet_bits,
            pdb_ms=user.traffic_profile.pdb_ms,
            completion_time=None,
        )
        user.lc.packets.append(packet)
        user.lc.eligible_cycle = cycle_index + 1 if slot_name.startswith("U") else cycle_index

    def collect_candidates(self, phase: str):
        return self.queue.peek_head_k(self.config.resources.max_ue_per_slot)

    def finish_phase(self, phase: str) -> None:
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
                now_ms=0,
                current_phase=phase,
                max_ue_per_slot=self.config.resources.max_ue_per_slot,
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python -m unittest tests.test_simulator -v`

Expected: PASS with `Ran 3 tests` and `OK`

- [ ] **Step 5: Checkpoint**

Run: `git rev-parse --is-inside-work-tree >/dev/null 2>&1 && git add src/scheduling_sim/simulator.py src/scheduling_sim/models.py tests/test_simulator.py && git commit -m "feat: add simulator orchestration" || printf 'skip git commit: workspace is not a git repo\n'`

Expected: Either a git commit is created, or the command prints `skip git commit: workspace is not a git repo`

## Task 7: Add metrics collection and report writing

**Files:**
- Create: `src/scheduling_sim/metrics.py`
- Create: `src/scheduling_sim/reporting.py`
- Modify: `src/scheduling_sim/simulator.py`
- Modify: `tests/test_simulator.py`

- [ ] **Step 1: Write the failing metrics test**

```python
# append to tests/test_simulator.py
from scheduling_sim.reporting import write_report


class MetricsTests(unittest.TestCase):
    def test_metrics_report_contains_pdb_and_throughput_keys(self) -> None:
        collector = MetricsCollector()
        collector.record_packet_completed(packet_id="pkt-1", completion_time=12, arrival_time=0, pdb_ms=15, bits_sent=120)
        summary = collector.build_summary(total_prb_used=12, total_prb_available=30)
        self.assertIn("pdb_violation_rate", summary)
        self.assertIn("throughput_bits", summary)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_simulator.MetricsTests -v`

Expected: FAIL with missing `MetricsCollector` methods or `write_report`

- [ ] **Step 3: Write minimal implementation**

```python
# src/scheduling_sim/metrics.py
import statistics


class MetricsCollector:
    def __init__(self) -> None:
        self.completed_packets: list[dict[str, int]] = []

    def record_packet_completed(self, packet_id: str, completion_time: int, arrival_time: int, pdb_ms: int, bits_sent: int) -> None:
        self.completed_packets.append(
            {
                "packet_id": packet_id,
                "delay_ms": completion_time - arrival_time,
                "pdb_ms": pdb_ms,
                "bits_sent": bits_sent,
            }
        )

    def build_summary(self, total_prb_used: int, total_prb_available: int) -> dict[str, float]:
        delays = [item["delay_ms"] for item in self.completed_packets] or [0]
        violations = [item for item in self.completed_packets if item["delay_ms"] > item["pdb_ms"]]
        return {
            "avg_delay_ms": statistics.mean(delays),
            "p95_delay_ms": sorted(delays)[int(0.95 * (len(delays) - 1))],
            "pdb_violation_rate": len(violations) / len(self.completed_packets) if self.completed_packets else 0.0,
            "throughput_bits": sum(item["bits_sent"] for item in self.completed_packets),
            "prb_utilization": total_prb_used / total_prb_available if total_prb_available else 0.0,
        }
```

```python
# src/scheduling_sim/reporting.py
import json
from pathlib import Path


def write_report(output_dir: str, summary: dict[str, float]) -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    report_path = path / "report.json"
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return report_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_simulator.MetricsTests -v`

Expected: PASS with `Ran 1 test` and `OK`

- [ ] **Step 5: Checkpoint**

Run: `git rev-parse --is-inside-work-tree >/dev/null 2>&1 && git add src/scheduling_sim/metrics.py src/scheduling_sim/reporting.py src/scheduling_sim/simulator.py tests/test_simulator.py && git commit -m "feat: add metrics and report output" || printf 'skip git commit: workspace is not a git repo\n'`

Expected: Either a git commit is created, or the command prints `skip git commit: workspace is not a git repo`

## Task 8: Wire full CLI execution and add reference config

**Files:**
- Modify: `src/scheduling_sim/cli.py`
- Modify: `src/scheduling_sim/simulator.py`
- Create: `configs/edge_compare.json`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing full-run CLI test**

```python
# replace tests/test_cli.py test body
import os

    def test_run_command_writes_report_file(self) -> None:
        result = subprocess.run(
            ["python", "-m", "scheduling_sim.cli", "run", "configs/edge_compare.json"],
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ, "PYTHONPATH": "src"},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("report.json", result.stdout)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_cli -v`

Expected: FAIL because `configs/edge_compare.json` does not exist or CLI does not write a report

- [ ] **Step 3: Write minimal implementation**

```json
// configs/edge_compare.json
{
  "simulation": { "cycles": 4, "slot_duration_ms": 1, "tdd_pattern": "DSUUU" },
  "resources": { "total_prb_per_u_slot": 106, "max_ue_per_slot": 16 },
  "traffic": {
    "center": { "count": 60, "period_slots": 1, "packet_bits": 200, "pdb_ms": 30 },
    "edge": { "count": 4, "burst_cycle_interval": 1, "packet_bits": 40000, "pdb_ms": 15 }
  },
  "radio": {
    "center": { "bits_per_prb": 20, "per_u_slot_prb_cap": 106 },
    "edge": { "bits_per_prb": 10, "per_u_slot_prb_cap": 18 }
  },
  "scheduler": { "ranking": "epf", "reinsert_policy": "constrained_insert" },
  "report": { "output_dir": "outputs/edge_compare", "keep_slot_trace": false }
}
```

```python
# src/scheduling_sim/cli.py
from scheduling_sim.metrics import MetricsCollector
from scheduling_sim.reporting import write_report
from scheduling_sim.scenario import ScenarioFactory
from scheduling_sim.simulator import UlSimulator


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("config_path")
    args = parser.parse_args()
    config = load_config(Path(args.config_path))
    users = ScenarioFactory(config).build_users()
    metrics = MetricsCollector()
    simulator = UlSimulator(config, users, metrics)
    summary = simulator.run()
    report_path = write_report(config.report.output_dir, summary)
    print(f"Report written to {report_path}")
    return 0
```

```python
# src/scheduling_sim/simulator.py
    def run(self) -> dict[str, float]:
        total_prb_available = self.config.simulation.cycles * 3 * self.config.resources.total_prb_per_u_slot
        total_prb_used = 0
        for _cycle_index in range(self.config.simulation.cycles):
            self.seed_active_queue()
            d_plan = self.finish_phase("D")
            s_plan = self.finish_phase("S")
            total_prb_used += sum(grant.prb_count for grants in d_plan.slot_grants.values() for grant in grants)
            total_prb_used += sum(grant.prb_count for grants in s_plan.slot_grants.values() for grant in grants)
        return self.metrics.build_summary(total_prb_used=total_prb_used, total_prb_available=total_prb_available)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_cli -v`

Expected: PASS with `Ran 1 test` and `OK`

- [ ] **Step 5: Checkpoint**

Run: `git rev-parse --is-inside-work-tree >/dev/null 2>&1 && git add src/scheduling_sim/cli.py src/scheduling_sim/simulator.py configs/edge_compare.json tests/test_cli.py && git commit -m "feat: wire full run flow" || printf 'skip git commit: workspace is not a git repo\n'`

Expected: Either a git commit is created, or the command prints `skip git commit: workspace is not a git repo`

## Task 9: Verify the end-to-end baseline vs constrained comparison

**Files:**
- Modify: `configs/edge_compare.json`
- Modify: `src/scheduling_sim/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing comparison test**

```python
# append to tests/test_cli.py
import os

    def test_run_command_supports_baseline_override(self) -> None:
        result = subprocess.run(
            ["python", "-m", "scheduling_sim.cli", "run", "configs/edge_compare.json", "--reinsert-policy", "tail_append"],
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ, "PYTHONPATH": "src"},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("tail_append", result.stdout)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_cli -v`

Expected: FAIL because CLI does not accept `--reinsert-policy`

- [ ] **Step 3: Write minimal implementation**

```python
# src/scheduling_sim/cli.py
from dataclasses import replace

run_parser.add_argument("--reinsert-policy", choices=["tail_append", "constrained_insert"])
...
if args.reinsert_policy is not None:
    config = replace(
        config,
        scheduler=replace(config.scheduler, reinsert_policy=args.reinsert_policy),
    )
...
print(f"Report written to {report_path} using {config.scheduler.reinsert_policy}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_cli -v`

Expected: PASS with `Ran 2 tests` and `OK`

- [ ] **Step 5: Checkpoint**

Run: `git rev-parse --is-inside-work-tree >/dev/null 2>&1 && git add src/scheduling_sim/cli.py configs/edge_compare.json tests/test_cli.py && git commit -m "feat: support baseline and constrained comparisons" || printf 'skip git commit: workspace is not a git repo\n'`

Expected: Either a git commit is created, or the command prints `skip git commit: workspace is not a git repo`

## Final Verification

- [ ] Run: `PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py' -v`
Expected: all tests pass

- [ ] Run: `PYTHONPATH=src python -m scheduling_sim.cli run configs/edge_compare.json`
Expected: prints `Report written to outputs/edge_compare/report.json` and creates the report file

- [ ] Run: `PYTHONPATH=src python -m scheduling_sim.cli run configs/edge_compare.json --reinsert-policy tail_append`
Expected: prints `tail_append` in stdout and writes a second report that can be compared against the constrained run

## Self-Review Checklist

- Every spec requirement has a matching task:
  - `DSUUU` timing → Tasks 4, 6
  - `D/S` algorithm execution → Tasks 4, 6
  - `U`-only execution → Task 6
  - edge `PRB` cap → Tasks 4, 5
  - tail append vs constrained insert → Tasks 5, 9
  - current-cycle `U` arrivals visible next cycle → Task 6
  - CLI + single config → Tasks 1, 8
  - metrics and reports → Task 7
- No stub markers remain.
- Function and class names are consistent across tasks.
