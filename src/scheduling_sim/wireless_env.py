from dataclasses import dataclass
import random

from scheduling_sim.models import CurrentRadioState, UserEquipment


@dataclass(frozen=True)
class McsEntryView:
    snr_db: float
    mcs_index: int
    bits_per_prb: int


@dataclass(frozen=True)
class WirelessEnvConfigView:
    alpha: float
    jitter_std_db: float
    mcs_table: list[McsEntryView]
    seed: int = 0


class StableWirelessEnv:
    def __init__(self, config: WirelessEnvConfigView) -> None:
        self._config = config
        self._rng = random.Random(config.seed)
        self._mcs_table = sorted(config.mcs_table, key=lambda entry: entry.snr_db)

    def reset(self, users: list[UserEquipment]) -> None:
        for user in users:
            base_snr_db = user.radio_profile.base_snr_db
            mcs_entry = self._resolve_mcs(base_snr_db)
            user.current_radio_state = CurrentRadioState(
                snr_db=self._clamp_snr(base_snr_db, user),
                mcs_index=mcs_entry.mcs_index,
                bits_per_prb=mcs_entry.bits_per_prb,
                per_u_slot_prb_cap=self._resolve_prb_cap(user),
            )

    def refresh_slot(self, users: list[UserEquipment], slot_index: int, slot_name: str) -> None:
        _ = (slot_index, slot_name)
        alpha = self._config.alpha
        for user in users:
            previous_snr_db = user.radio_profile.base_snr_db
            if user.current_radio_state is not None:
                previous_snr_db = user.current_radio_state.snr_db
            jitter = self._rng.gauss(0.0, self._config.jitter_std_db)
            smoothed_snr_db = (
                alpha * previous_snr_db
                + (1.0 - alpha) * user.radio_profile.base_snr_db
                + jitter
            )
            snr_db = self._clamp_snr(smoothed_snr_db, user)
            mcs_entry = self._resolve_mcs(snr_db)
            user.current_radio_state = CurrentRadioState(
                snr_db=snr_db,
                mcs_index=mcs_entry.mcs_index,
                bits_per_prb=mcs_entry.bits_per_prb,
                per_u_slot_prb_cap=self._resolve_prb_cap(user),
            )

    def _resolve_mcs(self, snr_db: float) -> McsEntryView:
        if not self._mcs_table:
            return McsEntryView(snr_db=snr_db, mcs_index=0, bits_per_prb=0)
        selected = self._mcs_table[0]
        for entry in self._mcs_table:
            if snr_db >= entry.snr_db:
                selected = entry
        return selected

    @staticmethod
    def _resolve_prb_cap(user: UserEquipment) -> int | None:
        if not user.is_edge_user:
            return None
        return user.radio_profile.edge_per_u_slot_prb_cap

    @staticmethod
    def _clamp_snr(snr_db: float, user: UserEquipment) -> float:
        return max(user.radio_profile.snr_min_db, min(user.radio_profile.snr_max_db, snr_db))
