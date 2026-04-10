from scheduling_sim.models import UserEquipment
from scheduling_sim.queue import ActiveQueue


class TailAppendPolicy:
    def apply(
        self,
        queue: ActiveQueue,
        ue: UserEquipment,
        queue_wait_size: int,
        service_bits_per_decision: int,
        now_ms: int,
        current_phase: str,
        max_ue_per_slot: int,
    ) -> None:
        queue.append_tail(ue)


class ConstrainedInsertPolicy:
    def apply(
        self,
        queue: ActiveQueue,
        ue: UserEquipment,
        queue_wait_size: int,
        service_bits_per_decision: int,
        now_ms: int,
        current_phase: str,
        max_ue_per_slot: int,
    ) -> None:
        if self._tail_is_safe(
            ue,
            queue_wait_size,
            service_bits_per_decision,
            now_ms,
            current_phase,
            max_ue_per_slot,
        ):
            queue.append_tail(ue)
            return
        queue.insert_at(min(max_ue_per_slot - 1, max(queue_wait_size - 1, 0)), ue)

    def _tail_is_safe(
        self,
        ue: UserEquipment,
        queue_wait_size: int,
        service_bits_per_decision: int,
        now_ms: int,
        current_phase: str,
        max_ue_per_slot: int,
    ) -> bool:
        head = ue.lc.head_packet
        if head is None:
            return True
        decisions_until_candidate = queue_wait_size // max_ue_per_slot
        wait_ms = self._decision_wait_ms(current_phase, decisions_until_candidate)
        bits_after_current_cycle = max(head.remaining_bits - service_bits_per_decision, 0)
        extra_cycles = 0 if service_bits_per_decision <= 0 else -(-bits_after_current_cycle // service_bits_per_decision)
        completion_ms = now_ms + wait_ms + (extra_cycles * 5)
        deadline_ms = head.arrival_time + head.pdb_ms
        return completion_ms <= deadline_ms

    def _decision_wait_ms(self, current_phase: str, decision_hops: int) -> int:
        if decision_hops <= 0:
            return 0
        gaps = [1, 4] if current_phase == "D" else [4, 1]
        total = 0
        for index in range(decision_hops):
            total += gaps[index % 2]
        return total
