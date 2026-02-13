from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List


SETTINGS_PATH = Path(__file__).with_name("settings.json")
SETTINGS_LOCAL_PATH = Path(__file__).with_name("settings.local.json")

DEFAULT_SETTINGS: Dict[str, Any] = {
    "sources": {
        "urls": [
            "https://www.nmc.cn/publish/weather-bulletin/index.htm",
            "https://www.nmc.cn/publish/weatherperday/index.htm",
            "https://www.nmc.cn/publish/news/weather_new.html",
            "https://www.nmc.cn/publish/bulletin/mid-range.htm",
            "https://www.nmc.cn/publish/typhoon/warning_index.html",
        ],
        "overview_only_urls": [
            "https://www.nmc.cn/publish/bulletin/mid-range.htm"
        ],
    },
    "filtering": {
        "target_provinces": [
            "山东",
            "湖北",
            "安徽",
            "山西",
            "河北",
            "辽宁",
            "河南",
            "黑龙江",
            "甘肃",
            "陕西",
            "宁夏",
            "广东",
            "江西",
            "广西",
            "贵州",
        ],
        "province_aliases": {
            "广西": ["广西", "广西壮族自治区", "广"],
            "宁夏": ["宁夏", "宁夏回族自治区"],
            "黑龙江": ["黑龙江", "龙江"],
        },
        "event_keywords": [
            "台风",
            "大风",
            "沙尘",
            "降雪",
            "暴雪",
            "雨夹雪",
            "大雨",
            "暴雨",
            "大暴雨",
            "特大暴雨",
        ],
    },
    "runtime": {
        "timeout_seconds": 20,
    },
    "llm": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-reasoner",
        "api_key": "",
    },
    "smtp": {
        "host": "",
        "port": 465,
        "user": "",
        "password": "",
        "use_ssl": True,
        "from": "",
        "to": "",
        "subject_prefix": "[CMA]",
    },
}


def _merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge_dict(out[key], value)
        else:
            out[key] = value
    return out


def load_settings() -> Dict[str, Any]:
    base = dict(DEFAULT_SETTINGS)

    if not SETTINGS_PATH.exists():
        SETTINGS_PATH.write_text(
            json.dumps(DEFAULT_SETTINGS, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        try:
            raw = SETTINGS_PATH.read_text(encoding="utf-8")
            user_settings = json.loads(raw)
            if isinstance(user_settings, dict):
                base = _merge_dict(base, user_settings)
        except Exception:
            pass

    # Local private overrides; should be gitignored.
    if SETTINGS_LOCAL_PATH.exists():
        try:
            raw_local = SETTINGS_LOCAL_PATH.read_text(encoding="utf-8")
            local_settings = json.loads(raw_local)
            if isinstance(local_settings, dict):
                base = _merge_dict(base, local_settings)
        except Exception:
            pass

    return base


SETTINGS = load_settings()

SOURCE_URLS = SETTINGS["sources"]["urls"]
OVERVIEW_ONLY_URLS = SETTINGS["sources"].get("overview_only_urls", [])
TARGET_PROVINCES = SETTINGS["filtering"]["target_provinces"]
PROVINCE_ALIASES = SETTINGS["filtering"]["province_aliases"]
EVENT_KEYWORDS = SETTINGS["filtering"]["event_keywords"]


@dataclass
class AppConfig:
    days: int = 3
    timeout_seconds: int = 20
    output_dir: str = "."
    use_llm: bool = True

    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-reasoner"
    llm_api_key: str = ""

    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_ssl: bool = True
    smtp_from: str = ""
    smtp_to: str = ""
    smtp_subject_prefix: str = "[CMA]"

    @classmethod
    def from_settings(cls, days: int, use_llm: bool, output_dir: str) -> "AppConfig":
        llm = SETTINGS.get("llm", {})
        smtp = SETTINGS.get("smtp", {})
        runtime = SETTINGS.get("runtime", {})

        smtp_port_raw = str(smtp.get("port", 465)).strip() or "465"
        smtp_use_ssl_raw = str(smtp.get("use_ssl", True)).lower().strip()

        cfg = cls(
            days=days,
            use_llm=use_llm,
            output_dir=output_dir,
            timeout_seconds=int(runtime.get("timeout_seconds", 20)),
            llm_base_url=str(llm.get("base_url", "https://api.deepseek.com")).strip(),
            llm_model=str(llm.get("model", "deepseek-reasoner")).strip(),
            llm_api_key=str(llm.get("api_key", "")).strip(),
            smtp_host=str(smtp.get("host", "")).strip(),
            smtp_port=int(smtp_port_raw),
            smtp_user=str(smtp.get("user", "")).strip(),
            smtp_password=str(smtp.get("password", "")).strip(),
            smtp_use_ssl=smtp_use_ssl_raw in {"1", "true", "yes", "y"},
            smtp_from=str(smtp.get("from", "")).strip(),
            smtp_to=str(smtp.get("to", "")).strip(),
            smtp_subject_prefix=str(smtp.get("subject_prefix", "[CMA]")).strip() or "[CMA]",
        )

        # Optional env overrides for deployment/CI.
        cfg.llm_api_key = os.getenv("DEEPSEEK_API_KEY", cfg.llm_api_key).strip()
        cfg.llm_base_url = os.getenv("DEEPSEEK_BASE_URL", cfg.llm_base_url).strip() or cfg.llm_base_url
        cfg.llm_model = os.getenv("DEEPSEEK_MODEL", cfg.llm_model).strip() or cfg.llm_model

        cfg.smtp_host = os.getenv("SMTP_HOST", cfg.smtp_host).strip()
        cfg.smtp_user = os.getenv("SMTP_USER", cfg.smtp_user).strip()
        cfg.smtp_password = os.getenv("SMTP_PASSWORD", cfg.smtp_password).strip()
        cfg.smtp_from = os.getenv("SMTP_FROM", cfg.smtp_from).strip()
        cfg.smtp_to = os.getenv("SMTP_TO", cfg.smtp_to).strip()
        cfg.smtp_subject_prefix = os.getenv("SMTP_SUBJECT_PREFIX", cfg.smtp_subject_prefix).strip() or cfg.smtp_subject_prefix

        smtp_port_env = os.getenv("SMTP_PORT", "").strip()
        if smtp_port_env:
            cfg.smtp_port = int(smtp_port_env)

        smtp_ssl_env = os.getenv("SMTP_USE_SSL", "").lower().strip()
        if smtp_ssl_env:
            cfg.smtp_use_ssl = smtp_ssl_env in {"1", "true", "yes", "y"}

        return cfg


def future_dates(base: date, days: int) -> List[date]:
    return [base.fromordinal(base.toordinal() + i) for i in range(days)]
