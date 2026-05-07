from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html

from stories.models import BulkProjectBatch, StoryConcept, StoryImageVariant, StoryProject
from stories.tasks import queue_bulk_batch, queue_project_generation


class StoryImageVariantInline(admin.TabularInline):
    model = StoryImageVariant
    extra = 0
    fields = ("variant_number", "status", "is_selected", "asset", "created_at")
    readonly_fields = fields
    can_delete = False


class StoryConceptInline(admin.TabularInline):
    model = StoryConcept
    extra = 0
    fields = ("version_number", "status", "headline", "price_text", "created_at")
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
        return format_html('<a class="button" href="{}">Queue generation</a>', reverse("admin:stories_project_queue", args=[obj.pk]))

    @admin.display(description="Current concept")
    def current_concept_preview(self, obj):
        if not obj:
            return "Save the project first."
        concept = obj.current_concept
        if not concept:
            return "No concept yet."
        return format_html("<strong>{}</strong><br>{}<br>{}", concept.headline, concept.price_text, concept.visual_direction)

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
        queue_project_generation.delay(project.pk)
        self.message_user(request, "Projeto colocado na fila.", level=messages.SUCCESS)
        return redirect(request.META.get("HTTP_REFERER", reverse("admin:stories_storyproject_changelist")))


@admin.register(StoryConcept)
class StoryConceptAdmin(admin.ModelAdmin):
    list_display = ("project", "version_number", "status", "generation_kind", "created_at")
    list_filter = ("status", "generation_kind", "project__brand_mode")
    search_fields = ("project__title", "headline", "body_text", "visual_direction")
    readonly_fields = ("created_at", "updated_at")
    inlines = [StoryImageVariantInline]


@admin.register(StoryImageVariant)
class StoryImageVariantAdmin(admin.ModelAdmin):
    list_display = ("concept", "variant_number", "status", "is_selected", "created_at")
    list_filter = ("status", "is_selected", "concept__project__brand_mode")
    search_fields = ("concept__project__title", "image_prompt_snapshot")
    readonly_fields = ("created_at", "updated_at")


@admin.register(BulkProjectBatch)
class BulkProjectBatchAdmin(admin.ModelAdmin):
    list_display = ("name", "brand_mode", "status", "completed_projects", "total_projects", "queue_action")
    list_filter = ("brand_mode", "status")
    search_fields = ("name", "raw_input")
    readonly_fields = ("total_projects", "completed_projects", "error_message", "created_at", "updated_at")

    @admin.display(description="Queue")
    def queue_action(self, obj):
        return format_html('<a class="button" href="{}">Queue batch</a>', reverse("admin:stories_batch_queue", args=[obj.pk]))

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("<int:batch_id>/queue/", self.admin_site.admin_view(self.queue_view), name="stories_batch_queue"),
        ]
        return custom_urls + urls

    def queue_view(self, request, batch_id):
        batch = self.get_object(request, batch_id)
        batch.status = BulkProjectBatch.Status.QUEUED
        batch.save(update_fields=["status", "updated_at"])
        queue_bulk_batch.delay(batch.pk)
        self.message_user(request, "Lote colocado na fila.", level=messages.SUCCESS)
        return redirect(request.META.get("HTTP_REFERER", reverse("admin:stories_bulkprojectbatch_changelist")))
