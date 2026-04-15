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

SummaryValue = float | int | bool
Summary = dict[str, SummaryValue]
RowValue = float | int | str | bool
Row = dict[str, RowValue]


def _load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_summary(config) -> Summary:
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


def _build_row(
    *,
    edge_packet_kb: int,
    dimension: str,
    value: int,
    policy: str,
    summary: Summary,
) -> Row:
    return {
        "edge_packet_kb": edge_packet_kb,
        "edge_packet_bits": _packet_bits_from_kb(edge_packet_kb),
        "dimension": dimension,
        "value": value,
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


def _collect_rows(config, sweep_spec: dict[str, Any]) -> list[Row]:
    rows: list[Row] = []
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
                    _build_row(
                        edge_packet_kb=int(edge_packet_kb),
                        dimension="edge_pdb_ms",
                        value=int(edge_pdb_ms),
                        policy=policy,
                        summary=summary,
                    )
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
                    _build_row(
                        edge_packet_kb=int(edge_packet_kb),
                        dimension="center_user_count",
                        value=int(center_user_count),
                        policy=policy,
                        summary=summary,
                    )
                )
    return rows


def _rows_for(rows: list[Row], *, edge_packet_kb: int, dimension: str) -> list[Row]:
    return [
        row
        for row in rows
        if int(row["edge_packet_kb"]) == edge_packet_kb and row["dimension"] == dimension
    ]


def _value_label(dimension: str, value: int) -> str:
    return {
        "edge_pdb_ms": f"{value} ms",
        "center_user_count": f"{value} center users",
    }[dimension]


def _build_table(rows: list[Row], *, dimension: str) -> list[str]:
    lines = [
        "| 参数值 | Baseline Completion | Ours Completion | Baseline Queue Wait | Ours Queue Wait | Baseline Service | Ours Service | Baseline PDB | Ours PDB | Baseline Center Avg | Ours Center Avg | 结论 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | --- |",
    ]
    values = sorted({int(row["value"]) for row in rows})
    for value in values:
        baseline = next(row for row in rows if int(row["value"]) == value and row["policy"] == "tail_append")
        ours = next(
            row
            for row in rows
            if int(row["value"]) == value and row["policy"] == "business_aware_constrained_insert"
        )
        delta_ms = float(baseline["target_edge_completion_delay_ms"]) - float(ours["target_edge_completion_delay_ms"])
        ratio = 0.0 if float(baseline["target_edge_completion_delay_ms"]) == 0.0 else (
            delta_ms / float(baseline["target_edge_completion_delay_ms"]) * 100.0
        )
        lines.append(
            "| "
            f"`{_value_label(dimension, value)}` | "
            f"`{float(baseline['target_edge_completion_delay_ms']):.0f} ms` | "
            f"`{float(ours['target_edge_completion_delay_ms']):.0f} ms` | "
            f"`{float(baseline['target_edge_queue_wait_ms']):.0f} ms` | "
            f"`{float(ours['target_edge_queue_wait_ms']):.0f} ms` | "
            f"`{float(baseline['target_edge_service_time_ms']):.0f} ms` | "
            f"`{float(ours['target_edge_service_time_ms']):.0f} ms` | "
            f"`{bool(baseline['target_edge_pdb_met'])}` | "
            f"`{bool(ours['target_edge_pdb_met'])}` | "
            f"`{float(baseline['center_avg_rate_bps']):.0f} bps` | "
            f"`{float(ours['center_avg_rate_bps']):.0f} bps` | "
            f"{delta_ms:.0f} ms ({ratio:.1f}%) |"
        )
    return lines


def _packet_size_heading(edge_packet_kb: int) -> str:
    return f"## `{edge_packet_kb} KB` 目标边缘大包场景"


def _build_packet_size_section(edge_packet_kb: int, rows: list[Row]) -> str:
    pdb_rows = _rows_for(rows, edge_packet_kb=edge_packet_kb, dimension="edge_pdb_ms")
    center_rows = _rows_for(rows, edge_packet_kb=edge_packet_kb, dimension="center_user_count")
    return "\n".join(
        [
            _packet_size_heading(edge_packet_kb),
            "",
            f"- 固定 `edge_packet_kb = {edge_packet_kb}`",
            "- 固定 `edge_per_u_slot_prb_cap = 237`",
            "",
            "### PDB 扫描",
            "- 固定 `center_user_count = 63`",
            "",
            *_build_table(pdb_rows, dimension="edge_pdb_ms"),
            "",
            "### PDB 趋势分析",
            "- 重点解释 `PDB` 收紧或放松时，完成时延收益主要来自 `Queue Wait` 还是 `Service Time`。",
            "- 重点解释在当前包大小下，deadline 压力是否让 `business_aware_constrained_insert` 更容易压缩 `Inter-Service Gap Wait`。",
            "",
            "### 中心用户数扫描",
            "- 固定 `edge_pdb_ms = 500`",
            "",
            *_build_table(center_rows, dimension="center_user_count"),
            "",
            "### 中心用户数趋势分析",
            "- 重点解释负载升高后，baseline 队尾轮转等待如何放大，以及我们的收益与中心吞吐代价是否同步扩大。",
            "",
            "### 小结",
            "- 总结该包大小下的主要收益区间、主要代价和是否出现策略收敛。",
        ]
    )


def _write_markdown_report(payload: dict[str, Any], output_dir: Path, rows: list[Row]) -> None:
    sections = [
        "# Target Edge 大包规模敏感性测试报告",
        "",
        "## 场景设置",
        "",
        "- TDD：`DSUUU`，每 slot `1 ms`，目标包发完即停；最大 `1000` 个周期作为安全上限（`5000 ms`）",
        "- 调度资源：每个 U-slot `237 PRB`，边缘目标用户固定 `edge_per_u_slot_prb_cap = 237`，即边缘无额外 cap 限制",
        "- 对比策略：`tail_append` 与 `business_aware_constrained_insert`",
        "- 扫描维度：`400 / 800 / 1200 / 1600 / 2000 KB`，每档下再扫描 `PDB` 与中心用户数",
        "",
        "## 指标说明",
        "",
        "- `Completion Delay`：目标边缘大包从到达到完成的总时延",
        "- `Queue Wait`：目标包总时延中未真正传 bit 的累计等待时间",
        "- `Service Time`：目标包实际占用的 `U` slot 数量 × `1 ms`",
        "- `Center Avg Rate`：目标包完成前中心背景用户的平均吞吐",
        "",
    ]
    for edge_packet_kb in payload.get("sweep", {}).get("edge_packet_kb", []):
        sections.extend([_build_packet_size_section(int(edge_packet_kb), rows), ""])
    sections.extend(
        [
            "## 跨包大小趋势总结",
            "",
            "- 重点总结包越大时，完成时延绝对收益与相对收益是否同步扩大。",
            "- 重点总结收益是否继续主要来自 `Queue Wait` 与 `Inter-Service Gap Wait` 的下降。",
            "- 重点总结边缘无 cap 条件下中心吞吐代价是否随包大小放大。",
            "",
            "## 结论",
            "",
            "- 用 3-5 条结论总结大包规模、PDB 压力、系统负载和中心代价之间的关系。",
        ]
    )
    (output_dir / "sensitivity_report.md").write_text("\n".join(sections), encoding="utf-8")


def _write_outputs(output_dir: Path, rows: list[Row]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    csv_path = output_dir / "sensitivity_rows.csv"
    json_path = output_dir / "sensitivity_rows.json"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    stdout_fieldnames = ["scope", "edge_packet_kb", "dimension", "value", "policy"]
    stdout_writer = csv.DictWriter(sys.stdout, fieldnames=stdout_fieldnames)
    stdout_writer.writeheader()
    stdout_writer.writerows(
        {
            "scope": "edge_packet_kb",
            "edge_packet_kb": int(row["edge_packet_kb"]),
            "dimension": str(row["dimension"]),
            "value": int(row["value"]),
            "policy": str(row["policy"]),
        }
        for row in rows
    )


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run_target_edge_packet_size_sensitivity_report.py CONFIG", file=sys.stderr)
        return 2
    config_path = Path(sys.argv[1])
    payload = _load_payload(config_path)
    config = load_config(config_path)
    rows = _collect_rows(config, payload.get("sweep", {}))
    output_dir = Path(config.report.output_dir)
    _write_outputs(output_dir, rows)
    _write_markdown_report(payload, output_dir, rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
