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
            "brand_mode": forms.RadioSelect,
            "content_type": forms.RadioSelect,
            "custom_brief": forms.Textarea(attrs={"rows": 4}),
            "adjustment_request": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "title": "Título do projeto",
            "brand_mode": "Marca visual",
            "content_type": "Tipo de projeto",
            "target_format": "Formato",
            "article": "Artigo de origem",
            "topic": "Tema / produto",
            "custom_brief": "Descrição da arte",
            "promotional_price": "Preço promocional",
            "call_to_action": "Chamada / CTA",
            "adjustment_request": "Pedido de ajuste",
        }
        help_texts = {
            "custom_brief": "Para promocionais, informe aqui o descritivo da arte: produto, benefícios, specs e oferta.",
            "adjustment_request": "Campo único usado para orientar a próxima geração de conceito e imagens.",
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
        labels = {
            "brand_mode": "Marca visual",
            "raw_input": "Artes promocionais em massa",
        }
