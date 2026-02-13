from __future__ import annotations

import argparse
import re
from datetime import date, datetime
from typing import Dict, List

from .config import (
    AppConfig,
    OVERVIEW_ONLY_URLS,
    SETTINGS_PATH,
    SOURCE_URLS,
    TARGET_PROVINCES,
)
from .email_sender import is_email_enabled, send_report_email
from .extract import (
    WeatherRecord,
    aggregate_by_province_and_date,
    extract_records,
    is_record_for_target_date,
)
from .fetchers import fetch_all
from .llm_client import select_events_for_table, summarize_daily_overview
from .report import compose_daily_markdown, render_markdown_table, save_markdown


def progress(stage: str, message: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{stage}] {message}", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CMA weather publish pipeline")
    parser.add_argument("--output-dir", default=".", help="Markdown output directory")
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable LLM summarization even if API key exists",
    )
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Send generated markdown through SMTP after file is written",
    )
    return parser.parse_args()


def _extract_level(text: str) -> str:
    patterns = [
        r"(特大暴雨|大暴雨|暴雨|大雨|暴雪|降雪|雨夹雪)",
        r"(超强台风|强台风|台风|热带风暴)",
        r"(\d{1,2}(?:[~～-]\d{1,2})?级(?:阵风\d{1,2}级)?)",
        r"(沙尘暴|强沙尘暴|扬沙|浮尘)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""


def _brief_from_record(record: WeatherRecord) -> str:
    base = record.event
    level = _extract_level(record.raw_line)
    if level and level not in base:
        return f"{base}{level}"
    return base


def build_summary_table(
    grouped,
    target_date: date,
    cfg: AppConfig,
) -> tuple[Dict[str, Dict[date, str]], List[str]]:
    summary_table: Dict[str, Dict[date, str]] = {
        p: {target_date: "无"} for p in TARGET_PROVINCES
    }
    warnings: List[str] = []
    warning_set = set()

    for province in TARGET_PROVINCES:
        records = grouped[province][target_date]
        if not records:
            continue

        model_items: List[str] = []
        if cfg.use_llm:
            model_items, warn = select_events_for_table(
                lines=[r.raw_line for r in records],
                target_date=target_date,
                api_key=cfg.llm_api_key,
                base_url=cfg.llm_base_url,
                model=cfg.llm_model,
            )
            if warn and warn not in warning_set:
                warnings.append(warn)
                warning_set.add(warn)

        compact = model_items
        if not compact:
            compact = []
            for record in records:
                text = _brief_from_record(record).strip()
                if text and text not in compact:
                    compact.append(text)

        summary_table[province][target_date] = "；".join(compact[:3]) if compact else "无"

    return summary_table, warnings


def render_table_from_summary(summary_table: Dict[str, Dict[date, str]], dates: List[date]) -> str:
    from .extract import WeatherRecord

    projected = {
        p: {
            d: (
                []
                if summary_table[p][d] == "无"
                else [
                    WeatherRecord(
                        province=p,
                        event=summary_table[p][d],
                        source_url="",
                        published_date=d,
                        raw_line=summary_table[p][d],
                    )
                ]
            )
            for d in dates
        }
        for p in TARGET_PROVINCES
    }
    return render_markdown_table(projected, dates)


def build_details_markdown(grouped, dates: List[date]) -> str:
    lines: List[str] = []
    has_details = False
    for d in dates:
        lines.append(f"### {d.isoformat()}")
        day_items = 0
        for province in TARGET_PROVINCES:
            records = grouped[province][d]
            if not records:
                continue
            for idx, record in enumerate(records, start=1):
                lines.append(f"- {province} #{idx}：{record.raw_line}")
                lines.append(f"  - 来源：{record.source_url}")
                day_items += 1
                has_details = True
        if day_items == 0:
            lines.append("- 无")
        lines.append("")

    return "\n".join(lines).strip() if has_details else "无"


def main() -> None:
    progress("INIT", "pipeline start")
    args = parse_args()
    cfg = AppConfig.from_settings(days=1, use_llm=not args.no_llm, output_dir=args.output_dir)
    warnings: List[str] = []
    if args.no_llm:
        warnings.append("运行参数：已启用 --no-llm，所有模型能力均已关闭。")
    elif not cfg.llm_api_key:
        warnings.append("模型配置：未设置 LLM API Key，已自动降级为非模型模式。")

    today = date.today()
    dates = [today]
    progress("INIT", f"config={SETTINGS_PATH}")
    progress("INIT", f"date={today.isoformat()} days=1(today-only) llm={'on' if cfg.use_llm else 'off'}")

    progress("FETCH", f"fetching {len(SOURCE_URLS)} sources")
    docs = fetch_all(SOURCE_URLS, timeout_seconds=cfg.timeout_seconds)
    failed = sum(1 for d in docs if d.text.startswith("[FETCH_FAILED]"))
    progress("FETCH", f"done, success={len(docs)-failed} failed={failed}")

    source_texts = [doc.text for doc in docs if not doc.text.startswith("[FETCH_FAILED]")]
    overview_only_set = set(OVERVIEW_ONLY_URLS)
    stat_docs = [
        doc for doc in docs
        if not doc.text.startswith("[FETCH_FAILED]") and doc.url not in overview_only_set
    ]
    progress(
        "FETCH",
        f"stats_sources={len(stat_docs)} overview_only={len([d for d in docs if d.url in overview_only_set])}",
    )

    progress("EXTRACT", "extracting weather records")
    all_records = []
    for doc in stat_docs:
        extracted = extract_records(doc.text, doc.url, today)
        today_records = [r for r in extracted if is_record_for_target_date(r, today)]
        all_records.extend(today_records)
    progress("EXTRACT", f"done, records={len(all_records)}")

    progress("AGGREGATE", "grouping by province/date")
    grouped = aggregate_by_province_and_date(all_records, dates, today)

    progress("SUMMARY", "building concise province table summaries")
    summary_table, summary_warnings = build_summary_table(grouped, today, cfg)
    warnings.extend([w for w in summary_warnings if w not in warnings])
    table_markdown = render_table_from_summary(summary_table, dates)
    details_markdown = build_details_markdown(grouped, dates)

    progress("OVERVIEW", "generating national overview sections")
    overview_sections, overview_warn = summarize_daily_overview(
        source_texts=source_texts,
        api_key=cfg.llm_api_key if cfg.use_llm else "",
        base_url=cfg.llm_base_url,
        model=cfg.llm_model,
        today=today,
    )
    if overview_warn and overview_warn not in warnings:
        warnings.append(overview_warn)

    progress("RENDER", "composing markdown")
    markdown = compose_daily_markdown(
        today,
        overview_sections,
        table_markdown,
        details_markdown,
        warnings,
    )

    progress("SAVE", "writing output file")
    output_path = save_markdown(markdown, cfg.output_dir, today)

    if args.send_email:
        progress("EMAIL", "checking SMTP configuration")
        if not is_email_enabled(cfg):
            progress("EMAIL", "skipped, missing SMTP_* settings")
        else:
            progress("EMAIL", f"sending email to {cfg.smtp_to}")
            subject = f"{cfg.smtp_subject_prefix} 全国天气简报 {today.isoformat()}"
            send_report_email(cfg, subject=subject, markdown_body=markdown)
            progress("EMAIL", "sent")

    progress("DONE", f"records={len(all_records)} output={output_path}")


if __name__ == "__main__":
    main()
