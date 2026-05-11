from django.core.management.base import BaseCommand
from django.db import connection
from django.utils.text import slugify

from stories.models import BulkProjectBatch, StoryConcept, StoryImageVariant


class Command(BaseCommand):
    help = "Repairs legacy tables when migration history is out of sync with current models"

    def handle(self, *args, **options):
        repaired = []

        with connection.cursor() as cursor:
            tables = set(connection.introspection.table_names(cursor))

        # Missing new tables can safely be created through Django because their full models exist now.
        with connection.schema_editor() as schema_editor:
            if "stories_bulkprojectbatch" not in tables:
                schema_editor.create_model(BulkProjectBatch)
                tables.add("stories_bulkprojectbatch")
                repaired.append("created table stories_bulkprojectbatch")
            if "stories_storyconcept" not in tables:
                schema_editor.create_model(StoryConcept)
                tables.add("stories_storyconcept")
                repaired.append("created table stories_storyconcept")
            if "stories_storyimagevariant" not in tables:
                schema_editor.create_model(StoryImageVariant)
                tables.add("stories_storyimagevariant")
                repaired.append("created table stories_storyimagevariant")

        with connection.cursor() as cursor:
            if "news_newssource" in tables:
                repaired.extend(self._repair_news_source(cursor))
            if "news_newsarticle" in tables:
                repaired.extend(self._repair_news_article(cursor))
            if "stories_storyproject" in tables:
                repaired.extend(self._repair_story_project(cursor))
            if "stories_storyconcept" in tables:
                repaired.extend(self._repair_story_concept(cursor))
            if "stories_storyimagevariant" in tables:
                repaired.extend(self._repair_story_image_variant(cursor))

        if repaired:
            self.stdout.write(self.style.WARNING("Legacy schema repaired:"))
            for item in repaired:
                self.stdout.write(f"- {item}")
        else:
            self.stdout.write(self.style.SUCCESS("Legacy schema already aligned."))

    def _columns(self, cursor, table_name: str) -> set[str]:
        return {column.name for column in connection.introspection.get_table_description(cursor, table_name)}

    def _add_column(self, cursor, table_name: str, column_name: str, sql_type: str, repaired: list[str]):
        columns = self._columns(cursor, table_name)
        if column_name in columns:
            return
        cursor.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {sql_type}')
        repaired.append(f"added column {table_name}.{column_name}")

    def _repair_news_source(self, cursor) -> list[str]:
        repaired = []
        table = "news_newssource"
        self._add_column(cursor, table, "slug", "varchar(50)", repaired)
        self._add_column(cursor, table, "website_url", "varchar(200) NOT NULL DEFAULT ''", repaired)
        self._add_column(cursor, table, "rss_url", "varchar(200) NOT NULL DEFAULT ''", repaired)
        self._add_column(cursor, table, "category", "varchar(20) NOT NULL DEFAULT 'hardware'", repaired)
        self._add_column(cursor, table, "is_active", "boolean NOT NULL DEFAULT true", repaired)
        self._add_column(cursor, table, "priority", "smallint NOT NULL DEFAULT 10", repaired)
        self._add_column(cursor, table, "notes", "text NOT NULL DEFAULT ''", repaired)
        self._add_column(cursor, table, "last_ingested_at", "timestamp with time zone NULL", repaired)
        repaired.extend(self._repair_legacy_source_columns(cursor, table))
        repaired.extend(self._backfill_source_slugs(cursor, table))
        return repaired

    def _repair_legacy_source_columns(self, cursor, table_name: str) -> list[str]:
        repaired = []
        columns = self._columns(cursor, table_name)
        if "site_url" in columns:
            cursor.execute(f'UPDATE "{table_name}" SET site_url = COALESCE(site_url, website_url, \'\')')
            cursor.execute(f'ALTER TABLE "{table_name}" ALTER COLUMN site_url SET DEFAULT \'\'')
            repaired.append(f"set default for legacy column {table_name}.site_url")
        return repaired

    def _repair_news_article(self, cursor) -> list[str]:
        repaired = []
        table = "news_newsarticle"
        self._add_column(cursor, table, "slug", "varchar(320)", repaired)
        self._add_column(cursor, table, "content", "text NOT NULL DEFAULT ''", repaired)
        self._add_column(cursor, table, "author", "varchar(200) NOT NULL DEFAULT ''", repaired)
        self._add_column(cursor, table, "category", "varchar(20) NOT NULL DEFAULT ''", repaired)
        self._add_column(cursor, table, "tags", "varchar(300) NOT NULL DEFAULT ''", repaired)
        self._add_column(cursor, table, "published_at", "timestamp with time zone NULL", repaired)
        self._add_column(cursor, table, "relevance_score", "numeric(5,2) NOT NULL DEFAULT 0", repaired)
        self._add_column(cursor, table, "is_featured", "boolean NOT NULL DEFAULT false", repaired)
        repaired.extend(self._backfill_article_slugs(cursor, table))
        return repaired

    def _repair_story_project(self, cursor) -> list[str]:
        repaired = []
        table = "stories_storyproject"
        self._add_column(cursor, table, "brand_mode", "varchar(10) NOT NULL DEFAULT 'blast'", repaired)
        self._add_column(cursor, table, "adjustment_request", "text NOT NULL DEFAULT ''", repaired)
        self._add_column(cursor, table, "requested_image_count", "smallint NOT NULL DEFAULT 2", repaired)
        self._add_column(cursor, table, "error_message", "text NOT NULL DEFAULT ''", repaired)
        self._add_column(cursor, table, "bulk_batch_id", "bigint NULL", repaired)
        return repaired

    def _repair_story_concept(self, cursor) -> list[str]:
        repaired = []
        table = "stories_storyconcept"
        self._add_column(cursor, table, "status", "varchar(20) NOT NULL DEFAULT 'ready'", repaired)
        self._add_column(cursor, table, "instruction_snapshot", "text NOT NULL DEFAULT ''", repaired)
        self._add_column(cursor, table, "headline", "varchar(180) NOT NULL DEFAULT ''", repaired)
        self._add_column(cursor, table, "subheadline", "varchar(220) NOT NULL DEFAULT ''", repaired)
        self._add_column(cursor, table, "body_text", "text NOT NULL DEFAULT ''", repaired)
        self._add_column(cursor, table, "price_text", "varchar(80) NOT NULL DEFAULT ''", repaired)
        self._add_column(cursor, table, "call_to_action", "varchar(140) NOT NULL DEFAULT ''", repaired)
        self._add_column(cursor, table, "visual_direction", "text NOT NULL DEFAULT ''", repaired)
        self._add_column(cursor, table, "prompt_snapshot", "text NOT NULL DEFAULT ''", repaired)
        self._add_column(cursor, table, "provider_response", "text NOT NULL DEFAULT ''", repaired)
        self._add_column(cursor, table, "is_current", "boolean NOT NULL DEFAULT true", repaired)
        self._add_column(cursor, table, "parent_id", "bigint NULL", repaired)
        return repaired

    def _repair_story_image_variant(self, cursor) -> list[str]:
        repaired = []
        table = "stories_storyimagevariant"
        self._add_column(cursor, table, "status", "varchar(20) NOT NULL DEFAULT 'ready'", repaired)
        self._add_column(cursor, table, "image_prompt_snapshot", "text NOT NULL DEFAULT ''", repaired)
        self._add_column(cursor, table, "provider_response", "text NOT NULL DEFAULT ''", repaired)
        self._add_column(cursor, table, "asset", "varchar(100) NOT NULL DEFAULT ''", repaired)
        self._add_column(cursor, table, "asset_mime_type", "varchar(60) NOT NULL DEFAULT ''", repaired)
        self._add_column(cursor, table, "error_message", "text NOT NULL DEFAULT ''", repaired)
        self._add_column(cursor, table, "is_selected", "boolean NOT NULL DEFAULT false", repaired)
        return repaired

    def _backfill_source_slugs(self, cursor, table_name: str) -> list[str]:
        repaired = []
        cursor.execute(f'SELECT id, name, slug FROM "{table_name}"')
        rows = cursor.fetchall()
        used = {slug for _, _, slug in rows if slug}
        for row_id, name, slug in rows:
            if slug:
                continue
            base = slugify(name or f"source-{row_id}") or f"source-{row_id}"
            candidate = base[:50]
            index = 2
            while candidate in used:
                suffix = f"-{index}"
                candidate = f"{base[:50 - len(suffix)]}{suffix}"
                index += 1
            cursor.execute(f'UPDATE "{table_name}" SET slug = %s WHERE id = %s', [candidate, row_id])
            used.add(candidate)
            repaired.append(f"filled {table_name}.slug for id {row_id}")
        return repaired

    def _backfill_article_slugs(self, cursor, table_name: str) -> list[str]:
        repaired = []
        cursor.execute(f'SELECT id, title, slug FROM "{table_name}"')
        rows = cursor.fetchall()
        for row_id, title, slug in rows:
            if slug:
                continue
            candidate = slugify(title or f"article-{row_id}") or f"article-{row_id}"
            cursor.execute(f'UPDATE "{table_name}" SET slug = %s WHERE id = %s', [candidate[:320], row_id])
            repaired.append(f"filled {table_name}.slug for id {row_id}")
        return repaired
