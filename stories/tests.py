from django.test import TestCase
from django.urls import reverse

from branding.models import BrandGuide

from .models import StoryProject


class StoryWorkflowTests(TestCase):
    def test_generates_concept_and_image_with_local_fallback(self):
        BrandGuide.get_active()
        project = StoryProject.objects.create(
            title="Chip nacional de IA",
            story_type=StoryProject.StoryType.GENERIC,
            user_request="Enfatizar impacto industrial.",
        )

        response = self.client.post(
            reverse("stories:project-detail", args=[project.pk]),
            {"action": "generate_concept"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        project.refresh_from_db()
        concept_version = project.latest_version
        self.assertEqual(project.status, StoryProject.Status.CONCEPT_READY)
        self.assertTrue(concept_version.has_concept)

        response = self.client.post(
            reverse("stories:project-detail", args=[project.pk]),
            {"action": "generate_image"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        project.refresh_from_db()
        image_version = project.latest_version
        self.assertEqual(project.status, StoryProject.Status.IMAGE_READY)
        self.assertTrue(image_version.has_image)
        self.assertEqual(project.versions.count(), 2)
