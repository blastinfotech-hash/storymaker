import base64
import json
import logging
from html import escape

from django.conf import settings
from django.core.files.base import ContentFile
from openai import OpenAI

from branding.models import BrandGuide

from .models import StoryProject, StoryVersion

logger = logging.getLogger(__name__)


class _SafeTemplateDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def _get_client() -> OpenAI | None:
    if not settings.OPENAI_API_KEY:
        return None
    return OpenAI(api_key=settings.OPENAI_API_KEY)


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

    prompt = _render_template(
        guide.copy_prompt_template,
        brand_name=guide.name,
        brand_summary=guide.brand_summary,
        visual_rules=guide.visual_rules,
        project_context=build_project_context(project=project, base_version=base_version),
        change_request=change_request or "Sem ajustes adicionais.",
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
        brand_summary=guide.brand_summary,
        visual_rules=guide.visual_rules,
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
    title = escape(version.headline or version.project.title)
    copy_text = escape((version.copy_text or "Preview local do story.")[:180])
    prompt_excerpt = escape(final_prompt[:220])
    svg = f"""<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"1080\" height=\"1920\" viewBox=\"0 0 1080 1920\">
<defs>
<linearGradient id=\"bg\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"1\">
<stop offset=\"0%\" stop-color=\"#070b1a\"/>
<stop offset=\"55%\" stop-color=\"#13213d\"/>
<stop offset=\"100%\" stop-color=\"#0fd3ff\"/>
</linearGradient>
</defs>
<rect width=\"1080\" height=\"1920\" fill=\"url(#bg)\"/>
<circle cx=\"840\" cy=\"380\" r=\"220\" fill=\"#8d3dff\" fill-opacity=\"0.35\"/>
<circle cx=\"250\" cy=\"1380\" r=\"260\" fill=\"#00f0ff\" fill-opacity=\"0.28\"/>
<rect x=\"84\" y=\"100\" width=\"912\" height=\"1720\" rx=\"42\" fill=\"rgba(4,8,20,0.48)\" stroke=\"rgba(255,255,255,0.16)\"/>
<text x=\"130\" y=\"220\" fill=\"#a9f6ff\" font-family=\"Arial, sans-serif\" font-size=\"42\" font-weight=\"700\">BLAST INFO &amp; TECH</text>
<text x=\"130\" y=\"360\" fill=\"#ffffff\" font-family=\"Arial, sans-serif\" font-size=\"86\" font-weight=\"700\">{title}</text>
<foreignObject x=\"130\" y=\"440\" width=\"820\" height=\"480\">
  <div xmlns=\"http://www.w3.org/1999/xhtml\" style=\"color:#ffffff;font-family:Arial,sans-serif;font-size:42px;line-height:1.35;\">{copy_text}</div>
</foreignObject>
<text x=\"130\" y=\"1620\" fill=\"#9ed8e2\" font-family=\"Arial, sans-serif\" font-size=\"28\">Prompt base:</text>
<foreignObject x=\"130\" y=\"1658\" width=\"820\" height=\"120\">
  <div xmlns=\"http://www.w3.org/1999/xhtml\" style=\"color:#d4edf2;font-family:Arial,sans-serif;font-size:24px;line-height:1.35;\">{prompt_excerpt}</div>
</foreignObject>
</svg>"""
    return svg.encode("utf-8")


def generate_image_asset(
    version: StoryVersion,
    guide: BrandGuide,
    change_request: str = "",
) -> tuple[str, ContentFile, str, str]:
    final_prompt = _render_template(
        guide.image_prompt_template,
        brand_name=guide.name,
        brand_summary=guide.brand_summary,
        visual_rules=guide.visual_rules,
        visual_direction=version.visual_direction or "Sem direcao visual.",
        image_prompt=version.image_prompt or "Sem prompt base.",
        change_request=change_request or "Sem ajustes adicionais.",
    )

    client = _get_client()
    if client is None:
        file_name = f"story-v{version.version_number or 'draft'}.svg"
        return file_name, ContentFile(_placeholder_svg(version, final_prompt)), final_prompt, "placeholder-svg"

    try:
        result = client.images.generate(
            model=settings.OPENAI_IMAGE_MODEL,
            prompt=final_prompt,
            size="1024x1536",
        )
        raw_image = base64.b64decode(result.data[0].b64_json)
        file_name = f"story-v{version.version_number or 'draft'}.png"
        return file_name, ContentFile(raw_image), final_prompt, settings.OPENAI_IMAGE_MODEL
    except Exception as exc:
        logger.exception("Failed to generate image asset: %s", exc)
        file_name = f"story-v{version.version_number or 'draft'}.svg"
        return file_name, ContentFile(_placeholder_svg(version, final_prompt)), final_prompt, "placeholder-svg"
