"""
Scraper de empresas de Mendoza desde directorios conocidos.
Polo TIC, Catálogo Competitividad, Chacras Park, y Google.
"""

import hashlib
import json
import re
import time
import random
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

from agent.config import (
    COMPANIES_FILE,
    DELAY_BETWEEN_CRAWLS,
    SEED_COMPANIES_FILE,
)
from agent.utils.logger import log, summary


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
}


def _company_id(name: str, url: str) -> str:
    """Genera un ID único para una empresa."""
    key = f"{name.lower().strip()}:{urlparse(url).netloc}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def _extract_domain(url: str) -> str:
    """Extrae el dominio limpio de una URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower().replace("www.", "")
    except Exception:
        return ""


def _fetch_page(url: str, timeout: int = 15) -> str | None:
    """Descarga el HTML de una URL."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        log.warning(f"Error descargando {url}: {e}")
        return None


def scrape_polo_tic(url: str = "https://poloticmendoza.org/pages/socios.php") -> list[dict]:
    """Scrapea el directorio de socios del Polo TIC Mendoza."""
    log.info("Scrapeando Polo TIC Mendoza...")
    companies = []

    html = _fetch_page(url)
    if not html:
        log.warning("No se pudo acceder al Polo TIC")
        return companies

    # Buscar links y nombres de empresas
    # Patrón genérico para extraer links con texto
    link_pattern = re.compile(
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>',
        re.IGNORECASE,
    )

    for match in link_pattern.finditer(html):
        href, text = match.group(1), match.group(2).strip()
        if not text or len(text) < 3:
            continue

        # Filtrar links internos del sitio y de navegación
        if any(skip in href.lower() for skip in [
            "poloticmendoza.org", "#", "javascript:", "mailto:",
            "facebook.com", "twitter.com", "instagram.com", "linkedin.com/company",
        ]):
            continue

        full_url = href if href.startswith("http") else urljoin(url, href)

        companies.append({
            "name": text,
            "url": full_url,
            "source": "polo_tic",
            "sector": "technology",
            "location": "Mendoza",
        })

    # También buscar nombres de empresas en texto plano
    # Muchos directorios muestran empresas en divs sin links
    name_patterns = re.findall(
        r'<(?:h[2-4]|strong|b|div[^>]*class="[^"]*(?:empresa|company|socio|partner)[^"]*")[^>]*>([^<]{3,60})</(?:h[2-4]|strong|b|div)>',
        html,
        re.IGNORECASE,
    )
    for name in name_patterns:
        name = name.strip()
        if name and not any(c["name"] == name for c in companies):
            companies.append({
                "name": name,
                "url": "",
                "source": "polo_tic",
                "sector": "technology",
                "location": "Mendoza",
            })

    log.info(f"  → {len(companies)} empresas del Polo TIC")
    return companies


def scrape_competitividad_mendoza(
    url: str = "https://competitividadmendoza.com.ar/agencia-innovacion/catalogo-empresas/"
) -> list[dict]:
    """Scrapea el catálogo de empresas tecnológicas de Competitividad Mendoza."""
    log.info("Scrapeando Catálogo Competitividad Mendoza...")
    companies = []

    html = _fetch_page(url)
    if not html:
        log.warning("No se pudo acceder al catálogo de Competitividad Mendoza")
        return companies

    # Extraer empresas del catálogo (links y nombres)
    link_pattern = re.compile(
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>',
        re.IGNORECASE,
    )

    for match in link_pattern.finditer(html):
        href, text = match.group(1), match.group(2).strip()
        if not text or len(text) < 3:
            continue
        if any(skip in href.lower() for skip in [
            "competitividadmendoza", "#", "javascript:", "mailto:",
        ]):
            continue

        full_url = href if href.startswith("http") else urljoin(url, href)

        companies.append({
            "name": text,
            "url": full_url,
            "source": "competitividad_mendoza",
            "sector": "technology",
            "location": "Mendoza",
        })

    log.info(f"  → {len(companies)} empresas del catálogo")
    return companies


def load_seed_companies() -> list[dict]:
    """Carga las empresas seed desde el archivo JSON."""
    if not SEED_COMPANIES_FILE.exists():
        log.warning("No se encontró seed_companies.json")
        return []

    data = json.loads(SEED_COMPANIES_FILE.read_text(encoding="utf-8"))
    companies = []

    for company in data.get("known_companies", []):
        companies.append({
            "name": company["name"],
            "url": company.get("url", ""),
            "source": "seed",
            "sector": company.get("sector", "technology"),
            "location": company.get("location", "Mendoza"),
        })

    log.info(f"  → {len(companies)} empresas del seed")
    return companies


def scrape_all_companies(skip_web: bool = False) -> list[dict]:
    """
    Recopila empresas de todas las fuentes disponibles.

    Args:
        skip_web: si True, solo carga seed sin scrapear web

    Returns:
        Lista de empresas deduplicadas
    """
    all_companies = []

    # 1. Cargar seed companies siempre
    all_companies.extend(load_seed_companies())

    # 2. Scrapear directorios web
    if not skip_web:
        time.sleep(random.uniform(*DELAY_BETWEEN_CRAWLS))
        all_companies.extend(scrape_polo_tic())

        time.sleep(random.uniform(*DELAY_BETWEEN_CRAWLS))
        all_companies.extend(scrape_competitividad_mendoza())

    # 3. Deduplicar por dominio o nombre
    seen = set()
    unique = []
    for company in all_companies:
        domain = _extract_domain(company["url"]) if company["url"] else ""
        key = domain or company["name"].lower().strip()

        if key and key not in seen:
            seen.add(key)
            company["id"] = _company_id(company["name"], company.get("url", ""))
            company["emails"] = []
            company["relevance_score"] = None
            company["relevance_reason"] = None
            company["contacted"] = False
            company["description"] = ""
            unique.append(company)

    summary.companies_found = len(unique)
    log.info(f"Total: {len(unique)} empresas únicas recopiladas")
    return unique


def save_companies(companies: list[dict], filepath: Path | None = None):
    """Guarda las empresas en un archivo JSON."""
    filepath = filepath or COMPANIES_FILE
    filepath.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "scraped_at": datetime.now().isoformat(),
        "total": len(companies),
        "companies": companies,
    }
    filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info(f"Empresas guardadas en {filepath}")


def load_companies(filepath: Path | None = None) -> list[dict]:
    """Carga empresas desde el cache JSON."""
    filepath = filepath or COMPANIES_FILE
    if not filepath.exists():
        log.warning(f"No se encontró cache de empresas en {filepath}")
        return []

    data = json.loads(filepath.read_text(encoding="utf-8"))
    companies = data.get("companies", [])
    log.info(f"Cargadas {len(companies)} empresas desde cache")
    return companies
