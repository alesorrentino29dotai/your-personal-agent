from __future__ import annotations

import json
import re
from html import unescape
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlparse

import httpx

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"
)
_DDG_HTML_URL = "https://html.duckduckgo.com/html/"
_WS_RE = re.compile(r"\s+")


def _clean_ws(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


def _unwrap_ddg_url(href: str) -> str:
    if not href:
        return href
    if href.startswith("//"):
        href = "https:" + href
    try:
        parsed = urlparse(href)
    except ValueError:
        return href
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path in ("/l/", "/l"):
        qs = parse_qs(parsed.query)
        uddg = qs.get("uddg")
        if uddg:
            return unquote(uddg[0])
    return href


class _DDGResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._capture: str | None = None
        self._buf: list[str] = []
        self._depth: int = 0
        self._capture_depth: int = 0

    def _start_capture(self, kind: str) -> None:
        self._capture = kind
        self._buf = []
        self._capture_depth = 1

    def _stop_capture(self) -> str:
        text = _clean_ws("".join(self._buf))
        self._capture = None
        self._buf = []
        self._capture_depth = 0
        return text

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = {k: (v or "") for k, v in attrs}
        classes = attr_dict.get("class", "").split()

        if self._capture is not None:
            self._capture_depth += 1
            return

        if tag == "a" and "result__a" in classes:
            if self._current is None:
                self._current = {"title": "", "url": "", "snippet": ""}
            self._current["url"] = _unwrap_ddg_url(attr_dict.get("href", ""))
            self._start_capture("title")
            return

        if "result__snippet" in classes:
            if self._current is None:
                self._current = {"title": "", "url": "", "snippet": ""}
            self._start_capture("snippet")
            return

    def handle_endtag(self, tag: str) -> None:
        if self._capture is not None:
            self._capture_depth -= 1
            if self._capture_depth <= 0:
                kind = self._capture
                text = self._stop_capture()
                if self._current is None:
                    self._current = {"title": "", "url": "", "snippet": ""}
                if kind == "title":
                    self._current["title"] = text
                elif kind == "snippet":
                    self._current["snippet"] = text
                    if self._current.get("title") or self._current.get("url"):
                        self.results.append(self._current)
                    self._current = None

    def handle_data(self, data: str) -> None:
        if self._capture is not None:
            self._buf.append(data)


def web_search(query: str, max_results: int = 5) -> str:
    query = (query or "").strip()
    if not query:
        return "Error: web search failed: empty query"

    try:
        n = int(max_results)
    except (TypeError, ValueError):
        n = 5
    n = max(1, min(10, n))

    headers = {
        "User-Agent": _USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    try:
        with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
            resp = client.post(_DDG_HTML_URL, data={"q": query})
            resp.raise_for_status()
            html_text = resp.text
    except httpx.HTTPError as exc:
        return f"Error: web search failed: {exc}"
    except Exception as exc:
        return f"Error: web search failed: {exc}"

    parser = _DDGResultParser()
    try:
        parser.feed(html_text)
        parser.close()
    except Exception as exc:
        return f"Error: web search failed: parse error: {exc}"

    results = parser.results[:n]
    if not results:
        return f"No results for: {query}"

    lines: list[str] = []
    for i, item in enumerate(results, 1):
        title = item.get("title") or "(no title)"
        url = item.get("url") or ""
        snippet = item.get("snippet") or ""
        lines.append(f"{i}. {title}\n   {url}\n   {snippet}".rstrip())

    return "\n\n".join(lines)


class _TextExtractor(HTMLParser):
    _SKIP = {"script", "style", "noscript", "template", "svg", "head"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._SKIP:
            self._skip_depth += 1
        elif tag in ("br", "p", "li", "tr", "div", "h1", "h2", "h3", "h4", "h5", "h6"):
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag in ("p", "li", "tr", "div", "h1", "h2", "h3", "h4", "h5", "h6"):
            self._parts.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "br":
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(data)

    def get_text(self) -> str:
        raw = "".join(self._parts)
        lines = [_clean_ws(line) for line in raw.splitlines()]
        cleaned = "\n".join(line for line in lines if line)
        return unescape(cleaned)


def _is_textual(content_type: str) -> tuple[bool, bool]:
    ct = (content_type or "").lower().split(";", 1)[0].strip()
    if not ct:
        return False, False
    if ct == "text/html" or ct == "application/xhtml+xml":
        return True, True
    if ct.startswith("text/"):
        return True, False
    if ct in ("application/json", "application/xml", "application/ld+json"):
        return True, False
    if ct.endswith("+json") or ct.endswith("+xml"):
        return True, False
    return False, False


def fetch_url(url: str, max_chars: int = 8000) -> str:
    url = (url or "").strip()
    if not url:
        return "Error: empty url"
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url

    try:
        mc = int(max_chars)
    except (TypeError, ValueError):
        mc = 8000
    mc = max(200, mc)

    headers = {
        "User-Agent": _USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        with httpx.Client(timeout=20.0, follow_redirects=True, headers=headers) as client:
            resp = client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            text = resp.text
    except httpx.HTTPError as exc:
        return f"Error: fetch failed: {exc}"
    except Exception as exc:
        return f"Error: fetch failed: {exc}"

    is_text, is_html = _is_textual(content_type)
    if not is_text:
        return f"Error: unsupported content-type: {content_type or 'unknown'}"

    if is_html:
        extractor = _TextExtractor()
        try:
            extractor.feed(text)
            extractor.close()
            body = extractor.get_text()
        except Exception as exc:
            return f"Error: html parse failed: {exc}"
    else:
        body = text

    body = body.strip()
    if len(body) > mc:
        truncated = len(body) - mc
        body = body[:mc] + f"\n... [{truncated} chars truncated]"
    return body


SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web via DuckDuckGo and return a numbered list of "
                "title, url, and snippet for each result."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Number of results to return (1-10).",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": (
                "Fetch a URL and return its readable text content. HTML is "
                "stripped of tags; other text/JSON content is returned as-is. "
                "Output is truncated to max_chars."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Absolute URL to fetch.",
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "Maximum characters to return.",
                        "minimum": 200,
                        "default": 8000,
                    },
                },
                "required": ["url"],
            },
        },
    },
]


def dispatch(name: str, args: dict | str | None) -> str | None:
    if isinstance(args, str):
        try:
            parsed = json.loads(args) if args else {}
        except json.JSONDecodeError:
            return f"Error: invalid JSON arguments for {name}"
        args = parsed if isinstance(parsed, dict) else {}
    args = args or {}

    if name == "web_search":
        query = args.get("query", "")
        max_results = args.get("max_results", 5)
        return web_search(query, max_results)
    if name == "fetch_url":
        url = args.get("url", "")
        max_chars = args.get("max_chars", 8000)
        return fetch_url(url, max_chars)
    return None
