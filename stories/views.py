from django.contrib import messages
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from branding.models import BrandGuide

from .forms import ChangeRequestForm, StoryProjectForm
from .models import StoryProject, StoryVersion
from .services import generate_image_asset, generate_story_concept, refine_image_direction


def dashboard(request):
    if request.method == "POST":
        form = StoryProjectForm(request.POST)
        if form.is_valid():
            project = form.save()
            messages.success(request, "Projeto criado. Gere o conceito para iniciar o workflow.")
            return redirect("stories:project-detail", pk=project.pk)
    else:
        form = StoryProjectForm()

    guide = BrandGuide.get_active()
    projects = StoryProject.objects.select_related("source_article").prefetch_related("versions")[:12]
    return render(
        request,
        "stories/dashboard.html",
        {
            "form": form,
            "guide": guide,
            "projects": projects,
        },
    )


def _create_concept_version(
    project: StoryProject,
    guide: BrandGuide,
    change_request: str = "",
    base_version: StoryVersion | None = None,
) -> StoryVersion:
    concept = generate_story_concept(
        project=project,
        guide=guide,
        change_request=change_request,
        base_version=base_version,
    )
    version = StoryVersion(
        project=project,
        based_on=base_version,
        change_request=change_request,
        headline=concept["headline"],
        copy_text=concept["copy_text"],
        visual_direction=concept["visual_direction"],
        image_prompt=concept["image_prompt"],
        generation_notes=concept["generation_notes"],
        text_model=concept["text_model"],
    )
    version.save()
    project.status = StoryProject.Status.CONCEPT_READY
    project.save(update_fields=["status", "updated_at"])
    return version


def _create_image_version(
    project: StoryProject,
    guide: BrandGuide,
    base_version: StoryVersion,
    change_request: str = "",
) -> StoryVersion:
    version = StoryVersion(
        project=project,
        based_on=base_version,
        change_request=change_request,
        headline=base_version.headline,
        copy_text=base_version.copy_text,
        visual_direction=base_version.visual_direction,
        image_prompt=base_version.image_prompt,
        generation_notes=base_version.generation_notes,
        text_model=base_version.text_model,
    )

    if change_request.strip():
        refined = refine_image_direction(base_version, guide, change_request)
        version.visual_direction = refined["visual_direction"]
        version.image_prompt = refined["image_prompt"]
        version.generation_notes = refined["generation_notes"]
        version.text_model = refined["text_model"]

    version.save()
    file_name, content, final_prompt, image_model = generate_image_asset(version, guide, change_request)
    version.prompt_snapshot = final_prompt
    version.image_model = image_model
    version.generated_image.save(file_name, content, save=False)
    version.save(update_fields=["prompt_snapshot", "image_model", "generated_image"])

    project.status = StoryProject.Status.IMAGE_READY
    project.save(update_fields=["status", "updated_at"])
    return version


def project_detail(request, pk: int):
    project = get_object_or_404(
        StoryProject.objects.select_related("source_article").prefetch_related("versions"),
        pk=pk,
    )
    guide = BrandGuide.get_active()
    latest_version = project.latest_version

    concept_form = ChangeRequestForm(prefix="concept")
    image_form = ChangeRequestForm(prefix="image")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "generate_concept":
            _create_concept_version(project=project, guide=guide)
            messages.success(request, "Conceito gerado com sucesso.")
            return redirect("stories:project-detail", pk=project.pk)

        if action == "refine_concept":
            concept_form = ChangeRequestForm(request.POST, prefix="concept")
            if concept_form.is_valid():
                _create_concept_version(
                    project=project,
                    guide=guide,
                    change_request=concept_form.cleaned_data["change_request"],
                    base_version=latest_version,
                )
                messages.success(request, "Nova versao de conceito criada.")
                return redirect("stories:project-detail", pk=project.pk)

        if action == "generate_image":
            if not latest_version or not latest_version.has_concept:
                messages.error(request, "Gere ou ajuste o conceito antes de renderizar a imagem.")
            else:
                _create_image_version(project=project, guide=guide, base_version=latest_version)
                messages.success(request, "Imagem gerada e salva no historico.")
                return redirect("stories:project-detail", pk=project.pk)

        if action == "refine_image":
            image_form = ChangeRequestForm(request.POST, prefix="image")
            if image_form.is_valid():
                if not latest_version or not latest_version.has_concept:
                    messages.error(request, "Gere um conceito antes de pedir ajustes na imagem.")
                else:
                    _create_image_version(
                        project=project,
                        guide=guide,
                        base_version=latest_version,
                        change_request=image_form.cleaned_data["change_request"],
                    )
                    messages.success(request, "Nova versao de imagem criada com os ajustes pedidos.")
                    return redirect("stories:project-detail", pk=project.pk)

        if action == "approve":
            if not latest_version or not latest_version.has_image:
                messages.error(request, "A aprovacao exige uma imagem gerada.")
            else:
                project.status = StoryProject.Status.APPROVED
                project.save(update_fields=["status", "updated_at"])
                messages.success(request, "Story aprovado.")
                return redirect("stories:project-detail", pk=project.pk)

    versions = project.versions.all()
    return render(
        request,
        "stories/project_detail.html",
        {
            "project": project,
            "guide": guide,
            "latest_version": latest_version,
            "versions": versions,
            "concept_form": concept_form,
            "image_form": image_form,
        },
    )


def download_version_image(request, version_id: int):
    version = get_object_or_404(StoryVersion.objects.select_related("project"), pk=version_id)
    if not version.generated_image:
        raise Http404("Esta versao nao possui imagem gerada.")
    file_handle = default_storage.open(version.generated_image.name, "rb")
    return FileResponse(file_handle, as_attachment=True, filename=version.generated_image.name.rsplit("/", 1)[-1])
