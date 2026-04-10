from dataclasses import dataclass, field


@dataclass
class Packet:
    packet_id: str
    arrival_time: int
    size_bits: int
    remaining_bits: int
    pdb_ms: int
    completion_time: int | None


@dataclass
class LogicalChannel:
    lc_id: str
    packets: list[Packet] = field(default_factory=list)
    eligible_cycle: int = 0

    @property
    def head_packet(self) -> Packet | None:
        return self.packets[0] if self.packets else None

    @property
    def has_pending_data(self) -> bool:
        return self.head_packet is not None

    def pop_head_packet(self) -> Packet | None:
        if not self.packets:
            return None
        return self.packets.pop(0)


@dataclass(frozen=True)
class RadioProfile:
    bits_per_prb: int
    per_u_slot_prb_cap: int


@dataclass(frozen=True)
class TrafficProfile:
    packet_bits: int
    pdb_ms: int
    period_slots: int | None = None
    burst_cycle_interval: int | None = None


@dataclass
class UserEquipment:
    ue_id: str
    lc: LogicalChannel
    is_edge_user: bool
    radio_profile: RadioProfile
    average_throughput: float
    traffic_profile: "TrafficProfile | None" = None
    hol_ms: int = 0


@dataclass
class SchedulingGrant:
    ue_id: str
    slot_index: int
    prb_count: int
    bits_planned: int


@dataclass
class PhasePlan:
    phase: str
    slot_prb_budgets: list[int]
    slot_grants: dict[int, list[SchedulingGrant]]
