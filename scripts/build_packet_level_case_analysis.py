import csv
import json
import math
import sys
from dataclasses import replace
from pathlib import Path

from scheduling_sim.config import load_config
from scheduling_sim.metrics import MetricsCollector
from scheduling_sim.simulator import UlSimulator
from scheduling_sim.systematic_analysis import (
    BackgroundMappingPolicy,
    LoadRatioCase,
    LoadRatioMappingPolicy,
    PdbMappingPolicy,
    SceneBankSpec,
    build_realization_bank,
    build_systematic_case_users,
    load_ratio_cases,
)


BASELINE_POLICY = "tail_append"
PROPOSED_POLICY = "hopeless_tail_append"
TRANSITION_PREFIXES = (
    "rescued_baseline",
    "rescued_proposed",
    "harmed_baseline",
    "harmed_proposed",
)


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key in seen:
                continue
            seen.add(key)
            fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _mapping_policy(sweep: dict[str, object]) -> LoadRatioMappingPolicy:
    background = dict(sweep["mapping_policy"]["background"])  # type: ignore[index]
    pdb = dict(sweep["mapping_policy"]["pdb"])  # type: ignore[index]
    return LoadRatioMappingPolicy(
        background=BackgroundMappingPolicy(
            background_user_count_values=[
                int(value) for value in background["background_user_count_values"]  # type: ignore[index]
            ],
            background_packet_kb_values=[
                float(value) for value in background["background_packet_kb_values"]  # type: ignore[index]
            ],
            background_period_ms_range=tuple(
                float(value) for value in background["background_period_ms_range"]  # type: ignore[index]
            ),
            anchor_background_user_count=int(background["anchor_background_user_count"]),
            anchor_background_packet_kb=float(background["anchor_background_packet_kb"]),
            kind=str(background.get("kind", "candidate_domain_solve_period")),
        ),
        pdb=PdbMappingPolicy(
            pdb_user_count_values=[int(value) for value in pdb["pdb_user_count_values"]],  # type: ignore[index]
            pdb_packet_kb_range=tuple(float(value) for value in pdb["pdb_packet_kb_range"]),  # type: ignore[index]
            anchor_pdb_user_count=int(pdb["anchor_pdb_user_count"]),
            kind=str(pdb.get("kind", "candidate_domain_solve_packet")),
        ),
    )


def _all_cases(config_path: Path) -> list[LoadRatioCase]:
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    sweep = payload["systematic_analysis"]
    capacity = sweep["capacity_reference"]
    return load_ratio_cases(
        rho_bg_values=[float(value) for value in sweep["rho_bg_values"]],
        rho_pdb_values=[float(value) for value in sweep["rho_pdb_values"]],
        pdb_ms_values=[int(value) for value in sweep["pdb_ms_values"]],
        background_capacity_mbps=float(capacity["background_capacity_mbps"]),
        pdb_capacity_mbps=float(capacity["pdb_capacity_mbps"]),
        mapping_policy=_mapping_policy(sweep),
        explicit_background_user_count_values=[
            int(value) for value in sweep["background_user_count_values"]
        ],
        explicit_pdb_user_count_values=[int(value) for value in sweep["pdb_user_count_values"]],
    )


def _case_matches(row: dict[str, str], case: LoadRatioCase) -> bool:
    return (
        int(row["background_user_count"]) == int(case.background_user_count)
        and int(row["pdb_user_count"]) == int(case.pdb_user_count)
        and int(row["pdb_ms"]) == int(case.pdb_ms)
        and abs(float(row["pdb_packet_kb"]) - float(case.pdb_packet_kb)) < 1e-9
        and abs(float(row["target_rho_bg"]) - float(case.target_rho_bg)) < 1e-9
        and abs(float(row["target_rho_pdb"]) - float(case.target_rho_pdb)) < 1e-9
    )


def _case_for_row(row: dict[str, str], cases: list[LoadRatioCase]) -> LoadRatioCase:
    matches = [case for case in cases if _case_matches(row, case)]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one case for row, got {len(matches)}: {row}")
    return matches[0]


def _select_rows(scene_rows: list[dict[str, str]]) -> list[tuple[str, dict[str, str]]]:
    rows = list(scene_rows)
    for row in rows:
        row["_baseline"] = str(float(row["baseline_edge_pdb_satisfaction_rate"]))
        row["_delta"] = str(float(row["mean_delta_pdb_satisfaction_rate"]))

    def eligible_positive(row: dict[str, str]) -> bool:
        baseline = float(row["baseline_edge_pdb_satisfaction_rate"])
        delta = float(row["mean_delta_pdb_satisfaction_rate"])
        return delta > 0.0 and 0.50 <= baseline <= 0.95

    def eligible_negative(row: dict[str, str]) -> bool:
        baseline = float(row["baseline_edge_pdb_satisfaction_rate"])
        delta = float(row["mean_delta_pdb_satisfaction_rate"])
        return delta < 0.0 and 0.50 <= baseline <= 0.95

    selected: list[tuple[str, dict[str, str]]] = []
    selected.append(
        (
            "best_positive",
            max(rows, key=lambda row: float(row["mean_delta_pdb_satisfaction_rate"])),
        )
    )
    selected.append(
        (
            "positive_midband",
            max(
                [
                    row
                    for row in rows
                    if eligible_positive(row)
                    and float(row["target_rho_pdb"]) in {0.30, 0.40, 0.45}
                ],
                key=lambda row: float(row["mean_delta_pdb_satisfaction_rate"]),
            ),
        )
    )
    selected.append(
        (
            "negative_midband",
            min(
                [
                    row
                    for row in rows
                    if eligible_negative(row)
                    and float(row["target_rho_pdb"]) in {0.30, 0.40, 0.45}
                ],
                key=lambda row: float(row["mean_delta_pdb_satisfaction_rate"]),
            ),
        )
    )
    selected.append(
        (
            "easy",
            min(
                [
                    row
                    for row in rows
                    if float(row["target_rho_pdb"]) == 0.18
                    and float(row["baseline_edge_pdb_satisfaction_rate"]) >= 0.999
                ],
                key=lambda row: (
                    abs(float(row["target_rho_bg"]) - 0.20),
                    int(row["pdb_ms"]) != 100,
                    int(row["background_user_count"]) != 32,
                    int(row["pdb_user_count"]) != 4,
                ),
            ),
        )
    )
    selected.append(
        (
            "heavy_overload",
            min(
                [row for row in rows if float(row["target_rho_pdb"]) == 0.55],
                key=lambda row: float(row["baseline_edge_pdb_satisfaction_rate"]),
            ),
        )
    )
    return selected


def _completed_packet_map(collector: MetricsCollector) -> dict[str, dict[str, object]]:
    return {
        str(packet["packet_id"]): packet
        for packet in collector.completed_packets
        if packet.get("user_class") == "edge"
        and packet.get("pdb_ms") is not None
        and bool(packet.get("arrival_in_analysis_window", True))
    }


def _packet_ids_in_window(collector: MetricsCollector) -> set[str]:
    return set(collector.edge_pdb_arrivals_in_window_set)


def _run_case(
    *,
    base_config,
    scene_bank_spec: SceneBankSpec,
    case: LoadRatioCase,
    seed: int,
    policy: str,
):
    bank = build_realization_bank(base_config, scene_bank_spec=scene_bank_spec, bank_seed=seed)
    users = build_systematic_case_users(
        base_config,
        bank,
        background_user_count=case.background_user_count,
        pdb_user_count=case.pdb_user_count,
        pdb_ms=case.pdb_ms,
        pdb_packet_bits=int(round(float(case.pdb_packet_kb) * 1000.0 * 8.0)),
        background_packet_bits=int(round(float(case.background_packet_kb) * 1000.0 * 8.0)),
        background_period_ms=float(case.background_period_ms),
    )
    config = replace(
        base_config,
        scheduler=replace(base_config.scheduler, reinsert_policy=policy),
    )
    collector = MetricsCollector()
    summary = UlSimulator(config, users, collector).run()
    return summary, collector


def _safe_mean(values: list[float]) -> float:
    return float("nan") if not values else sum(values) / float(len(values))


def _metrics_for_packets(packet_ids: set[str], packet_map: dict[str, dict[str, object]]) -> dict[str, float]:
    waits: list[float] = []
    service_delays: list[float] = []
    airtimes: list[float] = []
    delays: list[float] = []
    for packet_id in sorted(packet_ids):
        packet = packet_map[packet_id]
        delay = float(packet["delay_ms"])
        wait = float(packet.get("candidate_miss_wait_ms", 0.0))
        waits.append(wait)
        service_delays.append(delay - wait)
        airtimes.append(float(packet.get("service_slot_count", 0.0)))
        delays.append(delay)
    return {
        "mean_waiting_delay_ms": _safe_mean(waits),
        "mean_service_delay_ms": _safe_mean(service_delays),
        "mean_tx_airtime_ms": _safe_mean(airtimes),
        "mean_completion_delay_ms": _safe_mean(delays),
    }


def _format_float(value: float, digits: int = 2) -> str:
    if math.isnan(value):
        return "NaN"
    return f"{value:.{digits}f}"


def _transition_rows_for_case(
    *,
    label: str,
    scene_row: dict[str, str],
    case: LoadRatioCase,
    base_config,
    scene_bank_spec: SceneBankSpec,
    repeat_count: int,
    random_seed_base: int,
) -> dict[str, object]:
    baseline_maps: list[dict[str, dict[str, object]]] = []
    proposed_maps: list[dict[str, dict[str, object]]] = []
    arrival_sets: list[set[str]] = []
    for repeat_index in range(repeat_count):
        seed = random_seed_base + repeat_index
        _, baseline_collector = _run_case(
            base_config=base_config,
            scene_bank_spec=scene_bank_spec,
            case=case,
            seed=seed,
            policy=BASELINE_POLICY,
        )
        _, proposed_collector = _run_case(
            base_config=base_config,
            scene_bank_spec=scene_bank_spec,
            case=case,
            seed=seed,
            policy=PROPOSED_POLICY,
        )
        baseline_maps.append(_completed_packet_map(baseline_collector))
        proposed_maps.append(_completed_packet_map(proposed_collector))
        arrival_sets.append(
            _packet_ids_in_window(baseline_collector) | _packet_ids_in_window(proposed_collector)
        )

    total_ids: set[tuple[int, str]] = {
        (index, packet_id)
        for index, packet_ids in enumerate(arrival_sets)
        for packet_id in packet_ids
    }
    stable_satisfied: set[tuple[int, str]] = set()
    stable_missed: set[tuple[int, str]] = set()
    rescued: set[tuple[int, str]] = set()
    harmed: set[tuple[int, str]] = set()
    for index, packet_id in sorted(total_ids):
        baseline_packet = baseline_maps[index].get(packet_id)
        proposed_packet = proposed_maps[index].get(packet_id)
        pdb_ms = float(case.pdb_ms)
        baseline_on_time = (
            baseline_packet is not None and float(baseline_packet["delay_ms"]) <= pdb_ms
        )
        proposed_on_time = (
            proposed_packet is not None and float(proposed_packet["delay_ms"]) <= pdb_ms
        )
        key = (index, packet_id)
        if baseline_on_time and proposed_on_time:
            stable_satisfied.add(key)
        elif not baseline_on_time and not proposed_on_time:
            stable_missed.add(key)
        elif not baseline_on_time and proposed_on_time:
            rescued.add(key)
        elif baseline_on_time and not proposed_on_time:
            harmed.add(key)

    def collect_packet_maps(keys: set[tuple[int, str]], maps: list[dict[str, dict[str, object]]]):
        result: dict[str, dict[str, object]] = {}
        packet_ids: set[str] = set()
        for index, packet_id in sorted(keys):
            packet = maps[index].get(packet_id)
            if packet is None:
                continue
            namespaced_id = f"{index}:{packet_id}"
            result[namespaced_id] = packet
            packet_ids.add(namespaced_id)
        return packet_ids, result

    row: dict[str, object] = {
        "case_type": label,
        "case_label": scene_row["case_label"],
        "target_rho_bg": f"{float(scene_row['target_rho_bg']):.2f}",
        "target_rho_pdb": f"{float(scene_row['target_rho_pdb']):.2f}",
        "pdb_ms": int(float(scene_row["pdb_ms"])),
        "background_user_count": int(scene_row["background_user_count"]),
        "pdb_user_count": int(scene_row["pdb_user_count"]),
        "background_packet_kb": f"{float(scene_row['background_packet_kb']):.1f}",
        "background_period_ms": f"{float(scene_row['background_period_ms']):.1f}",
        "pdb_packet_kb": f"{float(scene_row['pdb_packet_kb']):.1f}",
        "total_pdb_arrivals": len(total_ids),
        "stable_satisfied_count": len(stable_satisfied),
        "rescued_count": len(rescued),
        "harmed_count": len(harmed),
        "stable_missed_count": len(stable_missed),
        "baseline_on_time": len(stable_satisfied) + len(harmed),
        "proposed_on_time": len(stable_satisfied) + len(rescued),
        "baseline_satisfaction_rate": f"{float(scene_row['baseline_edge_pdb_satisfaction_rate']):.4f}",
        "proposed_satisfaction_rate": f"{float(scene_row['proposed_edge_pdb_satisfaction_rate']):.4f}",
        "net_rescued_count": len(rescued) - len(harmed),
        "net_rescue_rate_pp": f"{(len(rescued) - len(harmed)) / len(total_ids) * 100.0:.3f}",
        "relative_gain_vs_baseline_satisfied_pct": (
            "NaN"
            if len(stable_satisfied) + len(harmed) == 0
            else f"{(len(rescued) - len(harmed)) / (len(stable_satisfied) + len(harmed)) * 100.0:.2f}"
        ),
        "stable_satisfied_share_pct": f"{len(stable_satisfied) / len(total_ids) * 100.0:.2f}",
        "stable_missed_share_pct": f"{len(stable_missed) / len(total_ids) * 100.0:.2f}",
    }
    transitions = {
        "rescued_baseline": (rescued, baseline_maps),
        "rescued_proposed": (rescued, proposed_maps),
        "harmed_baseline": (harmed, baseline_maps),
        "harmed_proposed": (harmed, proposed_maps),
    }
    for prefix, (keys, maps) in transitions.items():
        packet_ids, packet_map = collect_packet_maps(keys, maps)
        metrics = _metrics_for_packets(packet_ids, packet_map)
        for key, value in metrics.items():
            row[f"{prefix}_{key}"] = _format_float(value)
    return row


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: build_packet_level_case_analysis.py OUTPUT_DIR", file=sys.stderr)
        return 2
    output_dir = Path(sys.argv[1])
    manifest = json.loads((output_dir / "experiment_manifest.json").read_text(encoding="utf-8"))
    config_path = Path(str(manifest["reference_config"]))
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    sweep = payload["systematic_analysis"]
    base_config = load_config(config_path)
    scene_bank_spec = SceneBankSpec(
        medium_count=24,
        good_count=24,
        poor_count=16,
        medium_distance_range_m=tuple(float(value) for value in sweep["scene_bank"]["medium_distance_range_m"]),
        good_distance_range_m=tuple(float(value) for value in sweep["scene_bank"]["good_distance_range_m"]),
        poor_distance_range_m=tuple(float(value) for value in sweep["scene_bank"]["poor_distance_range_m"]),
    )
    cases = _all_cases(config_path)
    scene_rows = _read_rows(output_dir / "scene_summary.csv")
    selected_rows = _select_rows(scene_rows)
    rows = [
        _transition_rows_for_case(
            label=label,
            scene_row=scene_row,
            case=_case_for_row(scene_row, cases),
            base_config=base_config,
            scene_bank_spec=scene_bank_spec,
            repeat_count=int(sweep["repeat_count"]),
            random_seed_base=int(sweep["random_seed_base"]),
        )
        for label, scene_row in selected_rows
    ]
    _write_rows(output_dir / "packet_level_case_analysis.csv", rows)
    print(output_dir / "packet_level_case_analysis.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
