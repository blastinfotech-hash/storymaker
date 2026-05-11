from django.core.management.base import BaseCommand

from news.models import NewsSource
from news.services.rss import ingest_source


class Command(BaseCommand):
    help = "Import articles from active RSS sources"

    def handle(self, *args, **options):
        total = 0
        for source in NewsSource.objects.filter(is_active=True):
            created = ingest_source(source)
            total += created
            self.stdout.write(self.style.SUCCESS(f"{source.name}: {created} new articles"))
        self.stdout.write(self.style.SUCCESS(f"Total new articles: {total}"))
