import json
from pathlib import Path


def write_report(output_dir: str, summary: dict[str, float]) -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    report_path = path / "report.json"
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return report_path
