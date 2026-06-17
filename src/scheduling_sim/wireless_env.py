from dataclasses import dataclass, field
import math
import random

from scheduling_sim.models import CurrentRadioState, UserEquipment


@dataclass(frozen=True)
class McsEntryView:
    snr_db: float
    mcs_index: int
    bits_per_prb: int

    @property
    def sinr_db(self) -> float:
        return self.snr_db


@dataclass(frozen=True)
class WirelessEnvConfigView:
    alpha: float = 1.0
    jitter_std_db: float = 0.0
    scenario_type: str = "legacy"
    cell_radius_m: float = 0.0
    carrier_frequency_ghz: float = 0.0
    per_prb_tx_power_dbm: float = 5.0
    noise_figure_db: float = 0.0
    interference_margin_db: float = 0.0
    shadow_std_db: float = 0.0
    slow_fading_alpha: float = 1.0
    slot_jitter_std_db: float = 0.0
    mcs_table: list[McsEntryView] = field(default_factory=list)
    seed: int = 0
    backend: str = "stable"
    sionna_nominal_re_per_user: int = 144


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

    def _resolve_legacy_snr_db(self, user: UserEquipment, previous_snr_db: float | None) -> float:
        alpha = self._config.alpha
        anchor_snr_db = user.radio_profile.base_snr_db
        current_snr_db = anchor_snr_db if previous_snr_db is None else previous_snr_db
        jitter = self._rng.gauss(0.0, self._config.jitter_std_db)
        smoothed_snr_db = alpha * current_snr_db + (1.0 - alpha) * anchor_snr_db + jitter
        return self._clamp_snr(smoothed_snr_db, user)

    @staticmethod
    def _clamp_snr(snr_db: float, user: UserEquipment) -> float:
        return max(user.radio_profile.snr_min_db, min(user.radio_profile.snr_max_db, snr_db))

    def _build_uplink_budget_db(self) -> float:
        thermal_noise_per_prb_dbm = -174.0 + 10.0 * math.log10(180_000.0)
        return self._config.per_prb_tx_power_dbm - (thermal_noise_per_prb_dbm + self._config.noise_figure_db)

    def _uma_path_loss_db(self, distance_to_bs_m: float) -> float:
        distance_m = max(distance_to_bs_m, 10.0)
        frequency_ghz = max(self._config.carrier_frequency_ghz, 0.1)
        return 32.4 + 20.0 * math.log10(frequency_ghz) + 30.0 * math.log10(distance_m)
