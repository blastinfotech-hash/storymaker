from unittest.mock import patch

from django.test import TestCase

from .models import NewsArticle, NewsSource
from .services import import_source_articles


class NewsImportTests(TestCase):
    @patch("news.services.feedparser.parse")
    def test_imports_articles_from_rss_feed(self, mock_parse):
        source = NewsSource.objects.create(
            name="The Verge",
            rss_url="https://example.com/rss.xml",
        )
        mock_parse.return_value = type(
            "ParsedFeed",
            (),
            {
                "bozo": False,
                "entries": [
                    {
                        "title": "Nova GPU anunciada",
                        "link": "https://example.com/gpu",
                        "summary": "Resumo da noticia.",
                        "author": "Equipe",
                        "id": "gpu-1",
                        "published": "Tue, 29 Apr 2026 12:00:00 GMT",
                    }
                ],
            },
        )()

        result = import_source_articles(source, limit=10)

        self.assertEqual(result.created, 1)
        self.assertEqual(NewsArticle.objects.count(), 1)
        article = NewsArticle.objects.get()
        self.assertEqual(article.title, "Nova GPU anunciada")
        self.assertEqual(article.guid, "gpu-1")

    def test_creates_source_from_panel(self):
        response = self.client.post(
            "/feeds/",
            {
                "action": "save_source",
                "source-name": "TechCrunch",
                "source-description": "Noticias de tecnologia",
                "source-site_url": "https://techcrunch.com",
                "source-rss_url": "https://techcrunch.com/feed/",
                "source-is_active": "on",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(NewsSource.objects.filter(name="TechCrunch").exists())

    def test_toggles_article_curated_from_panel(self):
        source = NewsSource.objects.create(name="Ars Technica", rss_url="https://example.com/rss")
        article = NewsArticle.objects.create(
            source=source,
            title="CPU nova",
            url="https://example.com/cpu",
            is_curated=True,
        )

        response = self.client.post(
            "/noticias/",
            {"action": "toggle_curated", "article_id": article.pk},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        article.refresh_from_db()
        self.assertFalse(article.is_curated)
