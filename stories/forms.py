from django import forms

from stories.models import BulkProjectBatch, StoryProject


class StoryProjectForm(forms.ModelForm):
    class Meta:
        model = StoryProject
        fields = [
            "title",
            "brand_mode",
            "content_type",
            "target_format",
            "article",
            "topic",
            "custom_brief",
            "promotional_price",
            "call_to_action",
            "adjustment_request",
        ]
        widgets = {
            "custom_brief": forms.Textarea(attrs={"rows": 4}),
            "adjustment_request": forms.Textarea(attrs={"rows": 3}),
        }


class BulkProjectBatchForm(forms.ModelForm):
    class Meta:
        model = BulkProjectBatch
        fields = ["brand_mode", "raw_input"]
        widgets = {
            "raw_input": forms.Textarea(
                attrs={
                    "rows": 10,
                    "placeholder": "NOTEBOOK LENOVO IDEAPAD\nRyzen 7 16GB SSD 512GB\nR$ 3.999\n\nPC GAMER RTX 4060\nRyzen 5 5600 16GB SSD 1TB\nR$ 5.499",
                }
            )
        }
