from django.db import migrations, models


def migrate_generic_to_institutional(apps, schema_editor):
    StoryProject = apps.get_model("stories", "StoryProject")
    StoryProject.objects.filter(story_type="generic").update(story_type="institutional")


def migrate_institutional_to_generic(apps, schema_editor):
    StoryProject = apps.get_model("stories", "StoryProject")
    StoryProject.objects.filter(story_type="institutional").update(story_type="generic")


class Migration(migrations.Migration):

    dependencies = [
        ("stories", "0002_storyproject_equipment_configuration_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="storyproject",
            name="source_custom_text",
            field=models.TextField(blank=True),
        ),
        migrations.RunPython(migrate_generic_to_institutional, migrate_institutional_to_generic),
        migrations.AlterField(
            model_name="storyproject",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Rascunho"),
                    ("concept_ready", "Conceito pronto"),
                    ("image_ready", "Imagem pronta"),
                    ("approved", "Aprovado"),
                ],
                default="draft",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="storyproject",
            name="story_type",
            field=models.CharField(
                choices=[
                    ("news", "Notícia"),
                    ("promotional", "Promocional"),
                    ("institutional", "Institucional"),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="storyproject",
            name="title",
            field=models.CharField(max_length=180, verbose_name="Titulo"),
        ),
    ]
