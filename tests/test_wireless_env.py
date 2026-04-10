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
