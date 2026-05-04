from urllib.parse import urlparse

from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from .forms import BulkNewsSourceForm, NewsSourceForm
from .models import NewsArticle, NewsSource
from .services import import_active_sources, import_source_articles


def _parse_bulk_sources(blob: str) -> list[dict]:
    parsed_sources = []
    for raw_line in blob.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        parts = [part.strip() for part in line.split("|")]
        if len(parts) == 1:
            rss_url = parts[0]
            host = urlparse(rss_url).netloc.replace("www.", "")
            name = host or rss_url
            site_url = ""
            description = ""
        elif len(parts) == 2:
            name, rss_url = parts
            site_url = ""
            description = ""
        elif len(parts) == 3:
            name, rss_url, site_url = parts
            description = ""
        else:
            name, rss_url, site_url, description = parts[0], parts[1], parts[2], " | ".join(parts[3:])

        parsed_sources.append(
            {
                "name": name,
                "rss_url": rss_url,
                "site_url": site_url,
                "description": description,
                "is_active": True,
            }
        )
    return parsed_sources


def sources_panel(request, pk: int | None = None):
    editing_source = None
    if pk is not None:
        editing_source = get_object_or_404(NewsSource, pk=pk)

    source_form = NewsSourceForm(instance=editing_source, prefix="source")
    bulk_form = BulkNewsSourceForm(prefix="bulk")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "save_source":
            source_id = request.POST.get("source_id")
            editing_source = get_object_or_404(NewsSource, pk=source_id) if source_id else None
            source_form = NewsSourceForm(request.POST, instance=editing_source, prefix="source")
            if source_form.is_valid():
                source = source_form.save()
                messages.success(request, f"Fonte '{source.name}' salva com sucesso.")
                return redirect("news:sources-panel")

        if action == "save_bulk_sources":
            bulk_form = BulkNewsSourceForm(request.POST, prefix="bulk")
            source_form = NewsSourceForm(instance=editing_source, prefix="source")
            if bulk_form.is_valid():
                created_count = 0
                updated_count = 0
                for source_data in _parse_bulk_sources(bulk_form.cleaned_data["sources_blob"]):
                    _, created = NewsSource.objects.update_or_create(rss_url=source_data["rss_url"], defaults=source_data)
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                messages.success(request, f"Importacao em massa concluida: {created_count} criadas, {updated_count} atualizadas.")
                return redirect("news:sources-panel")

        if action == "toggle_source":
            source = get_object_or_404(NewsSource, pk=request.POST.get("source_id"))
            source.is_active = not source.is_active
            source.save(update_fields=["is_active", "updated_at"])
            status_label = "ativada" if source.is_active else "desativada"
            messages.success(request, f"Fonte '{source.name}' {status_label}.")
            return redirect("news:sources-panel")

        if action == "delete_source":
            source = get_object_or_404(NewsSource, pk=request.POST.get("source_id"))
            source_name = source.name
            source.delete()
            messages.success(request, f"Fonte '{source_name}' removida.")
            return redirect("news:sources-panel")

        if action == "import_source":
            source = get_object_or_404(NewsSource, pk=request.POST.get("source_id"))
            try:
                result = import_source_articles(source=source, limit=20)
            except ValueError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(
                    request,
                    f"{source.name}: {result.created} criados, {result.updated} atualizados, {result.skipped} ignorados.",
                )
            return redirect("news:sources-panel")

        if action == "import_active_sources":
            try:
                results = import_active_sources(limit=20)
            except ValueError as exc:
                messages.error(request, str(exc))
            else:
                total_created = sum(result.created for result in results)
                total_updated = sum(result.updated for result in results)
                total_skipped = sum(result.skipped for result in results)
                messages.success(
                    request,
                    f"Importacao concluida: {total_created} criados, {total_updated} atualizados, {total_skipped} ignorados.",
                )
            return redirect("news:sources-panel")
    sources = NewsSource.objects.annotate(article_count=Count("articles")).order_by("name")
    return render(
        request,
        "news/sources_panel.html",
        {
            "sources": sources,
            "source_form": source_form,
            "bulk_form": bulk_form,
            "editing_source": editing_source,
        },
    )


def articles_panel(request):
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "toggle_curated":
            article = get_object_or_404(NewsArticle, pk=request.POST.get("article_id"))
            article.is_curated = not article.is_curated
            article.save(update_fields=["is_curated", "updated_at"])
            label = "marcado como curado" if article.is_curated else "removido da curadoria"
            messages.success(request, f"Artigo '{article.title}' {label}.")
            return redirect("news:articles-panel")

    source_filter = request.GET.get("source", "")
    curated_filter = request.GET.get("curated", "all")

    articles = NewsArticle.objects.select_related("source")
    if source_filter:
        articles = articles.filter(source_id=source_filter)

    if curated_filter == "yes":
        articles = articles.filter(is_curated=True)
    elif curated_filter == "no":
        articles = articles.filter(is_curated=False)

    articles = articles[:80]
    sources = NewsSource.objects.order_by("name")
    return render(
        request,
        "news/articles_panel.html",
        {
            "articles": articles,
            "sources": sources,
            "selected_source": source_filter,
            "selected_curated": curated_filter,
        },
    )
