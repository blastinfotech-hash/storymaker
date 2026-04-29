from django.db import models


class NewsSource(models.Model):
    name = models.CharField(max_length=120)
    site_url = models.URLField(blank=True)
    rss_url = models.URLField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class NewsArticle(models.Model):
    source = models.ForeignKey(
        NewsSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
    )
    title = models.CharField(max_length=220)
    summary = models.TextField(blank=True)
    content = models.TextField(blank=True)
    url = models.URLField(unique=True)
    published_at = models.DateTimeField(null=True, blank=True)
    is_curated = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self) -> str:
        return self.title
