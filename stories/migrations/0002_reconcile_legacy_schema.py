from django.db import connection, migrations


def _table_exists(table_name: str) -> bool:
    with connection.cursor() as cursor:
        return table_name in connection.introspection.table_names(cursor)


def _column_names(table_name: str) -> set[str]:
    with connection.cursor() as cursor:
        return {column.name for column in connection.introspection.get_table_description(cursor, table_name)}


def reconcile_stories_schema(apps, schema_editor):
    BulkProjectBatch = apps.get_model("stories", "BulkProjectBatch")
    StoryProject = apps.get_model("stories", "StoryProject")
    StoryConcept = apps.get_model("stories", "StoryConcept")
    StoryImageVariant = apps.get_model("stories", "StoryImageVariant")

    if not _table_exists(BulkProjectBatch._meta.db_table):
        schema_editor.create_model(BulkProjectBatch)

    if not _table_exists(StoryProject._meta.db_table):
        schema_editor.create_model(StoryProject)
    else:
        existing_columns = _column_names(StoryProject._meta.db_table)
        for field_name in [
            "brand_mode",
            "adjustment_request",
            "requested_image_count",
            "error_message",
            "bulk_batch",
        ]:
            field = StoryProject._meta.get_field(field_name)
            if field.column not in existing_columns:
                schema_editor.add_field(StoryProject, field)
                existing_columns.add(field.column)

    if not _table_exists(StoryConcept._meta.db_table):
        schema_editor.create_model(StoryConcept)
    else:
        existing_columns = _column_names(StoryConcept._meta.db_table)
        for field_name in [
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
        ]:
            field = StoryConcept._meta.get_field(field_name)
            if field.column not in existing_columns:
                schema_editor.add_field(StoryConcept, field)
                existing_columns.add(field.column)

    if not _table_exists(StoryImageVariant._meta.db_table):
        schema_editor.create_model(StoryImageVariant)
    else:
        existing_columns = _column_names(StoryImageVariant._meta.db_table)
        for field_name in [
            "status",
            "image_prompt_snapshot",
            "provider_response",
            "asset",
            "asset_mime_type",
            "error_message",
            "is_selected",
        ]:
            field = StoryImageVariant._meta.get_field(field_name)
            if field.column not in existing_columns:
                schema_editor.add_field(StoryImageVariant, field)
                existing_columns.add(field.column)


class Migration(migrations.Migration):
    dependencies = [
        ("stories", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(reconcile_stories_schema, migrations.RunPython.noop),
    ]
