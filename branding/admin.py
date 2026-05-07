from django.contrib import admin

from branding.models import BrandGuide


@admin.register(BrandGuide)
class BrandGuideAdmin(admin.ModelAdmin):
    list_display = ("name", "brand_name", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "brand_name", "visual_identity_manual")
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        (None, {"fields": ("name", "slug", "is_active", "brand_name")}),
        (
            "Prompt system",
            {"fields": ("master_prompt", "gamer_prompt", "notebook_prompt", "workstation_prompt")},
        ),
        (
            "Visual identity",
            {
                "fields": (
                    "visual_identity_manual",
                    "primary_color",
                    "accent_color",
                    "dark_color",
                    "light_color",
                )
            },
        ),
    )
