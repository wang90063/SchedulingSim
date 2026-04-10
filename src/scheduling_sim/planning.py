from scheduling_sim.models import PhasePlan, SchedulingGrant, UserEquipment


class PhasePrbPlanner:
    def __init__(self, total_prb_per_u_slot: int) -> None:
        self.total_prb_per_u_slot = total_prb_per_u_slot

    def plan_phase(self, phase: str, ranked_users: list[UserEquipment]) -> PhasePlan:
        half = self.total_prb_per_u_slot // 2
        budgets = (
            [self.total_prb_per_u_slot, half, 0]
            if phase == "D"
            else [0, self.total_prb_per_u_slot - half, self.total_prb_per_u_slot]
        )
        slot_grants = {0: [], 1: [], 2: []}
        for slot_index, budget in enumerate(budgets):
            remaining = budget
            for user in ranked_users:
                if remaining <= 0:
                    break
                current_state = user.current_radio_state
                per_u_slot_prb_cap = None
                if user.is_edge_user:
                    per_u_slot_prb_cap = (
                        current_state.per_u_slot_prb_cap
                        if current_state is not None
                        else user.radio_profile.per_u_slot_prb_cap
                    )
                grant_prbs = remaining if per_u_slot_prb_cap is None else min(remaining, per_u_slot_prb_cap)
                if grant_prbs <= 0:
                    continue
                bits_per_prb = (
                    current_state.bits_per_prb
                    if current_state is not None
                    else user.radio_profile.bits_per_prb
                )
                slot_grants[slot_index].append(
                    SchedulingGrant(
                        ue_id=user.ue_id,
                        slot_index=slot_index,
                        prb_count=grant_prbs,
                        bits_planned=grant_prbs * bits_per_prb,
                    )
                )
                remaining -= grant_prbs
        return PhasePlan(phase=phase, slot_prb_budgets=budgets, slot_grants=slot_grants)
