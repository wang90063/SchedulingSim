# No-PDB EPF + DSUUU EWMA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `avg_rate` a DSUUU-cycle EWMA rate and let no-PDB traffic use pure EPF without deadline weighting.

**Architecture:** Extend config and models so `pdb_ms` can be `null` and simulation config exposes `avg_rate_ewma_beta`. Keep per-cycle served-bit accounting inside `UlSimulator`, update `average_throughput` once per completed DSUUU cycle, and split `EpfRankingPolicy` into no-PDB pure EPF and PDB-aware urgency branches. Make compatibility fixes in reinsertion and metrics so `pdb_ms = null` does not break queueing, summaries, or reports.

**Tech Stack:** Python, `unittest`, existing scheduling simulator config/scenario/simulator pipeline

---

### Task 1: Add failing compatibility and ranking tests

**Files:**
- Modify: `tests/test_config.py`
- Modify: `tests/test_ranking.py`
- Modify: `tests/test_reinsert.py`

- [ ] **Step 1: Write the failing config test for nullable PDB and EWMA beta**

```python
    def test_load_config_supports_null_pdb_and_avg_rate_ewma_beta(self) -> None:
        payload = {
            "simulation": {
                "cycles": 2,
                "slot_duration_ms": 1,
                "tdd_pattern": "DSUUU",
                "avg_rate_ewma_beta": 0.8,
            },
            "resources": {"total_prb_per_u_slot": 10, "max_ue_per_slot": 2},
            "traffic": {
                "center": {"count": 1, "period_slots": 1, "packet_bits": 100, "pdb_ms": None},
                "edge": {"count": 1, "burst_cycle_interval": 1, "packet_bits": 200, "pdb_ms": 15},
            },
            "radio": {
                "center": {"bits_per_prb": 10, "per_u_slot_prb_cap": 10},
                "edge": {"bits_per_prb": 10, "per_u_slot_prb_cap": 4},
            },
            "scheduler": {"ranking": "epf", "reinsert_policy": "tail_append"},
            "report": {"output_dir": "outputs/test", "keep_slot_trace": False},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            config = load_config(path)
        self.assertEqual(config.simulation.avg_rate_ewma_beta, 0.8)
        self.assertIsNone(config.traffic.center.pdb_ms)
```

- [ ] **Step 2: Run the config test to verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_config.ConfigLoaderTests.test_load_config_supports_null_pdb_and_avg_rate_ewma_beta -v`
Expected: FAIL because `SimulationConfig` does not accept `avg_rate_ewma_beta` and `TrafficConfig` still expects `int`-only `pdb_ms`

- [ ] **Step 3: Write the failing ranking tests for no-PDB EPF and PDB urgency**

```python
    def test_no_pdb_user_uses_pure_epf_ratio(self) -> None:
        ranking = EpfRankingPolicy()
        no_pdb_fast = UserEquipment(
            ue_id="ue-no-pdb-fast",
            lc=LogicalChannel("lc-fast", [Packet("pkt-fast", 0, 300, 300, None, None)], eligible_cycle=0),
            is_edge_user=False,
            radio_profile=RadioProfile(bits_per_prb=12, per_u_slot_prb_cap=10),
            average_throughput=3.0,
            traffic_profile=TrafficProfile(packet_bits=300, pdb_ms=None),
            current_radio_state=None,
            hol_ms=29,
        )
        no_pdb_slow = UserEquipment(
            ue_id="ue-no-pdb-slow",
            lc=LogicalChannel("lc-slow", [Packet("pkt-slow", 0, 300, 300, None, None)], eligible_cycle=0),
            is_edge_user=False,
            radio_profile=RadioProfile(bits_per_prb=8, per_u_slot_prb_cap=10),
            average_throughput=4.0,
            traffic_profile=TrafficProfile(packet_bits=300, pdb_ms=None),
            current_radio_state=None,
            hol_ms=1,
        )
        ranked = ranking.rank([no_pdb_slow, no_pdb_fast])
        self.assertEqual([ue.ue_id for ue in ranked], ["ue-no-pdb-fast", "ue-no-pdb-slow"])

    def test_pdb_user_keeps_overdue_priority(self) -> None:
        ranking = EpfRankingPolicy()
        overdue = UserEquipment(
            ue_id="ue-overdue",
            lc=LogicalChannel("lc-overdue", [Packet("pkt-overdue", 0, 300, 300, 15, None)], eligible_cycle=0),
            is_edge_user=False,
            radio_profile=RadioProfile(bits_per_prb=4, per_u_slot_prb_cap=10),
            average_throughput=100.0,
            traffic_profile=TrafficProfile(packet_bits=300, pdb_ms=15),
            current_radio_state=None,
            hol_ms=20,
        )
        fresh = UserEquipment(
            ue_id="ue-fresh",
            lc=LogicalChannel("lc-fresh", [Packet("pkt-fresh", 0, 300, 300, 30, None)], eligible_cycle=0),
            is_edge_user=False,
            radio_profile=RadioProfile(bits_per_prb=20, per_u_slot_prb_cap=10),
            average_throughput=1.0,
            traffic_profile=TrafficProfile(packet_bits=300, pdb_ms=30),
            current_radio_state=None,
            hol_ms=1,
        )
        ranked = ranking.rank([fresh, overdue])
        self.assertEqual([ue.ue_id for ue in ranked], ["ue-overdue", "ue-fresh"])
```

- [ ] **Step 4: Run the ranking tests to verify they fail**

Run: `PYTHONPATH=src python -m unittest tests.test_ranking.EpfRankingTests.test_no_pdb_user_uses_pure_epf_ratio tests.test_ranking.EpfRankingTests.test_pdb_user_keeps_overdue_priority -v`
Expected: FAIL because `Packet`/`TrafficProfile` reject `None` `pdb_ms` and ranking still assumes deadline math for every head packet

- [ ] **Step 5: Write the failing reinsertion compatibility test**

```python
    def test_constrained_insert_treats_no_pdb_packet_as_tail_safe(self) -> None:
        queue = ActiveQueue()
        users = [self.make_ue(f"ue-{index}", remaining_bits=120) for index in range(3)]
        users[0].lc.head_packet.pdb_ms = None
        users[0].traffic_profile = TrafficProfile(packet_bits=120, pdb_ms=None)
        for user in users:
            queue.activate(user)
        ConstrainedInsertPolicy().apply(
            queue,
            users[0],
            queue_wait_size=queue.size,
            service_bits_per_decision=120,
            now_ms=8,
            current_phase="S",
            max_ue_per_slot=2,
        )
        self.assertEqual(queue.ordered_users()[-1].ue_id, users[0].ue_id)
```

- [ ] **Step 6: Run the reinsertion test to verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_reinsert.ReinsertionPolicyTests.test_constrained_insert_treats_no_pdb_packet_as_tail_safe -v`
Expected: FAIL because reinsertion still adds `arrival_time + head.pdb_ms`

### Task 2: Add failing simulator and metrics tests for DSUUU-cycle EWMA

**Files:**
- Modify: `tests/test_simulator.py`

- [ ] **Step 1: Write the failing simulator test for per-cycle EWMA update**

```python
    def test_run_updates_average_throughput_from_cycle_rate(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(
                cycles=1,
                slot_duration_ms=1,
                tdd_pattern="DSUUU",
                avg_rate_ewma_beta=0.5,
            ),
            resources=ResourcesConfig(total_prb_per_u_slot=10, max_ue_per_slot=1),
            traffic=TrafficSection(
                center=TrafficConfig(count=1, period_slots=10, packet_bits=20, pdb_ms=None),
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
        simulator.run()
        self.assertEqual(users[0].average_throughput, 3005.0)
```

- [ ] **Step 2: Run the simulator test to verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_simulator.SimulatorCycleTests.test_run_updates_average_throughput_from_cycle_rate -v`
Expected: FAIL because `average_throughput` is still overwritten with the last `bits_sent` value instead of `0.5 * 1 + 0.5 * (30000 / 5 ms)`

- [ ] **Step 3: Write the failing simulator test for zero-service cycle decay**

```python
    def test_run_decays_average_throughput_when_cycle_has_no_service(self) -> None:
        config = AppConfig(
            simulation=SimulationConfig(
                cycles=1,
                slot_duration_ms=1,
                tdd_pattern="DSUUU",
                avg_rate_ewma_beta=0.8,
            ),
            resources=ResourcesConfig(total_prb_per_u_slot=10, max_ue_per_slot=1),
            traffic=TrafficSection(
                center=TrafficConfig(count=1, period_slots=10, packet_bits=0, pdb_ms=None),
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
        users[0].average_throughput = 10.0
        simulator = UlSimulator(config, users, DummyMetrics())
        simulator.run()
        self.assertEqual(users[0].average_throughput, 8.0)
```

- [ ] **Step 4: Run the zero-service simulator test to verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_simulator.SimulatorCycleTests.test_run_decays_average_throughput_when_cycle_has_no_service -v`
Expected: FAIL because idle users are never updated toward `0`

- [ ] **Step 5: Write the failing metrics compatibility test**

```python
    def test_metrics_ignore_packets_without_pdb_in_deadline_kpis(self) -> None:
        collector = MetricsCollector()
        collector.record_packet_completed(
            packet_id="pkt-no-pdb",
            completion_time=10,
            arrival_time=0,
            pdb_ms=None,
            bits_sent=100,
            user_class="edge",
        )
        summary = collector.build_summary(total_prb_used=1, total_prb_available=1, users=[])
        self.assertEqual(summary["pdb_violation_rate"], 0.0)
        self.assertEqual(summary["edge_pdb_satisfaction_rate"], 0.0)
```

- [ ] **Step 6: Run the metrics test to verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_simulator.MetricsTests.test_metrics_ignore_packets_without_pdb_in_deadline_kpis -v`
Expected: FAIL because metrics still compare delays against `None`

### Task 3: Implement config/model/scheduler changes and verify them

**Files:**
- Modify: `src/scheduling_sim/config.py`
- Modify: `src/scheduling_sim/models.py`
- Modify: `src/scheduling_sim/scenario.py`
- Modify: `src/scheduling_sim/ranking.py`
- Modify: `src/scheduling_sim/reinsert.py`
- Modify: `src/scheduling_sim/simulator.py`
- Modify: `src/scheduling_sim/metrics.py`

- [ ] **Step 1: Add nullable PDB and EWMA beta to config and models**

```python
@dataclass(frozen=True)
class TrafficConfig:
    count: int
    packet_bits: int
    pdb_ms: int | None
    period_slots: int | None = None
    burst_cycle_interval: int | None = None
    gbr_bps: float = 0.0


@dataclass(frozen=True)
class SimulationConfig:
    cycles: int
    slot_duration_ms: int
    tdd_pattern: str
    random_seed: int = 0
    stop_when_target_edge_finished: bool = False
    deadline_guard_ms: int = 0
    avg_rate_ewma_beta: float = 0.9
```

- [ ] **Step 2: Propagate nullable PDB into scenario packets**

```python
                    traffic_profile=TrafficProfile(
                        packet_bits=self.config.traffic.center.packet_bits,
                        pdb_ms=self.config.traffic.center.pdb_ms,
                        period_slots=self.config.traffic.center.period_slots,
                        gbr_bps=self.config.traffic.center.gbr_bps,
                    ),
```

- [ ] **Step 3: Split ranking into no-PDB EPF and PDB urgency**

```python
    def _weight(self, ue: UserEquipment) -> float:
        head = ue.lc.head_packet
        if head is None:
            return 0.0
        inst_rate = (
            ue.current_radio_state.bits_per_prb
            if ue.current_radio_state is not None
            else ue.radio_profile.bits_per_prb
        )
        avg_rate = max(ue.average_throughput, 1.0)
        if head.pdb_ms is None:
            return inst_rate / avg_rate
        if ue.hol_ms >= head.pdb_ms:
            return 100.0
        hol_factor = ue.hol_ms / max(1, head.pdb_ms - ue.hol_ms)
        return (inst_rate / avg_rate) * hol_factor
```

- [ ] **Step 4: Make reinsertion and metrics null-safe**

```python
        if head.pdb_ms is None:
            return True
```

```python
        violations = [
            item
            for item in self.completed_packets
            if item["pdb_ms"] is not None and item["delay_ms"] > item["pdb_ms"]
        ]
```

- [ ] **Step 5: Replace per-send overwrite with DSUUU-cycle EWMA**

```python
        self._cycle_served_bits_by_ue = {user.ue_id: 0 for user in self.users}

    def _record_cycle_service(self, ue_id: str, bits_sent: int) -> None:
        self._cycle_served_bits_by_ue[ue_id] = self._cycle_served_bits_by_ue.get(ue_id, 0) + bits_sent

    def _close_cycle_average_throughput(self) -> None:
        cycle_duration_seconds = (
            len(self.config.simulation.tdd_pattern) * self.config.simulation.slot_duration_ms / 1000.0
        )
        beta = float(getattr(self.config.simulation, "avg_rate_ewma_beta", 0.9))
        for user in self.users:
            cycle_rate_bps = self._cycle_served_bits_by_ue.get(user.ue_id, 0) / cycle_duration_seconds
            user.average_throughput = (beta * user.average_throughput) + ((1.0 - beta) * cycle_rate_bps)
            self._cycle_served_bits_by_ue[user.ue_id] = 0
```

- [ ] **Step 6: Call the EWMA finalizer once per completed cycle**

```python
            for u_slot_index in range(3):
                ...
            self._close_cycle_average_throughput()
            if should_stop:
                break
```

- [ ] **Step 7: Run the focused regression suite**

Run: `PYTHONPATH=src python -m unittest tests.test_config.ConfigLoaderTests.test_load_config_supports_null_pdb_and_avg_rate_ewma_beta tests.test_ranking.EpfRankingTests tests.test_reinsert.ReinsertionPolicyTests.test_constrained_insert_treats_no_pdb_packet_as_tail_safe tests.test_simulator.SimulatorCycleTests.test_run_updates_average_throughput_from_cycle_rate tests.test_simulator.SimulatorCycleTests.test_run_decays_average_throughput_when_cycle_has_no_service tests.test_simulator.MetricsTests.test_metrics_ignore_packets_without_pdb_in_deadline_kpis -v`
Expected: PASS

- [ ] **Step 8: Run the broader local regression suite**

Run: `PYTHONPATH=src python -m unittest tests.test_config tests.test_ranking tests.test_reinsert tests.test_simulator -v`
Expected: PASS
