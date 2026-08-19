import asyncio
import ipaddress
import re
import socket
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urljoin, urlparse

import feedparser
import httpx
from bs4 import BeautifulSoup
from bs4.element import Tag

MAX_RESPONSE_BYTES = 2_000_000
USER_AGENT = "Multi-Agent-Newsroom/0.1 (+source-capture)"


class IngestionError(ValueError):
    pass


@dataclass(frozen=True)
class IngestedSource:
    title: str
    url: str
    publisher: str | None
    snapshot_text: str
    published_at: datetime | None
    credibility_score: float
    credibility_signals: list[str]


async def validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise IngestionError("Only public HTTP and HTTPS URLs can be ingested")
    if parsed.username or parsed.password:
        raise IngestionError("URLs containing credentials cannot be ingested")
    try:
        addresses = await asyncio.get_running_loop().getaddrinfo(
            parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM
        )
    except socket.gaierror as exc:
        raise IngestionError("Source hostname could not be resolved") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise IngestionError("Private, loopback, and reserved network addresses are blocked")


async def fetch_public_url(url: str) -> tuple[str, str, str]:
    current = url
    async with httpx.AsyncClient(
        follow_redirects=False,
        timeout=httpx.Timeout(12),
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html, application/rss+xml, application/atom+xml",
        },
    ) as client:
        for _ in range(6):
            await validate_public_url(current)
            async with client.stream("GET", current) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise IngestionError("Source redirect did not include a destination")
                    current = urljoin(current, location)
                    continue
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0]
                if content_type not in {
                    "text/html",
                    "text/plain",
                    "application/rss+xml",
                    "application/atom+xml",
                    "application/xml",
                    "text/xml",
                }:
                    raise IngestionError(
                        f"Unsupported source content type: {content_type or 'unknown'}"
                    )
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > MAX_RESPONSE_BYTES:
                        raise IngestionError("Source exceeds the 2 MB capture limit")
                    chunks.append(chunk)
                return (
                    current,
                    content_type,
                    b"".join(chunks).decode(response.encoding or "utf-8", errors="replace"),
                )
    raise IngestionError("Source exceeded the redirect limit")


def credibility_score(
    *, url: str, publisher: str | None, published_at: datetime | None, text: str
) -> tuple[float, list[str]]:
    score = 20.0
    signals = ["Baseline: retrievable source snapshot"]
    if urlparse(url).scheme == "https":
        score += 20
        signals.append("Transport: HTTPS")
    if publisher:
        score += 20
        signals.append("Attribution: named publisher")
    if published_at:
        score += 15
        signals.append("Recency context: publication timestamp available")
    words = len(text.split())
    if words >= 100:
        score += 15
        signals.append("Evidence depth: at least 100 words captured")
    if words >= 300:
        score += 10
        signals.append("Evidence depth: at least 300 words captured")
    return min(score, 100), signals


def _clean_text(element: Tag) -> str:
    return re.sub(r"\s+", " ", element.get_text(" ", strip=True)).strip()


def parse_article(url: str, html: str) -> IngestedSource:
    soup = BeautifulSoup(html, "html.parser")
    for unwanted in soup.select("script, style, nav, footer, aside, form, noscript"):
        unwanted.decompose()
    title = (soup.title.string.strip() if soup.title and soup.title.string else None) or urlparse(
        url
    ).netloc
    publisher_tag = soup.select_one('meta[property="og:site_name"], meta[name="application-name"]')
    publisher = publisher_tag.get("content", "").strip() if publisher_tag else None
    article = soup.select_one("article") or soup.select_one("main") or soup.body
    text = _clean_text(article) if article else ""
    if len(text) < 20:
        raise IngestionError("The page did not contain enough readable article text")
    score, signals = credibility_score(url=url, publisher=publisher, published_at=None, text=text)
    return IngestedSource(title, url, publisher, text, None, score, signals)


def parse_feed(url: str, xml: str, max_items: int) -> list[IngestedSource]:
    feed = feedparser.parse(xml)
    if not feed.entries:
        raise IngestionError("The feed did not contain any entries")
    publisher = feed.feed.get("title") or urlparse(url).netloc
    results = []
    for entry in feed.entries[:max_items]:
        entry_url = entry.get("link") or url
        summary = BeautifulSoup(
            entry.get("summary") or entry.get("description") or "", "html.parser"
        ).get_text(" ", strip=True)
        if len(summary) < 20:
            continue
        published_at = None
        if entry.get("published_parsed"):
            published_at = datetime(*entry.published_parsed[:6], tzinfo=UTC)
        score, signals = credibility_score(
            url=entry_url, publisher=publisher, published_at=published_at, text=summary
        )
        results.append(
            IngestedSource(
                entry.get("title") or "Untitled feed entry",
                entry_url,
                publisher,
                summary,
                published_at,
                score,
                signals + ["Capture mode: feed-provided summary"],
            )
        )
    if not results:
        raise IngestionError("The feed entries did not contain usable text snapshots")
    return results


async def ingest_url(url: str, max_items: int) -> list[IngestedSource]:
    final_url, content_type, body = await fetch_public_url(url)
    looks_like_feed = (
        "xml" in content_type or "<rss" in body[:500].lower() or "<feed" in body[:500].lower()
    )
    return (
        parse_feed(final_url, body, max_items)
        if looks_like_feed
        else [parse_article(final_url, body)]
    )
