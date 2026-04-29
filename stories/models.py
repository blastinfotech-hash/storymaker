from django.db import models


class StoryProject(models.Model):
    class StoryType(models.TextChoices):
        NEWS = "news", "News"
        GENERIC = "generic", "Generic"
        PROMOTIONAL = "promotional", "Promotional"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        CONCEPT_READY = "concept_ready", "Concept ready"
        IMAGE_READY = "image_ready", "Image ready"
        APPROVED = "approved", "Approved"

    title = models.CharField(max_length=180)
    story_type = models.CharField(max_length=20, choices=StoryType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    source_article = models.ForeignKey(
        "news.NewsArticle",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="story_projects",
    )
    user_request = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]

    def __str__(self) -> str:
        return self.title

    @property
    def latest_version(self):
        return self.versions.order_by("-version_number", "-created_at").first()


class StoryVersion(models.Model):
    project = models.ForeignKey(StoryProject, on_delete=models.CASCADE, related_name="versions")
    based_on = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="next_versions",
    )
    version_number = models.PositiveIntegerField(editable=False)
    change_request = models.TextField(blank=True)
    headline = models.CharField(max_length=220, blank=True)
    copy_text = models.TextField(blank=True)
    visual_direction = models.TextField(blank=True)
    image_prompt = models.TextField(blank=True)
    prompt_snapshot = models.TextField(blank=True)
    generation_notes = models.TextField(blank=True)
    text_model = models.CharField(max_length=120, blank=True)
    image_model = models.CharField(max_length=120, blank=True)
    generated_image = models.FileField(upload_to="stories/generated/%Y/%m/%d/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version_number", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "version_number"],
                name="unique_story_version_per_project",
            )
        ]

    def __str__(self) -> str:
        return f"{self.project.title} v{self.version_number}"

    def save(self, *args, **kwargs):
        if not self.version_number:
            last_version = (
                type(self)
                .objects.filter(project=self.project)
                .order_by("-version_number")
                .values_list("version_number", flat=True)
                .first()
            )
            self.version_number = (last_version or 0) + 1
        super().save(*args, **kwargs)

    @property
    def has_concept(self) -> bool:
        return bool(self.copy_text or self.visual_direction or self.image_prompt)

    @property
    def has_image(self) -> bool:
        return bool(self.generated_image)

    @property
    def image_extension(self) -> str:
        if not self.generated_image:
            return ""
        _, _, extension = self.generated_image.name.lower().rpartition(".")
        return extension

    @property
    def is_svg_image(self) -> bool:
        return self.image_extension == "svg"
