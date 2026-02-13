from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

from .config import EVENT_KEYWORDS, PROVINCE_ALIASES, TARGET_PROVINCES

DATE_PATTERN = re.compile(r"(?:(\d{4})年)?\s*(\d{1,2})月(\d{1,2})日")


@dataclass
class WeatherRecord:
    province: str
    event: str
    source_url: str
    published_date: Optional[date]
    raw_line: str


def _normalize_province(line: str) -> Optional[str]:
    for province in TARGET_PROVINCES:
        if province in line:
            return province

    for province, aliases in PROVINCE_ALIASES.items():
        for alias in aliases:
            if alias in line:
                return province

    return None


def _extract_date(line: str, fallback_year: int) -> Optional[date]:
    match = DATE_PATTERN.search(line)
    if not match:
        return None

    year_raw, month_raw, day_raw = match.groups()
    year = int(year_raw) if year_raw else fallback_year

    try:
        return date(year=year, month=int(month_raw), day=int(day_raw))
    except ValueError:
        return None


def _extract_event(line: str) -> Optional[str]:
    for keyword in EVENT_KEYWORDS:
        if keyword in line:
            return keyword
    return None


def extract_records(source_text: str, source_url: str, today: date) -> List[WeatherRecord]:
    records: List[WeatherRecord] = []

    for raw_line in source_text.splitlines():
        line = raw_line.strip()
        if len(line) < 6:
            continue

        province = _normalize_province(line)
        if not province:
            continue

        event = _extract_event(line)
        if not event:
            continue

        record = WeatherRecord(
            province=province,
            event=event,
            source_url=source_url,
            published_date=_extract_date(line, today.year),
            raw_line=line,
        )
        records.append(record)

    return records


def aggregate_by_province_and_date(
    records: List[WeatherRecord],
    dates: List[date],
    today: date,
) -> Dict[str, Dict[date, List[WeatherRecord]]]:
    mapping: Dict[str, Dict[date, List[WeatherRecord]]] = {
        province: {d: [] for d in dates} for province in TARGET_PROVINCES
    }

    date_set = set(dates)
    for record in records:
        target_date = record.published_date or today
        if target_date not in date_set:
            continue
        mapping[record.province][target_date].append(record)

    return mapping


def is_record_for_target_date(record: WeatherRecord, target: date) -> bool:
    line = record.raw_line

    # If explicit date exists and it is not target date, exclude directly.
    if record.published_date and record.published_date != target:
        return False

    # If text includes explicit dates, target date must appear among them.
    found_dates = []
    for match in DATE_PATTERN.finditer(line):
        year_raw, month_raw, day_raw = match.groups()
        year = int(year_raw) if year_raw else target.year
        try:
            found_dates.append(date(year=year, month=int(month_raw), day=int(day_raw)))
        except ValueError:
            continue

    if found_dates and target not in found_dates:
        return False

    # Strong future/horizon wording usually means non-single-day scope.
    future_markers = ["未来", "中期", "趋势", "后期", "随后", "将有", "预计", "明天", "后天"]
    today_markers = ["今天", "今日", "当日", "24小时", "白天到夜间", "夜间到白天"]
    has_future = any(m in line for m in future_markers)
    has_today = any(m in line for m in today_markers)
    if has_future and not has_today and target not in found_dates:
        return False

    return True
