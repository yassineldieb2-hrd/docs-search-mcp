"""Safe-ish page fetcher: http(s) only, SSRF guard, robots.txt, size cap, HTML -> markdown.

Idea adapted from the `fetch` server in modelcontextprotocol/servers (MIT): fetch a URL, check
robots.txt, convert HTML to markdown, return in slices via start_index. Differences: a private-network
(SSRF) guard re-applied on every redirect hop, a download size cap, and stdlib robots parsing.
"""
from __future__ import annotations

import ipaddress
import re
import socket
import urllib.robotparser
from urllib.parse import urljoin, urlparse

import httpx
from markdownify import markdownify

USER_AGENT = "docs-search-mcp/0.1 (+https://github.com/yassineldieb2-hrd/docs-search-mcp)"
MAX_BYTES = 2_000_000
MAX_REDIRECTS = 3


class FetchError(ValueError):
    pass


def check_url(url: str, allow_private: bool = False) -> None:
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise FetchError("only absolute http(s) URLs are allowed")
    if allow_private:
        return
    try:
        infos = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80))
    except socket.gaierror as e:
        raise FetchError(f"cannot resolve host {p.hostname}: {e}") from None
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise FetchError(f"refusing to fetch non-public address {ip} (SSRF protection)") from None


def robots_allows(client: httpx.Client, url: str, allow_private: bool) -> bool:
    p = urlparse(url)
    robots_url = f"{p.scheme}://{p.netloc}/robots.txt"
    check_url(robots_url, allow_private)
    try:
        r = client.get(robots_url, headers={"User-Agent": USER_AGENT})
    except httpx.HTTPError:
        raise FetchError(f"could not fetch {robots_url}; not fetching without knowing the rules") from None
    if r.status_code in (401, 403):
        return False
    if r.status_code >= 400:
        return True  # no robots.txt (404 etc.) means no restrictions
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(r.text.splitlines())
    return rp.can_fetch(USER_AGENT, url)


def html_to_markdown(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer|header)\b.*?</\1>", "", html)
    md = markdownify(html, heading_style="ATX")
    return re.sub(r"\n{3,}", "\n\n", md).strip()


def fetch_url(url: str, max_length: int = 5000, start_index: int = 0, raw: bool = False,
              allow_private: bool = False, respect_robots: bool = True, timeout: float = 15.0) -> dict:
    if not 1 <= max_length <= 50_000:
        raise FetchError("max_length must be between 1 and 50000")
    if start_index < 0:
        raise FetchError("start_index must be >= 0")
    with httpx.Client(follow_redirects=False, timeout=timeout) as client:
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            check_url(current, allow_private)
            if respect_robots and not robots_allows(client, current, allow_private):
                raise FetchError(f"robots.txt disallows fetching {current}")
            with client.stream("GET", current, headers={"User-Agent": USER_AGENT}) as r:
                if r.is_redirect:
                    current = urljoin(current, r.headers.get("location", ""))
                    continue
                if r.status_code >= 400:
                    raise FetchError(f"{current} returned HTTP {r.status_code}")
                body = b""
                for chunk in r.iter_bytes():
                    body += chunk
                    if len(body) > MAX_BYTES:
                        raise FetchError(f"response larger than {MAX_BYTES} bytes")
                ctype = r.headers.get("content-type", "")
                text = body.decode(r.encoding or "utf-8", errors="replace")
                break
        else:
            raise FetchError(f"more than {MAX_REDIRECTS} redirects")
    is_html = "html" in ctype.lower() or text.lstrip()[:15].lower().startswith(("<!doctype", "<html"))
    content = text if (raw or not is_html) else html_to_markdown(text)
    piece = content[start_index:start_index + max_length]
    nxt = start_index + max_length
    return {"url": current, "content_type": ctype, "total_chars": len(content), "start_index": start_index,
            "content": piece, "next_start_index": nxt if nxt < len(content) else None}
