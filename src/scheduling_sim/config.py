import json
from dataclasses import dataclass
from pathlib import Path


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
    center: RadioConfig
    edge: RadioConfig


@dataclass(frozen=True)
class AppConfig:
    simulation: SimulationConfig
    resources: ResourcesConfig
    traffic: TrafficSection
    radio: RadioSection
    scheduler: SchedulerConfig
    report: ReportConfig


def load_config(path: Path) -> AppConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return AppConfig(
        simulation=SimulationConfig(**payload["simulation"]),
        resources=ResourcesConfig(**payload["resources"]),
        traffic=TrafficSection(
            center=TrafficConfig(**payload["traffic"]["center"]),
            edge=TrafficConfig(**payload["traffic"]["edge"]),
        ),
        radio=RadioSection(
            center=RadioConfig(**payload["radio"]["center"]),
            edge=RadioConfig(**payload["radio"]["edge"]),
        ),
        scheduler=SchedulerConfig(**payload["scheduler"]),
        report=ReportConfig(**payload["report"]),
    )
