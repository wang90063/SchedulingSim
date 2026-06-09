import unittest

from scheduling_sim.config import (
    AppConfig,
    RadioClassConfig,
    RadioSection,
    ReportConfig,
    ResourcesConfig,
    SchedulerConfig,
    SimulationConfig,
    TrafficConfig,
    TrafficSection,
)
from scheduling_sim.random_pdb_user_ratio_sweep import (
    PlannedArrivalOverlay,
    apply_single_shot_pdb_profiles,
    arrival_seed,
    build_case_config,
    build_single_shot_arrival_plan,
    scanned_pdb_user_count,
    select_pdb_user_ids,
    selection_seed,
)
from scheduling_sim.scenario import ScenarioFactory


class RandomPdbUserRatioSweepHelperTests(unittest.TestCase):
    def _base_config(self) -> AppConfig:
        return AppConfig(
            simulation=SimulationConfig(
                cycles=4,
                slot_duration_ms=1,
                tdd_pattern="DSUUU",
                random_seed=7,
                stop_when_target_edge_finished=False,
                deadline_guard_ms=10,
            ),
            resources=ResourcesConfig(total_prb_per_u_slot=273, max_ue_per_slot=16),
            traffic=TrafficSection(
                center=TrafficConfig(count=2, period_slots=6, packet_bits=960, pdb_ms=None, gbr_bps=7000),
                edge=TrafficConfig(count=2, packet_bits=80000, pdb_ms=800),
            ),
            radio=RadioSection(
                center=RadioClassConfig(base_snr_db=16.0, snr_min_db=-10.0, snr_max_db=25.0),
                edge=RadioClassConfig(
                    base_snr_db=0.0,
                    snr_min_db=-10.0,
                    snr_max_db=10.0,
                    edge_per_u_slot_prb_cap=273,
                ),
            ),
            scheduler=SchedulerConfig(ranking="epf", reinsert_policy="business_aware_constrained_insert"),
            report=ReportConfig(output_dir="outputs/test", keep_slot_trace=False),
        )

    def test_scanned_pdb_user_count_matches_historical_rounding_rule(self) -> None:
        self.assertEqual(scanned_pdb_user_count(total_users=32, pdb_user_ratio_pct=5), 2)
        self.assertEqual(scanned_pdb_user_count(total_users=32, pdb_user_ratio_pct=10), 3)
        self.assertEqual(scanned_pdb_user_count(total_users=32, pdb_user_ratio_pct=20), 6)
        self.assertEqual(scanned_pdb_user_count(total_users=40, pdb_user_ratio_pct=5), 2)
        self.assertEqual(scanned_pdb_user_count(total_users=40, pdb_user_ratio_pct=10), 4)
        self.assertEqual(scanned_pdb_user_count(total_users=40, pdb_user_ratio_pct=20), 8)

    def test_build_case_config_moves_all_users_to_center_pool_and_overrides_policy(self) -> None:
        config = build_case_config(self._base_config(), total_users=32, policy="tail_append")
        self.assertEqual(config.traffic.center.count, 32)
        self.assertEqual(config.traffic.edge.count, 0)
        self.assertEqual(config.scheduler.reinsert_policy, "tail_append")

    def test_select_pdb_user_ids_samples_from_full_center_pool_deterministically(self) -> None:
        users = ScenarioFactory(build_case_config(self._base_config(), total_users=32, policy="tail_append")).build_users()
        selected = select_pdb_user_ids(users, pdb_user_ratio_pct=20, seed=77)
        self.assertEqual(
            selected,
            [
                "center-16",
                "center-10",
                "center-6",
                "center-7",
                "center-29",
                "center-26",
            ],
        )

    def test_selection_and_arrival_seeds_stay_reproducible(self) -> None:
        self.assertEqual(selection_seed(random_seed_base=7, total_users=32, pdb_user_ratio_pct=20, repeat_index=0), selection_seed(random_seed_base=7, total_users=32, pdb_user_ratio_pct=20, repeat_index=0))
        self.assertEqual(arrival_seed(random_seed_base=7, total_users=32, pdb_user_ratio_pct=20, repeat_index=0), arrival_seed(random_seed_base=7, total_users=32, pdb_user_ratio_pct=20, repeat_index=0))

    def test_apply_single_shot_pdb_profiles_rewrites_selected_users_only(self) -> None:
        users = ScenarioFactory(build_case_config(self._base_config(), total_users=3, policy="tail_append")).build_users()
        users_by_id = {user.ue_id: user for user in users}
        selected_ue_ids = {"center-0", "center-2"}

        object.__setattr__(users_by_id["center-0"].traffic_profile, "arrival_model", "periodic")
        object.__setattr__(users_by_id["center-0"].traffic_profile, "total_lambda_per_slot", 2.5)

        apply_single_shot_pdb_profiles(users, selected_ue_ids=selected_ue_ids, packet_bits=4000, pdb_ms=120)

        selected_profile = users_by_id["center-0"].traffic_profile
        self.assertEqual(selected_profile.packet_bits, 4000)
        self.assertEqual(selected_profile.pdb_ms, 120)
        self.assertIsNone(selected_profile.period_slots)
        self.assertIsNone(getattr(selected_profile, "total_lambda_per_slot", None))
        self.assertEqual(getattr(selected_profile, "arrival_model", None), "scheduled")

        untouched_profile = users_by_id["center-1"].traffic_profile
        self.assertEqual(untouched_profile.period_slots, 6)
        self.assertEqual(untouched_profile.packet_bits, 960)
        self.assertIsNone(getattr(untouched_profile, "arrival_model", None))

    def test_single_shot_arrival_plan_creates_one_planned_packet_per_selected_user(self) -> None:
        config = build_case_config(self._base_config(), total_users=3, policy="tail_append")
        object.__setattr__(config.traffic.center, "period_slots", 1)
        users = ScenarioFactory(config).build_users()
        users_by_id = {user.ue_id: user for user in users}
        selected_ue_ids = ["center-0", "center-2"]

        apply_single_shot_pdb_profiles(users, selected_ue_ids=set(selected_ue_ids), packet_bits=4000, pdb_ms=120)
        plan = build_single_shot_arrival_plan(
            config,
            users_by_id,
            selected_ue_ids=selected_ue_ids,
            packet_bits=4000,
            seed=19,
        )

        self.assertEqual(plan.planned_pdb_total_count, 2)
        self.assertEqual(set(plan.arrival_slot_by_ue), set(selected_ue_ids))
        self.assertEqual(sum(len(arrivals) for arrivals in plan.planned_arrivals_by_slot.values()), 2)
        for ue_id in selected_ue_ids:
            slot = plan.arrival_slot_by_ue[ue_id]
            arrivals = plan.planned_arrivals_by_slot[slot]
            self.assertTrue(any(arrival.ue_id == ue_id and arrival.is_planned_pdb for arrival in arrivals))

        overlay = PlannedArrivalOverlay(config, users, plan.planned_arrivals_by_slot)
        planned_slot = plan.arrival_slot_by_ue["center-0"]
        arrivals = overlay.arrivals_for_slot(planned_slot)
        self.assertTrue(any(arrival.is_planned_pdb for arrival in arrivals))
        self.assertTrue(any(not arrival.is_planned_pdb for arrival in arrivals))


if __name__ == "__main__":
    unittest.main()
