from scheduling_sim.models import Packet
from scheduling_sim.planning import PhasePrbPlanner
from scheduling_sim.queue import ActiveQueue
from scheduling_sim.ranking import EpfRankingPolicy
from scheduling_sim.reinsert import ConstrainedInsertPolicy, TailAppendPolicy


class UlSimulator:
    def __init__(self, config, users, metrics) -> None:
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

    def seed_active_queue(self) -> None:
        for user in self.users:
            if user.lc.head_packet is not None and user.lc.eligible_cycle <= 0:
                self.queue.activate(user)

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

    def finish_phase(self, phase: str):
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
                now_ms=0,
                current_phase=phase,
                max_ue_per_slot=self.config.resources.max_ue_per_slot,
            )
        return plan
