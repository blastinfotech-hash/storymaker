from django.core.management.base import BaseCommand
from django.db import connection
from django.utils.text import slugify

from news.models import NewsArticle, NewsSource
from stories.models import BulkProjectBatch, StoryConcept, StoryImageVariant, StoryProject


class Command(BaseCommand):
    help = "Repairs legacy tables when migration history is out of sync with the current models"

    def handle(self, *args, **options):
        if not self._should_run_repair():
            self.stdout.write(self.style.SUCCESS("Legacy repair skipped: no legacy migration state detected."))
            return

        repaired = []

        with connection.cursor() as cursor:
            existing_tables = set(connection.introspection.table_names(cursor))

        with connection.schema_editor() as schema_editor:
            repaired.extend(
                self._ensure_model(
                    schema_editor,
                    NewsSource,
                    [
                        "slug",
                        "website_url",
                        "rss_url",
                        "category",
                        "is_active",
                        "priority",
                        "notes",
                        "last_ingested_at",
                    ],
                    existing_tables,
                )
            )
            repaired.extend(
                self._ensure_model(
                    schema_editor,
                    NewsArticle,
                    [
                        "slug",
                        "content",
                        "author",
                        "category",
                        "tags",
                        "published_at",
                        "relevance_score",
                        "is_featured",
                    ],
                    existing_tables,
                )
            )
            repaired.extend(self._ensure_model(schema_editor, BulkProjectBatch, [], existing_tables))
            repaired.extend(
                self._ensure_model(
                    schema_editor,
                    StoryProject,
                    ["brand_mode", "adjustment_request", "requested_image_count", "error_message", "bulk_batch"],
                    existing_tables,
                )
            )
            repaired.extend(
                self._ensure_model(
                    schema_editor,
                    StoryConcept,
                    [
                        "status",
                        "instruction_snapshot",
                        "headline",
                        "subheadline",
                        "body_text",
                        "price_text",
                        "call_to_action",
                        "visual_direction",
                        "prompt_snapshot",
                        "provider_response",
                        "is_current",
                        "parent",
                    ],
                    existing_tables,
                )
            )
            repaired.extend(
                self._ensure_model(
                    schema_editor,
                    StoryImageVariant,
                    ["status", "image_prompt_snapshot", "provider_response", "asset", "asset_mime_type", "error_message", "is_selected"],
                    existing_tables,
                )
            )

        if repaired:
            self.stdout.write(self.style.WARNING("Legacy schema repaired:"))
            for item in repaired:
                self.stdout.write(f"- {item}")
        else:
            self.stdout.write(self.style.SUCCESS("Legacy schema already aligned."))

    def _ensure_model(self, schema_editor, model, field_names, existing_tables):
        repaired = []
        table_name = model._meta.db_table
        if table_name not in existing_tables:
            if not self._should_create_missing_tables():
                return repaired
            schema_editor.create_model(model)
            existing_tables.add(table_name)
            repaired.append(f"created table {table_name}")
            return repaired

        with connection.cursor() as cursor:
            existing_columns = {column.name for column in connection.introspection.get_table_description(cursor, table_name)}

        for field_name in field_names:
            field = model._meta.get_field(field_name)
            if field.column not in existing_columns:
                schema_editor.add_field(model, self._temporary_field(field))
                existing_columns.add(field.column)
                repaired.append(f"added column {table_name}.{field.column}")

        if table_name == NewsSource._meta.db_table and "slug" in existing_columns:
            repaired.extend(self._backfill_source_slugs(table_name))

        if table_name == NewsArticle._meta.db_table and "slug" in existing_columns:
            repaired.extend(self._backfill_article_slugs(table_name))

        return repaired

    def _temporary_field(self, field):
        temp_field = field.clone()
        temp_field.null = True
        temp_field.blank = True
        if hasattr(temp_field, "_unique"):
            temp_field._unique = False
        return temp_field

    def _backfill_source_slugs(self, table_name: str):
        repaired = []
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT id, name, slug FROM "{table_name}"')
            rows = cursor.fetchall()
            used = {slug for _, _, slug in rows if slug}
            for row_id, name, slug in rows:
                if slug:
                    continue
                base = slugify(name or f"source-{row_id}") or f"source-{row_id}"
                candidate = base
                index = 2
                while candidate in used:
                    candidate = f"{base}-{index}"
                    index += 1
                cursor.execute(f'UPDATE "{table_name}" SET slug = %s WHERE id = %s', [candidate, row_id])
                used.add(candidate)
                repaired.append(f"filled {table_name}.slug for id {row_id}")
        return repaired

    def _backfill_article_slugs(self, table_name: str):
        repaired = []
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT id, title, slug FROM "{table_name}"')
            rows = cursor.fetchall()
            for row_id, title, slug in rows:
                if slug:
                    continue
                candidate = slugify(title or f"article-{row_id}") or f"article-{row_id}"
                cursor.execute(f'UPDATE "{table_name}" SET slug = %s WHERE id = %s', [candidate[:320], row_id])
                repaired.append(f"filled {table_name}.slug for id {row_id}")
        return repaired

    def _should_run_repair(self) -> bool:
        with connection.cursor() as cursor:
            tables = set(connection.introspection.table_names(cursor))
            if "django_migrations" not in tables:
                return False
            cursor.execute("SELECT COUNT(*) FROM django_migrations WHERE app IN ('news', 'stories')")
            return cursor.fetchone()[0] > 0

    def _should_create_missing_tables(self) -> bool:
        return True
