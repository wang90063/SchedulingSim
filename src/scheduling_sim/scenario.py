import random

from scheduling_sim.config import AppConfig
from scheduling_sim.models import CurrentRadioState, LogicalChannel, RadioProfile, TrafficProfile, UserEquipment


class ScenarioFactory:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def _build_radio_profile(self, radio_class_config, user_class: str, is_edge_user: bool, index: int) -> RadioProfile:
        bits_per_prb = getattr(radio_class_config, "bits_per_prb", 0) or 0
        per_u_slot_prb_cap = getattr(radio_class_config, "per_u_slot_prb_cap", 0) or 0
        return RadioProfile(
            user_class=user_class,
            base_snr_db=getattr(radio_class_config, "base_snr_db", 0.0),
            snr_min_db=getattr(radio_class_config, "snr_min_db", 0.0),
            snr_max_db=getattr(radio_class_config, "snr_max_db", 0.0),
            distance_to_bs_m=self._sample_distance(is_edge_user=is_edge_user, index=index),
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

    def _sample_distance(self, is_edge_user: bool, index: int) -> float:
        env = self.config.radio.environment
        if env.scenario_type != "uma":
            return 0.0
        low, high = env.edge_distance_range_m if is_edge_user else env.center_distance_range_m
        if low == 0.0 and high == 0.0:
            return 0.0
        offset = 10_000 if is_edge_user else 0
        rng = random.Random(self.config.simulation.random_seed + offset + index)
        return rng.uniform(low, high)

    def build_users(self) -> list[UserEquipment]:
        users: list[UserEquipment] = []
        for index in range(self.config.traffic.center.count):
            center_profile = self._build_radio_profile(
                self.config.radio.center,
                user_class="center",
                is_edge_user=False,
                index=index,
            )
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
                        gbr_bps=self.config.traffic.center.gbr_bps,
                        arrival_mode=self.config.traffic.center.arrival_mode,
                        initial_phase_mode=self.config.traffic.center.initial_phase_mode,
                    ),
                    current_radio_state=self._initial_radio_state(center_profile, is_edge_user=False),
                )
            )
        for index in range(self.config.traffic.edge.count):
            edge_profile = self._build_radio_profile(
                self.config.radio.edge,
                user_class="edge",
                is_edge_user=True,
                index=index,
            )
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
                        arrival_mode=self.config.traffic.edge.arrival_mode,
                        initial_phase_mode=self.config.traffic.edge.initial_phase_mode,
                    ),
                    current_radio_state=self._initial_radio_state(edge_profile, is_edge_user=True),
                )
            )
        return users
