from scheduling_sim.models import UserEquipment


class ActiveQueue:
    def __init__(self) -> None:
        self._users: list[UserEquipment] = []

    @property
    def size(self) -> int:
        return len(self._users)

    def activate(self, ue: UserEquipment) -> None:
        if ue not in self._users:
            self._users.append(ue)

    def deactivate(self, ue: UserEquipment) -> None:
        if ue in self._users:
            self._users.remove(ue)

    def peek_head_k(self, k: int) -> list[UserEquipment]:
        return self._users[:k]

    def append_tail(self, ue: UserEquipment) -> None:
        self.deactivate(ue)
        self._users.append(ue)

    def insert_at(self, index: int, ue: UserEquipment) -> None:
        self.deactivate(ue)
        self._users.insert(index, ue)
