from django.conf import settings
from django.db import models


DEFAULT_BRAND_SUMMARY = (
    "BLAST INFO & TECH produz stories com foco em tecnologia, hardware, IA e cultura digital, "
    "sempre com linguagem clara, forte contraste visual e leitura imediata em tela vertical."
)

DEFAULT_VISUAL_RULES = (
    "Priorizar composição vertical 9:16, contraste alto, clima editorial-tech, tipografia marcante, "
    "elemento principal único e legibilidade suficiente para sobreposição de texto de story."
)

DEFAULT_COPY_PROMPT_TEMPLATE = """Voce esta criando um conceito de Instagram Story para {brand_name}.

Guia da marca:
{brand_summary}

Regras visuais:
{visual_rules}

Contexto do projeto:
{project_context}

Pedido atual do editor:
{change_request}

Responda apenas em JSON valido com estas chaves:
- headline
- copy_text
- visual_direction
- image_prompt
- generation_notes

O copy_text deve ser conciso, pronto para um unico story, em portugues do Brasil.
"""

DEFAULT_IMAGE_PROMPT_TEMPLATE = """Crie a arte de um unico story vertical 9:16 para {brand_name}.

Guia da marca:
{brand_summary}

Regras visuais:
{visual_rules}

Direcao visual aprovada:
{visual_direction}

Prompt base da imagem:
{image_prompt}

Pedido atual do editor:
{change_request}

Evite marcas d'agua, mockups de celular, colagens confusas e texto pequeno ilegivel.
"""


class BrandGuide(models.Model):
    name = models.CharField(max_length=120, default=settings.BLAST_BRAND_NAME)
    is_active = models.BooleanField(default=True)
    brand_summary = models.TextField(default=DEFAULT_BRAND_SUMMARY)
    visual_rules = models.TextField(default=DEFAULT_VISUAL_RULES)
    copy_prompt_template = models.TextField(default=DEFAULT_COPY_PROMPT_TEMPLATE)
    image_prompt_template = models.TextField(default=DEFAULT_IMAGE_PROMPT_TEMPLATE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "-updated_at"]
        verbose_name = "Brand guide"
        verbose_name_plural = "Brand guides"

    def __str__(self) -> str:
        suffix = " (active)" if self.is_active else ""
        return f"{self.name}{suffix}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_active:
            type(self).objects.exclude(pk=self.pk).filter(is_active=True).update(is_active=False)

    @classmethod
    def get_active(cls) -> "BrandGuide":
        guide = cls.objects.filter(is_active=True).first()
        if guide:
            return guide
        return cls.objects.create(name=settings.BLAST_BRAND_NAME, is_active=True)
