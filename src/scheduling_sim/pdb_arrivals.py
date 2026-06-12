import random


def resolve_analysis_window_ms(config) -> int:
    simulation = getattr(config, "simulation", None)
    explicit_window_ms = getattr(simulation, "analysis_window_ms", None)
    if explicit_window_ms is not None:
        return int(explicit_window_ms)
    traffic = getattr(config, "traffic", None)
    edge_profile = getattr(traffic, "edge", None)
    if getattr(edge_profile, "arrival_mode", "single_burst") == "periodic_by_pdb":
        return 10000
    cycles = getattr(simulation, "cycles", None)
    tdd_pattern = getattr(simulation, "tdd_pattern", None)
    slot_duration_ms = getattr(simulation, "slot_duration_ms", None)
    if cycles is None or tdd_pattern is None or slot_duration_ms is None:
        return 0
    return int(cycles * len(tdd_pattern) * slot_duration_ms)


def build_periodic_pdb_schedule(users, random_seed: int, analysis_window_ms: int) -> dict[str, list[int]]:
    schedule_by_ue: dict[str, list[int]] = {}
    for user in users:
        profile = getattr(user, "traffic_profile", None)
        if (
            not user.is_edge_user
            or profile is None
            or profile.arrival_mode != "periodic_by_pdb"
            or profile.pdb_ms is None
            or profile.pdb_ms <= 0
        ):
            continue
        if profile.initial_phase_mode == "uniform_0_to_pdb":
            first_offset_ms = random.Random(f"{random_seed}:{user.ue_id}").randrange(profile.pdb_ms)
        else:
            first_offset_ms = 0
        schedule_by_ue[user.ue_id] = list(range(first_offset_ms, analysis_window_ms, profile.pdb_ms))
    return schedule_by_ue


def resolve_periodic_runtime_ms(base_runtime_ms: int, users, analysis_window_ms: int) -> int:
    periodic_pdb_values = [
        int(user.traffic_profile.pdb_ms)
        for user in users
        if user.is_edge_user
        and getattr(user, "traffic_profile", None) is not None
        and user.traffic_profile.arrival_mode == "periodic_by_pdb"
        and user.traffic_profile.pdb_ms is not None
    ]
    if not periodic_pdb_values:
        return base_runtime_ms
    return max(base_runtime_ms, int(analysis_window_ms) + max(periodic_pdb_values))
