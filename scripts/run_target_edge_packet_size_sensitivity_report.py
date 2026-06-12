import csv
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from scheduling_sim.config import load_config
from scheduling_sim.metrics import MetricsCollector
from scheduling_sim.report_rows import build_common_summary_row
from scheduling_sim.scenario import ScenarioFactory
from scheduling_sim.simulator import UlSimulator

SummaryValue = float | int | bool | str
Summary = dict[str, SummaryValue]
RowValue = float | int | str | bool | None
Row = dict[str, RowValue]

CENTER_PACKET_GRANULARITY_EDGE_PACKET_KB = 400


def _load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_summary(config) -> Summary:
    users = ScenarioFactory(config).build_users()
    return UlSimulator(config, users, MetricsCollector()).run()


def _packet_bits_from_kb(edge_packet_kb: int) -> int:
    return int(edge_packet_kb) * 1000 * 8


def _granularity_value(packet_bits: int, period_slots: int) -> str:
    return f"{packet_bits}_per_{period_slots}"


def _parse_granularity_value(value: str) -> tuple[int, int]:
    packet_bits_text, period_slots_text = value.split("_per_")
    return int(packet_bits_text), int(period_slots_text)


def _config_metadata(config) -> dict[str, int | None]:
    return {
        "total_prb_per_u_slot": int(config.resources.total_prb_per_u_slot),
        "center_pdb_ms": config.traffic.center.pdb_ms,
        "edge_per_u_slot_prb_cap": config.radio.edge.edge_per_u_slot_prb_cap,
    }


def _payload_section(payload: dict[str, Any], name: str) -> dict[str, Any]:
    section = payload.get(name, {})
    return section if isinstance(section, dict) else {}


def _payload_metadata(payload: dict[str, Any]) -> dict[str, int | None]:
    resources = _payload_section(payload, "resources")
    traffic = _payload_section(payload, "traffic")
    center = traffic.get("center", {}) if isinstance(traffic.get("center", {}), dict) else {}
    radio = _payload_section(payload, "radio")
    edge_radio = radio.get("edge", {}) if isinstance(radio.get("edge", {}), dict) else {}
    return {
        "total_prb_per_u_slot": int(resources.get("total_prb_per_u_slot", 0)),
        "center_pdb_ms": center.get("pdb_ms"),
        "edge_per_u_slot_prb_cap": edge_radio.get("edge_per_u_slot_prb_cap"),
    }


def _pdb_label(value: int | None) -> str:
    return "null" if value is None else f"{int(value)} ms"


def _case_config(config, *, edge_packet_kb: int, dimension: str, value: int | str, policy: str):
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
    if dimension == "center_packet_granularity":
        packet_bits, period_slots = _parse_granularity_value(str(value))
        return replace(
            updated,
            traffic=replace(
                updated.traffic,
                center=replace(
                    updated.traffic.center,
                    packet_bits=packet_bits,
                    period_slots=period_slots,
                ),
            ),
        )
    if dimension == "center_packet_load_per_6_slots":
        return replace(
            updated,
            traffic=replace(
                updated.traffic,
                center=replace(
                    updated.traffic.center,
                    packet_bits=int(value),
                    period_slots=6,
                ),
            ),
        )
    raise ValueError(f"unsupported dimension: {dimension}")


def _build_row(
    *,
    edge_packet_kb: int,
    dimension: str,
    value: int | str,
    policy: str,
    summary: Summary,
    config_metadata: dict[str, int | None],
) -> Row:
    return {
        "edge_packet_kb": edge_packet_kb,
        "edge_packet_bits": _packet_bits_from_kb(edge_packet_kb),
        "dimension": dimension,
        "value": value,
        "policy": policy,
        **config_metadata,
        **build_common_summary_row(summary),
    }


def _collect_rows(config, sweep_spec: dict[str, Any]) -> list[Row]:
    rows: list[Row] = []
    policies = tuple(sweep_spec.get("policies", ("tail_append", "business_aware_constrained_insert")))
    for edge_packet_kb in sweep_spec.get("edge_packet_kb", []):
        for edge_pdb_ms in sweep_spec.get("edge_pdb_ms", []):
            for policy in policies:
                case_config = _case_config(
                    config,
                    edge_packet_kb=int(edge_packet_kb),
                    dimension="edge_pdb_ms",
                    value=int(edge_pdb_ms),
                    policy=policy,
                )
                summary = _run_summary(case_config)
                rows.append(
                    _build_row(
                        edge_packet_kb=int(edge_packet_kb),
                        dimension="edge_pdb_ms",
                        value=int(edge_pdb_ms),
                        policy=policy,
                        summary=summary,
                        config_metadata=_config_metadata(case_config),
                    )
                )
        for center_user_count in sweep_spec.get("center_user_count", []):
            for policy in policies:
                case_config = _case_config(
                    config,
                    edge_packet_kb=int(edge_packet_kb),
                    dimension="center_user_count",
                    value=int(center_user_count),
                    policy=policy,
                )
                summary = _run_summary(case_config)
                rows.append(
                    _build_row(
                        edge_packet_kb=int(edge_packet_kb),
                        dimension="center_user_count",
                        value=int(center_user_count),
                        policy=policy,
                        summary=summary,
                        config_metadata=_config_metadata(case_config),
                    )
                )
        if int(edge_packet_kb) == CENTER_PACKET_GRANULARITY_EDGE_PACKET_KB:
            for item in sweep_spec.get("center_packet_granularity", []):
                value = _granularity_value(
                    int(item["packet_bits"]),
                    int(item["period_slots"]),
                )
                for policy in policies:
                    case_config = _case_config(
                        config,
                        edge_packet_kb=int(edge_packet_kb),
                        dimension="center_packet_granularity",
                        value=value,
                        policy=policy,
                    )
                    summary = _run_summary(case_config)
                    rows.append(
                        _build_row(
                            edge_packet_kb=int(edge_packet_kb),
                            dimension="center_packet_granularity",
                            value=value,
                            policy=policy,
                            summary=summary,
                            config_metadata=_config_metadata(case_config),
                        )
                    )
            for center_packet_bits in sweep_spec.get("center_packet_load_per_6_slots", []):
                for policy in policies:
                    case_config = _case_config(
                        config,
                        edge_packet_kb=int(edge_packet_kb),
                        dimension="center_packet_load_per_6_slots",
                        value=int(center_packet_bits),
                        policy=policy,
                    )
                    summary = _run_summary(case_config)
                    rows.append(
                        _build_row(
                            edge_packet_kb=int(edge_packet_kb),
                            dimension="center_packet_load_per_6_slots",
                            value=int(center_packet_bits),
                            policy=policy,
                            summary=summary,
                            config_metadata=_config_metadata(case_config),
                        )
                    )
    return rows


def _rows_for(rows: list[Row], *, edge_packet_kb: int, dimension: str) -> list[Row]:
    return [
        row
        for row in rows
        if int(row["edge_packet_kb"]) == edge_packet_kb and row["dimension"] == dimension
    ]


def _value_label(dimension: str, value: int | str) -> str:
    if dimension == "edge_pdb_ms":
        return f"{value} ms"
    if dimension == "center_user_count":
        return f"{value} center users"
    if dimension == "center_packet_granularity":
        packet_bits, period_slots = _parse_granularity_value(str(value))
        slot_label = "slot" if period_slots == 1 else "slots"
        return f"{packet_bits} bit / every {period_slots} {slot_label}"
    if dimension == "center_packet_load_per_6_slots":
        return f"{value} bit / every 6 slots"
    raise ValueError(f"unsupported dimension: {dimension}")


def _format_completion(row: Row) -> str:
    if bool(row["target_edge_finished"]):
        return f"{float(row['target_edge_completion_delay_ms']):.0f} ms"
    return f"unfinished ({float(row['target_edge_remaining_bits']):.0f} bit remain)"


def _format_delta(baseline: Row, ours: Row) -> str:
    if bool(baseline["target_edge_finished"]) and bool(ours["target_edge_finished"]):
        delta_ms = float(baseline["target_edge_completion_delay_ms"]) - float(
            ours["target_edge_completion_delay_ms"]
        )
        ratio = 0.0
        if float(baseline["target_edge_completion_delay_ms"]) > 0.0:
            ratio = delta_ms / float(baseline["target_edge_completion_delay_ms"]) * 100.0
        return f"{delta_ms:.0f} ms ({ratio:.1f}%)"
    if (not bool(baseline["target_edge_finished"])) and bool(ours["target_edge_finished"]):
        return "ours changes unfinished -> finished"
    if bool(baseline["target_edge_finished"]) and (not bool(ours["target_edge_finished"])):
        return "baseline better"
    return "both unfinished"


def _format_prb_utilization(row: Row) -> str:
    return f"{float(row['prb_utilization']) * 100.0:.1f}%"


def _build_load_trend_analysis(rows: list[Row]) -> list[str]:
    sorted_values = sorted(int(row["value"]) for row in rows if row["policy"] == "business_aware_constrained_insert")
    ours_by_value = {
        int(row["value"]): row for row in rows if row["policy"] == "business_aware_constrained_insert"
    }
    baseline_by_value = {
        int(row["value"]): row for row in rows if row["policy"] == "tail_append"
    }
    pivot_value = next(
        (
            value
            for value in sorted_values
            if float(ours_by_value[value]["prb_utilization"]) >= 0.95
        ),
        sorted_values[-1],
    )
    pivot_row = ours_by_value[pivot_value]
    pivot_completion = float(pivot_row["target_edge_completion_delay_ms"])
    post_pivot_rise_value = next(
        (
            value
            for value in sorted_values
            if value > pivot_value
            and float(ours_by_value[value]["target_edge_completion_delay_ms"]) > pivot_completion
        ),
        sorted_values[-1],
    )
    post_pivot_rise_row = ours_by_value[post_pivot_rise_value]
    extreme_value = sorted_values[-1]
    extreme_ours = ours_by_value[extreme_value]
    extreme_baseline = baseline_by_value[extreme_value]
    return [
        "### 中心业务负载趋势分析",
        (
            f"- 以 `Ours PRB Util` 看，`{pivot_value} bit / every 6 slots` 可视为接近饱和的拐点"
            f"（`{_format_prb_utilization(pivot_row)}`）；在这之前，继续增大中心包主要体现为资源利用率持续上升。"
        ),
        (
            f"- 过了这个拐点后，再继续增大中心负载，目标边缘包完成时延不再继续改善；"
            f"例如 `Ours Completion` 在 `{post_pivot_rise_value} bit / every 6 slots` 时升到 "
            f"`{float(post_pivot_rise_row['target_edge_completion_delay_ms']):.0f} ms`，"
            "说明系统开始进入高占用下的拥塞区。"
        ),
        (
            f"- 极端档位 `16000 bit / every 6 slots` 下，Baseline / Ours 的 `PRB Util` 分别为 "
            f"`{_format_prb_utilization(extreme_baseline)}` / `{_format_prb_utilization(extreme_ours)}`，"
            f"对应完成时延为 `{_format_completion(extreme_baseline)}` / `{_format_completion(extreme_ours)}`，"
            "可作为接近满载时的参考点。"
        ),
        "- `Center Avg Rate` 仍按目标边缘包完成前的停止窗口统计，跨策略比较时需要结合完成时间一起解读。",
        "",
    ]


def _build_table(rows: list[Row], *, dimension: str) -> list[str]:
    lines = [
        "| 参数值 | Baseline Completion | Ours Completion | Baseline Queue Wait | Ours Queue Wait | Baseline Service | Ours Service | Baseline PDB | Ours PDB | Baseline Center Avg | Ours Center Avg | Baseline PRB Util | Ours PRB Util | 结论 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    if dimension == "center_packet_granularity":
        values = sorted(
            {str(row["value"]) for row in rows},
            key=lambda item: _parse_granularity_value(item)[0],
        )
    else:
        values = sorted({int(row["value"]) for row in rows})
    for value in values:
        if dimension == "center_packet_granularity":
            baseline = next(
                row
                for row in rows
                if str(row["value"]) == value and row["policy"] == "tail_append"
            )
            ours = next(
                row
                for row in rows
                if str(row["value"]) == value
                and row["policy"] == "business_aware_constrained_insert"
            )
        else:
            baseline = next(
                row for row in rows if int(row["value"]) == value and row["policy"] == "tail_append"
            )
            ours = next(
                row
                for row in rows
                if int(row["value"]) == value
                and row["policy"] == "business_aware_constrained_insert"
            )
        lines.append(
            "| "
            f"`{_value_label(dimension, value)}` | "
            f"`{_format_completion(baseline)}` | "
            f"`{_format_completion(ours)}` | "
            f"`{float(baseline['target_edge_queue_wait_ms']):.0f} ms` | "
            f"`{float(ours['target_edge_queue_wait_ms']):.0f} ms` | "
            f"`{float(baseline['target_edge_service_time_ms']):.0f} ms` | "
            f"`{float(ours['target_edge_service_time_ms']):.0f} ms` | "
            f"`{bool(baseline['target_edge_pdb_met'])}` | "
            f"`{bool(ours['target_edge_pdb_met'])}` | "
            f"`{float(baseline['center_avg_rate_bps']):.0f} bps` | "
            f"`{float(ours['center_avg_rate_bps']):.0f} bps` | "
            f"`{_format_prb_utilization(baseline)}` | "
            f"`{_format_prb_utilization(ours)}` | "
            f"{_format_delta(baseline, ours)} |"
        )
    return lines


def _packet_size_heading(edge_packet_kb: int) -> str:
    return f"## `{edge_packet_kb} KB` 目标边缘大包场景"


def _build_packet_size_section(edge_packet_kb: int, rows: list[Row], *, metadata: dict[str, int | None]) -> str:
    pdb_rows = _rows_for(rows, edge_packet_kb=edge_packet_kb, dimension="edge_pdb_ms")
    center_rows = _rows_for(rows, edge_packet_kb=edge_packet_kb, dimension="center_user_count")
    granularity_rows = _rows_for(
        rows,
        edge_packet_kb=edge_packet_kb,
        dimension="center_packet_granularity",
    )
    load_rows = _rows_for(
        rows,
        edge_packet_kb=edge_packet_kb,
        dimension="center_packet_load_per_6_slots",
    )
    lines = [
        _packet_size_heading(edge_packet_kb),
        "",
        f"- 固定 `edge_packet_kb = {edge_packet_kb}`",
        f"- 固定 `edge_per_u_slot_prb_cap = {metadata['edge_per_u_slot_prb_cap']}`",
        f"- 中心用户 `pdb_ms = {_pdb_label(metadata['center_pdb_ms'])}`",
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
    ]
    if edge_packet_kb == CENTER_PACKET_GRANULARITY_EDGE_PACKET_KB and granularity_rows:
        lines.extend(
            [
                "### 中心业务颗粒度扫描",
                "- 固定 `edge_pdb_ms = 500`",
                "- 固定 `center_user_count = 63`",
                "- 这些档位按设计让平均 offered load 近似保持一致，重点观察颗粒度变化是否改变调度窗口利用方式。",
                "",
                *_build_table(granularity_rows, dimension="center_packet_granularity"),
                "",
                "### 中心业务颗粒度趋势分析",
                "- 重点观察中心业务更细或更粗时，目标边缘包的排队碎片化是否发生明显变化。",
                "- 重点观察两种策略在近似等 offered load 下，差异是否主要体现为 `Queue Wait` 的波动收敛。",
                "",
            ]
        )
    if edge_packet_kb == CENTER_PACKET_GRANULARITY_EDGE_PACKET_KB and load_rows:
        lines.extend(
            [
                "### 中心业务负载扫描（固定 every 6 slots）",
                "- 固定 `edge_pdb_ms = 500`",
                "- 固定 `center_user_count = 63`",
                "- 固定 `center period_slots = 6`",
                "- 这里只增大中心 `packet_bits`，因此总 offered load 增大；重点观察中心背景总 bit 数上升是否拉长边缘大包完成时延。",
                "",
                *_build_table(load_rows, dimension="center_packet_load_per_6_slots"),
                "",
                *_build_load_trend_analysis(load_rows),
            ]
        )
    lines.extend(
        [
            "### 小结",
            "- 总结该包大小下的主要收益区间、主要代价和是否出现策略收敛。",
        ]
    )
    return "\n".join(lines)


def _write_markdown_report(payload: dict[str, Any], output_dir: Path, rows: list[Row]) -> None:
    edge_packet_kb_values = [int(value) for value in payload.get("sweep", {}).get("edge_packet_kb", [])]
    edge_packet_kb_text = " / ".join(str(value) for value in edge_packet_kb_values)
    metadata = _payload_metadata(payload)
    sections = [
        "# Target Edge 大包规模敏感性测试报告",
        "",
        "## 场景设置",
        "",
        "- TDD：`DSUUU`，每 slot `1 ms`，目标包发完即停；最大 `1000` 个周期作为安全上限（`5000 ms`）",
        (
            f"- 调度资源：每个 U-slot `{metadata['total_prb_per_u_slot']} PRB`，"
            f"边缘目标用户固定 `edge_per_u_slot_prb_cap = {metadata['edge_per_u_slot_prb_cap']}`"
        ),
        f"- 中心业务配置：中心用户 `pdb_ms = {_pdb_label(metadata['center_pdb_ms'])}`",
        "- 对比策略：`tail_append` 与 `business_aware_constrained_insert`",
        f"- 扫描维度：`{edge_packet_kb_text} KB`，每档下再扫描 `PDB`、中心用户数、中心业务颗粒度与固定周期中心负载",
        "",
        "## 指标说明",
        "",
        "- `Completion Delay`：目标边缘大包从到达到完成的总时延",
        "- `Queue Wait`：目标包总时延中未真正传 bit 的累计等待时间",
        "- `Service Time`：目标包实际占用的 `U` slot 数量 × `1 ms`",
        "- `Center Avg Rate`：目标包完成前中心背景用户的平均吞吐",
        "- `PRB Utilization`：系统在当前统计窗口内的 `total_prb_used / total_prb_available`",
        "",
    ]
    for edge_packet_kb in payload.get("sweep", {}).get("edge_packet_kb", []):
        sections.extend([_build_packet_size_section(int(edge_packet_kb), rows, metadata=metadata), ""])
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


def _csv_row(row: Row) -> Row:
    return {key: ("null" if value is None else value) for key, value in row.items()}


def _write_outputs(output_dir: Path, rows: list[Row]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    csv_path = output_dir / "sensitivity_rows.csv"
    json_path = output_dir / "sensitivity_rows.json"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(_csv_row(row) for row in rows)
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    stdout_fieldnames = ["scope", "edge_packet_kb", "dimension", "value", "policy"]
    stdout_writer = csv.DictWriter(sys.stdout, fieldnames=stdout_fieldnames)
    stdout_writer.writeheader()
    stdout_writer.writerows(
        {
            "scope": "edge_packet_kb",
            "edge_packet_kb": int(row["edge_packet_kb"]),
            "dimension": str(row["dimension"]),
            "value": row["value"],
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
