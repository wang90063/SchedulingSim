import json
from dataclasses import dataclass, field
from pathlib import Path

UNCAPPED_PRB_LIMIT = 10**9
PRB_BANDWIDTH_HZ = 180_000


@dataclass(frozen=True)
class TrafficConfig:
    count: int
    packet_bits: int
    pdb_ms: int | None
    period_slots: int | None = None
    burst_cycle_interval: int | None = None
    gbr_bps: float = 0.0
    arrival_mode: str = "single_burst"
    initial_phase_mode: str = "none"


@dataclass(frozen=True)
class RadioConfig:
    bits_per_prb: int
    per_u_slot_prb_cap: int


@dataclass(frozen=True)
class SimulationConfig:
    cycles: int
    slot_duration_ms: int
    tdd_pattern: str
    random_seed: int = 0
    analysis_window_ms: int | None = None
    stop_when_target_edge_finished: bool = False
    deadline_guard_ms: int = 0
    avg_rate_ewma_beta: float = 0.9


@dataclass(frozen=True)
class McsEntryConfig:
    snr_db: float
    mcs_index: int
    bits_per_prb: int

    @property
    def sinr_db(self) -> float:
        return self.snr_db


@dataclass(frozen=True)
class WirelessEnvConfig:
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
    center_distance_range_m: tuple[float, float] = (0.0, 0.0)
    edge_distance_range_m: tuple[float, float] = (0.0, 0.0)
    mcs_table: list[McsEntryConfig] = field(default_factory=list)
    backend: str = "stable"
    sionna_nominal_re_per_user: int = 144


@dataclass(frozen=True)
class RadioClassConfig:
    base_snr_db: float
    snr_min_db: float
    snr_max_db: float
    edge_per_u_slot_prb_cap: int | None = None
    bits_per_prb: int | None = None

    @property
    def per_u_slot_prb_cap(self) -> int:
        return self.edge_per_u_slot_prb_cap if self.edge_per_u_slot_prb_cap is not None else UNCAPPED_PRB_LIMIT


@dataclass(frozen=True)
class ResourcesConfig:
    total_prb_per_u_slot: int
    max_ue_per_slot: int


@dataclass(frozen=True)
class SchedulerConfig:
    ranking: str
    reinsert_policy: str


@dataclass(frozen=True)
class ReportConfig:
    output_dir: str
    keep_slot_trace: bool


@dataclass(frozen=True)
class TrafficSection:
    center: TrafficConfig
    edge: TrafficConfig


@dataclass(frozen=True)
class RadioSection:
    environment: WirelessEnvConfig = field(
        default_factory=WirelessEnvConfig
    )
    center: RadioClassConfig = field(
        default_factory=lambda: RadioClassConfig(base_snr_db=0.0, snr_min_db=0.0, snr_max_db=0.0)
    )
    edge: RadioClassConfig = field(
        default_factory=lambda: RadioClassConfig(base_snr_db=0.0, snr_min_db=0.0, snr_max_db=0.0)
    )


@dataclass(frozen=True)
class AppConfig:
    simulation: SimulationConfig
    resources: ResourcesConfig
    traffic: TrafficSection
    radio: RadioSection
    scheduler: SchedulerConfig
    report: ReportConfig


def _resolve_bits_per_prb(
    payload: dict[str, object],
    env_config: WirelessEnvConfig,
) -> int | None:
    legacy_bits_per_prb = payload.get("bits_per_prb")
    if legacy_bits_per_prb is not None:
        return int(legacy_bits_per_prb)
    base_snr_db = payload.get("base_snr_db")
    if base_snr_db is None or not env_config.mcs_table:
        return None
    bits_per_prb = env_config.mcs_table[0].bits_per_prb
    for entry in env_config.mcs_table:
        if float(base_snr_db) >= entry.snr_db:
            bits_per_prb = entry.bits_per_prb
    return bits_per_prb


def _resolve_mcs_entry_bits_per_prb(entry: dict[str, object], *, slot_duration_ms: int) -> int:
    explicit_bits_per_prb = entry.get("bits_per_prb")
    if explicit_bits_per_prb is not None:
        return int(explicit_bits_per_prb)
    spectral_efficiency = entry.get("spectral_efficiency")
    if spectral_efficiency is None:
        raise KeyError("mcs entry requires bits_per_prb or spectral_efficiency")
    bits_per_prb = float(spectral_efficiency) * PRB_BANDWIDTH_HZ * (slot_duration_ms / 1000.0)
    return int(round(bits_per_prb))


def _load_mcs_table(
    payload: dict[str, object],
    *,
    config_dir: Path,
    slot_duration_ms: int,
) -> list[McsEntryConfig]:
    mcs_entries_payload = payload.get("mcs_table")
    if mcs_entries_payload is None and payload.get("mcs_table_path") is not None:
        table_path = config_dir / str(payload["mcs_table_path"])
        mcs_entries_payload = json.loads(table_path.read_text(encoding="utf-8"))
    return sorted(
        (
            McsEntryConfig(
                snr_db=float(entry.get("sinr_db", entry.get("snr_db", 0.0))),  # type: ignore[union-attr]
                mcs_index=int(entry["mcs_index"]),  # type: ignore[index]
                bits_per_prb=_resolve_mcs_entry_bits_per_prb(entry, slot_duration_ms=slot_duration_ms),  # type: ignore[arg-type]
            )
            for entry in (mcs_entries_payload or [])
        ),
        key=lambda entry: entry.snr_db,
    )


def _load_radio_class_config(
    payload: dict[str, object],
    env_config: WirelessEnvConfig,
) -> RadioClassConfig:
    resolved_bits_per_prb = _resolve_bits_per_prb(payload, env_config)
    if "base_snr_db" in payload:
        return RadioClassConfig(
            base_snr_db=float(payload["base_snr_db"]),
            snr_min_db=float(payload["snr_min_db"]),
            snr_max_db=float(payload["snr_max_db"]),
            edge_per_u_slot_prb_cap=payload.get("edge_per_u_slot_prb_cap"),  # type: ignore[arg-type]
            bits_per_prb=resolved_bits_per_prb,
        )
    return RadioClassConfig(
        base_snr_db=0.0,
        snr_min_db=0.0,
        snr_max_db=0.0,
        edge_per_u_slot_prb_cap=(
            int(payload["edge_per_u_slot_prb_cap"]) if "edge_per_u_slot_prb_cap" in payload else None
        ),
        bits_per_prb=resolved_bits_per_prb,
    )


def _load_wireless_env_config(
    payload: dict[str, object],
    *,
    config_dir: Path,
    slot_duration_ms: int,
) -> WirelessEnvConfig:
    if not payload:
        return WirelessEnvConfig()
    mcs_table = _load_mcs_table(payload, config_dir=config_dir, slot_duration_ms=slot_duration_ms)
    center_distance = payload.get("center_distance_range_m", (0.0, 0.0))
    edge_distance = payload.get("edge_distance_range_m", (0.0, 0.0))
    return WirelessEnvConfig(
        alpha=float(payload.get("alpha", payload.get("slow_fading_alpha", 1.0))),
        jitter_std_db=float(payload.get("jitter_std_db", payload.get("slot_jitter_std_db", 0.0))),
        scenario_type=str(payload.get("scenario_type", "legacy")),
        cell_radius_m=float(payload.get("cell_radius_m", 0.0)),
        carrier_frequency_ghz=float(payload.get("carrier_frequency_ghz", 0.0)),
        per_prb_tx_power_dbm=float(payload.get("per_prb_tx_power_dbm", 5.0)),
        noise_figure_db=float(payload.get("noise_figure_db", 0.0)),
        interference_margin_db=float(payload.get("interference_margin_db", 0.0)),
        shadow_std_db=float(payload.get("shadow_std_db", 0.0)),
        slow_fading_alpha=float(payload.get("slow_fading_alpha", payload.get("alpha", 1.0))),
        slot_jitter_std_db=float(payload.get("slot_jitter_std_db", payload.get("jitter_std_db", 0.0))),
        center_distance_range_m=(float(center_distance[0]), float(center_distance[1])),  # type: ignore[index]
        edge_distance_range_m=(float(edge_distance[0]), float(edge_distance[1])),  # type: ignore[index]
        mcs_table=mcs_table,
        backend=str(payload.get("backend", "stable")),
        sionna_nominal_re_per_user=int(payload.get("sionna_nominal_re_per_user", 144)),
    )


def load_config(path: Path) -> AppConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    simulation_config = SimulationConfig(**payload["simulation"])
    radio_payload = payload["radio"]
    env_payload = radio_payload.get("environment", {})
    wireless_env_config = _load_wireless_env_config(
        env_payload,
        config_dir=path.parent,
        slot_duration_ms=simulation_config.slot_duration_ms,
    )
    return AppConfig(
        simulation=simulation_config,
        resources=ResourcesConfig(**payload["resources"]),
        traffic=TrafficSection(
            center=TrafficConfig(**payload["traffic"]["center"]),
            edge=TrafficConfig(**payload["traffic"]["edge"]),
        ),
        radio=RadioSection(
            environment=wireless_env_config,
            center=_load_radio_class_config(radio_payload["center"], wireless_env_config),
            edge=_load_radio_class_config(radio_payload["edge"], wireless_env_config),
        ),
        scheduler=SchedulerConfig(**payload["scheduler"]),
        report=ReportConfig(**payload["report"]),
    )
