from io import BytesIO

from django.test import TestCase
from django.urls import reverse
from PIL import Image

from branding.models import BrandGuide
from news.models import NewsArticle, NewsSource

from .models import StoryProject, StoryVersion
from .services import ConceptGenerationError, _apply_exact_text_overlay, build_project_context, generate_story_concept


class StoryWorkflowTests(TestCase):
    def test_blocks_image_generation_when_openai_is_unavailable(self):
        BrandGuide.get_active()
        project = StoryProject.objects.create(
            title="Chip nacional de IA",
            story_type=StoryProject.StoryType.INSTITUTIONAL,
            source_custom_text="Panorama sobre impacto industrial de IA no Brasil.",
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

    def test_dashboard_creates_editorial_project_with_custom_text(self):
        response = self.client.post(
            reverse("stories:dashboard"),
            {
                "title": "Post institucional",
                "story_type": StoryProject.StoryType.INSTITUTIONAL,
                "source_custom_text": "Texto base institucional sobre produtividade.",
                "user_request": "Tom direto e confiavel.",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        project = StoryProject.objects.get(title="Post institucional")
        self.assertEqual(project.story_type, StoryProject.StoryType.INSTITUTIONAL)

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
        self.assertContains(response, "Informe a configuração do equipamento")

    def test_news_requires_source_article(self):
        response = self.client.post(
            reverse("stories:dashboard"),
            {
                "title": "Post de noticia",
                "story_type": StoryProject.StoryType.NEWS,
                "user_request": "Tom objetivo.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Selecione um artigo de origem para posts de notícia")

    def test_institutional_requires_article_or_custom_text(self):
        response = self.client.post(
            reverse("stories:dashboard"),
            {
                "title": "Post institucional",
                "story_type": StoryProject.StoryType.INSTITUTIONAL,
                "user_request": "Tom objetivo.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Selecione um artigo de origem ou preencha um texto personalizado da base")

    def test_news_concept_generates_caption_in_fallback(self):
        guide = BrandGuide.get_active()
        source = NewsSource.objects.create(name="Portal Tech", rss_url="https://example.com/rss-news")
        article = NewsArticle.objects.create(
            source=source,
            title="Nova linha de notebooks chega ao Brasil",
            summary="Fabricantes anunciaram desempenho superior e melhor autonomia para trabalho remoto.",
            extracted_content="a" * 2100,
            context_char_count=2100,
            context_status=NewsArticle.ContextStatus.SUFFICIENT,
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
        self.assertLessEqual(len(concept["copy_text"].split()), 5)
        self.assertLessEqual(len(concept["headline"].split()), 5)

    def test_news_concept_blocks_when_context_is_insufficient(self):
        guide = BrandGuide.get_active()
        source = NewsSource.objects.create(name="Portal", rss_url="https://example.com/rss-news")
        article = NewsArticle.objects.create(
            source=source,
            title="Atualizacao curta",
            summary="Resumo curto",
            context_char_count=420,
            context_status=NewsArticle.ContextStatus.INSUFFICIENT,
            url="https://example.com/noticia-curta",
            is_curated=True,
        )
        project = StoryProject.objects.create(
            title="Atualizacao",
            story_type=StoryProject.StoryType.NEWS,
            source_article=article,
        )

        with self.assertRaises(ConceptGenerationError):
            generate_story_concept(project=project, guide=guide)

    def test_project_detail_shows_error_when_news_context_is_insufficient(self):
        source = NewsSource.objects.create(name="Portal", rss_url="https://example.com/rss-news")
        article = NewsArticle.objects.create(
            source=source,
            title="Atualizacao curta",
            summary="Resumo curto",
            context_char_count=420,
            context_status=NewsArticle.ContextStatus.INSUFFICIENT,
            url="https://example.com/noticia-curta-2",
            is_curated=True,
        )
        project = StoryProject.objects.create(
            title="Atualizacao",
            story_type=StoryProject.StoryType.NEWS,
            source_article=article,
        )

        response = self.client.post(
            reverse("stories:project-detail", args=[project.pk]),
            {"action": "generate_concept"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Contexto insuficiente para noticia de qualidade")

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

    def test_institutional_context_uses_linked_article(self):
        source = NewsSource.objects.create(name="Tech", rss_url="https://example.com/rss")
        article = NewsArticle.objects.create(
            source=source,
            title="IA supera medicos em triagem",
            summary="Resumo medico",
            url="https://example.com/news",
        )
        project = StoryProject.objects.create(
            title="Tecnologia na saude",
            story_type=StoryProject.StoryType.INSTITUTIONAL,
            source_article=article,
            user_request="Visual editorial clean.",
        )

        context = build_project_context(project)

        self.assertIn("IA supera medicos", context)
        self.assertIn("Resumo medico", context)

    def test_promotional_fallback_concept_uses_equipment_seed(self):
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
            story_type=StoryProject.StoryType.PROMOTIONAL,
            equipment_configuration="Ryzen 7, 16GB, SSD 1TB",
            source_article=article,
            user_request="Visual editorial clean.",
        )

        concept = generate_story_concept(project=project, guide=guide)

        self.assertIn("Ryzen 7", concept["copy_text"])
        self.assertNotIn("IA supera medicos", concept["copy_text"])
