from django.core.management.base import BaseCommand
from django.db import connection

from news.models import NewsSource


DEFAULT_SOURCES = [
    {
        "name": "Tom's Hardware",
        "slug": "toms-hardware",
        "website_url": "https://www.tomshardware.com/",
        "rss_url": "https://www.tomshardware.com/feeds/all",
        "category": NewsSource.Category.HARDWARE,
        "priority": 1,
    },
    {
        "name": "TechPowerUp",
        "slug": "techpowerup",
        "website_url": "https://www.techpowerup.com/",
        "rss_url": "https://www.techpowerup.com/rss/news",
        "category": NewsSource.Category.HARDWARE,
        "priority": 2,
    },
    {
        "name": "Phoronix",
        "slug": "phoronix",
        "website_url": "https://www.phoronix.com/",
        "rss_url": "https://www.phoronix.com/rss.php",
        "category": NewsSource.Category.GENERAL,
        "priority": 3,
    },
    {
        "name": "The Verge",
        "slug": "the-verge",
        "website_url": "https://www.theverge.com/",
        "rss_url": "https://www.theverge.com/rss/index.xml",
        "category": NewsSource.Category.GENERAL,
        "priority": 4,
    },
]


class Command(BaseCommand):
    help = "Seed initial RSS sources for the Storymaker workflow"

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            existing_columns = {column.name for column in connection.introspection.get_table_description(cursor, NewsSource._meta.db_table)}
        if "slug" not in existing_columns:
            self.stdout.write(self.style.WARNING("Skipping RSS seed because legacy schema is not repaired yet."))
            return

        created_count = 0
        for source in DEFAULT_SOURCES:
            defaults = dict(source)
            if "site_url" in existing_columns:
                defaults["site_url"] = source["website_url"]
            _, created = NewsSource.objects.update_or_create(slug=source["slug"], defaults=defaults)
            created_count += int(created)
        self.stdout.write(self.style.SUCCESS(f"Seeded RSS sources. New rows: {created_count}"))
