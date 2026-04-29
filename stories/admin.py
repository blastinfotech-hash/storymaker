from django.contrib import admin

from .models import StoryProject, StoryVersion


class StoryVersionInline(admin.TabularInline):
    model = StoryVersion
    extra = 0
    readonly_fields = ("version_number", "created_at")
    ordering = ("-version_number",)


@admin.register(StoryProject)
class StoryProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "story_type", "status", "updated_at")
    list_filter = ("story_type", "status")
    search_fields = ("title", "user_request")
    inlines = [StoryVersionInline]


@admin.register(StoryVersion)
class StoryVersionAdmin(admin.ModelAdmin):
    list_display = ("project", "version_number", "text_model", "image_model", "created_at")
    list_filter = ("text_model", "image_model", "created_at")
    search_fields = ("project__title", "headline", "copy_text", "image_prompt")
