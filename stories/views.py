from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.db import connection, transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from stories.forms import BulkProjectBatchForm, StoryProjectForm
from stories.models import BulkProjectBatch, StoryConcept, StoryImageVariant, StoryProject
from stories.tasks import queue_bulk_batch, queue_concept_images, queue_project_generation

logger = logging.getLogger(__name__)


@login_required
def home(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        return _handle_home_post(request)

    query = request.GET.get("q", "").strip()
    return render(request, "stories/home.html", _build_home_context(query=query, batch_form=BulkProjectBatchForm()))


@login_required
def home_status(request: HttpRequest) -> JsonResponse:
    query = request.GET.get("q", "").strip()
    context = _build_home_context(query=query, batch_form=BulkProjectBatchForm())
    project_cards = [
        {
            "id": project.pk,
            "html": render_to_string("stories/partials/project_card.html", {"project": project}, request=request),
        }
        for project in context["projects"]
    ]
    batch_cards = [
        {
            "id": batch.pk,
            "html": render_to_string("stories/partials/batch_card.html", {"batch": batch}, request=request),
        }
        for batch in context["batches"]
    ]
    return JsonResponse(
        {
            "project_count": context["project_count"],
            "has_processing": context["has_processing"],
            "project_cards": project_cards,
            "batch_cards": batch_cards,
        }
    )


@login_required
def create_project(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = StoryProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.status = StoryProject.Status.DRAFT
            project.save()
            messages.success(request, "Projeto criado. Agora voce pode disparar a geracao async.")
            return redirect("project_detail", slug=project.slug)
    else:
        form = StoryProjectForm(initial={"brand_mode": StoryProject.BrandMode.BLAST, "requested_image_count": 2})
    return render(request, "stories/create_project.html", {"form": form})


@login_required
def project_detail(request: HttpRequest, slug: str) -> HttpResponse:
    project = get_object_or_404(StoryProject, slug=slug)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "save":
            form = StoryProjectForm(request.POST, instance=project)
            if form.is_valid():
                form.save()
                messages.success(request, "Projeto atualizado.")
                return redirect("project_detail", slug=project.slug)
        elif action == "generate_concept":
            form = StoryProjectForm(request.POST, instance=project)
            if form.is_valid():
                form.save()
                project.status = StoryProject.Status.QUEUED
                project.error_message = ""
                project.save(update_fields=["status", "error_message", "updated_at"])
                try:
                    queue_project_generation.delay(project.pk, False)
                except Exception as exc:  # noqa: BLE001
                    project.status = StoryProject.Status.FAILED
                    project.error_message = f"Fila assíncrona indisponível: {exc}"
                    project.save(update_fields=["status", "error_message", "updated_at"])
                    messages.error(request, project.error_message)
                    return redirect("project_detail", slug=project.slug)
                messages.success(request, "Geração de conceito colocada na fila.")
                return redirect("project_detail", slug=project.slug)
        elif action == "generate_images":
            form = StoryProjectForm(request.POST, instance=project)
            if form.is_valid():
                form.save()
                concept = project.current_concept
                if concept is None:
                    messages.error(request, "Gere um conceito antes de solicitar as imagens.")
                    return redirect("project_detail", slug=project.slug)
                project.status = StoryProject.Status.IMAGE_GENERATING
                project.error_message = ""
                project.save(update_fields=["status", "error_message", "updated_at"])
                try:
                    queue_concept_images.delay(concept.pk)
                except Exception as exc:  # noqa: BLE001
                    project.status = StoryProject.Status.FAILED
                    project.error_message = f"Fila assíncrona indisponível: {exc}"
                    project.save(update_fields=["status", "error_message", "updated_at"])
                    messages.error(request, project.error_message)
                    return redirect("project_detail", slug=project.slug)
                messages.success(request, "Geração de imagens colocada na fila.")
                return redirect("project_detail", slug=project.slug)
        elif action == "delete_project":
            if _delete_project(project):
                messages.success(request, "Projeto excluído.")
            else:
                messages.error(request, "Não foi possível excluir o projeto agora.")
            return redirect("home")
        else:
            return _handle_variant_action(request, project)
    else:
        form = StoryProjectForm(instance=project)

    context = _build_project_detail_context(project, form)
    return render(request, "stories/project_detail.html", context)


@login_required
def project_detail_status(request: HttpRequest, slug: str) -> JsonResponse:
    project = get_object_or_404(StoryProject, slug=slug)
    context = _build_project_detail_context(project, StoryProjectForm(instance=project))
    return JsonResponse(
        {
            "status_display": project.get_status_display(),
            "has_processing": project.is_processing,
            "actions_html": render_to_string("stories/partials/project_actions.html", context, request=request),
            "status_html": render_to_string("stories/partials/project_status.html", context, request=request),
            "concept_html": render_to_string("stories/partials/project_concept.html", context, request=request),
            "variants_html": render_to_string("stories/partials/project_variants.html", context, request=request),
        }
    )


def _handle_variant_action(request: HttpRequest, project: StoryProject) -> HttpResponse:
    action = request.POST.get("action")
    if action != "select_variant":
        messages.error(request, "Ação da variante inválida.")
        return redirect("project_detail", slug=project.slug)
    variant_id = request.POST.get("variant_id")
    variant = get_object_or_404(StoryImageVariant, pk=variant_id, concept__project=project)
    variant.concept.variants.update(is_selected=False)
    variant.is_selected = True
    variant.save(update_fields=["is_selected", "updated_at"])
    project.status = StoryProject.Status.APPROVED
    project.save(update_fields=["status", "updated_at"])
    messages.success(request, f"Variante {variant.variant_number} marcada como selecionada.")
    return redirect("project_detail", slug=project.slug)


def _handle_home_post(request: HttpRequest) -> HttpResponse:
    action = request.POST.get("action")
    if action == "bulk_create":
        form = BulkProjectBatchForm(request.POST)
        if form.is_valid():
            batch = form.save(commit=False)
            batch.name = f"Lote {timezone.now().strftime('%d/%m %H:%M')}"
            batch.status = BulkProjectBatch.Status.QUEUED
            batch.save()
            try:
                queue_bulk_batch.delay(batch.pk)
            except Exception as exc:  # noqa: BLE001
                batch.status = BulkProjectBatch.Status.FAILED
                batch.error_message = f"Fila assíncrona indisponível: {exc}"
                batch.save(update_fields=["status", "error_message", "updated_at"])
                messages.error(request, batch.error_message)
                return redirect("home")
            messages.success(request, "Lote enviado para processamento assíncrono.")
            return redirect("home")
        return render(request, "stories/home.html", _build_home_context(query="", batch_form=form))
    if action == "delete_project":
        project = get_object_or_404(StoryProject, pk=request.POST.get("project_id"))
        if _delete_project(project):
            messages.success(request, "Projeto excluído.")
        else:
            messages.error(request, "Não foi possível excluir o projeto agora.")
        return redirect("home")
    return redirect("home")


def _build_home_context(query: str, batch_form: BulkProjectBatchForm) -> dict:
    projects = StoryProject.objects.order_by("-updated_at")
    if query:
        projects = projects.filter(Q(title__icontains=query) | Q(topic__icontains=query) | Q(custom_brief__icontains=query))
    projects = list(projects[:24])
    batches = list(BulkProjectBatch.objects.order_by("-created_at")[:6])
    has_processing = any(project.is_processing for project in projects) or any(
        batch.status in {BulkProjectBatch.Status.QUEUED, BulkProjectBatch.Status.PARSING, BulkProjectBatch.Status.CREATING, BulkProjectBatch.Status.GENERATING}
        for batch in batches
    )
    return {
        "projects": projects,
        "batches": batches,
        "project_count": StoryProject.objects.count(),
        "batch_form": batch_form,
        "search_query": query,
        "has_processing": has_processing,
    }


def _build_project_detail_context(project: StoryProject, form: StoryProjectForm) -> dict:
    concept = project.current_concept
    variants = list(concept.variants.order_by("variant_number")) if concept else []
    return {
        "project": project,
        "form": form,
        "concept": concept,
        "variants": variants,
        "has_processing": project.is_processing,
    }


def _delete_project(project: StoryProject) -> bool:
    try:
        with transaction.atomic():
            _delete_project_assets(project)
            _delete_legacy_story_versions(project.pk)
            project.delete()
        return True
    except Exception:
        logger.exception("Failed to delete project %s", project.pk)
        return False


def _delete_project_assets(project: StoryProject) -> None:
    for variant in StoryImageVariant.objects.filter(concept__project=project).exclude(asset=""):
        if variant.asset:
            variant.asset.delete(save=False)


def _delete_legacy_story_versions(project_id: int) -> None:
    with connection.cursor() as cursor:
        tables = set(connection.introspection.table_names(cursor))
        if "stories_storyversion" not in tables:
            return

        columns = {column.name for column in connection.introspection.get_table_description(cursor, "stories_storyversion")}
        file_column = None
        if "generated_image" in columns:
            file_column = "generated_image"
        elif "asset" in columns:
            file_column = "asset"

        if file_column:
            cursor.execute(f'SELECT "{file_column}" FROM "stories_storyversion" WHERE project_id = %s', [project_id])
            for (file_name,) in cursor.fetchall():
                if file_name:
                    default_storage.delete(file_name)

        cursor.execute('DELETE FROM "stories_storyversion" WHERE project_id = %s', [project_id])
