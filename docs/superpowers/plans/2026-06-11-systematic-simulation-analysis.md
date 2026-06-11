# Systematic Simulation Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first `option 1: 系统性分析` pipeline: reusable `64 UE` realization banks with controlled `poor/medium/good` `SINR` classes, paired `baseline/proposed` panoramic sweeps across the approved `81`-point business grid, and output artifacts that summarize `PDB` gain, `center` cost, feasible-boundary expansion, and representative scene points.

**Architecture:** Base the worktree on the branch that already contains the periodic fixed-window simulator semantics from `2026-06-10-periodic-pdb-fixed-window-design.md`. On top of that base, first make `UMA` wireless randomness subset-invariant so a `64 UE` mother scene can be sliced without changing its radio evolution. Then add a focused `systematic_analysis` module that owns realization-bank generation, nested slicing, paired metrics, region summaries, and capacity summaries; a runner script will drive the sweep and write CSV/JSON/Markdown outputs, and a separate renderer script will turn those tables into overview, cost, and boundary figures.

**Tech Stack:** Python, `unittest`, existing simulator/config/metrics modules, `matplotlib`, JSON/CSV/Markdown outputs.

---

## Proposed File Structure

- Modify: `src/scheduling_sim/wireless_env.py`
  - Make `UMA` randomness deterministic per `UE` and per slot so subset order and subset membership do not perturb the same user's radio trace.
- Create: `src/scheduling_sim/systematic_analysis.py`
  - Own the `SceneBankSpec`, `RealizationBank`, `SystematicCase`, bank generation, nested slicing, per-run row builders, paired aggregations, region summaries, capacity summaries, and typical-case selection helpers.
- Create: `scripts/run_systematic_simulation_analysis.py`
  - Read the reference config, build realization banks, run paired `baseline/proposed` sweeps, and write manifest/table/report artifacts.
- Create: `scripts/render_systematic_simulation_analysis_plots.py`
  - Read the runner outputs and render the `3 x 3` gain, cost, and boundary figures.
- Create: `configs/systematic_simulation_analysis_option1.json`
  - Checked-in reference config for the approved first-pass scan.
- Modify: `tests/test_wireless_env.py`
  - Add subset-invariance regressions for the wireless environment.
- Create: `tests/test_systematic_analysis.py`
  - Cover bank construction, class-range validation, nested slicing, paired aggregation, region summaries, boundary summaries, and representative-case selection.
- Create: `tests/test_systematic_analysis_plots.py`
  - Cover the plot renderer on small synthetic fixtures.
- Modify: `tests/test_cli.py`
  - Add smoke coverage for the runner and renderer scripts.

## Task 1: Make `UMA` Wireless Randomness Subset-Invariant

**Files:**
- Modify: `src/scheduling_sim/wireless_env.py`
- Test: `tests/test_wireless_env.py`

- [ ] **Step 1: Write the failing subset-invariance regressions**

```python
# tests/test_wireless_env.py
    def test_reset_is_stable_for_same_user_even_when_other_users_are_removed(self) -> None:
        env = StableWirelessEnv(
            WirelessEnvConfigView(
                scenario_type="uma",
                carrier_frequency_ghz=3.5,
                noise_figure_db=7.0,
                interference_margin_db=3.0,
                shadow_std_db=4.0,
                slow_fading_alpha=1.0,
                slot_jitter_std_db=0.0,
                mcs_table=[
                    McsEntryView(snr_db=-5.0, mcs_index=0, bits_per_prb=24),
                    McsEntryView(snr_db=0.0, mcs_index=1, bits_per_prb=48),
                    McsEntryView(snr_db=10.0, mcs_index=2, bits_per_prb=96),
                ],
                seed=17,
            )
        )
        center_a = make_user("center-a", is_edge=False, distance_to_bs_m=120.0)
        center_b = make_user("center-b", is_edge=False, distance_to_bs_m=180.0)

        env.reset([center_a, center_b])
        full_state = center_b.current_radio_state

        center_b_only = make_user("center-b", is_edge=False, distance_to_bs_m=180.0)
        env.reset([center_b_only])

        self.assertEqual(center_b_only.current_radio_state.snr_db, full_state.snr_db)
        self.assertEqual(center_b_only.current_radio_state.bits_per_prb, full_state.bits_per_prb)

    def test_refresh_slot_is_stable_for_same_user_even_when_user_order_changes(self) -> None:
        env = StableWirelessEnv(
            WirelessEnvConfigView(
                scenario_type="uma",
                carrier_frequency_ghz=3.5,
                noise_figure_db=7.0,
                interference_margin_db=3.0,
                shadow_std_db=4.0,
                slow_fading_alpha=0.95,
                slot_jitter_std_db=0.5,
                mcs_table=[
                    McsEntryView(snr_db=-5.0, mcs_index=0, bits_per_prb=24),
                    McsEntryView(snr_db=0.0, mcs_index=1, bits_per_prb=48),
                    McsEntryView(snr_db=10.0, mcs_index=2, bits_per_prb=96),
                ],
                seed=23,
            )
        )
        poor = make_user("poor-0", is_edge=True, distance_to_bs_m=470.0)
        medium = make_user("medium-0", is_edge=False, distance_to_bs_m=210.0)

        env.reset([poor, medium])
        env.refresh_slot([poor, medium], slot_index=4, slot_name="U2")
        full_state = poor.current_radio_state

        poor_again = make_user("poor-0", is_edge=True, distance_to_bs_m=470.0)
        env.reset([poor_again])
        env.refresh_slot([poor_again], slot_index=4, slot_name="U2")

        self.assertEqual(poor_again.current_radio_state.snr_db, full_state.snr_db)
        self.assertEqual(poor_again.current_radio_state.bits_per_prb, full_state.bits_per_prb)
```

- [ ] **Step 2: Run the wireless-env test file and verify the new tests fail**

Run: `PYTHONPATH=src python -m unittest tests.test_wireless_env -v`

Expected: FAIL on the two new tests because `StableWirelessEnv` currently consumes a shared RNG stream, so removing users or changing order changes the same user's shadowing and jitter draws.

- [ ] **Step 3: Refactor `StableWirelessEnv` to seed randomness per `UE` and per slot**

```python
# src/scheduling_sim/wireless_env.py
class StableWirelessEnv:
    def __init__(self, config: WirelessEnvConfigView) -> None:
        self._config = config
        self._rng = random.Random(config.seed)
        self._mcs_table = sorted(config.mcs_table, key=lambda entry: entry.snr_db)
        self._shadow_cache: dict[str, float] = {}
        self._uma_uplink_budget_db = self._build_uplink_budget_db()

    @staticmethod
    def _seed_token(*parts: object) -> str:
        return ":".join(str(part) for part in parts)

    def _shadow_db_for_user(self, ue_id: str) -> float:
        cached = self._shadow_cache.get(ue_id)
        if cached is not None:
            return cached
        rng = random.Random(self._seed_token(self._config.seed, ue_id, "shadow"))
        shadow_db = rng.gauss(0.0, self._config.shadow_std_db)
        self._shadow_cache[ue_id] = shadow_db
        return shadow_db

    def _slot_jitter_db(self, *, ue_id: str, slot_index: int, slot_name: str) -> float:
        rng = random.Random(self._seed_token(self._config.seed, ue_id, slot_index, slot_name, "jitter"))
        return rng.gauss(0.0, self._config.slot_jitter_std_db)

    def reset(self, users: list[UserEquipment]) -> None:
        self._rng = random.Random(self._config.seed)
        self._shadow_cache = {}
        for user in users:
            snr_db = self._resolve_snr_db(user, previous_snr_db=None, slot_index=0, slot_name="RESET")
            mcs_entry = self._resolve_mcs(snr_db)
            user.current_radio_state = CurrentRadioState(
                snr_db=snr_db,
                mcs_index=mcs_entry.mcs_index,
                bits_per_prb=mcs_entry.bits_per_prb,
                per_u_slot_prb_cap=self._resolve_prb_cap(user),
            )

    def refresh_slot(self, users: list[UserEquipment], slot_index: int, slot_name: str) -> None:
        for user in users:
            previous_snr_db = (
                user.radio_profile.base_snr_db
                if user.current_radio_state is None
                else user.current_radio_state.snr_db
            )
            snr_db = self._resolve_snr_db(
                user,
                previous_snr_db=previous_snr_db,
                slot_index=slot_index,
                slot_name=slot_name,
            )
            mcs_entry = self._resolve_mcs(snr_db)
            user.current_radio_state = CurrentRadioState(
                snr_db=snr_db,
                mcs_index=mcs_entry.mcs_index,
                bits_per_prb=mcs_entry.bits_per_prb,
                per_u_slot_prb_cap=self._resolve_prb_cap(user),
            )

    def _resolve_snr_db(
        self,
        user: UserEquipment,
        previous_snr_db: float | None,
        *,
        slot_index: int,
        slot_name: str,
    ) -> float:
        if self._config.scenario_type == "uma":
            return self._resolve_uma_snr_db(
                user,
                previous_snr_db,
                slot_index=slot_index,
                slot_name=slot_name,
            )
        return self._resolve_legacy_snr_db(user, previous_snr_db)

    def _resolve_uma_snr_db(
        self,
        user: UserEquipment,
        previous_snr_db: float | None,
        *,
        slot_index: int,
        slot_name: str,
    ) -> float:
        path_loss_db = self._uma_path_loss_db(user.radio_profile.distance_to_bs_m)
        shadow_db = self._shadow_db_for_user(user.ue_id)
        mean_snr_db = (
            self._uma_uplink_budget_db
            - path_loss_db
            - shadow_db
            - self._config.interference_margin_db
        )
        if previous_snr_db is None:
            return mean_snr_db
        jitter = self._slot_jitter_db(ue_id=user.ue_id, slot_index=slot_index, slot_name=slot_name)
        return (
            self._config.slow_fading_alpha * previous_snr_db
            + (1.0 - self._config.slow_fading_alpha) * mean_snr_db
            + jitter
        )
```

- [ ] **Step 4: Re-run the wireless-env tests and verify they pass**

Run: `PYTHONPATH=src python -m unittest tests.test_wireless_env -v`

Expected: PASS

- [ ] **Step 5: Commit the subset-invariant wireless environment**

```bash
git add src/scheduling_sim/wireless_env.py tests/test_wireless_env.py
git commit -m "fix: make wireless env subset invariant"
```

## Task 2: Add the Realization-Bank and Nested-Slicing Core

**Files:**
- Create: `src/scheduling_sim/systematic_analysis.py`
- Test: `tests/test_systematic_analysis.py`

- [ ] **Step 1: Write failing unit tests for class-controlled bank generation and nested slicing**

```python
# tests/test_systematic_analysis.py
import unittest

from scheduling_sim.config import (
    AppConfig,
    McsEntryConfig,
    RadioClassConfig,
    RadioSection,
    ReportConfig,
    ResourcesConfig,
    SchedulerConfig,
    SimulationConfig,
    TrafficConfig,
    TrafficSection,
    WirelessEnvConfig,
)
from scheduling_sim.systematic_analysis import (
    SceneBankSpec,
    SystematicCase,
    build_realization_bank,
    build_systematic_case_users,
    systematic_cases,
)


class SystematicAnalysisTests(unittest.TestCase):
    def _base_config(self) -> AppConfig:
        return AppConfig(
            simulation=SimulationConfig(cycles=2000, slot_duration_ms=1, tdd_pattern="DSUUU", random_seed=7),
            resources=ResourcesConfig(total_prb_per_u_slot=273, max_ue_per_slot=16),
            traffic=TrafficSection(
                center=TrafficConfig(count=48, packet_bits=16_000, pdb_ms=None, period_slots=10, gbr_bps=0.0),
                edge=TrafficConfig(count=16, packet_bits=400_000, pdb_ms=100),
            ),
            radio=RadioSection(
                environment=WirelessEnvConfig(
                    scenario_type="uma",
                    cell_radius_m=500.0,
                    carrier_frequency_ghz=3.5,
                    per_prb_tx_power_dbm=5.0,
                    noise_figure_db=7.0,
                    interference_margin_db=3.0,
                    shadow_std_db=4.0,
                    slow_fading_alpha=0.95,
                    slot_jitter_std_db=0.5,
                    mcs_table=[
                        McsEntryConfig(snr_db=-5.0, mcs_index=0, bits_per_prb=24),
                        McsEntryConfig(snr_db=0.0, mcs_index=1, bits_per_prb=48),
                        McsEntryConfig(snr_db=10.0, mcs_index=2, bits_per_prb=96),
                    ],
                ),
                center=RadioClassConfig(base_snr_db=12.0, snr_min_db=0.0, snr_max_db=20.0),
                edge=RadioClassConfig(
                    base_snr_db=-2.0,
                    snr_min_db=-8.0,
                    snr_max_db=4.0,
                    edge_per_u_slot_prb_cap=273,
                ),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="tail_append"),
            report=ReportConfig(output_dir="outputs/test-systematic", keep_slot_trace=False),
        )

    def _scene_bank_spec(self) -> SceneBankSpec:
        return SceneBankSpec(
            medium_count=24,
            good_count=24,
            poor_count=16,
            medium_distance_range_m=(170.0, 230.0),
            good_distance_range_m=(80.0, 140.0),
            poor_distance_range_m=(390.0, 470.0),
        )

    def _simple_case(self) -> SystematicCase:
        return SystematicCase(background_user_count=24, pdb_user_count=4, pdb_ms=100, pdb_packet_kb=50)

    def test_build_realization_bank_creates_expected_class_pool_sizes(self) -> None:
        bank = build_realization_bank(self._base_config(), scene_bank_spec=self._scene_bank_spec(), bank_seed=7)
        self.assertEqual(len(bank.medium_users), 24)
        self.assertEqual(len(bank.good_users), 24)
        self.assertEqual(len(bank.poor_users), 16)

    def test_build_realization_bank_validates_sinr_class_ranges(self) -> None:
        bank = build_realization_bank(self._base_config(), scene_bank_spec=self._scene_bank_spec(), bank_seed=7)
        for template in bank.medium_users:
            self.assertGreaterEqual(template.initial_sinr_db, 0.0)
            self.assertLessEqual(template.initial_sinr_db, 10.0)
        for template in bank.good_users:
            self.assertGreaterEqual(template.initial_sinr_db, 10.0)
            self.assertLessEqual(template.initial_sinr_db, 20.0)
        for template in bank.poor_users:
            self.assertGreaterEqual(template.initial_sinr_db, -5.0)
            self.assertLessEqual(template.initial_sinr_db, 0.0)

    def test_build_systematic_case_users_uses_nested_slices(self) -> None:
        bank = build_realization_bank(self._base_config(), scene_bank_spec=self._scene_bank_spec(), bank_seed=7)
        users_small = build_systematic_case_users(
            self._base_config(),
            bank,
            background_user_count=24,
            pdb_user_count=4,
            pdb_ms=100,
            pdb_packet_bits=50 * 1000 * 8,
            background_packet_bits=2 * 1000 * 8,
        )
        users_large = build_systematic_case_users(
            self._base_config(),
            bank,
            background_user_count=36,
            pdb_user_count=10,
            pdb_ms=100,
            pdb_packet_bits=50 * 1000 * 8,
            background_packet_bits=2 * 1000 * 8,
        )
        small_ids = {user.ue_id for user in users_small}
        large_ids = {user.ue_id for user in users_large}
        self.assertTrue(small_ids.issubset(large_ids))

    def test_systematic_cases_emits_the_expected_81_point_matrix(self) -> None:
        cases = systematic_cases(
            background_user_counts=[24, 36, 48],
            pdb_user_counts=[4, 10, 16],
            pdb_ms_values=[100, 300, 500],
            pdb_packet_kb_values=[50, 150, 300],
        )
        self.assertEqual(len(cases), 81)
```

- [ ] **Step 2: Run the new test file and verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis -v`

Expected: FAIL because `scheduling_sim.systematic_analysis` does not exist yet.

- [ ] **Step 3: Create the core dataclasses, bank builder, class-range validation, and nested slicer**

```python
# src/scheduling_sim/systematic_analysis.py
from __future__ import annotations

import math
import random
from dataclasses import dataclass

from scheduling_sim.models import CurrentRadioState, LogicalChannel, RadioProfile, TrafficProfile, UserEquipment
from scheduling_sim.wireless_env import McsEntryView, StableWirelessEnv, WirelessEnvConfigView

CLASS_SINR_BOUNDS_DB = {
    "poor": (-5.0, 0.0),
    "medium": (0.0, 10.0),
    "good": (10.0, 20.0),
}


@dataclass(frozen=True)
class SceneBankSpec:
    medium_count: int
    good_count: int
    poor_count: int
    medium_distance_range_m: tuple[float, float]
    good_distance_range_m: tuple[float, float]
    poor_distance_range_m: tuple[float, float]


@dataclass(frozen=True)
class BankUserTemplate:
    ue_id: str
    scene_class: str
    distance_to_bs_m: float
    initial_sinr_db: float
    initial_mcs_index: int
    initial_bits_per_prb: int


@dataclass(frozen=True)
class RealizationBank:
    bank_seed: int
    medium_users: list[BankUserTemplate]
    good_users: list[BankUserTemplate]
    poor_users: list[BankUserTemplate]


@dataclass(frozen=True)
class SystematicCase:
    background_user_count: int
    pdb_user_count: int
    pdb_ms: int
    pdb_packet_kb: int


def systematic_cases(*, background_user_counts, pdb_user_counts, pdb_ms_values, pdb_packet_kb_values):
    return [
        SystematicCase(
            background_user_count=int(background_user_count),
            pdb_user_count=int(pdb_user_count),
            pdb_ms=int(pdb_ms),
            pdb_packet_kb=int(pdb_packet_kb),
        )
        for background_user_count in background_user_counts
        for pdb_user_count in pdb_user_counts
        for pdb_ms in pdb_ms_values
        for pdb_packet_kb in pdb_packet_kb_values
    ]


def _env_view_from_config(base_config, *, seed: int) -> WirelessEnvConfigView:
    env = base_config.radio.environment
    return WirelessEnvConfigView(
        alpha=float(env.alpha),
        jitter_std_db=float(env.jitter_std_db),
        scenario_type=str(env.scenario_type),
        cell_radius_m=float(env.cell_radius_m),
        carrier_frequency_ghz=float(env.carrier_frequency_ghz),
        per_prb_tx_power_dbm=float(env.per_prb_tx_power_dbm),
        noise_figure_db=float(env.noise_figure_db),
        interference_margin_db=float(env.interference_margin_db),
        shadow_std_db=float(env.shadow_std_db),
        slow_fading_alpha=float(env.slow_fading_alpha),
        slot_jitter_std_db=float(env.slot_jitter_std_db),
        mcs_table=[
            McsEntryView(
                snr_db=float(entry.snr_db),
                mcs_index=int(entry.mcs_index),
                bits_per_prb=int(entry.bits_per_prb),
            )
            for entry in env.mcs_table
        ],
        seed=int(seed),
    )


def _sample_distance(*, bank_seed: int, scene_class: str, index: int, distance_range_m: tuple[float, float]) -> float:
    low, high = distance_range_m
    rng = random.Random(f"{bank_seed}:{scene_class}:{index}:distance")
    return rng.uniform(float(low), float(high))


def _bank_user(scene_class: str, index: int, distance_to_bs_m: float, base_config) -> UserEquipment:
    is_edge_user = scene_class == "poor"
    radio_class = base_config.radio.edge if is_edge_user else base_config.radio.center
    radio_profile = RadioProfile(
        user_class="edge" if is_edge_user else "center",
        base_snr_db=float(radio_class.base_snr_db),
        snr_min_db=float(radio_class.snr_min_db),
        snr_max_db=float(radio_class.snr_max_db),
        distance_to_bs_m=float(distance_to_bs_m),
        edge_per_u_slot_prb_cap=radio_class.edge_per_u_slot_prb_cap,
        bits_per_prb=int(radio_class.bits_per_prb or 0),
        per_u_slot_prb_cap=int(radio_class.per_u_slot_prb_cap),
    )
    return UserEquipment(
        ue_id=f"{scene_class}-{index}",
        lc=LogicalChannel(lc_id=f"{scene_class}-{index}-lc"),
        is_edge_user=is_edge_user,
        radio_profile=radio_profile,
        average_throughput=1.0,
        traffic_profile=TrafficProfile(
            packet_bits=base_config.traffic.edge.packet_bits if is_edge_user else base_config.traffic.center.packet_bits,
            pdb_ms=base_config.traffic.edge.pdb_ms if is_edge_user else base_config.traffic.center.pdb_ms,
            period_slots=base_config.traffic.center.period_slots if not is_edge_user else None,
            burst_cycle_interval=base_config.traffic.edge.burst_cycle_interval if is_edge_user else None,
            gbr_bps=base_config.traffic.center.gbr_bps if not is_edge_user else 0.0,
        ),
        current_radio_state=CurrentRadioState(snr_db=0.0, mcs_index=0, bits_per_prb=0, per_u_slot_prb_cap=None),
    )


def _template_from_user(user: UserEquipment, scene_class: str) -> BankUserTemplate:
    state = user.current_radio_state
    if state is None:
        raise ValueError(f"user {user.ue_id!r} is missing current_radio_state")
    return BankUserTemplate(
        ue_id=user.ue_id,
        scene_class=scene_class,
        distance_to_bs_m=float(user.radio_profile.distance_to_bs_m),
        initial_sinr_db=float(state.snr_db),
        initial_mcs_index=int(state.mcs_index),
        initial_bits_per_prb=int(state.bits_per_prb),
    )


def _validate_class_range(template: BankUserTemplate) -> None:
    low, high = CLASS_SINR_BOUNDS_DB[template.scene_class]
    snr_db = float(template.initial_sinr_db)
    if snr_db < low or snr_db > high:
        raise ValueError(
            f"{template.ue_id} classified as {template.scene_class} but SINR {snr_db:.2f} dB is outside [{low}, {high}]"
        )


def build_realization_bank(base_config, *, scene_bank_spec: SceneBankSpec, bank_seed: int) -> RealizationBank:
    env = StableWirelessEnv(_env_view_from_config(base_config, seed=bank_seed))
    medium_users = [
        _bank_user(
            "medium",
            index,
            _sample_distance(
                bank_seed=bank_seed,
                scene_class="medium",
                index=index,
                distance_range_m=scene_bank_spec.medium_distance_range_m,
            ),
            base_config,
        )
        for index in range(scene_bank_spec.medium_count)
    ]
    good_users = [
        _bank_user(
            "good",
            index,
            _sample_distance(
                bank_seed=bank_seed,
                scene_class="good",
                index=index,
                distance_range_m=scene_bank_spec.good_distance_range_m,
            ),
            base_config,
        )
        for index in range(scene_bank_spec.good_count)
    ]
    poor_users = [
        _bank_user(
            "poor",
            index,
            _sample_distance(
                bank_seed=bank_seed,
                scene_class="poor",
                index=index,
                distance_range_m=scene_bank_spec.poor_distance_range_m,
            ),
            base_config,
        )
        for index in range(scene_bank_spec.poor_count)
    ]
    all_users = medium_users + good_users + poor_users
    env.reset(all_users)
    bank = RealizationBank(
        bank_seed=int(bank_seed),
        medium_users=[_template_from_user(user, "medium") for user in medium_users],
        good_users=[_template_from_user(user, "good") for user in good_users],
        poor_users=[_template_from_user(user, "poor") for user in poor_users],
    )
    for template in bank.medium_users + bank.good_users + bank.poor_users:
        _validate_class_range(template)
    return bank


def _background_templates(bank: RealizationBank, background_user_count: int) -> list[BankUserTemplate]:
    medium_take = int(math.ceil(background_user_count / 2.0))
    good_take = int(background_user_count) - medium_take
    return list(bank.medium_users[:medium_take]) + list(bank.good_users[:good_take])


def _user_from_template(template: BankUserTemplate, *, pdb_packet_bits: int, pdb_ms: int, background_packet_bits: int, base_config) -> UserEquipment:
    is_pdb = template.scene_class == "poor"
    radio_class = base_config.radio.edge if is_pdb else base_config.radio.center
    traffic_profile = TrafficProfile(
        packet_bits=int(pdb_packet_bits) if is_pdb else int(background_packet_bits),
        pdb_ms=int(pdb_ms) if is_pdb else None,
        period_slots=None if is_pdb else base_config.traffic.center.period_slots,
        burst_cycle_interval=base_config.traffic.edge.burst_cycle_interval if is_pdb else None,
        gbr_bps=0.0 if is_pdb else base_config.traffic.center.gbr_bps,
    )
    if is_pdb:
        object.__setattr__(traffic_profile, "arrival_mode", "periodic_by_pdb")
        object.__setattr__(traffic_profile, "initial_phase_mode", "uniform_0_to_pdb")
    radio_profile = RadioProfile(
        user_class="edge" if is_pdb else "center",
        base_snr_db=float(radio_class.base_snr_db),
        snr_min_db=float(radio_class.snr_min_db),
        snr_max_db=float(radio_class.snr_max_db),
        distance_to_bs_m=float(template.distance_to_bs_m),
        edge_per_u_slot_prb_cap=radio_class.edge_per_u_slot_prb_cap,
        bits_per_prb=int(template.initial_bits_per_prb),
        per_u_slot_prb_cap=int(radio_class.per_u_slot_prb_cap),
    )
    return UserEquipment(
        ue_id=template.ue_id,
        lc=LogicalChannel(lc_id=f"{template.ue_id}-lc"),
        is_edge_user=is_pdb,
        radio_profile=radio_profile,
        average_throughput=1.0,
        traffic_profile=traffic_profile,
        current_radio_state=CurrentRadioState(
            snr_db=float(template.initial_sinr_db),
            mcs_index=int(template.initial_mcs_index),
            bits_per_prb=int(template.initial_bits_per_prb),
            per_u_slot_prb_cap=radio_class.edge_per_u_slot_prb_cap if is_pdb else None,
        ),
    )


def build_systematic_case_users(
    base_config,
    bank: RealizationBank,
    *,
    background_user_count: int,
    pdb_user_count: int,
    pdb_ms: int,
    pdb_packet_bits: int,
    background_packet_bits: int,
) -> list[UserEquipment]:
    selected = _background_templates(bank, int(background_user_count)) + list(bank.poor_users[: int(pdb_user_count)])
    return [
        _user_from_template(
            template,
            pdb_packet_bits=int(pdb_packet_bits),
            pdb_ms=int(pdb_ms),
            background_packet_bits=int(background_packet_bits),
            base_config=base_config,
        )
        for template in selected
    ]
```

- [ ] **Step 4: Run the realization-bank tests and verify they pass**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis -v`

Expected: PASS

- [ ] **Step 5: Commit the realization-bank core**

```bash
git add src/scheduling_sim/systematic_analysis.py tests/test_systematic_analysis.py
git commit -m "feat: add systematic analysis realization bank"
```

## Task 3: Add Per-Run Rows, Paired Aggregation, Region Summaries, and Boundary Summaries

**Files:**
- Modify: `src/scheduling_sim/systematic_analysis.py`
- Test: `tests/test_systematic_analysis.py`

- [ ] **Step 1: Extend the test file with paired-summary, region, and boundary coverage**

```python
# tests/test_systematic_analysis.py
from scheduling_sim.systematic_analysis import (
    aggregate_scene_rows,
    capacity_summary_rows,
    paired_metric_row,
    partition_region,
    per_run_metric_row,
    select_typical_case_rows,
    summarize_regions,
)

    def test_per_run_metric_row_keeps_traceability_fields(self) -> None:
        row = per_run_metric_row(
            scenario_id="bg24_pdb4_d100_k50_seed00",
            seed=0,
            policy="tail_append",
            case=self._simple_case(),
            summary={
                "edge_pdb_satisfaction_rate": 0.6,
                "center_agg_rate_bps": 1000.0,
                "center_avg_rate_bps": 50.0,
                "prb_utilization": 0.5,
                "center_prb_share": 0.7,
                "edge_prb_share": 0.3,
                "pdb_violation_rate": 0.4,
                "target_edge_completion_delay_ms": 120.0,
                "target_edge_queue_wait_ms": 90.0,
                "target_edge_service_time_ms": 30.0,
                "edge_backlog_bits": 4000.0,
                "pdb_arrivals_in_window": 8.0,
            },
        )
        self.assertEqual(row["scenario_id"], "bg24_pdb4_d100_k50_seed00")
        self.assertEqual(row["policy"], "tail_append")
        self.assertEqual(row["pdb_arrivals_in_window"], 8.0)

    def test_paired_metric_row_computes_gain_and_retention(self) -> None:
        row = paired_metric_row(
            case=self._simple_case(),
            seed=3,
            baseline_summary={
                "edge_pdb_satisfaction_rate": 0.6,
                "center_agg_rate_bps": 1000.0,
                "prb_utilization": 0.50,
                "center_prb_share": 0.70,
                "edge_prb_share": 0.30,
            },
            proposed_summary={
                "edge_pdb_satisfaction_rate": 0.8,
                "center_agg_rate_bps": 900.0,
                "prb_utilization": 0.55,
                "center_prb_share": 0.66,
                "edge_prb_share": 0.34,
            },
        )
        self.assertEqual(row["delta_pdb_satisfaction_rate"], 0.2)
        self.assertEqual(row["center_throughput_retention"], 0.9)

    def test_aggregate_scene_rows_computes_mean_std_and_ci(self) -> None:
        rows = aggregate_scene_rows(
            [
                {
                    "background_user_count": 24,
                    "pdb_user_count": 4,
                    "pdb_ms": 100,
                    "pdb_packet_kb": 50,
                    "baseline_edge_pdb_satisfaction_rate": 0.60,
                    "proposed_edge_pdb_satisfaction_rate": 0.80,
                    "delta_pdb_satisfaction_rate": 0.20,
                    "center_throughput_retention": 0.90,
                    "delta_prb_utilization": 0.05,
                    "delta_center_prb_share": -0.04,
                    "delta_edge_prb_share": 0.04,
                },
                {
                    "background_user_count": 24,
                    "pdb_user_count": 4,
                    "pdb_ms": 100,
                    "pdb_packet_kb": 50,
                    "baseline_edge_pdb_satisfaction_rate": 0.50,
                    "proposed_edge_pdb_satisfaction_rate": 0.70,
                    "delta_pdb_satisfaction_rate": 0.20,
                    "center_throughput_retention": 0.80,
                    "delta_prb_utilization": 0.02,
                    "delta_center_prb_share": -0.03,
                    "delta_edge_prb_share": 0.03,
                },
            ]
        )
        self.assertEqual(rows[0]["mean_delta_pdb_satisfaction_rate"], 0.20)
        self.assertEqual(rows[0]["std_delta_pdb_satisfaction_rate"], 0.0)
        self.assertGreaterEqual(rows[0]["ci95_center_throughput_retention"], 0.0)

    def test_partition_region_uses_baseline_satisfaction_thresholds(self) -> None:
        self.assertEqual(partition_region(0.97), "feasible")
        self.assertEqual(partition_region(0.70), "critical")
        self.assertEqual(partition_region(0.20), "overloaded")

    def test_summarize_regions_reports_scene_share_and_win_rate(self) -> None:
        rows = summarize_regions(
            [
                {
                    "baseline_edge_pdb_satisfaction_rate": 0.97,
                    "mean_delta_pdb_satisfaction_rate": 0.01,
                    "mean_center_throughput_retention": 0.99,
                    "mean_delta_prb_utilization": 0.00,
                    "mean_delta_center_prb_share": -0.01,
                    "mean_delta_edge_prb_share": 0.01,
                },
                {
                    "baseline_edge_pdb_satisfaction_rate": 0.70,
                    "mean_delta_pdb_satisfaction_rate": 0.10,
                    "mean_center_throughput_retention": 0.95,
                    "mean_delta_prb_utilization": 0.03,
                    "mean_delta_center_prb_share": -0.02,
                    "mean_delta_edge_prb_share": 0.02,
                },
            ]
        )
        by_region = {row["region"]: row for row in rows}
        self.assertEqual(by_region["feasible"]["scene_point_count"], 1)
        self.assertEqual(by_region["critical"]["proposed_win_rate"], 1.0)

    def test_capacity_summary_rows_returns_both_boundary_views(self) -> None:
        rows = capacity_summary_rows(
            [
                {
                    "background_user_count": 24,
                    "pdb_user_count": 4,
                    "pdb_ms": 100,
                    "pdb_packet_kb": 50,
                    "baseline_edge_pdb_satisfaction_rate": 0.98,
                    "proposed_edge_pdb_satisfaction_rate": 0.98,
                },
                {
                    "background_user_count": 24,
                    "pdb_user_count": 10,
                    "pdb_ms": 100,
                    "pdb_packet_kb": 50,
                    "baseline_edge_pdb_satisfaction_rate": 0.80,
                    "proposed_edge_pdb_satisfaction_rate": 0.96,
                },
                {
                    "background_user_count": 36,
                    "pdb_user_count": 4,
                    "pdb_ms": 100,
                    "pdb_packet_kb": 50,
                    "baseline_edge_pdb_satisfaction_rate": 0.70,
                    "proposed_edge_pdb_satisfaction_rate": 0.95,
                },
            ],
            threshold=0.95,
        )
        dimensions = {row["dimension"] for row in rows}
        self.assertEqual(dimensions, {"fixed_background_user_count", "fixed_pdb_user_count"})

    def test_select_typical_case_rows_labels_key_scene_points(self) -> None:
        rows = select_typical_case_rows(
            [
                {
                    "background_user_count": 24,
                    "pdb_user_count": 4,
                    "pdb_ms": 100,
                    "pdb_packet_kb": 50,
                    "baseline_edge_pdb_satisfaction_rate": 0.98,
                    "proposed_edge_pdb_satisfaction_rate": 0.99,
                    "mean_delta_pdb_satisfaction_rate": 0.01,
                    "mean_center_throughput_retention": 0.99,
                },
                {
                    "background_user_count": 36,
                    "pdb_user_count": 10,
                    "pdb_ms": 100,
                    "pdb_packet_kb": 50,
                    "baseline_edge_pdb_satisfaction_rate": 0.70,
                    "proposed_edge_pdb_satisfaction_rate": 0.90,
                    "mean_delta_pdb_satisfaction_rate": 0.20,
                    "mean_center_throughput_retention": 0.93,
                },
                {
                    "background_user_count": 48,
                    "pdb_user_count": 16,
                    "pdb_ms": 500,
                    "pdb_packet_kb": 300,
                    "baseline_edge_pdb_satisfaction_rate": 0.20,
                    "proposed_edge_pdb_satisfaction_rate": 0.35,
                    "mean_delta_pdb_satisfaction_rate": 0.15,
                    "mean_center_throughput_retention": 0.91,
                },
            ]
        )
        labels = {row["case_label"] for row in rows}
        self.assertIn("easy", labels)
        self.assertIn("critical", labels)
        self.assertIn("overloaded", labels)
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis -v`

Expected: FAIL because these summary helpers are not implemented yet.

- [ ] **Step 3: Implement per-run row builders, paired aggregation, region summaries, and boundary summaries**

```python
# src/scheduling_sim/systematic_analysis.py
def per_run_metric_row(*, scenario_id: str, seed: int, policy: str, case: SystematicCase, summary: dict[str, float]) -> dict[str, float | int | str]:
    return {
        "seed": int(seed),
        "scenario_id": scenario_id,
        "policy": str(policy),
        "background_user_count": int(case.background_user_count),
        "pdb_user_count": int(case.pdb_user_count),
        "pdb_ms": int(case.pdb_ms),
        "pdb_packet_kb": int(case.pdb_packet_kb),
        "edge_pdb_satisfaction_rate": float(summary["edge_pdb_satisfaction_rate"]),
        "center_agg_rate_bps": float(summary["center_agg_rate_bps"]),
        "center_avg_rate_bps": float(summary["center_avg_rate_bps"]),
        "prb_utilization": float(summary["prb_utilization"]),
        "center_prb_share": float(summary["center_prb_share"]),
        "edge_prb_share": float(summary["edge_prb_share"]),
        "pdb_arrivals_in_window": float(summary.get("pdb_arrivals_in_window", 0.0)),
        "pdb_violation_rate": float(summary["pdb_violation_rate"]),
        "target_edge_completion_delay_ms": float(summary["target_edge_completion_delay_ms"]),
        "target_edge_queue_wait_ms": float(summary["target_edge_queue_wait_ms"]),
        "target_edge_service_time_ms": float(summary["target_edge_service_time_ms"]),
        "edge_backlog_bits": float(summary["edge_backlog_bits"]),
    }


def paired_metric_row(*, case: SystematicCase, seed: int, baseline_summary: dict[str, float], proposed_summary: dict[str, float]) -> dict[str, float | int]:
    baseline_center_rate = float(baseline_summary["center_agg_rate_bps"])
    proposed_center_rate = float(proposed_summary["center_agg_rate_bps"])
    return {
        "seed": int(seed),
        "background_user_count": int(case.background_user_count),
        "pdb_user_count": int(case.pdb_user_count),
        "pdb_ms": int(case.pdb_ms),
        "pdb_packet_kb": int(case.pdb_packet_kb),
        "baseline_edge_pdb_satisfaction_rate": float(baseline_summary["edge_pdb_satisfaction_rate"]),
        "proposed_edge_pdb_satisfaction_rate": float(proposed_summary["edge_pdb_satisfaction_rate"]),
        "delta_pdb_satisfaction_rate": float(proposed_summary["edge_pdb_satisfaction_rate"]) - float(baseline_summary["edge_pdb_satisfaction_rate"]),
        "center_throughput_retention": 1.0 if baseline_center_rate == 0.0 else proposed_center_rate / baseline_center_rate,
        "delta_prb_utilization": float(proposed_summary["prb_utilization"]) - float(baseline_summary["prb_utilization"]),
        "delta_center_prb_share": float(proposed_summary["center_prb_share"]) - float(baseline_summary["center_prb_share"]),
        "delta_edge_prb_share": float(proposed_summary["edge_prb_share"]) - float(baseline_summary["edge_prb_share"]),
    }


def _mean(values: list[float]) -> float:
    return sum(values) / float(len(values)) if values else 0.0


def _stdev(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    mean_value = _mean(values)
    variance = sum((value - mean_value) ** 2 for value in values) / float(len(values) - 1)
    return math.sqrt(variance)


def _ci95(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    return 1.96 * _stdev(values) / math.sqrt(float(len(values)))


def aggregate_scene_rows(paired_rows: list[dict[str, float | int]]) -> list[dict[str, float | int]]:
    grouped: dict[tuple[int, int, int, int], list[dict[str, float | int]]] = {}
    for row in paired_rows:
        key = (
            int(row["background_user_count"]),
            int(row["pdb_user_count"]),
            int(row["pdb_ms"]),
            int(row["pdb_packet_kb"]),
        )
        grouped.setdefault(key, []).append(row)
    aggregated: list[dict[str, float | int]] = []
    for key, group in sorted(grouped.items()):
        delta_values = [float(row["delta_pdb_satisfaction_rate"]) for row in group]
        retention_values = [float(row["center_throughput_retention"]) for row in group]
        delta_prb_values = [float(row["delta_prb_utilization"]) for row in group]
        delta_center_share_values = [float(row["delta_center_prb_share"]) for row in group]
        delta_edge_share_values = [float(row["delta_edge_prb_share"]) for row in group]
        baseline_values = [float(row["baseline_edge_pdb_satisfaction_rate"]) for row in group]
        proposed_values = [float(row["proposed_edge_pdb_satisfaction_rate"]) for row in group]
        aggregated.append(
            {
                "background_user_count": key[0],
                "pdb_user_count": key[1],
                "pdb_ms": key[2],
                "pdb_packet_kb": key[3],
                "repeat_count": len(group),
                "baseline_edge_pdb_satisfaction_rate": _mean(baseline_values),
                "proposed_edge_pdb_satisfaction_rate": _mean(proposed_values),
                "mean_delta_pdb_satisfaction_rate": _mean(delta_values),
                "std_delta_pdb_satisfaction_rate": _stdev(delta_values),
                "ci95_delta_pdb_satisfaction_rate": _ci95(delta_values),
                "mean_center_throughput_retention": _mean(retention_values),
                "std_center_throughput_retention": _stdev(retention_values),
                "ci95_center_throughput_retention": _ci95(retention_values),
                "mean_delta_prb_utilization": _mean(delta_prb_values),
                "mean_delta_center_prb_share": _mean(delta_center_share_values),
                "mean_delta_edge_prb_share": _mean(delta_edge_share_values),
            }
        )
    return aggregated


def partition_region(baseline_satisfaction: float) -> str:
    if baseline_satisfaction >= 0.95:
        return "feasible"
    if baseline_satisfaction >= 0.50:
        return "critical"
    return "overloaded"


def summarize_regions(scene_rows: list[dict[str, float | int]]) -> list[dict[str, float | int | str]]:
    total_scene_points = len(scene_rows)
    grouped: dict[str, list[dict[str, float | int]]] = {}
    for row in scene_rows:
        grouped.setdefault(partition_region(float(row["baseline_edge_pdb_satisfaction_rate"])), []).append(row)
    summaries: list[dict[str, float | int | str]] = []
    for region, group in sorted(grouped.items()):
        summaries.append(
            {
                "region": region,
                "scene_point_count": len(group),
                "scene_point_share": 0.0 if total_scene_points == 0 else len(group) / float(total_scene_points),
                "proposed_win_rate": sum(1 for row in group if float(row["mean_delta_pdb_satisfaction_rate"]) > 0.0) / float(len(group)),
                "mean_delta_pdb_satisfaction_rate": _mean([float(row["mean_delta_pdb_satisfaction_rate"]) for row in group]),
                "mean_center_throughput_retention": _mean([float(row["mean_center_throughput_retention"]) for row in group]),
                "mean_delta_prb_utilization": _mean([float(row["mean_delta_prb_utilization"]) for row in group]),
                "mean_delta_center_prb_share": _mean([float(row["mean_delta_center_prb_share"]) for row in group]),
                "mean_delta_edge_prb_share": _mean([float(row["mean_delta_edge_prb_share"]) for row in group]),
            }
        )
    return summaries


def select_typical_case_rows(scene_rows: list[dict[str, float | int]]) -> list[dict[str, float | int | str]]:
    if not scene_rows:
        return []

    selections: list[tuple[str, dict[str, float | int]]] = []
    easy_rows = [
        row for row in scene_rows
        if float(row["baseline_edge_pdb_satisfaction_rate"]) >= 0.95
        and float(row["proposed_edge_pdb_satisfaction_rate"]) >= 0.95
    ]
    critical_rows = [
        row for row in scene_rows
        if 0.50 <= float(row["baseline_edge_pdb_satisfaction_rate"]) < 0.95
    ]
    overloaded_rows = [
        row for row in scene_rows
        if float(row["baseline_edge_pdb_satisfaction_rate"]) < 0.50
    ]
    positive_gain_rows = [
        row for row in scene_rows
        if float(row["mean_delta_pdb_satisfaction_rate"]) > 0.0
    ]

    if easy_rows:
        selections.append(("easy", max(easy_rows, key=lambda row: float(row["baseline_edge_pdb_satisfaction_rate"]))))
    if critical_rows:
        selections.append(("critical", max(critical_rows, key=lambda row: float(row["mean_delta_pdb_satisfaction_rate"]))))
    if overloaded_rows:
        selections.append(("overloaded", max(overloaded_rows, key=lambda row: float(row["mean_delta_pdb_satisfaction_rate"]))))
    if positive_gain_rows:
        selections.append(("high_cost", min(positive_gain_rows, key=lambda row: float(row["mean_center_throughput_retention"]))))

    deduped: list[dict[str, float | int | str]] = []
    seen_keys: set[tuple[int, int, int, int]] = set()
    for label, row in selections:
        key = (
            int(row["background_user_count"]),
            int(row["pdb_user_count"]),
            int(row["pdb_ms"]),
            int(row["pdb_packet_kb"]),
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(
            {
                "case_label": label,
                "background_user_count": int(row["background_user_count"]),
                "pdb_user_count": int(row["pdb_user_count"]),
                "pdb_ms": int(row["pdb_ms"]),
                "pdb_packet_kb": int(row["pdb_packet_kb"]),
                "baseline_edge_pdb_satisfaction_rate": float(row["baseline_edge_pdb_satisfaction_rate"]),
                "proposed_edge_pdb_satisfaction_rate": float(row["proposed_edge_pdb_satisfaction_rate"]),
                "mean_delta_pdb_satisfaction_rate": float(row["mean_delta_pdb_satisfaction_rate"]),
                "mean_center_throughput_retention": float(row["mean_center_throughput_retention"]),
            }
        )
    return deduped


def capacity_summary_rows(scene_rows: list[dict[str, float | int]], *, threshold: float) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    by_background: dict[tuple[int, int, int], list[dict[str, float | int]]] = {}
    by_pdb_users: dict[tuple[int, int, int], list[dict[str, float | int]]] = {}
    for row in scene_rows:
        by_background.setdefault(
            (int(row["background_user_count"]), int(row["pdb_ms"]), int(row["pdb_packet_kb"])),
            [],
        ).append(row)
        by_pdb_users.setdefault(
            (int(row["pdb_user_count"]), int(row["pdb_ms"]), int(row["pdb_packet_kb"])),
            [],
        ).append(row)

    for (background_user_count, pdb_ms, pdb_packet_kb), group in sorted(by_background.items()):
        baseline_max = max(
            [int(row["pdb_user_count"]) for row in group if float(row["baseline_edge_pdb_satisfaction_rate"]) >= threshold],
            default=0,
        )
        proposed_max = max(
            [int(row["pdb_user_count"]) for row in group if float(row["proposed_edge_pdb_satisfaction_rate"]) >= threshold],
            default=0,
        )
        rows.append(
            {
                "dimension": "fixed_background_user_count",
                "background_user_count": background_user_count,
                "pdb_user_count": "",
                "pdb_ms": pdb_ms,
                "pdb_packet_kb": pdb_packet_kb,
                "threshold": float(threshold),
                "baseline_max_pdb_user_count": baseline_max,
                "proposed_max_pdb_user_count": proposed_max,
                "capacity_gain_pdb_users": proposed_max - baseline_max,
            }
        )

    for (pdb_user_count, pdb_ms, pdb_packet_kb), group in sorted(by_pdb_users.items()):
        baseline_max = max(
            [int(row["background_user_count"]) for row in group if float(row["baseline_edge_pdb_satisfaction_rate"]) >= threshold],
            default=0,
        )
        proposed_max = max(
            [int(row["background_user_count"]) for row in group if float(row["proposed_edge_pdb_satisfaction_rate"]) >= threshold],
            default=0,
        )
        rows.append(
            {
                "dimension": "fixed_pdb_user_count",
                "background_user_count": "",
                "pdb_user_count": pdb_user_count,
                "pdb_ms": pdb_ms,
                "pdb_packet_kb": pdb_packet_kb,
                "threshold": float(threshold),
                "baseline_max_background_user_count": baseline_max,
                "proposed_max_background_user_count": proposed_max,
                "capacity_gain_background_users": proposed_max - baseline_max,
            }
        )

    return rows
```

- [ ] **Step 4: Re-run the systematic-analysis test file and verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis -v`

Expected: PASS

- [ ] **Step 5: Commit the summary helpers**

```bash
git add src/scheduling_sim/systematic_analysis.py tests/test_systematic_analysis.py
git commit -m "feat: add systematic analysis summaries"
```

## Task 4: Add the Sweep Runner and Checked-In Reference Config

**Files:**
- Create: `scripts/run_systematic_simulation_analysis.py`
- Create: `configs/systematic_simulation_analysis_option1.json`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing runner smoke test**

```python
# tests/test_cli.py
    def test_systematic_simulation_analysis_runner_writes_manifest_and_tables(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "systematic_small.json"
            output_dir = Path(tmp) / "systematic-output"
            config_path.write_text(
                json.dumps(
                    {
                        "simulation": {
                            "cycles": 2400,
                            "slot_duration_ms": 1,
                            "tdd_pattern": "DSUUU",
                            "random_seed": 7,
                            "analysis_window_ms": 10000
                        },
                        "resources": {"total_prb_per_u_slot": 273, "max_ue_per_slot": 16},
                        "traffic": {
                            "center": {"count": 48, "period_slots": 10, "packet_bits": 16000, "pdb_ms": None, "gbr_bps": 0.0},
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
                                "mcs_table": [
                                    {"sinr_db": -5.0, "mcs_index": 0, "bits_per_prb": 24},
                                    {"sinr_db": 0.0, "mcs_index": 1, "bits_per_prb": 48},
                                    {"sinr_db": 10.0, "mcs_index": 2, "bits_per_prb": 96}
                                ]
                            },
                            "center": {"base_snr_db": 12.0, "snr_min_db": 0.0, "snr_max_db": 20.0},
                            "edge": {"base_snr_db": -2.0, "snr_min_db": -8.0, "snr_max_db": 4.0, "edge_per_u_slot_prb_cap": 273}
                        },
                        "scheduler": {"ranking": "epf", "reinsert_policy": "tail_append"},
                        "report": {"output_dir": str(output_dir), "keep_slot_trace": False},
                        "systematic_analysis": {
                            "background_user_count_values": [24],
                            "pdb_user_count_values": [4],
                            "pdb_ms_values": [100],
                            "pdb_packet_kb_values": [50],
                            "repeat_count": 1,
                            "random_seed_base": 7,
                            "baseline_policy": "tail_append",
                            "ours_policy": "business_aware_constrained_insert",
                            "background_packet_kb": 2,
                            "scene_bank": {
                                "medium_distance_range_m": [170.0, 230.0],
                                "good_distance_range_m": [80.0, 140.0],
                                "poor_distance_range_m": [390.0, 470.0]
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                ["python", "scripts/run_systematic_simulation_analysis.py", str(config_path)],
                cwd=repo_root,
                env={**os.environ, "PYTHONPATH": "src"},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue((output_dir / "experiment_manifest.json").exists())
            self.assertTrue((output_dir / "per_run_rows.csv").exists())
            self.assertTrue((output_dir / "paired_rows.csv").exists())
            self.assertTrue((output_dir / "scene_summary.csv").exists())
            self.assertTrue((output_dir / "region_summary.csv").exists())
            self.assertTrue((output_dir / "capacity_summary_95.csv").exists())
            self.assertTrue((output_dir / "capacity_summary_90.csv").exists())
            self.assertTrue((output_dir / "typical_case_candidates.csv").exists())
            self.assertTrue((output_dir / "summary_report.md").exists())
```

- [ ] **Step 2: Run the smoke test and verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_writes_manifest_and_tables -v`

Expected: FAIL because the runner script and reference config do not exist yet.

- [ ] **Step 3: Add the checked-in reference config**

```json
// configs/systematic_simulation_analysis_option1.json
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
      "mcs_table": [
        {"sinr_db": -5.0, "mcs_index": 0, "bits_per_prb": 24},
        {"sinr_db": 0.0, "mcs_index": 1, "bits_per_prb": 48},
        {"sinr_db": 10.0, "mcs_index": 2, "bits_per_prb": 96}
      ]
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
    "output_dir": "outputs/systematic_simulation_analysis_option1",
    "keep_slot_trace": false
  },
  "systematic_analysis": {
    "background_user_count_values": [24, 36, 48],
    "pdb_user_count_values": [4, 10, 16],
    "pdb_ms_values": [100, 300, 500],
    "pdb_packet_kb_values": [50, 150, 300],
    "repeat_count": 10,
    "random_seed_base": 7,
    "baseline_policy": "tail_append",
    "ours_policy": "business_aware_constrained_insert",
    "background_packet_kb": 2,
    "scene_bank": {
      "medium_distance_range_m": [170.0, 230.0],
      "good_distance_range_m": [80.0, 140.0],
      "poor_distance_range_m": [390.0, 470.0]
    }
  }
}
```

- [ ] **Step 4: Implement the sweep runner and output writers**

```python
# scripts/run_systematic_simulation_analysis.py
import csv
import json
import sys
from dataclasses import replace
from pathlib import Path

from scheduling_sim.config import load_config
from scheduling_sim.metrics import MetricsCollector
from scheduling_sim.simulator import UlSimulator
from scheduling_sim.systematic_analysis import (
    SceneBankSpec,
    aggregate_scene_rows,
    build_realization_bank,
    build_systematic_case_users,
    capacity_summary_rows,
    paired_metric_row,
    per_run_metric_row,
    select_typical_case_rows,
    summarize_regions,
    systematic_cases,
)


def _write_table(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _summary_report(*, manifest: dict[str, object], scene_rows: list[dict[str, object]], region_rows: list[dict[str, object]]) -> str:
    lines = [
        "# Systematic Simulation Analysis",
        "",
        "## Scan",
        "",
        f"- background_user_count: `{manifest['background_user_count_values']}`",
        f"- pdb_user_count: `{manifest['pdb_user_count_values']}`",
        f"- pdb_ms: `{manifest['pdb_ms_values']}`",
        f"- pdb_packet_kb: `{manifest['pdb_packet_kb_values']}`",
        f"- repeat_count: `{manifest['repeat_count']}`",
        "",
        "## Region Summary",
        "",
        "| Region | Scene Points | Share | Win Rate | Mean Delta PDB Satisfaction | Mean Center Retention |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in region_rows:
        lines.append(
            f"| {row['region']} | {row['scene_point_count']} | {float(row['scene_point_share']):.2f} | "
            f"{float(row['proposed_win_rate']):.2f} | {float(row['mean_delta_pdb_satisfaction_rate']):.3f} | "
            f"{float(row['mean_center_throughput_retention']):.3f} |"
        )
    lines.extend(["", "## Scene Summary", "", f"- Aggregated scene points: `{len(scene_rows)}`"])
    typical_rows = select_typical_case_rows(scene_rows)
    if typical_rows:
        lines.extend(
            [
                "",
                "## Typical Cases",
                "",
                "| Label | background_user_count | pdb_user_count | pdb_ms | pdb_packet_kb | Mean Delta PDB Satisfaction | Center Retention |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in typical_rows:
            lines.append(
                f"| {row['case_label']} | {row['background_user_count']} | {row['pdb_user_count']} | "
                f"{row['pdb_ms']} | {row['pdb_packet_kb']} | "
                f"{float(row['mean_delta_pdb_satisfaction_rate']):.3f} | "
                f"{float(row['mean_center_throughput_retention']):.3f} |"
            )
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run_systematic_simulation_analysis.py CONFIG", file=sys.stderr)
        return 2

    config_path = Path(sys.argv[1])
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    base_config = load_config(config_path)
    sweep = payload["systematic_analysis"]
    scene_bank_spec = SceneBankSpec(
        medium_count=24,
        good_count=24,
        poor_count=16,
        medium_distance_range_m=tuple(sweep["scene_bank"]["medium_distance_range_m"]),
        good_distance_range_m=tuple(sweep["scene_bank"]["good_distance_range_m"]),
        poor_distance_range_m=tuple(sweep["scene_bank"]["poor_distance_range_m"]),
    )
    output_dir = Path(base_config.report.output_dir)
    per_run_rows: list[dict[str, object]] = []
    paired_rows: list[dict[str, object]] = []
    raw_summaries: list[dict[str, object]] = []
    baseline_policy = str(sweep["baseline_policy"])
    ours_policy = str(sweep["ours_policy"])

    for repeat_index in range(int(sweep["repeat_count"])):
        bank_seed = int(sweep["random_seed_base"]) + repeat_index
        bank = build_realization_bank(base_config, scene_bank_spec=scene_bank_spec, bank_seed=bank_seed)
        for case in systematic_cases(
            background_user_counts=sweep["background_user_count_values"],
            pdb_user_counts=sweep["pdb_user_count_values"],
            pdb_ms_values=sweep["pdb_ms_values"],
            pdb_packet_kb_values=sweep["pdb_packet_kb_values"],
        ):
            scenario_id = (
                f"bg{case.background_user_count}_pdb{case.pdb_user_count}_"
                f"d{case.pdb_ms}_k{case.pdb_packet_kb}_seed{repeat_index:02d}"
            )
            summaries_by_policy: dict[str, dict[str, float]] = {}
            for policy in (baseline_policy, ours_policy):
                case_config = replace(
                    base_config,
                    scheduler=replace(base_config.scheduler, reinsert_policy=policy),
                    report=replace(base_config.report, output_dir=str(output_dir)),
                )
                users = build_systematic_case_users(
                    case_config,
                    bank,
                    background_user_count=case.background_user_count,
                    pdb_user_count=case.pdb_user_count,
                    pdb_ms=case.pdb_ms,
                    pdb_packet_bits=int(case.pdb_packet_kb) * 1000 * 8,
                    background_packet_bits=int(sweep["background_packet_kb"]) * 1000 * 8,
                )
                collector = MetricsCollector()
                summary = UlSimulator(case_config, users, collector).run()
                raw_summaries.append(
                    {
                        "seed": bank_seed,
                        "scenario_id": scenario_id,
                        "policy": policy,
                        "summary": summary,
                    }
                )
                per_run_rows.append(
                    per_run_metric_row(
                        scenario_id=scenario_id,
                        seed=bank_seed,
                        policy=policy,
                        case=case,
                        summary=summary,
                    )
                )
                summaries_by_policy[policy] = summary
            paired_rows.append(
                paired_metric_row(
                    case=case,
                    seed=bank_seed,
                    baseline_summary=summaries_by_policy[baseline_policy],
                    proposed_summary=summaries_by_policy[ours_policy],
                )
            )

    scene_rows = aggregate_scene_rows(paired_rows)
    region_rows = summarize_regions(scene_rows)
    capacity_rows_95 = capacity_summary_rows(scene_rows, threshold=0.95)
    capacity_rows_90 = capacity_summary_rows(scene_rows, threshold=0.90)
    typical_case_rows = select_typical_case_rows(scene_rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "experiment_manifest.json").write_text(json.dumps(sweep, indent=2), encoding="utf-8")
    (output_dir / "raw_summaries.json").write_text(json.dumps(raw_summaries, indent=2), encoding="utf-8")
    _write_table(output_dir / "per_run_rows.csv", per_run_rows)
    _write_table(output_dir / "paired_rows.csv", paired_rows)
    _write_table(output_dir / "scene_summary.csv", scene_rows)
    _write_table(output_dir / "region_summary.csv", region_rows)
    _write_table(output_dir / "capacity_summary_95.csv", capacity_rows_95)
    _write_table(output_dir / "capacity_summary_90.csv", capacity_rows_90)
    _write_table(output_dir / "typical_case_candidates.csv", typical_case_rows)
    (output_dir / "summary_report.md").write_text(
        _summary_report(manifest=sweep, scene_rows=scene_rows, region_rows=region_rows),
        encoding="utf-8",
    )
    print(output_dir / "summary_report.md")
    return 0
```

- [ ] **Step 5: Run the runner smoke and the systematic-analysis unit tests**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_writes_manifest_and_tables -v`

Expected: PASS

- [ ] **Step 6: Commit the runner and reference config**

```bash
git add src/scheduling_sim/systematic_analysis.py scripts/run_systematic_simulation_analysis.py configs/systematic_simulation_analysis_option1.json tests/test_systematic_analysis.py tests/test_cli.py
git commit -m "feat: add systematic analysis runner"
```

## Task 5: Add the Overview, Cost, and Boundary Plot Renderer

**Files:**
- Create: `scripts/render_systematic_simulation_analysis_plots.py`
- Create: `tests/test_systematic_analysis_plots.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing plot-render tests**

```python
# tests/test_systematic_analysis_plots.py
import csv
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class SystematicAnalysisPlotTests(unittest.TestCase):
    def test_render_script_writes_overview_cost_and_boundary_plots(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            (output_dir / "experiment_manifest.json").write_text(
                json.dumps(
                    {
                        "background_user_count_values": [24, 36, 48],
                        "pdb_user_count_values": [4, 10, 16],
                        "pdb_ms_values": [100, 300, 500],
                        "pdb_packet_kb_values": [50, 150, 300]
                    }
                ),
                encoding="utf-8",
            )
            with (output_dir / "scene_summary.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "background_user_count",
                        "pdb_user_count",
                        "pdb_ms",
                        "pdb_packet_kb",
                        "mean_delta_pdb_satisfaction_rate",
                        "mean_center_throughput_retention",
                        "baseline_edge_pdb_satisfaction_rate",
                        "proposed_edge_pdb_satisfaction_rate"
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "background_user_count": 24,
                        "pdb_user_count": 4,
                        "pdb_ms": 100,
                        "pdb_packet_kb": 50,
                        "mean_delta_pdb_satisfaction_rate": 0.20,
                        "mean_center_throughput_retention": 0.95,
                        "baseline_edge_pdb_satisfaction_rate": 0.80,
                        "proposed_edge_pdb_satisfaction_rate": 1.00
                    }
                )
            with (output_dir / "capacity_summary_95.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["dimension", "background_user_count", "pdb_user_count", "pdb_ms", "pdb_packet_kb", "threshold", "capacity_gain_pdb_users", "capacity_gain_background_users"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "dimension": "fixed_background_user_count",
                        "background_user_count": 24,
                        "pdb_user_count": "",
                        "pdb_ms": 100,
                        "pdb_packet_kb": 50,
                        "threshold": 0.95,
                        "capacity_gain_pdb_users": 6,
                        "capacity_gain_background_users": ""
                    }
                )
            with (output_dir / "capacity_summary_90.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["dimension", "background_user_count", "pdb_user_count", "pdb_ms", "pdb_packet_kb", "threshold", "capacity_gain_pdb_users", "capacity_gain_background_users"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "dimension": "fixed_background_user_count",
                        "background_user_count": 24,
                        "pdb_user_count": "",
                        "pdb_ms": 100,
                        "pdb_packet_kb": 50,
                        "threshold": 0.90,
                        "capacity_gain_pdb_users": 6,
                        "capacity_gain_background_users": ""
                    }
                )
            result = subprocess.run(
                ["python", "scripts/render_systematic_simulation_analysis_plots.py", str(output_dir)],
                cwd=repo_root,
                env={**os.environ, "PYTHONPATH": "src"},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue((output_dir / "overview_delta_pdb_satisfaction.png").exists())
            self.assertTrue((output_dir / "center_throughput_retention.png").exists())
            self.assertTrue((output_dir / "capacity_boundary_95.png").exists())
            self.assertTrue((output_dir / "capacity_boundary_90.png").exists())
```

- [ ] **Step 2: Run the plot test file and verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis_plots -v`

Expected: FAIL because the renderer script does not exist yet.

- [ ] **Step 3: Implement the plot renderer**

```python
# scripts/render_systematic_simulation_analysis_plots.py
import csv
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _scene_value(rows: list[dict[str, str]], *, pdb_ms: int, pdb_packet_kb: int, background_user_count: int, pdb_user_count: int, field_name: str) -> float:
    for row in rows:
        if (
            int(row["pdb_ms"]) == pdb_ms
            and int(row["pdb_packet_kb"]) == pdb_packet_kb
            and int(row["background_user_count"]) == background_user_count
            and int(row["pdb_user_count"]) == pdb_user_count
        ):
            return float(row[field_name])
    return 0.0


def _heatmap_grid(rows: list[dict[str, str]], manifest: dict[str, object], *, field_name: str, title: str, output_path: Path) -> None:
    pdb_ms_values = [int(value) for value in manifest["pdb_ms_values"]]
    packet_values = [int(value) for value in manifest["pdb_packet_kb_values"]]
    background_values = [int(value) for value in manifest["background_user_count_values"]]
    pdb_user_values = [int(value) for value in manifest["pdb_user_count_values"]]
    fig, axes = plt.subplots(len(pdb_ms_values), len(packet_values), figsize=(12, 10), constrained_layout=True)
    for row_index, pdb_ms in enumerate(pdb_ms_values):
        for col_index, packet_kb in enumerate(packet_values):
            ax = axes[row_index][col_index]
            matrix = [
                [
                    _scene_value(
                        rows,
                        pdb_ms=pdb_ms,
                        pdb_packet_kb=packet_kb,
                        background_user_count=background_user_count,
                        pdb_user_count=pdb_user_count,
                        field_name=field_name,
                    )
                    for background_user_count in background_values
                ]
                for pdb_user_count in pdb_user_values
            ]
            image = ax.imshow(matrix, aspect="auto", origin="lower")
            ax.set_title(f"PDB {pdb_ms} ms / {packet_kb} KB")
            ax.set_xticks(range(len(background_values)), labels=[str(value) for value in background_values])
            ax.set_yticks(range(len(pdb_user_values)), labels=[str(value) for value in pdb_user_values])
            ax.set_xlabel("background_user_count")
            ax.set_ylabel("pdb_user_count")
            fig.colorbar(image, ax=ax, shrink=0.75)
    fig.suptitle(title)
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def _boundary_plot(rows: list[dict[str, str]], manifest: dict[str, object], *, capacity_rows: list[dict[str, str]], threshold: float, output_path: Path) -> None:
    pdb_ms_values = [int(value) for value in manifest["pdb_ms_values"]]
    packet_values = [int(value) for value in manifest["pdb_packet_kb_values"]]
    fig, axes = plt.subplots(len(pdb_ms_values), len(packet_values), figsize=(12, 10), constrained_layout=True)
    for row_index, pdb_ms in enumerate(pdb_ms_values):
        for col_index, packet_kb in enumerate(packet_values):
            ax = axes[row_index][col_index]
            subset = [
                row for row in capacity_rows
                if int(row["pdb_ms"]) == pdb_ms and int(row["pdb_packet_kb"]) == packet_kb
            ]
            gains = [
                float(row["capacity_gain_pdb_users"] or 0.0)
                for row in subset
                if row["dimension"] == "fixed_background_user_count"
            ]
            ax.bar(range(len(gains)), gains)
            ax.set_title(f"PDB {pdb_ms} ms / {packet_kb} KB")
            ax.set_xlabel("background slices")
            ax.set_ylabel("capacity gain")
    fig.suptitle(f"Boundary Expansion @ {threshold:.0%}")
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: render_systematic_simulation_analysis_plots.py OUTPUT_DIR", file=sys.stderr)
        return 2

    output_dir = Path(sys.argv[1])
    manifest = json.loads((output_dir / "experiment_manifest.json").read_text(encoding="utf-8"))
    scene_rows = _rows(output_dir / "scene_summary.csv")
    capacity_rows_95 = _rows(output_dir / "capacity_summary_95.csv")
    capacity_rows_90 = _rows(output_dir / "capacity_summary_90.csv")
    _heatmap_grid(
        scene_rows,
        manifest,
        field_name="mean_delta_pdb_satisfaction_rate",
        title="Mean Paired Delta PDB Satisfaction",
        output_path=output_dir / "overview_delta_pdb_satisfaction.png",
    )
    _heatmap_grid(
        scene_rows,
        manifest,
        field_name="mean_center_throughput_retention",
        title="Mean Center Throughput Retention",
        output_path=output_dir / "center_throughput_retention.png",
    )
    _boundary_plot(
        scene_rows,
        manifest,
        capacity_rows=capacity_rows_95,
        threshold=0.95,
        output_path=output_dir / "capacity_boundary_95.png",
    )
    _boundary_plot(
        scene_rows,
        manifest,
        capacity_rows=capacity_rows_90,
        threshold=0.90,
        output_path=output_dir / "capacity_boundary_90.png",
    )
    print(output_dir)
    return 0
```

- [ ] **Step 4: Run the plot test file and verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_systematic_analysis_plots -v`

Expected: PASS

- [ ] **Step 5: Commit the renderer**

```bash
git add scripts/render_systematic_simulation_analysis_plots.py tests/test_systematic_analysis_plots.py
git commit -m "feat: add systematic analysis plots"
```

## Task 6: Add Final CLI Integration Coverage and Run Focused Verification

**Files:**
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add one final CLI smoke that chains runner output into renderer output**

```python
# tests/test_cli.py
    def test_systematic_simulation_analysis_renderer_runs_on_runner_output(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "systematic_small.json"
            output_dir = Path(tmp) / "systematic-output"
            config_path.write_text(
                Path(repo_root / "configs" / "systematic_simulation_analysis_option1.json").read_text(encoding="utf-8").replace(
                    '"output_dir": "outputs/systematic_simulation_analysis_option1"',
                    f'"output_dir": "{output_dir}"'
                ),
                encoding="utf-8",
            )
            run_result = subprocess.run(
                ["python", "scripts/run_systematic_simulation_analysis.py", str(config_path)],
                cwd=repo_root,
                env={**os.environ, "PYTHONPATH": "src"},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(run_result.returncode, 0, msg=run_result.stderr)
            render_result = subprocess.run(
                ["python", "scripts/render_systematic_simulation_analysis_plots.py", str(output_dir)],
                cwd=repo_root,
                env={**os.environ, "PYTHONPATH": "src"},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(render_result.returncode, 0, msg=render_result.stderr)
            self.assertTrue((output_dir / "overview_delta_pdb_satisfaction.png").exists())
            self.assertTrue((output_dir / "center_throughput_retention.png").exists())
            self.assertTrue((output_dir / "capacity_boundary_95.png").exists())
            self.assertTrue((output_dir / "capacity_boundary_90.png").exists())
```

- [ ] **Step 2: Run the focused verification set**

Run: `PYTHONPATH=src python -m unittest tests.test_wireless_env tests.test_systematic_analysis tests.test_systematic_analysis_plots tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_runner_writes_manifest_and_tables tests.test_cli.CliSmokeTests.test_systematic_simulation_analysis_renderer_runs_on_runner_output -v`

Expected: PASS

- [ ] **Step 3: Run the nearby regression slice around the touched simulator/report code**

Run: `PYTHONPATH=src python -m unittest tests.test_simulator tests.test_config tests.test_cli.CliSmokeTests.test_run_command_report_contains_grouped_metrics -v`

Expected: PASS

- [ ] **Step 4: Commit the final integration coverage**

```bash
git add tests/test_cli.py
git commit -m "test: verify systematic analysis integration"
```

## Self-Review Checklist

- Spec coverage:
  - fixed wireless defaults and approved scan grid are captured by the reference config in Task 4;
  - controlled `poor/medium/good` classes, reusable `64 UE` mother scenes, and nested slicing are covered by Task 2;
  - paired `baseline/proposed` comparisons, region summaries, and capacity summaries are covered by Task 3 and Task 4;
  - representative-case selection is covered by Task 3 and written by Task 4;
  - panoramic gain/cost/boundary figures are covered by Task 5;
  - final runner and renderer integration coverage is covered by Task 6.
- Placeholder scan:
  - no placeholder markers remain in steps or code snippets;
  - every code-changing step includes concrete code or a concrete command.
- Type consistency:
  - `background_user_count`, `pdb_user_count`, `pdb_ms`, and `pdb_packet_kb` are used consistently across unit tests, runner outputs, and plots;
  - `SceneBankSpec`, `RealizationBank`, `SystematicCase`, `per_run_metric_row`, `paired_metric_row`, `aggregate_scene_rows`, `summarize_regions`, and `capacity_summary_rows` are introduced before later tasks rely on them.
