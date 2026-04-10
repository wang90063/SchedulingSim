from scheduling_sim.config import AppConfig
from scheduling_sim.models import CurrentRadioState, LogicalChannel, RadioProfile, TrafficProfile, UserEquipment


class ScenarioFactory:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    @staticmethod
    def _build_radio_profile(radio_class_config, user_class: str) -> RadioProfile:
        bits_per_prb = getattr(radio_class_config, "bits_per_prb", 0) or 0
        per_u_slot_prb_cap = getattr(radio_class_config, "per_u_slot_prb_cap", 0) or 0
        return RadioProfile(
            user_class=user_class,
            base_snr_db=getattr(radio_class_config, "base_snr_db", 0.0),
            snr_min_db=getattr(radio_class_config, "snr_min_db", 0.0),
            snr_max_db=getattr(radio_class_config, "snr_max_db", 0.0),
            edge_per_u_slot_prb_cap=getattr(radio_class_config, "edge_per_u_slot_prb_cap", None),
            bits_per_prb=bits_per_prb,
            per_u_slot_prb_cap=per_u_slot_prb_cap,
        )

    @staticmethod
    def _initial_radio_state(profile: RadioProfile, is_edge_user: bool) -> CurrentRadioState:
        initial_snr = min(profile.snr_max_db, max(profile.snr_min_db, profile.base_snr_db))
        prb_cap = None
        if is_edge_user:
            prb_cap = (
                profile.edge_per_u_slot_prb_cap
                if profile.edge_per_u_slot_prb_cap is not None
                else profile.per_u_slot_prb_cap
            )
        return CurrentRadioState(
            snr_db=initial_snr,
            mcs_index=0,
            bits_per_prb=profile.bits_per_prb,
            per_u_slot_prb_cap=prb_cap,
        )

    def build_users(self) -> list[UserEquipment]:
        users: list[UserEquipment] = []
        for index in range(self.config.traffic.center.count):
            center_profile = self._build_radio_profile(self.config.radio.center, user_class="center")
            users.append(
                UserEquipment(
                    ue_id=f"center-{index}",
                    lc=LogicalChannel(lc_id=f"center-{index}-lc", packets=[], eligible_cycle=0),
                    is_edge_user=False,
                    radio_profile=center_profile,
                    average_throughput=1.0,
                    traffic_profile=TrafficProfile(
                        packet_bits=self.config.traffic.center.packet_bits,
                        pdb_ms=self.config.traffic.center.pdb_ms,
                        period_slots=self.config.traffic.center.period_slots,
                    ),
                    current_radio_state=self._initial_radio_state(center_profile, is_edge_user=False),
                )
            )
        for index in range(self.config.traffic.edge.count):
            edge_profile = self._build_radio_profile(self.config.radio.edge, user_class="edge")
            users.append(
                UserEquipment(
                    ue_id=f"edge-{index}",
                    lc=LogicalChannel(lc_id=f"edge-{index}-lc", packets=[], eligible_cycle=0),
                    is_edge_user=True,
                    radio_profile=edge_profile,
                    average_throughput=1.0,
                    traffic_profile=TrafficProfile(
                        packet_bits=self.config.traffic.edge.packet_bits,
                        pdb_ms=self.config.traffic.edge.pdb_ms,
                        burst_cycle_interval=self.config.traffic.edge.burst_cycle_interval,
                    ),
                    current_radio_state=self._initial_radio_state(edge_profile, is_edge_user=True),
                )
            )
        return users
