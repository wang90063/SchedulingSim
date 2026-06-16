from dataclasses import replace

from scheduling_sim.models import UserEquipment
from scheduling_sim.wireless_env import StableWirelessEnv, WirelessEnvConfigView


def sionna_available() -> bool:
    try:
        import sionna  # noqa: F401
        import torch  # noqa: F401
    except Exception:
        return False
    return True


class SionnaPhyWirelessEnv:
    """Wireless env that reuses StableWirelessEnv for SNR->MCS->bits_per_prb and
    annotates each user's radio state with a BLER computed by Sionna PHYAbstraction.

    Sionna is used purely as a deterministic BLER-curve oracle. All randomness
    that affects the simulation (the HARQ Bernoulli draw) stays on the simulator's
    own RNG, so reproducibility is preserved.
    """

    def __init__(self, config: WirelessEnvConfigView) -> None:
        self._config = config
        self._stable = StableWirelessEnv(config)
        self._nominal_re = int(getattr(config, "sionna_nominal_re_per_user", 144))
        self._phy = None

    def _ensure_phy(self):
        if self._phy is None:
            from sionna.sys import PHYAbstraction

            self._phy = PHYAbstraction()
        return self._phy

    def reset(self, users: list[UserEquipment]) -> None:
        self._stable.reset(users)
        self._annotate_bler(users)

    def refresh_slot(self, users: list[UserEquipment], slot_index: int, slot_name: str) -> None:
        self._stable.refresh_slot(users, slot_index=slot_index, slot_name=slot_name)
        self._annotate_bler(users)

    def _annotate_bler(self, users: list[UserEquipment]) -> None:
        import torch

        states = [user.current_radio_state for user in users]
        active = [i for i, state in enumerate(states) if state is not None and state.bits_per_prb > 0]
        if not active:
            return
        sinr_db = torch.tensor([states[i].snr_db for i in active], dtype=torch.float32)
        sinr_eff = torch.pow(torch.tensor(10.0), sinr_db / 10.0)
        mcs_index = torch.tensor([states[i].mcs_index for i in active], dtype=torch.int32)
        num_allocated_re = torch.full((len(active),), self._nominal_re, dtype=torch.int32)
        phy = self._ensure_phy()
        outputs = phy(mcs_index=mcs_index, sinr_eff=sinr_eff, num_allocated_re=num_allocated_re)
        bler_values = outputs[4].tolist()
        for position, user_index in enumerate(active):
            bler = max(0.0, min(1.0, float(bler_values[position])))
            users[user_index].current_radio_state = replace(states[user_index], bler=bler)
