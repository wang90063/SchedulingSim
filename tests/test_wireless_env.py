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
