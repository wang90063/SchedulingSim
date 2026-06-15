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
    LoadRatioCase,
    SceneBankSpec,
    SystematicCase,
    aggregate_scene_rows,
    build_boundary_feasibility_rows,
    build_realization_bank,
    load_ratio_cases,
    load_ratio_scene_key,
    build_systematic_case_users,
    build_typical_case_detail_rows,
    capacity_summary_rows,
    merge_row_sets,
    paired_metric_row,
    partition_region,
    per_run_metric_row,
    scene_key_set,
    select_typical_case_rows,
    summarize_regions,
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

    def test_systematic_cases_supports_scene_filters(self) -> None:
        cases = systematic_cases(
            background_user_counts=[16, 24],
            pdb_user_counts=[4, 16],
            pdb_ms_values=[100],
            pdb_packet_kb_values=[20],
            include_case=lambda case: (case.background_user_count + case.pdb_user_count) >= 32,
        )
        self.assertEqual(
            [
                (case.background_user_count, case.pdb_user_count, case.pdb_ms, case.pdb_packet_kb)
                for case in cases
            ],
            [(16, 16, 100, 20), (24, 16, 100, 20)],
        )

    def test_load_ratio_cases_expand_to_expected_business_points(self) -> None:
        cases = load_ratio_cases(
            background_user_count=40,
            background_period_ms=10,
            background_packet_kb_values=[0.8, 1.2],
            pdb_user_count=4,
            pdb_shapes=[
                {"pdb_ms": 100, "pdb_packet_kb_values": [5.0, 10.0]},
                {"pdb_ms": 300, "pdb_packet_kb_values": [15.0]},
            ],
            background_capacity_mbps=66.03,
            pdb_capacity_mbps=8.74,
        )

        self.assertEqual(len(cases), 6)
        self.assertEqual(cases[0].background_user_count, 40)
        self.assertEqual(cases[0].background_packet_kb, 0.8)
        self.assertEqual(cases[0].pdb_user_count, 4)
        self.assertEqual(cases[0].pdb_ms, 100)
        self.assertEqual(cases[0].pdb_packet_kb, 5.0)
        self.assertAlmostEqual(cases[0].rho_bg, 0.388, places=3)
        self.assertAlmostEqual(cases[0].rho_pdb, 0.183, places=3)
        self.assertAlmostEqual(cases[0].prb_share_pdb, 0.3206, places=3)
        self.assertAlmostEqual(cases[0].g_pdb_mbps, 0.4, places=3)

    def test_load_ratio_case_scene_key_remains_compatible_with_existing_pairing(self) -> None:
        case = LoadRatioCase(
            case_label="L01",
            background_user_count=40,
            background_packet_kb=0.8,
            background_period_ms=10,
            pdb_user_count=4,
            pdb_packet_kb=5.0,
            pdb_ms=100,
            rho_bg=0.388,
            rho_pdb=0.183,
            prb_share_pdb=0.321,
            g_pdb_mbps=0.4,
        )

        self.assertEqual(
            load_ratio_scene_key(case),
            (40, 4, 100, 5.0, 0.8, 10),
        )

    def test_scene_key_helpers_deduplicate_scene_rows(self) -> None:
        rows = [
            {"background_user_count": 24, "pdb_user_count": 4, "pdb_ms": 100, "pdb_packet_kb": 50, "seed": 7},
            {"background_user_count": 24, "pdb_user_count": 4, "pdb_ms": 100, "pdb_packet_kb": 50, "seed": 8},
            {"background_user_count": 32, "pdb_user_count": 8, "pdb_ms": 200, "pdb_packet_kb": 70, "seed": 7},
        ]
        self.assertEqual(
            scene_key_set(rows),
            {
                (24, 4, 100, 50),
                (32, 8, 200, 70),
            },
        )

    def test_merge_row_sets_appends_without_losing_existing_rows(self) -> None:
        merged = merge_row_sets(
            existing_rows=[
                {"seed": 7, "background_user_count": 24, "pdb_user_count": 4, "pdb_ms": 100, "pdb_packet_kb": 50}
            ],
            new_rows=[
                {"seed": 8, "background_user_count": 32, "pdb_user_count": 8, "pdb_ms": 200, "pdb_packet_kb": 70}
            ],
        )
        self.assertEqual(len(merged), 2)
        self.assertEqual(
            [row["background_user_count"] for row in merged],
            [24, 32],
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

    def test_build_typical_case_detail_rows_expands_each_selected_case_to_per_policy_rows(self) -> None:
        scene_rows = [
            {
                "background_user_count": 24,
                "pdb_user_count": 4,
                "pdb_ms": 100,
                "pdb_packet_kb": 50,
                "baseline_edge_pdb_satisfaction_rate": 0.98,
                "proposed_edge_pdb_satisfaction_rate": 0.99,
                "mean_delta_pdb_satisfaction_rate": 0.01,
                "mean_center_throughput_retention": 0.99,
            }
        ]
        per_run_rows = [
            {
                "policy": "tail_append",
                "background_user_count": 24,
                "pdb_user_count": 4,
                "pdb_ms": 100,
                "pdb_packet_kb": 50,
                "edge_pdb_satisfaction_rate": 0.98,
                "center_agg_rate_bps": 1000.0,
                "center_avg_rate_bps": 50.0,
                "prb_utilization": 0.50,
                "center_prb_share": 0.70,
                "edge_prb_share": 0.30,
                "pdb_arrivals_in_window": 8.0,
                "pdb_violation_rate": 0.02,
                "target_edge_completion_delay_ms": 120.0,
                "target_edge_queue_wait_ms": 90.0,
                "target_edge_service_time_ms": 30.0,
                "edge_backlog_bits": 4000.0,
            },
            {
                "policy": "tail_append",
                "background_user_count": 24,
                "pdb_user_count": 4,
                "pdb_ms": 100,
                "pdb_packet_kb": 50,
                "edge_pdb_satisfaction_rate": 0.96,
                "center_agg_rate_bps": 1100.0,
                "center_avg_rate_bps": 55.0,
                "prb_utilization": 0.54,
                "center_prb_share": 0.72,
                "edge_prb_share": 0.28,
                "pdb_arrivals_in_window": 10.0,
                "pdb_violation_rate": 0.04,
                "target_edge_completion_delay_ms": 130.0,
                "target_edge_queue_wait_ms": 110.0,
                "target_edge_service_time_ms": 20.0,
                "edge_backlog_bits": 4200.0,
            },
            {
                "policy": "hopeless_front_insert",
                "background_user_count": 24,
                "pdb_user_count": 4,
                "pdb_ms": 100,
                "pdb_packet_kb": 50,
                "edge_pdb_satisfaction_rate": 0.99,
                "center_agg_rate_bps": 980.0,
                "center_avg_rate_bps": 49.0,
                "prb_utilization": 0.52,
                "center_prb_share": 0.68,
                "edge_prb_share": 0.32,
                "pdb_arrivals_in_window": 8.0,
                "pdb_violation_rate": 0.01,
                "target_edge_completion_delay_ms": 110.0,
                "target_edge_queue_wait_ms": 82.0,
                "target_edge_service_time_ms": 28.0,
                "edge_backlog_bits": 3500.0,
            },
            {
                "policy": "hopeless_front_insert",
                "background_user_count": 24,
                "pdb_user_count": 4,
                "pdb_ms": 100,
                "pdb_packet_kb": 50,
                "edge_pdb_satisfaction_rate": 0.97,
                "center_agg_rate_bps": 960.0,
                "center_avg_rate_bps": 48.0,
                "prb_utilization": 0.50,
                "center_prb_share": 0.66,
                "edge_prb_share": 0.34,
                "pdb_arrivals_in_window": 10.0,
                "pdb_violation_rate": 0.03,
                "target_edge_completion_delay_ms": 108.0,
                "target_edge_queue_wait_ms": 78.0,
                "target_edge_service_time_ms": 30.0,
                "edge_backlog_bits": 3300.0,
            },
        ]

        rows = build_typical_case_detail_rows(
            scene_rows,
            per_run_rows,
            baseline_policy="tail_append",
            proposed_policy="hopeless_front_insert",
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual({row["policy"] for row in rows}, {"tail_append", "hopeless_front_insert"})
        self.assertEqual({row["case_label"] for row in rows}, {"easy"})
        by_policy = {row["policy"]: row for row in rows}
        self.assertEqual(by_policy["tail_append"]["edge_pdb_satisfaction_rate"], 0.97)
        self.assertEqual(by_policy["tail_append"]["center_agg_rate_bps"], 1050.0)
        self.assertEqual(by_policy["tail_append"]["target_edge_queue_wait_ms"], 100.0)
        self.assertEqual(by_policy["hopeless_front_insert"]["edge_pdb_satisfaction_rate"], 0.98)
        self.assertEqual(by_policy["hopeless_front_insert"]["center_agg_rate_bps"], 970.0)
        self.assertEqual(by_policy["hopeless_front_insert"]["target_edge_queue_wait_ms"], 80.0)

    def test_build_typical_case_detail_rows_raises_when_selected_case_is_missing_requested_policy(self) -> None:
        scene_rows = [
            {
                "background_user_count": 24,
                "pdb_user_count": 4,
                "pdb_ms": 100,
                "pdb_packet_kb": 50,
                "baseline_edge_pdb_satisfaction_rate": 0.98,
                "proposed_edge_pdb_satisfaction_rate": 0.99,
                "mean_delta_pdb_satisfaction_rate": 0.01,
                "mean_center_throughput_retention": 0.99,
            }
        ]
        per_run_rows = [
            {
                "policy": "tail_append",
                "background_user_count": 24,
                "pdb_user_count": 4,
                "pdb_ms": 100,
                "pdb_packet_kb": 50,
                "edge_pdb_satisfaction_rate": 0.98,
                "center_agg_rate_bps": 1000.0,
                "center_avg_rate_bps": 50.0,
                "prb_utilization": 0.50,
                "center_prb_share": 0.70,
                "edge_prb_share": 0.30,
                "pdb_arrivals_in_window": 8.0,
                "pdb_violation_rate": 0.02,
                "target_edge_completion_delay_ms": 120.0,
                "target_edge_queue_wait_ms": 90.0,
                "target_edge_service_time_ms": 30.0,
                "edge_backlog_bits": 4000.0,
            }
        ]

        with self.assertRaisesRegex(
            ValueError,
            "missing policy hopeless_front_insert for representative case bg=24 pdb_users=4 pdb_ms=100 pdb_kb=50",
        ):
            build_typical_case_detail_rows(
                scene_rows,
                per_run_rows,
                baseline_policy="tail_append",
                proposed_policy="hopeless_front_insert",
            )

    def test_boundary_feasibility_rows_builds_baseline_and_proposed_masks(self) -> None:
        rows = build_boundary_feasibility_rows(
            [
                {
                    "background_user_count": 24,
                    "pdb_user_count": 4,
                    "pdb_ms": 100,
                    "pdb_packet_kb": 50,
                    "baseline_edge_pdb_satisfaction_rate": 0.88,
                    "proposed_edge_pdb_satisfaction_rate": 0.95,
                }
            ],
            threshold=0.95,
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["baseline_feasible"], 0)
        self.assertEqual(rows[0]["proposed_feasible"], 1)
        self.assertEqual(rows[0]["threshold"], 0.95)

    def test_boundary_feasibility_rows_treats_equality_at_threshold_as_feasible(self) -> None:
        rows = build_boundary_feasibility_rows(
            [
                {
                    "background_user_count": 36,
                    "pdb_user_count": 10,
                    "pdb_ms": 300,
                    "pdb_packet_kb": 150,
                    "baseline_edge_pdb_satisfaction_rate": 0.95,
                    "proposed_edge_pdb_satisfaction_rate": 0.95,
                }
            ],
            threshold=0.95,
        )

        self.assertEqual(rows[0]["baseline_feasible"], 1)
        self.assertEqual(rows[0]["proposed_feasible"], 1)
