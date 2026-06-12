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
    build_realization_bank,
    build_systematic_case_users,
    capacity_summary_rows,
    paired_metric_row,
    per_run_metric_row,
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


def _summary_report(
    *,
    manifest: dict[str, object],
    scene_rows: list[dict[str, object]],
    region_rows: list[dict[str, object]],
) -> str:
    lines = [
        "# Systematic Simulation Analysis",
        "",
        "## Scan",
        "",
        f"- background_user_count: `{manifest['background_user_count_values']}`",
        f"- pdb_user_count: `{manifest['pdb_user_count_values']}`",
        f"- pdb_ms: `{manifest['pdb_ms_values']}`",
        f"- pdb_packet_kb: `{manifest['pdb_packet_kb_values']}`",
        f"- repeat_count: `{manifest['repeat_count']}`",
        "",
        "## Region Summary",
        "",
        "| Region | Scene Points | Share | Win Rate | Mean Delta PDB Satisfaction | Mean Center Retention |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in region_rows:
        lines.append(
            f"| {row['region']} | {row['scene_point_count']} | {float(row['scene_point_share']):.2f} | "
            f"{float(row['proposed_win_rate']):.2f} | {float(row['mean_delta_pdb_satisfaction_rate']):.3f} | "
            f"{float(row['mean_center_throughput_retention']):.3f} |"
        )
    lines.extend(["", "## Scene Summary", "", f"- Aggregated scene points: `{len(scene_rows)}`"])
    typical_rows = select_typical_case_rows(scene_rows)
    if typical_rows:
        lines.extend(
            [
                "",
                "## Typical Cases",
                "",
                "| Label | background_user_count | pdb_user_count | pdb_ms | pdb_packet_kb | Mean Delta PDB Satisfaction | Center Retention |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in typical_rows:
            lines.append(
                f"| {row['case_label']} | {row['background_user_count']} | {row['pdb_user_count']} | "
                f"{row['pdb_ms']} | {row['pdb_packet_kb']} | "
                f"{float(row['mean_delta_pdb_satisfaction_rate']):.3f} | "
                f"{float(row['mean_center_throughput_retention']):.3f} |"
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
    per_run_rows: list[dict[str, object]] = []
    paired_rows: list[dict[str, object]] = []
    raw_summaries: list[dict[str, object]] = []

    for repeat_index in range(int(sweep["repeat_count"])):
        bank_seed = int(sweep["random_seed_base"]) + repeat_index
        bank = build_realization_bank(base_config, scene_bank_spec=scene_bank_spec, bank_seed=bank_seed)
        for case in systematic_cases(
            background_user_counts=list(sweep["background_user_count_values"]),
            pdb_user_counts=list(sweep["pdb_user_count_values"]),
            pdb_ms_values=list(sweep["pdb_ms_values"]),
            pdb_packet_kb_values=list(sweep["pdb_packet_kb_values"]),
        ):
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

    scene_rows = aggregate_scene_rows(paired_rows)
    region_rows = summarize_regions(scene_rows)
    capacity_rows_95 = capacity_summary_rows(scene_rows, threshold=0.95)
    capacity_rows_90 = capacity_summary_rows(scene_rows, threshold=0.90)
    typical_case_rows = select_typical_case_rows(scene_rows)
    manifest = {
        **sweep,
        "reference_config": str(config_path),
        "scene_bank_counts": {
            "medium": scene_bank_spec.medium_count,
            "good": scene_bank_spec.good_count,
            "poor": scene_bank_spec.poor_count,
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "experiment_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output_dir / "raw_summaries.json").write_text(json.dumps(raw_summaries, indent=2), encoding="utf-8")
    _write_table(output_dir / "per_run_rows.csv", per_run_rows)
    _write_table(output_dir / "paired_rows.csv", paired_rows)
    _write_table(output_dir / "scene_summary.csv", scene_rows)
    _write_table(output_dir / "region_summary.csv", region_rows)
    _write_table(output_dir / "capacity_summary_95.csv", capacity_rows_95)
    _write_table(output_dir / "capacity_summary_90.csv", capacity_rows_90)
    _write_table(output_dir / "typical_case_candidates.csv", typical_case_rows)
    (output_dir / "summary_report.md").write_text(
        _summary_report(manifest=manifest, scene_rows=scene_rows, region_rows=region_rows),
        encoding="utf-8",
    )
    print(output_dir / "summary_report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
