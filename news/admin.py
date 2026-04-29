from django.contrib import admin

from .models import NewsArticle, NewsSource


@admin.register(NewsSource)
class NewsSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "rss_url", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "rss_url")


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "source", "published_at", "is_curated")
    list_filter = ("is_curated", "source")
    search_fields = ("title", "summary", "url")
