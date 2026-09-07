"""Local browser/page fetch — no Browserbase required."""

from __future__ import annotations

from pathlib import Path
from urllib import error, request


class LocalBrowserProvider:
    """Fetch local files or public HTTP pages for WOD import experiments."""

    def fetch(self, url: str) -> str:
        if url.startswith("file://"):
            return Path(url.removeprefix("file://")).read_text(encoding="utf-8")
        path = Path(url)
        if path.exists():
            return path.read_text(encoding="utf-8")
        req = request.Request(url, method="GET", headers={"User-Agent": "aegis-local/0.1"})
        try:
            with request.urlopen(req, timeout=10) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except error.URLError:
            return ""


def fetch_page(url: str) -> str:
    return LocalBrowserProvider().fetch(url)
