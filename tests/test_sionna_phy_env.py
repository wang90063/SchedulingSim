import unittest

from scheduling_sim.models import LogicalChannel, RadioProfile, UserEquipment
from scheduling_sim.sionna_phy_env import SionnaPhyWirelessEnv, sionna_available
from scheduling_sim.wireless_env import McsEntryView, WirelessEnvConfigView


def _user(ue_id: str, distance_m: float, is_edge: bool) -> UserEquipment:
    return UserEquipment(
        ue_id=ue_id,
        lc=LogicalChannel(lc_id=ue_id),
        is_edge_user=is_edge,
        radio_profile=RadioProfile(
            user_class="edge" if is_edge else "center",
            distance_to_bs_m=distance_m,
        ),
        average_throughput=0.0,
    )


def _config() -> WirelessEnvConfigView:
    return WirelessEnvConfigView(
        backend="sionna",
        scenario_type="uma",
        cell_radius_m=500.0,
        carrier_frequency_ghz=3.5,
        noise_figure_db=7.0,
        interference_margin_db=3.0,
        shadow_std_db=0.0,
        slow_fading_alpha=1.0,
        slot_jitter_std_db=0.0,
        sionna_nominal_re_per_user=144,
        mcs_table=[
            McsEntryView(snr_db=snr, mcs_index=mcs, bits_per_prb=bits)
            for snr, mcs, bits in [(-7, 1, 12), (0, 4, 48), (8, 8, 150), (18, 13, 400)]
        ],
        seed=7,
    )


@unittest.skipUnless(sionna_available(), "sionna/torch not installed in this env")
class SionnaPhyEnvTests(unittest.TestCase):
    def test_bler_is_a_probability_and_edge_ge_center(self) -> None:
        env = SionnaPhyWirelessEnv(_config())
        center = _user("c0", 80.0, is_edge=False)
        edge = _user("e0", 490.0, is_edge=True)
        env.reset([center, edge])
        edge_bler = edge.current_radio_state.bler
        center_bler = center.current_radio_state.bler
        self.assertGreaterEqual(edge_bler, 0.0)
        self.assertLessEqual(edge_bler, 1.0)
        self.assertGreaterEqual(center_bler, 0.0)
        self.assertLessEqual(center_bler, 1.0)
        self.assertGreaterEqual(edge_bler, center_bler)

    def test_refresh_slot_updates_bler(self) -> None:
        env = SionnaPhyWirelessEnv(_config())
        edge = _user("e0", 490.0, is_edge=True)
        env.reset([edge])
        env.refresh_slot([edge], slot_index=1, slot_name="D")
        self.assertIsNotNone(edge.current_radio_state)
        self.assertGreaterEqual(edge.current_radio_state.bler, 0.0)


if __name__ == "__main__":
    unittest.main()
