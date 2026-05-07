from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from stories.forms import BulkProjectBatchForm, StoryProjectForm
from stories.models import BulkProjectBatch, StoryConcept, StoryImageVariant, StoryProject
from stories.tasks import queue_bulk_batch, queue_project_generation


@login_required
def home(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        return _handle_home_post(request)

    query = request.GET.get("q", "").strip()
    projects = StoryProject.objects.order_by("-updated_at")
    if query:
        projects = projects.filter(Q(title__icontains=query) | Q(topic__icontains=query) | Q(custom_brief__icontains=query))
    projects = list(projects[:24])
    batches = BulkProjectBatch.objects.order_by("-created_at")[:6]
    has_processing = any(project.is_processing for project in projects) or any(
        batch.status in {BulkProjectBatch.Status.QUEUED, BulkProjectBatch.Status.PARSING, BulkProjectBatch.Status.CREATING, BulkProjectBatch.Status.GENERATING}
        for batch in batches
    )
    return render(
        request,
        "stories/home.html",
        {
            "projects": projects,
            "batches": batches,
            "project_count": StoryProject.objects.count(),
            "batch_form": BulkProjectBatchForm(),
            "search_query": query,
            "has_processing": has_processing,
        },
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
        elif action == "generate":
            form = StoryProjectForm(request.POST, instance=project)
            if form.is_valid():
                form.save()
                project.status = StoryProject.Status.QUEUED
                project.error_message = ""
                project.save(update_fields=["status", "error_message", "updated_at"])
                queue_project_generation.delay(project.pk)
                messages.success(request, "Geracao colocada na fila. A pagina vai atualizar automaticamente.")
                return redirect("project_detail", slug=project.slug)
        else:
            return _handle_variant_action(request, project)
    else:
        form = StoryProjectForm(instance=project)

    concept = project.current_concept
    variants = list(concept.variants.order_by("variant_number")) if concept else []
    return render(
        request,
        "stories/project_detail.html",
        {
            "project": project,
            "form": form,
            "concept": concept,
            "variants": variants,
            "has_processing": project.is_processing,
        },
    )


def _handle_variant_action(request: HttpRequest, project: StoryProject) -> HttpResponse:
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
            queue_bulk_batch.delay(batch.pk)
            messages.success(request, "Lote enviado para processamento assíncrono.")
            return redirect("home")
        projects = list(StoryProject.objects.order_by("-updated_at")[:24])
        batches = BulkProjectBatch.objects.order_by("-created_at")[:6]
        return render(
            request,
            "stories/home.html",
            {
                "projects": projects,
                "batches": batches,
                "project_count": StoryProject.objects.count(),
                "batch_form": form,
                "search_query": "",
                "has_processing": True,
            },
        )
    return redirect("home")
