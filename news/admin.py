from django.contrib import admin, messages
from django.utils.html import format_html

from news.models import NewsArticle, NewsSource
from news.services.rss import ingest_source


@admin.action(description="Import selected RSS sources")
def import_selected_sources(modeladmin, request, queryset):
    total = 0
    for source in queryset:
        total += ingest_source(source)
    messages.success(request, f"Imported {total} new articles from {queryset.count()} sources.")


@admin.register(NewsSource)
class NewsSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "priority", "is_active", "last_ingested_at", "admin_actions")
    list_filter = ("category", "is_active")
    search_fields = ("name", "rss_url", "website_url")
    prepopulated_fields = {"slug": ("name",)}
    actions = (import_selected_sources,)

    @admin.display(description="Actions")
    def admin_actions(self, obj):
        return format_html('<a class="button" href="{}">Import now</a>', f"{obj.pk}/import/")

    def get_urls(self):
        from django.urls import path

        urls = super().get_urls()
        custom_urls = [
            path("<int:source_id>/import/", self.admin_site.admin_view(self.import_view), name="news_source_import"),
        ]
        return custom_urls + urls

    def import_view(self, request, source_id):
        source = self.get_object(request, source_id)
        created = ingest_source(source)
        self.message_user(request, f"Imported {created} new articles from {source.name}.", level=messages.SUCCESS)
        from django.shortcuts import redirect

        return redirect(request.META.get("HTTP_REFERER", "../../"))


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "source", "category", "relevance_score", "published_at", "is_featured")
    list_filter = ("source", "category", "is_featured")
    search_fields = ("title", "summary", "url", "tags")
    readonly_fields = ("created_at", "updated_at")
