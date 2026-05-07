from celery import shared_task
from django.db import transaction

from stories.models import BulkProjectBatch, StoryConcept, StoryImageVariant, StoryProject
from stories.services.generation import generate_story_concept, generate_story_image_variant, split_bulk_promotions


@shared_task
def queue_project_generation(project_id: int) -> None:
    project = StoryProject.objects.get(pk=project_id)
    try:
        project.status = StoryProject.Status.CONCEPT_GENERATING
        project.error_message = ""
        project.save(update_fields=["status", "error_message", "updated_at"])

        concept = generate_story_concept(project)
        project.status = StoryProject.Status.IMAGE_GENERATING
        project.save(update_fields=["status", "updated_at"])

        for variant_number in range(1, project.requested_image_count + 1):
            StoryImageVariant.objects.update_or_create(
                concept=concept,
                variant_number=variant_number,
                defaults={"status": StoryImageVariant.Status.QUEUED, "image_prompt_snapshot": ""},
            )
            generate_image_variant.delay(concept.pk, variant_number)
    except Exception as exc:  # noqa: BLE001
        project.status = StoryProject.Status.FAILED
        project.error_message = str(exc)
        project.save(update_fields=["status", "error_message", "updated_at"])


@shared_task
def generate_image_variant(concept_id: int, variant_number: int) -> None:
    concept = StoryConcept.objects.select_related("project").get(pk=concept_id)
    variant, _ = StoryImageVariant.objects.get_or_create(concept=concept, variant_number=variant_number)
    try:
        variant.status = StoryImageVariant.Status.GENERATING
        variant.error_message = ""
        variant.save(update_fields=["status", "error_message", "updated_at"])
        generate_story_image_variant(concept, variant_number)
    except Exception as exc:  # noqa: BLE001
        variant.status = StoryImageVariant.Status.FAILED
        variant.error_message = str(exc)
        variant.save(update_fields=["status", "error_message", "updated_at"])
        concept.project.status = StoryProject.Status.FAILED
        concept.project.error_message = str(exc)
        concept.project.save(update_fields=["status", "error_message", "updated_at"])
    if concept.project.bulk_batch_id:
        refresh_bulk_batch_status.delay(concept.project.bulk_batch_id)


@shared_task
def queue_bulk_batch(batch_id: int) -> None:
    batch = BulkProjectBatch.objects.get(pk=batch_id)
    try:
        batch.status = BulkProjectBatch.Status.PARSING
        batch.error_message = ""
        batch.save(update_fields=["status", "error_message", "updated_at"])

        promotions = split_bulk_promotions(batch.raw_input)
        if not promotions:
            batch.status = BulkProjectBatch.Status.FAILED
            batch.error_message = "No promotions could be parsed from the provided text."
            batch.save(update_fields=["status", "error_message", "updated_at"])
            return

        batch.status = BulkProjectBatch.Status.CREATING
        batch.total_projects = len(promotions)
        batch.completed_projects = 0
        batch.save(update_fields=["status", "total_projects", "completed_projects", "updated_at"])

        with transaction.atomic():
            for promo in promotions:
                project = StoryProject.objects.create(
                    title=promo["title"],
                    content_type=StoryProject.ContentType.PROMOTIONAL,
                    brand_mode=batch.brand_mode,
                    target_format=StoryProject.Format.FEED,
                    topic=promo["title"],
                    custom_brief=promo["description"],
                    promotional_price=promo["price"],
                    bulk_batch=batch,
                    status=StoryProject.Status.QUEUED,
                )
                queue_project_generation.delay(project.pk)

        batch.status = BulkProjectBatch.Status.GENERATING
        batch.save(update_fields=["status", "updated_at"])
    except Exception as exc:  # noqa: BLE001
        batch.status = BulkProjectBatch.Status.FAILED
        batch.error_message = str(exc)
        batch.save(update_fields=["status", "error_message", "updated_at"])


@shared_task
def refresh_bulk_batch_status(batch_id: int) -> None:
    batch = BulkProjectBatch.objects.get(pk=batch_id)
    total = batch.projects.count()
    completed = batch.projects.filter(status=StoryProject.Status.READY_FOR_SELECTION).count()
    failed = batch.projects.filter(status=StoryProject.Status.FAILED).count()
    batch.total_projects = total
    batch.completed_projects = completed
    if total and completed + failed >= total:
        batch.status = BulkProjectBatch.Status.COMPLETED if failed == 0 else BulkProjectBatch.Status.FAILED
    batch.save(update_fields=["total_projects", "completed_projects", "status", "updated_at"])
