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
        return {
            "x_label": "rho_bg",
            "y_label": "rho_pdb",
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
) -> float:
    for row in rows:
        if (
            int(row["pdb_ms"]) == pdb_ms
            and math.isclose(float(row["pdb_packet_kb"]), pdb_packet_kb, rel_tol=0.0, abs_tol=1e-9)
            and math.isclose(float(row["rho_bg"]), rho_bg, rel_tol=0.0, abs_tol=1e-9)
            and math.isclose(float(row["rho_pdb"]), rho_pdb, rel_tol=0.0, abs_tol=1e-9)
        ):
            return float(row[field_name])
    return math.nan


def _ratio_grid(
    rows: list[dict[str, str]],
    manifest: dict[str, object],
    *,
    field_name: str,
    title: str,
    output_path: Path,
) -> None:
    shape_pairs = [
        (int(shape["pdb_ms"]), float(packet_kb))
        for shape in manifest["pdb_shapes"]
        for packet_kb in shape["pdb_packet_kb_values"]
    ]
    rho_bg_values = sorted({float(row["rho_bg"]) for row in rows})
    rho_pdb_values = sorted({float(row["rho_pdb"]) for row in rows})
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
                )
                if math.isnan(metric_value):
                    continue
                matching_row = next(
                    row
                    for row in rows
                    if int(row["pdb_ms"]) == pdb_ms
                    and math.isclose(float(row["pdb_packet_kb"]), packet_kb, rel_tol=0.0, abs_tol=1e-9)
                    and math.isclose(float(row["rho_bg"]), rho_bg, rel_tol=0.0, abs_tol=1e-9)
                    and math.isclose(float(row["rho_pdb"]), rho_pdb, rel_tol=0.0, abs_tol=1e-9)
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
        ax.set_xlabel("rho_bg")
        ax.set_ylabel("rho_pdb")
        ax.set_xticks(rho_bg_values, labels=[f"{value:.3f}" for value in rho_bg_values], rotation=20, ha="right")
        ax.set_yticks(rho_pdb_values, labels=[f"{value:.3f}" for value in rho_pdb_values])
        if x_values and y_values:
            fig.colorbar(scatter, ax=ax, shrink=0.80)
    fig.suptitle(f"{title} (marker size = prb_share_pdb)")
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
    shape_pairs = [
        (int(shape["pdb_ms"]), float(packet_kb))
        for shape in manifest["pdb_shapes"]
        for packet_kb in shape["pdb_packet_kb_values"]
    ]
    rho_bg_values = sorted({float(row["rho_bg"]) for row in boundary_rows})
    rho_pdb_values = sorted({float(row["rho_pdb"]) for row in boundary_rows})
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
                float(row["rho_bg"]),
                float(row["rho_pdb"]),
                s=max(float(row["prb_share_pdb"]) * 800.0, 60.0),
                c=color,
                marker=marker,
                edgecolors="black",
                linewidths=0.5,
            )
        ax.set_title(f"PDB {pdb_ms} ms / {packet_kb:g} KB")
        ax.set_xlabel("rho_bg")
        ax.set_ylabel("rho_pdb")
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
