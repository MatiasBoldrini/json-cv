"""
Scraper multi-portal de ofertas laborales usando python-jobspy.
Busca en LinkedIn, Indeed, Glassdoor y Google Jobs.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path

from agent.config import (
    DEFAULT_LOCATIONS,
    DEFAULT_RESULTS_PER_SITE,
    DEFAULT_SEARCH_TERMS,
    DEFAULT_RELEVANCE_THRESHOLD,
    JOBS_FILE,
    CONTEXT_FILE,
)
from agent.utils.logger import log, summary
from agent.ai.llm_client import get_llm_client


def _job_id(url: str) -> str:
    """Genera un ID único basado en la URL del job."""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def scrape_jobs(
    search_terms: list[str] | None = None,
    locations: list[str] | None = None,
    results_per_site: int | None = None,
    sites: list[str] | None = None,
) -> list[dict]:
    """
    Scrapea ofertas laborales de múltiples portales.
    Retorna lista de jobs normalizados.
    """
    from jobspy import scrape_jobs as jobspy_scrape

    search_terms = search_terms or DEFAULT_SEARCH_TERMS
    locations = locations or DEFAULT_LOCATIONS
    results_per_site = results_per_site or DEFAULT_RESULTS_PER_SITE
    sites = sites or ["indeed", "linkedin", "glassdoor", "google"]

    all_jobs = []
    seen_urls = set()

    for term in search_terms:
        for location in locations:
            log.info(f"Buscando '{term}' en {location}...")
            try:
                df = jobspy_scrape(
                    site_name=sites,
                    search_term=term,
                    location=location,
                    results_wanted=results_per_site,
                    country_indeed="Argentina",
                )

                if df is None or df.empty:
                    log.info(f"  → 0 resultados")
                    continue

                count = 0
                for _, row in df.iterrows():
                    url = str(row.get("job_url", ""))
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)

                    job = {
                        "id": _job_id(url),
                        "title": str(row.get("title", "")),
                        "company": str(row.get("company_name", "")),
                        "location": str(row.get("location", "")),
                        "description": str(row.get("description", ""))[:5000],
                        "url": url,
                        "source": str(row.get("site", "")),
                        "date_posted": str(row.get("date_posted", "")),
                        "job_type": str(row.get("job_type", "")),
                        "salary_min": row.get("min_amount") if row.get("min_amount") else None,
                        "salary_max": row.get("max_amount") if row.get("max_amount") else None,
                        "company_url": str(row.get("company_url", "")),
                        "easy_apply": bool(row.get("is_remote", False)),
                        "scraped_at": datetime.now().isoformat(),
                        "relevance_score": None,
                        "relevance_reason": None,
                    }
                    all_jobs.append(job)
                    count += 1

                log.info(f"  → {count} jobs nuevos")

            except Exception as e:
                log.error(f"Error scrapeando '{term}' en {location}: {e}")
                summary.add_error(f"Scraping failed: {term} @ {location}: {str(e)[:100]}")

    summary.jobs_found = len(all_jobs)
    log.info(f"Total: {len(all_jobs)} jobs únicos encontrados")
    return all_jobs


def filter_jobs_by_relevance(
    jobs: list[dict],
    threshold: int | None = None,
) -> list[dict]:
    """
    Usa el LLM para puntuar la relevancia de cada job respecto al perfil.
    Filtra los que están por debajo del threshold.
    """
    threshold = threshold or DEFAULT_RELEVANCE_THRESHOLD
    llm = get_llm_client()

    # Cargar contexto resumido
    context_summary = ""
    if CONTEXT_FILE.exists():
        full_context = CONTEXT_FILE.read_text(encoding="utf-8")
        # Usar solo las primeras ~2000 chars del contexto para el filtro
        context_summary = full_context[:2000]

    log.info(f"Filtrando {len(jobs)} jobs por relevancia (threshold: {threshold})...")

    # Procesar en batches de 5 para eficiencia
    batch_size = 5
    for i in range(0, len(jobs), batch_size):
        batch = jobs[i:i + batch_size]
        jobs_text = ""
        for idx, job in enumerate(batch):
            jobs_text += (
                f"\n--- JOB {idx + 1} ---\n"
                f"Título: {job['title']}\n"
                f"Empresa: {job['company']}\n"
                f"Ubicación: {job['location']}\n"
                f"Descripción: {job['description'][:500]}\n"
            )

        messages = [
            {
                "role": "system",
                "content": (
                    "Sos un evaluador de ofertas laborales. Evaluá cada oferta "
                    "respecto al perfil del candidato y dá un puntaje de relevancia 0-100.\n"
                    "Respondé SOLO con un JSON array con objetos {\"index\": N, \"score\": N, \"reason\": \"...\"}.\n"
                    "Score guide: 80-100 = match excelente, 60-79 = buen match, "
                    "40-59 = match parcial, 0-39 = poco relevante."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"PERFIL DEL CANDIDATO:\n{context_summary}\n\n"
                    f"OFERTAS A EVALUAR:{jobs_text}"
                ),
            },
        ]

        try:
            result = llm.chat_json(messages, temperature=0.2)
            # Puede ser una lista directa o un dict con una key
            if isinstance(result, dict):
                result = result.get("jobs", result.get("results", [result]))
            if not isinstance(result, list):
                result = [result]

            for item in result:
                idx = int(item.get("index", 1)) - 1
                if 0 <= idx < len(batch):
                    batch[idx]["relevance_score"] = int(item.get("score", 0))
                    batch[idx]["relevance_reason"] = str(item.get("reason", ""))

        except Exception as e:
            log.error(f"Error evaluando batch de relevancia: {e}")
            # Si falla, dar score medio a todos del batch
            for job in batch:
                if job["relevance_score"] is None:
                    job["relevance_score"] = 50
                    job["relevance_reason"] = "Score por defecto (error en evaluación)"

        summary.jobs_filtered += len(batch)

    # Filtrar por threshold
    relevant = [j for j in jobs if (j.get("relevance_score") or 0) >= threshold]
    relevant.sort(key=lambda j: j.get("relevance_score", 0), reverse=True)

    summary.jobs_relevant = len(relevant)
    log.info(
        f"Filtrado: {len(relevant)} jobs relevantes de {len(jobs)} "
        f"(threshold: {threshold})"
    )

    for job in relevant[:5]:
        log.info(
            f"  ★ [{job['relevance_score']}] {job['title']} @ {job['company']}"
        )

    return relevant


def save_jobs(jobs: list[dict], filepath: Path | None = None):
    """Guarda los jobs en un archivo JSON."""
    filepath = filepath or JOBS_FILE
    filepath.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "scraped_at": datetime.now().isoformat(),
        "total": len(jobs),
        "jobs": jobs,
    }
    filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info(f"Jobs guardados en {filepath} ({len(jobs)} jobs)")


def load_jobs(filepath: Path | None = None) -> list[dict]:
    """Carga jobs desde el cache JSON."""
    filepath = filepath or JOBS_FILE
    if not filepath.exists():
        log.warning(f"No se encontró cache de jobs en {filepath}")
        return []

    data = json.loads(filepath.read_text(encoding="utf-8"))
    jobs = data.get("jobs", [])
    log.info(f"Cargados {len(jobs)} jobs desde cache ({data.get('scraped_at', 'unknown')})")
    return jobs
