from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Dict, List

from .config import TARGET_PROVINCES
from .extract import WeatherRecord


def _cell_text(records: List[WeatherRecord]) -> str:
    if not records:
        return "无"

    seen = set()
    parts: List[str] = []
    for r in records:
        key = (r.event, r.raw_line)
        if key in seen:
            continue
        seen.add(key)
        parts.append(r.event)

    compact = []
    for item in parts:
        if item not in compact:
            compact.append(item)

    return "、".join(compact) if compact else "无"


def render_markdown_table(
    table_data: Dict[str, Dict[date, List[WeatherRecord]]],
    dates: List[date],
) -> str:
    headers = ["省份"] + [d.isoformat() for d in dates]
    sep = ["---"] * len(headers)

    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(sep) + " |"]

    for province in TARGET_PROVINCES:
        row = [province]
        for d in dates:
            row.append(_cell_text(table_data[province][d]))
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines) + "\n"


def save_markdown(markdown: str, output_dir: str, file_date: date) -> Path:
    output_path = Path(output_dir) / f"{file_date.isoformat()}.md"
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


def compose_daily_markdown(
    file_date: date,
    overview_sections: Dict[str, str],
    table_markdown: str,
    details_markdown: str,
    warnings: List[str],
) -> str:
    warning_lines = warnings if warnings else ["无"]
    parts = [
        f"# 全国天气简报（{file_date.isoformat()}）",
        "",
        "## 警告",
        *[f"- {w}" for w in warning_lines],
        "",
        "## 每日天气情况简介",
        f"- 全国区域：{overview_sections.get('national', '').strip()}",
        f"- 天气动力过程：{overview_sections.get('dynamics', '').strip()}",
        f"- 风险提示：{overview_sections.get('risk', '').strip()}",
        "",
        "## 重点省份天气列表",
        table_markdown.strip(),
        "",
        "## 详细信息",
        details_markdown.strip(),
        "",
    ]
    return "\n".join(parts)
