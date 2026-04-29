import csv
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from scheduling_sim.config import load_config
from scheduling_sim.diagnostics import TargetEdgeDiagnosticCollector
from scheduling_sim.metrics import MetricsCollector
from scheduling_sim.scenario import ScenarioFactory
from scheduling_sim.simulator import UlSimulator


def _load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_policy(config, policy: str):
    updated = replace(
        config,
        scheduler=replace(config.scheduler, reinsert_policy=policy),
    )
    users = ScenarioFactory(updated).build_users()
    collector = TargetEdgeDiagnosticCollector(policy=policy)
    UlSimulator(updated, users, MetricsCollector(), diagnostic_collector=collector).run()
    return collector.rows


def _write_trace_outputs(output_dir: Path, rows: list[dict[str, object]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else [
        "policy",
        "time_ms",
        "phase",
        "queue_rank",
    ]

    csv_path = output_dir / "decision_trace.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    json_path = output_dir / "decision_trace.json"
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    stdout_writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    stdout_writer.writeheader()
    stdout_writer.writerows(rows)


def _rows_by_policy(rows: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(str(row["policy"]), []).append(row)
    return grouped


def _summarize_rows(rows: list[dict[str, object]]) -> dict[str, object]:
    def _first_time(predicate) -> int | None:
        for row in rows:
            if predicate(row):
                return int(row["time_ms"])
        return None

    return {
        "first_candidate_time_ms": _first_time(lambda row: bool(row["in_candidate_window"])),
        "first_rank1_time_ms": _first_time(lambda row: row["candidate_rank_epf"] == 1),
        "first_pdb_dominated_time_ms": _first_time(
            lambda row: row["dominance_label"] in {"pdb_dominated", "overdue_pdb_forced"}
        ),
        "queue_limited_count": sum(1 for row in rows if row["dominance_label"] == "queue_limited"),
        "spectral_dominated_count": sum(
            1 for row in rows if row["dominance_label"] == "spectral_dominated"
        ),
        "pdb_dominated_count": sum(1 for row in rows if row["dominance_label"] == "pdb_dominated"),
        "overdue_pdb_forced_count": sum(
            1 for row in rows if row["dominance_label"] == "overdue_pdb_forced"
        ),
    }


def _decision_axis(rows: list[dict[str, object]]) -> tuple[list[int], list[str]]:
    xs = list(range(len(rows)))
    labels = [f"{row['phase']}@{row['time_ms']}" for row in rows]
    return xs, labels


def _apply_sparse_decision_ticks(ax, xs: list[int], labels: list[str]) -> None:
    if not xs:
        return
    step = max(1, len(xs) // 12)
    tick_indexes = list(range(0, len(xs), step))
    if tick_indexes[-1] != len(xs) - 1:
        tick_indexes.append(len(xs) - 1)
    ax.set_xticks([xs[index] for index in tick_indexes])
    ax.set_xticklabels([labels[index] for index in tick_indexes], rotation=45, ha="right")


def _plot_queue_position(rows_by_policy: dict[str, list[dict[str, object]]], output_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 4))
    axis_labels: list[str] = []
    axis_xs: list[int] = []
    for policy, rows in rows_by_policy.items():
        xs, labels = _decision_axis(rows)
        if len(xs) > len(axis_xs):
            axis_xs = xs
            axis_labels = labels
        ys = [int(row["queue_rank"]) for row in rows]
        ax.plot(xs, ys, marker="o", markersize=3, linewidth=1.2, label=policy)
    ax.set_title("Target Edge Queue Position vs D/S Decisions")
    ax.set_xlabel("D/S decision index")
    ax.set_ylabel("queue_rank")
    ax.invert_yaxis()
    ax.legend()
    ax.grid(True, alpha=0.3)
    _apply_sparse_decision_ticks(ax, axis_xs, axis_labels)
    fig.tight_layout()
    fig.savefig(output_dir / "queue_position_vs_time.png", dpi=150)
    plt.close(fig)


def _plot_epf_rank(rows_by_policy: dict[str, list[dict[str, object]]], output_dir: Path) -> None:
    _plot_epf_rank_view(rows_by_policy, output_dir, "epf_rank_vs_time.png", max_time_ms=None)


def _plot_epf_rank_view(
    rows_by_policy: dict[str, list[dict[str, object]]],
    output_dir: Path,
    filename: str,
    max_time_ms: int | None,
) -> None:
    fig, ax = plt.subplots(figsize=(10, 4))
    for policy, rows in rows_by_policy.items():
        filtered = [row for row in rows if row["candidate_rank_epf"] is not None]
        if max_time_ms is not None:
            filtered = [row for row in filtered if int(row["time_ms"]) <= max_time_ms]
        xs = [int(row["time_ms"]) for row in filtered]
        ys = [int(row["candidate_rank_epf"]) for row in filtered]
        ax.plot(xs, ys, marker="o", markersize=3, linewidth=1.2, label=policy)
    title = "Target Edge EPF Rank vs Time"
    if max_time_ms is not None:
        title = f"Target Edge EPF Rank vs Time (First {max_time_ms} ms)"
        ax.set_xlim(0, max_time_ms)
    ax.set_title(title)
    ax.set_xlabel("time_ms")
    ax.set_ylabel("candidate_rank_epf")
    ax.invert_yaxis()
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / filename, dpi=150)
    plt.close(fig)


def _plot_dominance_terms(rows_by_policy: dict[str, list[dict[str, object]]], output_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 4))
    for policy, rows in rows_by_policy.items():
        xs = [int(row["time_ms"]) for row in rows]
        spectral = [float(row["spectral_term"]) for row in rows]
        hol = [float(row["hol_factor"]) for row in rows]
        ax.plot(xs, spectral, linewidth=1.2, label=f"{policy} spectral_term")
        ax.plot(xs, hol, linewidth=1.2, linestyle="--", label=f"{policy} hol_factor")
    ax.set_title("Spectral Term and HOL Factor vs Time")
    ax.set_xlabel("time_ms")
    ax.set_ylabel("value")
    ax.legend(fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "dominance_terms_vs_time.png", dpi=150)
    plt.close(fig)


def _plot_dominance_terms_by_policy(
    rows_by_policy: dict[str, list[dict[str, object]]], output_dir: Path
) -> None:
    for policy, rows in rows_by_policy.items():
        fig, ax = plt.subplots(figsize=(10, 4))
        xs = [int(row["time_ms"]) for row in rows]
        spectral = [float(row["spectral_term"]) for row in rows]
        hol = [float(row["hol_factor"]) for row in rows]
        ax.plot(xs, spectral, linewidth=1.2, label="spectral_term")
        ax.plot(xs, hol, linewidth=1.2, linestyle="--", label="hol_factor")
        ax.set_title(f"Spectral Term and HOL Factor vs Time ({policy})")
        ax.set_xlabel("time_ms")
        ax.set_ylabel("value")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(output_dir / f"dominance_terms_{policy}.png", dpi=150)
        plt.close(fig)


DOMINANCE_COLORS = {
    "not_pending": "#c7c7c7",
    "queue_limited": "#d62728",
    "spectral_dominated": "#1f77b4",
    "pdb_dominated": "#ff7f0e",
    "overdue_pdb_forced": "#9467bd",
}


def _plot_dominance_timeline(rows_by_policy: dict[str, list[dict[str, object]]], output_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 3))
    policies = list(rows_by_policy.keys())
    for row_index, policy in enumerate(policies):
        for row in rows_by_policy[policy]:
            ax.scatter(
                int(row["time_ms"]),
                row_index,
                color=DOMINANCE_COLORS.get(str(row["dominance_label"]), "#000000"),
                s=18,
            )
    ax.set_title("Dominance Timeline")
    ax.set_xlabel("time_ms")
    ax.set_yticks(range(len(policies)))
    ax.set_yticklabels(policies)
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "dominance_timeline.png", dpi=150)
    plt.close(fig)


def _plot_dominance_timeline_by_policy(
    rows_by_policy: dict[str, list[dict[str, object]]], output_dir: Path
) -> None:
    for policy, rows in rows_by_policy.items():
        fig, ax = plt.subplots(figsize=(10, 2.5))
        for row in rows:
            ax.scatter(
                int(row["time_ms"]),
                0,
                color=DOMINANCE_COLORS.get(str(row["dominance_label"]), "#000000"),
                s=18,
            )
        ax.set_title(f"Dominance Timeline ({policy})")
        ax.set_xlabel("time_ms")
        ax.set_yticks([0])
        ax.set_yticklabels([policy])
        ax.grid(True, axis="x", alpha=0.3)
        fig.tight_layout()
        fig.savefig(output_dir / f"dominance_timeline_{policy}.png", dpi=150)
        plt.close(fig)


def _write_markdown_report(
    payload: dict[str, Any],
    output_dir: Path,
    rows_by_policy: dict[str, list[dict[str, object]]],
) -> None:
    summaries = {policy: _summarize_rows(rows) for policy, rows in rows_by_policy.items()}
    lines = [
        "# Target Edge PDB Dominance Diagnostic",
        "",
        "## 场景设置",
        "",
        "- Target edge: `400KB`",
        "- Edge PDB: `500 ms`",
        "- Center users: `63`",
        "- Center traffic: `960 bit / every 6 slots`",
        "- Policies: `tail_append` vs `business_aware_constrained_insert`",
        "",
        "## 判定口径",
        "",
        "- `queue_limited`：目标大包还没进入候选窗口",
        "- `spectral_dominated`：已进候选窗口，但 `HOL < PDB / 2`",
        "- `pdb_dominated`：已进候选窗口，且 `HOL >= PDB / 2`",
        "- `overdue_pdb_forced`：`HOL >= PDB`",
        "",
        "## 图形总览",
        "",
        "![Queue Position](queue_position_vs_time.png)",
        "",
        "![EPF Rank](epf_rank_vs_time.png)",
        "",
        "![Dominance Terms](dominance_terms_vs_time.png)",
        "",
        "![Dominance Timeline](dominance_timeline.png)",
        "",
        "## 局部放大 / 分策略视图",
        "",
        "![EPF Rank First 100ms](epf_rank_vs_time_first_100ms.png)",
        "",
        "![Dominance Terms Tail Append](dominance_terms_tail_append.png)",
        "",
        "![Dominance Terms Business Aware](dominance_terms_business_aware_constrained_insert.png)",
        "",
        "![Dominance Timeline Tail Append](dominance_timeline_tail_append.png)",
        "",
        "![Dominance Timeline Business Aware](dominance_timeline_business_aware_constrained_insert.png)",
        "",
        "## 策略对比摘要",
        "",
    ]
    for policy, summary in summaries.items():
        lines.extend(
            [
                f"### `{policy}`",
                f"- first_candidate_time_ms: `{summary['first_candidate_time_ms']}`",
                f"- first_rank1_time_ms: `{summary['first_rank1_time_ms']}`",
                f"- first_pdb_dominated_time_ms: `{summary['first_pdb_dominated_time_ms']}`",
                f"- queue_limited_count: `{summary['queue_limited_count']}`",
                f"- spectral_dominated_count: `{summary['spectral_dominated_count']}`",
                f"- pdb_dominated_count: `{summary['pdb_dominated_count']}`",
                f"- overdue_pdb_forced_count: `{summary['overdue_pdb_forced_count']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## 解释结论",
            "",
            "- 先看 target 何时摆脱 `queue_limited`，再看它进入候选窗口后的 EPF rank 变化。",
            "- 若 `hol_factor` 明显抬升且 rank 同步前移，则说明 PDB 压力在增强。",
            "- 若 target 长时间排在候选窗口外，则主导因素仍是队列位置和回插策略。",
        ]
    )
    (output_dir / "diagnostic_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run_target_edge_pdb_dominance_diagnostic.py CONFIG", file=sys.stderr)
        return 2

    config_path = Path(sys.argv[1])
    payload = _load_payload(config_path)
    config = load_config(config_path)

    rows: list[dict[str, object]] = []
    for policy in payload["diagnostic"]["policies"]:
        rows.extend(row.to_dict() for row in _run_policy(config, str(policy)))

    output_dir = Path(config.report.output_dir)
    _write_trace_outputs(output_dir, rows)
    rows_by_policy = _rows_by_policy(rows)
    _plot_queue_position(rows_by_policy, output_dir)
    _plot_epf_rank(rows_by_policy, output_dir)
    _plot_epf_rank_view(
        rows_by_policy,
        output_dir,
        "epf_rank_vs_time_first_100ms.png",
        max_time_ms=100,
    )
    _plot_dominance_terms(rows_by_policy, output_dir)
    _plot_dominance_terms_by_policy(rows_by_policy, output_dir)
    _plot_dominance_timeline(rows_by_policy, output_dir)
    _plot_dominance_timeline_by_policy(rows_by_policy, output_dir)
    _write_markdown_report(payload, output_dir, rows_by_policy)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
