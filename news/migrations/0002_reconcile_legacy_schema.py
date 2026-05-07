from django.db import connection, migrations


def _table_exists(table_name: str) -> bool:
    with connection.cursor() as cursor:
        return table_name in connection.introspection.table_names(cursor)


def _column_names(table_name: str) -> set[str]:
    with connection.cursor() as cursor:
        return {column.name for column in connection.introspection.get_table_description(cursor, table_name)}


def reconcile_news_schema(apps, schema_editor):
    NewsSource = apps.get_model("news", "NewsSource")
    NewsArticle = apps.get_model("news", "NewsArticle")

    if not _table_exists(NewsSource._meta.db_table):
        schema_editor.create_model(NewsSource)
    else:
        existing_columns = _column_names(NewsSource._meta.db_table)
        for field_name in [
            "slug",
            "website_url",
            "rss_url",
            "category",
            "is_active",
            "priority",
            "notes",
            "last_ingested_at",
        ]:
            field = NewsSource._meta.get_field(field_name)
            if field.column not in existing_columns:
                schema_editor.add_field(NewsSource, field)
                existing_columns.add(field.column)

    if not _table_exists(NewsArticle._meta.db_table):
        schema_editor.create_model(NewsArticle)
    else:
        existing_columns = _column_names(NewsArticle._meta.db_table)
        for field_name in [
            "slug",
            "content",
            "author",
            "category",
            "tags",
            "published_at",
            "relevance_score",
            "is_featured",
        ]:
            field = NewsArticle._meta.get_field(field_name)
            if field.column not in existing_columns:
                schema_editor.add_field(NewsArticle, field)
                existing_columns.add(field.column)


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(reconcile_news_schema, migrations.RunPython.noop),
    ]
