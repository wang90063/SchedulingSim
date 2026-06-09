from __future__ import annotations

import copy
import random
from dataclasses import dataclass, is_dataclass, replace


@dataclass(frozen=True)
class TrafficArrival:
    ue_id: str
    slot_index: int
    packet_bits: int
    pdb_ms: int | None
    is_planned_pdb: bool = False


@dataclass(frozen=True)
class SingleShotArrivalPlan:
    arrival_slot_by_ue: dict[str, int]
    planned_arrivals_by_slot: dict[int, list[TrafficArrival]]
    planned_pdb_total_count: int


def scanned_pdb_user_count(*, total_users: int, pdb_user_ratio_pct: int) -> int:
    return int(total_users * pdb_user_ratio_pct / 100.0 + 0.5)


def selection_seed(*, random_seed_base: int, total_users: int, pdb_user_ratio_pct: int, repeat_index: int) -> int:
    return (
        int(random_seed_base) * 1_000_000_000_000
        + int(total_users) * 1_000_000
        + int(pdb_user_ratio_pct) * 1_000
        + int(repeat_index)
    )


def arrival_seed(*, random_seed_base: int, total_users: int, pdb_user_ratio_pct: int, repeat_index: int) -> int:
    return selection_seed(
        random_seed_base=random_seed_base,
        total_users=total_users,
        pdb_user_ratio_pct=pdb_user_ratio_pct,
        repeat_index=repeat_index,
    ) + 1


def build_case_config(base_config, *, total_users: int, policy: str):
    return replace(
        base_config,
        scheduler=replace(base_config.scheduler, reinsert_policy=policy),
        traffic=replace(
            base_config.traffic,
            center=replace(base_config.traffic.center, count=total_users),
            edge=replace(base_config.traffic.edge, count=0),
        ),
    )


def select_pdb_user_ids(users, *, pdb_user_ratio_pct: int, seed: int) -> list[str]:
    user_ids = [user.ue_id for user in users]
    selected_count = min(len(user_ids), scanned_pdb_user_count(total_users=len(user_ids), pdb_user_ratio_pct=pdb_user_ratio_pct))
    if selected_count <= 0:
        return []
    rng = random.Random(seed)
    return rng.sample(user_ids, selected_count)


def _rewrite_single_shot_profile(profile, *, packet_bits: int, pdb_ms: int):
    def _set_extra_attr(obj, name: str, value) -> None:
        object.__setattr__(obj, name, value)

    if is_dataclass(profile):
        updated_profile = replace(
            profile,
            packet_bits=packet_bits,
            pdb_ms=pdb_ms,
            period_slots=None,
            burst_cycle_interval=None,
        )
    else:
        updated_profile = copy.copy(profile)
        setattr(updated_profile, "packet_bits", packet_bits)
        setattr(updated_profile, "pdb_ms", pdb_ms)
        setattr(updated_profile, "period_slots", None)
        setattr(updated_profile, "burst_cycle_interval", None)
    _set_extra_attr(updated_profile, "arrival_model", "scheduled")
    _set_extra_attr(updated_profile, "total_lambda_per_slot", None)
    return updated_profile


def apply_single_shot_pdb_profiles(users, *, selected_ue_ids: set[str], packet_bits: int, pdb_ms: int) -> None:
    for user in users:
        if user.ue_id not in selected_ue_ids or user.traffic_profile is None:
            continue
        user.traffic_profile = _rewrite_single_shot_profile(user.traffic_profile, packet_bits=packet_bits, pdb_ms=pdb_ms)


def build_single_shot_arrival_plan(
    config,
    users_by_id: dict[str, object],
    *,
    selected_ue_ids: list[str],
    packet_bits: int,
    seed: int,
):
    total_slots = max(1, int(config.simulation.cycles) * len(str(config.simulation.tdd_pattern)))
    rng = random.Random(seed)
    arrival_slot_by_ue: dict[str, int] = {}
    planned_arrivals_by_slot: dict[int, list[TrafficArrival]] = {}

    for ue_id in selected_ue_ids:
        user = users_by_id[ue_id]
        profile = getattr(user, "traffic_profile", None)
        if profile is None:
            raise ValueError(f"user {ue_id!r} has no traffic profile")
        slot_index = rng.randrange(total_slots)
        arrival_slot_by_ue[ue_id] = slot_index
        arrival = TrafficArrival(
            ue_id=ue_id,
            slot_index=slot_index,
            packet_bits=packet_bits,
            pdb_ms=getattr(profile, "pdb_ms", None),
            is_planned_pdb=True,
        )
        planned_arrivals_by_slot.setdefault(slot_index, []).append(arrival)

    return SingleShotArrivalPlan(
        arrival_slot_by_ue=arrival_slot_by_ue,
        planned_arrivals_by_slot=planned_arrivals_by_slot,
        planned_pdb_total_count=len(arrival_slot_by_ue),
    )


class PlannedArrivalOverlay:
    def __init__(self, config, users, planned_arrivals_by_slot):
        self.config = config
        self.users = list(users)
        self.planned_arrivals_by_slot = {
            int(slot_index): list(arrivals) for slot_index, arrivals in planned_arrivals_by_slot.items()
        }

    @property
    def planned_pdb_total_count(self) -> int:
        return sum(len(arrivals) for arrivals in self.planned_arrivals_by_slot.values())

    def _slot_coordinates(self, global_slot: int) -> tuple[int, int]:
        pattern_length = max(1, len(str(self.config.simulation.tdd_pattern)))
        return divmod(int(global_slot), pattern_length)

    def _fallback_arrivals_for_slot(self, global_slot: int) -> list[TrafficArrival]:
        cycle_index, u_slot_index = self._slot_coordinates(global_slot)
        arrivals: list[TrafficArrival] = []
        for user in self.users:
            profile = getattr(user, "traffic_profile", None)
            if profile is None:
                continue
            if getattr(user, "is_edge_user", False):
                burst_cycle_interval = getattr(profile, "burst_cycle_interval", None)
                if burst_cycle_interval and (cycle_index + 1) % int(burst_cycle_interval) == 0 and u_slot_index == 0:
                    arrivals.append(
                        TrafficArrival(
                            ue_id=user.ue_id,
                            slot_index=global_slot,
                            packet_bits=int(getattr(profile, "packet_bits", 0)),
                            pdb_ms=getattr(profile, "pdb_ms", None),
                            is_planned_pdb=False,
                        )
                    )
            else:
                period_slots = getattr(profile, "period_slots", None)
                if period_slots and global_slot % int(period_slots) == 0:
                    arrivals.append(
                        TrafficArrival(
                            ue_id=user.ue_id,
                            slot_index=global_slot,
                            packet_bits=int(getattr(profile, "packet_bits", 0)),
                            pdb_ms=getattr(profile, "pdb_ms", None),
                            is_planned_pdb=False,
                        )
                    )
        return arrivals

    def arrivals_for_slot(self, *args, **kwargs) -> list[TrafficArrival]:
        if "global_slot" in kwargs:
            global_slot = int(kwargs["global_slot"])
        elif "slot_index" in kwargs and "cycle_index" in kwargs:
            global_slot = int(kwargs["cycle_index"]) * max(1, len(str(self.config.simulation.tdd_pattern))) + int(kwargs["slot_index"])
        elif len(args) == 1:
            global_slot = int(args[0])
        elif len(args) == 2:
            global_slot = int(args[0]) * max(1, len(str(self.config.simulation.tdd_pattern))) + int(args[1])
        else:
            raise TypeError("arrivals_for_slot() expects a global slot or cycle/slot coordinates")

        arrivals = self._fallback_arrivals_for_slot(global_slot)
        arrivals.extend(self.planned_arrivals_by_slot.get(global_slot, []))
        return arrivals
