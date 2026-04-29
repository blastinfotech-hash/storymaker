from django.conf import settings
from django.db import models


DEFAULT_VISUAL_IDENTITY_PROMPT = (
    "BLAST INFO & TECH produz stories verticais 9:16 sobre tecnologia, hardware, IA e cultura digital. "
    "A imagem deve ter energia editorial-tech, contraste alto, leitura imediata, clima premium, "
    "tipografia forte quando houver texto sobreposto, composicao limpa com um elemento principal, "
    "iluminacao dramatica, sem mockup de celular, sem marca d'agua, sem colagem confusa e sem excesso de elementos."
)

DEFAULT_COPY_PROMPT_TEMPLATE = """Voce esta criando um conceito de Instagram Story para {brand_name}.

Guia visual da marca:
{visual_identity_prompt}

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

Guia visual da marca:
{visual_identity_prompt}

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
    visual_identity_prompt = models.TextField(default=DEFAULT_VISUAL_IDENTITY_PROMPT)
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
