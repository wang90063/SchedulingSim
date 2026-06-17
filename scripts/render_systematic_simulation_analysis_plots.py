import csv
import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def ratio_axis_labels(output_dir: Path) -> dict[str, str]:
    manifest = json.loads((output_dir / "experiment_manifest.json").read_text(encoding="utf-8"))
    if str(manifest.get("scan_mode", "")) == "load_ratio":
        x_label = "target_rho_bg" if "rho_bg_values" in manifest else "rho_bg"
        y_label = "target_rho_pdb" if "rho_pdb_values" in manifest else "rho_pdb"
        return {
            "x_label": x_label,
            "y_label": y_label,
            "panel_label": "pdb_ms / pdb_packet_kb",
            "size_label": "prb_share_pdb",
        }
    return {
        "x_label": "background_user_count",
        "y_label": "pdb_user_count",
        "panel_label": "pdb_ms / pdb_packet_kb",
        "size_label": "none",
    }


def _scene_value(
    rows: list[dict[str, str]],
    *,
    pdb_ms: int,
    pdb_packet_kb: int,
    background_user_count: int,
    pdb_user_count: int,
    field_name: str,
) -> float:
    for row in rows:
        if (
            int(row["pdb_ms"]) == pdb_ms
            and int(row["pdb_packet_kb"]) == pdb_packet_kb
            and int(row["background_user_count"]) == background_user_count
            and int(row["pdb_user_count"]) == pdb_user_count
        ):
            return float(row[field_name])
    return math.nan


def _grid_value(
    rows: list[dict[str, str]],
    *,
    pdb_ms: int,
    pdb_packet_kb: int,
    background_user_count: int,
    pdb_user_count: int,
    field_name: str,
) -> float:
    for row in rows:
        if (
            int(row["pdb_ms"]) == pdb_ms
            and int(row["pdb_packet_kb"]) == pdb_packet_kb
            and int(row["background_user_count"]) == background_user_count
            and int(row["pdb_user_count"]) == pdb_user_count
        ):
            return float(row[field_name])
    return math.nan


def _heatmap_grid(
    rows: list[dict[str, str]],
    manifest: dict[str, object],
    *,
    field_name: str,
    title: str,
    output_path: Path,
) -> None:
    pdb_ms_values = [int(value) for value in manifest["pdb_ms_values"]]
    packet_values = [int(value) for value in manifest["pdb_packet_kb_values"]]
    background_values = [int(value) for value in manifest["background_user_count_values"]]
    pdb_user_values = [int(value) for value in manifest["pdb_user_count_values"]]
    fig, axes = plt.subplots(
        len(pdb_ms_values),
        len(packet_values),
        figsize=(12, 10),
        constrained_layout=True,
        squeeze=False,
    )
    for row_index, pdb_ms in enumerate(pdb_ms_values):
        for col_index, packet_kb in enumerate(packet_values):
            ax = axes[row_index][col_index]
            matrix = [
                [
                    _scene_value(
                        rows,
                        pdb_ms=pdb_ms,
                        pdb_packet_kb=packet_kb,
                        background_user_count=background_user_count,
                        pdb_user_count=pdb_user_count,
                        field_name=field_name,
                    )
                    for background_user_count in background_values
                ]
                for pdb_user_count in pdb_user_values
            ]
            image = ax.imshow(matrix, aspect="auto", origin="lower")
            image.cmap.set_bad(color="#d9d9d9")
            ax.set_title(f"PDB {pdb_ms} ms / {packet_kb} KB")
            ax.set_xticks(range(len(background_values)), labels=[str(value) for value in background_values])
            ax.set_yticks(range(len(pdb_user_values)), labels=[str(value) for value in pdb_user_values])
            ax.set_xlabel("background_user_count")
            ax.set_ylabel("pdb_user_count")
            fig.colorbar(image, ax=ax, shrink=0.75)
    fig.suptitle(title)
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def _ratio_scene_value(
    rows: list[dict[str, str]],
    *,
    pdb_ms: int,
    pdb_packet_kb: float,
    rho_bg: float,
    rho_pdb: float,
    field_name: str,
    x_field: str,
    y_field: str,
) -> float:
    for row in rows:
        if (
            int(row["pdb_ms"]) == pdb_ms
            and math.isclose(float(row["pdb_packet_kb"]), pdb_packet_kb, rel_tol=0.0, abs_tol=1e-9)
            and math.isclose(float(row[x_field]), rho_bg, rel_tol=0.0, abs_tol=1e-9)
            and math.isclose(float(row[y_field]), rho_pdb, rel_tol=0.0, abs_tol=1e-9)
        ):
            return float(row[field_name])
    return math.nan


def _business_scene_value(
    rows: list[dict[str, str]],
    *,
    target_rho_bg: float,
    target_rho_pdb: float,
    pdb_ms: int,
    background_user_count: int,
    pdb_user_count: int,
    field_name: str,
    x_field: str,
    y_field: str,
) -> float:
    for row in rows:
        if (
            int(row["pdb_ms"]) == pdb_ms
            and int(row["background_user_count"]) == background_user_count
            and int(row["pdb_user_count"]) == pdb_user_count
            and math.isclose(float(row[x_field]), target_rho_bg, rel_tol=0.0, abs_tol=1e-9)
            and math.isclose(float(row[y_field]), target_rho_pdb, rel_tol=0.0, abs_tol=1e-9)
        ):
            return float(row[field_name])
    return math.nan


def _business_baseline_prb_value(
    rows: list[dict[str, str]],
    *,
    target_rho_bg: float,
    target_rho_pdb: float,
    pdb_ms: int,
    background_user_count: int,
    pdb_user_count: int,
    x_field: str,
    y_field: str,
) -> float:
    values = [
        float(row["prb_utilization"])
        for row in rows
        if int(row["pdb_ms"]) == pdb_ms
        and int(row["background_user_count"]) == background_user_count
        and int(row["pdb_user_count"]) == pdb_user_count
        and math.isclose(float(row[x_field]), target_rho_bg, rel_tol=0.0, abs_tol=1e-9)
        and math.isclose(float(row[y_field]), target_rho_pdb, rel_tol=0.0, abs_tol=1e-9)
    ]
    if not values:
        return math.nan
    return sum(values) / float(len(values))


def _ratio_fields(manifest: dict[str, object], rows: list[dict[str, str]]) -> tuple[str, str]:
    if str(manifest.get("scan_mode", "")) != "load_ratio":
        raise ValueError("ratio fields are only valid for load-ratio manifests")
    if "rho_bg_values" in manifest and rows and "target_rho_bg" in rows[0] and "target_rho_pdb" in rows[0]:
        return ("target_rho_bg", "target_rho_pdb")
    return ("rho_bg", "rho_pdb")


def _ratio_shape_pairs(manifest: dict[str, object], rows: list[dict[str, str]]) -> list[tuple[int, float]]:
    if "pdb_shapes" in manifest:
        return [
            (int(shape["pdb_ms"]), float(packet_kb))
            for shape in manifest["pdb_shapes"]
            for packet_kb in shape["pdb_packet_kb_values"]
        ]
    return sorted({(int(row["pdb_ms"]), float(row["pdb_packet_kb"])) for row in rows})


def _per_run_baseline_prb_rows(output_dir: Path) -> list[dict[str, str]]:
    path = output_dir / "per_run_rows.csv"
    if not path.exists():
        return []
    rows = _rows(path)
    return [row for row in rows if str(row.get("policy", "")) == "tail_append"]


def _per_run_rows(output_dir: Path) -> list[dict[str, str]]:
    path = output_dir / "per_run_rows.csv"
    if not path.exists():
        return []
    return _rows(path)


def _relative_packet_gain_rows(
    rows: list[dict[str, str]],
    *,
    baseline_policy: str,
    proposed_policy: str,
) -> list[dict[str, str]]:
    required_fields = {
        "policy",
        "edge_pdb_satisfaction_rate",
        "pdb_arrivals_in_window",
        "background_user_count",
        "pdb_user_count",
        "pdb_ms",
    }
    if not rows or not required_fields.issubset(rows[0]):
        return []
    x_field = "target_rho_bg" if "target_rho_bg" in rows[0] else "rho_bg"
    y_field = "target_rho_pdb" if "target_rho_pdb" in rows[0] else "rho_pdb"
    key_fields = [
        x_field,
        y_field,
        "background_user_count",
        "pdb_user_count",
        "pdb_ms",
    ]
    groups: dict[tuple[str, ...], dict[str, object]] = {}
    for row in rows:
        policy = str(row.get("policy", ""))
        if policy not in {baseline_policy, proposed_policy}:
            continue
        if x_field not in row or y_field not in row:
            continue
        key = tuple(str(row[field]) for field in key_fields)
        group = groups.setdefault(
            key,
            {
                "template": {field: str(row[field]) for field in key_fields},
                "baseline_satisfied_packets": 0.0,
                "proposed_satisfied_packets": 0.0,
            },
        )
        satisfied_packets = float(row["edge_pdb_satisfaction_rate"]) * float(row["pdb_arrivals_in_window"])
        if policy == baseline_policy:
            group["baseline_satisfied_packets"] = float(group["baseline_satisfied_packets"]) + satisfied_packets
        else:
            group["proposed_satisfied_packets"] = float(group["proposed_satisfied_packets"]) + satisfied_packets

    output_rows: list[dict[str, str]] = []
    for key in sorted(groups):
        group = groups[key]
        baseline_satisfied = float(group["baseline_satisfied_packets"])
        proposed_satisfied = float(group["proposed_satisfied_packets"])
        template = dict(group["template"])  # type: ignore[arg-type]
        template["relative_packet_gain"] = (
            "NaN"
            if baseline_satisfied == 0.0
            else str((proposed_satisfied - baseline_satisfied) / baseline_satisfied)
        )
        template["baseline_satisfied_packets"] = str(baseline_satisfied)
        template["proposed_satisfied_packets"] = str(proposed_satisfied)
        output_rows.append(template)
    return output_rows


def _mean_baseline_prb(
    rows: list[dict[str, str]],
    *,
    pdb_ms: int,
    rho_bg: float,
    rho_pdb: float,
    x_field: str,
    y_field: str,
) -> float:
    values = [
        float(row["prb_utilization"])
        for row in rows
        if int(row["pdb_ms"]) == pdb_ms
        and math.isclose(float(row[x_field]), rho_bg, rel_tol=0.0, abs_tol=1e-9)
        and math.isclose(float(row[y_field]), rho_pdb, rel_tol=0.0, abs_tol=1e-9)
    ]
    if not values:
        return math.nan
    return sum(values) / float(len(values))


def _ratio_prb_grid(
    rows: list[dict[str, str]],
    manifest: dict[str, object],
    *,
    title: str,
    output_path: Path,
) -> None:
    x_field, y_field = _ratio_fields(manifest, rows)
    rho_bg_values = sorted({float(row[x_field]) for row in rows})
    rho_pdb_values = sorted({float(row[y_field]) for row in rows})
    pdb_ms_values = sorted({int(row["pdb_ms"]) for row in rows})
    fig, axes = plt.subplots(
        1,
        len(pdb_ms_values),
        figsize=(5 * max(len(pdb_ms_values), 1), 5),
        constrained_layout=True,
        squeeze=False,
    )
    vmin = min(float(row["prb_utilization"]) for row in rows)
    vmax = max(float(row["prb_utilization"]) for row in rows)
    for col_index, pdb_ms in enumerate(pdb_ms_values):
        ax = axes[0][col_index]
        matrix = [
            [
                _mean_baseline_prb(
                    rows,
                    pdb_ms=pdb_ms,
                    rho_bg=rho_bg,
                    rho_pdb=rho_pdb,
                    x_field=x_field,
                    y_field=y_field,
                )
                for rho_bg in rho_bg_values
            ]
            for rho_pdb in rho_pdb_values
        ]
        image = ax.imshow(matrix, aspect="auto", origin="lower", vmin=vmin, vmax=vmax, cmap="viridis")
        image.cmap.set_bad(color="#d9d9d9")
        ax.set_title(f"pdb_ms={pdb_ms}")
        ax.set_xticks(range(len(rho_bg_values)), labels=[f"{value:.3f}" for value in rho_bg_values], rotation=20, ha="right")
        ax.set_yticks(range(len(rho_pdb_values)), labels=[f"{value:.3f}" for value in rho_pdb_values])
        ax.set_xlabel(x_field)
        ax.set_ylabel(y_field)
        fig.colorbar(image, ax=ax, shrink=0.80)
    fig.suptitle(title)
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def _ratio_grid(
    rows: list[dict[str, str]],
    manifest: dict[str, object],
    *,
    field_name: str,
    title: str,
    output_path: Path,
) -> None:
    shape_pairs = _ratio_shape_pairs(manifest, rows)
    x_field, y_field = _ratio_fields(manifest, rows)
    rho_bg_values = sorted({float(row[x_field]) for row in rows})
    rho_pdb_values = sorted({float(row[y_field]) for row in rows})
    fig, axes = plt.subplots(
        1,
        len(shape_pairs),
        figsize=(5 * max(len(shape_pairs), 1), 5),
        constrained_layout=True,
        squeeze=False,
    )
    for col_index, (pdb_ms, packet_kb) in enumerate(shape_pairs):
        ax = axes[0][col_index]
        x_values: list[float] = []
        y_values: list[float] = []
        sizes: list[float] = []
        colors: list[float] = []
        for rho_bg in rho_bg_values:
            for rho_pdb in rho_pdb_values:
                metric_value = _ratio_scene_value(
                    rows,
                    pdb_ms=pdb_ms,
                    pdb_packet_kb=packet_kb,
                    rho_bg=rho_bg,
                    rho_pdb=rho_pdb,
                    field_name=field_name,
                    x_field=x_field,
                    y_field=y_field,
                )
                if math.isnan(metric_value):
                    continue
                matching_row = next(
                    row
                    for row in rows
                    if int(row["pdb_ms"]) == pdb_ms
                    and math.isclose(float(row["pdb_packet_kb"]), packet_kb, rel_tol=0.0, abs_tol=1e-9)
                    and math.isclose(float(row[x_field]), rho_bg, rel_tol=0.0, abs_tol=1e-9)
                    and math.isclose(float(row[y_field]), rho_pdb, rel_tol=0.0, abs_tol=1e-9)
                )
                x_values.append(rho_bg)
                y_values.append(rho_pdb)
                sizes.append(max(float(matching_row["prb_share_pdb"]) * 800.0, 60.0))
                colors.append(metric_value)
        scatter = ax.scatter(
            x_values,
            y_values,
            s=sizes,
            c=colors,
            cmap="viridis",
            edgecolors="black",
            linewidths=0.5,
        )
        ax.set_title(f"PDB {pdb_ms} ms / {packet_kb:g} KB")
        ax.set_xlabel(x_field)
        ax.set_ylabel(y_field)
        ax.set_xticks(rho_bg_values, labels=[f"{value:.3f}" for value in rho_bg_values], rotation=20, ha="right")
        ax.set_yticks(rho_pdb_values, labels=[f"{value:.3f}" for value in rho_pdb_values])
        if x_values and y_values:
            fig.colorbar(scatter, ax=ax, shrink=0.80)
    fig.suptitle(f"{title} (marker size = prb_share_pdb)")
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def _business_ratio_grid(
    rows: list[dict[str, str]],
    manifest: dict[str, object],
    *,
    field_name: str,
    title: str,
    output_path: Path,
) -> None:
    x_field, y_field = _ratio_fields(manifest, rows)
    rho_bg_values = [float(value) for value in manifest["rho_bg_values"]]
    rho_pdb_values = [float(value) for value in manifest["rho_pdb_values"]]
    pdb_ms_values = [int(value) for value in manifest["pdb_ms_values"]]
    background_values = [int(value) for value in manifest["explicit_background_user_count_values"]]
    pdb_user_values = [int(value) for value in manifest["explicit_pdb_user_count_values"]]
    panels = [
        (rho_bg, rho_pdb, pdb_ms)
        for rho_bg in rho_bg_values
        for rho_pdb in rho_pdb_values
        for pdb_ms in pdb_ms_values
    ]
    values = [float(row[field_name]) for row in rows]
    if field_name == "mean_delta_pdb_satisfaction_rate":
        limit = max([abs(value) for value in values] + [0.01])
        vmin, vmax, cmap = -limit, limit, "RdBu_r"
    else:
        vmin, vmax, cmap = min(values), max(values), "viridis"
    fig, axes = plt.subplots(
        1,
        len(panels),
        figsize=(4.6 * max(len(panels), 1), 4.2),
        constrained_layout=True,
        squeeze=False,
    )
    for col_index, (target_rho_bg, target_rho_pdb, pdb_ms) in enumerate(panels):
        ax = axes[0][col_index]
        matrix = [
            [
                _business_scene_value(
                    rows,
                    target_rho_bg=target_rho_bg,
                    target_rho_pdb=target_rho_pdb,
                    pdb_ms=pdb_ms,
                    background_user_count=background_user_count,
                    pdb_user_count=pdb_user_count,
                    field_name=field_name,
                    x_field=x_field,
                    y_field=y_field,
                )
                for background_user_count in background_values
            ]
            for pdb_user_count in pdb_user_values
        ]
        image = ax.imshow(matrix, aspect="auto", origin="lower", vmin=vmin, vmax=vmax, cmap=cmap)
        image.cmap.set_bad(color="#d9d9d9")
        ax.set_title(f"rho_bg={target_rho_bg:.3f}\nrho_pdb={target_rho_pdb:.3f}, pdb={pdb_ms}ms")
        ax.set_xticks(range(len(background_values)), labels=[str(value) for value in background_values])
        ax.set_yticks(range(len(pdb_user_values)), labels=[str(value) for value in pdb_user_values])
        ax.set_xlabel("background_user_count")
        ax.set_ylabel("pdb_user_count")
        ax.set_xticks([tick - 0.5 for tick in range(1, len(background_values))], minor=True)
        ax.set_yticks([tick - 0.5 for tick in range(1, len(pdb_user_values))], minor=True)
        ax.grid(which="minor", color="white", linestyle="-", linewidth=1.5)
    fig.colorbar(image, ax=axes.ravel().tolist(), shrink=0.80)
    fig.suptitle(title)
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def _heatmap_percent_label(value: float, *, signed: bool) -> str:
    if math.isnan(value):
        return ""
    if signed:
        return f"{value * 100.0:+.1f}%"
    return f"{value * 100.0:.1f}%"


def _is_signed_heatmap_field(field_name: str) -> bool:
    return field_name in {"mean_delta_pdb_satisfaction_rate", "relative_packet_gain"}


def _add_heatmap_cell_annotations(
    ax,
    matrix: list[list[float]],
    *,
    signed: bool,
) -> None:
    for y_index, row in enumerate(matrix):
        for x_index, value in enumerate(row):
            label = _heatmap_percent_label(value, signed=signed)
            if not label:
                continue
            text_color = "white" if abs(value) >= 0.55 else "black"
            ax.text(x_index, y_index, label, ha="center", va="center", fontsize=7, color=text_color)


def _add_heatmap_cell_boundaries(ax, *, width: int, height: int) -> None:
    ax.set_xticks([tick - 0.5 for tick in range(1, width)], minor=True)
    ax.set_yticks([tick - 0.5 for tick in range(1, height)], minor=True)
    ax.grid(which="minor", color="white", linestyle="-", linewidth=1.8)
    ax.tick_params(which="minor", bottom=False, left=False)


def _business_metric_scale(rows: list[dict[str, str]], field_name: str) -> tuple[float, float, str]:
    values = [
        float(row[field_name])
        for row in rows
        if row.get(field_name, "") != "" and not math.isnan(float(row[field_name]))
    ]
    if not values:
        return (0.0, 1.0, "viridis")
    if _is_signed_heatmap_field(field_name):
        limit = max([abs(value) for value in values] + [0.01])
        return (-limit, limit, "RdBu_r")
    lower = min(values)
    upper = max(values)
    if math.isclose(lower, upper, rel_tol=0.0, abs_tol=1e-12):
        padding = max(abs(lower) * 0.01, 0.01)
        return (lower - padding, upper + padding, "viridis")
    return (lower, upper, "viridis")


def _faceted_business_ratio_grid(
    rows: list[dict[str, str]],
    manifest: dict[str, object],
    *,
    field_name: str,
    title: str,
    pdb_ms: int,
    output_path: Path,
) -> None:
    x_field, y_field = _ratio_fields(manifest, rows)
    rho_bg_values = [float(value) for value in manifest["rho_bg_values"]]
    rho_pdb_values = [float(value) for value in manifest["rho_pdb_values"]]
    background_values = [int(value) for value in manifest["explicit_background_user_count_values"]]
    pdb_user_values = [int(value) for value in manifest["explicit_pdb_user_count_values"]]
    vmin, vmax, cmap = _business_metric_scale(rows, field_name)
    fig, axes = plt.subplots(
        len(rho_pdb_values),
        len(rho_bg_values),
        figsize=(4.4 * max(len(rho_bg_values), 1), 3.7 * max(len(rho_pdb_values), 1)),
        constrained_layout=True,
        squeeze=False,
    )
    signed = _is_signed_heatmap_field(field_name)
    last_image = None
    for row_index, target_rho_pdb in enumerate(rho_pdb_values):
        for col_index, target_rho_bg in enumerate(rho_bg_values):
            ax = axes[row_index][col_index]
            matrix = [
                [
                    _business_scene_value(
                        rows,
                        target_rho_bg=target_rho_bg,
                        target_rho_pdb=target_rho_pdb,
                        pdb_ms=pdb_ms,
                        background_user_count=background_user_count,
                        pdb_user_count=pdb_user_count,
                        field_name=field_name,
                        x_field=x_field,
                        y_field=y_field,
                    )
                    for background_user_count in background_values
                ]
                for pdb_user_count in pdb_user_values
            ]
            last_image = ax.imshow(matrix, aspect="auto", origin="lower", vmin=vmin, vmax=vmax, cmap=cmap)
            last_image.cmap.set_bad(color="#d9d9d9")
            ax.set_title(f"rho_bg={target_rho_bg:.2f}, rho_pdb={target_rho_pdb:.2f}")
            ax.set_xticks(range(len(background_values)), labels=[str(value) for value in background_values])
            ax.set_yticks(range(len(pdb_user_values)), labels=[str(value) for value in pdb_user_values])
            ax.set_xlabel("background_user_count")
            ax.set_ylabel("pdb_user_count")
            _add_heatmap_cell_boundaries(ax, width=len(background_values), height=len(pdb_user_values))
            _add_heatmap_cell_annotations(ax, matrix, signed=signed)
    if last_image is not None:
        fig.colorbar(last_image, ax=axes.ravel().tolist(), shrink=0.80)
    fig.suptitle(f"{title} (pdb_ms={pdb_ms}, cell text = percentage)")
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def _faceted_business_baseline_prb_grid(
    rows: list[dict[str, str]],
    manifest: dict[str, object],
    *,
    title: str,
    pdb_ms: int,
    output_path: Path,
) -> None:
    x_field, y_field = _ratio_fields(manifest, rows)
    rho_bg_values = [float(value) for value in manifest["rho_bg_values"]]
    rho_pdb_values = [float(value) for value in manifest["rho_pdb_values"]]
    background_values = [int(value) for value in manifest["explicit_background_user_count_values"]]
    pdb_user_values = [int(value) for value in manifest["explicit_pdb_user_count_values"]]
    values = [float(row["prb_utilization"]) for row in rows]
    vmin = min(values) if values else 0.0
    vmax = max(values) if values else 1.0
    if math.isclose(vmin, vmax, rel_tol=0.0, abs_tol=1e-12):
        padding = max(abs(vmin) * 0.01, 0.01)
        vmin -= padding
        vmax += padding
    fig, axes = plt.subplots(
        len(rho_pdb_values),
        len(rho_bg_values),
        figsize=(4.4 * max(len(rho_bg_values), 1), 3.7 * max(len(rho_pdb_values), 1)),
        constrained_layout=True,
        squeeze=False,
    )
    last_image = None
    for row_index, target_rho_pdb in enumerate(rho_pdb_values):
        for col_index, target_rho_bg in enumerate(rho_bg_values):
            ax = axes[row_index][col_index]
            matrix = [
                [
                    _business_baseline_prb_value(
                        rows,
                        target_rho_bg=target_rho_bg,
                        target_rho_pdb=target_rho_pdb,
                        pdb_ms=pdb_ms,
                        background_user_count=background_user_count,
                        pdb_user_count=pdb_user_count,
                        x_field=x_field,
                        y_field=y_field,
                    )
                    for background_user_count in background_values
                ]
                for pdb_user_count in pdb_user_values
            ]
            last_image = ax.imshow(matrix, aspect="auto", origin="lower", vmin=vmin, vmax=vmax, cmap="viridis")
            last_image.cmap.set_bad(color="#d9d9d9")
            ax.set_title(f"rho_bg={target_rho_bg:.2f}, rho_pdb={target_rho_pdb:.2f}")
            ax.set_xticks(range(len(background_values)), labels=[str(value) for value in background_values])
            ax.set_yticks(range(len(pdb_user_values)), labels=[str(value) for value in pdb_user_values])
            ax.set_xlabel("background_user_count")
            ax.set_ylabel("pdb_user_count")
            _add_heatmap_cell_boundaries(ax, width=len(background_values), height=len(pdb_user_values))
            _add_heatmap_cell_annotations(ax, matrix, signed=False)
    if last_image is not None:
        fig.colorbar(last_image, ax=axes.ravel().tolist(), shrink=0.80)
    fig.suptitle(f"{title} (pdb_ms={pdb_ms}, cell text = percentage)")
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def _boundary_plot(
    manifest: dict[str, object],
    *,
    boundary_rows: list[dict[str, str]],
    threshold: float,
    output_path: Path,
) -> None:
    pdb_ms_values = [int(value) for value in manifest["pdb_ms_values"]]
    packet_values = [int(value) for value in manifest["pdb_packet_kb_values"]]
    background_values = [int(value) for value in manifest["background_user_count_values"]]
    pdb_user_values = [int(value) for value in manifest["pdb_user_count_values"]]
    fig, axes = plt.subplots(
        len(pdb_ms_values),
        len(packet_values),
        figsize=(12, 10),
        constrained_layout=True,
        squeeze=False,
    )
    for row_index, pdb_ms in enumerate(pdb_ms_values):
        for col_index, packet_kb in enumerate(packet_values):
            ax = axes[row_index][col_index]
            baseline_matrix = [
                [
                    _grid_value(
                        boundary_rows,
                        pdb_ms=pdb_ms,
                        pdb_packet_kb=packet_kb,
                        background_user_count=background_user_count,
                        pdb_user_count=pdb_user_count,
                        field_name="baseline_feasible",
                    )
                    for background_user_count in background_values
                ]
                for pdb_user_count in pdb_user_values
            ]
            proposed_matrix = [
                [
                    _grid_value(
                        boundary_rows,
                        pdb_ms=pdb_ms,
                        pdb_packet_kb=packet_kb,
                        background_user_count=background_user_count,
                        pdb_user_count=pdb_user_count,
                        field_name="proposed_feasible",
                    )
                    for background_user_count in background_values
                ]
                for pdb_user_count in pdb_user_values
            ]
            baseline_image = ax.imshow(
                baseline_matrix,
                origin="lower",
                aspect="auto",
                cmap="Blues",
                alpha=0.60,
                vmin=0.0,
                vmax=1.0,
            )
            baseline_image.cmap.set_bad(color="#d9d9d9")
            proposed_image = ax.imshow(
                proposed_matrix,
                origin="lower",
                aspect="auto",
                cmap="Oranges",
                alpha=0.40,
                vmin=0.0,
                vmax=1.0,
            )
            proposed_image.cmap.set_bad(color="#d9d9d9")
            ax.set_title(f"PDB {pdb_ms} ms / {packet_kb} KB")
            ax.set_xticks(range(len(background_values)), labels=[str(value) for value in background_values])
            ax.set_yticks(range(len(pdb_user_values)), labels=[str(value) for value in pdb_user_values])
            ax.set_xlabel("background_user_count")
            ax.set_ylabel("pdb_user_count")
    fig.suptitle(f"Feasible Region Comparison @ {threshold:.0%} (blue=baseline, orange=proposed)")
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def _ratio_boundary_plot(
    manifest: dict[str, object],
    *,
    boundary_rows: list[dict[str, str]],
    threshold: float,
    output_path: Path,
) -> None:
    shape_pairs = _ratio_shape_pairs(manifest, boundary_rows)
    x_field, y_field = _ratio_fields(manifest, boundary_rows)
    rho_bg_values = sorted({float(row[x_field]) for row in boundary_rows})
    rho_pdb_values = sorted({float(row[y_field]) for row in boundary_rows})
    fig, axes = plt.subplots(
        1,
        len(shape_pairs),
        figsize=(5 * max(len(shape_pairs), 1), 5),
        constrained_layout=True,
        squeeze=False,
    )
    for col_index, (pdb_ms, packet_kb) in enumerate(shape_pairs):
        ax = axes[0][col_index]
        for row in boundary_rows:
            if int(row["pdb_ms"]) != pdb_ms or not math.isclose(
                float(row["pdb_packet_kb"]),
                packet_kb,
                rel_tol=0.0,
                abs_tol=1e-9,
            ):
                continue
            baseline_feasible = int(row["baseline_feasible"])
            proposed_feasible = int(row["proposed_feasible"])
            marker = "o" if baseline_feasible == proposed_feasible else "^"
            color = "#1f77b4" if baseline_feasible else "#ff7f0e"
            if baseline_feasible == 0 and proposed_feasible == 1:
                color = "#2ca02c"
            ax.scatter(
                float(row[x_field]),
                float(row[y_field]),
                s=max(float(row["prb_share_pdb"]) * 800.0, 60.0),
                c=color,
                marker=marker,
                edgecolors="black",
                linewidths=0.5,
            )
        ax.set_title(f"PDB {pdb_ms} ms / {packet_kb:g} KB")
        ax.set_xlabel(x_field)
        ax.set_ylabel(y_field)
        ax.set_xticks(rho_bg_values, labels=[f"{value:.3f}" for value in rho_bg_values], rotation=20, ha="right")
        ax.set_yticks(rho_pdb_values, labels=[f"{value:.3f}" for value in rho_pdb_values])
    fig.suptitle(f"Feasible Region Comparison @ {threshold:.0%} (marker size = prb_share_pdb)")
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def _representative_case_metric_specs() -> list[dict[str, object]]:
    return [
        {"title": "PDB Satisfaction", "metrics": ["edge_pdb_satisfaction_rate"], "y_label": "rate"},
        {"title": "Queue Wait", "metrics": ["target_edge_queue_wait_ms"], "y_label": "ms"},
        {"title": "Service Time", "metrics": ["target_edge_service_time_ms"], "y_label": "ms"},
        {"title": "Completion Delay", "metrics": ["target_edge_completion_delay_ms"], "y_label": "ms"},
        {"title": "Backlog", "metrics": ["edge_backlog_bits"], "y_label": "bits"},
        {"title": "PRB Utilization", "metrics": ["prb_utilization"], "y_label": "share"},
        {"title": "Center PRB Share", "metrics": ["center_prb_share"], "y_label": "share"},
        {"title": "Edge PRB Share", "metrics": ["edge_prb_share"], "y_label": "share"},
        {"title": "Center Aggregate Rate", "metrics": ["center_agg_rate_bps"], "y_label": "bps"},
    ]


def _render_typical_case_figures(output_dir: Path, detail_rows: list[dict[str, str]]) -> None:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in detail_rows:
        grouped.setdefault(str(row["case_label"]), []).append(row)
    metric_specs = _representative_case_metric_specs()
    for case_label, rows in grouped.items():
        ordered_rows = sorted(rows, key=lambda row: str(row["policy"]))
        fig, axes = plt.subplots(3, 3, figsize=(15, 10), constrained_layout=True, squeeze=False)
        for ax, spec in zip(axes.flat, metric_specs):
            metric_name = str(spec["metrics"][0])
            values = [float(row[metric_name]) for row in ordered_rows]
            ax.bar(range(len(ordered_rows)), values, width=0.6)
            ax.set_xticks(range(len(ordered_rows)), labels=[str(row["policy"]) for row in ordered_rows], rotation=15, ha="right")
            ax.set_title(str(spec["title"]))
            ax.set_ylabel(str(spec["y_label"]))
        fig.suptitle(f"Representative Case: {case_label}")
        fig.savefig(output_dir / f"typical_case_{case_label}.png", dpi=200)
        plt.close(fig)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: render_systematic_simulation_analysis_plots.py OUTPUT_DIR", file=sys.stderr)
        return 2

    output_dir = Path(sys.argv[1])
    manifest = json.loads((output_dir / "experiment_manifest.json").read_text(encoding="utf-8"))
    scene_rows = _rows(output_dir / "scene_summary.csv")
    boundary_rows_95 = _rows(output_dir / "boundary_feasibility_95.csv")
    boundary_rows_90 = _rows(output_dir / "boundary_feasibility_90.csv")
    typical_case_detail_rows = _rows(output_dir / "typical_case_details.csv")
    per_run_rows = _per_run_rows(output_dir)
    per_run_baseline_rows = _per_run_baseline_prb_rows(output_dir)
    relative_packet_gain_rows = _relative_packet_gain_rows(
        per_run_rows,
        baseline_policy=str(manifest.get("baseline_policy", "tail_append")),
        proposed_policy=str(manifest.get("ours_policy", "hopeless_tail_append")),
    )
    if str(manifest.get("scan_mode", "")) == "load_ratio":
        _ratio_grid(
            scene_rows,
            manifest,
            field_name="mean_delta_pdb_satisfaction_rate",
            title="Mean Paired Delta PDB Satisfaction",
            output_path=output_dir / "overview_delta_pdb_satisfaction.png",
        )
        _ratio_grid(
            scene_rows,
            manifest,
            field_name="mean_center_throughput_retention",
            title="Mean Center Throughput Retention",
            output_path=output_dir / "center_throughput_retention.png",
        )
        _ratio_boundary_plot(
            manifest,
            boundary_rows=boundary_rows_95,
            threshold=0.95,
            output_path=output_dir / "capacity_boundary_95.png",
        )
        _ratio_boundary_plot(
            manifest,
            boundary_rows=boundary_rows_90,
            threshold=0.90,
            output_path=output_dir / "capacity_boundary_90.png",
        )
        if per_run_baseline_rows:
            _ratio_prb_grid(
                per_run_baseline_rows,
                manifest,
                title="Baseline PRB Utilization by PDB Period",
                output_path=output_dir / "baseline_prb_utilization_by_pdb_ms.png",
            )
        if (
            "explicit_background_user_count_values" in manifest
            and "explicit_pdb_user_count_values" in manifest
        ):
            _business_ratio_grid(
                scene_rows,
                manifest,
                field_name="mean_delta_pdb_satisfaction_rate",
                title="Mean Paired Delta PDB Satisfaction",
                output_path=output_dir / "business_delta_pdb_satisfaction.png",
            )
            _business_ratio_grid(
                scene_rows,
                manifest,
                field_name="mean_center_throughput_retention",
                title="Mean Center Throughput Retention",
                output_path=output_dir / "business_center_throughput_retention.png",
            )
            for pdb_ms in [int(value) for value in manifest["pdb_ms_values"]]:
                if relative_packet_gain_rows:
                    _faceted_business_ratio_grid(
                        relative_packet_gain_rows,
                        manifest,
                        field_name="relative_packet_gain",
                        title="Relative Packet Gain vs Baseline Satisfied",
                        pdb_ms=pdb_ms,
                        output_path=output_dir / f"faceted_business_delta_pdb_satisfaction_pdb{pdb_ms}.png",
                    )
                _faceted_business_ratio_grid(
                    scene_rows,
                    manifest,
                    field_name="mean_center_throughput_retention",
                    title="Mean Center Throughput Retention",
                    pdb_ms=pdb_ms,
                    output_path=output_dir / f"faceted_business_center_throughput_retention_pdb{pdb_ms}.png",
                )
                if per_run_baseline_rows:
                    _faceted_business_baseline_prb_grid(
                        per_run_baseline_rows,
                        manifest,
                        title="Baseline PRB Utilization",
                        pdb_ms=pdb_ms,
                        output_path=output_dir / f"faceted_baseline_prb_utilization_pdb{pdb_ms}.png",
                    )
    else:
        _heatmap_grid(
            scene_rows,
            manifest,
            field_name="mean_delta_pdb_satisfaction_rate",
            title="Mean Paired Delta PDB Satisfaction",
            output_path=output_dir / "overview_delta_pdb_satisfaction.png",
        )
        _heatmap_grid(
            scene_rows,
            manifest,
            field_name="mean_center_throughput_retention",
            title="Mean Center Throughput Retention",
            output_path=output_dir / "center_throughput_retention.png",
        )
        _boundary_plot(
            manifest,
            boundary_rows=boundary_rows_95,
            threshold=0.95,
            output_path=output_dir / "capacity_boundary_95.png",
        )
        _boundary_plot(
            manifest,
            boundary_rows=boundary_rows_90,
            threshold=0.90,
            output_path=output_dir / "capacity_boundary_90.png",
        )
    _render_typical_case_figures(output_dir, typical_case_detail_rows)
    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
