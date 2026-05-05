from django import forms

from news.models import NewsArticle

from .models import StoryProject


class StoryProjectForm(forms.ModelForm):
    class Meta:
        model = StoryProject
        fields = [
            "title",
            "story_type",
            "source_article",
            "source_custom_text",
            "equipment_configuration",
            "user_request",
        ]
        labels = {
            "story_type": "Estilo de Postagem",
            "source_article": "Artigo de origem",
            "source_custom_text": "Texto personalizado da base",
            "equipment_configuration": "Configuracao do equipamento",
            "user_request": "Direcionamento adicional",
        }
        widgets = {
            "source_custom_text": forms.Textarea(attrs={"rows": 5}),
            "equipment_configuration": forms.Textarea(attrs={"rows": 5}),
            "user_request": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["source_article"].queryset = NewsArticle.objects.select_related("source").order_by("-published_at", "-created_at")
        self.fields["source_article"].required = False
        self.fields["source_custom_text"].required = False
        self.fields["equipment_configuration"].required = False
        self.fields["user_request"].required = False

    def clean(self):
        cleaned_data = super().clean()
        story_type = cleaned_data.get("story_type")
        source_article = cleaned_data.get("source_article")
        source_custom_text = (cleaned_data.get("source_custom_text") or "").strip()
        equipment_configuration = cleaned_data.get("equipment_configuration")
        if story_type in {StoryProject.StoryType.NEWS, StoryProject.StoryType.INSTITUTIONAL}:
            if not source_article and not source_custom_text:
                self.add_error(
                    "source_article",
                    "Selecione um artigo de origem ou preencha um texto personalizado da base.",
                )
        if story_type == StoryProject.StoryType.PROMOTIONAL and not equipment_configuration:
            self.add_error("equipment_configuration", "Informe a configuração do equipamento para projetos promocionais.")

        if story_type == StoryProject.StoryType.PROMOTIONAL:
            cleaned_data["source_article"] = None
            cleaned_data["source_custom_text"] = ""

        if story_type in {StoryProject.StoryType.NEWS, StoryProject.StoryType.INSTITUTIONAL}:
            cleaned_data["equipment_configuration"] = ""

        cleaned_data["source_custom_text"] = source_custom_text
        return cleaned_data


class ChangeRequestForm(forms.Form):
    change_request = forms.CharField(
        label="Pedido de ajuste",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Ex.: deixar a imagem mais dramatica e reduzir o texto."}),
    )
