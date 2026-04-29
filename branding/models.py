from django.conf import settings
from django.db import models


DEFAULT_VISUAL_IDENTITY_PROMPT = """Manual Oficial de Identidade Visual para Geracao de Imagens IA — BLAST INFO & TECH

1. Visao Estrategica da Marca

A identidade visual da BLAST INFO & TECH deve comunicar imediatamente:

- Autoridade em tecnologia
- Oferta confiavel
- Preco competitivo
- Modernidade
- Clareza comercial
- Performance
- Compra inteligente
- Loja solida e profissional
- Tecnologia acessivel e premium ao mesmo tempo

Toda peca precisa parecer criada por uma empresa seria, dominante no segmento local e altamente especializada.

2. Posicionamento Visual Obrigatorio

A BLAST nao deve parecer:

- Loja amadora
- Banner poluido
- Design improvisado
- Arte generica de marketplace
- Criativo barato
- Visual gamer infantilizado, exceto campanhas gamer especificas

A BLAST deve parecer:

- Referencia regional em informatica
- Loja premium com precos agressivos
- Marca moderna e consolidada
- Especialista tecnica
- Empresa confiavel e atualizada

3. DNA Visual Consolidado

Assinatura visual principal: minimalismo comercial de alta conversao.

Mistura de:

- Clean design
- Retail premium
- Tecnologia corporativa
- E-commerce moderno
- Campanha Meta Ads de alta performance
- Visual de varejo nacional forte

4. Estrutura Padrao de Layout

Toda imagem promocional deve seguir hierarquia clara.

Ordem visual ideal:

- Headline impactante no topo
- Oferta ou beneficio principal
- Produto centralizado
- Especificacoes rapidas
- Preco dominante
- Provas de valor
- Marca no rodape

5. Formatos Oficiais

- Feed principal: 1080x1350 px, proporcao 4:5
- Story: 1080x1920 px
- Quadrado secundario: 1080x1080 px

Sempre gerar em resolucao alta, nitidez maxima e qualidade premium.

6. Paleta Oficial BLAST

Primaria:

- Roxo Institucional Principal: #6E2BC3
- Roxo Vibrante Oferta: #7A22FF
- Roxo Escuro Premium: #4A0D91
- Lilas Apoio: #C8A7FF

Neutras:

- Preto Premium: #120018
- Grafite: #2B2B2B
- Branco Limpo: #FFFFFF
- Cinza Fundo: #ECECEC

7. Uso das Cores

Roxo em headlines, bordas, precos, selos, icones e destaques.
Branco em fundo de caixas, contraste e tipografia sobre fundos roxos.
Preto em logo, texto institucional e headline secundaria.
Cinza em fundos clean.

8. Tipografia Oficial

Estilo obrigatorio: sans-serif moderna, pesada, geometrica.

Similares ideais:

- Montserrat ExtraBold
- League Spartan
- Gotham Bold
- Nexa Heavy
- Inter Bold
- Poppins Bold

9. Hierarquia Tipografica

- Headline principal: gigante, bold extremo, caixa alta
- Subheadline: menor, forte e objetiva
- Preco: maior elemento comercial da peca
- Especificacoes: medias, claras e de leitura instantanea
- Rodape: discreto e elegante

10. Headlines Permitidas

Devem gerar interrupcao visual, ser curtas, em caixa alta, com impacto imediato e leitura em menos de 1 segundo.

Modelos:

- NAO COMPRE NOTEBOOK...
- COMPUTADOR PARA TRABALHO
- PC PARA PROJETISTA
- NOTEBOOK COM MENOR PRECO
- MONTE SEU PC HOJE
- OFERTA IMPERDIVEL
- PC RAPIDO E SLIM
- NOTEBOOK A PRONTA ENTREGA

11. Fundo Oficial

Estilo obrigatorio: limpo e tecnologico.

Pode conter:

- Geometrias suaves
- Linhas conectadas
- Pontos abstratos
- Colunas desfocadas
- Ambientes corporativos blur
- Shapes translucidos

Nunca usar fundo poluido, texturas pesadas, cores gritantes ou cenarios baguncados.

12. Produto

O produto precisa parecer real, premium e desejavel.

Tratamento visual:

- Recorte limpo
- Sombra suave
- Reflexos discretos
- Iluminacao profissional
- Nitidez alta

Posicao: centro da composicao.
Escala: grande o suficiente para dominar a peca.

13. Categorias de Produto

- Desktop corporativo: limpo, compacto e profissional
- Gamer: RGB controlado, potencia e design agressivo premium
- Notebook: fino, moderno e tela viva
- Perifericos: hero shot central e fundo clean

14. Blocos Comerciais

Caixa de preco:

- Fundo branco
- Borda roxa
- Cantos arredondados
- Preco antigo tachado
- Preco atual gigante

Caixa de beneficios:

- Icones simples
- Texto curto
- Uma linha por beneficio

Caixa tecnica:

- Specs rapidas
- 4 a 6 bullets

15. Estilo de Conversao

Toda imagem precisa vender em 2 segundos.

Elementos obrigatorios:

- Produto claro
- Preco claro
- Oferta clara
- Beneficio claro
- Marca presente

16. Sensacao Psicologica Desejada

Quando alguem olhar a arte deve pensar:

- Loja seria
- Bom preco
- Produto bom
- Vale visitar
- Parece confiavel
- Profissionais entendem do assunto

17. Elementos Proibidos

Nunca gerar:

- Visual amador
- Excesso de efeitos
- Neon exagerado
- Fontes decorativas
- Poluicao textual
- Muitas cores conflitantes
- Produto pequeno
- Fundo carregado
- Clipart barato
- Estilo infantil

18. Identidade por Segmento

Corporativo:

- Fundo claro
- Preto + roxo
- Clean
- Formal

Gamer:

- Roxo + preto + verde ou vermelho secundario
- Mais contraste
- Energia visual
- Premium

Promocional:

- Mais branco
- Menos texto
- Produto hero
- Promocao agressiva
- Preco gigante
- Headline forte
- Selos

19. Logo da Marca

Rodape centralizado: BLAST INFO & TECH

Estilo:

- Futurista
- Minimalista
- Preto ou roxo escuro

Sempre respirar no rodape.

20. Composicao Ideal

Formula vencedora:

- Topo: headline brutal
- Meio esquerdo: specs
- Meio direito: preco
- Centro inferior: produto
- Rodape: logo

21. Prompt Mestre Universal BLAST

Create a premium Brazilian computer store advertisement for BLAST INFO & TECH, vertical 4:5 format, clean light gray background with subtle futuristic tech elements, bold geometric sans-serif typography, strong purple brand identity, giant headline at top, dominant promotional price box, realistic centered product with studio lighting and soft shadows, premium retail commercial design, ultra sharp, modern ecommerce aesthetic, high conversion social media ad, clean hierarchy, trustworthy technology brand.

22. Prompt para Campanha Gamer

High-performance gaming PC ad for BLAST INFO & TECH, black and purple premium background, subtle RGB lighting, bold aggressive typography, powerful centered gaming desktop, modern retail campaign style, dramatic lighting, premium Brazilian electronics store ad.

23. Prompt para Notebook

Modern notebook sale ad for BLAST INFO & TECH, clean gray background, bold top headline, 3 laptops centered with depth, rounded benefit boxes, purple brand accents, premium social media retail design, high conversion layout.

24. Prompt para Workstation

Professional workstation PC ad for architects, engineers and designers, premium tower centered, clean office blurred background, strong purple typography, trustworthy commercial design, modern Brazilian tech retail campaign.

25. Regra Final de Consistencia

Se remover o logo e o nome da marca, a arte ainda precisa parecer BLAST apenas por:

- Roxo dominante
- Fundo clean
- Tipografia forte
- Produto hero
- Layout organizado
- Oferta clara
- Aparencia premium

26. Nivel de Qualidade Esperado

Cada nova arte deve parecer:

- Feita por agencia profissional
- Marca consolidada nacional
- Campanha de alta verba
- Visual pronto para escalar anuncios

27. Mandamento Principal

A BLAST vende tecnologia com autoridade visual.
Nenhuma peca pode parecer improvisada.
Toda imagem precisa transmitir valor antes mesmo de ser lida.
"""

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
