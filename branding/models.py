from django.db import models

from core.models import TimeStampedModel


class BrandGuide(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=False)
    brand_name = models.CharField(max_length=120, default="BLAST INFO & TECH")
    visual_identity_manual = models.TextField()
    master_prompt = models.TextField()
    gamer_prompt = models.TextField(blank=True)
    notebook_prompt = models.TextField(blank=True)
    workstation_prompt = models.TextField(blank=True)
    primary_color = models.CharField(max_length=7, default="#6E2BC3")
    accent_color = models.CharField(max_length=7, default="#7A22FF")
    dark_color = models.CharField(max_length=7, default="#120018")
    light_color = models.CharField(max_length=7, default="#FFFFFF")

    class Meta:
        verbose_name = "Brand guide"
        verbose_name_plural = "Brand guides"
        ordering = ["-is_active", "name"]

    def __str__(self) -> str:
        return self.name
