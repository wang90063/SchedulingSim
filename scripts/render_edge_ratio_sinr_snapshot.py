import csv
import json
import sys
from pathlib import Path

from scheduling_sim.config import load_config
from scheduling_sim.edge_ratio_packet_sweep import build_case_config, scanned_edge_user_count
from scheduling_sim.metrics import MetricsCollector
from scheduling_sim.scenario import ScenarioFactory
from scheduling_sim.simulator import UlSimulator


def _load_manifest(output_dir: Path) -> dict[str, object]:
    manifest_path = output_dir / "experiment_manifest.json"
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _resolve_reference_config(reference_config: str) -> Path:
    reference_path = Path(reference_config)
    if reference_path.is_absolute():
        return reference_path
    repo_root = Path(__file__).resolve().parents[1]
    return repo_root / reference_path


def _build_rows(output_dir: Path) -> list[dict[str, float | int | str]]:
    manifest = _load_manifest(output_dir)
    base_config = load_config(_resolve_reference_config(str(manifest["reference_config"])))
    total_users = int(manifest["total_users"])
    ratios = [int(value) for value in manifest["requested_edge_ratio_pct"]]
    rows: list[dict[str, float | int | str]] = []

    for requested_edge_ratio_pct in ratios:
        case_config = build_case_config(
            base_config,
            total_users=total_users,
            requested_edge_ratio_pct=requested_edge_ratio_pct,
            pdb_packet_kb=10,
            policy=base_config.scheduler.reinsert_policy,
        )
        users = ScenarioFactory(case_config).build_users()
        collector = MetricsCollector()
        UlSimulator(case_config, users, collector)
        edge_count = scanned_edge_user_count(
            total_users=total_users,
            requested_edge_ratio_pct=requested_edge_ratio_pct,
        )
        actual_scanned_edge_ratio_pct = edge_count / total_users * 100.0
        for radio_row in collector.build_user_radio_rows(users):
            rows.append(
                {
                    "requested_edge_ratio_pct": requested_edge_ratio_pct,
                    "actual_scanned_edge_ratio_pct": actual_scanned_edge_ratio_pct,
                    "total_users": total_users,
                    "scanned_edge_user_count": edge_count,
                    **radio_row,
                }
            )
    return rows


def _write_csv(path: Path, rows: list[dict[str, float | int | str]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, rows: list[dict[str, float | int | str]]) -> None:
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def _render_report(rows: list[dict[str, float | int | str]]) -> str:
    lines = [
        "# Historical SINR Snapshot Report",
        "",
        "Initial/stable anchor SINR snapshots reconstructed from the historical edge-ratio output.",
        "",
    ]
    ratios = sorted({int(row["requested_edge_ratio_pct"]) for row in rows})
    for requested_edge_ratio_pct in ratios:
        ratio_rows = [row for row in rows if int(row["requested_edge_ratio_pct"]) == requested_edge_ratio_pct]
        edge_count = int(ratio_rows[0]["scanned_edge_user_count"])
        total_users = int(ratio_rows[0]["total_users"])
        actual_ratio = float(ratio_rows[0]["actual_scanned_edge_ratio_pct"])
        lines.extend(
            [
                f"## {requested_edge_ratio_pct}% Edge Ratio",
                "",
                (
                    f"Initial/stable anchor SINR snapshot for `{edge_count}` scanned edge users out of "
                    f"`{total_users}` total users (`{actual_ratio:.3f}%` actual scanned edge ratio)."
                ),
                "",
            ]
        )
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python scripts/render_edge_ratio_sinr_snapshot.py OUTPUT_DIR", file=sys.stderr)
        return 1

    output_dir = Path(argv[1])
    rows = _build_rows(output_dir)

    csv_path = output_dir / "sinr_snapshot_by_ratio.csv"
    json_path = output_dir / "sinr_snapshot_by_ratio.json"
    report_path = output_dir / "sinr_snapshot_report.md"

    _write_csv(csv_path, rows)
    _write_json(json_path, rows)
    report_path.write_text(_render_report(rows), encoding="utf-8")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
