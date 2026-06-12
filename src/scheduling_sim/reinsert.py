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
    def __init__(self, deadline_guard_ms: int = 0) -> None:
        self.deadline_guard_ms = max(0, int(deadline_guard_ms))

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
        tail_index = max(queue_wait_size - 1, 0)
        if self._position_is_safe(
            ue,
            queue_index=tail_index,
            service_bits_per_decision=service_bits_per_decision,
            now_ms=now_ms,
            current_phase=current_phase,
            max_ue_per_slot=max_ue_per_slot,
        ):
            queue.append_tail(ue)
            return
        for queue_index in range(tail_index, -1, -1):
            if self._position_is_safe(
                ue,
                queue_index=queue_index,
                service_bits_per_decision=service_bits_per_decision,
                now_ms=now_ms,
                current_phase=current_phase,
                max_ue_per_slot=max_ue_per_slot,
            ):
                queue.insert_at(queue_index, ue)
                return
        queue.insert_at(min(max_ue_per_slot - 1, tail_index), ue)

    def _position_is_safe(
        self,
        ue: UserEquipment,
        queue_index: int,
        service_bits_per_decision: int,
        now_ms: int,
        current_phase: str,
        max_ue_per_slot: int,
    ) -> bool:
        head = ue.lc.head_packet
        if head is None:
            return True
        if head.pdb_ms is None:
            return True
        decisions_until_candidate = queue_index // max_ue_per_slot
        wait_ms = self._decision_wait_ms(current_phase, decisions_until_candidate)
        bits_after_current_cycle = max(head.remaining_bits - service_bits_per_decision, 0)
        extra_cycles = 0 if service_bits_per_decision <= 0 else -(-bits_after_current_cycle // service_bits_per_decision)
        completion_ms = now_ms + wait_ms + (extra_cycles * 5)
        deadline_ms = head.arrival_time + head.pdb_ms
        safe_deadline_ms = deadline_ms - self.deadline_guard_ms
        return completion_ms <= safe_deadline_ms

    def _decision_wait_ms(self, current_phase: str, decision_hops: int) -> int:
        if decision_hops <= 0:
            return 0
        gaps = [1, 4] if current_phase == "D" else [4, 1]
        total = 0
        for index in range(decision_hops):
            total += gaps[index % 2]
        return total


class TargetOnlyConstrainedInsertPolicy:
    def __init__(self, deadline_guard_ms: int = 0) -> None:
        self._tail = TailAppendPolicy()
        self._constrained = ConstrainedInsertPolicy(deadline_guard_ms=deadline_guard_ms)

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
        head = ue.lc.head_packet
        if head is None or not getattr(head, "is_target", False):
            self._tail.apply(
                queue,
                ue,
                queue_wait_size=queue_wait_size,
                service_bits_per_decision=service_bits_per_decision,
                now_ms=now_ms,
                current_phase=current_phase,
                max_ue_per_slot=max_ue_per_slot,
            )
            return
        self._constrained.apply(
            queue,
            ue,
            queue_wait_size=queue_wait_size,
            service_bits_per_decision=service_bits_per_decision,
            now_ms=now_ms,
            current_phase=current_phase,
            max_ue_per_slot=max_ue_per_slot,
        )


class HopelessFrontInsertPolicy(ConstrainedInsertPolicy):
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
        tail_index = max(queue_wait_size - 1, 0)
        if self._position_is_safe(
            ue,
            queue_index=tail_index,
            service_bits_per_decision=service_bits_per_decision,
            now_ms=now_ms,
            current_phase=current_phase,
            max_ue_per_slot=max_ue_per_slot,
        ):
            queue.append_tail(ue)
            return
        for queue_index in range(tail_index, -1, -1):
            if self._position_is_safe(
                ue,
                queue_index=queue_index,
                service_bits_per_decision=service_bits_per_decision,
                now_ms=now_ms,
                current_phase=current_phase,
                max_ue_per_slot=max_ue_per_slot,
            ):
                queue.insert_at(queue_index, ue)
                return
        queue.insert_at(0, ue)
