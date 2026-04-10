from scheduling_sim.models import Packet, UserEquipment
from scheduling_sim.planning import PhasePrbPlanner
from scheduling_sim.queue import ActiveQueue
from scheduling_sim.ranking import EpfRankingPolicy
from scheduling_sim.reinsert import ConstrainedInsertPolicy, TailAppendPolicy
from scheduling_sim.wireless_env import McsEntryView, StableWirelessEnv, WirelessEnvConfigView


class UlSimulator:
    def __init__(self, config, users, metrics, wireless_env=None) -> None:
        self.config = config
        self.users = users
        self.metrics = metrics
        self.queue = ActiveQueue()
        self.ranking = EpfRankingPolicy()
        self.planner = PhasePrbPlanner(config.resources.total_prb_per_u_slot)
        self.reinsert = (
            TailAppendPolicy()
            if config.scheduler.reinsert_policy == "tail_append"
            else ConstrainedInsertPolicy()
        )
        self._wireless_env_injected = wireless_env is not None
        self.wireless_env = wireless_env or self._build_wireless_env()
        reset_users = self.users if self._wireless_env_injected else self._dynamic_radio_users()
        if self.wireless_env is not None and reset_users and hasattr(self.wireless_env, "reset"):
            self.wireless_env.reset(reset_users)

    def _build_wireless_env(self):
        radio_section = getattr(self.config, "radio", None)
        env_config = getattr(radio_section, "environment", None)
        mcs_table = getattr(env_config, "mcs_table", None) if env_config is not None else None
        if not mcs_table or not self._dynamic_radio_users():
            return None
        seed = getattr(self.config.simulation, "random_seed", 0)
        return StableWirelessEnv(
            WirelessEnvConfigView(
                alpha=float(getattr(env_config, "alpha", 1.0)),
                jitter_std_db=float(getattr(env_config, "jitter_std_db", 0.0)),
                mcs_table=[
                    McsEntryView(
                        snr_db=float(entry.snr_db),
                        mcs_index=int(entry.mcs_index),
                        bits_per_prb=int(entry.bits_per_prb),
                    )
                    for entry in mcs_table
                ],
                seed=seed,
            )
        )

    def _dynamic_radio_users(self) -> list[UserEquipment]:
        return [user for user in self.users if self._is_dynamic_radio_profile(user.radio_profile)]

    @staticmethod
    def _is_dynamic_radio_profile(radio_profile) -> bool:
        if radio_profile is None:
            return False
        required_attrs = ("base_snr_db", "snr_min_db", "snr_max_db")
        if not all(hasattr(radio_profile, attr) for attr in required_attrs):
            return False
        looks_legacy_fixed_rate = (
            getattr(radio_profile, "bits_per_prb", None) is not None
            and getattr(radio_profile, "base_snr_db", 0.0) == 0.0
            and getattr(radio_profile, "snr_min_db", 0.0) == 0.0
            and getattr(radio_profile, "snr_max_db", 0.0) == 0.0
        )
        return not looks_legacy_fixed_rate

    def seed_active_queue(self, cycle_index: int) -> None:
        for user in self.users:
            if user.lc.head_packet is not None and user.lc.eligible_cycle <= cycle_index:
                self.queue.activate(user)
            elif self.queue.contains(user) and (
                user.lc.head_packet is None or user.lc.eligible_cycle > cycle_index
            ):
                self.queue.deactivate(user)

    def inject_packet(self, user, packet_bits: int, cycle_index: int, slot_name: str) -> None:
        packet = Packet(
            packet_id=f"{user.ue_id}-{cycle_index}-{slot_name}",
            arrival_time=cycle_index * 5,
            size_bits=packet_bits,
            remaining_bits=packet_bits,
            pdb_ms=user.traffic_profile.pdb_ms,
            completion_time=None,
        )
        user.lc.packets.append(packet)
        user.lc.eligible_cycle = cycle_index + 1 if slot_name.startswith("U") else cycle_index

    def collect_candidates(self, phase: str):
        return self.queue.peek_head_k(self.config.resources.max_ue_per_slot)

    def finish_phase(self, phase: str, now_ms: int = 0, slot_index: int = 0):
        if self.wireless_env is not None and phase in {"D", "S"}:
            refresh_users = self.users if self._wireless_env_injected else self._dynamic_radio_users()
            if refresh_users:
                self.wireless_env.refresh_slot(refresh_users, slot_index=slot_index, slot_name=phase)
        candidates = self.collect_candidates(phase)
        ranked = self.ranking.rank(candidates)
        plan = self.planner.plan_phase(phase, ranked)
        for user in ranked:
            service_bits = sum(
                grant.bits_planned
                for slot_grants in plan.slot_grants.values()
                for grant in slot_grants
                if grant.ue_id == user.ue_id
            )
            self.reinsert.apply(
                self.queue,
                user,
                queue_wait_size=self.queue.size,
                service_bits_per_decision=service_bits,
                now_ms=now_ms,
                current_phase=phase,
                max_ue_per_slot=self.config.resources.max_ue_per_slot,
            )
        return plan

    def run(self) -> dict[str, float]:
        total_prb_available = self.config.simulation.cycles * 3 * self.config.resources.total_prb_per_u_slot
        total_prb_used = 0
        self._preload_initial_backlog()
        slots_per_cycle = len(self.config.simulation.tdd_pattern)
        for cycle_index in range(self.config.simulation.cycles):
            self.seed_active_queue(cycle_index)
            cycle_start_ms = cycle_index * len(self.config.simulation.tdd_pattern) * self.config.simulation.slot_duration_ms
            self._refresh_hol(cycle_start_ms)
            d_plan = self.finish_phase(
                "D",
                now_ms=cycle_start_ms,
                slot_index=cycle_index * slots_per_cycle,
            )
            self._refresh_hol(cycle_start_ms + self.config.simulation.slot_duration_ms)
            s_plan = self.finish_phase(
                "S",
                now_ms=cycle_start_ms + self.config.simulation.slot_duration_ms,
                slot_index=cycle_index * slots_per_cycle + 1,
            )
            for u_slot_index in range(3):
                total_prb_used += self._execute_u_slot(
                    cycle_index=cycle_index,
                    slot_index=u_slot_index,
                    now_ms=cycle_start_ms + (2 + u_slot_index) * self.config.simulation.slot_duration_ms,
                    d_plan=d_plan,
                    s_plan=s_plan,
                )
                self._inject_u_slot_arrivals(cycle_index, u_slot_index)
                self.seed_active_queue(cycle_index + 1)
        return self.metrics.build_summary(
            total_prb_used=total_prb_used,
            total_prb_available=total_prb_available,
        )

    def _preload_initial_backlog(self) -> None:
        for user in self.users:
            profile = user.traffic_profile
            if profile is None:
                continue
            self.inject_packet(user, profile.packet_bits, cycle_index=0, slot_name="D")

    def _inject_u_slot_arrivals(self, cycle_index: int, u_slot_index: int) -> None:
        global_slot = cycle_index * 3 + u_slot_index
        for user in self.users:
            profile = user.traffic_profile
            if profile is None:
                continue
            if user.is_edge_user:
                if profile.burst_cycle_interval and (cycle_index + 1) % profile.burst_cycle_interval == 0 and u_slot_index == 0:
                    self.inject_packet(user, profile.packet_bits, cycle_index=cycle_index, slot_name=f"U{u_slot_index + 1}")
            elif profile.period_slots and global_slot % profile.period_slots == 0:
                self.inject_packet(user, profile.packet_bits, cycle_index=cycle_index, slot_name=f"U{u_slot_index + 1}")

    def _execute_u_slot(self, cycle_index: int, slot_index: int, now_ms: int, d_plan, s_plan) -> int:
        grant_bits_by_user: dict[str, int] = {}
        prb_count_by_user: dict[str, int] = {}
        for plan in (d_plan, s_plan):
            for grant in plan.slot_grants.get(slot_index, []):
                grant_bits_by_user[grant.ue_id] = grant_bits_by_user.get(grant.ue_id, 0) + grant.bits_planned
                prb_count_by_user[grant.ue_id] = prb_count_by_user.get(grant.ue_id, 0) + grant.prb_count
        for user in self.users:
            bits_budget = grant_bits_by_user.get(user.ue_id, 0)
            if bits_budget <= 0:
                continue
            self._consume_user_bits(user, bits_budget, now_ms)
        self._refresh_hol(now_ms)
        self.seed_active_queue(cycle_index)
        return sum(prb_count_by_user.values())

    def _consume_user_bits(self, user: UserEquipment, bits_budget: int, now_ms: int) -> None:
        remaining_budget = bits_budget
        while remaining_budget > 0 and user.lc.head_packet is not None:
            packet = user.lc.head_packet
            bits_sent = min(packet.remaining_bits, remaining_budget)
            packet.remaining_bits -= bits_sent
            remaining_budget -= bits_sent
            user.average_throughput = max(1.0, float(bits_sent))
            if packet.remaining_bits > 0:
                break
            packet.completion_time = now_ms
            completed = user.lc.pop_head_packet()
            if completed is not None and hasattr(self.metrics, "record_packet_completed"):
                self.metrics.record_packet_completed(
                    packet_id=completed.packet_id,
                    completion_time=completed.completion_time or now_ms,
                    arrival_time=completed.arrival_time,
                    pdb_ms=completed.pdb_ms,
                    bits_sent=completed.size_bits,
                )
        if user.lc.head_packet is None and self.queue.contains(user):
            self.queue.deactivate(user)

    def _refresh_hol(self, now_ms: int) -> None:
        for user in self.users:
            head = user.lc.head_packet
            user.hol_ms = 0 if head is None else max(0, now_ms - head.arrival_time)
