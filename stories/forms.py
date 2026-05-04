from django import forms

from branding.models import BrandGuide
from news.models import NewsArticle

from .models import StoryProject


class StoryProjectForm(forms.ModelForm):
    class Meta:
        model = StoryProject
        fields = ["title", "story_type", "source_article", "equipment_configuration", "user_request"]
        widgets = {
            "equipment_configuration": forms.Textarea(attrs={"rows": 5}),
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
        equipment_configuration = cleaned_data.get("equipment_configuration")
        if story_type == StoryProject.StoryType.NEWS and not source_article:
            self.add_error("source_article", "Selecione uma noticia curada para stories do tipo news.")
        if story_type == StoryProject.StoryType.PROMOTIONAL and not equipment_configuration:
            self.add_error("equipment_configuration", "Informe a configuracao do equipamento para projetos promocionais.")
        if story_type != StoryProject.StoryType.NEWS:
            cleaned_data["source_article"] = None
        if story_type != StoryProject.StoryType.PROMOTIONAL:
            cleaned_data["equipment_configuration"] = ""
        return cleaned_data


class ChangeRequestForm(forms.Form):
    change_request = forms.CharField(
        label="Pedido de ajuste",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Ex.: deixar a imagem mais dramatica e reduzir o texto."}),
    )


class ActiveBrandGuideForm(forms.ModelForm):
    class Meta:
        model = BrandGuide
        fields = ["name", "visual_identity_prompt", "copy_prompt_template", "image_prompt_template"]
        labels = {
            "visual_identity_prompt": "Prompt de identidade visual",
            "copy_prompt_template": "Template do conceito",
            "image_prompt_template": "Template da imagem",
        }
        widgets = {
            "visual_identity_prompt": forms.Textarea(attrs={"rows": 8}),
            "copy_prompt_template": forms.Textarea(attrs={"rows": 10}),
            "image_prompt_template": forms.Textarea(attrs={"rows": 10}),
        }
