from django.db import models

from core.models import TimeStampedModel


class NewsSource(TimeStampedModel):
    class Category(models.TextChoices):
        NOTEBOOK = "notebook", "Notebook"
        HARDWARE = "hardware", "Hardware"
        PERIPHERALS = "peripherals", "Peripherals"
        GENERAL = "general", "General tech"

    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(unique=True)
    website_url = models.URLField(blank=True)
    rss_url = models.URLField(unique=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.HARDWARE)
    is_active = models.BooleanField(default=True)
    priority = models.PositiveSmallIntegerField(default=10)
    notes = models.TextField(blank=True)
    last_ingested_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["priority", "name"]

    def __str__(self) -> str:
        return self.name


class NewsArticle(TimeStampedModel):
    source = models.ForeignKey(NewsSource, on_delete=models.CASCADE, related_name="articles")
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=320)
    url = models.URLField(unique=True)
    summary = models.TextField(blank=True)
    content = models.TextField(blank=True)
    author = models.CharField(max_length=200, blank=True)
    category = models.CharField(max_length=20, choices=NewsSource.Category.choices, blank=True)
    tags = models.CharField(max_length=300, blank=True)
    published_at = models.DateTimeField(blank=True, null=True)
    relevance_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [models.Index(fields=["-published_at"])]

    def __str__(self) -> str:
        return self.title
