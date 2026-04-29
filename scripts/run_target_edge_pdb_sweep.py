import csv
import json
import sys
from dataclasses import replace
from pathlib import Path

from scheduling_sim.config import load_config
from scheduling_sim.metrics import MetricsCollector
from scheduling_sim.report_rows import build_common_summary_row
from scheduling_sim.scenario import ScenarioFactory
from scheduling_sim.simulator import UlSimulator


EDGE_PDB_VALUES = (100, 150, 200)
POLICIES = ("tail_append", "business_aware_constrained_insert")


def run_case(config, edge_pdb_ms: int, policy: str) -> dict[str, float]:
    traffic = replace(
        config.traffic,
        edge=replace(config.traffic.edge, pdb_ms=edge_pdb_ms),
    )
    case_config = replace(
        config,
        traffic=traffic,
        scheduler=replace(config.scheduler, reinsert_policy=policy),
    )
    users = ScenarioFactory(case_config).build_users()
    return UlSimulator(case_config, users, MetricsCollector()).run()


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run_target_edge_pdb_sweep.py CONFIG", file=sys.stderr)
        return 2
    config = load_config(Path(sys.argv[1]))
    rows = []
    for edge_pdb_ms in EDGE_PDB_VALUES:
        for policy in POLICIES:
            summary = run_case(config, edge_pdb_ms=edge_pdb_ms, policy=policy)
            rows.append(
                {
                    "edge_pdb_ms": edge_pdb_ms,
                    "policy": policy,
                    "center_user_gbr_satisfaction_rate": summary["center_user_gbr_satisfaction_rate"],
                    **build_common_summary_row(summary),
                }
            )
    output_dir = Path(config.report.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "pdb_sweep.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
