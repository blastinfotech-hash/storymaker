from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from stories.services.generation import split_bulk_promotions
from stories.models import StoryProject


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


class ProjectWorkflowViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="tester", password="secret123", is_staff=True)
        self.client.login(username="tester", password="secret123")

    @patch("stories.views.queue_project_generation.delay")
    def test_generate_concept_works_without_resubmitting_full_form(self, mocked_delay):
        project = StoryProject.objects.create(
            title="Projeto teste",
            brand_mode=StoryProject.BrandMode.BETA,
            content_type=StoryProject.ContentType.PROMOTIONAL,
            topic="PC TESTE",
            custom_brief="PC TESTE\nR$ 1000",
            promotional_price="R$ 1000",
        )

        response = self.client.post(reverse("project_detail", args=[project.slug]), {"action": "generate_concept"})

        self.assertEqual(response.status_code, 302)
        project.refresh_from_db()
        self.assertEqual(project.status, StoryProject.Status.QUEUED)
        mocked_delay.assert_called_once_with(project.pk, False)

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
