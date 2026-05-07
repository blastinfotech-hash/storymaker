from django.core.management.base import BaseCommand
from django.db import connection

from news.models import NewsArticle, NewsSource
from stories.models import BulkProjectBatch, StoryConcept, StoryImageVariant, StoryProject


class Command(BaseCommand):
    help = "Repairs legacy tables when migration history is out of sync with the current models"

    def handle(self, *args, **options):
        repaired = []

        with connection.cursor() as cursor:
            existing_tables = set(connection.introspection.table_names(cursor))

        with connection.schema_editor() as schema_editor:
            repaired.extend(self._ensure_model(schema_editor, NewsSource, [
                "slug",
                "website_url",
                "rss_url",
                "category",
                "is_active",
                "priority",
                "notes",
                "last_ingested_at",
            ], existing_tables))
            repaired.extend(self._ensure_model(schema_editor, NewsArticle, [
                "slug",
                "content",
                "author",
                "category",
                "tags",
                "published_at",
                "relevance_score",
                "is_featured",
            ], existing_tables))
            repaired.extend(self._ensure_model(schema_editor, BulkProjectBatch, [], existing_tables))
            repaired.extend(self._ensure_model(schema_editor, StoryProject, [
                "brand_mode",
                "adjustment_request",
                "requested_image_count",
                "error_message",
                "bulk_batch",
            ], existing_tables))
            repaired.extend(self._ensure_model(schema_editor, StoryConcept, [
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
            ], existing_tables))
            repaired.extend(self._ensure_model(schema_editor, StoryImageVariant, [
                "status",
                "image_prompt_snapshot",
                "provider_response",
                "asset",
                "asset_mime_type",
                "error_message",
                "is_selected",
            ], existing_tables))

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
            schema_editor.create_model(model)
            existing_tables.add(table_name)
            repaired.append(f"created table {table_name}")
            return repaired

        with connection.cursor() as cursor:
            existing_columns = {
                column.name for column in connection.introspection.get_table_description(cursor, table_name)
            }

        for field_name in field_names:
            field = model._meta.get_field(field_name)
            if field.column not in existing_columns:
                schema_editor.add_field(model, field)
                existing_columns.add(field.column)
                repaired.append(f"added column {table_name}.{field.column}")
        return repaired
