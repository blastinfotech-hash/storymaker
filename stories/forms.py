from django import forms

from news.models import NewsArticle

from .models import StoryProject


class StoryProjectForm(forms.ModelForm):
    class Meta:
        model = StoryProject
        fields = ["title", "story_type", "source_article", "user_request"]
        widgets = {
            "user_request": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["source_article"].queryset = NewsArticle.objects.filter(is_curated=True)
        self.fields["source_article"].required = False

    def clean(self):
        cleaned_data = super().clean()
        story_type = cleaned_data.get("story_type")
        source_article = cleaned_data.get("source_article")
        if story_type == StoryProject.StoryType.NEWS and not source_article:
            self.add_error("source_article", "Selecione uma noticia curada para stories do tipo news.")
        return cleaned_data


class ChangeRequestForm(forms.Form):
    change_request = forms.CharField(
        label="Pedido de ajuste",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Ex.: deixar a imagem mais dramatica e reduzir o texto."}),
    )
