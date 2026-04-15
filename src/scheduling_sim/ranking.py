from scheduling_sim.models import UserEquipment


class EpfRankingPolicy:
    def rank(self, users: list[UserEquipment]) -> list[UserEquipment]:
        return sorted(users, key=self._weight, reverse=True)

    def _weight(self, ue: UserEquipment) -> float:
        head = ue.lc.head_packet
        if head is None:
            return 0.0
        inst_rate = (
            ue.current_radio_state.bits_per_prb
            if ue.current_radio_state is not None
            else ue.radio_profile.bits_per_prb
        )
        avg_rate = max(ue.average_throughput, 1.0)
        if head.pdb_ms is None:
            return inst_rate / avg_rate
        if ue.hol_ms >= head.pdb_ms:
            return 100.0
        hol_factor = ue.hol_ms / max(1, head.pdb_ms - ue.hol_ms)
        return (inst_rate / avg_rate) * hol_factor
