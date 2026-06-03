from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stories", "0005_alter_storyconcept_price_text_and_more"),
    ]

    operations = [
        migrations.AlterField,
        migrations.AlterField(
            model_name="storyimagevariant",
            name="asset",
            field=models.FileField(blank=True, max_length=500, upload_to="stories.models.story_asset_upload_to"),
        ),
        migrations.AlterField(
            model_name="storyproject",
            name="requested_image_count",
            field=models.PositiveSmallIntegerField(default=1),
        ),
    ]
