from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html

from stories.models import StoryConcept, StoryImageVariant, StoryProject
from stories.tasks import generate_project_image


class StoryImageVariantInline(admin.TabularInline):
    model = StoryImageVariant
    extra = 0
    fields = ("variant_number", "status", "is_selected", "asset", "created_at")
    readonly_fields = fields
    can_delete = False


class StoryConceptInline(admin.TabularInline):
    model = StoryConcept
    extra = 0
    fields = ("version_number", "status", "created_at")
    readonly_fields = fields
    can_delete = False
    show_change_link = True


@admin.register(StoryProject)
class StoryProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "brand_mode", "content_type", "status", "updated_at", "workflow_action")
    list_filter = ("brand_mode", "content_type", "status", "target_format")
    search_fields = ("title", "topic", "custom_brief")
    inlines = [StoryConceptInline]
    readonly_fields = ("requested_image_count", "error_message", "created_at", "updated_at", "current_concept_preview")
    fieldsets = (
        (None, {"fields": ("title", "slug", "brand_mode", "content_type", "status", "target_format")}),
        (
            "Inputs",
            {"fields": ("article", "topic", "custom_brief", "promotional_price", "call_to_action", "adjustment_request")},
        ),
        ("Async state", {"fields": ("requested_image_count", "error_message", "current_concept_preview")}),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Queue")
    def workflow_action(self, obj):
        return format_html('<a class="button" href="{}">Queue image</a>', reverse("admin:stories_project_queue", args=[obj.pk]))

    @admin.display(description="Current concept")
    def current_concept_preview(self, obj):
        if not obj:
            return "Save the project first."
        concept = obj.current_concept
        if not concept:
            return "No image run yet."
        variant = concept.variants.order_by("variant_number").first()
        if not variant:
            return "No variant yet."
        return format_html("<strong>{}</strong>", variant.get_status_display())

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("<int:project_id>/queue/", self.admin_site.admin_view(self.queue_view), name="stories_project_queue"),
        ]
        return custom_urls + urls

    def queue_view(self, request, project_id):
        project = self.get_object(request, project_id)
        project.status = StoryProject.Status.QUEUED
        project.save(update_fields=["status", "updated_at"])
        try:
            generate_project_image.delay(project.pk)
        except Exception as exc:  # noqa: BLE001
            project.status = StoryProject.Status.FAILED
            project.error_message = f"Fila assíncrona indisponível: {exc}"
            project.save(update_fields=["status", "error_message", "updated_at"])
            self.message_user(request, project.error_message, level=messages.ERROR)
            return redirect(request.META.get("HTTP_REFERER", reverse("admin:stories_storyproject_changelist")))
        self.message_user(request, "Geração de imagem colocada na fila.", level=messages.SUCCESS)
        return redirect(request.META.get("HTTP_REFERER", reverse("admin:stories_storyproject_changelist")))


@admin.register(StoryConcept)
class StoryConceptAdmin(admin.ModelAdmin):
    list_display = ("project", "version_number", "status", "generation_kind", "created_at")
    list_filter = ("status", "generation_kind", "project__brand_mode")
    search_fields = ("project__title",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [StoryImageVariantInline]


@admin.register(StoryImageVariant)
class StoryImageVariantAdmin(admin.ModelAdmin):
    list_display = ("concept", "variant_number", "status", "is_selected", "created_at")
    list_filter = ("status", "is_selected", "concept__project__brand_mode")
    search_fields = ("concept__project__title", "image_prompt_snapshot")
    readonly_fields = ("created_at", "updated_at")
