from scheduling_sim.models import Packet, UserEquipment
from scheduling_sim.planning import PhasePrbPlanner
from scheduling_sim.queue import ActiveQueue
from scheduling_sim.ranking import EpfRankingPolicy
from scheduling_sim.reinsert import ConstrainedInsertPolicy, TailAppendPolicy, TargetOnlyConstrainedInsertPolicy
from scheduling_sim.wireless_env import McsEntryView, StableWirelessEnv, WirelessEnvConfigView


class UlSimulator:
    def __init__(self, config, users, metrics, wireless_env=None, diagnostic_collector=None) -> None:
        self.config = config
        self.users = users
        self.metrics = metrics
        self.queue = ActiveQueue()
        self.ranking = EpfRankingPolicy()
        self.diagnostic_collector = diagnostic_collector
        self.planner = PhasePrbPlanner(config.resources.total_prb_per_u_slot)
        deadline_guard_ms = int(getattr(config.simulation, "deadline_guard_ms", 0))
        if config.scheduler.reinsert_policy == "tail_append":
            self.reinsert = TailAppendPolicy()
        elif config.scheduler.reinsert_policy == "target_only_constrained_insert":
            self.reinsert = TargetOnlyConstrainedInsertPolicy(deadline_guard_ms=deadline_guard_ms)
        else:
            self.reinsert = ConstrainedInsertPolicy(deadline_guard_ms=deadline_guard_ms)
        self._wireless_env_injected = wireless_env is not None
        self.wireless_env = wireless_env or self._build_wireless_env()
        reset_users = self.users if self._wireless_env_injected else self._dynamic_radio_users()
        if self.wireless_env is not None and reset_users and hasattr(self.wireless_env, "reset"):
            self.wireless_env.reset(reset_users)
        self._cycle_served_bits_by_ue = {user.ue_id: 0 for user in self.users}

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
                scenario_type=str(getattr(env_config, "scenario_type", "legacy")),
                cell_radius_m=float(getattr(env_config, "cell_radius_m", 0.0)),
                carrier_frequency_ghz=float(getattr(env_config, "carrier_frequency_ghz", 0.0)),
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
        if getattr(radio_profile, "distance_to_bs_m", 0.0) > 0.0:
            return True
        required_attrs = ("base_snr_db", "snr_min_db", "snr_max_db")
        if not all(hasattr(radio_profile, attr) for attr in required_attrs):
            return False
        looks_legacy_fixed_rate = (
            getattr(radio_profile, "bits_per_prb", None) is not None
            and getattr(radio_profile, "base_snr_db", 0.0) == 0.0
            and getattr(radio_profile, "snr_min_db", 0.0) == 0.0
            and getattr(radio_profile, "snr_max_db", 0.0) == 0.0
            and getattr(radio_profile, "distance_to_bs_m", 0.0) == 0.0
        )
        return not looks_legacy_fixed_rate

    def seed_active_queue(self, cycle_index: int) -> None:
        for user in self.users:
            head_packet = user.lc.head_packet
            head_eligible_cycle = (
                head_packet.eligible_cycle
                if head_packet is not None
                else user.lc.eligible_cycle
            )
            user.lc.eligible_cycle = head_eligible_cycle
            if head_packet is not None and head_eligible_cycle <= cycle_index:
                self.queue.activate(user)
            elif self.queue.contains(user) and (head_packet is None or head_eligible_cycle > cycle_index):
                self.queue.deactivate(user)

    def inject_packet(self, user, packet_bits: int, cycle_index: int, slot_name: str, is_target: bool = False) -> None:
        eligible_cycle = cycle_index + 1 if slot_name.startswith("U") else cycle_index
        head_before_arrival = user.lc.head_packet
        packet = Packet(
            packet_id=f"{user.ue_id}-{cycle_index}-{slot_name}",
            arrival_time=cycle_index * 5,
            size_bits=packet_bits,
            remaining_bits=packet_bits,
            pdb_ms=user.traffic_profile.pdb_ms,
            completion_time=None,
            eligible_cycle=eligible_cycle,
            is_target=is_target,
        )
        user.lc.packets.append(packet)
        user.lc.eligible_cycle = (
            eligible_cycle
            if head_before_arrival is None
            else head_before_arrival.eligible_cycle
        )

    def collect_candidates(self, phase: str):
        return self.queue.peek_head_k(self.config.resources.max_ue_per_slot)

    def finish_phase(self, phase: str, now_ms: int = 0, slot_index: int = 0):
        if self.wireless_env is not None and phase in {"D", "S"}:
            refresh_users = self.users if self._wireless_env_injected else self._dynamic_radio_users()
            if refresh_users:
                self.wireless_env.refresh_slot(refresh_users, slot_index=slot_index, slot_name=phase)
        candidates = self.collect_candidates(phase)
        ranked = self.ranking.rank(candidates)
        if self.diagnostic_collector is not None:
            self.diagnostic_collector.capture(
                queue=self.queue,
                candidates=candidates,
                ranked=ranked,
                ranking_policy=self.ranking,
                time_ms=now_ms,
                phase=phase,
            )
        plan = self.planner.plan_phase(phase, ranked)
        for user in candidates:
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
        total_prb_available = 0
        total_prb_used = 0
        self._preload_initial_backlog()
        slots_per_cycle = len(self.config.simulation.tdd_pattern)
        simulation_duration_ms = (
            self.config.simulation.cycles
            * len(self.config.simulation.tdd_pattern)
            * self.config.simulation.slot_duration_ms
        )
        should_stop = False
        for cycle_index in range(self.config.simulation.cycles):
            self.seed_active_queue(cycle_index)
            cycle_start_ms = cycle_index * len(self.config.simulation.tdd_pattern) * self.config.simulation.slot_duration_ms
            self._refresh_hol(cycle_start_ms)
            self._track_target_control_slot()
            d_plan = self.finish_phase(
                "D",
                now_ms=cycle_start_ms,
                slot_index=cycle_index * slots_per_cycle,
            )
            self._refresh_hol(cycle_start_ms + self.config.simulation.slot_duration_ms)
            self._track_target_control_slot()
            s_plan = self.finish_phase(
                "S",
                now_ms=cycle_start_ms + self.config.simulation.slot_duration_ms,
                slot_index=cycle_index * slots_per_cycle + 1,
            )
            for u_slot_index in range(3):
                now_ms = cycle_start_ms + (2 + u_slot_index) * self.config.simulation.slot_duration_ms
                total_prb_available += self.config.resources.total_prb_per_u_slot
                total_prb_used += self._execute_u_slot(
                    cycle_index=cycle_index,
                    slot_index=u_slot_index,
                    now_ms=now_ms,
                    d_plan=d_plan,
                    s_plan=s_plan,
                )
                self._inject_u_slot_arrivals(cycle_index, u_slot_index)
                self.seed_active_queue(cycle_index + 1)
                if self._should_stop_after_target_edge_finished():
                    simulation_duration_ms = now_ms + self.config.simulation.slot_duration_ms
                    should_stop = True
                    break
            self._close_cycle_average_throughput()
            if should_stop:
                break
        self._refresh_hol(simulation_duration_ms)
        return self.metrics.build_summary(
            total_prb_used=total_prb_used,
            total_prb_available=total_prb_available,
            users=self.users,
            simulation_duration_ms=simulation_duration_ms,
            slot_duration_ms=self.config.simulation.slot_duration_ms,
            tdd_pattern=self.config.simulation.tdd_pattern,
        )

    def _should_stop_after_target_edge_finished(self) -> bool:
        if not getattr(self.config.simulation, "stop_when_target_edge_finished", False):
            return False
        completed_packets = getattr(self.metrics, "completed_packets", [])
        return any(bool(packet.get("is_target")) for packet in completed_packets)

    def _preload_initial_backlog(self) -> None:
        target_edge_marked = False
        for user in self.users:
            profile = user.traffic_profile
            if profile is None:
                continue
            is_target = user.is_edge_user and not target_edge_marked
            self.inject_packet(
                user,
                profile.packet_bits,
                cycle_index=0,
                slot_name="D",
                is_target=is_target,
            )
            if is_target:
                target_edge_marked = True

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
        grant_bits_by_user, prb_count_by_user = self._merge_u_slot_grants(slot_index, d_plan, s_plan)
        self._track_target_u_slot_wait(grant_bits_by_user)
        for user in self.users:
            bits_budget = grant_bits_by_user.get(user.ue_id, 0)
            prb_count = prb_count_by_user.get(user.ue_id, 0)
            if prb_count > 0 and hasattr(self.metrics, "record_prb_used"):
                self.metrics.record_prb_used(
                    user_class="edge" if user.is_edge_user else "center",
                    prb_count=prb_count,
                )
            if bits_budget <= 0:
                continue
            self._consume_user_bits(user, bits_budget, now_ms)
        self._refresh_hol(now_ms)
        self.seed_active_queue(cycle_index)
        return sum(prb_count_by_user.values())

    def _find_target_packet(self) -> tuple[UserEquipment | None, Packet | None]:
        for user in self.users:
            head_packet = user.lc.head_packet
            if head_packet is not None and head_packet.is_target:
                return user, head_packet
        return None, None

    def _track_target_control_slot(self) -> None:
        _, packet = self._find_target_packet()
        if packet is None:
            return
        packet.control_slot_count_while_pending += 1

    def _track_target_u_slot_wait(self, grant_bits_by_user: dict[str, int]) -> None:
        target_user, packet = self._find_target_packet()
        if target_user is None or packet is None:
            return
        if grant_bits_by_user.get(target_user.ue_id, 0) > 0:
            return
        if packet.first_service_time is None:
            packet.waiting_u_slot_count_before_first_service += 1
            return
        packet.waiting_u_slot_count_after_first_service += 1

    def _merge_u_slot_grants(self, slot_index: int, d_plan, s_plan) -> tuple[dict[str, int], dict[str, int]]:
        grant_bits_by_user: dict[str, int] = {}
        prb_count_by_user: dict[str, int] = {}
        for plan in (d_plan, s_plan):
            for grant in plan.slot_grants.get(slot_index, []):
                grant_bits_by_user[grant.ue_id] = grant_bits_by_user.get(grant.ue_id, 0) + grant.bits_planned
                prb_count_by_user[grant.ue_id] = prb_count_by_user.get(grant.ue_id, 0) + grant.prb_count
        for user in self.users:
            total_prbs = prb_count_by_user.get(user.ue_id, 0)
            if total_prbs <= 0 or not user.is_edge_user:
                continue
            current_state = user.current_radio_state
            cap = (
                current_state.per_u_slot_prb_cap
                if current_state is not None
                else user.radio_profile.per_u_slot_prb_cap
            )
            if cap is None or total_prbs <= cap:
                continue
            bits_per_prb = (
                current_state.bits_per_prb
                if current_state is not None
                else user.radio_profile.bits_per_prb
            )
            prb_count_by_user[user.ue_id] = cap
            grant_bits_by_user[user.ue_id] = cap * bits_per_prb
        return grant_bits_by_user, prb_count_by_user

    def _consume_user_bits(self, user: UserEquipment, bits_budget: int, now_ms: int) -> None:
        remaining_budget = bits_budget
        user_class = "edge" if user.is_edge_user else "center"
        while remaining_budget > 0 and user.lc.head_packet is not None:
            packet = user.lc.head_packet
            bits_sent = min(packet.remaining_bits, remaining_budget)
            if bits_sent > 0:
                if packet.first_service_time is None:
                    packet.first_service_time = now_ms
                packet.service_slot_count += 1
                packet.served_bits += bits_sent
            packet.remaining_bits -= bits_sent
            remaining_budget -= bits_sent
            if hasattr(self.metrics, "record_bits_served"):
                self.metrics.record_bits_served(
                    user_class=user_class,
                    bits_sent=bits_sent,
                    ue_id=user.ue_id,
                )
            if bits_sent > 0:
                self._record_cycle_service(user.ue_id, bits_sent)
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
                    user_class=user_class,
                    ue_id=user.ue_id,
                    is_target=completed.is_target,
                    first_service_time=completed.first_service_time,
                    service_slot_count=completed.service_slot_count,
                    control_slot_count_while_pending=completed.control_slot_count_while_pending,
                    waiting_u_slot_count_before_first_service=completed.waiting_u_slot_count_before_first_service,
                    waiting_u_slot_count_after_first_service=completed.waiting_u_slot_count_after_first_service,
                )
        if user.lc.head_packet is None and self.queue.contains(user):
            self.queue.deactivate(user)

    def _record_cycle_service(self, ue_id: str, bits_sent: int) -> None:
        self._cycle_served_bits_by_ue[ue_id] = self._cycle_served_bits_by_ue.get(ue_id, 0) + bits_sent

    def _close_cycle_average_throughput(self) -> None:
        cycle_duration_seconds = (
            len(self.config.simulation.tdd_pattern) * self.config.simulation.slot_duration_ms / 1000.0
        )
        if cycle_duration_seconds <= 0:
            return
        beta = min(1.0, max(0.0, float(getattr(self.config.simulation, "avg_rate_ewma_beta", 0.9))))
        for user in self.users:
            cycle_rate_bps = self._cycle_served_bits_by_ue.get(user.ue_id, 0) / cycle_duration_seconds
            user.average_throughput = (beta * user.average_throughput) + ((1.0 - beta) * cycle_rate_bps)
            self._cycle_served_bits_by_ue[user.ue_id] = 0

    def _refresh_hol(self, now_ms: int) -> None:
        for user in self.users:
            head = user.lc.head_packet
            user.hol_ms = 0 if head is None else max(0, now_ms - head.arrival_time)
