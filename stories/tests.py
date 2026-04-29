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
        self.assertTrue(image_version.generated_image.name.endswith(".svg"))

        with image_version.generated_image.open("r") as image_file:
            svg_content = image_file.read()

        self.assertIn("<svg", svg_content)
        self.assertNotIn("foreignObject", svg_content)
        self.assertIn("OPENAI_API_KEY", image_version.generation_notes)

        preview_response = self.client.get(reverse("stories:version-preview", args=[image_version.pk]))
        self.assertEqual(preview_response.status_code, 200)
        self.assertEqual(preview_response.headers["Content-Type"], "image/svg+xml")

    def test_updates_active_guide_from_dashboard(self):
        guide = BrandGuide.get_active()

        response = self.client.post(
            reverse("stories:dashboard"),
            {
                "action": "update_guide",
                "guide-name": guide.name,
                "guide-brand_summary": "Novo resumo da marca.",
                "guide-visual_rules": "Usar notebook em close, luz dramatica e fundo escuro.",
                "guide-copy_prompt_template": guide.copy_prompt_template,
                "guide-image_prompt_template": guide.image_prompt_template,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        guide.refresh_from_db()
        self.assertEqual(guide.brand_summary, "Novo resumo da marca.")
