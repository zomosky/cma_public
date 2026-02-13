from __future__ import annotations

import json
from datetime import date
from typing import Dict, Iterable, List, Optional, Tuple


def _fallback_overview(today: date) -> Dict[str, str]:
    return {
        "national": (
            f"{today.isoformat()}全国范围内，北方和西北地区需重点关注大风、沙尘过程，"
            "东北地区关注雨雪及相态转换，江南华南关注阶段性降雨影响。"
        ),
        "dynamics": "主要动力条件为冷空气南下、低涡切变发展及低层水汽输送共同作用。",
        "risk": "建议关注强对流、局地短时强降雨及大风叠加影响，及时跟踪最新预警与实况。",
    }


def summarize_daily_overview(
    source_texts: Iterable[str],
    api_key: str,
    base_url: str,
    model: str,
    today: date,
) -> Tuple[Dict[str, str], Optional[str]]:
    """Build overview and return (sections, warning)."""
    texts = [t.strip() for t in source_texts if t and t.strip()]
    if not texts:
        return _fallback_overview(today), "简介生成：无可用源文本，已使用兜底简介。"
    if not api_key:
        return _fallback_overview(today), "简介生成：未启用模型，已使用兜底简介。"

    try:
        from openai import OpenAI
    except Exception:
        return _fallback_overview(today), "简介生成：OpenAI SDK 不可用，已使用兜底简介。"

    clipped = [t[:700] for t in texts[:6]]
    joined = "\n\n".join(clipped)

    client = OpenAI(api_key=api_key, base_url=base_url)
    system_prompt = (
        "你是国家级气象信息简报助手。"
        "请基于材料输出严格JSON对象，字段仅包含national,dynamics,risk。"
        "national写全国区域分布；dynamics写天气动力过程；risk写风险提示。"
        "每个字段1-2句，禁止Markdown，禁止额外字段。"
    )
    user_prompt = f"日期：{today.isoformat()}\n\n原始材料：\n{joined}"

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            return _fallback_overview(today), "简介生成：模型返回为空，已使用兜底简介。"

        data = json.loads(text)
        national = str(data.get("national", "")).strip()
        dynamics = str(data.get("dynamics", "")).strip()
        risk = str(data.get("risk", "")).strip()
        if not (national and dynamics and risk):
            return _fallback_overview(today), "简介生成：模型返回字段不完整，已使用兜底简介。"

        return {"national": national, "dynamics": dynamics, "risk": risk}, None
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).lower()
        if "timeout" in msg or "timed out" in msg:
            return _fallback_overview(today), "简介生成：模型调用超时，已使用兜底简介。"
        return _fallback_overview(today), f"简介生成：模型调用失败（{type(exc).__name__}），已使用兜底简介。"


def select_events_for_table(
    lines: Iterable[str],
    target_date: date,
    api_key: str,
    base_url: str,
    model: str,
) -> Tuple[List[str], Optional[str]]:
    """Return selected concise events and optional warning."""
    raw_lines = [line.strip() for line in lines if line and line.strip()]
    if not raw_lines:
        return [], None
    if not api_key:
        return [], "表格核验：未启用模型，已使用规则提取。"

    try:
        from openai import OpenAI
    except Exception:
        return [], "表格核验：OpenAI SDK 不可用，已使用规则提取。"

    client = OpenAI(api_key=api_key, base_url=base_url)
    system_prompt = (
        "你是气象信息核验助手。请反复核查每条信息的时间范围，只保留在目标日期内生效的天气现象。"
        "输出严格JSON，格式为{\"items\":[\"现象+程度\",...] }。"
        "每项不超过10个字，只保留如大风8-10级、暴雨、暴雪、沙尘、台风。"
        "如果无法确认属于目标日期，必须丢弃。"
    )
    user_prompt = (
        f"目标日期：{target_date.isoformat()}\n"
        "候选信息如下：\n"
        + "\n".join(f"- {line}" for line in raw_lines[:80])
    )

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            return [], "表格核验：模型返回为空，已使用规则提取。"

        data = json.loads(text)
        items = data.get("items", [])
        if not isinstance(items, list):
            return [], "表格核验：模型返回格式无效，已使用规则提取。"

        clean: List[str] = []
        for item in items:
            v = str(item).strip()
            if v and v not in clean:
                clean.append(v)
        return clean[:3], None
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).lower()
        if "timeout" in msg or "timed out" in msg:
            return [], "表格核验：模型调用超时，已使用规则提取。"
        return [], f"表格核验：模型调用失败（{type(exc).__name__}），已使用规则提取。"
