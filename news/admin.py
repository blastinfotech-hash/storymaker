from django.contrib import admin
from django.contrib import messages

from .models import NewsArticle, NewsSource
from .services import import_source_articles


@admin.register(NewsSource)
class NewsSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "rss_url", "is_active", "last_fetched_at")
    list_filter = ("is_active",)
    search_fields = ("name", "rss_url", "description")
    actions = ["import_selected_sources"]

    @admin.action(description="Importar artigos RSS das fontes selecionadas")
    def import_selected_sources(self, request, queryset):
        for source in queryset:
            try:
                result = import_source_articles(source, limit=20)
            except ValueError as exc:
                self.message_user(request, f"{source.name}: {exc}", level=messages.ERROR)
                continue

            self.message_user(
                request,
                f"{source.name}: {result.created} criados, {result.updated} atualizados, {result.skipped} ignorados.",
                level=messages.SUCCESS,
            )


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "source", "published_at", "is_curated")
    list_filter = ("is_curated", "source")
    search_fields = ("title", "summary", "content", "url", "guid", "author")
