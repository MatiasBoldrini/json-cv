"""
Generador de cold emails personalizados usando LLM.
Genera emails para 3 escenarios: HR, CEO, y Prospección.
"""

from pathlib import Path

from agent.config import CONTEXT_FILE, SENDER_NAME, TEMPLATES_DIR
from agent.ai.llm_client import get_llm_client
from agent.utils.logger import log


def _load_template(template_name: str) -> str:
    """Carga un template de email desde el directorio de templates."""
    path = TEMPLATES_DIR / template_name
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _load_context_summary() -> str:
    """Carga un resumen del contexto para el LLM."""
    if CONTEXT_FILE.exists():
        return CONTEXT_FILE.read_text(encoding="utf-8")[:3000]
    return ""


def write_hr_email(
    job: dict,
    recipient_email: str = "",
    recipient_name: str = "",
) -> dict:
    """
    Genera un cold email para HR/Selección basado en una oferta laboral.

    Returns:
        dict con {subject, body_html, body_text}
    """
    llm = get_llm_client()
    template = _load_template("cold_email_hr.md")
    context = _load_context_summary()

    messages = [
        {
            "role": "system",
            "content": (
                "Sos un experto en cold emails para búsqueda laboral. "
                "Escribí un email profesional, conciso y personalizado para "
                "el departamento de RRHH/selección de la empresa.\n\n"
                f"GUÍA DE ESTILO:\n{template}\n\n"
                "REGLAS:\n"
                "- Máximo 150 palabras en el body\n"
                "- Tono profesional pero con personalidad\n"
                "- Mencionar 2-3 skills que matcheen con la oferta\n"
                "- Incluir call-to-action (disponibilidad para charlar)\n"
                "- Escribir en el idioma de la oferta (español por defecto)\n"
                "- NO usar frases genéricas tipo 'Estimados señores'\n"
                f"- Firmar como {SENDER_NAME}\n\n"
                "Respondé con un JSON: {\"subject\": \"...\", \"body_text\": \"...\", \"body_html\": \"...\"}\n"
                "El body_html debe ser HTML simple (p, strong, br, ul/li)."
            ),
        },
        {
            "role": "user",
            "content": (
                f"CONTEXTO DEL CANDIDATO:\n{context}\n\n"
                f"OFERTA LABORAL:\n"
                f"- Título: {job.get('title', 'N/A')}\n"
                f"- Empresa: {job.get('company', 'N/A')}\n"
                f"- Descripción: {job.get('description', 'N/A')[:1500]}\n\n"
                f"Destinatario: {recipient_name or 'Equipo de Selección'} ({recipient_email})\n\n"
                "Generá el email."
            ),
        },
    ]

    try:
        result = llm.chat_json(messages, temperature=0.6)
        log.info(f"  ✓ Email HR generado para {job.get('company', '?')}")
        return result
    except Exception as e:
        log.error(f"Error generando email HR: {e}")
        return _fallback_email(job, "hr")


def write_ceo_email(
    job: dict,
    ceo_name: str = "",
    ceo_email: str = "",
    company_info: str = "",
) -> dict:
    """
    Genera un cold email para el CEO/Fundador.
    Tono más personal, enfocado en valor de negocio.

    Returns:
        dict con {subject, body_html, body_text}
    """
    llm = get_llm_client()
    template = _load_template("cold_email_ceo.md")
    context = _load_context_summary()

    messages = [
        {
            "role": "system",
            "content": (
                "Sos un experto en cold emails de alto impacto. "
                "Escribí un email para el CEO/fundador de la empresa.\n\n"
                f"GUÍA DE ESTILO:\n{template}\n\n"
                "REGLAS:\n"
                "- Máximo 120 palabras en el body\n"
                "- Tono personal, no corporativo\n"
                "- Mostrar que investigaste la empresa\n"
                "- Enfocarse en VALOR que podés aportar\n"
                "- No pedir trabajo directamente, ofrecer valor\n"
                "- Escribir en español (mercado argentino)\n"
                f"- Firmar como {SENDER_NAME}\n\n"
                "Respondé con JSON: {\"subject\": \"...\", \"body_text\": \"...\", \"body_html\": \"...\"}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"CONTEXTO DEL CANDIDATO:\n{context}\n\n"
                f"EMPRESA:\n"
                f"- Nombre: {job.get('company', 'N/A')}\n"
                f"- Info: {company_info or job.get('description', 'N/A')[:500]}\n\n"
                f"CEO/Fundador: {ceo_name or 'el fundador'} ({ceo_email})\n\n"
                "Generá el email."
            ),
        },
    ]

    try:
        result = llm.chat_json(messages, temperature=0.6)
        log.info(f"  ✓ Email CEO generado para {job.get('company', '?')}")
        return result
    except Exception as e:
        log.error(f"Error generando email CEO: {e}")
        return _fallback_email(job, "ceo")


def write_prospect_email(
    company: dict,
    recipient_email: str = "",
    recipient_name: str = "",
) -> dict:
    """
    Genera un cold email para prospección (empresa sin oferta publicada).
    Este es el más personalizado.

    Returns:
        dict con {subject, body_html, body_text}
    """
    llm = get_llm_client()
    template = _load_template("cold_email_prospect.md")
    context = _load_context_summary()

    messages = [
        {
            "role": "system",
            "content": (
                "Sos un experto en cold emails para prospección laboral. "
                "Escribí un email personalizado para una empresa que NO publicó "
                "una oferta de trabajo, pero podría beneficiarse del perfil.\n\n"
                f"GUÍA DE ESTILO:\n{template}\n\n"
                "REGLAS:\n"
                "- Máximo 130 palabras en el body\n"
                "- Tono cercano, local (Mendoza), profesional\n"
                "- Mencionar algo específico de la empresa\n"
                "- No pedir trabajo directamente — ofrecer valor\n"
                "- Mencionar conexión local (comunidad tech, Cursor, CuyoConnect)\n"
                "- Siempre en español\n"
                f"- Firmar como {SENDER_NAME}\n\n"
                "Respondé con JSON: {\"subject\": \"...\", \"body_text\": \"...\", \"body_html\": \"...\"}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"CONTEXTO DEL CANDIDATO:\n{context}\n\n"
                f"EMPRESA OBJETIVO:\n"
                f"- Nombre: {company.get('name', 'N/A')}\n"
                f"- Sector: {company.get('sector', 'N/A')}\n"
                f"- URL: {company.get('url', 'N/A')}\n"
                f"- Ubicación: {company.get('location', 'Mendoza')}\n"
                f"- Ángulo sugerido: {company.get('email_angle', 'automatización e IA')}\n\n"
                f"Destinatario: {recipient_name or 'el equipo'} ({recipient_email})\n\n"
                "Generá el email."
            ),
        },
    ]

    try:
        result = llm.chat_json(messages, temperature=0.6)
        log.info(f"  ✓ Email prospect generado para {company.get('name', '?')}")
        return result
    except Exception as e:
        log.error(f"Error generando email prospect: {e}")
        return _fallback_prospect_email(company)


def _fallback_email(job: dict, email_type: str) -> dict:
    """Email de fallback si el LLM falla."""
    company = job.get("company", "la empresa")
    title = job.get("title", "la posición")

    return {
        "subject": f"Aplicación para {title} — {SENDER_NAME}",
        "body_text": (
            f"Hola,\n\n"
            f"Me contacto en relación a la posición de {title} en {company}. "
            f"Soy {SENDER_NAME}, Product Engineer con experiencia en IA, automatización "
            f"y desarrollo fullstack.\n\n"
            f"Adjunto mi CV para su consideración. Quedo a disposición para "
            f"coordinar una entrevista.\n\n"
            f"Saludos,\n{SENDER_NAME}"
        ),
        "body_html": (
            f"<p>Hola,</p>"
            f"<p>Me contacto en relación a la posición de <strong>{title}</strong> "
            f"en <strong>{company}</strong>. Soy {SENDER_NAME}, Product Engineer "
            f"con experiencia en IA, automatización y desarrollo fullstack.</p>"
            f"<p>Adjunto mi CV para su consideración. Quedo a disposición para "
            f"coordinar una entrevista.</p>"
            f"<p>Saludos,<br>{SENDER_NAME}</p>"
        ),
    }


def _fallback_prospect_email(company: dict) -> dict:
    """Email de fallback para prospección."""
    name = company.get("name", "la empresa")

    return {
        "subject": f"Propuesta de colaboración — {SENDER_NAME}",
        "body_text": (
            f"Hola,\n\n"
            f"Soy {SENDER_NAME}, Product Engineer de Mendoza especializado en "
            f"IA y automatización. Conozco el trabajo que hacen en {name} y me "
            f"encantaría explorar cómo podría aportar valor al equipo.\n\n"
            f"Adjunto mi CV. ¿Tendrían disponibilidad para una breve charla?\n\n"
            f"Saludos,\n{SENDER_NAME}"
        ),
        "body_html": (
            f"<p>Hola,</p>"
            f"<p>Soy <strong>{SENDER_NAME}</strong>, Product Engineer de Mendoza "
            f"especializado en IA y automatización. Conozco el trabajo que hacen "
            f"en <strong>{name}</strong> y me encantaría explorar cómo podría "
            f"aportar valor al equipo.</p>"
            f"<p>Adjunto mi CV. ¿Tendrían disponibilidad para una breve charla?</p>"
            f"<p>Saludos,<br>{SENDER_NAME}</p>"
        ),
    }
