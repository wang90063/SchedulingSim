import csv
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

os.environ.setdefault(
    "MPLCONFIGDIR",
    os.path.join(tempfile.gettempdir(), "scheduling-sim-matplotlib"),
)
os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)
os.environ.setdefault(
    "XDG_CACHE_HOME",
    os.path.join(tempfile.gettempdir(), "scheduling-sim-cache"),
)
os.makedirs(os.path.join(os.environ["XDG_CACHE_HOME"], "fontconfig"), exist_ok=True)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RowValue = str | int | float | bool | None
Row = dict[str, RowValue]

INPUT_SUBDIR = "target_edge_packet_size_sensitivity_400kb"
REPORT_FILENAME = "uplink_scheduler_edge_delay_throughput_tradeoff_report.md"
USER_COUNT_DELAY_PLOT = "user_count_sensitivity_edge_delay_breakdown.png"
USER_COUNT_RATE_PLOT = "user_count_sensitivity_center_rate_prb_util.png"
CENTER_LOAD_DELAY_PLOT = "center_load_sensitivity_edge_delay_breakdown.png"
CENTER_LOAD_RATE_PLOT = "center_load_sensitivity_center_rate_prb_util.png"
ANCHOR_PLOT = "latency_throughput_tradeoff_pdb_anchors.png"
BASELINE_POLICY = "tail_append"
OURS_POLICY = "business_aware_constrained_insert"
BASELINE_COLOR = "#1f77b4"
OURS_COLOR = "#ff7f0e"


def _coerce_csv_value(value: str | None) -> RowValue:
    if value is None:
        return None
    stripped = value.strip()
    lowered = stripped.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", ""}:
        return None

    try:
        return int(stripped)
    except ValueError:
        pass

    try:
        return float(stripped)
    except ValueError:
        return stripped


def _load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_rows(path: Path) -> list[Row]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                key: _coerce_csv_value(value)
                for key, value in row.items()
                if key is not None
            }
            for row in reader
        ]


def _build_dimension_pairs(rows: list[Row], dimension: str) -> list[dict[str, Row | int]]:
    grouped: dict[int, dict[str, Row]] = {}
    for row in rows:
        if row.get("dimension") != dimension:
            continue
        if row.get("value") is None:
            raise ValueError(f"Row missing value for dimension {dimension}: {row}")
        if row.get("policy") is None:
            raise ValueError(f"Row missing policy for dimension {dimension}: {row}")
        value = int(row["value"])  # type: ignore[arg-type]
        policy = str(row["policy"])
        grouped.setdefault(value, {})[policy] = row

    pairs: list[dict[str, Row | int]] = []
    if not grouped:
        raise ValueError(f"No rows found for dimension={dimension}")
    for value in sorted(grouped):
        policies = grouped[value]
        baseline = policies.get(BASELINE_POLICY)
        ours = policies.get(OURS_POLICY)
        if baseline is None or ours is None:
            raise ValueError(
                f"Missing policies for {dimension}={value}: have {sorted(policies)}"
            )
        pairs.append({"value": value, "baseline": baseline, "ours": ours})
    return pairs


def _center_prb_util_percent(row: Row) -> float:
    return float(row["prb_utilization"]) * float(row["center_prb_share"]) * 100.0


def _edge_prb_util_percent(row: Row) -> float:
    return float(row["prb_utilization"]) * float(row["edge_prb_share"]) * 100.0


def _latency_gain_percent(baseline: Row, ours: Row) -> float:
    baseline_completion = float(baseline["target_edge_completion_delay_ms"])
    if baseline_completion == 0.0:
        raise ValueError(
            "Cannot compute latency gain: baseline target_edge_completion_delay_ms is zero"
        )
    ours_completion = float(ours["target_edge_completion_delay_ms"])
    return (baseline_completion - ours_completion) / baseline_completion * 100.0


def _throughput_retention_percent(baseline: Row, ours: Row, key: str) -> float:
    baseline_value = float(baseline[key])
    if baseline_value == 0.0:
        raise ValueError(f"Cannot compute throughput retention for {key}: baseline value is zero")
    return float(ours[key]) / baseline_value * 100.0


def _find_row(rows: list[Row], *, dimension: str, value: int, policy: str) -> Row:
    for row in rows:
        if row.get("dimension") != dimension:
            continue
        if row.get("policy") != policy:
            continue
        if row.get("value") is None:
            continue
        if int(row["value"]) != value:  # type: ignore[arg-type]
            continue
        return row
    raise ValueError(f"Row not found for dimension={dimension} value={value} policy={policy}")


def _build_tradeoff_anchor_rows(rows: list[Row]) -> list[dict[str, float | str]]:
    anchors = [
        ("PDB = 100 ms", "edge_pdb_ms", 100),
        ("PDB = 500 ms", "edge_pdb_ms", 500),
        ("High Load = 12000 bit / 6 slots", "center_packet_load_per_6_slots", 12000),
    ]

    anchor_rows: list[dict[str, float | str]] = []
    for label, dimension, value in anchors:
        baseline = _find_row(rows, dimension=dimension, value=value, policy=BASELINE_POLICY)
        ours = _find_row(rows, dimension=dimension, value=value, policy=OURS_POLICY)
        anchor_rows.append(
            {
                "label": label,
                "latency_gain_pct": _latency_gain_percent(baseline, ours),
                "center_retention_pct": _throughput_retention_percent(
                    baseline, ours, "center_avg_rate_bps"
                ),
            }
        )
    return anchor_rows


def _pair_values(pair_rows: list[dict[str, Row | int]]) -> list[int]:
    return [int(pair["value"]) for pair in pair_rows]


def _series(pair_rows: list[dict[str, Row | int]], policy_key: str, metric_key: str) -> list[float]:
    return [float(pair[policy_key][metric_key]) for pair in pair_rows]  # type: ignore[index]


def _delay_line_specs() -> list[dict[str, str]]:
    return [
        {
            "label": "baseline total delay",
            "policy_key": "baseline",
            "metric_key": "target_edge_completion_delay_ms",
            "linestyle": "-",
            "marker": "o",
            "color": BASELINE_COLOR,
        },
        {
            "label": "baseline queue wait",
            "policy_key": "baseline",
            "metric_key": "target_edge_queue_wait_ms",
            "linestyle": "--",
            "marker": "o",
            "color": BASELINE_COLOR,
        },
        {
            "label": "baseline service time",
            "policy_key": "baseline",
            "metric_key": "target_edge_service_time_ms",
            "linestyle": ":",
            "marker": "o",
            "color": BASELINE_COLOR,
        },
        {
            "label": "proposed total delay",
            "policy_key": "ours",
            "metric_key": "target_edge_completion_delay_ms",
            "linestyle": "-",
            "marker": "s",
            "color": OURS_COLOR,
        },
        {
            "label": "proposed queue wait",
            "policy_key": "ours",
            "metric_key": "target_edge_queue_wait_ms",
            "linestyle": "--",
            "marker": "s",
            "color": OURS_COLOR,
        },
        {
            "label": "proposed service time",
            "policy_key": "ours",
            "metric_key": "target_edge_service_time_ms",
            "linestyle": ":",
            "marker": "s",
            "color": OURS_COLOR,
        },
    ]


def _rate_line_specs() -> list[dict[str, str]]:
    return [
        {
            "label": "baseline center avg rate",
            "policy_key": "baseline",
            "metric_key": "center_avg_rate_bps",
            "linestyle": "-",
            "marker": "o",
            "color": BASELINE_COLOR,
        },
        {
            "label": "baseline total PRB util",
            "policy_key": "baseline",
            "metric_key": "prb_utilization",
            "linestyle": "--",
            "marker": "o",
            "color": BASELINE_COLOR,
        },
        {
            "label": "baseline center PRB util",
            "policy_key": "baseline",
            "metric_key": "center",
            "linestyle": ":",
            "marker": "o",
            "color": BASELINE_COLOR,
        },
        {
            "label": "baseline edge PRB util",
            "policy_key": "baseline",
            "metric_key": "edge",
            "linestyle": "-.",
            "marker": "o",
            "color": BASELINE_COLOR,
        },
        {
            "label": "proposed center avg rate",
            "policy_key": "ours",
            "metric_key": "center_avg_rate_bps",
            "linestyle": "-",
            "marker": "s",
            "color": OURS_COLOR,
        },
        {
            "label": "proposed total PRB util",
            "policy_key": "ours",
            "metric_key": "prb_utilization",
            "linestyle": "--",
            "marker": "s",
            "color": OURS_COLOR,
        },
        {
            "label": "proposed center PRB util",
            "policy_key": "ours",
            "metric_key": "center",
            "linestyle": ":",
            "marker": "s",
            "color": OURS_COLOR,
        },
        {
            "label": "proposed edge PRB util",
            "policy_key": "ours",
            "metric_key": "edge",
            "linestyle": "-.",
            "marker": "s",
            "color": OURS_COLOR,
        },
    ]


def _plot_edge_delay_breakdown(
    pair_rows: list[dict[str, Row | int]],
    *,
    title: str,
    xlabel: str,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    xs = _pair_values(pair_rows)

    fig, ax = plt.subplots(figsize=(10, 5))
    for spec in _delay_line_specs():
        ax.plot(
            xs,
            _series(pair_rows, spec["policy_key"], spec["metric_key"]),
            linestyle=spec["linestyle"],
            marker=spec["marker"],
            color=spec["color"],
            linewidth=1.5,
            label=spec["label"],
        )

    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Delay (ms)")
    ax.set_xticks(xs)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _plot_center_rate_prb_util(
    pair_rows: list[dict[str, Row | int]],
    *,
    title: str,
    xlabel: str,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    xs = _pair_values(pair_rows)

    fig, rate_ax = plt.subplots(figsize=(10, 5))
    util_ax = rate_ax.twinx()

    for spec in _rate_line_specs():
        metric_key = spec["metric_key"]
        policy_key = spec["policy_key"]
        if metric_key == "center_avg_rate_bps":
            ys = [value / 1000.0 for value in _series(pair_rows, policy_key, metric_key)]
            target_ax = rate_ax
        elif metric_key == "center":
            ys = [_center_prb_util_percent(pair[policy_key]) for pair in pair_rows]  # type: ignore[arg-type,index]
            target_ax = util_ax
        elif metric_key == "edge":
            ys = [_edge_prb_util_percent(pair[policy_key]) for pair in pair_rows]  # type: ignore[arg-type,index]
            target_ax = util_ax
        else:
            ys = [value * 100.0 for value in _series(pair_rows, policy_key, metric_key)]
            target_ax = util_ax
        target_ax.plot(
            xs,
            ys,
            linestyle=spec["linestyle"],
            marker=spec["marker"],
            color=spec["color"],
            linewidth=1.2,
            label=spec["label"],
        )

    rate_ax.set_title(title)
    rate_ax.set_xlabel(xlabel)
    rate_ax.set_ylabel("Center Avg Rate (kbps)")
    rate_ax.set_xticks(xs)
    rate_ax.grid(True, alpha=0.3)
    util_ax.set_ylabel("PRB Utilization (%)")

    lines, labels = rate_ax.get_legend_handles_labels()
    util_lines, util_labels = util_ax.get_legend_handles_labels()
    rate_ax.legend(lines + util_lines, labels + util_labels, fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _plot_tradeoff_anchors(
    anchor_rows: list[dict[str, float | str]],
    *,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    labels = [str(row["label"]) for row in anchor_rows]
    xs = list(range(len(anchor_rows)))

    fig, latency_ax = plt.subplots(figsize=(10, 5))
    retention_ax = latency_ax.twinx()
    latency_ax.bar(
        xs,
        [float(row["latency_gain_pct"]) for row in anchor_rows],
        width=0.45,
        alpha=0.7,
        label="Latency Gain (%)",
    )
    retention_ax.plot(
        xs,
        [float(row["center_retention_pct"]) for row in anchor_rows],
        marker="s",
        color=OURS_COLOR,
        linewidth=1.5,
        label="Center Throughput Retention (%)",
    )

    latency_ax.set_title("Latency-Throughput Tradeoff Anchors")
    latency_ax.set_ylabel("Latency Gain (%)")
    retention_ax.set_ylabel("Throughput Retention (%)")
    latency_ax.set_xticks(xs)
    latency_ax.set_xticklabels(labels, rotation=15, ha="right")
    latency_ax.grid(True, axis="y", alpha=0.3)

    lines, line_labels = latency_ax.get_legend_handles_labels()
    retention_lines, retention_labels = retention_ax.get_legend_handles_labels()
    latency_ax.legend(lines + retention_lines, line_labels + retention_labels, fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _pair_summary_line(pair_rows: list[dict[str, Row | int]], value: int) -> tuple[Row, Row]:
    for pair in pair_rows:
        if int(pair["value"]) == value:
            return pair["baseline"], pair["ours"]  # type: ignore[return-value]
    raise ValueError(f"Pair not found for value={value}")


def _payload_section(payload: dict[str, Any], name: str) -> dict[str, Any]:
    section = payload.get(name, {})
    return section if isinstance(section, dict) else {}


def _nested_section(section: dict[str, Any], name: str) -> dict[str, Any]:
    nested = section.get(name, {})
    return nested if isinstance(nested, dict) else {}


def _fmt(value: Any, digits: int = 2) -> str:
    if value is None:
        return "null"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _row_summary(pair_rows: list[dict[str, Row | int]]) -> list[str]:
    lines = [
        "| Value | Baseline Delay (ms) | Baseline Queue (ms) | Baseline Service (ms) | Ours Delay (ms) | Ours Queue (ms) | Ours Service (ms) | Latency Gain (%) | Center Throughput Retention (%) |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for pair in pair_rows:
        baseline = pair["baseline"]  # type: ignore[assignment]
        ours = pair["ours"]  # type: ignore[assignment]
        lines.append(
            "| "
            f"{pair['value']} | "
            f"{float(baseline['target_edge_completion_delay_ms']):.1f} | "
            f"{float(baseline['target_edge_queue_wait_ms']):.1f} | "
            f"{float(baseline['target_edge_service_time_ms']):.1f} | "
            f"{float(ours['target_edge_completion_delay_ms']):.1f} | "
            f"{float(ours['target_edge_queue_wait_ms']):.1f} | "
            f"{float(ours['target_edge_service_time_ms']):.1f} | "
            f"{_latency_gain_percent(baseline, ours):.2f} | "
            f"{_throughput_retention_percent(baseline, ours, 'center_avg_rate_bps'):.2f} |"
        )
    return lines


def _anchor_summary(anchor_rows: list[dict[str, float | str]]) -> list[str]:
    lines = [
        "| Anchor | Latency Gain (%) | Center Throughput Retention (%) |",
        "| --- | ---: | ---: |",
    ]
    for row in anchor_rows:
        lines.append(
            "| "
            f"{row['label']} | "
            f"{float(row['latency_gain_pct']):.2f} | "
            f"{float(row['center_retention_pct']):.2f} |"
        )
    return lines


def _rate_prb_summary(pair_rows: list[dict[str, Row | int]]) -> list[str]:
    lines = [
        "图 4 数据表（中心速率与 PRB 利用率）",
        "",
        "| Value | Baseline Center Avg Rate (kbps) | Ours Center Avg Rate (kbps) | Baseline Total PRB Util (%) | Ours Total PRB Util (%) | Baseline Center PRB Util (%) | Ours Center PRB Util (%) | Baseline Edge PRB Util (%) | Ours Edge PRB Util (%) |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for pair in pair_rows:
        baseline = pair["baseline"]  # type: ignore[assignment]
        ours = pair["ours"]  # type: ignore[assignment]
        lines.append(
            "| "
            f"{pair['value']} | "
            f"{float(baseline['center_avg_rate_bps']) / 1000.0:.2f} | "
            f"{float(ours['center_avg_rate_bps']) / 1000.0:.2f} | "
            f"{float(baseline['prb_utilization']) * 100.0:.2f} | "
            f"{float(ours['prb_utilization']) * 100.0:.2f} | "
            f"{_center_prb_util_percent(baseline):.2f} | "
            f"{_center_prb_util_percent(ours):.2f} | "
            f"{_edge_prb_util_percent(baseline):.2f} | "
            f"{_edge_prb_util_percent(ours):.2f} |"
        )
    return lines


def _delay_detail(row: Row) -> str:
    return (
        f"Completion Delay {float(row['target_edge_completion_delay_ms']):.1f} ms"
        f"（Queue Wait {float(row['target_edge_queue_wait_ms']):.1f} ms，"
        f"Service Time {float(row['target_edge_service_time_ms']):.1f} ms）"
    )


def _select_representative_value(
    pair_rows: list[dict[str, Row | int]],
    *,
    preferred_value: int | None = None,
) -> int:
    values = [int(pair["value"]) for pair in pair_rows]
    if not values:
        raise ValueError("Cannot select representative value from empty pairs")
    if preferred_value is not None and preferred_value in values:
        return preferred_value
    return values[len(values) // 2]


def _gain_transition_word(start: float, end: float) -> str:
    if end > start:
        return "扩大到"
    if end < start:
        return "回落到"
    return "保持在"


def _delay_figure_notes(
    pair_rows: list[dict[str, Row | int]],
    *,
    figure_index: int,
    x_label: str,
) -> list[str]:
    first_pair = pair_rows[0]
    last_pair = pair_rows[-1]
    baseline_first = first_pair["baseline"]  # type: ignore[assignment]
    ours_first = first_pair["ours"]  # type: ignore[assignment]
    baseline_last = last_pair["baseline"]  # type: ignore[assignment]
    ours_last = last_pair["ours"]  # type: ignore[assignment]

    low_value = int(first_pair["value"])
    high_value = int(last_pair["value"])
    low_gain = _latency_gain_percent(baseline_first, ours_first)
    high_gain = _latency_gain_percent(baseline_last, ours_last)
    high_queue_reduction = float(baseline_last["target_edge_queue_wait_ms"]) - float(
        ours_last["target_edge_queue_wait_ms"]
    )
    high_service_reduction = float(baseline_last["target_edge_service_time_ms"]) - float(
        ours_last["target_edge_service_time_ms"]
    )

    return [
        f"图 {figure_index} 横坐标：{x_label}",
        f"图 {figure_index} 纵坐标：边缘用户时延（ms）",
        f"图 {figure_index} 描述：展示两种算法下边缘用户总时延、排队时延与服务时延的分解结果。",
        "变化上看，随着横坐标增加，边缘用户总时延整体上升，且排队时延通常是主导项，"
        "说明系统负载加重后，等待阶段比实际发送阶段更容易成为瓶颈。",
        f"增益上看，在 {x_label}={low_value} 时，本策略相对基线的总时延收益为 {low_gain:.2f}%；"
        f"在 {x_label}={high_value} 时，总时延收益{_gain_transition_word(low_gain, high_gain)} {high_gain:.2f}%，"
        f"其中高负载点排队时延减少 {high_queue_reduction:.1f} ms，服务时延变化 {high_service_reduction:.1f} ms，"
        "说明收益主要来自排队等待压缩，而不是单纯牺牲服务阶段效率。",
    ]


def _rate_prb_figure_notes(
    pair_rows: list[dict[str, Row | int]],
    *,
    figure_index: int,
    x_label: str,
) -> list[str]:
    first_pair = pair_rows[0]
    last_pair = pair_rows[-1]
    baseline_first = first_pair["baseline"]  # type: ignore[assignment]
    ours_first = first_pair["ours"]  # type: ignore[assignment]
    baseline_last = last_pair["baseline"]  # type: ignore[assignment]
    ours_last = last_pair["ours"]  # type: ignore[assignment]

    low_value = int(first_pair["value"])
    high_value = int(last_pair["value"])
    low_center_retention = _throughput_retention_percent(
        baseline_first, ours_first, "center_avg_rate_bps"
    )
    high_center_retention = _throughput_retention_percent(
        baseline_last, ours_last, "center_avg_rate_bps"
    )
    baseline_total_util_high = float(baseline_last["prb_utilization"]) * 100.0
    ours_total_util_high = float(ours_last["prb_utilization"]) * 100.0
    baseline_center_util_high = _center_prb_util_percent(baseline_last)
    ours_center_util_high = _center_prb_util_percent(ours_last)
    baseline_edge_util_high = _edge_prb_util_percent(baseline_last)
    ours_edge_util_high = _edge_prb_util_percent(ours_last)

    return [
        f"图 {figure_index} 横坐标：{x_label}",
        f"图 {figure_index} 左纵坐标：中心用户平均速率（kbps）",
        f"图 {figure_index} 右纵坐标：PRB Utilization（%）",
        f"图 {figure_index} 描述：左轴展示两种算法下中心用户平均速率，右轴展示总 PRB Utilization 以及中心、边缘用户的 PRB Utilization 分解。",
        "变化上看，随着横坐标增加，中心业务平均速率与总 PRB 利用率整体抬升，"
        "同时中心/边缘 PRB 占比会随调度策略不同而重新分配，因此需要同时观察吞吐与资源占用两类指标。",
        f"增益上看，在 {x_label}={low_value} 时，本策略的中心吞吐保持率为 {low_center_retention:.2f}%，"
        f"在 {x_label}={high_value} 时，中心吞吐保持率为 {high_center_retention:.2f}%。"
        f"对应高负载点总 PRB Utilization 由 {baseline_total_util_high:.2f}% 变化到 {ours_total_util_high:.2f}%，"
        f"中心 PRB Utilization 由 {baseline_center_util_high:.2f}% 调整为 {ours_center_util_high:.2f}%，"
        f"边缘 PRB Utilization 由 {baseline_edge_util_high:.2f}% 调整为 {ours_edge_util_high:.2f}%，"
        "说明本策略在保证边缘收益的同时，主要通过资源重分配而非大幅吞吐坍塌来实现优化。",
    ]


def _render_report(
    *,
    payload: dict[str, Any],
    user_count_pairs: list[dict[str, Row | int]],
    center_load_pairs: list[dict[str, Row | int]],
    anchor_rows: list[dict[str, float | str]],
) -> str:
    simulation = _payload_section(payload, "simulation")
    resources = _payload_section(payload, "resources")
    traffic = _payload_section(payload, "traffic")
    center_traffic = _nested_section(traffic, "center")
    edge_traffic = _nested_section(traffic, "edge")
    radio = _payload_section(payload, "radio")
    environment = _nested_section(radio, "environment")
    edge_radio = _nested_section(radio, "edge")

    if not user_count_pairs:
        raise ValueError("Cannot render report: user_count_pairs is empty")
    if not center_load_pairs:
        raise ValueError("Cannot render report: center_load_pairs is empty")

    user_representative_value = _select_representative_value(
        user_count_pairs,
        preferred_value=63,
    )
    load_high_value = 12000
    user_baseline, user_ours = _pair_summary_line(user_count_pairs, user_representative_value)
    load_baseline, load_ours = _pair_summary_line(center_load_pairs, load_high_value)

    lines = [
        "# 上行调度边缘时延-吞吐权衡实验报告",
        "",
        "## 1. 实验背景与目标",
        "",
        "本实验围绕上行调度中边缘业务低时延保障与中心业务吞吐保持之间的矛盾展开，"
        "对比 tail_append 基线策略与 business_aware_constrained_insert 策略。",
        "报告目标是量化边缘业务 Completion Delay 的改善幅度、"
        "中心业务吞吐的保持水平，以及对应的 PRB 资源再分配代价。",
        "",
        "## 2. 系统实现结构、系统参数与业务模型",
        "",
        "系统在共享上行 PRB 池中同时承载中心用户周期业务与单个边缘大包业务，"
        "通过不同调度策略对边缘业务插入时机、中心业务排队与资源切分关系进行对照。",
        "",
        "| 参数 | 值 |",
        "| --- | --- |",
        f"| slot_duration_ms | {_fmt(simulation.get('slot_duration_ms'))} |",
        f"| tdd_pattern | {_fmt(simulation.get('tdd_pattern'))} |",
        f"| deadline_guard_ms | {_fmt(simulation.get('deadline_guard_ms'))} |",
        f"| PRB_per_u_slot | {_fmt(resources.get('total_prb_per_u_slot'))} |",
        f"| max_ue_per_slot | {_fmt(resources.get('max_ue_per_slot'))} |",
        f"| center_user_count | {_fmt(center_traffic.get('count'))} |",
        f"| center_packet_bits | {_fmt(center_traffic.get('packet_bits'))} |",
        f"| center_period_slots | {_fmt(center_traffic.get('period_slots'))} |",
        f"| center_pdb_ms | {_fmt(center_traffic.get('pdb_ms'))} |",
        f"| edge_user_count | {_fmt(edge_traffic.get('count'))} |",
        f"| edge_packet_bits | {_fmt(edge_traffic.get('packet_bits'))} |",
        f"| edge_pdb_ms | {_fmt(edge_traffic.get('pdb_ms'))} |",
        f"| edge_per_u_slot_prb_cap | {_fmt(edge_radio.get('edge_per_u_slot_prb_cap'))} |",
        f"| scenario_type | {_fmt(environment.get('scenario_type'))} |",
        "",
        "## 3. 指标定义与公式说明",
        "",
        "- Completion Delay：目标边缘业务从进入系统到全部比特发送完成的总历时，"
        "记为 Completion Delay = Queue Wait + Service Time。",
        "- Queue Wait：边缘业务尚未获得有效业务传输机会而产生的累计等待时间，"
        "可拆解为 Control Phase Wait、Pre-First-Service Wait 与 Inter-Service Gap Wait。",
        "- Service Time：边缘业务真正占用可发送资源并完成数据传输的业务服务时长。",
        "- Control Phase Wait：受帧结构、控制相位或不可发送时隙影响而产生的基础等待时间。",
        "- Pre-First-Service Wait：业务到达后、首次获得业务传输前的等待时间。",
        "- Inter-Service Gap Wait：首次服务之后，由于调度中断或资源让渡造成的分段服务间隔等待时间。",
        "- Analysis Window：统计中心吞吐与 PRB 使用情况的观测窗口，"
        "相关速率指标按该窗口折算。",
        "- Center Avg Rate：中心用户平均吞吐率，可写为 Center Avg Rate = center_total_bits / center_user_count / Analysis Window × 1000。",
        "- Center Throughput Retention (%)：Center Throughput Retention (%) = "
        "Ours center_avg_rate_bps / Baseline center_avg_rate_bps × 100。",
        "- PRB_available,total：Analysis Window 内全部可用于上行业务发送的 PRB 总量，"
        "记为 PRB_available,total = PRB_per_u_slot × 可用 U-slot 数。",
        "- Center PRB Utilization：Center PRB Utilization = prb_utilization × center_prb_share × 100%。",
        "- Edge PRB Utilization：Edge PRB Utilization = prb_utilization × edge_prb_share × 100%。",
        "- Latency Gain (%)：Latency Gain (%) = "
        "(Baseline Completion Delay - Ours Completion Delay) / Baseline Completion Delay × 100。",
        "",
        "## 4. 敏感度分析结果",
        "",
        "### 4.1 用户数敏感度",
        "",
        f"![User Count Edge Delay Breakdown]({USER_COUNT_DELAY_PLOT})",
        "",
        *_delay_figure_notes(
            user_count_pairs,
            figure_index=1,
            x_label="center_user_count",
        ),
        "",
        f"![User Count Center Rate and PRB Util]({USER_COUNT_RATE_PLOT})",
        "",
        *_rate_prb_figure_notes(
            user_count_pairs,
            figure_index=2,
            x_label="center_user_count",
        ),
        "",
        *_row_summary(user_count_pairs),
        "",
        f"代表点 center_user_count = {user_representative_value}: 基线 {_delay_detail(user_baseline)}，"
        f"本策略 {_delay_detail(user_ours)}，"
        f"Latency Gain = {_latency_gain_percent(user_baseline, user_ours):.2f}%。",
        "",
        "### 4.2 中心用户数据量敏感度",
        "",
        f"![Center Load Edge Delay Breakdown]({CENTER_LOAD_DELAY_PLOT})",
        "",
        *_delay_figure_notes(
            center_load_pairs,
            figure_index=3,
            x_label="center_packet_load_per_6_slots",
        ),
        "",
        f"![Center Load Center Rate and PRB Util]({CENTER_LOAD_RATE_PLOT})",
        "",
        *_rate_prb_figure_notes(
            center_load_pairs,
            figure_index=4,
            x_label="center_packet_load_per_6_slots",
        ),
        "",
        *_rate_prb_summary(center_load_pairs),
        "",
        *_row_summary(center_load_pairs),
        "",
        f"High Load = {load_high_value} bit / 6 slots: 基线 {_delay_detail(load_baseline)}，"
        f"本策略 {_delay_detail(load_ours)}，中心吞吐保持率 "
        f"{_throughput_retention_percent(load_baseline, load_ours, 'center_avg_rate_bps'):.2f}%，"
        f"对应 Latency Gain = {_latency_gain_percent(load_baseline, load_ours):.2f}%。",
        "",
        "## 5. 边缘时延收益与中心吞吐代价的权衡分析",
        "",
        f"![Latency Throughput Tradeoff Anchors]({ANCHOR_PLOT})",
        "",
        *_anchor_summary(anchor_rows),
        "",
        "锚点覆盖 PDB = 100 ms、PDB = 500 ms 与 High Load = 12000 bit / 6 slots，"
        "用于同时观察低时延约束与高中心负载下的边缘时延收益、中心吞吐保持与 PRB 代价。",
        f"其中高负载叙述锚点固定为 High Load = {load_high_value} bit / 6 slots，"
        "而非负载扫描中的末端样本值，以保持图表、表格与文字分析口径一致。",
        "",
        "## 6. 结论",
        "",
        f"- business_aware_constrained_insert 在代表用户点 center_user_count = {user_representative_value} 上显著降低边缘业务 Completion Delay。",
        f"- 在固定高负载锚点 High Load = {load_high_value} bit / 6 slots 下，边缘时延收益与中心吞吐保持率可以同时量化比较。",
        "- Queue Wait 的下降是边缘业务时延优化的主要来源，说明策略改善主要发生在等待阶段而非纯业务发送阶段。",
        "- PRB 资源在中心与边缘之间发生再分配，需结合 Center PRB Utilization 与 Edge PRB Utilization 判断代价是否可接受。",
        "- 因此，该策略更适合作为强调边缘低时延保障、同时要求中心业务吞吐退化可控的上行调度方案。",
        "",
    ]
    return "\n".join(lines)


def _write_report(output_root: Path, report_text: str) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    report_path = output_root / REPORT_FILENAME
    report_path.write_text(report_text, encoding="utf-8")
    return report_path


def _validate_cli_inputs(output_root: Path) -> tuple[Path, Path, Path] | None:
    if not output_root.exists():
        print(f"Results directory does not exist: {output_root}", file=sys.stderr)
        return None
    if not output_root.is_dir():
        print(f"Results path is not a directory: {output_root}", file=sys.stderr)
        return None

    input_dir = output_root / INPUT_SUBDIR
    if not input_dir.exists():
        print(
            f"Expected input directory is missing: {input_dir}. "
            f"Run the sensitivity job first or provide the correct results_dir.",
            file=sys.stderr,
        )
        return None
    if not input_dir.is_dir():
        print(f"Expected input path is not a directory: {input_dir}", file=sys.stderr)
        return None

    payload_path = input_dir / "config_rerun.json"
    if not payload_path.exists():
        print(f"Required config file is missing: {payload_path}", file=sys.stderr)
        return None

    rows_path = input_dir / "sensitivity_rows.csv"
    if not rows_path.exists():
        print(f"Required sensitivity CSV is missing: {rows_path}", file=sys.stderr)
        return None

    return input_dir, payload_path, rows_path


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"Usage: {argv[0]} <results_dir>", file=sys.stderr)
        return 1

    output_root = Path(argv[1])
    validated_paths = _validate_cli_inputs(output_root)
    if validated_paths is None:
        return 1

    _, payload_path, rows_path = validated_paths
    try:
        payload = _load_payload(payload_path)
        rows = _load_rows(rows_path)

        user_count_pairs = _build_dimension_pairs(rows, "center_user_count")
        center_load_pairs = _build_dimension_pairs(rows, "center_packet_load_per_6_slots")
        anchor_rows = _build_tradeoff_anchor_rows(rows)

        _plot_edge_delay_breakdown(
            user_count_pairs,
            title="User Count Sensitivity",
            xlabel="center_user_count",
            output_path=output_root / USER_COUNT_DELAY_PLOT,
        )
        _plot_center_rate_prb_util(
            user_count_pairs,
            title="User Count Sensitivity",
            xlabel="center_user_count",
            output_path=output_root / USER_COUNT_RATE_PLOT,
        )
        _plot_edge_delay_breakdown(
            center_load_pairs,
            title="Center Load Sensitivity",
            xlabel="center_packet_load_per_6_slots",
            output_path=output_root / CENTER_LOAD_DELAY_PLOT,
        )
        _plot_center_rate_prb_util(
            center_load_pairs,
            title="Center Load Sensitivity",
            xlabel="center_packet_load_per_6_slots",
            output_path=output_root / CENTER_LOAD_RATE_PLOT,
        )
        _plot_tradeoff_anchors(anchor_rows, output_path=output_root / ANCHOR_PLOT)

        report_text = _render_report(
            payload=payload,
            user_count_pairs=user_count_pairs,
            center_load_pairs=center_load_pairs,
            anchor_rows=anchor_rows,
        )
        report_path = _write_report(output_root, report_text)
    except (OSError, json.JSONDecodeError, ValueError, KeyError) as exc:
        print(f"Failed to render edge delay throughput tradeoff report: {exc}", file=sys.stderr)
        return 1

    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
