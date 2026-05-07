from django.core.management.base import BaseCommand

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
        created_count = 0
        for source in DEFAULT_SOURCES:
            _, created = NewsSource.objects.update_or_create(
                slug=source["slug"],
                defaults=source,
            )
            created_count += int(created)
        self.stdout.write(self.style.SUCCESS(f"Seeded RSS sources. New rows: {created_count}"))
