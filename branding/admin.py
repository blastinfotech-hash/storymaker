from django.contrib import admin

from .models import BrandGuide


@admin.register(BrandGuide)
class BrandGuideAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "visual_identity_prompt")
