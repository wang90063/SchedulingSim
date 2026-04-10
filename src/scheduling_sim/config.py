import json
from dataclasses import dataclass, field
from pathlib import Path

UNCAPPED_PRB_LIMIT = 10**9


@dataclass(frozen=True)
class TrafficConfig:
    count: int
    packet_bits: int
    pdb_ms: int
    period_slots: int | None = None
    burst_cycle_interval: int | None = None


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


@dataclass(frozen=True)
class McsEntryConfig:
    snr_db: float
    mcs_index: int
    bits_per_prb: int


@dataclass(frozen=True)
class WirelessEnvConfig:
    alpha: float
    jitter_std_db: float
    mcs_table: list[McsEntryConfig]


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
        default_factory=lambda: WirelessEnvConfig(alpha=1.0, jitter_std_db=0.0, mcs_table=[])
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
        edge_per_u_slot_prb_cap=int(payload.get("per_u_slot_prb_cap", UNCAPPED_PRB_LIMIT)),  # type: ignore[arg-type]
        bits_per_prb=resolved_bits_per_prb,
    )


def _load_wireless_env_config(payload: dict[str, object]) -> WirelessEnvConfig:
    if not payload:
        return WirelessEnvConfig(alpha=1.0, jitter_std_db=0.0, mcs_table=[])
    mcs_table = sorted(
        (McsEntryConfig(**entry) for entry in payload["mcs_table"]),  # type: ignore[index]
        key=lambda entry: entry.snr_db,
    )
    return WirelessEnvConfig(
        alpha=float(payload["alpha"]),
        jitter_std_db=float(payload["jitter_std_db"]),
        mcs_table=mcs_table,
    )


def load_config(path: Path) -> AppConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    radio_payload = payload["radio"]
    env_payload = radio_payload.get("environment", {})
    wireless_env_config = _load_wireless_env_config(env_payload)
    return AppConfig(
        simulation=SimulationConfig(**payload["simulation"]),
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
