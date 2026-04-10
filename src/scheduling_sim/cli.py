import argparse
from dataclasses import replace
from pathlib import Path

from scheduling_sim.config import load_config
from scheduling_sim.metrics import MetricsCollector
from scheduling_sim.reporting import write_report
from scheduling_sim.scenario import ScenarioFactory
from scheduling_sim.simulator import UlSimulator


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("config_path")
    run_parser.add_argument(
        "--reinsert-policy",
        choices=["tail_append", "constrained_insert"],
    )
    args = parser.parse_args()
    config = load_config(Path(args.config_path))
    if args.reinsert_policy is not None:
        config = replace(
            config,
            scheduler=replace(config.scheduler, reinsert_policy=args.reinsert_policy),
        )
    users = ScenarioFactory(config).build_users()
    metrics = MetricsCollector()
    simulator = UlSimulator(config, users, metrics)
    summary = simulator.run()
    report_path = write_report(config.report.output_dir, summary)
    print(f"Report written to {report_path} using {config.scheduler.reinsert_policy}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
