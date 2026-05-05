from celery import shared_task

from .models import NewsArticle
from .services import enrich_article_context


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def enrich_article_context_task(self, article_id: int) -> None:
    article = NewsArticle.objects.filter(pk=article_id).first()
    if not article:
        return
    enrich_article_context(article)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def enrich_source_articles_task(self, source_id: int) -> None:
    article_ids = list(
        NewsArticle.objects.filter(source_id=source_id)
        .exclude(context_status=NewsArticle.ContextStatus.SUFFICIENT)
        .values_list("pk", flat=True)
    )
    for article_id in article_ids:
        article = NewsArticle.objects.filter(pk=article_id).first()
        if article:
            enrich_article_context(article)
