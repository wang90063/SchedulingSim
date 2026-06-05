import csv
import json
import sys
from pathlib import Path

from scheduling_sim.config import load_config
from scheduling_sim.edge_ratio_packet_sweep import (
    apply_edge_pdb_assignments,
    build_case_config,
    packet_bits_from_kb,
    random_pdb_by_ue,
    scanned_edge_user_count,
    uniform_pdb_by_ue,
)
from scheduling_sim.metrics import MetricsCollector
from scheduling_sim.scenario import ScenarioFactory
from scheduling_sim.simulator import UlSimulator


def _edge_ids(users) -> list[str]:
    return [user.ue_id for user in users if user.is_edge_user]


def _assignment_seed(
    *,
    random_seed_base: int,
    pdb_packet_kb: int,
    requested_edge_ratio_pct: int,
    repeat_index: int,
    uniform_pdb_ms: int | None,
) -> int:
    uniform_offset = 0 if uniform_pdb_ms is None else int(uniform_pdb_ms) * 100000
    return (
        int(random_seed_base)
        + int(pdb_packet_kb) * 1000
        + int(requested_edge_ratio_pct) * 10
        + int(repeat_index)
        + uniform_offset
    )


def _pdb_assignment(
    edge_ratio_sweep: dict[str, object],
    *,
    users,
    pdb_packet_kb: int,
    requested_edge_ratio_pct: int,
    repeat_index: int,
    uniform_pdb_ms: int | None,
) -> dict[str, int | None]:
    edge_ids = _edge_ids(users)
    pdb_mode = str(edge_ratio_sweep["pdb_mode"])
    if pdb_mode == "uniform":
        return uniform_pdb_by_ue(edge_ids=edge_ids, pdb_ms=int(uniform_pdb_ms))
    return random_pdb_by_ue(
        edge_ids=edge_ids,
        pdb_choices=list(edge_ratio_sweep["pdb_choices"]),
        seed=_assignment_seed(
            random_seed_base=int(edge_ratio_sweep["random_seed_base"]),
            pdb_packet_kb=pdb_packet_kb,
            requested_edge_ratio_pct=requested_edge_ratio_pct,
            repeat_index=repeat_index,
            uniform_pdb_ms=uniform_pdb_ms,
        ),
    )


def _queue_time_ms(completed_packet: dict[str, object]) -> int:
    return (
        int(completed_packet["control_slot_count_while_pending"])
        + int(completed_packet["waiting_u_slot_count_before_first_service"])
        + int(completed_packet["waiting_u_slot_count_after_first_service"])
    )


def _build_edge_user_rows(
    *,
    users,
    collector: MetricsCollector,
    requested_edge_ratio_pct: int,
    total_users: int,
    repeat_index: int,
    policy: str,
    pdb_packet_kb: int,
    pdb_mode: str,
    uniform_pdb_ms: int | None,
) -> list[dict[str, object]]:
    radio_rows = {str(row["ue_id"]): row for row in collector.build_user_radio_rows(users)}
    completed_by_ue = {
        str(item["ue_id"]): item
        for item in collector.completed_packets
        if item.get("user_class") == "edge" and item.get("ue_id") is not None
    }
    edge_users = [user for user in users if user.is_edge_user]
    edge_count = scanned_edge_user_count(
        total_users=total_users,
        requested_edge_ratio_pct=requested_edge_ratio_pct,
    )
    actual_ratio = edge_count / float(total_users) * 100.0 if total_users > 0 else 0.0
    pdb_user_count = sum(
        1 for user in edge_users if user.traffic_profile is not None and user.traffic_profile.pdb_ms is not None
    )
    non_pdb_user_count = total_users - pdb_user_count
    rows: list[dict[str, object]] = []
    for user in edge_users:
        radio = radio_rows.get(user.ue_id, {})
        pdb_ms = None if user.traffic_profile is None else user.traffic_profile.pdb_ms
        served_bits = int(collector.served_bits_by_user.get(user.ue_id, 0))
        remaining_bits = sum(int(packet.remaining_bits) for packet in user.lc.packets)
        row: dict[str, object] = {
            "pdb_mode": pdb_mode,
            "uniform_pdb_ms": "" if uniform_pdb_ms is None else int(uniform_pdb_ms),
            "pdb_packet_kb": int(pdb_packet_kb),
            "requested_edge_ratio_pct": int(requested_edge_ratio_pct),
            "actual_scanned_edge_ratio_pct": actual_ratio,
            "total_users": int(total_users),
            "scanned_edge_user_count": int(edge_count),
            "non_pdb_user_count": int(non_pdb_user_count),
            "repeat_index": int(repeat_index),
            "policy": policy,
            "ue_id": user.ue_id,
            "pdb_setting": "null" if pdb_ms is None else str(int(pdb_ms)),
            "pdb_ms": "" if pdb_ms is None else int(pdb_ms),
            "completed": "",
            "delay_ms": "",
            "queue_time_ms": "",
            "service_time_ms": "",
            "pdb_met": "",
            "served_bits": served_bits,
            "remaining_bits": remaining_bits,
            "distance_to_bs_m": radio.get("distance_to_bs_m", float(getattr(user.radio_profile, "distance_to_bs_m", 0.0))),
            "initial_sinr_db": radio.get("initial_sinr_db", ""),
            "sinr_mean_db": radio.get("sinr_mean_db", ""),
            "sinr_min_db": radio.get("sinr_min_db", ""),
            "sinr_max_db": radio.get("sinr_max_db", ""),
            "initial_mcs_index": radio.get("initial_mcs_index", ""),
            "initial_bits_per_prb": radio.get("initial_bits_per_prb", ""),
        }
        if pdb_ms is not None:
            completed = completed_by_ue.get(user.ue_id)
            if completed is not None:
                row["completed"] = True
                row["delay_ms"] = int(completed["delay_ms"])
                row["queue_time_ms"] = _queue_time_ms(completed)
                row["service_time_ms"] = int(completed["service_slot_count"])
                row["pdb_met"] = bool(int(completed["delay_ms"]) <= int(pdb_ms))
            else:
                row["completed"] = False
        rows.append(row)
    return rows


def _policy_row(
    *,
    summary: dict[str, float],
    user_rows: list[dict[str, object]],
    pdb_packet_kb: int,
    total_users: int,
    requested_edge_ratio_pct: int,
    repeat_index: int,
    policy: str,
    pdb_mode: str,
    uniform_pdb_ms: int | None,
) -> dict[str, object]:
    edge_count = scanned_edge_user_count(
        total_users=total_users,
        requested_edge_ratio_pct=requested_edge_ratio_pct,
    )
    actual_ratio = edge_count / float(total_users) * 100.0 if total_users > 0 else 0.0
    pdb_users = [row for row in user_rows if row["pdb_ms"] != ""]
    satisfied = [row for row in pdb_users if row["pdb_met"] is True]
    analysis_window_seconds = (
        float(summary["analysis_window_ms"]) / 1000.0 if float(summary["analysis_window_ms"]) > 0.0 else 0.0
    )
    pdb_edge_agg_throughput_bps = (
        0.0
        if analysis_window_seconds == 0.0
        else sum(int(row["served_bits"]) for row in pdb_users) / analysis_window_seconds
    )
    cell_total_throughput_bps = float(summary["system_agg_rate_bps"])
    non_pdb_user_count = total_users - len(pdb_users)
    non_pdb_agg_throughput_bps = cell_total_throughput_bps - pdb_edge_agg_throughput_bps
    assigned_values = [str(row["pdb_setting"]) for row in user_rows]
    return {
        "pdb_mode": pdb_mode,
        "uniform_pdb_ms": "" if uniform_pdb_ms is None else int(uniform_pdb_ms),
        "pdb_packet_kb": int(pdb_packet_kb),
        "pdb_packet_bits": packet_bits_from_kb(pdb_packet_kb),
        "requested_edge_ratio_pct": int(requested_edge_ratio_pct),
        "actual_scanned_edge_ratio_pct": actual_ratio,
        "total_users": int(total_users),
        "scanned_edge_user_count": int(edge_count),
        "non_pdb_user_count": int(non_pdb_user_count),
        "pdb_user_count": int(len(pdb_users)),
        "repeat_index": int(repeat_index),
        "policy": policy,
        "pdb_user_satisfaction_rate": 0.0 if not pdb_users else len(satisfied) / float(len(pdb_users)),
        "non_pdb_agg_throughput_bps": non_pdb_agg_throughput_bps,
        "non_pdb_avg_user_throughput_bps": (
            0.0 if non_pdb_user_count == 0 else non_pdb_agg_throughput_bps / float(non_pdb_user_count)
        ),
        "cell_total_throughput_bps": cell_total_throughput_bps,
        "pdb_edge_agg_throughput_bps": pdb_edge_agg_throughput_bps,
        "prb_utilization": float(summary["prb_utilization"]),
        "analysis_window_ms": float(summary["analysis_window_ms"]),
        "assigned_null_count": float(sum(1 for value in assigned_values if value == "null")),
        "assigned_200_count": float(sum(1 for value in assigned_values if value == "200")),
        "assigned_400_count": float(sum(1 for value in assigned_values if value == "400")),
        "assigned_600_count": float(sum(1 for value in assigned_values if value == "600")),
        "assigned_800_count": float(sum(1 for value in assigned_values if value == "800")),
    }


def _aggregate_policy_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[object, object, object, object, object], list[dict[str, object]]] = {}
    for row in rows:
        key = (
            row["pdb_mode"],
            row["uniform_pdb_ms"],
            row["pdb_packet_kb"],
            row["requested_edge_ratio_pct"],
            row["policy"],
        )
        grouped.setdefault(key, []).append(row)
    averaged = []
    for key, group in sorted(grouped.items()):
        first = group[0]
        averaged.append(
            {
                "pdb_mode": first["pdb_mode"],
                "uniform_pdb_ms": first["uniform_pdb_ms"],
                "pdb_packet_kb": first["pdb_packet_kb"],
                "pdb_packet_bits": first["pdb_packet_bits"],
                "requested_edge_ratio_pct": first["requested_edge_ratio_pct"],
                "actual_scanned_edge_ratio_pct": first["actual_scanned_edge_ratio_pct"],
                "total_users": first["total_users"],
                "scanned_edge_user_count": first["scanned_edge_user_count"],
                "non_pdb_user_count_mean": sum(float(row["non_pdb_user_count"]) for row in group) / len(group),
                "pdb_user_count_mean": sum(float(row["pdb_user_count"]) for row in group) / len(group),
                "repeat_count": len(group),
                "policy": first["policy"],
                "pdb_user_satisfaction_rate_mean": (
                    sum(float(row["pdb_user_satisfaction_rate"]) for row in group) / len(group)
                ),
                "non_pdb_agg_throughput_bps_mean": (
                    sum(float(row["non_pdb_agg_throughput_bps"]) for row in group) / len(group)
                ),
                "non_pdb_avg_user_throughput_bps_mean": (
                    sum(float(row["non_pdb_avg_user_throughput_bps"]) for row in group) / len(group)
                ),
                "cell_total_throughput_bps_mean": (
                    sum(float(row["cell_total_throughput_bps"]) for row in group) / len(group)
                ),
                "pdb_edge_agg_throughput_bps_mean": (
                    sum(float(row["pdb_edge_agg_throughput_bps"]) for row in group) / len(group)
                ),
                "prb_utilization_mean": sum(float(row["prb_utilization"]) for row in group) / len(group),
                "analysis_window_ms_mean": sum(float(row["analysis_window_ms"]) for row in group) / len(group),
                "assigned_null_count_mean": sum(float(row["assigned_null_count"]) for row in group) / len(group),
                "assigned_200_count_mean": sum(float(row["assigned_200_count"]) for row in group) / len(group),
                "assigned_400_count_mean": sum(float(row["assigned_400_count"]) for row in group) / len(group),
                "assigned_600_count_mean": sum(float(row["assigned_600_count"]) for row in group) / len(group),
                "assigned_800_count_mean": sum(float(row["assigned_800_count"]) for row in group) / len(group),
            }
        )
    return averaged


def _gain_rows(averaged_policy_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[object, object, object, object], dict[str, dict[str, object]]] = {}
    for row in averaged_policy_rows:
        key = (
            row["pdb_mode"],
            row["uniform_pdb_ms"],
            row["pdb_packet_kb"],
            row["requested_edge_ratio_pct"],
        )
        grouped.setdefault(key, {})[str(row["policy"])] = row
    rows = []
    for key, pair in sorted(grouped.items()):
        if "tail_append" not in pair or "business_aware_constrained_insert" not in pair:
            continue
        baseline = pair["tail_append"]
        ours = pair["business_aware_constrained_insert"]
        baseline_non_pdb = float(baseline["non_pdb_agg_throughput_bps_mean"])
        ours_non_pdb = float(ours["non_pdb_agg_throughput_bps_mean"])
        baseline_cell = float(baseline["cell_total_throughput_bps_mean"])
        ours_cell = float(ours["cell_total_throughput_bps_mean"])
        rows.append(
            {
                "pdb_mode": baseline["pdb_mode"],
                "uniform_pdb_ms": baseline["uniform_pdb_ms"],
                "pdb_packet_kb": baseline["pdb_packet_kb"],
                "pdb_packet_bits": baseline["pdb_packet_bits"],
                "requested_edge_ratio_pct": baseline["requested_edge_ratio_pct"],
                "actual_scanned_edge_ratio_pct": baseline["actual_scanned_edge_ratio_pct"],
                "total_users": baseline["total_users"],
                "scanned_edge_user_count": baseline["scanned_edge_user_count"],
                "non_pdb_user_count_mean": baseline["non_pdb_user_count_mean"],
                "pdb_user_count_mean": baseline["pdb_user_count_mean"],
                "repeat_count": baseline["repeat_count"],
                "baseline_policy": "tail_append",
                "ours_policy": "business_aware_constrained_insert",
                "baseline_pdb_satisfaction_rate_mean": baseline["pdb_user_satisfaction_rate_mean"],
                "ours_pdb_satisfaction_rate_mean": ours["pdb_user_satisfaction_rate_mean"],
                "pdb_satisfaction_delta_pct_points_mean": (
                    (
                        float(ours["pdb_user_satisfaction_rate_mean"])
                        - float(baseline["pdb_user_satisfaction_rate_mean"])
                    )
                    * 100.0
                ),
                "baseline_non_pdb_agg_throughput_bps_mean": baseline_non_pdb,
                "ours_non_pdb_agg_throughput_bps_mean": ours_non_pdb,
                "non_pdb_agg_throughput_delta_bps_mean": ours_non_pdb - baseline_non_pdb,
                "non_pdb_agg_throughput_delta_pct_mean": (
                    0.0
                    if baseline_non_pdb == 0.0
                    else ((ours_non_pdb - baseline_non_pdb) / baseline_non_pdb * 100.0)
                ),
                "baseline_cell_total_throughput_bps_mean": baseline_cell,
                "ours_cell_total_throughput_bps_mean": ours_cell,
                "cell_total_throughput_gain_bps_mean": ours_cell - baseline_cell,
                "cell_total_throughput_gain_pct_mean": (
                    0.0 if baseline_cell == 0.0 else ((ours_cell - baseline_cell) / baseline_cell * 100.0)
                ),
            }
        )
    return rows


def _write_table(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _format_pct(value: float) -> str:
    return f"{value * 100.0:.1f}%"


def _format_gain_pct(value: float) -> str:
    return f"{value:+.2f}%"


def _pdb_mode_title(manifest: dict[str, object]) -> str:
    mode = str(manifest.get("pdb_mode", "random"))
    total_users = manifest.get("total_users", "")
    repeat_count = manifest.get("repeat_count", "")
    if mode == "uniform":
        return f"# {total_users} 用户 Edge 占比统一 PDB 包长扫描汇总（平均 {repeat_count} 次）"
    return f"# {total_users} 用户 Edge 占比随机 PDB 包长扫描汇总（平均 {repeat_count} 次）"


def _render_summary_report(
    *,
    manifest: dict[str, object],
    summary_policy_average: list[dict[str, object]],
    summary_gain_average: list[dict[str, object]],
) -> str:
    lines = [
        _pdb_mode_title(manifest),
        "",
        "## 设置",
        "",
    ]
    reference_config = manifest.get("reference_config")
    if reference_config:
        lines.append(f"- 参考配置：`{reference_config}`")
    total_users = manifest.get("total_users")
    ratios = list(manifest.get("requested_edge_ratio_pct", []))
    if total_users != "" and ratios:
        lines.append(
            f"- 总用户数：`{total_users}`；扫描用户占比请求：`{min(ratios)}%` 到 `{max(ratios)}%`。"
        )
    mode = str(manifest.get("pdb_mode", "random"))
    if mode == "uniform":
        uniform_values = list(manifest.get("uniform_pdb_ms_values", []))
        lines.append(f"- 统一 PDB 值：`{uniform_values} ms`。")
    else:
        pdb_choices = list(manifest.get("pdb_choices", []))
        lines.append(f"- 随机 PDB 候选：`{pdb_choices} ms`。")
    if manifest.get("pdb_null_handling"):
        lines.append(f"- 汇总口径里，`pdb=null` 与其他非 PDB 用户统一并入“非 PDB 用户”。")
    if manifest.get("non_pdb_packet_bits") is not None and manifest.get("non_pdb_period_slots") is not None:
        lines.append(
            f"- `PDB>0` 用户业务按包长扫描；非 PDB 用户业务固定为 "
            f"`{manifest['non_pdb_packet_bits']} bit / {manifest['non_pdb_period_slots']} slots`。"
        )
    packet_sizes = list(manifest.get("pdb_packet_kb_values", []))
    if packet_sizes:
        lines.append(f"- 包长扫描点：`{', '.join(str(value) for value in packet_sizes)} KB`。")
    if manifest.get("repeat_count"):
        lines.append(
            f"- 每个 `包长 × 占比` 组合按同一分配对两种策略各跑 `{manifest['repeat_count']}` 次，再对指标求平均。"
        )
    lines.append("")

    averaged_by_key = {
        (
            row["pdb_mode"],
            row["uniform_pdb_ms"],
            row["pdb_packet_kb"],
            row["requested_edge_ratio_pct"],
            row["policy"],
        ): row
        for row in summary_policy_average
    }
    gain_by_key = {
        (
            row["pdb_mode"],
            row["uniform_pdb_ms"],
            row["pdb_packet_kb"],
            row["requested_edge_ratio_pct"],
        ): row
        for row in summary_gain_average
    }
    packet_keys = sorted(
        {
            (row["uniform_pdb_ms"], row["pdb_packet_kb"])
            for row in summary_policy_average
        },
        key=lambda item: ((-1 if item[0] == "" else int(item[0])), int(item[1])),
    )
    for uniform_pdb_ms, packet_kb in packet_keys:
        title = f"## 包长 {int(packet_kb)}KB"
        if uniform_pdb_ms != "":
            title = f"## 包长 {int(packet_kb)}KB / 统一 PDB {int(uniform_pdb_ms)}ms"
        lines.extend(
            [
                title,
                "",
                "| 请求占比 | 扫描用户 | 平均PDB用户数 | 平均非PDB用户数 | Ours PDB满足率 | Baseline PDB满足率 | Ours 非PDB吞吐(bps) | 小区总吞吐增益 | 平均PDB分布(null/200/400/600/800) |",
                "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        ratio_values = sorted(
            {
                int(row["requested_edge_ratio_pct"])
                for row in summary_policy_average
                if row["pdb_packet_kb"] == packet_kb and row["uniform_pdb_ms"] == uniform_pdb_ms
            }
        )
        for ratio in ratio_values:
            baseline = averaged_by_key.get((mode, uniform_pdb_ms, packet_kb, ratio, "tail_append"))
            ours = averaged_by_key.get((mode, uniform_pdb_ms, packet_kb, ratio, "business_aware_constrained_insert"))
            if baseline is None or ours is None:
                continue
            gain = gain_by_key.get((mode, uniform_pdb_ms, packet_kb, ratio), {})
            lines.append(
                "| "
                f"{ratio}% | "
                f"{int(ours['scanned_edge_user_count'])} | "
                f"{float(ours['pdb_user_count_mean']):.1f} | "
                f"{float(ours['non_pdb_user_count_mean']):.1f} | "
                f"{_format_pct(float(ours['pdb_user_satisfaction_rate_mean']))} | "
                f"{_format_pct(float(baseline['pdb_user_satisfaction_rate_mean']))} | "
                f"{float(ours['non_pdb_agg_throughput_bps_mean']):,.1f} | "
                f"{_format_gain_pct(float(gain.get('cell_total_throughput_gain_pct_mean', 0.0)))} | "
                f"{float(ours['assigned_null_count_mean']):.1f}/"
                f"{float(ours['assigned_200_count_mean']):.1f}/"
                f"{float(ours['assigned_400_count_mean']):.1f}/"
                f"{float(ours['assigned_600_count_mean']):.1f}/"
                f"{float(ours['assigned_800_count_mean']):.1f} |"
            )
        lines.append("")
    return "\n".join(lines)


def _user_row_markdown(row: dict[str, object], *, include_repeat: bool) -> str:
    completed = row["completed"]
    completed_text = "-" if completed == "" else ("是" if bool(completed) else "否")
    if row["delay_ms"] == "":
        delay_text = queue_text = service_text = pdb_met_text = "-"
    else:
        delay_text = str(row["delay_ms"])
        queue_text = str(row["queue_time_ms"])
        service_text = str(row["service_time_ms"])
        pdb_met_text = "是" if bool(row["pdb_met"]) else "否"
    distance_text = f"{float(row['distance_to_bs_m']):.1f}" if row.get("distance_to_bs_m", "") != "" else "-"
    sinr_text = f"{float(row['initial_sinr_db']):.1f}" if row.get("initial_sinr_db", "") != "" else "-"
    base = (
        f"| `{row['ue_id']}` | {row['pdb_setting']} | {completed_text} | {delay_text} | {queue_text} | "
        f"{service_text} | {pdb_met_text} | {row['remaining_bits']} | {distance_text} | {sinr_text} |"
    )
    if include_repeat:
        return f"| {int(row['repeat_index'])} " + base[1:]
    return base


def _render_user_report(rows: list[dict[str, object]], *, title: str, include_repeat: bool) -> str:
    lines = [
        title,
        "",
        "说明：`pdb_setting = null` 表示该用户本次按非 PDB 用户处理，因此时延/queue/service/PDB满足显示为 `-`。",
        "",
    ]
    packet_values = sorted({int(row["pdb_packet_kb"]) for row in rows})
    for packet_kb in packet_values:
        packet_rows = [row for row in rows if int(row["pdb_packet_kb"]) == packet_kb]
        uniform_values = sorted(
            {str(row["uniform_pdb_ms"]) for row in packet_rows},
            key=lambda value: (-1 if value == "" else int(value)),
        )
        for uniform_pdb_ms in uniform_values:
            subset = [row for row in packet_rows if str(row["uniform_pdb_ms"]) == uniform_pdb_ms]
            packet_title = f"## 包长 {packet_kb}KB"
            if uniform_pdb_ms != "":
                packet_title = f"## 包长 {packet_kb}KB / 统一 PDB {int(uniform_pdb_ms)}ms"
            lines.extend([packet_title, ""])
            ratio_values = sorted({int(row["requested_edge_ratio_pct"]) for row in subset})
            for ratio in ratio_values:
                ratio_rows = [row for row in subset if int(row["requested_edge_ratio_pct"]) == ratio]
                lines.extend([f"### 请求占比 {ratio}%", ""])
                policy_values = [
                    policy
                    for policy in ("tail_append", "business_aware_constrained_insert")
                    if any(str(row["policy"]) == policy for row in ratio_rows)
                ]
                for policy in policy_values:
                    policy_rows = [row for row in ratio_rows if str(row["policy"]) == policy]
                    lines.extend([f"#### `{policy}`", ""])
                    if include_repeat:
                        lines.append(
                            "| Repeat | UE | PDB设置 | 完成 | 时延(ms) | Queue(ms) | Service(ms) | PDB满足 | 剩余bit | Distance(m) | Initial SINR(dB) |"
                        )
                        lines.append(
                            "| ---: | --- | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |"
                        )
                    else:
                        lines.append(
                            "| UE | PDB设置 | 完成 | 时延(ms) | Queue(ms) | Service(ms) | PDB满足 | 剩余bit | Distance(m) | Initial SINR(dB) |"
                        )
                        lines.append("| --- | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |")
                    for row in policy_rows:
                        lines.append(_user_row_markdown(row, include_repeat=include_repeat))
                    lines.append("")
    return "\n".join(lines)


def _write_outputs(
    *,
    output_dir: Path,
    manifest: dict[str, object],
    pdb_assignments: dict[str, object],
    raw_summaries: list[dict[str, object]],
    summary_policy_per_repeat: list[dict[str, object]],
    summary_policy_average: list[dict[str, object]],
    summary_gain_average: list[dict[str, object]],
    user_rows: list[dict[str, object]],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "experiment_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output_dir / "pdb_assignments.json").write_text(json.dumps(pdb_assignments, indent=2), encoding="utf-8")
    (output_dir / "raw_simulator_summaries.json").write_text(json.dumps(raw_summaries, indent=2), encoding="utf-8")
    (output_dir / "summary_policy_per_repeat.json").write_text(
        json.dumps(summary_policy_per_repeat, indent=2), encoding="utf-8"
    )
    (output_dir / "summary_policy_average.json").write_text(
        json.dumps(summary_policy_average, indent=2), encoding="utf-8"
    )
    (output_dir / "summary_gain_average.json").write_text(
        json.dumps(summary_gain_average, indent=2), encoding="utf-8"
    )
    (output_dir / "user_report.json").write_text(json.dumps(user_rows, indent=2), encoding="utf-8")
    _write_table(output_dir / "summary_policy_per_repeat.csv", summary_policy_per_repeat)
    _write_table(output_dir / "summary_policy_average.csv", summary_policy_average)
    _write_table(output_dir / "summary_gain_average.csv", summary_gain_average)
    _write_table(output_dir / "user_report.csv", user_rows)

    per_repeat_dir = output_dir / "user_reports_by_repeat"
    per_repeat_dir.mkdir(parents=True, exist_ok=True)
    for repeat_index in sorted({int(row["repeat_index"]) for row in user_rows}):
        repeat_rows = [row for row in user_rows if int(row["repeat_index"]) == repeat_index]
        _write_table(per_repeat_dir / f"repeat_{repeat_index:02d}.csv", repeat_rows)
        (per_repeat_dir / f"repeat_{repeat_index:02d}.json").write_text(
            json.dumps(repeat_rows, indent=2), encoding="utf-8"
        )
        (per_repeat_dir / f"repeat_{repeat_index:02d}.md").write_text(
            _render_user_report(
                repeat_rows,
                title=f"# Repeat {repeat_index:02d} 用户明细",
                include_repeat=False,
            ),
            encoding="utf-8",
        )

    (output_dir / "user_report.md").write_text(
        _render_user_report(
            user_rows,
            title=f"# {manifest.get('total_users', '')} 用户逐用户明细（包长扫描，{manifest.get('repeat_count', '')} 次随机）",
            include_repeat=True,
        ),
        encoding="utf-8",
    )
    (output_dir / "summary_report.md").write_text(
        _render_summary_report(
            manifest=manifest,
            summary_policy_average=summary_policy_average,
            summary_gain_average=summary_gain_average,
        ),
        encoding="utf-8",
    )


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run_edge_ratio_packet_sweep_report.py CONFIG", file=sys.stderr)
        return 2

    config_path = Path(sys.argv[1])
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    edge_ratio_sweep = payload["edge_ratio_sweep"]
    base_config = load_config(config_path)
    summary_policy_per_repeat: list[dict[str, object]] = []
    user_rows: list[dict[str, object]] = []
    raw_summaries: list[dict[str, object]] = []
    pdb_assignments: dict[str, object] = {}
    total_users = int(edge_ratio_sweep["total_users"])
    pdb_mode = str(edge_ratio_sweep["pdb_mode"])
    requested_ratios = [int(value) for value in edge_ratio_sweep["requested_edge_ratio_pct"]]
    packet_sizes = [int(value) for value in edge_ratio_sweep["pdb_packet_kb_values"]]
    uniform_values = (
        [None]
        if pdb_mode == "random"
        else [int(value) for value in edge_ratio_sweep["uniform_pdb_ms_values"]]
    )

    for uniform_pdb_ms in uniform_values:
        for pdb_packet_kb in packet_sizes:
            packet_key = str(pdb_packet_kb) if uniform_pdb_ms is None else f"{pdb_packet_kb}_pdb_{uniform_pdb_ms}"
            pdb_assignments[packet_key] = {}
            for requested_edge_ratio_pct in requested_ratios:
                ratio_key = str(requested_edge_ratio_pct)
                pdb_assignments[packet_key][ratio_key] = {}
                for repeat_index in range(int(edge_ratio_sweep["repeat_count"])):
                    repeat_key = str(repeat_index)
                    assignment_users = ScenarioFactory(
                        build_case_config(
                            base_config,
                            total_users=total_users,
                            requested_edge_ratio_pct=requested_edge_ratio_pct,
                            pdb_packet_kb=pdb_packet_kb,
                            policy="tail_append",
                        )
                    ).build_users()
                    assignment = _pdb_assignment(
                        edge_ratio_sweep,
                        users=assignment_users,
                        pdb_packet_kb=pdb_packet_kb,
                        requested_edge_ratio_pct=requested_edge_ratio_pct,
                        repeat_index=repeat_index,
                        uniform_pdb_ms=uniform_pdb_ms,
                    )
                    pdb_assignments[packet_key][ratio_key][repeat_key] = {
                        "pdb_packet_kb": int(pdb_packet_kb),
                        "requested_edge_ratio_pct": int(requested_edge_ratio_pct),
                        "repeat_index": int(repeat_index),
                        "uniform_pdb_ms": "" if uniform_pdb_ms is None else int(uniform_pdb_ms),
                        "pdb_by_ue": assignment,
                    }

                    for policy in edge_ratio_sweep["policies"]:
                        case_config = build_case_config(
                            base_config,
                            total_users=total_users,
                            requested_edge_ratio_pct=requested_edge_ratio_pct,
                            pdb_packet_kb=pdb_packet_kb,
                            policy=str(policy),
                        )
                        users = ScenarioFactory(case_config).build_users()
                        apply_edge_pdb_assignments(users, assignment)
                        collector = MetricsCollector()
                        summary = UlSimulator(case_config, users, collector).run()
                        raw_summaries.append(
                            {
                                "pdb_mode": pdb_mode,
                                "uniform_pdb_ms": "" if uniform_pdb_ms is None else int(uniform_pdb_ms),
                                "pdb_packet_kb": int(pdb_packet_kb),
                                "requested_edge_ratio_pct": int(requested_edge_ratio_pct),
                                "repeat_index": int(repeat_index),
                                "scanned_edge_user_count": len([user for user in users if user.is_edge_user]),
                                "base_center_user_count": len([user for user in users if not user.is_edge_user]),
                                "policy": str(policy),
                                "summary": summary,
                            }
                        )
                        edge_user_rows = _build_edge_user_rows(
                            users=users,
                            collector=collector,
                            requested_edge_ratio_pct=requested_edge_ratio_pct,
                            total_users=total_users,
                            repeat_index=repeat_index,
                            policy=str(policy),
                            pdb_packet_kb=pdb_packet_kb,
                            pdb_mode=pdb_mode,
                            uniform_pdb_ms=uniform_pdb_ms,
                        )
                        user_rows.extend(edge_user_rows)
                        summary_policy_per_repeat.append(
                            _policy_row(
                                summary=summary,
                                user_rows=edge_user_rows,
                                pdb_packet_kb=pdb_packet_kb,
                                total_users=total_users,
                                requested_edge_ratio_pct=requested_edge_ratio_pct,
                                repeat_index=repeat_index,
                                policy=str(policy),
                                pdb_mode=pdb_mode,
                                uniform_pdb_ms=uniform_pdb_ms,
                            )
                        )

    summary_policy_average = _aggregate_policy_rows(summary_policy_per_repeat)
    summary_gain_average = _gain_rows(summary_policy_average)
    output_dir = Path(base_config.report.output_dir)
    manifest = {
        "reference_config": edge_ratio_sweep["reference_config"],
        "output_dir": str(output_dir),
        "total_users": total_users,
        "requested_edge_ratio_pct": requested_ratios,
        "scanned_edge_user_count_rule": "nearest integer: int(total_users * ratio / 100 + 0.5)",
        "pdb_choices": list(edge_ratio_sweep.get("pdb_choices", [])),
        "repeat_count": int(edge_ratio_sweep["repeat_count"]),
        "pdb_mode": pdb_mode,
        "pdb_null_handling": "PDB=null is treated as non-PDB user and is not separated from other non-PDB users in summary metrics",
        "random_seed_base": int(edge_ratio_sweep.get("random_seed_base", 0)),
        "uniform_pdb_ms_values": (
            [] if pdb_mode == "random" else [int(value) for value in edge_ratio_sweep["uniform_pdb_ms_values"]]
        ),
        "pdb_packet_kb_values": packet_sizes,
        "policies": list(edge_ratio_sweep["policies"]),
        "baseline_policy": "tail_append",
        "ours_policy": "business_aware_constrained_insert",
        "non_pdb_packet_bits": int(edge_ratio_sweep.get("non_pdb_packet_bits", 0)),
        "non_pdb_period_slots": int(edge_ratio_sweep.get("non_pdb_period_slots", 0)),
        "user_report_extra_columns": [
            "queue_time_ms",
            "service_time_ms",
            "distance_to_bs_m",
            "initial_sinr_db",
            "sinr_mean_db",
            "sinr_min_db",
            "sinr_max_db",
            "initial_mcs_index",
            "initial_bits_per_prb",
        ],
        "per_repeat_user_report_dir": str(output_dir / "user_reports_by_repeat"),
        "pairing_rule": (
            "For the same packet_kb, ratio, repeat, the identical random PDB assignment is reused across policies"
            if pdb_mode == "random"
            else "For the same packet_kb, ratio, repeat, the identical uniform PDB assignment is reused across policies"
        ),
        "pdb_satisfaction_denominator": "PDB>0 users only; unfinished PDB users count as not met",
    }
    _write_outputs(
        output_dir=output_dir,
        manifest=manifest,
        pdb_assignments=pdb_assignments,
        raw_summaries=raw_summaries,
        summary_policy_per_repeat=summary_policy_per_repeat,
        summary_policy_average=summary_policy_average,
        summary_gain_average=summary_gain_average,
        user_rows=user_rows,
    )
    print(output_dir / "summary_report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
