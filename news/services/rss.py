from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

import feedparser
from django.utils import timezone
from django.utils.text import slugify

from news.models import NewsArticle, NewsSource


KEYWORDS = {
    "notebook": Decimal("9.50"),
    "laptop": Decimal("9.50"),
    "placa de video": Decimal("10.00"),
    "gpu": Decimal("9.00"),
    "processador": Decimal("9.00"),
    "cpu": Decimal("8.50"),
    "placa-mae": Decimal("8.50"),
    "motherboard": Decimal("8.50"),
    "monitor": Decimal("7.50"),
    "mouse": Decimal("7.00"),
    "teclado": Decimal("7.00"),
    "ssd": Decimal("7.50"),
    "ram": Decimal("7.00"),
}


def score_article(title: str, summary: str) -> Decimal:
    haystack = f"{title} {summary}".lower()
    score = Decimal("5.00")
    for keyword, weight in KEYWORDS.items():
        if keyword in haystack:
            score = max(score, weight)
    return score


def ingest_source(source: NewsSource) -> int:
    parsed = feedparser.parse(source.rss_url)
    created_count = 0

    for entry in parsed.entries:
        url = entry.get("link")
        if not url:
            continue

        title = entry.get("title", "Untitled")
        summary = entry.get("summary", "")
        article, created = NewsArticle.objects.update_or_create(
            url=url,
            defaults={
                "source": source,
                "title": title[:300],
                "slug": slugify(title)[:320] or slugify(source.name),
                "summary": summary,
                "content": entry.get("description", summary),
                "author": entry.get("author", "")[:200],
                "category": source.category,
                "tags": ", ".join(tag.get("term", "") for tag in entry.get("tags", []) if tag.get("term"))[:300],
                "relevance_score": score_article(title, summary),
                "published_at": _entry_published_at(entry),
            },
        )
        if created:
            created_count += 1
        elif article.relevance_score == 0:
            article.relevance_score = score_article(title, summary)
            article.save(update_fields=["relevance_score", "updated_at"])

    source.last_ingested_at = timezone.now()
    source.save(update_fields=["last_ingested_at", "updated_at"])
    return created_count


def _entry_published_at(entry):
    published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not published_parsed:
        return None
    return datetime(*published_parsed[:6], tzinfo=dt_timezone.utc)
