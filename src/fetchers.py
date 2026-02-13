from __future__ import annotations

from dataclasses import dataclass
from typing import List

import requests
from bs4 import BeautifulSoup


@dataclass
class SourceDocument:
    url: str
    text: str


def fetch_url_text(url: str, timeout_seconds: int = 20) -> str:
    response = requests.get(url, timeout=timeout_seconds)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    soup = BeautifulSoup(response.text, "html.parser")
    return soup.get_text("\n", strip=True)


def fetch_all(urls: List[str], timeout_seconds: int = 20) -> List[SourceDocument]:
    docs: List[SourceDocument] = []
    for url in urls:
        try:
            text = fetch_url_text(url, timeout_seconds=timeout_seconds)
            docs.append(SourceDocument(url=url, text=text))
        except Exception as exc:  # noqa: BLE001
            docs.append(SourceDocument(url=url, text=f"[FETCH_FAILED] {exc}"))
    return docs
