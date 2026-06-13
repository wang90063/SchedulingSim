import csv
import json
import sys
from dataclasses import replace
from pathlib import Path

from scheduling_sim.config import load_config
from scheduling_sim.metrics import MetricsCollector
from scheduling_sim.simulator import UlSimulator
from scheduling_sim.systematic_analysis import (
    SceneBankSpec,
    aggregate_scene_rows,
    build_boundary_feasibility_rows,
    build_realization_bank,
    build_systematic_case_users,
    build_typical_case_detail_rows,
    capacity_summary_rows,
    merge_row_sets,
    paired_metric_row,
    per_run_metric_row,
    scene_key,
    scene_key_set,
    select_typical_case_rows,
    summarize_regions,
    systematic_cases,
)


def _write_table(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key in seen:
                continue
            seen.add(key)
            fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_table(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _mean_metric(rows: list[dict[str, object]], field: str) -> float:
    if not rows:
        return 0.0
    return sum(float(row[field]) for row in rows) / float(len(rows))


def _boundary_summary(boundary_rows: list[dict[str, object]]) -> dict[str, object]:
    expanded_rows = [
        row for row in boundary_rows if int(row["baseline_feasible"]) == 0 and int(row["proposed_feasible"]) == 1
    ]
    regressed_rows = [
        row for row in boundary_rows if int(row["baseline_feasible"]) == 1 and int(row["proposed_feasible"]) == 0
    ]
    return {
        "baseline_feasible_points": sum(int(row["baseline_feasible"]) for row in boundary_rows),
        "proposed_feasible_points": sum(int(row["proposed_feasible"]) for row in boundary_rows),
        "expanded_points": len(expanded_rows),
        "regressed_points": len(regressed_rows),
        "expanded_rows": expanded_rows,
    }


def _include_case_from_sweep(sweep: dict[str, object]):
    minimum_total_users = int(sweep.get("minimum_total_users", 0) or 0)
    if minimum_total_users <= 0:
        return None
    return lambda case: (case.background_user_count + case.pdb_user_count) >= minimum_total_users


def _reuse_raw_summaries(reuse_output_dirs: list[str]) -> list[dict[str, object]]:
    raw_summaries: list[dict[str, object]] = []
    for directory in reuse_output_dirs:
        raw_summary_path = Path(directory) / "raw_summaries.json"
        if not raw_summary_path.exists():
            continue
        raw_summaries.extend(json.loads(raw_summary_path.read_text(encoding="utf-8")))
    return raw_summaries


def _reuse_rows(reuse_output_dirs: list[str]) -> tuple[list[dict[str, object]], list[dict[str, object]], set[tuple[int, int, int, int]]]:
    per_run_rows: list[dict[str, object]] = []
    paired_rows: list[dict[str, object]] = []
    scene_keys: set[tuple[int, int, int, int]] = set()
    for directory in reuse_output_dirs:
        reuse_dir = Path(directory)
        reuse_per_run_rows = _read_table(reuse_dir / "per_run_rows.csv")
        reuse_paired_rows = _read_table(reuse_dir / "paired_rows.csv")
        per_run_rows.extend(reuse_per_run_rows)
        paired_rows.extend(reuse_paired_rows)
        scene_keys |= scene_key_set(reuse_paired_rows)
    return per_run_rows, paired_rows, scene_keys


def _summary_report(
    *,
    manifest: dict[str, object],
    scene_rows: list[dict[str, object]],
    region_rows: list[dict[str, object]],
    typical_case_rows: list[dict[str, object]],
    typical_case_detail_rows: list[dict[str, object]],
    boundary_rows_95: list[dict[str, object]],
    boundary_rows_90: list[dict[str, object]],
) -> str:
    improved_rows = [row for row in scene_rows if float(row["mean_delta_pdb_satisfaction_rate"]) > 0.0]
    worsened_rows = [row for row in scene_rows if float(row["mean_delta_pdb_satisfaction_rate"]) < 0.0]
    neutral_rows = [row for row in scene_rows if float(row["mean_delta_pdb_satisfaction_rate"]) == 0.0]
    total_paired_realizations = sum(int(row["repeat_count"]) for row in scene_rows)
    best_gain_row = max(scene_rows, key=lambda row: float(row["mean_delta_pdb_satisfaction_rate"]), default=None)
    worst_cost_row = min(scene_rows, key=lambda row: float(row["mean_center_throughput_retention"]), default=None)
    boundary_95_summary = _boundary_summary(boundary_rows_95)
    boundary_90_summary = _boundary_summary(boundary_rows_90)
    detail_by_case_and_policy = {
        (str(row["case_label"]), str(row["policy"])): row for row in typical_case_detail_rows
    }
    lines = [
        "# Systematic Simulation Analysis",
        "",
        "## Wireless Environment and Realization Bank",
        "",
        f"- reference_config: `{manifest['reference_config']}`",
        f"- scene_bank_counts: `{manifest['scene_bank_counts']}`",
        f"- realization_bank_total_users: `{sum(int(value) for value in dict(manifest['scene_bank_counts']).values())}`",
        f"- repeat_count_per_scene_point: `{manifest['repeat_count']}`",
        "",
        "## Business Scan Matrix",
        "",
        f"- background_user_count_values: `{manifest['background_user_count_values']}`",
        f"- pdb_user_count_values: `{manifest['pdb_user_count_values']}`",
        f"- pdb_ms_values: `{manifest['pdb_ms_values']}`",
        f"- pdb_packet_kb_values: `{manifest['pdb_packet_kb_values']}`",
        f"- repeat_count: `{manifest['repeat_count']}`",
        f"- Scene points evaluated: `{len(scene_rows)}`",
        f"- Paired realization rows: `{total_paired_realizations}`",
        f"- Policy runs executed: `{total_paired_realizations * 2}`",
        "",
        "## Reporting Semantics",
        "",
        "- `scene_summary.csv` aggregates policy-paired results at each business scan point.",
        "- `capacity_summary_95.csv` and `capacity_summary_90.csv` summarize feasible operating ranges at two thresholds.",
        f"- boundary_feasibility_files: `{manifest['boundary_feasibility_files']}`",
        f"- representative_case_files: `{manifest['representative_case_files']}`",
        f"- Aggregated scene points: `{len(scene_rows)}`",
        "",
        "## Panoramic PDB Gain Overview",
        "",
        f"- Scene points evaluated: `{len(scene_rows)}`",
        f"- Proposed improves `{len(improved_rows)}` points, ties `{len(neutral_rows)}` points, and regresses `{len(worsened_rows)}` points.",
        f"- Mean scene-level delta PDB satisfaction: `{_mean_metric(scene_rows, 'mean_delta_pdb_satisfaction_rate'):.3f}`",
        f"- Mean scene-level center throughput retention: `{_mean_metric(scene_rows, 'mean_center_throughput_retention'):.3f}`",
        "",
        "| background_user_count | pdb_user_count | pdb_ms | pdb_packet_kb | baseline_pdb_satisfaction | proposed_pdb_satisfaction | delta_pdb_satisfaction | center_retention |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in sorted(scene_rows, key=lambda item: float(item["mean_delta_pdb_satisfaction_rate"]), reverse=True)[:3]:
        lines.append(
            f"| {int(row['background_user_count'])} | {int(row['pdb_user_count'])} | {int(row['pdb_ms'])} | "
            f"{int(row['pdb_packet_kb'])} | {float(row['baseline_edge_pdb_satisfaction_rate']):.3f} | "
            f"{float(row['proposed_edge_pdb_satisfaction_rate']):.3f} | "
            f"{float(row['mean_delta_pdb_satisfaction_rate']):.3f} | "
            f"{float(row['mean_center_throughput_retention']):.3f} |"
        )
    lines.extend(
        [
            "",
            "## Background Cost and Resource Analysis",
            "",
            f"- Mean center throughput retention across scene points: `{_mean_metric(scene_rows, 'mean_center_throughput_retention'):.3f}`",
            f"- Mean PRB utilization delta (proposed - baseline): `{_mean_metric(scene_rows, 'mean_delta_prb_utilization'):.3f}`",
            f"- Mean center PRB share delta: `{_mean_metric(scene_rows, 'mean_delta_center_prb_share'):.3f}`",
            f"- Mean edge PRB share delta: `{_mean_metric(scene_rows, 'mean_delta_edge_prb_share'):.3f}`",
            "",
            "| Region | Scene Points | Share | Win Rate | Mean Delta PDB Satisfaction | Mean Center Retention | Mean Delta PRB Utilization |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in region_rows:
        lines.append(
            f"| {row['region']} | {row['scene_point_count']} | {float(row['scene_point_share']):.2f} | "
            f"{float(row['proposed_win_rate']):.2f} | {float(row['mean_delta_pdb_satisfaction_rate']):.3f} | "
            f"{float(row['mean_center_throughput_retention']):.3f} | {float(row['mean_delta_prb_utilization']):.3f} |"
        )
    if worst_cost_row is not None:
        lines.extend(
            [
                "",
                "- Lowest center-retention scene point:",
                f"  - bg=`{int(worst_cost_row['background_user_count'])}`, pdb_users=`{int(worst_cost_row['pdb_user_count'])}`, "
                f"pdb_ms=`{int(worst_cost_row['pdb_ms'])}`, pdb_packet_kb=`{int(worst_cost_row['pdb_packet_kb'])}`",
                f"  - delta_pdb_satisfaction=`{float(worst_cost_row['mean_delta_pdb_satisfaction_rate']):.3f}`, "
                f"center_retention=`{float(worst_cost_row['mean_center_throughput_retention']):.3f}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Feasible Boundary Expansion",
            "",
            "- Threshold snapshots are exported in `boundary_feasibility_95.csv` and `boundary_feasibility_90.csv`.",
            "",
            "| Threshold | Baseline Feasible Points | Proposed Feasible Points | Expanded Points | Regressed Points |",
            "| ---: | ---: | ---: | ---: | ---: |",
            f"| 0.95 | {boundary_95_summary['baseline_feasible_points']} | {boundary_95_summary['proposed_feasible_points']} | "
            f"{boundary_95_summary['expanded_points']} | {boundary_95_summary['regressed_points']} |",
            f"| 0.90 | {boundary_90_summary['baseline_feasible_points']} | {boundary_90_summary['proposed_feasible_points']} | "
            f"{boundary_90_summary['expanded_points']} | {boundary_90_summary['regressed_points']} |",
        ]
    )
    if boundary_95_summary["expanded_rows"]:
        lines.extend(
            [
                "",
                "| Expanded @95% background_user_count | pdb_user_count | pdb_ms | pdb_packet_kb |",
                "| ---: | ---: | ---: | ---: |",
            ]
        )
        for row in boundary_95_summary["expanded_rows"][:5]:
            lines.append(
                f"| {int(row['background_user_count'])} | {int(row['pdb_user_count'])} | {int(row['pdb_ms'])} | "
                f"{int(row['pdb_packet_kb'])} |"
            )
    lines.extend(
        [
            "",
            "## Representative Case Mechanism Analysis",
            "",
            f"- Representative cases selected: `{len(typical_case_rows)}`",
            f"- Representative detail rows: `{len(typical_case_detail_rows)}`",
            "- `typical_case_details.csv` is the renderer-facing mechanism table for these cases.",
        ]
    )
    if typical_case_rows:
        lines.extend(
            [
                "",
                "| Label | background_user_count | pdb_user_count | pdb_ms | pdb_packet_kb | Mean Delta PDB Satisfaction | Center Retention |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in typical_case_rows:
            lines.append(
                f"| {row['case_label']} | {row['background_user_count']} | {row['pdb_user_count']} | "
                f"{row['pdb_ms']} | {row['pdb_packet_kb']} | "
                f"{float(row['mean_delta_pdb_satisfaction_rate']):.3f} | "
                f"{float(row['mean_center_throughput_retention']):.3f} |"
            )
        lines.extend(
            [
                "",
                "| Label | baseline_satisfaction | proposed_satisfaction | baseline_queue_ms | proposed_queue_ms | baseline_completion_ms | proposed_completion_ms | baseline_center_rate_bps | proposed_center_rate_bps | center_retention |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for case_row in typical_case_rows:
            baseline_row = detail_by_case_and_policy.get((str(case_row["case_label"]), str(manifest["baseline_policy"])))
            proposed_row = detail_by_case_and_policy.get((str(case_row["case_label"]), str(manifest["ours_policy"])))
            if baseline_row is None or proposed_row is None:
                continue
            baseline_center_rate = float(baseline_row["center_agg_rate_bps"])
            proposed_center_rate = float(proposed_row["center_agg_rate_bps"])
            center_retention = 1.0 if baseline_center_rate == 0.0 else proposed_center_rate / baseline_center_rate
            lines.append(
                f"| {case_row['case_label']} | {float(baseline_row['edge_pdb_satisfaction_rate']):.3f} | "
                f"{float(proposed_row['edge_pdb_satisfaction_rate']):.3f} | "
                f"{float(baseline_row['target_edge_queue_wait_ms']):.1f} | "
                f"{float(proposed_row['target_edge_queue_wait_ms']):.1f} | "
                f"{float(baseline_row['target_edge_completion_delay_ms']):.1f} | "
                f"{float(proposed_row['target_edge_completion_delay_ms']):.1f} | "
                f"{baseline_center_rate:.1f} | {proposed_center_rate:.1f} | {center_retention:.3f} |"
            )
        lines.extend(
            [
                "",
                "| Label | baseline_prb_utilization | proposed_prb_utilization | baseline_center_prb_share | proposed_center_prb_share | baseline_edge_prb_share | proposed_edge_prb_share | baseline_backlog_bits | proposed_backlog_bits |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for case_row in typical_case_rows:
            baseline_row = detail_by_case_and_policy.get((str(case_row["case_label"]), str(manifest["baseline_policy"])))
            proposed_row = detail_by_case_and_policy.get((str(case_row["case_label"]), str(manifest["ours_policy"])))
            if baseline_row is None or proposed_row is None:
                continue
            lines.append(
                f"| {case_row['case_label']} | {float(baseline_row['prb_utilization']):.3f} | "
                f"{float(proposed_row['prb_utilization']):.3f} | "
                f"{float(baseline_row['center_prb_share']):.3f} | {float(proposed_row['center_prb_share']):.3f} | "
                f"{float(baseline_row['edge_prb_share']):.3f} | {float(proposed_row['edge_prb_share']):.3f} | "
                f"{float(baseline_row['edge_backlog_bits']):.1f} | {float(proposed_row['edge_backlog_bits']):.1f} |"
            )
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Proposed improves `{len(improved_rows)}/{len(scene_rows)}` scene points; best gain is "
            f"`{0.0 if best_gain_row is None else float(best_gain_row['mean_delta_pdb_satisfaction_rate']):.3f}`.",
            f"- Mean center throughput retention is `{_mean_metric(scene_rows, 'mean_center_throughput_retention'):.3f}`; "
            f"worst retained point is `{1.0 if worst_cost_row is None else float(worst_cost_row['mean_center_throughput_retention']):.3f}`.",
            f"- Feasible-region expansion adds `{boundary_95_summary['expanded_points']}` points at 95% and "
            f"`{boundary_90_summary['expanded_points']}` points at 90%.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run_systematic_simulation_analysis.py CONFIG", file=sys.stderr)
        return 2

    config_path = Path(sys.argv[1])
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    sweep = payload["systematic_analysis"]
    base_config = load_config(config_path)
    output_dir = Path(base_config.report.output_dir)
    scene_bank_spec = SceneBankSpec(
        medium_count=24,
        good_count=24,
        poor_count=16,
        medium_distance_range_m=tuple(float(value) for value in sweep["scene_bank"]["medium_distance_range_m"]),
        good_distance_range_m=tuple(float(value) for value in sweep["scene_bank"]["good_distance_range_m"]),
        poor_distance_range_m=tuple(float(value) for value in sweep["scene_bank"]["poor_distance_range_m"]),
    )

    baseline_policy = str(sweep["baseline_policy"])
    ours_policy = str(sweep["ours_policy"])
    background_packet_bits = int(sweep["background_packet_kb"]) * 1000 * 8
    reuse_output_dirs = [str(value) for value in sweep.get("reuse_output_dirs", [])]
    existing_raw_summaries = _reuse_raw_summaries(reuse_output_dirs)
    existing_per_run_rows, existing_paired_rows, reused_scene_keys = _reuse_rows(reuse_output_dirs)
    include_case = _include_case_from_sweep(sweep)
    all_cases = systematic_cases(
        background_user_counts=list(sweep["background_user_count_values"]),
        pdb_user_counts=list(sweep["pdb_user_count_values"]),
        pdb_ms_values=list(sweep["pdb_ms_values"]),
        pdb_packet_kb_values=list(sweep["pdb_packet_kb_values"]),
        include_case=include_case,
    )
    cases_to_run = [case for case in all_cases if scene_key(case.__dict__) not in reused_scene_keys]
    per_run_rows: list[dict[str, object]] = []
    paired_rows: list[dict[str, object]] = []
    raw_summaries: list[dict[str, object]] = []

    for repeat_index in range(int(sweep["repeat_count"])):
        bank_seed = int(sweep["random_seed_base"]) + repeat_index
        bank = build_realization_bank(base_config, scene_bank_spec=scene_bank_spec, bank_seed=bank_seed)
        for case in cases_to_run:
            scenario_id = (
                f"bg{case.background_user_count}_pdb{case.pdb_user_count}_"
                f"d{case.pdb_ms}_k{case.pdb_packet_kb}_seed{repeat_index:02d}"
            )
            summaries_by_policy: dict[str, dict[str, float]] = {}
            for policy in (baseline_policy, ours_policy):
                case_config = replace(
                    base_config,
                    scheduler=replace(base_config.scheduler, reinsert_policy=policy),
                    report=replace(base_config.report, output_dir=str(output_dir)),
                )
                users = build_systematic_case_users(
                    case_config,
                    bank,
                    background_user_count=case.background_user_count,
                    pdb_user_count=case.pdb_user_count,
                    pdb_ms=case.pdb_ms,
                    pdb_packet_bits=int(case.pdb_packet_kb) * 1000 * 8,
                    background_packet_bits=background_packet_bits,
                )
                collector = MetricsCollector()
                summary = UlSimulator(case_config, users, collector).run()
                raw_summaries.append(
                    {
                        "seed": bank_seed,
                        "scenario_id": scenario_id,
                        "policy": policy,
                        "summary": summary,
                    }
                )
                per_run_rows.append(
                    per_run_metric_row(
                        scenario_id=scenario_id,
                        seed=bank_seed,
                        policy=policy,
                        case=case,
                        summary=summary,
                    )
                )
                summaries_by_policy[policy] = summary
            paired_rows.append(
                paired_metric_row(
                    case=case,
                    seed=bank_seed,
                    baseline_summary=summaries_by_policy[baseline_policy],
                    proposed_summary=summaries_by_policy[ours_policy],
                )
            )

    merged_per_run_rows = merge_row_sets(existing_rows=existing_per_run_rows, new_rows=per_run_rows)
    merged_paired_rows = merge_row_sets(existing_rows=existing_paired_rows, new_rows=paired_rows)
    merged_raw_summaries = [*existing_raw_summaries, *raw_summaries]
    scene_rows = aggregate_scene_rows(merged_paired_rows)
    region_rows = summarize_regions(scene_rows)
    capacity_rows_95 = capacity_summary_rows(scene_rows, threshold=0.95)
    capacity_rows_90 = capacity_summary_rows(scene_rows, threshold=0.90)
    typical_case_rows = select_typical_case_rows(scene_rows)
    typical_case_detail_rows = build_typical_case_detail_rows(
        scene_rows=scene_rows,
        per_run_rows=merged_per_run_rows,
        baseline_policy=baseline_policy,
        proposed_policy=ours_policy,
    )
    boundary_rows_95 = build_boundary_feasibility_rows(scene_rows, threshold=0.95)
    boundary_rows_90 = build_boundary_feasibility_rows(scene_rows, threshold=0.90)
    final_output_dir = Path(str(sweep.get("merged_output_dir", output_dir)))
    manifest = {
        **sweep,
        "reference_config": str(config_path),
        "scene_bank_counts": {
            "medium": scene_bank_spec.medium_count,
            "good": scene_bank_spec.good_count,
            "poor": scene_bank_spec.poor_count,
        },
        "boundary_feasibility_files": ["boundary_feasibility_95.csv", "boundary_feasibility_90.csv"],
        "representative_case_files": ["typical_case_candidates.csv", "typical_case_details.csv"],
        "reuse_output_dirs": reuse_output_dirs,
        "reused_scene_point_count": len(reused_scene_keys),
        "new_scene_point_count": len(cases_to_run),
        "final_scene_point_count": len(scene_rows),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "experiment_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output_dir / "raw_summaries.json").write_text(json.dumps(raw_summaries, indent=2), encoding="utf-8")
    _write_table(output_dir / "per_run_rows.csv", per_run_rows)
    _write_table(output_dir / "paired_rows.csv", paired_rows)
    final_output_dir.mkdir(parents=True, exist_ok=True)
    (final_output_dir / "experiment_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (final_output_dir / "raw_summaries.json").write_text(json.dumps(merged_raw_summaries, indent=2), encoding="utf-8")
    _write_table(final_output_dir / "per_run_rows.csv", merged_per_run_rows)
    _write_table(final_output_dir / "paired_rows.csv", merged_paired_rows)
    _write_table(final_output_dir / "scene_summary.csv", scene_rows)
    _write_table(final_output_dir / "region_summary.csv", region_rows)
    _write_table(final_output_dir / "capacity_summary_95.csv", capacity_rows_95)
    _write_table(final_output_dir / "capacity_summary_90.csv", capacity_rows_90)
    _write_table(final_output_dir / "boundary_feasibility_95.csv", boundary_rows_95)
    _write_table(final_output_dir / "boundary_feasibility_90.csv", boundary_rows_90)
    _write_table(final_output_dir / "typical_case_candidates.csv", typical_case_rows)
    _write_table(final_output_dir / "typical_case_details.csv", typical_case_detail_rows)
    (final_output_dir / "summary_report.md").write_text(
        _summary_report(
            manifest=manifest,
            scene_rows=scene_rows,
            region_rows=region_rows,
            typical_case_rows=typical_case_rows,
            typical_case_detail_rows=typical_case_detail_rows,
            boundary_rows_95=boundary_rows_95,
            boundary_rows_90=boundary_rows_90,
        ),
        encoding="utf-8",
    )
    print(final_output_dir / "summary_report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
