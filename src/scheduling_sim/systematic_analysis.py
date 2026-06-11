from dataclasses import dataclass
import random

from scheduling_sim.config import AppConfig, RadioClassConfig
from scheduling_sim.models import (
    CurrentRadioState,
    LogicalChannel,
    RadioProfile,
    TrafficProfile,
    UserEquipment,
)
from scheduling_sim.wireless_env import McsEntryView, StableWirelessEnv, WirelessEnvConfigView

POOR_SINR_RANGE_DB = (-5.0, 0.0)
MEDIUM_SINR_RANGE_DB = (0.0, 10.0)
GOOD_SINR_RANGE_DB = (10.0, 20.0)


@dataclass(frozen=True)
class SceneBankSpec:
    medium_count: int
    good_count: int
    poor_count: int
    medium_distance_range_m: tuple[float, float]
    good_distance_range_m: tuple[float, float]
    poor_distance_range_m: tuple[float, float]


@dataclass(frozen=True)
class BankUserTemplate:
    ue_id: str
    is_edge_user: bool
    radio_profile: RadioProfile
    initial_sinr_db: float
    initial_mcs_index: int
    initial_bits_per_prb: int
    initial_per_u_slot_prb_cap: int | None


@dataclass(frozen=True)
class RealizationBank:
    medium_users: tuple[BankUserTemplate, ...]
    good_users: tuple[BankUserTemplate, ...]
    poor_users: tuple[BankUserTemplate, ...]


@dataclass(frozen=True)
class SystematicCase:
    background_user_count: int
    pdb_user_count: int
    pdb_ms: int
    pdb_packet_kb: int


def systematic_cases(
    *,
    background_user_counts: list[int],
    pdb_user_counts: list[int],
    pdb_ms_values: list[int],
    pdb_packet_kb_values: list[int],
) -> list[SystematicCase]:
    return [
        SystematicCase(
            background_user_count=background_user_count,
            pdb_user_count=pdb_user_count,
            pdb_ms=pdb_ms,
            pdb_packet_kb=pdb_packet_kb,
        )
        for background_user_count in background_user_counts
        for pdb_user_count in pdb_user_counts
        for pdb_ms in pdb_ms_values
        for pdb_packet_kb in pdb_packet_kb_values
    ]


def _env_view_from_config(base_config: AppConfig, *, seed: int) -> WirelessEnvConfigView:
    env_config = base_config.radio.environment
    return WirelessEnvConfigView(
        alpha=float(getattr(env_config, "alpha", 1.0)),
        jitter_std_db=float(getattr(env_config, "jitter_std_db", 0.0)),
        scenario_type=str(getattr(env_config, "scenario_type", "legacy")),
        cell_radius_m=float(getattr(env_config, "cell_radius_m", 0.0)),
        carrier_frequency_ghz=float(getattr(env_config, "carrier_frequency_ghz", 0.0)),
        noise_figure_db=float(getattr(env_config, "noise_figure_db", 0.0)),
        interference_margin_db=float(getattr(env_config, "interference_margin_db", 0.0)),
        shadow_std_db=float(getattr(env_config, "shadow_std_db", 0.0)),
        slow_fading_alpha=float(getattr(env_config, "slow_fading_alpha", getattr(env_config, "alpha", 1.0))),
        slot_jitter_std_db=float(getattr(env_config, "slot_jitter_std_db", getattr(env_config, "jitter_std_db", 0.0))),
        mcs_table=[
            McsEntryView(
                snr_db=float(entry.snr_db),
                mcs_index=int(entry.mcs_index),
                bits_per_prb=int(entry.bits_per_prb),
            )
            for entry in getattr(env_config, "mcs_table", [])
        ],
        seed=seed,
    )


def _sample_distance(rng: random.Random, distance_range_m: tuple[float, float]) -> float:
    low, high = distance_range_m
    return rng.uniform(low, high)


def _bank_user(
    *,
    ue_id: str,
    radio_class_config: RadioClassConfig,
    user_class: str,
    is_edge_user: bool,
    distance_to_bs_m: float,
) -> UserEquipment:
    radio_profile = RadioProfile(
        user_class=user_class,
        base_snr_db=float(getattr(radio_class_config, "base_snr_db", 0.0)),
        snr_min_db=float(getattr(radio_class_config, "snr_min_db", 0.0)),
        snr_max_db=float(getattr(radio_class_config, "snr_max_db", 0.0)),
        distance_to_bs_m=distance_to_bs_m,
        edge_per_u_slot_prb_cap=getattr(radio_class_config, "edge_per_u_slot_prb_cap", None),
        bits_per_prb=int(getattr(radio_class_config, "bits_per_prb", 0) or 0),
        per_u_slot_prb_cap=int(getattr(radio_class_config, "per_u_slot_prb_cap", 0) or 0),
    )
    return UserEquipment(
        ue_id=ue_id,
        lc=LogicalChannel(lc_id=f"{ue_id}-lc", packets=[], eligible_cycle=0),
        is_edge_user=is_edge_user,
        radio_profile=radio_profile,
        average_throughput=1.0,
    )


def _template_from_user(user: UserEquipment) -> BankUserTemplate:
    if user.current_radio_state is None:
        raise ValueError(f"user {user.ue_id} has no current radio state")
    return BankUserTemplate(
        ue_id=user.ue_id,
        is_edge_user=user.is_edge_user,
        radio_profile=user.radio_profile,
        initial_sinr_db=user.current_radio_state.snr_db,
        initial_mcs_index=user.current_radio_state.mcs_index,
        initial_bits_per_prb=user.current_radio_state.bits_per_prb,
        initial_per_u_slot_prb_cap=user.current_radio_state.per_u_slot_prb_cap,
    )


def _validate_class_range(template: BankUserTemplate, class_range_db: tuple[float, float], *, class_name: str) -> None:
    low, high = class_range_db
    if low <= template.initial_sinr_db <= high:
        return
    raise ValueError(
        f"{class_name} user {template.ue_id} has initial_sinr_db={template.initial_sinr_db} outside [{low}, {high}]"
    )


def _build_class_users(
    env: StableWirelessEnv,
    rng: random.Random,
    *,
    count: int,
    id_prefix: str,
    radio_class_config: RadioClassConfig,
    user_class: str,
    is_edge_user: bool,
    distance_range_m: tuple[float, float],
    class_range_db: tuple[float, float],
) -> list[UserEquipment]:
    users: list[UserEquipment] = []
    for index in range(count):
        attempts = 0
        while True:
            candidate = _bank_user(
                ue_id=f"{id_prefix}-{index}-sample-{attempts}",
                radio_class_config=radio_class_config,
                user_class=user_class,
                is_edge_user=is_edge_user,
                distance_to_bs_m=_sample_distance(rng, distance_range_m),
            )
            env.reset([candidate])
            template = _template_from_user(candidate)
            try:
                _validate_class_range(template, class_range_db, class_name=id_prefix)
            except ValueError:
                attempts += 1
                if attempts >= 10_000:
                    raise ValueError(f"could not generate {id_prefix} user {index} within requested SINR range")
                continue
            users.append(candidate)
            break
    return users


def build_realization_bank(
    base_config: AppConfig,
    *,
    scene_bank_spec: SceneBankSpec,
    bank_seed: int,
) -> RealizationBank:
    env = StableWirelessEnv(_env_view_from_config(base_config, seed=bank_seed))
    rng = random.Random(bank_seed)

    medium_users = _build_class_users(
        env,
        rng,
        count=scene_bank_spec.medium_count,
        id_prefix="medium",
        radio_class_config=base_config.radio.center,
        user_class="center",
        is_edge_user=False,
        distance_range_m=scene_bank_spec.medium_distance_range_m,
        class_range_db=MEDIUM_SINR_RANGE_DB,
    )
    good_users = _build_class_users(
        env,
        rng,
        count=scene_bank_spec.good_count,
        id_prefix="good",
        radio_class_config=base_config.radio.center,
        user_class="center",
        is_edge_user=False,
        distance_range_m=scene_bank_spec.good_distance_range_m,
        class_range_db=GOOD_SINR_RANGE_DB,
    )
    poor_users = _build_class_users(
        env,
        rng,
        count=scene_bank_spec.poor_count,
        id_prefix="poor",
        radio_class_config=base_config.radio.edge,
        user_class="edge",
        is_edge_user=True,
        distance_range_m=scene_bank_spec.poor_distance_range_m,
        class_range_db=POOR_SINR_RANGE_DB,
    )

    all_users = [*medium_users, *good_users, *poor_users]
    env.reset(all_users)

    medium_templates = tuple(_template_from_user(user) for user in medium_users)
    good_templates = tuple(_template_from_user(user) for user in good_users)
    poor_templates = tuple(_template_from_user(user) for user in poor_users)

    for template in medium_templates:
        _validate_class_range(template, MEDIUM_SINR_RANGE_DB, class_name="medium")
    for template in good_templates:
        _validate_class_range(template, GOOD_SINR_RANGE_DB, class_name="good")
    for template in poor_templates:
        _validate_class_range(template, POOR_SINR_RANGE_DB, class_name="poor")

    return RealizationBank(
        medium_users=medium_templates,
        good_users=good_templates,
        poor_users=poor_templates,
    )


def _background_templates(bank: RealizationBank, *, background_user_count: int) -> list[BankUserTemplate]:
    if background_user_count % 2 != 0:
        raise ValueError("background_user_count must be even for nested medium/good slices")
    per_class_count = background_user_count // 2
    if per_class_count > len(bank.medium_users) or per_class_count > len(bank.good_users):
        raise ValueError("background_user_count exceeds available medium/good templates")
    return [*bank.medium_users[:per_class_count], *bank.good_users[:per_class_count]]


def _user_from_template(
    template: BankUserTemplate,
    *,
    packet_bits: int,
    pdb_ms: int | None,
    period_slots: int | None = None,
) -> UserEquipment:
    traffic_profile = TrafficProfile(
        packet_bits=packet_bits,
        pdb_ms=pdb_ms,
        period_slots=period_slots,
        gbr_bps=0.0,
    )
    if pdb_ms is not None:
        object.__setattr__(traffic_profile, "arrival_mode", "periodic_by_pdb")
        object.__setattr__(traffic_profile, "initial_phase_mode", "uniform_0_to_pdb")
    return UserEquipment(
        ue_id=template.ue_id,
        lc=LogicalChannel(lc_id=f"{template.ue_id}-lc", packets=[], eligible_cycle=0),
        is_edge_user=template.is_edge_user,
        radio_profile=template.radio_profile,
        average_throughput=1.0,
        traffic_profile=traffic_profile,
        current_radio_state=CurrentRadioState(
            snr_db=template.initial_sinr_db,
            mcs_index=template.initial_mcs_index,
            bits_per_prb=template.initial_bits_per_prb,
            per_u_slot_prb_cap=template.initial_per_u_slot_prb_cap,
        ),
    )


def build_systematic_case_users(
    base_config: AppConfig,
    bank: RealizationBank,
    *,
    background_user_count: int,
    pdb_user_count: int,
    pdb_ms: int,
    pdb_packet_bits: int,
    background_packet_bits: int,
) -> list[UserEquipment]:
    if pdb_user_count > len(bank.poor_users):
        raise ValueError("pdb_user_count exceeds available poor templates")

    background_users = [
        _user_from_template(
            template,
            packet_bits=background_packet_bits,
            pdb_ms=None,
            period_slots=base_config.traffic.center.period_slots,
        )
        for template in _background_templates(bank, background_user_count=background_user_count)
    ]
    pdb_users = [
        _user_from_template(
            template,
            packet_bits=pdb_packet_bits,
            pdb_ms=pdb_ms,
            period_slots=None,
        )
        for template in bank.poor_users[:pdb_user_count]
    ]
    return [*background_users, *pdb_users]
