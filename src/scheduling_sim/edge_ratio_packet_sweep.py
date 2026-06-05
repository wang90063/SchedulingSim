import random
from dataclasses import replace


def packet_bits_from_kb(packet_kb: int) -> int:
    return int(packet_kb) * 1000 * 8


def scanned_edge_user_count(total_users: int, requested_edge_ratio_pct: int) -> int:
    return int(total_users * requested_edge_ratio_pct / 100.0 + 0.5)


def build_case_config(
    base_config,
    *,
    total_users: int,
    requested_edge_ratio_pct: int,
    pdb_packet_kb: int,
    policy: str,
):
    edge_count = scanned_edge_user_count(
        total_users=total_users,
        requested_edge_ratio_pct=requested_edge_ratio_pct,
    )
    center_count = total_users - edge_count
    return replace(
        base_config,
        scheduler=replace(base_config.scheduler, reinsert_policy=policy),
        traffic=replace(
            base_config.traffic,
            center=replace(base_config.traffic.center, count=center_count),
            edge=replace(
                base_config.traffic.edge,
                count=edge_count,
                packet_bits=packet_bits_from_kb(pdb_packet_kb),
            ),
        ),
    )


def random_pdb_by_ue(*, edge_ids: list[str], pdb_choices: list[int | None], seed: int) -> dict[str, int | None]:
    rng = random.Random(seed)
    return {ue_id: rng.choice(pdb_choices) for ue_id in edge_ids}


def uniform_pdb_by_ue(*, edge_ids: list[str], pdb_ms: int) -> dict[str, int | None]:
    return {ue_id: int(pdb_ms) for ue_id in edge_ids}


def apply_edge_pdb_assignments(users, pdb_by_ue: dict[str, int | None]) -> None:
    for user in users:
        if not user.is_edge_user or user.traffic_profile is None or user.ue_id not in pdb_by_ue:
            continue
        user.traffic_profile = replace(user.traffic_profile, pdb_ms=pdb_by_ue[user.ue_id])
