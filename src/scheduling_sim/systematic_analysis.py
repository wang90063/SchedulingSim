from dataclasses import dataclass
import math
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
        per_prb_tx_power_dbm=float(getattr(env_config, "per_prb_tx_power_dbm", 5.0)),
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


def per_run_metric_row(
    *,
    scenario_id: str,
    seed: int,
    policy: str,
    case: SystematicCase,
    summary: dict[str, float],
) -> dict[str, float | int | str]:
    return {
        "seed": int(seed),
        "scenario_id": scenario_id,
        "policy": str(policy),
        "background_user_count": int(case.background_user_count),
        "pdb_user_count": int(case.pdb_user_count),
        "pdb_ms": int(case.pdb_ms),
        "pdb_packet_kb": int(case.pdb_packet_kb),
        "edge_pdb_satisfaction_rate": float(summary["edge_pdb_satisfaction_rate"]),
        "center_agg_rate_bps": float(summary["center_agg_rate_bps"]),
        "center_avg_rate_bps": float(summary["center_avg_rate_bps"]),
        "prb_utilization": float(summary["prb_utilization"]),
        "center_prb_share": float(summary["center_prb_share"]),
        "edge_prb_share": float(summary["edge_prb_share"]),
        "pdb_arrivals_in_window": float(summary.get("pdb_arrivals_in_window", 0.0)),
        "pdb_violation_rate": float(summary["pdb_violation_rate"]),
        "target_edge_completion_delay_ms": float(summary["target_edge_completion_delay_ms"]),
        "target_edge_queue_wait_ms": float(summary["target_edge_queue_wait_ms"]),
        "target_edge_service_time_ms": float(summary["target_edge_service_time_ms"]),
        "edge_backlog_bits": float(summary["edge_backlog_bits"]),
    }


def paired_metric_row(
    *,
    case: SystematicCase,
    seed: int,
    baseline_summary: dict[str, float],
    proposed_summary: dict[str, float],
) -> dict[str, float | int]:
    baseline_center_rate = float(baseline_summary["center_agg_rate_bps"])
    proposed_center_rate = float(proposed_summary["center_agg_rate_bps"])
    delta_pdb_satisfaction_rate = round(
        float(proposed_summary["edge_pdb_satisfaction_rate"])
        - float(baseline_summary["edge_pdb_satisfaction_rate"]),
        12,
    )
    center_throughput_retention = round(
        1.0 if baseline_center_rate == 0.0 else proposed_center_rate / baseline_center_rate,
        12,
    )
    return {
        "seed": int(seed),
        "background_user_count": int(case.background_user_count),
        "pdb_user_count": int(case.pdb_user_count),
        "pdb_ms": int(case.pdb_ms),
        "pdb_packet_kb": int(case.pdb_packet_kb),
        "baseline_edge_pdb_satisfaction_rate": float(baseline_summary["edge_pdb_satisfaction_rate"]),
        "proposed_edge_pdb_satisfaction_rate": float(proposed_summary["edge_pdb_satisfaction_rate"]),
        "delta_pdb_satisfaction_rate": delta_pdb_satisfaction_rate,
        "center_throughput_retention": center_throughput_retention,
        "delta_prb_utilization": float(proposed_summary["prb_utilization"]) - float(baseline_summary["prb_utilization"]),
        "delta_center_prb_share": float(proposed_summary["center_prb_share"]) - float(baseline_summary["center_prb_share"]),
        "delta_edge_prb_share": float(proposed_summary["edge_prb_share"]) - float(baseline_summary["edge_prb_share"]),
    }


def _mean(values: list[float]) -> float:
    return sum(values) / float(len(values)) if values else 0.0


def _stdev(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    mean_value = _mean(values)
    variance = sum((value - mean_value) ** 2 for value in values) / float(len(values) - 1)
    return math.sqrt(variance)


def _ci95(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    return 1.96 * _stdev(values) / math.sqrt(float(len(values)))


def aggregate_scene_rows(paired_rows: list[dict[str, float | int]]) -> list[dict[str, float | int]]:
    grouped: dict[tuple[int, int, int, int], list[dict[str, float | int]]] = {}
    for row in paired_rows:
        key = (
            int(row["background_user_count"]),
            int(row["pdb_user_count"]),
            int(row["pdb_ms"]),
            int(row["pdb_packet_kb"]),
        )
        grouped.setdefault(key, []).append(row)
    aggregated: list[dict[str, float | int]] = []
    for key, group in sorted(grouped.items()):
        delta_values = [float(row["delta_pdb_satisfaction_rate"]) for row in group]
        retention_values = [float(row["center_throughput_retention"]) for row in group]
        delta_prb_values = [float(row["delta_prb_utilization"]) for row in group]
        delta_center_share_values = [float(row["delta_center_prb_share"]) for row in group]
        delta_edge_share_values = [float(row["delta_edge_prb_share"]) for row in group]
        baseline_values = [float(row["baseline_edge_pdb_satisfaction_rate"]) for row in group]
        proposed_values = [float(row["proposed_edge_pdb_satisfaction_rate"]) for row in group]
        aggregated.append(
            {
                "background_user_count": key[0],
                "pdb_user_count": key[1],
                "pdb_ms": key[2],
                "pdb_packet_kb": key[3],
                "repeat_count": len(group),
                "baseline_edge_pdb_satisfaction_rate": _mean(baseline_values),
                "proposed_edge_pdb_satisfaction_rate": _mean(proposed_values),
                "mean_delta_pdb_satisfaction_rate": _mean(delta_values),
                "std_delta_pdb_satisfaction_rate": _stdev(delta_values),
                "ci95_delta_pdb_satisfaction_rate": _ci95(delta_values),
                "mean_center_throughput_retention": _mean(retention_values),
                "std_center_throughput_retention": _stdev(retention_values),
                "ci95_center_throughput_retention": _ci95(retention_values),
                "mean_delta_prb_utilization": _mean(delta_prb_values),
                "mean_delta_center_prb_share": _mean(delta_center_share_values),
                "mean_delta_edge_prb_share": _mean(delta_edge_share_values),
            }
        )
    return aggregated


def partition_region(baseline_satisfaction: float) -> str:
    if baseline_satisfaction >= 0.95:
        return "feasible"
    if baseline_satisfaction >= 0.50:
        return "critical"
    return "overloaded"


def summarize_regions(scene_rows: list[dict[str, float | int]]) -> list[dict[str, float | int | str]]:
    total_scene_points = len(scene_rows)
    grouped: dict[str, list[dict[str, float | int]]] = {}
    for row in scene_rows:
        grouped.setdefault(partition_region(float(row["baseline_edge_pdb_satisfaction_rate"])), []).append(row)
    summaries: list[dict[str, float | int | str]] = []
    for region, group in sorted(grouped.items()):
        summaries.append(
            {
                "region": region,
                "scene_point_count": len(group),
                "scene_point_share": 0.0 if total_scene_points == 0 else len(group) / float(total_scene_points),
                "proposed_win_rate": (
                    sum(1 for row in group if float(row["mean_delta_pdb_satisfaction_rate"]) > 0.0) / float(len(group))
                ),
                "mean_delta_pdb_satisfaction_rate": _mean(
                    [float(row["mean_delta_pdb_satisfaction_rate"]) for row in group]
                ),
                "mean_center_throughput_retention": _mean(
                    [float(row["mean_center_throughput_retention"]) for row in group]
                ),
                "mean_delta_prb_utilization": _mean([float(row["mean_delta_prb_utilization"]) for row in group]),
                "mean_delta_center_prb_share": _mean([float(row["mean_delta_center_prb_share"]) for row in group]),
                "mean_delta_edge_prb_share": _mean([float(row["mean_delta_edge_prb_share"]) for row in group]),
            }
        )
    return summaries


def select_typical_case_rows(scene_rows: list[dict[str, float | int]]) -> list[dict[str, float | int | str]]:
    if not scene_rows:
        return []

    selections: list[tuple[str, dict[str, float | int]]] = []
    easy_rows = [
        row
        for row in scene_rows
        if float(row["baseline_edge_pdb_satisfaction_rate"]) >= 0.95
        and float(row["proposed_edge_pdb_satisfaction_rate"]) >= 0.95
    ]
    critical_rows = [
        row for row in scene_rows if 0.50 <= float(row["baseline_edge_pdb_satisfaction_rate"]) < 0.95
    ]
    overloaded_rows = [
        row for row in scene_rows if float(row["baseline_edge_pdb_satisfaction_rate"]) < 0.50
    ]
    positive_gain_rows = [
        row for row in scene_rows if float(row["mean_delta_pdb_satisfaction_rate"]) > 0.0
    ]

    if easy_rows:
        selections.append(("easy", max(easy_rows, key=lambda row: float(row["baseline_edge_pdb_satisfaction_rate"]))))
    if critical_rows:
        selections.append(("critical", max(critical_rows, key=lambda row: float(row["mean_delta_pdb_satisfaction_rate"]))))
    if overloaded_rows:
        selections.append(
            ("overloaded", max(overloaded_rows, key=lambda row: float(row["mean_delta_pdb_satisfaction_rate"])))
        )
    if positive_gain_rows:
        selections.append(("high_cost", min(positive_gain_rows, key=lambda row: float(row["mean_center_throughput_retention"]))))

    deduped: list[dict[str, float | int | str]] = []
    seen_keys: set[tuple[int, int, int, int]] = set()
    for label, row in selections:
        key = (
            int(row["background_user_count"]),
            int(row["pdb_user_count"]),
            int(row["pdb_ms"]),
            int(row["pdb_packet_kb"]),
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(
            {
                "case_label": label,
                "background_user_count": int(row["background_user_count"]),
                "pdb_user_count": int(row["pdb_user_count"]),
                "pdb_ms": int(row["pdb_ms"]),
                "pdb_packet_kb": int(row["pdb_packet_kb"]),
                "baseline_edge_pdb_satisfaction_rate": float(row["baseline_edge_pdb_satisfaction_rate"]),
                "proposed_edge_pdb_satisfaction_rate": float(row["proposed_edge_pdb_satisfaction_rate"]),
                "mean_delta_pdb_satisfaction_rate": float(row["mean_delta_pdb_satisfaction_rate"]),
                "mean_center_throughput_retention": float(row["mean_center_throughput_retention"]),
            }
        )
    return deduped


def capacity_summary_rows(
    scene_rows: list[dict[str, float | int]],
    *,
    threshold: float,
) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    by_background: dict[tuple[int, int, int], list[dict[str, float | int]]] = {}
    by_pdb_users: dict[tuple[int, int, int], list[dict[str, float | int]]] = {}
    for row in scene_rows:
        by_background.setdefault(
            (int(row["background_user_count"]), int(row["pdb_ms"]), int(row["pdb_packet_kb"])),
            [],
        ).append(row)
        by_pdb_users.setdefault(
            (int(row["pdb_user_count"]), int(row["pdb_ms"]), int(row["pdb_packet_kb"])),
            [],
        ).append(row)

    for (background_user_count, pdb_ms, pdb_packet_kb), group in sorted(by_background.items()):
        baseline_max = max(
            [int(row["pdb_user_count"]) for row in group if float(row["baseline_edge_pdb_satisfaction_rate"]) >= threshold],
            default=0,
        )
        proposed_max = max(
            [int(row["pdb_user_count"]) for row in group if float(row["proposed_edge_pdb_satisfaction_rate"]) >= threshold],
            default=0,
        )
        rows.append(
            {
                "dimension": "fixed_background_user_count",
                "background_user_count": background_user_count,
                "pdb_user_count": "",
                "pdb_ms": pdb_ms,
                "pdb_packet_kb": pdb_packet_kb,
                "threshold": float(threshold),
                "baseline_max_pdb_user_count": baseline_max,
                "proposed_max_pdb_user_count": proposed_max,
                "capacity_gain_pdb_users": proposed_max - baseline_max,
            }
        )

    for (pdb_user_count, pdb_ms, pdb_packet_kb), group in sorted(by_pdb_users.items()):
        baseline_max = max(
            [int(row["background_user_count"]) for row in group if float(row["baseline_edge_pdb_satisfaction_rate"]) >= threshold],
            default=0,
        )
        proposed_max = max(
            [int(row["background_user_count"]) for row in group if float(row["proposed_edge_pdb_satisfaction_rate"]) >= threshold],
            default=0,
        )
        rows.append(
            {
                "dimension": "fixed_pdb_user_count",
                "background_user_count": "",
                "pdb_user_count": pdb_user_count,
                "pdb_ms": pdb_ms,
                "pdb_packet_kb": pdb_packet_kb,
                "threshold": float(threshold),
                "baseline_max_background_user_count": baseline_max,
                "proposed_max_background_user_count": proposed_max,
                "capacity_gain_background_users": proposed_max - baseline_max,
            }
        )

    return rows
