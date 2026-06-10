from dataclasses import dataclass, field


@dataclass
class Packet:
    packet_id: str
    arrival_time: int
    size_bits: int
    remaining_bits: int
    pdb_ms: int | None
    completion_time: int | None
    eligible_cycle: int = 0
    is_target: bool = False
    first_service_time: int | None = None
    service_slot_count: int = 0
    served_bits: int = 0
    control_slot_count_while_pending: int = 0
    waiting_u_slot_count_before_first_service: int = 0
    waiting_u_slot_count_after_first_service: int = 0


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
        packet = self.packets.pop(0)
        if self.head_packet is not None:
            self.eligible_cycle = self.head_packet.eligible_cycle
        return packet


@dataclass(frozen=True)
class RadioProfile:
    user_class: str = "center"
    base_snr_db: float = 0.0
    snr_min_db: float = 0.0
    snr_max_db: float = 0.0
    distance_to_bs_m: float = 0.0
    edge_per_u_slot_prb_cap: int | None = None
    bits_per_prb: int = 0
    per_u_slot_prb_cap: int = 0


@dataclass(frozen=True)
class CurrentRadioState:
    snr_db: float
    mcs_index: int
    bits_per_prb: int
    per_u_slot_prb_cap: int | None


@dataclass(frozen=True)
class TrafficProfile:
    packet_bits: int
    pdb_ms: int | None
    period_slots: int | None = None
    burst_cycle_interval: int | None = None
    gbr_bps: float = 0.0
    arrival_mode: str = "single_burst"
    initial_phase_mode: str = "none"


@dataclass
class UserEquipment:
    ue_id: str
    lc: LogicalChannel
    is_edge_user: bool
    radio_profile: RadioProfile
    average_throughput: float
    traffic_profile: "TrafficProfile | None" = None
    current_radio_state: CurrentRadioState | None = None
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
