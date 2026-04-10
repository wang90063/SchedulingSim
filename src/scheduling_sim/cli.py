import argparse
from pathlib import Path

from scheduling_sim.config import load_config


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("config_path")
    args = parser.parse_args()
    config = load_config(Path(args.config_path))
    print(f"Report written to {config.report.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
