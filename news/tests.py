from unittest.mock import patch

from django.test import TestCase

from .models import NewsArticle, NewsSource
from .services import import_active_sources, import_source_articles


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

    def test_creates_sources_in_bulk_from_panel(self):
        response = self.client.post(
            "/feeds/",
            {
                "action": "save_bulk_sources",
                "bulk-sources_blob": (
                    "The Verge | https://www.theverge.com/rss/index.xml | https://www.theverge.com\n"
                    "https://techcrunch.com/feed/"
                ),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(NewsSource.objects.count(), 2)

    @patch("news.services.feedparser.parse")
    def test_import_active_sources_replaces_old_articles_and_keeps_only_active(self, mock_parse):
        active_source = NewsSource.objects.create(name="Ativa", rss_url="https://example.com/ativa.xml", is_active=True)
        inactive_source = NewsSource.objects.create(name="Inativa", rss_url="https://example.com/inativa.xml", is_active=False)

        NewsArticle.objects.create(source=active_source, title="Artigo antigo ativo", url="https://example.com/old-active")
        NewsArticle.objects.create(source=inactive_source, title="Artigo antigo inativo", url="https://example.com/old-inactive")

        mock_parse.return_value = type(
            "ParsedFeed",
            (),
            {
                "bozo": False,
                "entries": [
                    {
                        "title": "Artigo novo",
                        "link": "https://example.com/new-active",
                        "summary": "Resumo",
                        "id": "active-1",
                        "published": "Tue, 29 Apr 2026 12:00:00 GMT",
                    }
                ],
            },
        )()

        results = import_active_sources(limit=20)

        self.assertEqual(len(results), 1)
        self.assertEqual(NewsArticle.objects.count(), 1)
        article = NewsArticle.objects.get()
        self.assertEqual(article.url, "https://example.com/new-active")
        self.assertEqual(article.source, active_source)
