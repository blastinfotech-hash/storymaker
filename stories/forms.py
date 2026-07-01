from django import forms

from stories.models import StoryProject


class StoryProjectForm(forms.ModelForm):
    target_format = forms.ChoiceField(
        label="Tamanho a gerar",
        choices=StoryProject.Format.choices,
        widget=forms.RadioSelect,
        required=True,
        help_text="Selecione o formato principal da arte gerada para este projeto.",
    )

    class Meta:
        model = StoryProject
        fields = [
            "title",
            "brand_mode",
            "content_type",
            "article",
            "target_format",
            "topic",
            "custom_brief",
            "promotional_price",
            "call_to_action",
            "adjustment_request",
        ]
        widgets = {
            "brand_mode": forms.RadioSelect,
            "content_type": forms.RadioSelect,
            "custom_brief": forms.Textarea(attrs={"rows": 4}),
            "adjustment_request": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "title": "Título do projeto",
            "brand_mode": "Marca visual",
            "content_type": "Tipo de projeto",
            "article": "Artigo de origem",
            "topic": "Tema / produto",
            "custom_brief": "Descrição da arte",
            "promotional_price": "Preço promocional",
            "call_to_action": "Chamada / CTA",
            "adjustment_request": "Pedido de ajuste",
        }
        help_texts = {
            "custom_brief": "Para promocionais, informe aqui o descritivo da arte: produto, benefícios, specs e oferta.",
             "adjustment_request": "Campo único usado para orientar a próxima geração de imagem.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Default new projects to the feed format (1080x1350).
        if self.instance.pk:
            self.fields["target_format"].initial = self.instance.target_format
        else:
            self.fields["target_format"].initial = StoryProject.Format.FEED
