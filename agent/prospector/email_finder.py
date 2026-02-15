"""
Buscador de emails para ofertas laborales.
Encuentra emails de HR y CEO de empresas que publicaron ofertas.
Combina múltiples estrategias: crawling, Hunter.io, y pattern guessing.
"""

import re
from urllib.parse import urlparse

from agent.prospector.email_crawler import (
    crawl_emails_from_website,
    enrich_with_hunter,
    verify_domain_mx,
    _classify_email,
    _is_valid_email,
)
from agent.utils.logger import log


# Patrones comunes de emails corporativos
EMAIL_PATTERNS = [
    "{first}@{domain}",
    "{first}.{last}@{domain}",
    "{first}{last}@{domain}",
    "{f}{last}@{domain}",
    "{first}_{last}@{domain}",
    "{first}-{last}@{domain}",
]


def _guess_email_patterns(first_name: str, last_name: str, domain: str) -> list[str]:
    """Genera variantes posibles de email basadas en patrones comunes."""
    if not first_name or not domain:
        return []

    first = first_name.lower().strip()
    last = last_name.lower().strip() if last_name else ""
    f = first[0] if first else ""

    candidates = []
    for pattern in EMAIL_PATTERNS:
        try:
            email = pattern.format(
                first=first, last=last, f=f, domain=domain
            )
            if _is_valid_email(email):
                candidates.append(email)
        except (KeyError, IndexError):
            continue

    return candidates


def _extract_email_from_job(job: dict) -> str | None:
    """Intenta extraer un email directamente del listing del job."""
    description = job.get("description", "")
    if not description:
        return None

    email_pattern = re.compile(
        r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
        re.IGNORECASE,
    )
    matches = email_pattern.findall(description)

    # Filtrar emails que probablemente son de contacto de la empresa
    for email in matches:
        email = email.lower()
        # Ignorar emails personales (gmail, hotmail, etc.)
        domain = email.split("@")[1]
        if domain in {"gmail.com", "hotmail.com", "outlook.com", "yahoo.com"}:
            continue
        return email

    return None


def find_job_emails(job: dict) -> dict:
    """
    Encuentra emails de HR y CEO para una oferta laboral.

    Estrategia:
    1. Extraer email directamente del listing
    2. Crawl del website de la empresa
    3. Hunter.io domain search (si hay key)
    4. Pattern guessing para el CEO

    Args:
        job: dict con datos del job (company, company_url, description, etc.)

    Returns:
        dict con {
            hr_email: str | None,
            ceo_email: str | None,
            ceo_name: str | None,
            all_emails: list[dict],
        }
    """
    company = job.get("company", "")
    company_url = job.get("company_url", "")
    result = {
        "hr_email": None,
        "ceo_email": None,
        "ceo_name": None,
        "all_emails": [],
    }

    log.info(f"Buscando emails para: {company}...")

    # 1. Email directo del listing
    listing_email = _extract_email_from_job(job)
    if listing_email:
        log.info(f"  → Email del listing: {listing_email}")
        result["hr_email"] = listing_email
        result["all_emails"].append({
            "email": listing_email,
            "type": _classify_email(listing_email),
            "source": "job_listing",
        })

    # 2. Crawl del website si hay URL
    if company_url and company_url.startswith("http"):
        website_emails = crawl_emails_from_website(company_url, max_pages=5)
        for e in website_emails:
            result["all_emails"].append({
                "email": e["email"],
                "type": e["type"],
                "source": "website_crawl",
            })
            # Usar el primer email corporativo como HR si no tenemos uno
            if not result["hr_email"] and e["type"] in ("corporate", "generic"):
                result["hr_email"] = e["email"]

    # 3. Hunter.io
    domain = ""
    if company_url:
        domain = urlparse(company_url).netloc.lower().replace("www.", "")
    elif result["hr_email"]:
        domain = result["hr_email"].split("@")[1]

    if domain:
        hunter_emails = enrich_with_hunter(domain)
        for e in hunter_emails:
            result["all_emails"].append({
                "email": e["email"],
                "type": e["type"],
                "source": "hunter.io",
                "name": f"{e.get('first_name', '')} {e.get('last_name', '')}".strip(),
                "position": e.get("position", ""),
            })

            # Buscar CEO/Fundador en resultados de Hunter
            position = e.get("position", "").lower()
            if any(title in position for title in [
                "ceo", "cto", "founder", "fundador", "director", "owner",
                "gerente general", "managing director",
            ]):
                result["ceo_email"] = e["email"]
                result["ceo_name"] = f"{e.get('first_name', '')} {e.get('last_name', '')}".strip()

            # Usar como HR si no tenemos
            if not result["hr_email"]:
                result["hr_email"] = e["email"]

    # Resumen
    total = len(result["all_emails"])
    log.info(
        f"  → {total} emails encontrados "
        f"(HR: {'✓' if result['hr_email'] else '✗'}, "
        f"CEO: {'✓' if result['ceo_email'] else '✗'})"
    )

    return result
