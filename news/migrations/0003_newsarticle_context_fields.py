from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("news", "0002_newsarticle_author_newsarticle_guid_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="newsarticle",
            name="context_char_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="newsarticle",
            name="context_error",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="newsarticle",
            name="context_last_checked_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="newsarticle",
            name="context_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pendente"),
                    ("sufficient", "Suficiente"),
                    ("insufficient", "Insuficiente"),
                    ("failed", "Falhou"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="newsarticle",
            name="extracted_content",
            field=models.TextField(blank=True),
        ),
    ]
