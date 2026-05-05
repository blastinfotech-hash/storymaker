from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser
from django.db import transaction
from django.utils import timezone

from .models import NewsArticle, NewsSource


@dataclass
class ImportResult:
    source: NewsSource
    created: int = 0
    updated: int = 0
    skipped: int = 0


def _entry_value(entry, *keys, default=""):
    for key in keys:
        value = entry.get(key)
        if value:
            return value
    return default


def _extract_image_url(entry) -> str:
    media_content = entry.get("media_content") or []
    if media_content and media_content[0].get("url"):
        return media_content[0]["url"]

    media_thumbnail = entry.get("media_thumbnail") or []
    if media_thumbnail and media_thumbnail[0].get("url"):
        return media_thumbnail[0]["url"]

    for link in entry.get("links", []):
        if link.get("type", "").startswith("image/") and link.get("href"):
            return link["href"]

    return ""


def _parse_published_at(entry):
    for key in ("published", "updated"):
        raw_value = entry.get(key)
        if not raw_value:
            continue
        try:
            parsed = parsedate_to_datetime(raw_value)
        except (TypeError, ValueError, IndexError):
            continue
        if parsed.tzinfo is None:
            parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed
    return None


@transaction.atomic
def import_source_articles(source: NewsSource, limit: int | None = None) -> ImportResult:
    parsed_feed = feedparser.parse(source.rss_url)
    result = ImportResult(source=source)

    if parsed_feed.bozo and not parsed_feed.entries:
        source.last_error = str(parsed_feed.bozo_exception)
        source.last_fetched_at = timezone.now()
        source.save(update_fields=["last_error", "last_fetched_at", "updated_at"])
        raise ValueError(f"Falha ao ler feed RSS de {source.name}: {parsed_feed.bozo_exception}")

    entries = parsed_feed.entries[:limit] if limit else parsed_feed.entries

    for entry in entries:
        url = _entry_value(entry, "link")
        if not url:
            result.skipped += 1
            continue

        defaults = {
            "source": source,
            "title": _entry_value(entry, "title", default="Sem titulo"),
            "author": _entry_value(entry, "author"),
            "summary": _entry_value(entry, "summary", "description"),
            "content": "\n\n".join(item.get("value", "") for item in entry.get("content", [])),
            "guid": _entry_value(entry, "id", "guid"),
            "image_url": _extract_image_url(entry),
            "published_at": _parse_published_at(entry),
        }

        article, created = NewsArticle.objects.update_or_create(url=url, defaults=defaults)
        if created:
            result.created += 1
        else:
            result.updated += 1

    source.last_error = ""
    source.last_fetched_at = timezone.now()
    source.save(update_fields=["last_error", "last_fetched_at", "updated_at"])
    return result


def import_active_sources(limit: int | None = None) -> list[ImportResult]:
    active_sources = list(NewsSource.objects.filter(is_active=True).order_by("name"))
    active_source_ids = [source.pk for source in active_sources]

    if active_source_ids:
        NewsArticle.objects.exclude(source_id__in=active_source_ids).delete()
        NewsArticle.objects.filter(source_id__in=active_source_ids).delete()
    else:
        NewsArticle.objects.all().delete()

    results = []
    for source in active_sources:
        results.append(import_source_articles(source=source, limit=limit))
    return results
