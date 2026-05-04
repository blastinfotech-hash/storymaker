import base64
import hashlib
import json
import logging
from io import BytesIO
from html import escape

from django.conf import settings
from django.core.files.base import ContentFile
from openai import OpenAI
from PIL import Image

from branding.models import BrandGuide

from .models import StoryProject, StoryVersion

logger = logging.getLogger(__name__)


class ImageGenerationError(Exception):
    pass

PALETTES = [
    ("#04111f", "#0e2a47", "#2de1fc", "#90f3ff"),
    ("#12081f", "#33215f", "#8d63ff", "#ded0ff"),
    ("#08131d", "#11354a", "#35ffa1", "#c4ffe6"),
    ("#180d08", "#523223", "#ff9654", "#ffe0cc"),
]


class _SafeTemplateDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def _resize_to_target(raw_image: bytes, target_size: tuple[int, int]) -> bytes:
    image = Image.open(BytesIO(raw_image)).convert("RGBA")
    resized = image.resize(target_size, Image.Resampling.LANCZOS)
    output = BytesIO()
    resized.convert("RGB").save(output, format="PNG", optimize=True)
    return output.getvalue()


def _get_client() -> OpenAI | None:
    if not settings.OPENAI_API_KEY:
        return None
    return OpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=settings.OPENAI_REQUEST_TIMEOUT,
        max_retries=0,
    )


def is_openai_configured() -> bool:
    return bool(settings.OPENAI_API_KEY)


def _article_context(project: StoryProject) -> str:
    if not project.source_article:
        return ""
    article = project.source_article
    return (
        f"Noticia relacionada: {article.title}\n"
        f"Resumo: {article.summary or article.content or 'Sem resumo salvo.'}\n"
        f"URL: {article.url}"
    )


def build_project_context(project: StoryProject, base_version: StoryVersion | None = None) -> str:
    lines = [
        f"Titulo interno: {project.title}",
        f"Tipo de story: {project.get_story_type_display()}",
        f"Briefing do editor: {project.user_request or 'Sem briefing adicional.'}",
    ]
    if project.equipment_configuration:
        lines.append(f"Configuracao do equipamento: {project.equipment_configuration}")
    article_context = _article_context(project)
    if article_context:
        lines.append(article_context)
    if base_version:
        lines.extend(
            [
                f"Versao base: v{base_version.version_number}",
                f"Headline atual: {base_version.headline or 'Sem headline.'}",
                f"Copy atual: {base_version.copy_text or 'Sem copy.'}",
                f"Direcao visual atual: {base_version.visual_direction or 'Sem direcao.'}",
                f"Prompt de imagem atual: {base_version.image_prompt or 'Sem prompt.'}",
            ]
        )
    return "\n".join(lines)


def _news_article_context(project: StoryProject) -> str:
    article = project.source_article
    if not article:
        return "Sem noticia associada."
    return "\n".join(
        [
            f"Titulo da noticia: {article.title}",
            f"Resumo da noticia: {article.summary or 'Sem resumo.'}",
            f"Conteudo da noticia: {article.content or 'Sem conteudo adicional.'}",
            f"Fonte: {article.source.name if article.source else 'Fonte nao informada'}",
            f"URL: {article.url}",
        ]
    )


def _story_generation_prompt(
    project: StoryProject,
    guide: BrandGuide,
    change_request: str,
    base_version: StoryVersion | None = None,
) -> str:
    return _render_template(
        guide.copy_prompt_template,
        brand_name=guide.name,
        visual_identity_prompt=guide.visual_identity_prompt,
        brand_summary=guide.visual_identity_prompt,
        visual_rules=guide.visual_identity_prompt,
        project_context=build_project_context(project=project, base_version=base_version),
        change_request=change_request or "Sem ajustes adicionais.",
    )


def _news_generation_prompt(
    project: StoryProject,
    guide: BrandGuide,
    change_request: str,
    base_version: StoryVersion | None = None,
) -> str:
    return f"""Voce esta criando um post de noticia para a BLAST INFO & TECH.

Guia visual da marca:
{guide.visual_identity_prompt}

Noticia base:
{_news_article_context(project)}

Contexto do projeto:
{build_project_context(project=project, base_version=base_version)}

Direcionamento complementar do editor:
{change_request or project.user_request or 'Sem direcionamento adicional.'}

Regras obrigatorias:
- Este fluxo e para noticia, nao para story promocional.
- Gere a arte pensando em feed 4:5 e nao em story 9:16.
- O texto da imagem deve ser criado principalmente com base na noticia.
- O direcionamento do editor serve apenas como complemento.
- Gere tambem uma legenda separada em portugues do Brasil com no maximo 500 caracteres.
- A legenda deve ser informativa e pronta para publicacao.
- Para noticia, o texto da imagem e a legenda nao podem ser identicos.

Responda apenas em JSON valido com estas chaves:
- headline
- copy_text
- caption_text
- visual_direction
- image_prompt
- generation_notes
"""


def _strip_json_block(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        parts = text.split("\n")
        if parts:
            parts = parts[1:]
        if parts and parts[-1].strip() == "```":
            parts = parts[:-1]
        text = "\n".join(parts).strip()
    return text


def _safe_json(raw_text: str) -> dict:
    text = _strip_json_block(raw_text)
    return json.loads(text)


def _render_template(template: str, **context) -> str:
    return template.format_map(_SafeTemplateDict(context))


def _wrap_svg_text(text: str, max_chars: int, max_lines: int) -> list[str]:
    words = text.replace("\n", " ").split()
    if not words:
        return []

    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        lines.append(current)
        current = word
        if len(lines) >= max_lines - 1:
            break

    if len(lines) < max_lines:
        lines.append(current)

    if len(lines) > max_lines:
        lines = lines[:max_lines]

    remaining_words = words[len(" ".join(lines).split()):]
    if remaining_words and lines:
        lines[-1] = lines[-1][: max(0, max_chars - 1)].rstrip() + "..."
    return lines


def _text_block(lines: list[str], x: int, y: int, font_size: int, line_height: int, fill: str, weight: str = "400") -> str:
    if not lines:
        return ""
    tspans = []
    for index, line in enumerate(lines):
        dy = "0" if index == 0 else str(line_height)
        tspans.append(f'<tspan x="{x}" dy="{dy}">{escape(line)}</tspan>')
    return (
        f'<text x="{x}" y="{y}" fill="{fill}" font-family="Arial, sans-serif" '
        f'font-size="{font_size}" font-weight="{weight}">{"".join(tspans)}</text>'
    )


def _palette_for_version(version: StoryVersion) -> tuple[str, str, str, str]:
    seed = f"{version.project.story_type}:{version.headline}:{version.image_prompt}"
    index = int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16) % len(PALETTES)
    return PALETTES[index]


def _infer_subject(prompt: str) -> str:
    lowered = prompt.lower()
    if any(term in lowered for term in ["notebook", "laptop"]):
        return "laptop"
    if any(term in lowered for term in ["chip", "ia", "ai", "circuit"]):
        return "chip"
    if any(term in lowered for term in ["cloud", "nuvem", "server", "servidor", "datacenter"]):
        return "cloud"
    return "abstract"


def _subject_art(subject: str, accent: str, accent_soft: str) -> str:
    if subject == "laptop":
        return f"""
<g transform="translate(590 560)">
  <rect x="0" y="0" width="340" height="220" rx="22" fill="#08111d" stroke="{accent}" stroke-width="5"/>
  <rect x="24" y="24" width="292" height="172" rx="12" fill="none" stroke="{accent_soft}" stroke-width="3" opacity="0.95"/>
  <rect x="-36" y="230" width="412" height="28" rx="14" fill="{accent}" opacity="0.95"/>
  <rect x="110" y="238" width="120" height="8" rx="4" fill="#ffffff" opacity="0.48"/>
  <path d="M70 175 L138 118 L178 148 L238 88 L290 126" fill="none" stroke="{accent}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="138" cy="118" r="8" fill="{accent_soft}"/>
  <circle cx="178" cy="148" r="8" fill="{accent_soft}"/>
  <circle cx="238" cy="88" r="8" fill="{accent_soft}"/>
  <circle cx="290" cy="126" r="8" fill="{accent_soft}"/>
</g>
"""
    if subject == "chip":
        return f"""
<g transform="translate(620 520)">
  <rect x="0" y="0" width="260" height="260" rx="34" fill="#08111d" stroke="{accent}" stroke-width="6"/>
  <rect x="54" y="54" width="152" height="152" rx="22" fill="none" stroke="{accent_soft}" stroke-width="4"/>
  <circle cx="130" cy="130" r="38" fill="{accent}" opacity="0.2"/>
  <circle cx="130" cy="130" r="20" fill="{accent}"/>
  <g stroke="{accent_soft}" stroke-width="6" stroke-linecap="round">
    <line x1="38" y1="40" x2="38" y2="0"/><line x1="84" y1="40" x2="84" y2="0"/><line x1="130" y1="40" x2="130" y2="0"/><line x1="176" y1="40" x2="176" y2="0"/><line x1="222" y1="40" x2="222" y2="0"/>
    <line x1="38" y1="260" x2="38" y2="300"/><line x1="84" y1="260" x2="84" y2="300"/><line x1="130" y1="260" x2="130" y2="300"/><line x1="176" y1="260" x2="176" y2="300"/><line x1="222" y1="260" x2="222" y2="300"/>
    <line x1="0" y1="38" x2="40" y2="38"/><line x1="0" y1="84" x2="40" y2="84"/><line x1="0" y1="130" x2="40" y2="130"/><line x1="0" y1="176" x2="40" y2="176"/><line x1="0" y1="222" x2="40" y2="222"/>
    <line x1="220" y1="38" x2="260" y2="38"/><line x1="220" y1="84" x2="260" y2="84"/><line x1="220" y1="130" x2="260" y2="130"/><line x1="220" y1="176" x2="260" y2="176"/><line x1="220" y1="222" x2="260" y2="222"/>
  </g>
</g>
"""
    if subject == "cloud":
        return f"""
<g transform="translate(560 560)">
  <ellipse cx="210" cy="170" rx="180" ry="90" fill="#08111d" stroke="{accent}" stroke-width="5"/>
  <circle cx="150" cy="130" r="80" fill="#08111d" stroke="{accent_soft}" stroke-width="5"/>
  <circle cx="250" cy="110" r="92" fill="#08111d" stroke="{accent_soft}" stroke-width="5"/>
  <path d="M80 210 C160 275 260 275 340 210" fill="none" stroke="{accent}" stroke-width="8" stroke-linecap="round"/>
  <path d="M142 280 L210 220 L278 280" fill="none" stroke="{accent_soft}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>
</g>
"""
    return f"""
<g transform="translate(610 500)">
  <circle cx="150" cy="160" r="130" fill="{accent}" opacity="0.16"/>
  <circle cx="290" cy="320" r="96" fill="{accent_soft}" opacity="0.18"/>
  <path d="M0 280 C80 120 240 80 340 180" fill="none" stroke="{accent}" stroke-width="12" stroke-linecap="round"/>
  <path d="M20 350 C120 180 260 160 350 250" fill="none" stroke="{accent_soft}" stroke-width="8" stroke-linecap="round"/>
</g>
"""


def _fallback_concept(
    project: StoryProject,
    change_request: str,
    base_version: StoryVersion | None = None,
) -> dict:
    base_copy = base_version.copy_text if base_version else ""
    direction = base_version.visual_direction if base_version else ""
    prompt = base_version.image_prompt if base_version else ""
    seed = project.source_article.title if project.source_article else project.title
    change_suffix = f" Ajuste solicitado: {change_request.strip()}" if change_request.strip() else ""
    return {
        "headline": project.title,
        "copy_text": (
            base_copy
            or f"{seed}\nPanorama rapido para story da {settings.BLAST_BRAND_NAME}."
        ) + change_suffix,
        "caption_text": (
            (project.source_article.summary if project.source_article and project.source_article.summary else seed)[:500]
            if project.story_type == StoryProject.StoryType.NEWS
            else ""
        ),
        "visual_direction": (
            direction
            or "Editorial tech com contraste alto, foco em um elemento principal e leitura imediata no formato 9:16."
        ) + change_suffix,
        "image_prompt": (
            prompt
            or f"Vertical 9:16 editorial tech artwork about {seed}, dramatic lighting, bold composition, premium contrast."
        ) + change_suffix,
        "generation_notes": "Concepto montado em fallback local porque a API de texto nao retornou uma resposta utilizavel.",
        "text_model": "fallback-local",
    }


def generate_story_concept(
    project: StoryProject,
    guide: BrandGuide,
    change_request: str = "",
    base_version: StoryVersion | None = None,
) -> dict:
    client = _get_client()
    if client is None:
        return _fallback_concept(project=project, change_request=change_request, base_version=base_version)

    prompt = (
        _news_generation_prompt(project=project, guide=guide, change_request=change_request, base_version=base_version)
        if project.story_type == StoryProject.StoryType.NEWS
        else _story_generation_prompt(project=project, guide=guide, change_request=change_request, base_version=base_version)
    )

    try:
        response = client.responses.create(
            model=settings.OPENAI_TEXT_MODEL,
            input=prompt,
        )
        data = _safe_json(response.output_text)
    except Exception as exc:
        logger.exception("Failed to generate story concept: %s", exc)
        return _fallback_concept(project=project, change_request=change_request, base_version=base_version)

    return {
        "headline": data.get("headline", project.title),
        "copy_text": data.get("copy_text", "").strip(),
        "caption_text": (data.get("caption_text", "")[:500]).strip() if project.story_type == StoryProject.StoryType.NEWS else "",
        "visual_direction": data.get("visual_direction", "").strip(),
        "image_prompt": data.get("image_prompt", "").strip(),
        "generation_notes": data.get("generation_notes", "Gerado pela API de texto.").strip(),
        "text_model": settings.OPENAI_TEXT_MODEL,
    }


def refine_image_direction(
    version: StoryVersion,
    guide: BrandGuide,
    change_request: str,
) -> dict:
    if not change_request.strip():
        return {
            "visual_direction": version.visual_direction,
            "image_prompt": version.image_prompt,
            "generation_notes": version.generation_notes,
            "text_model": version.text_model,
        }

    client = _get_client()
    if client is None:
        return {
            "visual_direction": f"{version.visual_direction}\nAjuste solicitado: {change_request.strip()}",
            "image_prompt": f"{version.image_prompt}\nAjuste solicitado: {change_request.strip()}",
            "generation_notes": "Direcao visual ajustada em fallback local.",
            "text_model": "fallback-local",
        }

    prompt = _render_template(
        guide.copy_prompt_template,
        brand_name=guide.name,
        visual_identity_prompt=guide.visual_identity_prompt,
        brand_summary=guide.visual_identity_prompt,
        visual_rules=guide.visual_identity_prompt,
        project_context=(
            f"Story aprovado para render de imagem.\n"
            f"Headline: {version.headline}\n"
            f"Copy: {version.copy_text}\n"
            f"Direcao visual atual: {version.visual_direction}\n"
            f"Prompt atual: {version.image_prompt}"
        ),
        change_request=(
            f"Ajuste apenas a direcao visual e o prompt da imagem. Nao reescreva headline nem copy.\n"
            f"Pedido: {change_request}"
        ),
    )

    try:
        response = client.responses.create(model=settings.OPENAI_TEXT_MODEL, input=prompt)
        data = _safe_json(response.output_text)
    except Exception as exc:
        logger.exception("Failed to refine image direction: %s", exc)
        return {
            "visual_direction": f"{version.visual_direction}\nAjuste solicitado: {change_request.strip()}",
            "image_prompt": f"{version.image_prompt}\nAjuste solicitado: {change_request.strip()}",
            "generation_notes": "Direcao visual ajustada em fallback local apos falha da API.",
            "text_model": "fallback-local",
        }

    return {
        "visual_direction": data.get("visual_direction", version.visual_direction).strip(),
        "image_prompt": data.get("image_prompt", version.image_prompt).strip(),
        "generation_notes": data.get("generation_notes", "Direcao visual ajustada pela API de texto.").strip(),
        "text_model": settings.OPENAI_TEXT_MODEL,
    }


def _placeholder_svg(version: StoryVersion, final_prompt: str) -> bytes:
    bg_start, bg_end, accent, accent_soft = _palette_for_version(version)
    subject = _infer_subject(f"{version.headline} {version.image_prompt} {final_prompt}")
    headline_lines = _wrap_svg_text(version.headline or version.project.title, max_chars=18, max_lines=3)
    copy_lines = _wrap_svg_text(version.copy_text or "Preview local gerado para manter o workflow utilizavel.", max_chars=30, max_lines=5)
    prompt_lines = _wrap_svg_text(version.image_prompt or final_prompt, max_chars=40, max_lines=4)
    subject_label = {
        "laptop": "Laptop focus",
        "chip": "AI chip focus",
        "cloud": "Cloud infra focus",
        "abstract": "Editorial tech focus",
    }[subject]
    svg = f"""<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"1080\" height=\"1920\" viewBox=\"0 0 1080 1920\">
<defs>
  <linearGradient id=\"bg\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"1\">
    <stop offset=\"0%\" stop-color=\"{bg_start}\"/>
    <stop offset=\"100%\" stop-color=\"{bg_end}\"/>
  </linearGradient>
  <linearGradient id=\"panel\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"1\">
    <stop offset=\"0%\" stop-color=\"#091120\" stop-opacity=\"0.92\"/>
    <stop offset=\"100%\" stop-color=\"#0f1c32\" stop-opacity=\"0.72\"/>
  </linearGradient>
</defs>
<rect width=\"1080\" height=\"1920\" fill=\"url(#bg)\"/>
<circle cx=\"930\" cy=\"210\" r=\"240\" fill=\"{accent}\" fill-opacity=\"0.18\"/>
<circle cx=\"170\" cy=\"1540\" r=\"290\" fill=\"{accent_soft}\" fill-opacity=\"0.12\"/>
<g opacity=\"0.12\" stroke=\"#ffffff\">
  <line x1=\"80\" y1=\"140\" x2=\"1000\" y2=\"140\"/>
  <line x1=\"80\" y1=\"1780\" x2=\"1000\" y2=\"1780\"/>
  <line x1=\"140\" y1=\"100\" x2=\"140\" y2=\"1820\"/>
  <line x1=\"940\" y1=\"100\" x2=\"940\" y2=\"1820\"/>
</g>
<rect x=\"78\" y=\"96\" width=\"924\" height=\"1728\" rx=\"42\" fill=\"url(#panel)\" stroke=\"#ffffff\" stroke-opacity=\"0.14\"/>
<rect x=\"118\" y=\"140\" width=\"260\" height=\"42\" rx=\"21\" fill=\"{accent}\" fill-opacity=\"0.18\" stroke=\"{accent}\" stroke-opacity=\"0.35\"/>
<text x=\"148\" y=\"169\" fill=\"{accent_soft}\" font-family=\"Arial, sans-serif\" font-size=\"24\" font-weight=\"700\">BLAST INFO &amp; TECH</text>
<text x=\"120\" y=\"250\" fill=\"#ffffff\" font-family=\"Arial, sans-serif\" font-size=\"28\" font-weight=\"700\" letter-spacing=\"4\">GENERATED LOCAL ART</text>
{_text_block(headline_lines, 120, 370, 92, 104, '#ffffff', '700')}
<rect x=\"120\" y=\"720\" width=\"360\" height=\"8\" rx=\"4\" fill=\"{accent}\"/>
{_text_block(copy_lines, 120, 790, 42, 54, '#d9ecff', '400')}
<g transform=\"translate(120 1110)\">
  <rect x=\"0\" y=\"0\" width=\"340\" height=\"128\" rx=\"24\" fill=\"#0a1426\" stroke=\"{accent}\" stroke-opacity=\"0.28\"/>
  <text x=\"28\" y=\"44\" fill=\"{accent_soft}\" font-family=\"Arial, sans-serif\" font-size=\"22\" font-weight=\"700\">VISUAL FOCUS</text>
  <text x=\"28\" y=\"88\" fill=\"#ffffff\" font-family=\"Arial, sans-serif\" font-size=\"34\" font-weight=\"700\">{escape(subject_label)}</text>
</g>
{_subject_art(subject, accent, accent_soft)}
<g transform=\"translate(120 1550)\">
  <rect x=\"0\" y=\"0\" width=\"840\" height=\"190\" rx=\"28\" fill=\"#091221\" fill-opacity=\"0.92\" stroke=\"#ffffff\" stroke-opacity=\"0.08\"/>
  <text x=\"28\" y=\"40\" fill=\"{accent_soft}\" font-family=\"Arial, sans-serif\" font-size=\"22\" font-weight=\"700\">PROMPT SNAPSHOT</text>
  {_text_block(prompt_lines, 28, 86, 28, 34, '#cae6f7', '400')}
</g>
</svg>"""
    return svg.encode("utf-8")


def generate_image_asset(
    version: StoryVersion,
    guide: BrandGuide,
    change_request: str = "",
) -> tuple[str, ContentFile, str, str, str]:
    final_prompt = _render_template(
        guide.image_prompt_template,
        brand_name=guide.name,
        visual_identity_prompt=guide.visual_identity_prompt,
        brand_summary=guide.visual_identity_prompt,
        visual_rules=guide.visual_identity_prompt,
        visual_direction=version.visual_direction or "Sem direcao visual.",
        image_prompt=version.image_prompt or "Sem prompt base.",
        change_request=change_request or "Sem ajustes adicionais.",
    )
    final_prompt += (
        "\n\nNao inserir logo, marca d'agua, assinatura ou selo institucional na arte final."
    )
    if version.project.story_type == StoryProject.StoryType.NEWS:
        final_prompt += (
            "\n\nFormato obrigatorio: post de noticia em feed 4:5 pensado para 1080x1350. "
            "A arte deve usar texto derivado da noticia e o briefing do usuario apenas como direcionamento extra."
        )
    else:
        final_prompt += "\n\nFormato obrigatorio: story 9:16 pensado para 1080x1920, sem legenda separada."

    client = _get_client()
    if client is None:
        raise ImageGenerationError(
            "OPENAI_API_KEY nao esta configurada no processo atual do Django. A imagem nao foi gerada."
        )

    try:
        result = client.images.generate(
            model=settings.OPENAI_IMAGE_MODEL,
            prompt=final_prompt,
            size=settings.OPENAI_IMAGE_SIZE,
        )
        raw_image = base64.b64decode(result.data[0].b64_json)
        raw_image = _resize_to_target(raw_image, version.project.target_dimensions)
        file_name = f"story-v{version.version_number or 'draft'}.png"
        note = (
            f"Imagem gerada pela API da OpenAI com o modelo {settings.OPENAI_IMAGE_MODEL} "
            f"no tamanho final {version.project.target_dimensions[0]}x{version.project.target_dimensions[1]}, sem aplicacao automatica de logo."
        )
        return file_name, ContentFile(raw_image), final_prompt, settings.OPENAI_IMAGE_MODEL, note
    except Exception as exc:
        logger.exception("Failed to generate image asset: %s", exc)
        raise ImageGenerationError(f"Falha na geracao da imagem pela OpenAI: {exc}") from exc
