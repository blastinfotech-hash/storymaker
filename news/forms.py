from django import forms

from .models import NewsSource


class NewsSourceForm(forms.ModelForm):
    class Meta:
        model = NewsSource
        fields = ["name", "description", "site_url", "rss_url", "is_active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

        labels = {
            "site_url": "Site da fonte",
            "rss_url": "URL do feed RSS",
            "is_active": "Fonte ativa",
        }
