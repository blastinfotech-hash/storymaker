from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from textwrap import dedent

from django.conf import settings
from django.core.files.base import ContentFile

from openai import OpenAI

from stories.models import StoryConcept, StoryImageVariant, StoryProject


PRICE_CONTEXT_PATTERN = re.compile(
    r"(R\$\s*[\d\.,]+|\b\d{1,2}x\b|\bx\s*de\b|\bsem juros\b|\bparcelad[oa]\b|\bà vista\b|\ba vista\b)",
    flags=re.IGNORECASE,
)


# ============================================================================
# PROMPT VISUAL FIXO — para alterar a diretriz visual, edite APENAS aqui.
# Cada marca tem o seu próprio prompt fixo, contendo somente cores e elementos
# a serem utilizados. Nenhuma instrução de estrutura/composição/layout deve
# existir aqui: o único acoplamento da imagem é este prompt + o texto digitado
# pelo operador.
# ============================================================================

BLAST_FIXED_VISUAL_PROMPT = dedent(
    """
    Manual Oficial de Identidade Visual para Geração de Imagens IA - BLAST INFO & TECH.

    A BLAST deve comunicar autoridade em tecnologia, oferta confiável, preço competitivo, modernidade, clareza comercial, performance, compra inteligente e aparência premium acessível. Toda peça precisa parecer criada por uma empresa séria, dominante no segmento local e altamente especializada.

    DNA visual: minimalismo comercial de alta conversão, mistura de clean design, retail premium, tecnologia corporativa, e-commerce moderno e campanha Meta Ads de alta performance. A BLAST não deve parecer loja amadora, banner poluído, arte genérica de marketplace, criativo barato ou visual gamer infantilizado fora de campanhas gamer específicas.

    Paleta: roxo institucional #6E2BC3, roxo vibrante #7A22FF, roxo escuro #4A0D91, lilás #C8A7FF, preto premium #120018, grafite, branco limpo e cinza de fundo. Roxo deve aparecer em headlines, bordas, preços, selos, ícones e destaques.

    Tipografia: sans-serif moderna, pesada e geométrica, similar a Montserrat ExtraBold, League Spartan, Gotham Bold, Nexa Heavy, Inter Bold ou Poppins Bold. Headline gigante e forte; preço como maior elemento comercial; especificações claras e de leitura instantânea.

    Fundo: limpo e tecnológico, com geometrias suaves, linhas conectadas, pontos abstratos, colunas desfocadas ou ambientes corporativos blur. Nunca usar fundo poluído, texturas pesadas, cores gritantes ou cenários bagunçados.

    Qualidade esperada: arte de agência profissional, marca consolidada, campanha de alta verba, visual pronto para escalar anúncios. Se remover logo e nome da marca, a peça ainda precisa parecer BLAST por roxo dominante, fundo clean, tipografia forte, produto hero e oferta clara.
    """
).strip()


BETA_FIXED_VISUAL_PROMPT = dedent(
    """
    Guia Mestre de Direção Visual - DNA Visual das Artes Promocionais Beta Informática.

    Objetivo: criar peças com forte apelo comercial, conversão rápida em redes sociais, clareza extrema de leitura, aparência tecnológica e profissional. A leitura principal deve acontecer em menos de 3 segundos e comunicar promoção, oportunidade, confiança, tecnologia, custo-benefício e profissionalismo.

    Categoria visual: varejo de informática, marketplace premium popular, promoção corporativa, tecnologia comercial, comunicação de feed social e loja física regional. A estética deve ser limpa, objetiva, comercial, moderna, funcional e altamente escaneável.

    Fundo: nunca competir com o produto. Usar loja de informática, showroom, escritório, ambiente corporativo ou espaço comercial com gaussian blur forte, baixa nitidez, opacidade reduzida, baixo contraste e aparência clean. Paleta de fundo: branco acinzentado, off-white, cinza claro e cinza frio.

    Paleta: azul corporativo dominante transmitindo tecnologia, confiança, segurança, profissionalismo e varejo moderno. Usar azul em caixas promocionais, boxes de preço, rodapés, CTAs, destaques e headlines. Tons aproximados: #0077D9, #0066CC, #0A5DBB. Branco para preços e títulos sobre azul. Preto para headlines secundárias, subtítulos e especificações. Cinza para fundo, sombras e profundidade. Madeira clara pode aparecer como base física clean, horizontal, pouco saturada e com baixa presença visual.

    Tipografia: sans-serif moderna, referência Montserrat, Gotham, Poppins, Anton ou Arial Rounded em casos específicos. Predominar caixa alta, bold agressivo, alta legibilidade, pouco ornamento, espaçamento controlado e leitura mobile-first.

    Produto: protagonista sempre. Grande escala, centralizado, alta nitidez, iluminação suave, recorte limpo, sombras suaves e profundidade realista. Evitar brilho exagerado, reflexos agressivos, glow, estética gamer e saturação excessiva.

    Linguagem visual: direta, comercial, objetiva, limpa, moderna e escaneável. A arte deve funcionar em leitura rápida, identificando instantaneamente promoção, preço, produto e categoria.

    Proibições: fundos poluídos, neon exagerado, RGB gamer, sombras pesadas, glow excessivo, gradientes agressivos, tipografia fina, excesso de elementos, excesso de cores, desalinhamentos, textos longos e ícones desnecessários.
    """
).strip()


@dataclass(frozen=True)
class BrandSystem:
    label: str
    company_name: str
    primary: str
    accent: str
    dark: str
    light: str
    visual_prompt: str


BLAST_GUIDE = BrandSystem(
    label="BLAST",
    company_name="BLAST INFO & TECH",
    primary="#6E2BC3",
    accent="#7A22FF",
    dark="#120018",
    light="#FFFFFF",
    visual_prompt=BLAST_FIXED_VISUAL_PROMPT,
)

BETA_GUIDE = BrandSystem(
    label="BETA",
    company_name="Beta Informática",
    primary="#0077D9",
    accent="#0066CC",
    dark="#111111",
    light="#FFFFFF",
    visual_prompt=BETA_FIXED_VISUAL_PROMPT,
)


def get_brand_system(brand_mode: str) -> BrandSystem:
    return BLAST_GUIDE if brand_mode == StoryProject.BrandMode.BLAST else BETA_GUIDE


def build_image_prompt(project: StoryProject, brand: BrandSystem, target_format: str) -> str:
    """Monta o prompt da imagem casando apenas o prompt visual fixo da marca
    com o texto digitado pelo operador. Nenhuma instrução de estrutura ou
    composição é adicionada."""

    format_label = dict(StoryProject.Format.choices).get(target_format, target_format)

    human_lines = [
        f"- Tema/produto: {project.topic}" if project.topic else "",
        f"- Descrição da arte: {project.custom_brief}" if project.custom_brief else "",
        f"- Preço promocional: {project.promotional_price}" if project.promotional_price else "",
        f"- Chamada/CTA: {project.call_to_action}" if project.call_to_action else "",
        f"- Pedido de ajuste: {project.adjustment_request}" if project.adjustment_request else "",
    ]
    human_text = "\n".join(line for line in human_lines if line)

    return (
        f"{brand.visual_prompt}\n\n"
        f"Texto fornecido pelo operador:\n"
        f"{human_text}\n\n"
        f"Formato de saída: {format_label}"
    )


def generate_story_image(project: StoryProject, target_format: str) -> StoryImageVariant:
    brand = get_brand_system(project.brand_mode)

    # O conceito existe apenas como contêiner de variants. Nenhuma cópia de
    # texto é gerada: o prompt da imagem usa direto o texto do operador.
    concept = project.current_concept
    if concept is None:
        project.concepts.update(is_current=False)
        concept = StoryConcept.objects.create(
            project=project,
            version_number=1,
            generation_kind=StoryConcept.GenerationKind.INITIAL,
            status=StoryConcept.Status.READY,
            is_current=True,
        )

    variant, _ = StoryImageVariant.objects.get_or_create(
        concept=concept,
        target_format=target_format,
        variant_number=1,
    )
    prompt_snapshot = build_image_prompt(project, brand, target_format)
    provider_response = ""
    content: bytes | None = None
    mime_type = ""
    filename = ""
    success = False

    if settings.OPENAI_API_KEY:
        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.images.generate(
                model=settings.OPENAI_IMAGE_MODEL,
                prompt=prompt_snapshot,
                size=image_size_for_format(target_format),
            )
            content = base64.b64decode(response.data[0].b64_json)
            mime_type = "image/png"
            filename = f"{target_format}-variant-1.png"
            provider_response = f"Image generated with {settings.OPENAI_IMAGE_MODEL}."
            success = True
        except Exception as exc:  # noqa: BLE001
            provider_response = f"OpenAI image generation failed: {exc}"
    else:
        provider_response = "Image generation skipped: OPENAI_API_KEY is not configured."

    variant.image_prompt_snapshot = prompt_snapshot
    variant.provider_response = provider_response

    if success and content is not None:
        variant.status = StoryImageVariant.Status.READY
        variant.error_message = ""
        variant.asset.save(filename, ContentFile(content), save=False)
        variant.asset_mime_type = mime_type
    else:
        variant.status = StoryImageVariant.Status.FAILED
        variant.error_message = provider_response or "Image generation failed."
        if variant.asset:
            variant.asset.delete(save=False)
        variant.asset_mime_type = ""

    variant.save()
    refresh_project_status(project)
    return variant


def image_size_for_format(target_format: str) -> str:
    if target_format == StoryProject.Format.FEED:
        return "1024x1536"
    if target_format == StoryProject.Format.SQUARE:
        return "1024x1024"
    return "1024x1792"


def refresh_project_status(project: StoryProject) -> None:
    concept = project.current_concept
    if not concept:
        return
    ready_count = concept.variants.filter(status=StoryImageVariant.Status.READY).count()
    generating_count = concept.variants.filter(status__in=[StoryImageVariant.Status.QUEUED, StoryImageVariant.Status.GENERATING]).count()
    failed_count = concept.variants.filter(status=StoryImageVariant.Status.FAILED).count()
    total_count = concept.variants.count()
    if ready_count and not generating_count:
        project.status = StoryProject.Status.READY_FOR_SELECTION
        project.error_message = ""
    elif generating_count:
        project.status = StoryProject.Status.IMAGE_GENERATING
    elif total_count and failed_count >= total_count:
        project.status = StoryProject.Status.FAILED
    project.save(update_fields=["status", "error_message", "updated_at"])


def split_bulk_promotions(raw_input: str) -> list[dict]:
    normalized = raw_input.strip()
    if not normalized:
        return []

    blocks = [block.strip() for block in re.split(r"\n\s*\n+", normalized) if block.strip()]
    if len(blocks) == 1:
        blocks = split_by_price_blocks(normalized)

    promotions = []
    for block in blocks:
        lines = [line.strip(" -\t") for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        title = lines[0]
        price_lines = extract_price_lines(block)
        price = " | ".join(price_lines)
        description_lines = [line for line in lines[1:] if line not in price_lines]
        description = "\n".join(description_lines).strip()
        promotions.append({"title": title[:200], "description": description, "price": price})
    return promotions


def split_by_price_blocks(raw_input: str) -> list[str]:
    lines = [line.strip() for line in raw_input.splitlines() if line.strip()]
    if not lines:
        return []

    blocks = []
    current = []
    saw_price = False
    for index, line in enumerate(lines):
        if current and saw_price and is_new_promotion_start(lines, index):
            blocks.append("\n".join(current))
            current = []
            saw_price = False
        current.append(line)
        if is_price_line(line):
            saw_price = True
    if current:
        blocks.append("\n".join(current))
    return blocks


def extract_price_lines(text: str) -> list[str]:
    price_lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if is_price_line(line):
            price_lines.append(line)
    return price_lines


def is_price_line(line: str) -> bool:
    if not line:
        return False
    normalized = " ".join(line.split())
    if not PRICE_CONTEXT_PATTERN.search(normalized):
        return False
    return bool(re.search(r"\d", normalized))


def is_new_promotion_start(lines: list[str], index: int) -> bool:
    line = lines[index].strip()
    if not line or is_price_line(line):
        return False

    previous_line = lines[index - 1].strip() if index > 0 else ""
    if not previous_line or not is_price_line(previous_line):
        return False

    if len(line) < 8 or not re.search(r"[A-Za-zÀ-ÿ]", line):
        return False

    if line.lower().startswith(("ou ", "em ", "pix", "boleto", "cartao")):
        return False

    return True
