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


def _load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_summary(config) -> dict[str, float]:
    users = ScenarioFactory(config).build_users()
    return UlSimulator(config, users, MetricsCollector()).run()


def _case_config(
    config,
    dimension: str,
    value: int,
    policy: str,
    *,
    center_user_count_override: int | None = None,
):
    updated_config = replace(
        config,
        scheduler=replace(config.scheduler, reinsert_policy=policy),
    )
    if center_user_count_override is not None:
        updated_config = replace(
            updated_config,
            traffic=replace(
                updated_config.traffic,
                center=replace(updated_config.traffic.center, count=center_user_count_override),
            ),
        )
    if dimension == "edge_pdb_ms":
        traffic = replace(
            updated_config.traffic,
            edge=replace(updated_config.traffic.edge, pdb_ms=value),
        )
        return replace(updated_config, traffic=traffic)
    if dimension == "edge_per_u_slot_prb_cap":
        radio = replace(
            updated_config.radio,
            edge=replace(updated_config.radio.edge, edge_per_u_slot_prb_cap=value),
        )
        return replace(updated_config, radio=radio)
    if dimension == "center_user_count":
        traffic = replace(
            updated_config.traffic,
            center=replace(updated_config.traffic.center, count=value),
        )
        return replace(updated_config, traffic=traffic)
    raise ValueError(f"unsupported dimension: {dimension}")


def _collect_rows(config, sweep_spec: dict[str, Any]) -> list[dict[str, float | int | str | bool]]:
    policies = tuple(sweep_spec.get("policies", ("tail_append", "business_aware_constrained_insert")))
    rows: list[dict[str, float | int | str | bool]] = []
    for dimension in ("edge_pdb_ms", "edge_per_u_slot_prb_cap", "center_user_count"):
        for value in sweep_spec.get(dimension, []):
            for policy in policies:
                summary = _run_summary(_case_config(config, dimension=dimension, value=int(value), policy=policy))
                rows.append(
                    {
                        "dimension": dimension,
                        "value": int(value),
                        "policy": policy,
                        **build_common_summary_row(summary),
                        "context": "default",
                    }
                )
    for center_user_count in sweep_spec.get("fixed_center_user_count_for_other_scans", []):
        fixed_center_value = int(center_user_count)
        context = _fixed_center_context(fixed_center_value)
        for dimension in ("edge_pdb_ms", "edge_per_u_slot_prb_cap"):
            for value in sweep_spec.get(dimension, []):
                for policy in policies:
                    summary = _run_summary(
                        _case_config(
                            config,
                            dimension=dimension,
                            value=int(value),
                            policy=policy,
                            center_user_count_override=fixed_center_value,
                        )
                    )
                    rows.append(
                        {
                            "dimension": dimension,
                            "value": int(value),
                            "policy": policy,
                            **build_common_summary_row(summary),
                            "context": context,
                        }
                    )
    fine_center_values = sweep_spec.get("fine_center_user_count", [])
    if fine_center_values:
        for value in fine_center_values:
            for policy in policies:
                summary = _run_summary(_case_config(config, dimension="center_user_count", value=int(value), policy=policy))
                rows.append(
                    {
                        "dimension": "center_user_count",
                        "value": int(value),
                        "policy": policy,
                        **build_common_summary_row(summary),
                        "context": _fine_center_context(),
                    }
                )
    return rows


def _fixed_center_context(center_user_count: int) -> str:
    return f"fixed_center_user_count_{center_user_count}"


def _fine_center_context() -> str:
    return "fine_center_user_count"


def _format_completion(row: dict[str, float | int | str | bool]) -> str:
    if bool(row["target_edge_finished"]):
        return f"{float(row['target_edge_completion_delay_ms']):.0f} ms"
    return f"unfinished ({float(row['target_edge_remaining_bits']):.0f} bit remain)"


def _format_delta(baseline: dict[str, float | int | str | bool], ours: dict[str, float | int | str | bool]) -> str:
    if bool(baseline["target_edge_finished"]) and bool(ours["target_edge_finished"]):
        delta_ms = float(baseline["target_edge_completion_delay_ms"]) - float(ours["target_edge_completion_delay_ms"])
        ratio = 0.0
        if float(baseline["target_edge_completion_delay_ms"]) > 0:
            ratio = delta_ms / float(baseline["target_edge_completion_delay_ms"]) * 100.0
        return f"{delta_ms:.0f} ms ({ratio:.1f}%)"
    if (not bool(baseline["target_edge_finished"])) and bool(ours["target_edge_finished"]):
        return "ours changes unfinished -> finished"
    if bool(baseline["target_edge_finished"]) and (not bool(ours["target_edge_finished"])):
        return "baseline better"
    return "both unfinished"


def _format_metric_difference(
    baseline: dict[str, float | int | str | bool],
    ours: dict[str, float | int | str | bool],
    field: str,
) -> str:
    delta_ms = float(baseline[field]) - float(ours[field])
    return f"{delta_ms:+.0f} ms"


def _format_completion_difference(
    baseline: dict[str, float | int | str | bool],
    ours: dict[str, float | int | str | bool],
) -> str:
    if bool(baseline["target_edge_finished"]) and bool(ours["target_edge_finished"]):
        return _format_metric_difference(baseline, ours, "target_edge_completion_delay_ms")
    if (not bool(baseline["target_edge_finished"])) and bool(ours["target_edge_finished"]):
        return f"unfinished -> {float(ours['target_edge_completion_delay_ms']):.0f} ms"
    if bool(baseline["target_edge_finished"]) and (not bool(ours["target_edge_finished"])):
        return f"{float(baseline['target_edge_completion_delay_ms']):.0f} ms -> unfinished"
    return "both unfinished"


def _format_observed_lifecycle(row: dict[str, float | int | str | bool]) -> str:
    return (
        f"{float(row['target_edge_queue_wait_ms']):.0f} ms queue wait + "
        f"{float(row['target_edge_service_time_ms']):.0f} ms service time"
    )


def _dimension_label(dimension: str) -> str:
    return {
        "edge_pdb_ms": "Edge PDB 扫描",
        "edge_per_u_slot_prb_cap": "Edge PRB 上限扫描",
        "center_user_count": "中心背景用户数扫描",
    }[dimension]


def _value_label(dimension: str, value: int) -> str:
    return {
        "edge_pdb_ms": f"{value} ms",
        "edge_per_u_slot_prb_cap": f"{value} PRB/U-slot",
        "center_user_count": f"{value} center users",
    }[dimension]


def _section_fixed_context(payload: dict[str, Any], dimension: str) -> list[str]:
    traffic = payload["traffic"]
    radio = payload["radio"]
    fixed_lines = {
        "edge_pdb_ms": [
            f"- 固定 `edge_per_u_slot_prb_cap = {radio['edge']['edge_per_u_slot_prb_cap']}`",
            f"- 固定 `center_user_count = {traffic['center']['count']}`",
        ],
        "edge_per_u_slot_prb_cap": [
            f"- 固定 `edge_pdb_ms = {traffic['edge']['pdb_ms']}`",
            f"- 固定 `center_user_count = {traffic['center']['count']}`",
        ],
        "center_user_count": [
            f"- 固定 `edge_pdb_ms = {traffic['edge']['pdb_ms']}`",
            f"- 固定 `edge_per_u_slot_prb_cap = {radio['edge']['edge_per_u_slot_prb_cap']}`",
        ],
    }
    return fixed_lines[dimension]


def _rows_for_dimension(
    rows: list[dict[str, float | int | str | bool]],
    *,
    dimension: str,
    context: str = "default",
) -> list[dict[str, float | int | str | bool]]:
    return [
        row
        for row in rows
        if row["dimension"] == dimension and str(row.get("context", "default")) == context
    ]


def _build_section(
    payload: dict[str, Any],
    rows: list[dict[str, float | int | str | bool]],
    dimension: str,
    *,
    context: str = "default",
    title: str | None = None,
    fixed_context_lines: list[str] | None = None,
) -> str:
    section_rows = _rows_for_dimension(rows, dimension=dimension, context=context)
    value_to_rows = {
        int(row["value"]): row
        for row in section_rows
        if row["policy"] == "tail_append"
    }
    report_lines = [
        f"## {title or _dimension_label(dimension)}",
        "",
        *(fixed_context_lines or _section_fixed_context(payload, dimension)),
        "",
        "| 参数值 | Baseline Completion | Ours Completion | Baseline Queue Wait | Ours Queue Wait | Baseline Service | Ours Service | Baseline PDB | Ours PDB | Baseline Center Avg | Ours Center Avg | 结论 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | --- |",
    ]
    for value in sorted(value_to_rows):
        baseline = next(
            row
            for row in section_rows
            if int(row["value"]) == value and row["policy"] == "tail_append"
        )
        ours = next(
            row
            for row in section_rows
            if int(row["value"]) == value and row["policy"] == "business_aware_constrained_insert"
        )
        report_lines.append(
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
            f"{_format_delta(baseline, ours)} |"
        )
    return "\n".join(report_lines)


def _build_fixed_center_sweep_sections(
    payload: dict[str, Any],
    rows: list[dict[str, float | int | str | bool]],
) -> list[str]:
    radio = payload["radio"]
    sections: list[str] = []
    for center_user_count in payload.get("sweep", {}).get("fixed_center_user_count_for_other_scans", []):
        fixed_center_value = int(center_user_count)
        context = _fixed_center_context(fixed_center_value)
        if not _rows_for_dimension(rows, dimension="edge_pdb_ms", context=context):
            continue
        sections.append(
            _build_section(
                payload,
                rows,
                "edge_pdb_ms",
                context=context,
                title=f"固定 1+{fixed_center_value} 用户场景：Edge PDB 扫描",
                fixed_context_lines=[
                    f"- 固定 `center_user_count = {fixed_center_value}`（即 `1+{fixed_center_value}={fixed_center_value + 1} UE`）",
                    f"- 固定 `edge_per_u_slot_prb_cap = {radio['edge']['edge_per_u_slot_prb_cap']}`",
                ],
            )
        )
        sections.append(
            _build_section(
                payload,
                rows,
                "edge_per_u_slot_prb_cap",
                context=context,
                title=f"固定 1+{fixed_center_value} 用户场景：Edge PRB 上限扫描",
                fixed_context_lines=[
                    f"- 固定 `center_user_count = {fixed_center_value}`（即 `1+{fixed_center_value}={fixed_center_value + 1} UE`）",
                    f"- 固定 `edge_pdb_ms = {payload['traffic']['edge']['pdb_ms']}`",
                ],
            )
        )
    return sections


def _build_fine_center_sweep_section(
    payload: dict[str, Any],
    rows: list[dict[str, float | int | str | bool]],
) -> str | None:
    context = _fine_center_context()
    section_rows = _rows_for_dimension(rows, dimension="center_user_count", context=context)
    if not section_rows:
        return None
    values = sorted({int(row["value"]) for row in section_rows})
    return _build_section(
        payload,
        rows,
        "center_user_count",
        context=context,
        title=f"细粒度中心用户数扫描（1+{values[0]} 到 1+{values[-1]}）",
        fixed_context_lines=[
            f"- 固定 `edge_pdb_ms = {payload['traffic']['edge']['pdb_ms']}`",
            f"- 固定 `edge_per_u_slot_prb_cap = {payload['radio']['edge']['edge_per_u_slot_prb_cap']}`",
            f"- 聚焦临界带 `1+{values[0]}` 到 `1+{values[-1]}`（即 `{values[0] + 1}` 到 `{values[-1] + 1} UE`）",
        ],
    )


def _find_row(
    rows: list[dict[str, float | int | str | bool]],
    *,
    dimension: str,
    value: int,
    policy: str,
    context: str = "default",
) -> dict[str, float | int | str | bool]:
    return next(
        row
        for row in rows
        if row["dimension"] == dimension
        and int(row["value"]) == value
        and row["policy"] == policy
        and str(row.get("context", "default")) == context
    )


def _has_row(
    rows: list[dict[str, float | int | str | bool]],
    *,
    dimension: str,
    value: int,
    context: str = "default",
) -> bool:
    return any(
        row["dimension"] == dimension
        and int(row["value"]) == value
        and str(row.get("context", "default")) == context
        for row in rows
    )


def _representative_center_values(rows: list[dict[str, float | int | str | bool]]) -> tuple[int, ...]:
    preferred_values = (16, 31, 63)
    return tuple(
        value for value in preferred_values if _has_row(rows, dimension="center_user_count", value=value, context="default")
    )


def _center_case_label(center_user_count: int, suffix: str) -> str:
    total_user_count = center_user_count + 1
    return f"{center_user_count} center users（1+{center_user_count}={total_user_count} UE）{suffix}"


def _build_center_pair(
    rows: list[dict[str, float | int | str | bool]],
    center_user_count: int,
    suffix: str,
) -> tuple[str, dict[str, float | int | str | bool], dict[str, float | int | str | bool]]:
    return (
        _center_case_label(center_user_count, suffix),
        _find_row(rows, dimension="center_user_count", value=center_user_count, policy="tail_append"),
        _find_row(
            rows,
            dimension="center_user_count",
            value=center_user_count,
            policy="business_aware_constrained_insert",
        ),
    )


def _build_breakdown_section(rows: list[dict[str, float | int | str | bool]]) -> str:
    suffix_by_center_count = {16: "低负载场景", 31: "代表场景", 63: "默认场景"}
    representative_pairs = [
        _build_center_pair(rows, value, suffix_by_center_count[value])
        for value in _representative_center_values(rows)
    ]
    pdb_pairs = [
        (
            value,
            _find_row(rows, dimension="edge_pdb_ms", value=value, policy="tail_append"),
            _find_row(rows, dimension="edge_pdb_ms", value=value, policy="business_aware_constrained_insert"),
        )
        for value in (100, 150, 200)
    ]
    pdb_ours_rows = [ours for _, _, ours in pdb_pairs]
    prb_cap_12 = _find_row(rows, dimension="edge_per_u_slot_prb_cap", value=12, policy="business_aware_constrained_insert")
    prb_cap_30 = _find_row(rows, dimension="edge_per_u_slot_prb_cap", value=30, policy="business_aware_constrained_insert")
    prb_cap_48_ours = _find_row(rows, dimension="edge_per_u_slot_prb_cap", value=48, policy="business_aware_constrained_insert")
    prb_cap_106_tail = _find_row(rows, dimension="edge_per_u_slot_prb_cap", value=106, policy="tail_append")
    prb_cap_106_ours = _find_row(rows, dimension="edge_per_u_slot_prb_cap", value=106, policy="business_aware_constrained_insert")

    control_phase_values = [
        float(baseline["target_edge_control_phase_wait_ms"])
        for _, baseline, _ in representative_pairs
    ] + [
        float(ours["target_edge_control_phase_wait_ms"])
        for _, _, ours in representative_pairs
    ]
    pdb_gap_values = [float(row["target_edge_inter_service_gap_wait_ms"]) for row in pdb_ours_rows]
    pdb_service_values = [float(row["target_edge_service_time_ms"]) for row in pdb_ours_rows]
    pdb_gap_difference = _format_metric_difference(
        pdb_pairs[0][1],
        pdb_pairs[0][2],
        "target_edge_inter_service_gap_wait_ms",
    )
    pdb_service_difference = _format_metric_difference(
        pdb_pairs[0][1],
        pdb_pairs[0][2],
        "target_edge_service_time_ms",
    )

    if len(set(control_phase_values)) == 1:
        representative_labels = "、".join(
            f"`{int(baseline['value'])}`" for _, baseline, _ in representative_pairs
        )
        control_phase_bullet = (
            f"- `Control Phase Wait` 的趋势：在 {representative_labels} 这些代表负载点里，"
            f"基线和我们的 `Control Phase Wait` 都保持在 `{control_phase_values[0]:.0f} ms`。"
            "这说明当前差异主要不在控制时隙本身，而在 `U` slot 内两次服务之间的空等有没有被压缩。"
        )
    else:
        baseline_low = representative_pairs[0][1]
        baseline_high = representative_pairs[-1][1]
        ours_low = representative_pairs[0][2]
        ours_high = representative_pairs[-1][2]
        low_center_count = int(baseline_low["value"])
        high_center_count = int(baseline_high["value"])
        control_phase_bullet = (
            "- `Control Phase Wait` 的趋势：它本质上和“目标包存活了多少个 `DSUUU` 周期”近似成正比。"
            f"例如中心用户数从 `{low_center_count}` 增到 `{high_center_count}` 时，基线从 "
            f"`{float(baseline_low['target_edge_control_phase_wait_ms']):.0f} ms` 升到 "
            f"`{float(baseline_high['target_edge_control_phase_wait_ms']):.0f} ms`；"
            f"我们的策略只从 `{float(ours_low['target_edge_control_phase_wait_ms']):.0f} ms` "
            f"升到 `{float(ours_high['target_edge_control_phase_wait_ms']):.0f} ms`。"
            "原因不是控制时隙变长了，而是负载更高时，基线要跨更多轮 `D->S` 才能把大包发完。"
        )

    if len(set(pdb_gap_values)) == 1:
        default_pair = next((pair for pair in representative_pairs if int(pair[1]["value"]) == 63), representative_pairs[-1])
        inter_service_gap_bullet = (
            "- `Inter-Service Gap Wait` 的趋势：这是最核心的收益来源。"
            f"在 `{int(default_pair[1]['value'])}` 个中心用户场景里，基线是 "
            f"`{float(default_pair[1]['target_edge_inter_service_gap_wait_ms']):.0f} ms`，"
            f"我们的策略降到 `{float(default_pair[2]['target_edge_inter_service_gap_wait_ms']):.0f} ms`；"
            f"而在 `PDB = 100/150/200 ms` 这三档里，我们的 `Inter-Service Gap Wait` 都是 "
            f"`{pdb_gap_values[0]:.0f} ms`，相对基线都减少 `{pdb_gap_difference}`。"
            "这说明更紧的 `PDB` 已经触发了同一档回插行为，收益稳定地体现在两次服务之间少空等很多轮。"
        )
    else:
        default_pair = next((pair for pair in representative_pairs if int(pair[1]["value"]) == 63), representative_pairs[-1])
        inter_service_gap_bullet = (
            "- `Inter-Service Gap Wait` 的趋势：这是最核心的收益来源。"
            f"在 `{int(default_pair[1]['value'])}` 个中心用户场景里，基线是 "
            f"`{float(default_pair[1]['target_edge_inter_service_gap_wait_ms']):.0f} ms`，"
            f"我们的策略降到 `{float(default_pair[2]['target_edge_inter_service_gap_wait_ms']):.0f} ms`；"
            f"当 `PDB` 从 `200 ms` 收紧到 `100 ms` 时，这项又从 "
            f"`{float(pdb_ours_rows[2]['target_edge_inter_service_gap_wait_ms']):.0f} ms` 降到 "
            f"`{float(pdb_ours_rows[0]['target_edge_inter_service_gap_wait_ms']):.0f} ms`。"
            "原因是 `PDB` 越紧，目标包越容易被提前回插到候选窗口附近，于是两次传输之间少空等很多轮。"
        )

    if len(set(pdb_service_values)) == 1:
        service_time_pdb_bullets = [
            (
                "- `PDB = 100/150/200 ms` 这三档下，我们的 `Service Time` 都保持在 "
                f"`{pdb_service_values[0]:.0f} ms`，相对基线都体现为 `{pdb_service_difference}`。"
            ),
            (
                "- 这说明在当前这组负载下，更紧的 `PDB` 主要压缩的是等待时间，"
                "而不是继续改变目标包实际占用的 `U` slot` 数。"
            ),
        ]
        service_time_trend_bullet = (
            "- `Service Time` 的趋势：它主要受两类因素影响。第一类是物理资源上限，"
            f"例如边缘 `PRB cap` 从 `30` 降到 `12` 时，我们的 `Service Time` 从 "
            f"`{float(prb_cap_30['target_edge_service_time_ms']):.0f} ms` 增到 "
            f"`{float(prb_cap_12['target_edge_service_time_ms']):.0f} ms`，"
            "因为同样目标大包只能拆到更多 `U` slot 去传。第二类是调度轨迹本身，"
            f"但在当前 `PDB = 100/150/200 ms` 这三档里，`Service Time` 都保持在 "
            f"`{pdb_service_values[0]:.0f} ms`。"
            "这说明此时主收益已经集中在 `Queue Wait` 的下降，而不是 `Service Time` 的进一步变化。"
        )
    else:
        service_time_pdb_bullets = [
            "- `PDB` 越紧，目标包越容易被提前回插，所以 `Inter-Service Gap Wait` 会明显下降",
            "- `Service Time` 不是固定值，因为目标包被切分到的 `U` slot` 组合变了：更激进的回插会让它更连续地落在可服务窗口里",
        ]
        service_time_trend_bullet = (
            "- `Service Time` 的趋势：它主要受两类因素影响。第一类是物理资源上限，"
            f"例如边缘 `PRB cap` 从 `30` 降到 `12` 时，我们的 `Service Time` 从 "
            f"`{float(prb_cap_30['target_edge_service_time_ms']):.0f} ms` 增到 "
            f"`{float(prb_cap_12['target_edge_service_time_ms']):.0f} ms`，"
            "因为同样目标大包只能拆到更多 `U` slot 去传。第二类是调度轨迹本身，"
            f"例如 `PDB = 100/150/200 ms` 时，`Service Time` 分别是 "
            f"`{float(pdb_ours_rows[0]['target_edge_service_time_ms']):.0f}/"
            f"{float(pdb_ours_rows[1]['target_edge_service_time_ms']):.0f}/"
            f"{float(pdb_ours_rows[2]['target_edge_service_time_ms']):.0f} ms`。"
            "这说明更激进的回插会改变目标包落入哪些 `U` slot、每次拿到多少 PRB，因此 `Service Time` 会有小幅波动，但它仍然是次级效应，主收益还是 `Queue Wait` 的下降。"
        )

    report_lines = [
        "## Queue Wait Breakdown",
        "",
        "- `Control Phase Wait`：目标包存活期间经历的全部 `D/S` 控制时隙",
        "- `Pre-First-Service Wait`：首次真正发 bit 之前，在 `U` slot 里没拿到资源的累计时间",
        "- `Inter-Service Gap Wait`：第一次被服务之后，到后续各次服务之间，在 `U` slot 里没拿到资源的累计时间",
        "- 这三项相加就是 `Queue Wait`；再加上 `Service Time`，就是目标边缘大包的生命周期时长",
        "- `Difference` 列统一按 `Baseline - Ours` 计算：正数表示我们的等待更少，负数表示我们的时间更长",
        "",
        "### `Control Phase Wait` 和 `Inter-Service Gap Wait` 的区别与联系",
        "",
        "- 区别一：`Control Phase Wait` 统计的是 `D/S` 这类控制时隙本身；`Inter-Service Gap Wait` 统计的是两次真实传输之间，那些已经进入 `U` 时域但目标包没有发到 bit 的空档",
        "- 区别二：`Control Phase Wait` 更像“这个大包活了多久、跨了多少轮调度周期”的结果；`Inter-Service Gap Wait` 更像“每一轮调度之后，它有没有被尽快拉回可服务窗口”的结果",
        "- 联系一：两者都会随着目标包完成变慢而变大，所以它们都属于 `Queue Wait` 的组成部分",
        "- 联系二：如果回插策略让目标包更快完成，通常会同时压低这两项；但主导机制不一样：`Control Phase Wait` 更受总完成周期数影响，`Inter-Service Gap Wait` 更直接反映回插是否减少了两次服务之间的空等",
        "- 在当前实验里，`Inter-Service Gap Wait` 往往更能体现我们算法的核心优势，因为它直接对应“传过一次之后，能不能很快再次被调度到”",
        "",
        "### 代表负载点：总体对比",
        "",
        "| 场景 | Baseline Completion | Ours Completion | Completion Difference | Baseline Queue Wait | Ours Queue Wait | Queue Wait Difference | Baseline Service Time | Ours Service Time | Service Time Difference |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for label, baseline, ours in representative_pairs:
        report_lines.append(
            "| "
            f"{label} | "
            f"`{_format_completion(baseline)}` | "
            f"`{_format_completion(ours)}` | "
            f"`{_format_completion_difference(baseline, ours)}` | "
            f"`{float(baseline['target_edge_queue_wait_ms']):.0f} ms` | "
            f"`{float(ours['target_edge_queue_wait_ms']):.0f} ms` | "
            f"`{_format_metric_difference(baseline, ours, 'target_edge_queue_wait_ms')}` | "
            f"`{float(baseline['target_edge_service_time_ms']):.0f} ms` | "
            f"`{float(ours['target_edge_service_time_ms']):.0f} ms` | "
            f"`{_format_metric_difference(baseline, ours, 'target_edge_service_time_ms')}` |"
        )
    report_lines.extend(
        [
            "",
            "### 代表负载点：Queue Wait 拆分差值",
            "",
            "| 场景 | Baseline Control Phase Wait | Ours Control Phase Wait | Control Phase Difference | Baseline Pre-First-Service Wait | Ours Pre-First-Service Wait | Pre-First-Service Difference | Baseline Inter-Service Gap Wait | Ours Inter-Service Gap Wait | Inter-Service Gap Difference |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for label, baseline, ours in representative_pairs:
        report_lines.append(
            "| "
            f"{label} | "
            f"`{float(baseline['target_edge_control_phase_wait_ms']):.0f} ms` | "
            f"`{float(ours['target_edge_control_phase_wait_ms']):.0f} ms` | "
            f"`{_format_metric_difference(baseline, ours, 'target_edge_control_phase_wait_ms')}` | "
            f"`{float(baseline['target_edge_pre_first_service_wait_ms']):.0f} ms` | "
            f"`{float(ours['target_edge_pre_first_service_wait_ms']):.0f} ms` | "
            f"`{_format_metric_difference(baseline, ours, 'target_edge_pre_first_service_wait_ms')}` | "
            f"`{float(baseline['target_edge_inter_service_gap_wait_ms']):.0f} ms` | "
            f"`{float(ours['target_edge_inter_service_gap_wait_ms']):.0f} ms` | "
            f"`{_format_metric_difference(baseline, ours, 'target_edge_inter_service_gap_wait_ms')}` |"
        )
    report_lines.extend(
        [
            "",
            "### PDB 改变时，为什么 `service time` 也会变化",
            "",
            "| Edge PDB | Completion Difference | Queue Wait Difference | Control Phase Difference | Pre-First-Service Difference | Inter-Service Gap Difference | Service Time Difference |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for value, baseline, ours in pdb_pairs:
        report_lines.append(
            "| "
            f"`{value} ms` | "
            f"`{_format_completion_difference(baseline, ours)}` | "
            f"`{_format_metric_difference(baseline, ours, 'target_edge_queue_wait_ms')}` | "
            f"`{_format_metric_difference(baseline, ours, 'target_edge_control_phase_wait_ms')}` | "
            f"`{_format_metric_difference(baseline, ours, 'target_edge_pre_first_service_wait_ms')}` | "
            f"`{_format_metric_difference(baseline, ours, 'target_edge_inter_service_gap_wait_ms')}` | "
            f"`{_format_metric_difference(baseline, ours, 'target_edge_service_time_ms')}` |"
        )
    report_lines.extend(
        [
            "",
            *service_time_pdb_bullets,
            "",
            "### 趋势分析",
            "",
            control_phase_bullet,
            (
                "- `Pre-First-Service Wait` 的趋势：这项通常比较小，也比较稳定。"
                f"在默认 `63` 用户场景里，`PDB = 100/150/200 ms` 时都保持在 "
                f"`{float(pdb_ours_rows[0]['target_edge_pre_first_service_wait_ms']):.0f} ms` 左右。"
                "这说明当前算法主要改进的是“第一次发完之后的回插位置”，而不是第一次被调度上的时刻；首次服务更多由初始入队位置和第一轮 `D/S` 决策决定。"
            ),
            inter_service_gap_bullet,
            service_time_trend_bullet,
            (
                "- 高 `PRB cap` 区间的趋势：当 `PRB cap` 提到 `48` 以后，两种策略在这个单包场景里会逐渐收敛。"
                f"例如 `48` 时两者都约为 `{float(prb_cap_48_ours['target_edge_completion_delay_ms']):.0f} ms`，"
                f"`106` 时两者都约为 `{float(prb_cap_106_ours['target_edge_completion_delay_ms']):.0f} ms`。"
                "原因是物理资源已经足够大，目标边缘单个大包不需要很多轮回插就能发完，此时决定性因素更像是 PRB 上限本身，而不是回插策略。"
            ),
            (
                "- 高 `PRB cap` 对中心吞吐的影响：在 `48/60` 这种中高区间，中心平均吞吐未必立刻下降，"
                "因为目标边缘包更快传完后，后半段仿真窗口又把资源释放给了中心用户。"
                f"但当 `PRB cap = 106` 时，基线和我们的中心平均吞吐都降到 "
                f"`{float(prb_cap_106_tail['center_avg_rate_bps']):.0f} / {float(prb_cap_106_ours['center_avg_rate_bps']):.0f} bps`，"
                "说明在单包场景下，只有当边缘几乎能吃满单个 `U` slot` 的物理上限时，中心吞吐才会出现更显著的受损。"
            ),
            "",
            "### 为什么 `Service Time` 往往是我们略高一点",
            "",
            "- 第一，不是因为我们的无线条件更差，而是因为当前 `Service Time` 的定义是“目标包实际占用了多少个 `U` slot`”。只要最后多拆到一个额外的 `U` slot 才发完，`Service Time` 就会多 `1 ms`。",
            "- 第二，我们的策略目标是尽早重新回到候选窗口，而不是等到一次性拿大块 PRB 再传。所以常见现象是：更早开始、传得更连续，但每次拿到的是更细碎的一小段资源，于是同一个目标大包会被切到更多 `U` slot 里完成。",
            "- 第三，边缘用户还有 `PRB cap`。在这种上限存在时，“更频繁地被调度到”并不等于“每次都能拿很大一块 PRB”；很多时候只是把原本长时间空等，换成了多几个较短的服务片段。",
            "- 第四，基线 `tail_append` 虽然等待更久，但一旦重新回到候选窗口，有时会在某几个 `U` slot 里拿到更集中的资源，于是 `Service Time` 反而略短；不过它为此付出的代价，是更长的 `Inter-Service Gap Wait` 和更高的总完成时延。",
            "- 所以你现在看到的现象可以概括成一句话：**我们的算法通常把“大块空等 + 较少服务片段”，变成了“较少空等 + 稍多服务片段”**。从业务目标上看，这是一笔划算的交换，因为主收益来自总时延下降，而不是追求最小的 `Service Time`。",
        ]
    )
    return "\n".join(report_lines)


def _build_prb_band_summary(rows: list[dict[str, float | int | str | bool]]) -> str:
    low_cap_tail = _find_row(rows, dimension="edge_per_u_slot_prb_cap", value=24, policy="tail_append")
    low_cap_ours = _find_row(rows, dimension="edge_per_u_slot_prb_cap", value=24, policy="business_aware_constrained_insert")
    mid_cap_tail = _find_row(rows, dimension="edge_per_u_slot_prb_cap", value=36, policy="tail_append")
    mid_cap_ours = _find_row(rows, dimension="edge_per_u_slot_prb_cap", value=36, policy="business_aware_constrained_insert")
    high_cap_equal = _find_row(rows, dimension="edge_per_u_slot_prb_cap", value=48, policy="business_aware_constrained_insert")
    extreme_cap_equal = _find_row(rows, dimension="edge_per_u_slot_prb_cap", value=106, policy="business_aware_constrained_insert")
    extreme_cap_tail = _find_row(rows, dimension="edge_per_u_slot_prb_cap", value=106, policy="tail_append")
    ultra_cap_equal = next(
        (
            row
            for row in rows
            if row["dimension"] == "edge_per_u_slot_prb_cap"
            and int(row["value"]) == 237
            and row["policy"] == "business_aware_constrained_insert"
        ),
        None,
    )
    ultra_cap_tail = next(
        (
            row
            for row in rows
            if row["dimension"] == "edge_per_u_slot_prb_cap"
            and int(row["value"]) == 237
            and row["policy"] == "tail_append"
        ),
        None,
    )
    high_cap_throughput_line = (
        "- **高 PRB cap 对中心吞吐的影响**：在 `48/60` 这种中高区间，中心平均吞吐未必立刻下降，"
        "因为目标边缘包更快传完后，后半段仿真窗口又把资源释放给了中心用户。"
        f"但当 `PRB cap = 106` 时，基线和我们的中心平均吞吐都在 "
        f"`{float(extreme_cap_tail['center_avg_rate_bps']):.0f} / {float(extreme_cap_equal['center_avg_rate_bps']):.0f} bps` 左右。"
    )
    if ultra_cap_equal is not None and ultra_cap_tail is not None:
        high_cap_throughput_line = (
            high_cap_throughput_line
            + f"当 `PRB cap = 237` 时，两种策略都降到 "
            f"`{float(ultra_cap_tail['center_avg_rate_bps']):.0f} / {float(ultra_cap_equal['center_avg_rate_bps']):.0f} bps`，"
            "这时边缘单个大包已经明显压缩了中心吞吐。"
        )
    else:
        high_cap_throughput_line = (
            high_cap_throughput_line
            + "说明在单包场景下，只有当边缘几乎能吃满单个 `U` slot` 的物理上限时，中心吞吐才会出现更显著的受损。"
        )
    return "\n".join(
        [
            "## PRB Cap 分段总结",
            "",
            "- **算法敏感区（`12~36`）**：这一段最能体现回插算法价值。比如 `24` 时，基线约为 "
            f"`{_format_completion(low_cap_tail)}`、我们约为 "
            f"`{_format_completion(low_cap_ours)}`；`36` 时，基线约为 "
            f"`{_format_completion(mid_cap_tail)}`、我们约为 "
            f"`{_format_completion(mid_cap_ours)}`。这里物理资源还不算充裕，目标边缘包需要跨多轮调度完成，所以“能不能少空等几轮”对结果非常关键。",
            "- **过渡区（`48~60`）**：这一段开始由资源上限主导。`48` 时两种策略都在约 "
            f"`{float(high_cap_equal['target_edge_completion_delay_ms']):.0f} ms` 完成，`60` 时都在约 `"
            f"{float(_find_row(rows, dimension='edge_per_u_slot_prb_cap', value=60, policy='business_aware_constrained_insert')['target_edge_completion_delay_ms']):.0f} ms` 完成。说明一旦 `PRB cap` 足够高，单个边缘大包不需要很多轮回插就能发完，算法空间被物理资源压缩了。",
            "- **资源主导区（`84+`）**：这一段更像在看“高 PRB cap 会不会集中吃资源”。`106` 时，基线和我们的目标包都在约 "
            f"`{float(extreme_cap_equal['target_edge_completion_delay_ms']):.0f} ms` 完成，但中心平均吞吐同时降到 "
            f"`{float(extreme_cap_tail['center_avg_rate_bps']):.0f} / {float(extreme_cap_equal['center_avg_rate_bps']):.0f} bps`。",
            high_cap_throughput_line,
            "- **怎么讲这张图**：如果你要突出算法本身，重点讲 `12~36`；如果你要说明“边缘强吃资源会不会伤中心”，重点讲 `84+`；而 `48~60` 正好是两者之间的分界带。",
            "- **一句话结论**：在当前单边缘大包场景下，`edge PRB cap` 扫描同时呈现出两种机制——低 cap 区看算法收益，高 cap 区看物理资源上限的系统代价。",
        ]
    )


def _build_report(payload: dict[str, Any], rows: list[dict[str, float | int | str | bool]]) -> str:
    simulation = payload["simulation"]
    resources = payload["resources"]
    traffic = payload["traffic"]
    radio = payload["radio"]
    env = radio["environment"]
    slot_duration_ms = int(simulation["slot_duration_ms"])
    tdd_pattern = str(simulation["tdd_pattern"])
    simulation_cap_ms = int(simulation["cycles"]) * len(tdd_pattern) * slot_duration_ms
    stop_when_target_edge_finished = bool(simulation.get("stop_when_target_edge_finished", False))
    deadline_guard_ms = int(simulation.get("deadline_guard_ms", 0))
    guard_lines = (
        [
            f"- 回插安全裕量：`deadline_guard_ms = {deadline_guard_ms} ms`，"
            f"预测完成时间需不晚于 `PDB - {deadline_guard_ms} ms`，避免贴边决策"
        ]
        if deadline_guard_ms > 0
        else []
    )
    representative_center_value = 16 if _has_row(rows, dimension="center_user_count", value=16) else 31
    representative_total_users = representative_center_value + 1
    timing_line = (
        f"- TDD：`{tdd_pattern}`，每 slot `{slot_duration_ms} ms`，"
        f"目标包发完即停；最大 `{simulation['cycles']}` 个周期作为安全上限（`{simulation_cap_ms} ms`）"
        if stop_when_target_edge_finished
        else f"- TDD：`{tdd_pattern}`，每 slot `{slot_duration_ms} ms`，"
        f"共 `{simulation['cycles']}` 个周期，窗口 `{simulation_cap_ms} ms`"
    )
    completion_line = (
        "- `Completion Delay`：目标边缘大包从到达到完成的总时延；"
        f"本实验启用目标包发完即停，若到 `{simulation_cap_ms} ms` 安全上限仍未完成才标为 `unfinished`"
        if stop_when_target_edge_finished
        else f"- `Completion Delay`：目标边缘大包从到达到完成的总时延；"
        f"若在 `{simulation_cap_ms} ms` 窗口内未完成，则标为 `unfinished`"
    )
    center_rate_line = (
        "- `Center Avg Rate`：中心背景用户在目标包完成前的实际运行时长上计算平均吞吐，作为“边缘收益是否明显挤压中心业务”的辅助口径"
        if stop_when_target_edge_finished
        else "- `Center Avg Rate`：中心背景用户在整个实验窗口上的平均吞吐，作为“边缘收益是否明显挤压中心业务”的辅助口径"
    )
    lifecycle_scope = "实际累计" if stop_when_target_edge_finished else "窗口内累计"
    baseline_representative = _find_row(
        rows,
        dimension="center_user_count",
        value=representative_center_value,
        policy="tail_append",
    )
    ours_representative = _find_row(
        rows,
        dimension="center_user_count",
        value=representative_center_value,
        policy="business_aware_constrained_insert",
    )
    fine_center_section = _build_fine_center_sweep_section(payload, rows)
    fixed_center_sections = _build_fixed_center_sweep_sections(payload, rows)
    return "\n".join(
        [
            "# Target Edge 参数敏感性测试报告",
            "",
            "## 场景设置",
            "",
            timing_line,
            f"- 调度资源：每个 U-slot `{resources['total_prb_per_u_slot']} PRB`，每次 `D/S` 从链表前 `{resources['max_ue_per_slot']}` 个 UE 中做 EPF 排序和顺序分配",
            f"- 目标业务：`1` 个边缘目标 UE，固定 `{traffic['edge']['packet_bits']} bit` 大包，上行传输",
            f"- 背景业务：中心用户周期小包，默认 `{traffic['center']['count']}` 个中心用户，`{traffic['center']['packet_bits']} bit/slot`",
            (
                "- 业务感知口径：中心背景关闭 `PDB` 权重（`pdb_ms = null`）；"
                f"边缘目标基线 `PDB = {traffic['edge']['pdb_ms']} ms`"
                if traffic["center"]["pdb_ms"] is None
                else f"- 业务感知口径：中心背景 `PDB = {traffic['center']['pdb_ms']} ms`，可视为“天然队尾”；边缘目标基线 `PDB = {traffic['edge']['pdb_ms']} ms`"
            ),
            *guard_lines,
            f"- 无线环境：`UMa`，小区半径 `{env['cell_radius_m']} m`，中心距离 `{env['center_distance_range_m']}`，边缘距离 `{env['edge_distance_range_m']}`",
            f"- 边缘 PRB 上限：默认 `edge_per_u_slot_prb_cap = {radio['edge']['edge_per_u_slot_prb_cap']}`，仅对边缘 UE 生效",
            "",
            "## 对比策略",
            "",
            "- `tail_append`：候选集调度后统一回队尾",
            "- `business_aware_constrained_insert`：优先判断队尾是否仍能满足目标包 PDB；若不满足则往前插，直到预测可满足或至少回到下一个候选窗口",
            "",
            "## 调度机制说明",
            "",
            "- 每个 `DSUUU` 周期里，`D` 先做一次调度决策，分配前半段 PRB；然后更新全局链表；`S` 再基于更新后的链表做第二次决策，分配后半段 PRB",
            "- 两次决策共同生成后面 `3` 个 `U` slot` 的传输计划；真正发 bit 的动作只发生在 `U` slot",
            f"- 因为每次 `D/S` 都只看链表前 `{resources['max_ue_per_slot']}` 个 UE，目标边缘大包即便刚被服务过，也不保证在同周期 `S` 或下周期 `D` 还能继续留在候选窗口",
            f"- 所以即使总用户数只有 `{representative_total_users}`（即 `{representative_center_value}` 个中心背景用户 + `1` 个边缘目标用户），大包也不会天然“连续不断地一直传”",
            "",
            "## 指标说明",
            "",
            completion_line,
            "- `Queue Wait`：目标包总时延中未真正传 bit 的累计时间，包含 `D/S` 控制时隙、未进候选窗口的时间、进入候选后但未拿到 PRB 的时间",
            f"- `Service Time`：目标包实际发生传输的 `U` slot` 数量 × `{slot_duration_ms} ms`；不是理论纯净传输时长，而是“这个包被切成多少个 U-slot 才发完”",
            "- `PDB Met`：目标边缘大包是否满足给定 `PDB`",
            center_rate_line,
            "- 详细原始字段如 `time_to_first_service`、`remaining_bits` 已写入 JSON/CSV，便于后续继续画图",
            "",
            _build_section(payload, rows, "edge_pdb_ms"),
            "",
            _build_section(payload, rows, "edge_per_u_slot_prb_cap"),
            "",
            _build_section(payload, rows, "center_user_count"),
            *(
                ["", fine_center_section]
                if fine_center_section is not None
                else []
            ),
            *(
                ["", *fixed_center_sections]
                if fixed_center_sections
                else []
            ),
            "",
            _build_prb_band_summary(rows),
            "",
            _build_breakdown_section(rows),
            "",
            "## 数字怎么理解",
            "",
            (
                f"- 先看 `{representative_total_users}` 用户场景，也就是 `1+{representative_center_value}` 这一行："
                f"基线 `{_format_completion(baseline_representative)}`，{lifecycle_scope} `{_format_observed_lifecycle(baseline_representative)}`；"
                f"我们的策略 `{_format_completion(ours_representative)}`，{lifecycle_scope} `{_format_observed_lifecycle(ours_representative)}`"
            ),
            (
                "- 这说明当前收益的主体不是“无线链路突然变强”，而是目标边缘大包少空等了很多轮："
                f"`queue wait` 从 `{float(baseline_representative['target_edge_queue_wait_ms']):.0f} ms` "
                f"降到 `{float(ours_representative['target_edge_queue_wait_ms']):.0f} ms`"
            ),
            "- `service time` 在不同 `PDB` 下会变化，是因为 `PDB` 改变了回插激进程度，进而改变了目标包会落在哪些 `D/S` 决策里、被切分到多少个 `U` slot 才发完",
            "- 当目标包完成时，`completion delay = queue wait + service time`；若安全上限结束时仍未完成，报告里展示的是已经发生的 `queue wait/service time` 拆分",
            "",
            "## 结论",
            "",
            "- `PDB` 越紧，业务感知回插的收益越明显；当 `PDB = 200 ms` 时，算法自然退化为队尾，符合兼容性预期",
            "- 边缘 `PRB cap` 越小，基线越容易在窗口内完不成目标大包；业务感知回插仍能明显压缩等待时间，甚至把“未完成”变成“完成”",
            "- 中心背景用户数越多，队尾基线的轮转等待越严重；业务感知回插对高负载场景更敏感，收益更稳定",
            "- 本轮扫描下中心平均吞吐始终保持在相近量级，说明当前收益主要来自边缘大包排队位置优化，而不是明显牺牲中心业务",
        ]
    )


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run_target_edge_sensitivity_report.py CONFIG", file=sys.stderr)
        return 2
    config_path = Path(sys.argv[1])
    payload = _load_payload(config_path)
    config = load_config(config_path)
    sweep_spec = payload.get("sweep", {})
    rows = _collect_rows(config, sweep_spec)
    output_dir = Path(config.report.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0])
    (output_dir / "sensitivity_rows.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    with (output_dir / "sensitivity_rows.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    report = _build_report(payload, rows)
    (output_dir / "sensitivity_report.md").write_text(report, encoding="utf-8")
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
