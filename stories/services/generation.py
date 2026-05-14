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


PRICE_CONTEXT_PATTERN = re.compile(
    r"(R\$\s*[\d\.,]+|\b\d{1,2}x\b|\bx\s*de\b|\bsem juros\b|\bparcelad[oa]\b|\bà vista\b|\ba vista\b)",
    flags=re.IGNORECASE,
)


BLAST_VISUAL_IDENTITY_PROMPT = dedent(
    """
    Manual Oficial de Identidade Visual para Geração de Imagens IA - BLAST INFO & TECH.

    A BLAST deve comunicar autoridade em tecnologia, oferta confiável, preço competitivo, modernidade, clareza comercial, performance, compra inteligente e aparência premium acessível. Toda peça precisa parecer criada por uma empresa séria, dominante no segmento local e altamente especializada.

    DNA visual: minimalismo comercial de alta conversão, mistura de clean design, retail premium, tecnologia corporativa, e-commerce moderno e campanha Meta Ads de alta performance. A BLAST não deve parecer loja amadora, banner poluído, arte genérica de marketplace, criativo barato ou visual gamer infantilizado fora de campanhas gamer específicas.

    Estrutura promocional: headline impactante no topo, oferta ou benefício principal, produto centralizado, especificações rápidas, preço dominante, provas de valor e marca no rodapé. Produto sempre como hero visual, com recorte limpo, sombra suave, reflexos discretos, iluminação profissional e nitidez alta.

    Paleta: roxo institucional #6E2BC3, roxo vibrante #7A22FF, roxo escuro #4A0D91, lilás #C8A7FF, preto premium #120018, grafite, branco limpo e cinza de fundo. Roxo deve aparecer em headlines, bordas, preços, selos, ícones e destaques.

    Tipografia: sans-serif moderna, pesada e geométrica, similar a Montserrat ExtraBold, League Spartan, Gotham Bold, Nexa Heavy, Inter Bold ou Poppins Bold. Headline gigante e forte; preço como maior elemento comercial; especificações claras e de leitura instantânea.

    Fundo: limpo e tecnológico, com geometrias suaves, linhas conectadas, pontos abstratos, colunas desfocadas ou ambientes corporativos blur. Nunca usar fundo poluído, texturas pesadas, cores gritantes ou cenários bagunçados.

    Qualidade esperada: arte de agência profissional, marca consolidada, campanha de alta verba, visual pronto para escalar anúncios. Se remover logo e nome da marca, a peça ainda precisa parecer BLAST por roxo dominante, fundo clean, tipografia forte, produto hero, layout organizado e oferta clara.
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
    layout_summary: str
    manual: str
    master_prompt: str


BLAST_GUIDE = BrandSystem(
    label="BLAST",
    company_name="BLAST INFO & TECH",
    primary="#6E2BC3",
    accent="#7A22FF",
    dark="#120018",
    light="#FFFFFF",
    layout_summary="minimalismo comercial premium, roxo dominante, produto hero centralizado, layout clean de alta conversao",
    manual=BLAST_VISUAL_IDENTITY_PROMPT,
    master_prompt=(
        "Create a premium Brazilian computer store advertisement for BLAST INFO & TECH, vertical social media format, "
        "clean light gray background with subtle futuristic tech elements, bold geometric sans-serif typography, "
        "strong purple brand identity, giant headline at top, dominant promotional price box, realistic centered product with studio lighting and soft shadows."
    ),
)

BETA_GUIDE = BrandSystem(
    label="BETA",
    company_name="Beta Informática",
    primary="#0077D9",
    accent="#0066CC",
    dark="#111111",
    light="#FFFFFF",
    layout_summary="varejo de informatica mobile-first, azul corporativo forte, preco extremamente dominante, produto central e fundo corporativo desfocado",
    manual=dedent(
        """
        Guia Mestre de Direção Visual - DNA Visual das Artes Promocionais Beta Informática.

        Objetivo: criar peças com forte apelo comercial, conversão rápida em redes sociais, clareza extrema de leitura, destaque agressivo de preço, aparência tecnológica e profissional, estrutura modular replicável e alta performance mobile-first. A leitura principal deve acontecer em menos de 3 segundos e comunicar promoção, oportunidade, confiança, tecnologia, custo-benefício e profissionalismo.

        Categoria visual: varejo de informática, marketplace premium popular, promoção corporativa, tecnologia comercial, comunicação de feed social e loja física regional. A estética deve ser limpa, objetiva, comercial, moderna, funcional e altamente escaneável.

        Estrutura fixa: HEADLINE PROMOCIONAL, SUBTÍTULO OU BENEFÍCIO, PREÇO PRINCIPAL, PRODUTO EM DESTAQUE, ESPECIFICAÇÕES e RODAPÉ INSTITUCIONAL. O formato oficial é vertical 4:5, otimizado para Instagram Feed, Facebook Feed, Marketplace e Ads Mobile.

        Hierarquia de atenção: PROMOÇÃO, PREÇO, PRODUTO, BENEFÍCIO, ESPECIFICAÇÕES e MARCA. Usar escala tipográfica, contraste, peso visual, centralização, cor e espaçamento para guiar a leitura.

        Composição: blocos grandes e modulares. Topo com headline promocional. Subhead com benefício principal e especificação resumida. Área central com produto, preço e elementos de destaque. Base com especificações, CTA institucional e reforço comercial.

        Fundo: nunca competir com o produto. Usar loja de informática, showroom, escritório, ambiente corporativo ou espaço comercial com gaussian blur forte, baixa nitidez, opacidade reduzida, baixo contraste e aparência clean. Paleta de fundo: branco acinzentado, off-white, cinza claro e cinza frio.

        Paleta: azul corporativo dominante transmitindo tecnologia, confiança, segurança, profissionalismo e varejo moderno. Usar azul em caixas promocionais, boxes de preço, rodapés, CTAs, destaques e headlines. Tons aproximados: #0077D9, #0066CC, #0A5DBB. Branco para preços e títulos sobre azul. Preto para headlines secundárias, subtítulos e especificações. Cinza para fundo, sombras e profundidade. Madeira clara pode aparecer como base física clean, horizontal, pouco saturada e com baixa presença visual.

        Tipografia: sans-serif moderna, referência Montserrat, Gotham, Poppins, Anton ou Arial Rounded em casos específicos. Predominar caixa alta, bold agressivo, alta legibilidade, pouco ornamento, espaçamento controlado e leitura mobile-first. Promoção: ultra bold, branco sobre azul, caixa alta. Preço: destacado, branco, peso pesado e leitura instantânea, mas em escala equilibrada com o restante do layout. Produto: preto, bold médio, centralizado. Especificações: menor escala, alta legibilidade e múltiplas linhas curtas.

        Ajuste obrigatório de composição: o preço deve ter destaque comercial claro, mas não pode dominar exageradamente a peça nem ocupar área visual excessiva. Ele deve ser relevante sem roubar o protagonismo do produto e da hierarquia geral. Prefira caixa de preço equilibrada, legível e proporcional ao layout.

        Destaque visual das informações: sempre que fizer sentido, apresentar benefícios e especificações relevantes com apoio de ícones visuais simples, limpos e coerentes com tecnologia e varejo corporativo, sem excesso de elementos e sem transformar a arte em infográfico poluído.

        Boxes promocionais: cantos extremamente arredondados, gradiente azul, sombra suave e contraste forte. Box de preço é um elemento importante de conversão, com estrutura POR, R$, VALOR, ,00, À VISTA e PARCELAMENTO quando houver. O valor deve ter destaque, mas sem escala exagerada ou ocupação excessiva da peça.

        Produto: protagonista sempre. Grande escala, centralizado, alta nitidez, iluminação suave, recorte limpo, sombras suaves e profundidade realista. Evitar brilho exagerado, reflexos agressivos, glow, estética gamer e saturação excessiva.

        Rodapé institucional: faixa horizontal azul ocupando toda a largura, com gradiente azul, texto branco, centralização e forte contraste. Deve encerrar a peça com reforço comercial, resumo técnico ou CTA institucional.

        Linguagem visual: direta, comercial, objetiva, limpa, moderna e escaneável. A arte deve funcionar em leitura rápida, identificando instantaneamente promoção, preço, produto e categoria.

        Proibições: fundos poluídos, neon exagerado, RGB gamer, sombras pesadas, glow excessivo, gradientes agressivos, tipografia fina, excesso de elementos, excesso de cores, desalinhamentos, textos longos e ícones desnecessários.

        Fórmula ideal: topo com headline; subhead com benefício ou especificações rápidas; centro com produto e preço equilibrado; base com resumo e CTA institucional. DNA consolidado: varejo tecnológico, promoção direta, conversão rápida, estética limpa, mobile-first, produto protagonista, preço com destaque controlado, azul corporativo forte, tipografia bold, fundo desfocado clean, composição modular, contraste extremo e alta legibilidade.
        """
    ).strip(),
    master_prompt=(
        "Create a clean Brazilian computer store promotional ad for Beta Informatica, corporate blue visual identity, vertical social ad, "
        "aggressive promotional headline, balanced price box with strong but controlled emphasis, centered realistic product, clean blurred store or office background, bold sans-serif typography, simple tech icons to support relevant specs, and extremely clear commercial hierarchy, without logos or brand marks in the image."
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

    if project.content_type != StoryProject.ContentType.PROMOTIONAL and settings.OPENAI_API_KEY:
        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.responses.create(model=settings.OPENAI_TEXT_MODEL, input=prompt_snapshot)
            provider_response = response.output_text
            payload = parse_story_response(response.output_text, project, brand)
        except Exception as exc:  # noqa: BLE001
            provider_response = f"OpenAI text generation failed: {exc}"
    elif project.content_type == StoryProject.ContentType.PROMOTIONAL:
        provider_response = "Promotional concept grounded from project inputs to preserve the exact product, specs and price."

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


def generate_story_image_variant(concept: StoryConcept, target_format: str, variant_number: int) -> StoryImageVariant:
    brand = get_brand_system(concept.project.brand_mode)
    variant, _ = StoryImageVariant.objects.get_or_create(
        concept=concept,
        target_format=target_format,
        variant_number=variant_number,
    )
    prompt_snapshot = build_image_prompt(concept, brand, target_format, variant_number)
    provider_response = ""
    content = build_svg_placeholder(concept, brand, target_format, variant_number)
    mime_type = "image/svg+xml"
    filename = f"{target_format}-variant-{variant_number}.svg"

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
            filename = f"{target_format}-variant-{variant_number}.png"
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
    if project.content_type == StoryProject.ContentType.PROMOTIONAL:
        return build_promotional_concept_prompt(project, brand, latest)

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
        You are creating a commercial social media concept for {brand.company_name}.

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


def build_image_prompt(concept: StoryConcept, brand: BrandSystem, target_format: str, variant_number: int) -> str:
    project = concept.project
    format_label = dict(StoryProject.Format.choices).get(target_format, target_format)
    if project.content_type == StoryProject.ContentType.PROMOTIONAL:
        facts = promotional_source_facts(project)
        product_category = infer_product_category(facts)
        return dedent(
            f"""
            {brand.master_prompt}

            Brand mode: {project.get_brand_mode_display()}
            Layout summary: {brand.layout_summary}
            Output format: {format_label}
            Variation number: {variant_number} of {project.requested_image_count}
            Product category lock: {product_category}

            Locked commercial facts from the approved concept and project:
            - Headline exact: {concept.headline}
            - Subheadline exact: {concept.subheadline}
            - Body exact: {concept.body_text}
            - Price exact: {concept.price_text}
            - CTA exact: {concept.call_to_action}
            - Product/topic exact: {project.topic}
            - Source brief exact: {facts}
            - Approved visual direction: {concept.visual_direction}

            Hard rules:
            - Render the exact product category described in the locked facts. Never swap desktop for notebook, notebook for desktop, or invent another item.
            - Never invent, replace or alter brands, models, specs, capacities, product family or price.
            - Use only the exact approved text and price above. Do not paraphrase, shorten, expand or translate them.
            - The final image must contain the approved promotional text itself, with correct spelling and numbers.
            - Never add logos, brand marks, fake seals, fake UI labels or extra callouts.
            - Keep the product large, centered and commercially realistic.
            - Use a clean blurred environment and preserve legibility for headline, specs and price.
            """
        ).strip()

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
        Output format: {format_label}
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
    if project.content_type == StoryProject.ContentType.PROMOTIONAL:
        return build_promotional_payload(project, brand, latest)

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


def build_promotional_concept_prompt(project: StoryProject, brand: BrandSystem, latest: StoryConcept | None) -> str:
    facts = promotional_source_facts(project)
    previous_context = ""
    if latest:
        previous_context = dedent(
            f"""
            Previous approved promotional concept:
            - Headline: {latest.headline}
            - Subheadline: {latest.subheadline}
            - Body: {latest.body_text}
            - Price: {latest.price_text}
            - CTA: {latest.call_to_action}
            - Visual direction: {latest.visual_direction}
            """
        ).strip()

    return dedent(
        f"""
        Promotional concept generation for {brand.company_name}.

        Brand DNA:
        {brand.manual}

        Locked source facts. Never alter, swap or invent product family, specs or price:
        {facts}

        Topic exact: {project.topic}
        Promotional price exact: {project.promotional_price}
        CTA exact: {project.call_to_action}
        Adjustment request: {project.adjustment_request}

        {previous_context}

        Important: preserve the exact commercial facts from the source. You may only reorganize wording for hierarchy and readability. No substitutions.

        Return plain text in this exact format:
        HEADLINE: ...
        SUBHEADLINE: ...
        BODY: ...
        PRICE: ...
        CTA: ...
        VISUAL_DIRECTION: ...
        """
    ).strip()


def promotional_source_facts(project: StoryProject) -> str:
    parts = [part.strip() for part in [project.topic, project.custom_brief, project.promotional_price, project.call_to_action] if part and part.strip()]
    return "\n".join(parts)


def build_promotional_payload(project: StoryProject, brand: BrandSystem, latest: StoryConcept | None) -> dict:
    lines = [line.strip() for line in re.split(r"\n+", project.custom_brief or "") if line.strip()]
    headline_source = project.topic or project.title
    headline = normalize_short_line(headline_source, max_words=7, max_chars=70).upper()
    subheadline = normalize_short_line(lines[0] if lines else headline_source, max_words=12, max_chars=110)
    spec_lines = [line for line in lines if extract_price_text(line) == ""]
    body = " | ".join(spec_lines[:4]).strip() or subheadline
    price = extract_price_text(project.promotional_price) or extract_price_text(project.custom_brief) or "Consulte o valor"
    cta = (project.call_to_action or "Fale conosco agora").strip()
    refinement = f" Ajuste solicitado: {project.adjustment_request.strip()}" if project.adjustment_request.strip() else ""
    visual_direction = (
        f"Seguir o DNA {brand.label} com {brand.layout_summary}. Produto protagonista, preço com destaque controlado, hierarquia comercial limpa, ícones simples para apoiar informações relevantes e área segura para texto legível gerado na própria arte."
        f" Categoria do produto travada em {infer_product_category(promotional_source_facts(project))}."
        f"{refinement}"
    )
    return {
        "headline": headline,
        "subheadline": subheadline,
        "body_text": body[:220],
        "price_text": price,
        "call_to_action": cta[:140],
        "visual_direction": visual_direction,
    }


def normalize_short_line(text: str, max_words: int, max_chars: int) -> str:
    words = [word for word in re.split(r"\s+", text or "") if word]
    cleaned = " ".join(words[:max_words]).strip()
    return cleaned[:max_chars].strip(" -|,.;:")


def extract_price_text(text: str) -> str:
    if not text:
        return ""
    price_lines = extract_price_lines(text)
    if price_lines:
        return " | ".join(price_lines)
    match = re.search(r"R\$\s*[\d\.,]+(?:[^\n]*)", text, flags=re.IGNORECASE)
    return match.group(0).strip() if match else ""


def infer_product_category(text: str) -> str:
    lowered = (text or "").lower()
    if any(token in lowered for token in ["notebook", "laptop", "ideapad", "vivobook"]):
        return "notebook"
    if any(token in lowered for token in ["pc", "desktop", "gabinete", "rtx", "rx ", "geforce", "placa de video"]):
        return "desktop computer"
    if any(token in lowered for token in ["monitor"]):
        return "monitor"
    return "computer product"


def build_svg_placeholder(concept: StoryConcept, brand: BrandSystem, target_format: str, variant_number: int) -> bytes:
    width, height = canvas_for_format(target_format)
    headline = escape_xml(concept.headline[:52])
    subheadline = escape_xml(concept.subheadline[:90])
    body = escape_xml(concept.body_text[:180])
    price = escape_xml(concept.price_text or "Consulte")
    cta = escape_xml(concept.call_to_action or "Fale com a loja")
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


def escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )
