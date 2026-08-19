import asyncio
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from newsroom_api.ingestion import (
    IngestedSource,
    IngestionError,
    credibility_score,
    parse_article,
    parse_feed,
    validate_public_url,
)


def test_article_parser_captures_readable_evidence_and_signals() -> None:
    article = parse_article(
        "https://example.com/report",
        """
        <html><head><title>Verified city report</title>
        <meta property="og:site_name" content="Example News"></head>
        <body><nav>Ignore navigation</nav><article>
        <p>Officials published a detailed timeline after the council meeting.</p>
        <p>The source document records the vote and identifies every participant.</p>
        </article></body></html>
        """,
    )

    assert article.title == "Verified city report"
    assert article.publisher == "Example News"
    assert "Ignore navigation" not in article.snapshot_text
    assert article.credibility_score == 60
    assert "Transport: HTTPS" in article.credibility_signals


def test_feed_parser_creates_immutable_entry_snapshots() -> None:
    sources = parse_feed(
        "https://wire.example/feed.xml",
        """<?xml version="1.0"?><rss version="2.0"><channel><title>City Wire</title>
        <item><title>First bulletin</title><link>https://wire.example/first</link>
        <pubDate>Wed, 19 Aug 2026 10:00:00 GMT</pubDate>
        <description>Officials confirmed the first bulletin with enough detail
        for review.</description>
        </item></channel></rss>""",
        5,
    )

    assert len(sources) == 1
    assert sources[0].title == "First bulletin"
    assert sources[0].publisher == "City Wire"
    assert sources[0].published_at is not None
    assert "Capture mode: feed-provided summary" in sources[0].credibility_signals


def test_credibility_score_is_explainable_and_bounded() -> None:
    score, signals = credibility_score(
        url="https://example.com/report",
        publisher="Example News",
        published_at=datetime.now(UTC),
        text="word " * 400,
    )

    assert score == 100
    assert len(signals) == 6


def test_private_network_source_is_rejected(monkeypatch) -> None:
    async def private_address(*args, **kwargs):
        return [(2, 1, 6, "", ("127.0.0.1", 80))]

    loop = asyncio.new_event_loop()
    monkeypatch.setattr(loop, "getaddrinfo", private_address)
    asyncio.set_event_loop(loop)
    try:
        try:
            loop.run_until_complete(validate_public_url("http://localhost/internal"))
        except IngestionError as exc:
            assert "reserved network addresses" in str(exc)
        else:
            raise AssertionError("Private source URL was accepted")
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_ingestion_endpoint_persists_captured_source(client: TestClient, monkeypatch) -> None:
    story = client.post("/api/v1/stories", json={"title": "A source ingestion story"}).json()

    async def fake_ingest(url: str, max_items: int) -> list[IngestedSource]:
        assert url == "https://example.com/report"
        assert max_items == 5
        return [
            IngestedSource(
                title="Captured report",
                url=url,
                publisher="Example News",
                snapshot_text="This is an immutable snapshot captured from the published report.",
                published_at=None,
                credibility_score=60,
                credibility_signals=["Transport: HTTPS", "Attribution: named publisher"],
            )
        ]

    monkeypatch.setattr("newsroom_api.routers.stories.ingest_url", fake_ingest)
    response = client.post(
        f"/api/v1/stories/{story['id']}/sources/ingest",
        json={"url": "https://example.com/report"},
    )

    assert response.status_code == 201
    source = response.json()[0]
    assert source["snapshot_text"].startswith("This is an immutable snapshot")
    assert source["credibility_score"] == 60
    assert source["credibility_signals"] == [
        "Transport: HTTPS",
        "Attribution: named publisher",
    ]
