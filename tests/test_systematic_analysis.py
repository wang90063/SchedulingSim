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
