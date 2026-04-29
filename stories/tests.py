from django.test import TestCase
from django.urls import reverse

from branding.models import BrandGuide

from .models import StoryProject


class StoryWorkflowTests(TestCase):
    def test_blocks_image_generation_when_openai_is_unavailable(self):
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
        self.assertContains(response, "OPENAI_API_KEY nao esta configurada")
        self.assertEqual(project.status, StoryProject.Status.CONCEPT_READY)
        self.assertEqual(project.versions.count(), 1)

    def test_updates_active_guide_from_dashboard(self):
        guide = BrandGuide.get_active()

        response = self.client.post(
            reverse("stories:dashboard"),
            {
                "action": "update_guide",
                "guide-name": guide.name,
                "guide-visual_identity_prompt": "Usar notebook em close, luz dramatica e fundo escuro.",
                "guide-copy_prompt_template": guide.copy_prompt_template,
                "guide-image_prompt_template": guide.image_prompt_template,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        guide.refresh_from_db()
        self.assertEqual(guide.visual_identity_prompt, "Usar notebook em close, luz dramatica e fundo escuro.")
