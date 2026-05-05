from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
import re
import threading
from urllib.request import Request, urlopen

import feedparser
from django.db import transaction
from django.utils import timezone
from django.utils.html import strip_tags

from .models import NewsArticle, NewsSource

MIN_NEWS_CONTEXT_CHARS = 2000


def _enqueue_source_enrichment(source: NewsSource) -> None:
    def _dispatch() -> None:
        try:
            from .tasks import enrich_source_articles_task

            enrich_source_articles_task.apply_async(args=[source.pk], retry=False)
        except Exception as exc:
            source.last_error = f"Fila de enriquecimento indisponivel: {exc}"
            source.last_fetched_at = timezone.now()
            source.save(update_fields=["last_error", "last_fetched_at", "updated_at"])

    threading.Thread(target=_dispatch, daemon=True).start()


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


def _build_article_context(article: NewsArticle) -> str:
    parts = [
        article.title or "",
        article.summary or "",
        article.content or "",
        article.extracted_content or "",
    ]
    return "\n".join(part.strip() for part in parts if part and part.strip())


def _extract_main_text_from_html(html: str) -> str:
    cleaned = re.sub(r"<script.*?>.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<style.*?>.*?</style>", " ", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = strip_tags(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def enrich_article_context(article: NewsArticle) -> NewsArticle:
    try:
        request = Request(
            article.url,
            headers={
                "User-Agent": "StorymakerBot/1.0 (+https://blastinfoetech.com)",
            },
        )
        with urlopen(request, timeout=15) as response:
            raw_html = response.read().decode("utf-8", errors="ignore")
        extracted = _extract_main_text_from_html(raw_html)
        article.extracted_content = extracted

        context = _build_article_context(article)
        article.context_char_count = len(context)
        article.context_status = (
            NewsArticle.ContextStatus.SUFFICIENT
            if article.context_char_count >= MIN_NEWS_CONTEXT_CHARS
            else NewsArticle.ContextStatus.INSUFFICIENT
        )
        article.context_error = ""
    except Exception as exc:
        context = _build_article_context(article)
        article.context_char_count = len(context)
        article.context_status = NewsArticle.ContextStatus.FAILED
        article.context_error = str(exc)

    article.context_last_checked_at = timezone.now()
    article.save(
        update_fields=[
            "extracted_content",
            "context_char_count",
            "context_status",
            "context_last_checked_at",
            "context_error",
            "updated_at",
        ]
    )
    return article


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
        article.context_status = NewsArticle.ContextStatus.PENDING
        article.context_error = ""
        article.context_last_checked_at = None
        article.save(update_fields=["context_status", "context_error", "context_last_checked_at", "updated_at"])
        if created:
            result.created += 1
        else:
            result.updated += 1

    source.last_error = ""
    source.last_fetched_at = timezone.now()
    source.save(update_fields=["last_error", "last_fetched_at", "updated_at"])
    _enqueue_source_enrichment(source)
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
