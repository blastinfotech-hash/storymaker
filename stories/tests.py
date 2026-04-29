import tempfile
from io import BytesIO

from django.test import TestCase
from django.urls import reverse
from django.test.utils import override_settings
from PIL import Image

from branding.models import BrandGuide

from .models import StoryProject
from .services import _apply_brand_logo


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

    def test_applies_brand_logo_to_generated_image(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            primary_logo_path = f"{temp_dir}/logo-dark.png"
            light_logo_path = f"{temp_dir}/logo-light.png"

            Image.new("RGBA", (500, 100), (60, 10, 120, 255)).save(primary_logo_path)
            Image.new("RGBA", (500, 100), (255, 255, 255, 255)).save(light_logo_path)

            base_image = Image.new("RGB", (1024, 1792), (235, 235, 235))
            buffer = BytesIO()
            base_image.save(buffer, format="PNG")

            with override_settings(
                BLAST_LOGO_PRIMARY_PATH=primary_logo_path,
                BLAST_LOGO_LIGHT_PATH=light_logo_path,
            ):
                output = _apply_brand_logo(buffer.getvalue())

            final_image = Image.open(BytesIO(output))
            self.assertEqual(final_image.size, (1024, 1792))
            footer_pixel = final_image.getpixel((512, 1700))
            self.assertNotEqual(footer_pixel, (235, 235, 235))
