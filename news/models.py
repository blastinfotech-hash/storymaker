from django.db import models


class NewsSource(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    site_url = models.URLField(blank=True)
    rss_url = models.URLField(unique=True)
    is_active = models.BooleanField(default=True)
    last_fetched_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
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
    author = models.CharField(max_length=160, blank=True)
    summary = models.TextField(blank=True)
    content = models.TextField(blank=True)
    guid = models.CharField(max_length=500, blank=True)
    url = models.URLField(unique=True)
    image_url = models.URLField(blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    is_curated = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self) -> str:
        return self.title
