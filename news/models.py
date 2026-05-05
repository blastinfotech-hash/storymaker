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
    class ContextStatus(models.TextChoices):
        PENDING = "pending", "Pendente"
        SUFFICIENT = "sufficient", "Suficiente"
        INSUFFICIENT = "insufficient", "Insuficiente"
        FAILED = "failed", "Falhou"

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
    extracted_content = models.TextField(blank=True)
    context_char_count = models.PositiveIntegerField(default=0)
    context_status = models.CharField(
        max_length=20,
        choices=ContextStatus.choices,
        default=ContextStatus.PENDING,
    )
    context_last_checked_at = models.DateTimeField(null=True, blank=True)
    context_error = models.TextField(blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    is_curated = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self) -> str:
        return self.title
