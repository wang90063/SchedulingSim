import csv
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from scheduling_sim.config import load_config
from scheduling_sim.metrics import MetricsCollector
from scheduling_sim.scenario import ScenarioFactory
from scheduling_sim.simulator import UlSimulator


def _load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_summary(config) -> dict[str, float]:
    users = ScenarioFactory(config).build_users()
    return UlSimulator(config, users, MetricsCollector()).run()


def _packet_bits_from_kb(edge_packet_kb: int) -> int:
    return int(edge_packet_kb) * 1000 * 8


def _case_config(config, *, edge_packet_kb: int, dimension: str, value: int, policy: str):
    updated = replace(
        config,
        scheduler=replace(config.scheduler, reinsert_policy=policy),
        traffic=replace(
            config.traffic,
            edge=replace(config.traffic.edge, packet_bits=_packet_bits_from_kb(edge_packet_kb)),
        ),
    )
    if dimension == "edge_pdb_ms":
        return replace(
            updated,
            traffic=replace(updated.traffic, edge=replace(updated.traffic.edge, pdb_ms=value)),
        )
    if dimension == "center_user_count":
        return replace(
            updated,
            traffic=replace(updated.traffic, center=replace(updated.traffic.center, count=value)),
        )
    raise ValueError(f"unsupported dimension: {dimension}")


def _collect_rows(config, sweep_spec: dict[str, Any]) -> list[dict[str, float | int | str | bool]]:
    rows: list[dict[str, float | int | str | bool]] = []
    policies = tuple(sweep_spec.get("policies", ("tail_append", "business_aware_constrained_insert")))
    for edge_packet_kb in sweep_spec.get("edge_packet_kb", []):
        for edge_pdb_ms in sweep_spec.get("edge_pdb_ms", []):
            for policy in policies:
                summary = _run_summary(
                    _case_config(
                        config,
                        edge_packet_kb=int(edge_packet_kb),
                        dimension="edge_pdb_ms",
                        value=int(edge_pdb_ms),
                        policy=policy,
                    )
                )
                rows.append(
                    {
                        "edge_packet_kb": int(edge_packet_kb),
                        "edge_packet_bits": _packet_bits_from_kb(int(edge_packet_kb)),
                        "dimension": "edge_pdb_ms",
                        "value": int(edge_pdb_ms),
                        "policy": policy,
                        "target_edge_finished": bool(summary["target_edge_finished"]),
                        "target_edge_completion_delay_ms": summary["target_edge_completion_delay_ms"],
                        "target_edge_queue_wait_ms": summary["target_edge_queue_wait_ms"],
                        "target_edge_service_time_ms": summary["target_edge_service_time_ms"],
                        "target_edge_control_phase_wait_ms": summary["target_edge_control_phase_wait_ms"],
                        "target_edge_pre_first_service_wait_ms": summary["target_edge_pre_first_service_wait_ms"],
                        "target_edge_inter_service_gap_wait_ms": summary["target_edge_inter_service_gap_wait_ms"],
                        "target_edge_time_to_first_service_ms": summary["target_edge_time_to_first_service_ms"],
                        "target_edge_pdb_met": bool(summary["target_edge_pdb_met"]),
                        "target_edge_remaining_bits": summary["target_edge_remaining_bits"],
                        "center_avg_rate_bps": summary["center_avg_rate_bps"],
                    }
                )
        for center_user_count in sweep_spec.get("center_user_count", []):
            for policy in policies:
                summary = _run_summary(
                    _case_config(
                        config,
                        edge_packet_kb=int(edge_packet_kb),
                        dimension="center_user_count",
                        value=int(center_user_count),
                        policy=policy,
                    )
                )
                rows.append(
                    {
                        "edge_packet_kb": int(edge_packet_kb),
                        "edge_packet_bits": _packet_bits_from_kb(int(edge_packet_kb)),
                        "dimension": "center_user_count",
                        "value": int(center_user_count),
                        "policy": policy,
                        "target_edge_finished": bool(summary["target_edge_finished"]),
                        "target_edge_completion_delay_ms": summary["target_edge_completion_delay_ms"],
                        "target_edge_queue_wait_ms": summary["target_edge_queue_wait_ms"],
                        "target_edge_service_time_ms": summary["target_edge_service_time_ms"],
                        "target_edge_control_phase_wait_ms": summary["target_edge_control_phase_wait_ms"],
                        "target_edge_pre_first_service_wait_ms": summary["target_edge_pre_first_service_wait_ms"],
                        "target_edge_inter_service_gap_wait_ms": summary["target_edge_inter_service_gap_wait_ms"],
                        "target_edge_time_to_first_service_ms": summary["target_edge_time_to_first_service_ms"],
                        "target_edge_pdb_met": bool(summary["target_edge_pdb_met"]),
                        "target_edge_remaining_bits": summary["target_edge_remaining_bits"],
                        "center_avg_rate_bps": summary["center_avg_rate_bps"],
                    }
                )
    return rows


def _write_outputs(output_dir: Path, rows: list[dict[str, float | int | str | bool]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    csv_path = output_dir / "sensitivity_report.csv"
    json_path = output_dir / "sensitivity_report.json"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    compact_writer = csv.writer(sys.stdout)
    for row in rows:
        compact_writer.writerow(
            [
                "edge_packet_kb",
                int(row["edge_packet_kb"]),
                str(row["dimension"]),
                int(row["value"]),
                str(row["policy"]),
            ]
        )


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run_target_edge_packet_size_sensitivity_report.py CONFIG", file=sys.stderr)
        return 2
    config_path = Path(sys.argv[1])
    payload = _load_payload(config_path)
    config = load_config(config_path)
    rows = _collect_rows(config, payload.get("sweep", {}))
    _write_outputs(Path(config.report.output_dir), rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
