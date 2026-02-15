"""
Envío de emails via Resend API.
Soporta adjuntos (PDF del CV) y rate limiting.
"""

import random
import time
from pathlib import Path

import resend

from agent.config import (
    DELAY_BETWEEN_EMAILS,
    MAX_EMAILS_PER_RUN,
    RESEND_API_KEY,
    SENDER_EMAIL,
    SENDER_NAME,
)
from agent.utils.logger import log, summary


def _init_resend():
    """Inicializa el cliente de Resend."""
    if not RESEND_API_KEY:
        raise ValueError(
            "RESEND_API_KEY no configurado. "
            "Registrate gratis en https://resend.com"
        )
    resend.api_key = RESEND_API_KEY


def send_email(
    to: str,
    subject: str,
    body_html: str,
    body_text: str = "",
    attachment_path: Path | None = None,
    attachment_name: str = "CV-Matias-Boldrini.pdf",
    dry_run: bool = False,
) -> bool:
    """
    Envía un email via Resend API.

    Args:
        to: dirección de email del destinatario
        subject: asunto del email
        body_html: cuerpo en HTML
        body_text: cuerpo en texto plano (fallback)
        attachment_path: path al PDF para adjuntar
        attachment_name: nombre del archivo adjunto
        dry_run: si True, no envía realmente

    Returns:
        bool: True si se envió exitosamente
    """
    if dry_run:
        log.info(f"  [DRY-RUN] Email a {to}: {subject}")
        summary.emails_sent += 1
        return True

    _init_resend()

    try:
        params = {
            "from": f"{SENDER_NAME} <{SENDER_EMAIL}>",
            "to": [to],
            "subject": subject,
            "html": body_html,
            "reply_to": SENDER_EMAIL,
        }

        if body_text:
            params["text"] = body_text

        # Adjuntar PDF si existe
        if attachment_path and attachment_path.exists():
            params["attachments"] = [
                {
                    "filename": attachment_name,
                    "path": str(attachment_path.absolute()),
                    "content_type": "application/pdf",
                }
            ]

        result = resend.Emails.send(params)

        if result and result.get("id"):
            summary.emails_sent += 1
            log.info(f"  ✓ Email enviado a {to} (ID: {result['id']})")
            return True
        else:
            log.error(f"  ✗ Error enviando email a {to}: respuesta inesperada")
            return False

    except Exception as e:
        log.error(f"  ✗ Error enviando email a {to}: {e}")
        summary.add_error(f"Email send failed to {to}: {str(e)[:100]}")
        return False


def send_job_emails(
    job: dict,
    emails: dict,
    pdf_path: Path | None = None,
    dry_run: bool = False,
) -> dict:
    """
    Envía emails para una oferta laboral (HR + CEO).

    Args:
        job: datos del job
        emails: dict con {hr_email, hr_subject, hr_html, hr_text,
                          ceo_email, ceo_subject, ceo_html, ceo_text}
        pdf_path: path al PDF adaptado
        dry_run: no enviar realmente

    Returns:
        dict con resultados {hr_sent: bool, ceo_sent: bool}
    """
    results = {"hr_sent": False, "ceo_sent": False}
    company = job.get("company", "empresa")
    safe_name = company.replace(" ", "-").lower()[:30]
    attachment_name = f"CV-Matias-Boldrini-{safe_name}.pdf"

    # Email a HR
    if emails.get("hr_email"):
        log.info(f"Enviando email HR a {emails['hr_email']}...")
        results["hr_sent"] = send_email(
            to=emails["hr_email"],
            subject=emails.get("hr_subject", f"Aplicación — {SENDER_NAME}"),
            body_html=emails.get("hr_html", ""),
            body_text=emails.get("hr_text", ""),
            attachment_path=pdf_path,
            attachment_name=attachment_name,
            dry_run=dry_run,
        )

        # Delay entre emails a la misma empresa
        if emails.get("ceo_email"):
            delay = random.uniform(5, 15)
            time.sleep(delay)

    # Email al CEO
    if emails.get("ceo_email"):
        log.info(f"Enviando email CEO a {emails['ceo_email']}...")
        results["ceo_sent"] = send_email(
            to=emails["ceo_email"],
            subject=emails.get("ceo_subject", f"Propuesta — {SENDER_NAME}"),
            body_html=emails.get("ceo_html", ""),
            body_text=emails.get("ceo_text", ""),
            attachment_path=pdf_path,
            attachment_name=attachment_name,
            dry_run=dry_run,
        )

    return results


def send_prospect_emails(
    company: dict,
    email_content: dict,
    pdf_path: Path | None = None,
    dry_run: bool = False,
) -> list[str]:
    """
    Envía emails de prospección a todos los emails de una empresa.

    Args:
        company: datos de la empresa (con field 'emails')
        email_content: dict con {subject, body_html, body_text}
        pdf_path: path al PDF adaptado
        dry_run: no enviar realmente

    Returns:
        lista de emails a los que se envió exitosamente
    """
    company_emails = company.get("emails", [])
    if not company_emails:
        log.warning(f"  No hay emails para {company.get('name', '?')}")
        return []

    safe_name = company.get("name", "empresa").replace(" ", "-").lower()[:30]
    attachment_name = f"CV-Matias-Boldrini-{safe_name}.pdf"
    sent_to = []

    # Enviar a los primeros 3 emails (no spam masivo)
    for email_data in company_emails[:3]:
        email_addr = email_data if isinstance(email_data, str) else email_data.get("email", "")
        if not email_addr:
            continue

        success = send_email(
            to=email_addr,
            subject=email_content.get("subject", f"Propuesta — {SENDER_NAME}"),
            body_html=email_content.get("body_html", ""),
            body_text=email_content.get("body_text", ""),
            attachment_path=pdf_path,
            attachment_name=attachment_name,
            dry_run=dry_run,
        )

        if success:
            sent_to.append(email_addr)

        # Delay entre emails
        if company_emails.index(email_data) < len(company_emails) - 1:
            delay = random.uniform(*DELAY_BETWEEN_EMAILS)
            time.sleep(delay)

    return sent_to
