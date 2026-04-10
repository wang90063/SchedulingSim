from scheduling_sim.config import AppConfig
from scheduling_sim.models import LogicalChannel, RadioProfile, TrafficProfile, UserEquipment


class ScenarioFactory:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def build_users(self) -> list[UserEquipment]:
        users: list[UserEquipment] = []
        for index in range(self.config.traffic.center.count):
            users.append(
                UserEquipment(
                    ue_id=f"center-{index}",
                    lc=LogicalChannel(lc_id=f"center-{index}-lc", packets=[], eligible_cycle=0),
                    is_edge_user=False,
                    radio_profile=RadioProfile(
                        bits_per_prb=self.config.radio.center.bits_per_prb,
                        per_u_slot_prb_cap=self.config.radio.center.per_u_slot_prb_cap,
                    ),
                    average_throughput=1.0,
                    traffic_profile=TrafficProfile(
                        packet_bits=self.config.traffic.center.packet_bits,
                        pdb_ms=self.config.traffic.center.pdb_ms,
                        period_slots=self.config.traffic.center.period_slots,
                    ),
                )
            )
        for index in range(self.config.traffic.edge.count):
            users.append(
                UserEquipment(
                    ue_id=f"edge-{index}",
                    lc=LogicalChannel(lc_id=f"edge-{index}-lc", packets=[], eligible_cycle=0),
                    is_edge_user=True,
                    radio_profile=RadioProfile(
                        bits_per_prb=self.config.radio.edge.bits_per_prb,
                        per_u_slot_prb_cap=self.config.radio.edge.per_u_slot_prb_cap,
                    ),
                    average_throughput=1.0,
                    traffic_profile=TrafficProfile(
                        packet_bits=self.config.traffic.edge.packet_bits,
                        pdb_ms=self.config.traffic.edge.pdb_ms,
                        burst_cycle_interval=self.config.traffic.edge.burst_cycle_interval,
                    ),
                )
            )
        return users
