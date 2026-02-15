"""
Crawler de emails empresariales.
Crawlea websites de empresas para extraer todos los emails de contacto.
Usa extract-emails y verificación DNS (MX records).
"""

import re
import random
import time
from urllib.parse import urlparse

import requests
import dns.resolver

from agent.config import DELAY_BETWEEN_CRAWLS, HUNTER_API_KEY
from agent.utils.logger import log, summary


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

# Regex robusto para emails
EMAIL_REGEX = re.compile(
    r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
    re.IGNORECASE,
)

# Emails genéricos que son menos valiosos (pero aún útiles)
GENERIC_PREFIXES = {
    "info", "contacto", "contact", "ventas", "sales", "soporte", "support",
    "admin", "administracion", "rrhh", "hr", "empleo", "jobs", "careers",
    "no-reply", "noreply", "newsletter", "marketing", "prensa", "press",
    "hola", "hello", "webmaster",
}

# Dominios de email personales (no empresariales)
PERSONAL_DOMAINS = {
    "gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "live.com",
    "icloud.com", "protonmail.com", "aol.com", "mail.com",
}


def _is_valid_email(email: str) -> bool:
    """Validación básica de formato de email."""
    if not email or len(email) > 254:
        return False
    if not EMAIL_REGEX.fullmatch(email):
        return False
    # Filtrar emails con extensiones de archivos
    if any(email.lower().endswith(ext) for ext in [".png", ".jpg", ".gif", ".svg", ".css", ".js"]):
        return False
    return True


def _classify_email(email: str) -> str:
    """Clasifica un email como 'personal', 'generic', o 'corporate'."""
    local, domain = email.lower().split("@", 1)

    if domain in PERSONAL_DOMAINS:
        return "personal"

    if local in GENERIC_PREFIXES:
        return "generic"

    return "corporate"


def verify_domain_mx(domain: str) -> bool:
    """Verifica que un dominio tiene registros MX (puede recibir email)."""
    try:
        dns.resolver.resolve(domain, "MX")
        return True
    except Exception:
        return False


def crawl_emails_from_website(url: str, max_pages: int = 10) -> list[dict]:
    """
    Crawlea un website y extrae todos los emails encontrados.

    Args:
        url: URL base del sitio web
        max_pages: máximo de páginas a crawlear

    Returns:
        Lista de dicts {email, type, source_page, verified}
    """
    if not url or not url.startswith("http"):
        return []

    parsed = urlparse(url)
    base_domain = parsed.netloc.lower().replace("www.", "")

    found_emails = {}
    visited = set()
    to_visit = [url]

    # Páginas clave donde suelen estar los emails
    common_pages = [
        "/contacto", "/contact", "/about", "/nosotros", "/equipo",
        "/team", "/about-us", "/sobre-nosotros", "/empresa",
    ]
    for page in common_pages:
        candidate = f"{parsed.scheme}://{parsed.netloc}{page}"
        if candidate not in to_visit:
            to_visit.append(candidate)

    pages_crawled = 0

    while to_visit and pages_crawled < max_pages:
        current_url = to_visit.pop(0)
        if current_url in visited:
            continue
        visited.add(current_url)

        try:
            resp = requests.get(
                current_url, headers=HEADERS, timeout=10, allow_redirects=True
            )
            if resp.status_code != 200:
                continue

            html = resp.text
            pages_crawled += 1

            # Extraer emails del HTML
            emails_in_page = EMAIL_REGEX.findall(html)

            for email in emails_in_page:
                email = email.lower().strip()
                if not _is_valid_email(email):
                    continue
                if email not in found_emails:
                    found_emails[email] = {
                        "email": email,
                        "type": _classify_email(email),
                        "source_page": current_url,
                        "verified": False,
                    }

            # Extraer links internos para seguir crawleando
            link_pattern = re.compile(
                r'href=["\']([^"\']+)["\']', re.IGNORECASE
            )
            for match in link_pattern.finditer(html):
                link = match.group(1)
                # Solo seguir links del mismo dominio
                if link.startswith("/"):
                    link = f"{parsed.scheme}://{parsed.netloc}{link}"
                elif not link.startswith("http"):
                    continue

                link_domain = urlparse(link).netloc.lower().replace("www.", "")
                if link_domain == base_domain and link not in visited:
                    to_visit.append(link)

        except Exception:
            continue

        # Pequeño delay entre requests
        time.sleep(random.uniform(0.5, 1.5))

    return list(found_emails.values())


def enrich_with_hunter(domain: str) -> list[dict]:
    """
    Usa Hunter.io API para encontrar emails adicionales del dominio.
    Requiere HUNTER_API_KEY configurado.

    Returns:
        Lista de dicts con emails encontrados
    """
    if not HUNTER_API_KEY:
        return []

    try:
        resp = requests.get(
            "https://api.hunter.io/v2/domain-search",
            params={"domain": domain, "api_key": HUNTER_API_KEY},
            timeout=10,
        )
        if resp.status_code != 200:
            return []

        data = resp.json()
        emails = []

        for entry in data.get("data", {}).get("emails", []):
            email = entry.get("value", "")
            if email and _is_valid_email(email):
                emails.append({
                    "email": email.lower(),
                    "type": _classify_email(email.lower()),
                    "source_page": f"hunter.io/{domain}",
                    "verified": entry.get("verification", {}).get("status") == "valid",
                    "first_name": entry.get("first_name", ""),
                    "last_name": entry.get("last_name", ""),
                    "position": entry.get("position", ""),
                })

        return emails

    except Exception as e:
        log.warning(f"Error con Hunter.io para {domain}: {e}")
        return []


def crawl_company_emails(company: dict) -> list[dict]:
    """
    Proceso completo de extracción de emails para una empresa.

    Args:
        company: dict con al menos 'name' y 'url'

    Returns:
        Lista de emails encontrados (actualizados en el dict)
    """
    url = company.get("url", "")
    name = company.get("name", "?")

    if not url:
        log.info(f"  {name}: sin URL, saltando crawl")
        return []

    log.info(f"Crawleando emails de: {name} ({url})...")

    all_emails = {}

    # 1. Crawl del website
    website_emails = crawl_emails_from_website(url)
    for e in website_emails:
        all_emails[e["email"]] = e

    # 2. Enriquecer con Hunter.io si hay key
    domain = urlparse(url).netloc.lower().replace("www.", "")
    if domain and HUNTER_API_KEY:
        hunter_emails = enrich_with_hunter(domain)
        for e in hunter_emails:
            if e["email"] not in all_emails:
                all_emails[e["email"]] = e

    # 3. Verificar dominios MX
    for email_data in all_emails.values():
        email_domain = email_data["email"].split("@")[1]
        if not email_data.get("verified"):
            email_data["verified"] = verify_domain_mx(email_domain)

    emails = list(all_emails.values())

    # Ordenar: corporativos verificados primero, genéricos después
    emails.sort(key=lambda e: (
        0 if e["type"] == "corporate" and e["verified"] else
        1 if e["type"] == "generic" and e["verified"] else
        2 if e["type"] == "corporate" else
        3
    ))

    if emails:
        summary.emails_extracted += len(emails)
        log.info(f"  → {len(emails)} emails encontrados")
        for e in emails[:3]:
            log.info(f"    {e['email']} ({e['type']}, {'✓' if e['verified'] else '?'})")
    else:
        log.info(f"  → 0 emails encontrados")

    summary.companies_crawled += 1
    return emails


def crawl_all_companies(companies: list[dict]) -> list[dict]:
    """
    Crawlea emails de todas las empresas.
    Modifica las empresas in-place agregando los emails.

    Returns:
        Las empresas actualizadas con emails
    """
    log.info(f"Crawleando emails de {len(companies)} empresas...")

    for i, company in enumerate(companies):
        if company.get("emails"):
            log.info(f"  {company['name']}: ya tiene emails, saltando")
            continue

        emails = crawl_company_emails(company)
        company["emails"] = emails

        # Delay entre crawls
        if i < len(companies) - 1:
            delay = random.uniform(*DELAY_BETWEEN_CRAWLS)
            time.sleep(delay)

    companies_with_emails = sum(1 for c in companies if c.get("emails"))
    log.info(
        f"Crawl completo: {companies_with_emails}/{len(companies)} "
        f"empresas con emails"
    )

    return companies
