from dataclasses import dataclass
import math
import random
from typing import Callable

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


@dataclass(frozen=True)
class BackgroundMappingPolicy:
    background_user_count_values: list[int]
    background_packet_kb_values: list[float]
    background_period_ms_range: tuple[float, float]
    anchor_background_user_count: int
    anchor_background_packet_kb: float
    kind: str = "candidate_domain_solve_period"


@dataclass(frozen=True)
class PdbMappingPolicy:
    pdb_user_count_values: list[int]
    pdb_packet_kb_range: tuple[float, float]
    anchor_pdb_user_count: int
    kind: str = "candidate_domain_solve_packet"


@dataclass(frozen=True)
class LoadRatioMappingPolicy:
    background: BackgroundMappingPolicy
    pdb: PdbMappingPolicy


@dataclass(frozen=True)
class BackgroundMappingResult:
    background_user_count: int
    background_packet_kb: float
    background_period_ms: float
    actual_rho_bg: float
    mapping_policy: str


@dataclass(frozen=True)
class PdbMappingResult:
    pdb_user_count: int
    pdb_packet_kb: float
    pdb_ms: int
    actual_rho_pdb: float
    mapping_policy: str


@dataclass(frozen=True)
class LoadRatioCase:
    case_label: str
    background_user_count: int
    background_packet_kb: float
    background_period_ms: float
    pdb_user_count: int
    pdb_packet_kb: float
    pdb_ms: int
    prb_share_pdb: float
    g_pdb_mbps: float
    target_rho_bg: float | None = None
    target_rho_pdb: float | None = None
    actual_rho_bg: float | None = None
    actual_rho_pdb: float | None = None
    rho_bg: float | None = None
    rho_pdb: float | None = None
    background_mapping_policy: str = ""
    pdb_mapping_policy: str = ""

    def __post_init__(self) -> None:
        resolved_actual_rho_bg = (
            self.actual_rho_bg
            if self.actual_rho_bg is not None
            else self.rho_bg
            if self.rho_bg is not None
            else self.target_rho_bg
        )
        resolved_actual_rho_pdb = (
            self.actual_rho_pdb
            if self.actual_rho_pdb is not None
            else self.rho_pdb
            if self.rho_pdb is not None
            else self.target_rho_pdb
        )
        if resolved_actual_rho_bg is None or resolved_actual_rho_pdb is None:
            raise ValueError("load-ratio cases require rho metadata")
        object.__setattr__(self, "actual_rho_bg", float(resolved_actual_rho_bg))
        object.__setattr__(self, "actual_rho_pdb", float(resolved_actual_rho_pdb))
        object.__setattr__(
            self,
            "target_rho_bg",
            float(self.target_rho_bg if self.target_rho_bg is not None else resolved_actual_rho_bg),
        )
        object.__setattr__(
            self,
            "target_rho_pdb",
            float(self.target_rho_pdb if self.target_rho_pdb is not None else resolved_actual_rho_pdb),
        )
        object.__setattr__(self, "rho_bg", float(self.rho_bg if self.rho_bg is not None else resolved_actual_rho_bg))
        object.__setattr__(self, "rho_pdb", float(self.rho_pdb if self.rho_pdb is not None else resolved_actual_rho_pdb))


SceneFilter = Callable[[SystematicCase], bool]


def systematic_cases(
    *,
    background_user_counts: list[int],
    pdb_user_counts: list[int],
    pdb_ms_values: list[int],
    pdb_packet_kb_values: list[int],
    include_case: SceneFilter | None = None,
) -> list[SystematicCase]:
    cases = [
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
    if include_case is None:
        return cases
    return [case for case in cases if include_case(case)]


def _background_offered_load_mbps(
    *,
    background_user_count: int,
    background_packet_kb: float,
    background_period_ms: float,
) -> float:
    if float(background_period_ms) <= 0.0:
        raise ValueError("background_period_ms must be > 0")
    return (float(background_user_count) * float(background_packet_kb) * 8.0) / float(background_period_ms)


def _pdb_offered_load_mbps(
    *,
    pdb_user_count: int,
    pdb_packet_kb: float,
    pdb_ms: int,
) -> float:
    if int(pdb_ms) <= 0:
        raise ValueError("pdb_ms must be > 0")
    return (float(pdb_user_count) * float(pdb_packet_kb) * 8.0) / float(pdb_ms)


def _round_to_tenth(value: float) -> float:
    return round(float(value), 1)


def solve_background_mapping(
    *,
    target_rho_bg: float,
    background_capacity_mbps: float,
    policy: BackgroundMappingPolicy,
) -> BackgroundMappingResult:
    if float(background_capacity_mbps) <= 0.0:
        raise ValueError("background_capacity_mbps must be > 0")
    if float(target_rho_bg) <= 0.0:
        raise ValueError("target_rho_bg must be > 0")

    target_load_mbps = float(target_rho_bg) * float(background_capacity_mbps)
    min_period_ms, max_period_ms = policy.background_period_ms_range
    candidates: list[tuple[float, tuple[int, float], float, BackgroundMappingResult]] = []
    for background_user_count in policy.background_user_count_values:
        for background_packet_kb in policy.background_packet_kb_values:
            solved_period_ms = (
                float(background_user_count) * float(background_packet_kb) * 8.0
            ) / target_load_mbps
            if not min_period_ms <= solved_period_ms <= max_period_ms:
                continue
            rounded_period_ms = _round_to_tenth(solved_period_ms)
            if not min_period_ms <= rounded_period_ms <= max_period_ms:
                continue
            actual_rho_bg = _background_offered_load_mbps(
                background_user_count=background_user_count,
                background_packet_kb=background_packet_kb,
                background_period_ms=rounded_period_ms,
            ) / float(background_capacity_mbps)
            candidates.append(
                (
                    abs(
                        _background_offered_load_mbps(
                            background_user_count=background_user_count,
                            background_packet_kb=background_packet_kb,
                            background_period_ms=solved_period_ms,
                        )
                        / float(background_capacity_mbps)
                        - float(target_rho_bg)
                    ),
                    (
                        abs(int(background_user_count) - int(policy.anchor_background_user_count)),
                        abs(float(background_packet_kb) - float(policy.anchor_background_packet_kb)),
                    ),
                    abs(actual_rho_bg - float(target_rho_bg)),
                    BackgroundMappingResult(
                        background_user_count=int(background_user_count),
                        background_packet_kb=float(background_packet_kb),
                        background_period_ms=rounded_period_ms,
                        actual_rho_bg=actual_rho_bg,
                        mapping_policy=str(policy.kind),
                    ),
                )
            )
    if not candidates:
        raise ValueError(f"no valid background mapping for target_rho_bg={target_rho_bg}")
    candidates.sort(
        key=lambda item: (
            item[0],
            item[1][0],
            item[1][1],
            item[2],
            item[3].background_user_count,
            item[3].background_packet_kb,
            item[3].background_period_ms,
        )
    )
    return candidates[0][3]


def solve_pdb_mapping(
    *,
    target_rho_pdb: float,
    pdb_ms: int,
    pdb_capacity_mbps: float,
    policy: PdbMappingPolicy,
) -> PdbMappingResult:
    if int(pdb_ms) <= 0:
        raise ValueError("pdb_ms must be > 0")
    if float(pdb_capacity_mbps) <= 0.0:
        raise ValueError("pdb_capacity_mbps must be > 0")
    if float(target_rho_pdb) <= 0.0:
        raise ValueError("target_rho_pdb must be > 0")

    target_load_mbps = float(target_rho_pdb) * float(pdb_capacity_mbps)
    min_packet_kb, max_packet_kb = policy.pdb_packet_kb_range
    candidates: list[tuple[float, int, float, PdbMappingResult]] = []
    for pdb_user_count in policy.pdb_user_count_values:
        solved_packet_kb = (target_load_mbps * float(pdb_ms)) / (float(pdb_user_count) * 8.0)
        if not min_packet_kb <= solved_packet_kb <= max_packet_kb:
            continue
        rounded_packet_kb = _round_to_tenth(solved_packet_kb)
        if not min_packet_kb <= rounded_packet_kb <= max_packet_kb:
            continue
        actual_rho_pdb = _pdb_offered_load_mbps(
            pdb_user_count=pdb_user_count,
            pdb_packet_kb=rounded_packet_kb,
            pdb_ms=pdb_ms,
        ) / float(pdb_capacity_mbps)
        candidates.append(
            (
                abs(
                    _pdb_offered_load_mbps(
                        pdb_user_count=pdb_user_count,
                        pdb_packet_kb=solved_packet_kb,
                        pdb_ms=pdb_ms,
                    )
                    / float(pdb_capacity_mbps)
                    - float(target_rho_pdb)
                ),
                abs(int(pdb_user_count) - int(policy.anchor_pdb_user_count)),
                abs(actual_rho_pdb - float(target_rho_pdb)),
                PdbMappingResult(
                    pdb_user_count=int(pdb_user_count),
                    pdb_packet_kb=rounded_packet_kb,
                    pdb_ms=int(pdb_ms),
                    actual_rho_pdb=actual_rho_pdb,
                    mapping_policy=str(policy.kind),
                ),
            )
        )
    if not candidates:
        raise ValueError(f"no valid pdb mapping for target_rho_pdb={target_rho_pdb} pdb_ms={pdb_ms}")
    candidates.sort(
        key=lambda item: (
            item[0],
            item[1],
            item[2],
            item[3].pdb_user_count,
            item[3].pdb_packet_kb,
        )
    )
    return candidates[0][3]


def _legacy_load_ratio_cases(
    *,
    background_user_count: int,
    background_period_ms: int,
    background_packet_kb_values: list[float],
    pdb_user_count: int,
    pdb_shapes: list[dict[str, object]],
    background_capacity_mbps: float,
    pdb_capacity_mbps: float,
) -> list[LoadRatioCase]:
    if int(background_period_ms) <= 0:
        raise ValueError("background_period_ms must be > 0")
    if float(background_capacity_mbps) <= 0.0:
        raise ValueError("background_capacity_mbps must be > 0")
    if float(pdb_capacity_mbps) <= 0.0:
        raise ValueError("pdb_capacity_mbps must be > 0")

    normalized_pdb_shapes = [
        {
            "pdb_ms": int(shape["pdb_ms"]),
            "pdb_packet_kb_values": [float(value) for value in shape["pdb_packet_kb_values"]],
        }
        for shape in pdb_shapes
    ]
    for shape in normalized_pdb_shapes:
        if int(shape["pdb_ms"]) <= 0:
            raise ValueError("pdb_ms must be > 0")

    cases: list[LoadRatioCase] = []
    case_index = 1
    for background_packet_kb in background_packet_kb_values:
        rho_bg = _background_offered_load_mbps(
            background_user_count=background_user_count,
            background_packet_kb=background_packet_kb,
            background_period_ms=background_period_ms,
        ) / float(background_capacity_mbps)
        for shape in normalized_pdb_shapes:
            pdb_ms = int(shape["pdb_ms"])
            for pdb_packet_kb in shape["pdb_packet_kb_values"]:
                rho_pdb = _pdb_offered_load_mbps(
                    pdb_user_count=pdb_user_count,
                    pdb_packet_kb=pdb_packet_kb,
                    pdb_ms=pdb_ms,
                ) / float(pdb_capacity_mbps)
                prb_share_pdb = rho_pdb / (rho_bg + rho_pdb) if (rho_bg + rho_pdb) > 0.0 else 0.0
                g_pdb_mbps = (float(pdb_packet_kb) * 8.0) / float(pdb_ms)
                cases.append(
                    LoadRatioCase(
                        case_label=f"L{case_index:02d}",
                        background_user_count=background_user_count,
                        background_packet_kb=float(background_packet_kb),
                        background_period_ms=float(background_period_ms),
                        pdb_user_count=pdb_user_count,
                        pdb_packet_kb=float(pdb_packet_kb),
                        pdb_ms=pdb_ms,
                        target_rho_bg=rho_bg,
                        target_rho_pdb=rho_pdb,
                        actual_rho_bg=rho_bg,
                        actual_rho_pdb=rho_pdb,
                        rho_bg=rho_bg,
                        rho_pdb=rho_pdb,
                        prb_share_pdb=prb_share_pdb,
                        g_pdb_mbps=g_pdb_mbps,
                    )
                )
                case_index += 1
    return cases


def _rho_first_load_ratio_cases(
    *,
    rho_bg_values: list[float],
    rho_pdb_values: list[float],
    pdb_ms_values: list[int],
    background_capacity_mbps: float,
    pdb_capacity_mbps: float,
    mapping_policy: LoadRatioMappingPolicy,
) -> list[LoadRatioCase]:
    if float(background_capacity_mbps) <= 0.0:
        raise ValueError("background_capacity_mbps must be > 0")
    if float(pdb_capacity_mbps) <= 0.0:
        raise ValueError("pdb_capacity_mbps must be > 0")

    cases: list[LoadRatioCase] = []
    case_index = 1
    for target_rho_bg in rho_bg_values:
        background_mapping = solve_background_mapping(
            target_rho_bg=float(target_rho_bg),
            background_capacity_mbps=float(background_capacity_mbps),
            policy=mapping_policy.background,
        )
        for target_rho_pdb in rho_pdb_values:
            for pdb_ms in pdb_ms_values:
                pdb_mapping = solve_pdb_mapping(
                    target_rho_pdb=float(target_rho_pdb),
                    pdb_ms=int(pdb_ms),
                    pdb_capacity_mbps=float(pdb_capacity_mbps),
                    policy=mapping_policy.pdb,
                )
                prb_share_pdb = (
                    pdb_mapping.actual_rho_pdb / (background_mapping.actual_rho_bg + pdb_mapping.actual_rho_pdb)
                    if (background_mapping.actual_rho_bg + pdb_mapping.actual_rho_pdb) > 0.0
                    else 0.0
                )
                cases.append(
                    LoadRatioCase(
                        case_label=f"L{case_index:02d}",
                        background_user_count=background_mapping.background_user_count,
                        background_packet_kb=background_mapping.background_packet_kb,
                        background_period_ms=background_mapping.background_period_ms,
                        pdb_user_count=pdb_mapping.pdb_user_count,
                        pdb_packet_kb=pdb_mapping.pdb_packet_kb,
                        pdb_ms=pdb_mapping.pdb_ms,
                        target_rho_bg=float(target_rho_bg),
                        target_rho_pdb=float(target_rho_pdb),
                        actual_rho_bg=background_mapping.actual_rho_bg,
                        actual_rho_pdb=pdb_mapping.actual_rho_pdb,
                        rho_bg=background_mapping.actual_rho_bg,
                        rho_pdb=pdb_mapping.actual_rho_pdb,
                        prb_share_pdb=prb_share_pdb,
                        g_pdb_mbps=(float(pdb_mapping.pdb_packet_kb) * 8.0) / float(pdb_mapping.pdb_ms),
                        background_mapping_policy=background_mapping.mapping_policy,
                        pdb_mapping_policy=pdb_mapping.mapping_policy,
                    )
                )
                case_index += 1
    return cases


def load_ratio_cases(
    *,
    rho_bg_values: list[float] | None = None,
    rho_pdb_values: list[float] | None = None,
    pdb_ms_values: list[int] | None = None,
    background_capacity_mbps: float,
    pdb_capacity_mbps: float,
    mapping_policy: LoadRatioMappingPolicy | None = None,
    background_user_count: int | None = None,
    background_period_ms: int | None = None,
    background_packet_kb_values: list[float] | None = None,
    pdb_user_count: int | None = None,
    pdb_shapes: list[dict[str, object]] | None = None,
) -> list[LoadRatioCase]:
    uses_rho_first = (
        rho_bg_values is not None
        or rho_pdb_values is not None
        or pdb_ms_values is not None
        or mapping_policy is not None
    )
    if uses_rho_first:
        if rho_bg_values is None or rho_pdb_values is None or pdb_ms_values is None or mapping_policy is None:
            raise ValueError("rho-first load-ratio scans require rho_bg_values, rho_pdb_values, pdb_ms_values, and mapping_policy")
        return _rho_first_load_ratio_cases(
            rho_bg_values=[float(value) for value in rho_bg_values],
            rho_pdb_values=[float(value) for value in rho_pdb_values],
            pdb_ms_values=[int(value) for value in pdb_ms_values],
            background_capacity_mbps=float(background_capacity_mbps),
            pdb_capacity_mbps=float(pdb_capacity_mbps),
            mapping_policy=mapping_policy,
        )
    if (
        background_user_count is None
        or background_period_ms is None
        or background_packet_kb_values is None
        or pdb_user_count is None
        or pdb_shapes is None
    ):
        raise ValueError(
            "legacy load-ratio scans require background_user_count, background_period_ms, background_packet_kb_values, pdb_user_count, and pdb_shapes"
        )
    return _legacy_load_ratio_cases(
        background_user_count=int(background_user_count),
        background_period_ms=int(background_period_ms),
        background_packet_kb_values=[float(value) for value in background_packet_kb_values],
        pdb_user_count=int(pdb_user_count),
        pdb_shapes=list(pdb_shapes),
        background_capacity_mbps=float(background_capacity_mbps),
        pdb_capacity_mbps=float(pdb_capacity_mbps),
    )


def _has_non_blank_value(row: dict[str, object], field_name: str) -> bool:
    if field_name not in row:
        return False
    value = row[field_name]
    if isinstance(value, str):
        return value.strip() != ""
    return True


def _has_load_ratio_key_fields(row: dict[str, object]) -> bool:
    return _has_non_blank_value(row, "background_packet_kb") and _has_non_blank_value(row, "background_period_ms")


def scene_key(
    row: dict[str, float | int | str],
) -> tuple[int, int, int, int] | tuple[int, int, int, float, float, int]:
    has_background_packet_kb = _has_non_blank_value(row, "background_packet_kb")
    has_background_period_ms = _has_non_blank_value(row, "background_period_ms")
    if has_background_packet_kb and has_background_period_ms:
        return (
            int(row["background_user_count"]),
            int(row["pdb_user_count"]),
            int(row["pdb_ms"]),
            float(row["pdb_packet_kb"]),
            float(row["background_packet_kb"]),
            int(row["background_period_ms"]),
        )
    if has_background_packet_kb or has_background_period_ms:
        raise ValueError("load-ratio rows require both background_packet_kb and background_period_ms")
    return (
        int(row["background_user_count"]),
        int(row["pdb_user_count"]),
        int(row["pdb_ms"]),
        int(row["pdb_packet_kb"]),
    )


def scene_key_set(
    rows: list[dict[str, float | int | str]],
) -> set[tuple[int, int, int, int] | tuple[int, int, int, float, float, int]]:
    return {scene_key(row) for row in rows}


def load_ratio_scene_key(case: LoadRatioCase) -> tuple[int, int, int, float, float, int]:
    return (
        int(case.background_user_count),
        int(case.pdb_user_count),
        int(case.pdb_ms),
        float(case.pdb_packet_kb),
        float(case.background_packet_kb),
        int(case.background_period_ms),
    )


def _case_metadata(case: SystematicCase | LoadRatioCase) -> dict[str, float | int | str]:
    metadata: dict[str, float | int | str] = {
        "background_user_count": int(case.background_user_count),
        "pdb_user_count": int(case.pdb_user_count),
        "pdb_ms": int(case.pdb_ms),
        "pdb_packet_kb": float(case.pdb_packet_kb) if isinstance(case, LoadRatioCase) else int(case.pdb_packet_kb),
    }
    if isinstance(case, LoadRatioCase):
        metadata.update(
            {
                "case_label": str(case.case_label),
                "background_packet_kb": float(case.background_packet_kb),
                "background_period_ms": int(case.background_period_ms),
                "rho_bg": float(case.rho_bg),
                "rho_pdb": float(case.rho_pdb),
                "prb_share_pdb": float(case.prb_share_pdb),
                "g_pdb_mbps": float(case.g_pdb_mbps),
            }
        )
    return metadata


def _row_metadata(
    row: dict[str, float | int | str],
    *,
    case_label_override: str | None = None,
) -> dict[str, float | int | str]:
    has_load_ratio_fields = _has_load_ratio_key_fields(row)
    metadata: dict[str, float | int | str] = {
        "background_user_count": int(row["background_user_count"]),
        "pdb_user_count": int(row["pdb_user_count"]),
        "pdb_ms": int(row["pdb_ms"]),
        "pdb_packet_kb": float(row["pdb_packet_kb"]) if has_load_ratio_fields else int(row["pdb_packet_kb"]),
    }
    if case_label_override is not None:
        metadata["case_label"] = str(case_label_override)
    elif _has_non_blank_value(row, "case_label"):
        metadata["case_label"] = str(row["case_label"])
    if has_load_ratio_fields:
        metadata.update(
            {
                "background_packet_kb": float(row["background_packet_kb"]),
                "background_period_ms": int(row["background_period_ms"]),
            }
        )
        for field_name in ("rho_bg", "rho_pdb", "prb_share_pdb", "g_pdb_mbps"):
            if _has_non_blank_value(row, field_name):
                metadata[field_name] = float(row[field_name])
    return metadata


def merge_row_sets(
    *,
    existing_rows: list[dict[str, float | int | str]],
    new_rows: list[dict[str, float | int | str]],
) -> list[dict[str, float | int | str]]:
    return [*existing_rows, *new_rows]


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
    case: SystematicCase | LoadRatioCase,
    summary: dict[str, float],
) -> dict[str, float | int | str]:
    return {
        "seed": int(seed),
        "scenario_id": scenario_id,
        "policy": str(policy),
        **_case_metadata(case),
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
    case: SystematicCase | LoadRatioCase,
    seed: int,
    baseline_summary: dict[str, float],
    proposed_summary: dict[str, float],
) -> dict[str, float | int | str]:
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
        **_case_metadata(case),
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


_TYPICAL_CASE_DETAIL_METRICS = (
    "edge_pdb_satisfaction_rate",
    "center_agg_rate_bps",
    "center_avg_rate_bps",
    "prb_utilization",
    "center_prb_share",
    "edge_prb_share",
    "pdb_arrivals_in_window",
    "pdb_violation_rate",
    "target_edge_completion_delay_ms",
    "target_edge_queue_wait_ms",
    "target_edge_service_time_ms",
    "edge_backlog_bits",
)


def aggregate_scene_rows(
    paired_rows: list[dict[str, float | int | str]],
) -> list[dict[str, float | int | str]]:
    grouped: dict[
        tuple[int, int, int, int] | tuple[int, int, int, float, float, int],
        list[dict[str, float | int | str]],
    ] = {}
    for row in paired_rows:
        key = scene_key(row)
        grouped.setdefault(key, []).append(row)
    aggregated: list[dict[str, float | int | str]] = []
    for key, group in sorted(grouped.items()):
        delta_values = [float(row["delta_pdb_satisfaction_rate"]) for row in group]
        retention_values = [float(row["center_throughput_retention"]) for row in group]
        delta_prb_values = [float(row["delta_prb_utilization"]) for row in group]
        delta_center_share_values = [float(row["delta_center_prb_share"]) for row in group]
        delta_edge_share_values = [float(row["delta_edge_prb_share"]) for row in group]
        baseline_values = [float(row["baseline_edge_pdb_satisfaction_rate"]) for row in group]
        proposed_values = [float(row["proposed_edge_pdb_satisfaction_rate"]) for row in group]
        aggregated_row = {
            **_row_metadata(group[0]),
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
        aggregated.append(aggregated_row)
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
    seen_keys: set[tuple[int, int, int, int] | tuple[int, int, int, float, float, int]] = set()
    for label, row in selections:
        key = scene_key(row)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        selected_row = {
            **_row_metadata(row, case_label_override=label),
            "baseline_edge_pdb_satisfaction_rate": float(row["baseline_edge_pdb_satisfaction_rate"]),
            "proposed_edge_pdb_satisfaction_rate": float(row["proposed_edge_pdb_satisfaction_rate"]),
            "mean_delta_pdb_satisfaction_rate": float(row["mean_delta_pdb_satisfaction_rate"]),
            "mean_center_throughput_retention": float(row["mean_center_throughput_retention"]),
        }
        deduped.append(selected_row)
    return deduped


def build_typical_case_detail_rows(
    scene_rows: list[dict[str, float | int]],
    per_run_rows: list[dict[str, float | int | str]],
    baseline_policy: str,
    proposed_policy: str,
) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    grouped: dict[
        tuple[str, int, int, int, int]
        | tuple[str, int, int, int, float, float, int],
        list[dict[str, float | int | str]],
    ] = {}
    for row in per_run_rows:
        scene_identity = scene_key(row)
        key = (str(row["policy"]), *scene_identity)
        grouped.setdefault(key, []).append(row)

    for case_row in select_typical_case_rows(scene_rows):
        background_user_count = int(case_row["background_user_count"])
        pdb_user_count = int(case_row["pdb_user_count"])
        pdb_ms = int(case_row["pdb_ms"])
        pdb_packet_kb = int(case_row["pdb_packet_kb"])
        scene_identity = scene_key(case_row)
        case_groups: dict[str, list[dict[str, float | int | str]]] = {}
        for policy in (baseline_policy, proposed_policy):
            group = grouped.get((policy, *scene_identity), [])
            if not group:
                raise ValueError(
                    "missing policy "
                    f"{policy} for representative case "
                    f"bg={background_user_count} "
                    f"pdb_users={pdb_user_count} "
                    f"pdb_ms={pdb_ms} "
                    f"pdb_kb={pdb_packet_kb}"
                )
            case_groups[policy] = group
        for policy in (baseline_policy, proposed_policy):
            detail_row = {
                **_row_metadata(case_row),
                "case_label": str(case_row["case_label"]),
                "policy": str(policy),
            }
            for metric in _TYPICAL_CASE_DETAIL_METRICS:
                detail_row[metric] = _mean([float(row[metric]) for row in case_groups[policy]])
            rows.append(detail_row)
    return rows


def build_boundary_feasibility_rows(
    scene_rows: list[dict[str, float | int]],
    threshold: float,
) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    for row in scene_rows:
        boundary_row = {
            **_row_metadata(row),
            "threshold": float(threshold),
            "baseline_feasible": int(float(row["baseline_edge_pdb_satisfaction_rate"]) >= threshold),
            "proposed_feasible": int(float(row["proposed_edge_pdb_satisfaction_rate"]) >= threshold),
        }
        rows.append(boundary_row)
    return rows


def capacity_summary_rows(
    scene_rows: list[dict[str, float | int | str]],
    *,
    threshold: float,
) -> list[dict[str, float | int | str]]:
    if any(_has_load_ratio_key_fields(row) for row in scene_rows):
        return []

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
