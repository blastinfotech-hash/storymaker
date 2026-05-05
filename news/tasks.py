from celery import shared_task

from .models import NewsArticle
from .services import enrich_article_context


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def enrich_article_context_task(self, article_id: int) -> None:
    article = NewsArticle.objects.filter(pk=article_id).first()
    if not article:
        return
    enrich_article_context(article)
