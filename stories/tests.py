from io import BytesIO

from django.test import TestCase
from django.urls import reverse
from PIL import Image

from branding.models import BrandGuide
from news.models import NewsArticle, NewsSource

from .models import StoryProject, StoryVersion
from .services import _apply_exact_text_overlay, build_project_context, generate_story_concept


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

    def test_promotional_requires_equipment_configuration(self):
        response = self.client.post(
            reverse("stories:dashboard"),
            {
                "title": "Notebook promocional",
                "story_type": StoryProject.StoryType.PROMOTIONAL,
                "user_request": "Destacar velocidade.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Informe a configuracao do equipamento")

    def test_news_concept_generates_caption_in_fallback(self):
        guide = BrandGuide.get_active()
        source = NewsSource.objects.create(name="Portal Tech", rss_url="https://example.com/rss-news")
        article = NewsArticle.objects.create(
            source=source,
            title="Nova linha de notebooks chega ao Brasil",
            summary="Fabricantes anunciaram desempenho superior e melhor autonomia para trabalho remoto.",
            url="https://example.com/noticia",
            is_curated=True,
        )
        project = StoryProject.objects.create(
            title="Nova linha de notebooks",
            story_type=StoryProject.StoryType.NEWS,
            source_article=article,
            user_request="Usar tom mais premium.",
        )

        concept = generate_story_concept(project=project, guide=guide)

        self.assertIn("caption_text", concept)
        self.assertLessEqual(len(concept["caption_text"]), 1000)
        self.assertGreaterEqual(len(concept["caption_text"]), 180)
        self.assertLessEqual(len(concept["copy_text"].split()), 6)

    def test_applies_exact_text_overlay_without_changing_size(self):
        project = StoryProject.objects.create(
            title="Oferta notebook",
            story_type=StoryProject.StoryType.PROMOTIONAL,
            equipment_configuration="Ryzen 7, 16GB, SSD 1TB, R$ 4.999,00",
        )
        version = StoryVersion.objects.create(
            project=project,
            headline="OFERTA IMPERDIVEL",
            copy_text="Notebook Ryzen 7, 16GB RAM, SSD 1TB. R$ 4.999,00 a vista.",
        )
        image = Image.new("RGB", (1080, 1920), (230, 230, 230))
        buffer = BytesIO()
        image.save(buffer, format="PNG")

        output = _apply_exact_text_overlay(buffer.getvalue(), version)
        final_image = Image.open(BytesIO(output))

        self.assertEqual(final_image.size, (1080, 1920))

    def test_generic_context_ignores_linked_news_article(self):
        source = NewsSource.objects.create(name="Tech", rss_url="https://example.com/rss")
        article = NewsArticle.objects.create(
            source=source,
            title="IA supera medicos em triagem",
            summary="Resumo medico",
            url="https://example.com/news",
        )
        project = StoryProject.objects.create(
            title="Tecnologia na saude",
            story_type=StoryProject.StoryType.GENERIC,
            source_article=article,
            user_request="Visual editorial clean.",
        )

        context = build_project_context(project)

        self.assertNotIn("IA supera medicos", context)
        self.assertNotIn("Resumo medico", context)

    def test_generic_fallback_concept_does_not_use_news_seed(self):
        guide = BrandGuide.get_active()
        source = NewsSource.objects.create(name="Tech", rss_url="https://example.com/rss")
        article = NewsArticle.objects.create(
            source=source,
            title="IA supera medicos em triagem",
            summary="Resumo medico",
            url="https://example.com/news-2",
        )
        project = StoryProject.objects.create(
            title="Tecnologia na saude",
            story_type=StoryProject.StoryType.GENERIC,
            source_article=article,
            user_request="Visual editorial clean.",
        )

        concept = generate_story_concept(project=project, guide=guide)

        self.assertIn("Tecnologia na saude", concept["copy_text"])
        self.assertNotIn("IA supera medicos", concept["copy_text"])
