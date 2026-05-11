from django.db import models
from django.utils.text import slugify
from uuid import uuid4

from core.models import TimeStampedModel
from news.models import NewsArticle


def story_asset_upload_to(instance: "StoryImageVariant", filename: str) -> str:
    slug = instance.concept.project.slug or slugify(instance.concept.project.title) or f"project-{instance.concept.project_id}"
    return f"stories/{slug}/concept-{instance.concept.version_number}/variant-{instance.variant_number}-{filename}"


class BulkProjectBatch(TimeStampedModel):
    class Status(models.TextChoices):
        QUEUED = "queued", "Na fila"
        PARSING = "parsing", "Recortando promoções"
        CREATING = "creating", "Criando projetos"
        GENERATING = "generating", "Gerando artes"
        COMPLETED = "completed", "Concluído"
        FAILED = "failed", "Falhou"

    class BrandMode(models.TextChoices):
        BLAST = "blast", "Blast"
        BETA = "beta", "Beta"

    name = models.CharField(max_length=180)
    brand_mode = models.CharField(max_length=10, choices=BrandMode.choices, default=BrandMode.BLAST)
    raw_input = models.TextField(help_text="Cole as promoções com título, descrição e preço, mesmo com espaços irregulares.")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    total_projects = models.PositiveIntegerField(default=0)
    completed_projects = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name


class StoryProject(TimeStampedModel):
    class ContentType(models.TextChoices):
        NEWS = "news", "Notícia"
        GENERIC = "generic", "Institucional"
        PROMOTIONAL = "promotional", "Promocional"

    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        QUEUED = "queued", "Na fila"
        CONCEPT_GENERATING = "concept_generating", "Gerando conceito"
        CONCEPT_READY = "concept_ready", "Conceito pronto"
        IMAGE_GENERATING = "image_generating", "Gerando imagens"
        READY_FOR_SELECTION = "ready_for_selection", "Pronto para escolher"
        APPROVED = "approved", "Aprovado"
        PUBLISHED = "published", "Publicado"
        FAILED = "failed", "Falhou"

    class Format(models.TextChoices):
        STORY = "story", "Story 1080x1920"
        FEED = "feed", "Feed 1080x1350"
        SQUARE = "square", "Quadrado 1080x1080"

    class BrandMode(models.TextChoices):
        BLAST = "blast", "Blast"
        BETA = "beta", "Beta"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    content_type = models.CharField(max_length=20, choices=ContentType.choices, default=ContentType.NEWS)
    brand_mode = models.CharField(max_length=10, choices=BrandMode.choices, default=BrandMode.BLAST)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    target_format = models.CharField(max_length=20, choices=Format.choices, default=Format.STORY)
    topic = models.CharField(max_length=200, blank=True)
    custom_brief = models.TextField(blank=True)
    promotional_price = models.CharField(max_length=80, blank=True)
    call_to_action = models.CharField(max_length=140, blank=True)
    adjustment_request = models.TextField(blank=True, help_text="Único campo para pedir ajuste de conceito e das próximas imagens.")
    article = models.ForeignKey(NewsArticle, on_delete=models.SET_NULL, blank=True, null=True, related_name="story_projects")
    bulk_batch = models.ForeignKey(BulkProjectBatch, on_delete=models.SET_NULL, blank=True, null=True, related_name="projects")
    requested_image_count = models.PositiveSmallIntegerField(default=2)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if self.brand_mode == self.BrandMode.BETA:
            self.target_format = self.Format.FEED
        self.requested_image_count = 2
        if not self.slug:
            self.slug = f"{slugify(self.title) or 'story-project'}-{uuid4().hex[:8]}"
        super().save(*args, **kwargs)

    @property
    def current_concept(self):
        return self.concepts.filter(is_current=True).order_by("-version_number", "-created_at").first()

    @property
    def latest_ready_variants(self):
        concept = self.current_concept
        if not concept:
            return []
        return list(concept.variants.filter(status=StoryImageVariant.Status.READY).order_by("variant_number"))

    @property
    def is_processing(self) -> bool:
        return self.status in {
            self.Status.QUEUED,
            self.Status.CONCEPT_GENERATING,
            self.Status.IMAGE_GENERATING,
        }


class StoryConcept(TimeStampedModel):
    class GenerationKind(models.TextChoices):
        INITIAL = "initial", "Inicial"
        REVISION = "revision", "Revisão"
        BULK_AUTO = "bulk_auto", "Massa automática"

    class Status(models.TextChoices):
        QUEUED = "queued", "Na fila"
        GENERATING = "generating", "Gerando"
        READY = "ready", "Pronto"
        FAILED = "failed", "Falhou"

    project = models.ForeignKey(StoryProject, on_delete=models.CASCADE, related_name="concepts")
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, blank=True, null=True, related_name="children")
    version_number = models.PositiveIntegerField(default=1)
    generation_kind = models.CharField(max_length=20, choices=GenerationKind.choices, default=GenerationKind.INITIAL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    instruction_snapshot = models.TextField(blank=True)
    headline = models.CharField(max_length=180, blank=True)
    subheadline = models.CharField(max_length=220, blank=True)
    body_text = models.TextField(blank=True)
    price_text = models.CharField(max_length=80, blank=True)
    call_to_action = models.CharField(max_length=140, blank=True)
    visual_direction = models.TextField(blank=True)
    prompt_snapshot = models.TextField(blank=True)
    provider_response = models.TextField(blank=True)
    is_current = models.BooleanField(default=True)

    class Meta:
        ordering = ["-version_number", "-created_at"]
        unique_together = [("project", "version_number")]

    def __str__(self) -> str:
        return f"{self.project.title} concept v{self.version_number}"


class StoryImageVariant(TimeStampedModel):
    class Status(models.TextChoices):
        QUEUED = "queued", "Na fila"
        GENERATING = "generating", "Gerando"
        READY = "ready", "Pronta"
        FAILED = "failed", "Falhou"

    concept = models.ForeignKey(StoryConcept, on_delete=models.CASCADE, related_name="variants")
    variant_number = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    image_prompt_snapshot = models.TextField(blank=True)
    provider_response = models.TextField(blank=True)
    asset = models.FileField(upload_to=story_asset_upload_to, blank=True)
    asset_mime_type = models.CharField(max_length=60, blank=True)
    error_message = models.TextField(blank=True)
    is_selected = models.BooleanField(default=False)

    class Meta:
        ordering = ["variant_number", "-created_at"]
        unique_together = [("concept", "variant_number")]

    def __str__(self) -> str:
        return f"{self.concept.project.title} v{self.concept.version_number}.{self.variant_number}"
