import unittest

from scheduling_sim.models import CurrentRadioState, LogicalChannel, RadioProfile, UserEquipment
from scheduling_sim.wireless_env import StableWirelessEnv, WirelessEnvConfigView, McsEntryView


def make_user(name: str, is_edge: bool, distance_to_bs_m: float = 0.0) -> UserEquipment:
    return UserEquipment(
        ue_id=name,
        lc=LogicalChannel(lc_id=f"{name}-lc"),
        is_edge_user=is_edge,
        radio_profile=RadioProfile(
            user_class="edge" if is_edge else "center",
            base_snr_db=4.0 if is_edge else 16.0,
            snr_min_db=-2.0 if is_edge else 10.0,
            snr_max_db=8.0 if is_edge else 22.0,
            distance_to_bs_m=distance_to_bs_m,
            edge_per_u_slot_prb_cap=6 if is_edge else None,
        ),
        average_throughput=1.0,
        current_radio_state=CurrentRadioState(0.0, 0, 4, 6 if is_edge else None),
    )


class StableWirelessEnvTests(unittest.TestCase):
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
                    McsEntryView(snr_db=-5.0, mcs_index=0, bits_per_prb=24),
                    McsEntryView(snr_db=0.0, mcs_index=1, bits_per_prb=48),
                ],
                seed=7,
            )
        )
        edge_user = make_user("edge-0", is_edge=True, distance_to_bs_m=500.0)
        env.reset([edge_user])
        self.assertLess(edge_user.current_radio_state.snr_db, 0.0)
        self.assertEqual(edge_user.current_radio_state.mcs_index, 0)
        self.assertEqual(edge_user.current_radio_state.bits_per_prb, 24)

    def test_refresh_slot_changes_sinr_smoothly(self) -> None:
        env = StableWirelessEnv(
            WirelessEnvConfigView(
                scenario_type="uma",
                cell_radius_m=500.0,
                carrier_frequency_ghz=3.5,
                noise_figure_db=7.0,
                interference_margin_db=3.0,
                shadow_std_db=0.0,
                slow_fading_alpha=0.9,
                slot_jitter_std_db=0.0,
                mcs_table=[McsEntryView(snr_db=-5.0, mcs_index=0, bits_per_prb=24)],
                seed=9,
            )
        )
        center_user = make_user("center-0", is_edge=False, distance_to_bs_m=120.0)
        env.reset([center_user])
        first = center_user.current_radio_state.snr_db
        env.refresh_slot([center_user], slot_index=0, slot_name="D")
        second = center_user.current_radio_state.snr_db
        self.assertLess(abs(second - first), 3.0)

    def test_refresh_maps_mcs_from_clamped_snr(self) -> None:
        env = StableWirelessEnv(
            WirelessEnvConfigView(
                alpha=1.0,
                jitter_std_db=0.0,
                mcs_table=[
                    McsEntryView(snr_db=0.0, mcs_index=0, bits_per_prb=4),
                    McsEntryView(snr_db=6.0, mcs_index=1, bits_per_prb=8),
                ],
                seed=5,
            )
        )
        user = make_user("edge-refresh", is_edge=True)
        user.current_radio_state = CurrentRadioState(20.0, 1, 8, 6)
        env.refresh_slot([user], slot_index=1, slot_name="S")
        self.assertEqual(user.current_radio_state.snr_db, 8.0)
        self.assertEqual(user.current_radio_state.mcs_index, 1)
        self.assertEqual(user.current_radio_state.bits_per_prb, 8)

    def test_reset_maps_mcs_from_clamped_snr(self) -> None:
        env = StableWirelessEnv(
            WirelessEnvConfigView(
                alpha=0.95,
                jitter_std_db=0.2,
                mcs_table=[
                    McsEntryView(snr_db=0.0, mcs_index=0, bits_per_prb=4),
                    McsEntryView(snr_db=6.0, mcs_index=1, bits_per_prb=8),
                ],
                seed=3,
            )
        )
        user = make_user("edge-high", is_edge=True)
        user.radio_profile = RadioProfile(
            user_class="edge",
            base_snr_db=20.0,
            snr_min_db=-2.0,
            snr_max_db=5.0,
            edge_per_u_slot_prb_cap=6,
        )
        env.reset([user])
        self.assertEqual(user.current_radio_state.snr_db, 5.0)
        self.assertEqual(user.current_radio_state.mcs_index, 0)
        self.assertEqual(user.current_radio_state.bits_per_prb, 4)

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
                alpha=0.5,
                jitter_std_db=0.0,
                mcs_table=[McsEntryView(snr_db=0.0, mcs_index=0, bits_per_prb=4)],
                seed=11,
            )
        )
        user = make_user("edge-0", is_edge=True)
        user.current_radio_state = CurrentRadioState(8.0, 0, 4, 6)
        env.refresh_slot([user], slot_index=0, slot_name="D")
        first = user.current_radio_state.snr_db
        env.refresh_slot([user], slot_index=1, slot_name="S")
        second = user.current_radio_state.snr_db
        self.assertEqual(first, 6.0)
        self.assertEqual(second, 5.0)
