from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.urls import reverse

from stories.forms import StoryProjectForm
from stories.services.generation import split_bulk_promotions
from stories.models import StoryConcept, StoryImageVariant, StoryProject
from stories.tasks import generate_project_image


class BulkPromotionSplitTests(TestCase):
    def test_keeps_single_promotion_with_two_price_lines_as_one_block(self):
        raw_input = """
PC Gamer AMD Ryzen 5 8600G, 16GB, SSD 512GB
Amd Ryzen 5 8600g,
Memória 16gb 5600mhz Ddr5,
Ssd Nvme 512gb,
Fonte 500w,
Placa A620,
Gabinete Antec Cx200
(imagens meramente ilustrativas*)
À vista R$ 4556,07
ou R$ 4899,00 parcelado em 10x de R$ 489,90 sem juros
""".strip()

        promotions = split_bulk_promotions(raw_input)

        self.assertEqual(len(promotions), 1)
        self.assertEqual(promotions[0]["title"], "PC Gamer AMD Ryzen 5 8600G, 16GB, SSD 512GB")
        self.assertIn("Gabinete Antec Cx200", promotions[0]["description"])
        self.assertIn("À vista R$ 4556,07", promotions[0]["price"])
        self.assertIn("10x de R$ 489,90", promotions[0]["price"])

    def test_keeps_single_promotion_with_price_without_currency_symbol_as_one_block(self):
        raw_input = """
Peças para essa Promo
12400F
Msi H610
1 pente 16GB
512
600w
RX 7600 dual fan
Gabinete GC10 3 fans
4.999 a vista ou
10x de 559,90 sem juros
""".strip()

        promotions = split_bulk_promotions(raw_input)

        self.assertEqual(len(promotions), 1)
        self.assertEqual(promotions[0]["title"], "Peças para essa Promo")
        self.assertIn("RX 7600 dual fan", promotions[0]["description"])
        self.assertIn("4.999 a vista ou", promotions[0]["price"])
        self.assertIn("10x de 559,90 sem juros", promotions[0]["price"])

    def test_long_price_text_fits_project_and_concept_fields(self):
        raw_input = """
PC Gamer AMD Ryzen 5 8600G, 16GB, SSD 512GB
Amd Ryzen 5 8600g,
Memória 16gb 5600mhz Ddr5,
Ssd Nvme 512gb,
Fonte 500w,
Placa A620,
Gabinete Antec Cx200
À vista R$ 4556,07
ou R$ 4899,00 parcelado em 10x de R$ 489,90 sem juros
""".strip()

        promotions = split_bulk_promotions(raw_input)
        project = StoryProject.objects.create(
            title=promotions[0]["title"],
            brand_mode=StoryProject.BrandMode.BETA,
            content_type=StoryProject.ContentType.PROMOTIONAL,
            topic=promotions[0]["title"],
            custom_brief=promotions[0]["description"],
            promotional_price=promotions[0]["price"],
        )
        concept = StoryConcept.objects.create(
            project=project,
            version_number=1,
            status=StoryConcept.Status.READY,
            is_current=True,
            price_text=promotions[0]["price"],
        )

        self.assertIn("489,90", project.promotional_price)
        self.assertIn("489,90", concept.price_text)


class ProjectWorkflowViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="tester", password="secret123", is_staff=True)
        self.client.login(username="tester", password="secret123")

    @patch("stories.views.generate_project_image.delay")
    def test_generate_image_works_without_resubmitting_full_form(self, mocked_delay):
        project = StoryProject.objects.create(
            title="Projeto teste",
            brand_mode=StoryProject.BrandMode.BETA,
            content_type=StoryProject.ContentType.PROMOTIONAL,
            topic="PC TESTE",
            custom_brief="PC TESTE\nR$ 1000",
            promotional_price="R$ 1000",
        )

        response = self.client.post(
            reverse("project_detail", args=[project.slug]),
            {
                "action": "generate_image",
                "title": project.title,
                "brand_mode": project.brand_mode,
                "content_type": project.content_type,
                "target_format": StoryProject.Format.FEED,
                "article": "",
                "topic": project.topic,
                "custom_brief": project.custom_brief,
                "promotional_price": project.promotional_price,
                "call_to_action": project.call_to_action,
                "adjustment_request": project.adjustment_request,
            },
        )

        self.assertEqual(response.status_code, 302)
        project.refresh_from_db()
        self.assertEqual(project.status, StoryProject.Status.QUEUED)
        self.assertEqual(project.selected_target_formats, [StoryProject.Format.FEED])
        mocked_delay.assert_called_once_with(project.pk)

    def test_home_can_delete_project(self):
        project = StoryProject.objects.create(
            title="Excluir teste",
            brand_mode=StoryProject.BrandMode.BETA,
            content_type=StoryProject.ContentType.PROMOTIONAL,
            topic="PC TESTE",
        )

        response = self.client.post(reverse("home"), {"action": "delete_project", "project_id": project.pk})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(StoryProject.objects.filter(pk=project.pk).exists())


class ProjectFormatSelectionTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="format-tester", password="secret123", is_staff=True)
        self.client.login(username="format-tester", password="secret123")

    def test_beta_project_keeps_manually_selected_formats(self):
        form = StoryProjectForm(
            data={
                "title": "Formatos beta",
                "brand_mode": StoryProject.BrandMode.BETA,
                "content_type": StoryProject.ContentType.PROMOTIONAL,
                "target_format": StoryProject.Format.FEED,
                "topic": "PC TESTE",
                "custom_brief": "PC TESTE",
                "promotional_price": "R$ 1000",
                "call_to_action": "Fale",
                "adjustment_request": "",
                "article": "",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        project = form.save()

        self.assertEqual(project.selected_target_formats, [StoryProject.Format.FEED])
        self.assertEqual(project.target_format, StoryProject.Format.FEED)

    @patch("stories.tasks.generate_story_image")
    def test_generate_project_image_creates_concept_shell_and_single_variant(self, mocked_generate):
        mocked_generate.side_effect = lambda project, target_format: StoryImageVariant.objects.create(
            concept=StoryConcept.objects.create(
                project=project,
                version_number=1,
                status=StoryConcept.Status.READY,
                is_current=True,
            ),
            target_format=target_format,
            variant_number=1,
            status=StoryImageVariant.Status.READY,
        )
        project = StoryProject.objects.create(
            title="Multiformato",
            brand_mode=StoryProject.BrandMode.BETA,
            content_type=StoryProject.ContentType.PROMOTIONAL,
            target_format=StoryProject.Format.FEED,
            topic="PC TESTE",
            custom_brief="PC TESTE",
            promotional_price="R$ 1000",
        )

        generate_project_image(project.pk)

        concept = project.current_concept
        self.assertIsNotNone(concept)
        created_pairs = set(StoryImageVariant.objects.filter(concept=concept).values_list("target_format", "variant_number"))
        self.assertEqual(
            created_pairs,
            {
                (StoryProject.Format.FEED, 1),
            },
        )

    def test_project_delete_does_not_crash_with_legacy_storyversion_table(self):
        project = StoryProject.objects.create(
            title="Excluir legado",
            brand_mode=StoryProject.BrandMode.BETA,
            content_type=StoryProject.ContentType.PROMOTIONAL,
            topic="PC TESTE",
        )

        with connection.cursor() as cursor:
            cursor.execute(
                'CREATE TABLE IF NOT EXISTS "stories_storyversion" (id integer primary key autoincrement, project_id bigint, generated_image varchar(255) DEFAULT \'\')'
            )
            cursor.execute('INSERT INTO "stories_storyversion" (project_id, generated_image) VALUES (%s, %s)', [project.pk, ""])

        response = self.client.post(reverse("project_detail", args=[project.slug]), {"action": "delete_project"})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(StoryProject.objects.filter(pk=project.pk).exists())
