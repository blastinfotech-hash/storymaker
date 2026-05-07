from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from textwrap import dedent

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils.html import strip_tags

from openai import OpenAI

from stories.models import StoryConcept, StoryImageVariant, StoryProject


@dataclass(frozen=True)
class BrandSystem:
    label: str
    primary: str
    accent: str
    dark: str
    light: str
    layout_summary: str
    manual: str
    master_prompt: str


BLAST_GUIDE = BrandSystem(
    label="BLAST",
    primary="#6E2BC3",
    accent="#7A22FF",
    dark="#120018",
    light="#FFFFFF",
    layout_summary="minimalismo comercial premium, roxo dominante, produto hero centralizado, layout clean de alta conversao",
    manual=(
        "Autoridade em tecnologia, varejo premium, tipografia sans-serif pesada, layout claro com headline no topo, "
        "produto no centro, preco dominante, blocos comerciais limpos, fundo clean tecnologico e roxo institucional."
    ),
    master_prompt=(
        "Create a premium Brazilian computer store advertisement for BLAST INFO & TECH, vertical social media format, "
        "clean light gray background with subtle futuristic tech elements, bold geometric sans-serif typography, "
        "strong purple brand identity, giant headline at top, dominant promotional price box, realistic centered product with studio lighting and soft shadows."
    ),
)

BETA_GUIDE = BrandSystem(
    label="BETA",
    primary="#0077D9",
    accent="#0066CC",
    dark="#111111",
    light="#FFFFFF",
    layout_summary="varejo de informatica mobile-first, azul corporativo forte, preco extremamente dominante, produto central e fundo corporativo desfocado",
    manual=(
        "Promocao direta, conversao rapida, leitura em menos de 3 segundos, estrutura modular 4:5, azul corporativo vibrante, "
        "boxes muito arredondados, fundo clean desfocado, produto protagonista, preco dominante, tipografia bold e composicao simetrica."
    ),
    master_prompt=(
        "Create a clean Brazilian computer store promotional ad for Beta Informatica, corporate blue visual identity, vertical social ad, "
        "logo on top, aggressive promotional headline, dominant price box, centered realistic product, clean blurred store or office background, bold sans-serif typography and extremely clear commercial hierarchy."
    ),
)


def get_brand_system(brand_mode: str) -> BrandSystem:
    return BLAST_GUIDE if brand_mode == StoryProject.BrandMode.BLAST else BETA_GUIDE


def generate_story_concept(project: StoryProject) -> StoryConcept:
    latest = project.current_concept
    brand = get_brand_system(project.brand_mode)
    version_number = (latest.version_number + 1) if latest else 1
    kind = StoryConcept.GenerationKind.REVISION if latest else StoryConcept.GenerationKind.INITIAL
    prompt_snapshot = build_story_prompt(project, brand, latest)
    provider_response = ""
    payload = fallback_story_copy(project, brand, latest)

    if settings.OPENAI_API_KEY:
        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.responses.create(model=settings.OPENAI_TEXT_MODEL, input=prompt_snapshot)
            provider_response = response.output_text
            payload = parse_story_response(response.output_text, project, brand)
        except Exception as exc:  # noqa: BLE001
            provider_response = f"OpenAI text generation failed: {exc}"

    project.concepts.update(is_current=False)
    concept = StoryConcept.objects.create(
        project=project,
        parent=latest,
        version_number=version_number,
        generation_kind=kind,
        status=StoryConcept.Status.READY,
        instruction_snapshot=project.adjustment_request,
        prompt_snapshot=prompt_snapshot,
        provider_response=provider_response,
        **payload,
    )
    project.status = StoryProject.Status.CONCEPT_READY
    project.error_message = ""
    project.save(update_fields=["status", "error_message", "updated_at"])
    return concept


def generate_story_image_variant(concept: StoryConcept, variant_number: int) -> StoryImageVariant:
    brand = get_brand_system(concept.project.brand_mode)
    variant, _ = StoryImageVariant.objects.get_or_create(concept=concept, variant_number=variant_number)
    prompt_snapshot = build_image_prompt(concept, brand, variant_number)
    provider_response = ""
    content = build_svg_placeholder(concept, brand, variant_number)
    mime_type = "image/svg+xml"
    filename = f"variant-{variant_number}.svg"

    if settings.OPENAI_API_KEY:
        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.images.generate(
                model=settings.OPENAI_IMAGE_MODEL,
                prompt=prompt_snapshot,
                size=image_size_for_format(concept.project.target_format),
            )
            content = base64.b64decode(response.data[0].b64_json)
            mime_type = "image/png"
            filename = f"variant-{variant_number}.png"
            provider_response = f"Image generated with {settings.OPENAI_IMAGE_MODEL}."
        except Exception as exc:  # noqa: BLE001
            provider_response = f"OpenAI image generation failed: {exc}"

    variant.image_prompt_snapshot = prompt_snapshot
    variant.provider_response = provider_response
    variant.status = StoryImageVariant.Status.READY
    variant.error_message = ""
    variant.asset.save(filename, ContentFile(content), save=False)
    variant.asset_mime_type = mime_type
    variant.save()
    refresh_project_status(concept.project)
    return variant


def build_story_prompt(project: StoryProject, brand: BrandSystem, latest: StoryConcept | None) -> str:
    article_context = ""
    if project.article_id:
        article_context = dedent(
            f"""
            Article title: {project.article.title}
            Article summary: {strip_tags(project.article.summary)}
            Article category: {project.article.category}
            """
        ).strip()

    previous_context = ""
    if latest:
        previous_context = dedent(
            f"""
            Previous headline: {latest.headline}
            Previous body: {latest.body_text}
            Previous visual direction: {latest.visual_direction}
            """
        ).strip()

    return dedent(
        f"""
        You are creating a commercial social media concept for {brand.label} Informatica.

        Brand DNA:
        {brand.manual}

        Master prompt:
        {brand.master_prompt}

        Project title: {project.title}
        Brand mode: {project.brand_mode}
        Content type: {project.content_type}
        Target format: {project.target_format}
        Topic: {project.topic}
        Custom brief: {project.custom_brief}
        Promotional price: {project.promotional_price}
        Call to action: {project.call_to_action}
        Adjustment request: {project.adjustment_request}

        {article_context}

        {previous_context}

        Return plain text in this exact format:
        HEADLINE: ...
        SUBHEADLINE: ...
        BODY: ...
        PRICE: ...
        CTA: ...
        VISUAL_DIRECTION: ...
        """
    ).strip()


def build_image_prompt(concept: StoryConcept, brand: BrandSystem, variant_number: int) -> str:
    project = concept.project
    return dedent(
        f"""
        {brand.master_prompt}

        Brand mode: {project.get_brand_mode_display()}
        Layout summary: {brand.layout_summary}
        Headline: {concept.headline}
        Subheadline: {concept.subheadline}
        Body: {concept.body_text}
        Price: {concept.price_text}
        CTA: {concept.call_to_action}
        Visual direction: {concept.visual_direction}
        Output format: {project.get_target_format_display()}
        Variation number: {variant_number} of {project.requested_image_count}

        Create a distinct variation while keeping the same campaign concept, same product positioning and same brand identity.
        """
    ).strip()


def parse_story_response(response_text: str, project: StoryProject, brand: BrandSystem) -> dict:
    values = {}
    for line in response_text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip().upper()] = value.strip()
    generated = fallback_story_copy(project, brand, None)
    return {
        "headline": values.get("HEADLINE", generated["headline"]),
        "subheadline": values.get("SUBHEADLINE", generated["subheadline"]),
        "body_text": values.get("BODY", generated["body_text"]),
        "price_text": values.get("PRICE", generated["price_text"]),
        "call_to_action": values.get("CTA", generated["call_to_action"]),
        "visual_direction": values.get("VISUAL_DIRECTION", generated["visual_direction"]),
    }


def fallback_story_copy(project: StoryProject, brand: BrandSystem, latest: StoryConcept | None) -> dict:
    topic = project.topic or (project.article.title if project.article_id else project.title)
    body = strip_tags(project.article.summary) if project.article_id else project.custom_brief
    body = body or "Destaque rapido com foco em conversao, clareza comercial e leitura imediata."
    prefix = "OFERTA" if project.content_type == StoryProject.ContentType.PROMOTIONAL else "DESTAQUE"
    headline = f"{prefix} {brand.label}: {topic[:100].upper()}"
    subheadline = {
        StoryProject.BrandMode.BLAST: "Visual premium, tecnologia com autoridade e oferta clara.",
        StoryProject.BrandMode.BETA: "Promocao direta, preco forte e leitura mobile-first.",
    }[project.brand_mode]
    refinement = f" Ajuste solicitado: {project.adjustment_request}" if project.adjustment_request else ""
    visual_direction = (
        f"Seguir o DNA {brand.label} com {brand.layout_summary}. Preco dominante, produto protagonista e hierarquia comercial extrema."
        f"{refinement}"
    )
    return {
        "headline": headline,
        "subheadline": subheadline,
        "body_text": body,
        "price_text": project.promotional_price or "Consulte o melhor preco",
        "call_to_action": project.call_to_action or "Chame agora e garanta sua oferta",
        "visual_direction": visual_direction,
    }


def build_svg_placeholder(concept: StoryConcept, brand: BrandSystem, variant_number: int) -> bytes:
    width, height = canvas_for_format(concept.project.target_format)
    headline = escape_xml(concept.headline[:52])
    subheadline = escape_xml(concept.subheadline[:90])
    body = escape_xml(concept.body_text[:180])
    price = escape_xml(concept.price_text or "Consulte")
    cta = escape_xml(concept.call_to_action or "Fale com a loja")
    brand_label = "BLAST INFO & TECH" if concept.project.brand_mode == StoryProject.BrandMode.BLAST else "BETA INFORMATICA"
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
      <rect width="{width}" height="{height}" fill="#F4F5F7"/>
      <rect x="0" y="0" width="{width}" height="{int(height * 0.2)}" fill="{brand.primary}"/>
      <circle cx="{int(width * 0.88)}" cy="{int(height * 0.12)}" r="{int(width * 0.22)}" fill="{brand.accent}" fill-opacity="0.18"/>
      <rect x="{int(width * 0.08)}" y="{int(height * 0.24)}" width="{int(width * 0.84)}" height="{int(height * 0.30)}" rx="32" fill="#FFFFFF"/>
      <rect x="{int(width * 0.08)}" y="{int(height * 0.58)}" width="{int(width * 0.46)}" height="{int(height * 0.16)}" rx="28" fill="#FFFFFF"/>
      <rect x="{int(width * 0.60)}" y="{int(height * 0.58)}" width="{int(width * 0.32)}" height="{int(height * 0.14)}" rx="28" fill="#FFFFFF" stroke="{brand.primary}" stroke-width="8"/>
      <rect x="0" y="{int(height * 0.87)}" width="{width}" height="{int(height * 0.13)}" fill="{brand.primary}"/>
      <text x="{int(width * 0.08)}" y="{int(height * 0.09)}" fill="{brand.light}" font-size="{int(width * 0.055)}" font-weight="700" font-family="Arial">{headline}</text>
      <text x="{int(width * 0.08)}" y="{int(height * 0.135)}" fill="{brand.light}" font-size="{int(width * 0.027)}" font-family="Arial">{subheadline}</text>
      <text x="{int(width * 0.20)}" y="{int(height * 0.39)}" fill="{brand.dark}" font-size="{int(width * 0.035)}" font-weight="700" font-family="Arial">Produto / imagem IA</text>
      <text x="{int(width * 0.20)}" y="{int(height * 0.44)}" fill="{brand.dark}" font-size="{int(width * 0.023)}" font-family="Arial">{body}</text>
      <text x="{int(width * 0.12)}" y="{int(height * 0.65)}" fill="{brand.dark}" font-size="{int(width * 0.028)}" font-family="Arial">Variacao {variant_number}</text>
      <text x="{int(width * 0.63)}" y="{int(height * 0.63)}" fill="{brand.primary}" font-size="{int(width * 0.025)}" font-family="Arial">Preco</text>
      <text x="{int(width * 0.63)}" y="{int(height * 0.68)}" fill="{brand.primary}" font-size="{int(width * 0.05)}" font-weight="700" font-family="Arial">{price}</text>
      <text x="{int(width * 0.08)}" y="{int(height * 0.94)}" fill="{brand.light}" font-size="{int(width * 0.024)}" font-family="Arial">{cta}</text>
      <text x="{int(width * 0.92)}" y="{int(height * 0.94)}" text-anchor="end" fill="{brand.light}" font-size="{int(width * 0.026)}" font-family="Arial">{brand_label}</text>
    </svg>
    """
    return dedent(svg).strip().encode("utf-8")


def canvas_for_format(target_format: str) -> tuple[int, int]:
    if target_format == StoryProject.Format.FEED:
        return 1080, 1350
    if target_format == StoryProject.Format.SQUARE:
        return 1080, 1080
    return 1080, 1920


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
    if ready_count >= project.requested_image_count:
        project.status = StoryProject.Status.READY_FOR_SELECTION
        project.error_message = ""
    elif generating_count:
        project.status = StoryProject.Status.IMAGE_GENERATING
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
        price_match = re.search(r"R\$\s*[\d\.,]+", block, flags=re.IGNORECASE)
        price = price_match.group(0).upper() if price_match else ""
        description_lines = [line for line in lines[1:] if line.upper() != price.upper()]
        description = " ".join(description_lines).strip()
        promotions.append({"title": title[:200], "description": description, "price": price})
    return promotions


def split_by_price_blocks(raw_input: str) -> list[str]:
    lines = [line for line in raw_input.splitlines() if line.strip()]
    if not lines:
        return []
    blocks = []
    current = []
    for line in lines:
        current.append(line)
        if re.search(r"R\$\s*[\d\.,]+", line, flags=re.IGNORECASE):
            blocks.append("\n".join(current))
            current = []
    if current:
        blocks.append("\n".join(current))
    return blocks


def escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )
