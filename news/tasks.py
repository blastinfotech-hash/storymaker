from celery import shared_task

from .models import NewsSource
from .services.rss import ingest_source


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def ingest_source_task(self, source_id: int) -> int:
    source = NewsSource.objects.filter(pk=source_id).first()
    if not source:
        return 0
    return ingest_source(source)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def ingest_active_sources_task(self) -> int:
    total = 0
    for source in NewsSource.objects.filter(is_active=True).order_by("priority", "name"):
        total += ingest_source(source)
    return total


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def enrich_article_context_task(self, article_id: int) -> None:
    # Backward-compatible no-op for old queued jobs from the previous RSS pipeline.
    return None


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def enrich_source_articles_task(self, source_id: int) -> None:
    source = NewsSource.objects.filter(pk=source_id).first()
    if not source:
        return
    ingest_source(source)
