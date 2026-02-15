"""
Orquestador principal del pipeline de búsqueda de empleo automatizada.

Modos de operación:
  --mode apply     Aplica en portales con browser-use (IA que controla el browser)
  --mode email     Envía cold emails (HR + CEO) con CV adaptado
  --mode prospect  Deep research: crawlea empresas de Mendoza, extrae emails, envía
  --mode full      Los 3 modos juntos

Uso:
  python -m agent.main --mode apply --dry-run
  python -m agent.main --mode email --max 5
  python -m agent.main --mode prospect --skip-crawl
  python -m agent.main --mode full --dry-run --headed
"""

import argparse
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path

from agent.config import (
    APPLICATIONS_FILE,
    DATA_DIR,
    DEFAULT_RELEVANCE_THRESHOLD,
    DELAY_BETWEEN_APPLICATIONS,
    DELAY_BETWEEN_EMAILS,
    MAX_APPLICATIONS_PER_RUN,
    MAX_EMAILS_PER_RUN,
    ensure_data_dirs,
    validate_config,
)
from agent.utils.logger import log, summary


# ═══════════════════════════════════════════════
# Application Tracker (anti-duplicados)
# ═══════════════════════════════════════════════

def load_applications() -> list[dict]:
    """Carga el historial de aplicaciones."""
    if APPLICATIONS_FILE.exists():
        return json.loads(APPLICATIONS_FILE.read_text(encoding="utf-8"))
    return []


def save_applications(applications: list[dict]):
    """Guarda el historial de aplicaciones."""
    APPLICATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    APPLICATIONS_FILE.write_text(
        json.dumps(applications, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def is_already_processed(url_or_name: str, applications: list[dict]) -> bool:
    """Verifica si un job/empresa ya fue procesado."""
    for app in applications:
        if app.get("url") == url_or_name or app.get("target") == url_or_name:
            return True
    return False


def record_application(
    applications: list[dict],
    app_type: str,
    target: str,
    url: str,
    action: str,
    emails_sent_to: list[str] | None = None,
    notes: str = "",
):
    """Registra una aplicación en el historial."""
    applications.append({
        "type": app_type,
        "target": target,
        "url": url,
        "date": datetime.now().isoformat(),
        "action_taken": action,
        "emails_sent_to": emails_sent_to or [],
        "notes": notes,
    })
    save_applications(applications)


# ═══════════════════════════════════════════════
# Pipeline: Modo APPLY
# ═══════════════════════════════════════════════

def run_apply_pipeline(args):
    """Pipeline completo para aplicar en portales."""
    from agent.scraper.job_scraper import (
        scrape_jobs, filter_jobs_by_relevance, save_jobs, load_jobs,
    )
    from agent.ai.cv_adapter import adapt_cv_for_job
    from agent.pdf.generator import generate_pdf
    from agent.applier.agent import apply_to_job
    import asyncio

    applications = load_applications()

    # 1. Scrape o cargar cache
    if args.skip_scrape:
        jobs = load_jobs()
    else:
        search_terms = [args.search] if args.search else None
        locations = [args.location] if args.location else None
        jobs = scrape_jobs(search_terms=search_terms, locations=locations)
        save_jobs(jobs)

    if not jobs:
        log.warning("No se encontraron ofertas. Terminando.")
        return

    # 2. Filtrar por relevancia
    relevant_jobs = filter_jobs_by_relevance(jobs, threshold=args.min_score)

    if not relevant_jobs:
        log.warning("Ninguna oferta pasó el filtro de relevancia. Terminando.")
        return

    # 3. Procesar cada job
    max_apps = args.max or MAX_APPLICATIONS_PER_RUN
    processed = 0

    for job in relevant_jobs:
        if processed >= max_apps:
            log.info(f"Límite de {max_apps} aplicaciones alcanzado.")
            break

        # Anti-duplicados
        if is_already_processed(job["url"], applications):
            log.info(f"Ya aplicado: {job['title']} @ {job['company']}, saltando.")
            continue

        log.info(f"\n{'═' * 60}")
        log.info(f"APLICACIÓN {processed + 1}: {job['title']} @ {job['company']}")
        log.info(f"{'═' * 60}")

        # 3a. Adaptar CV
        adapted_cv = adapt_cv_for_job(job)

        # 3b. Generar PDF
        pdf_path = generate_pdf(adapted_cv, job["company"])
        if not pdf_path:
            record_application(
                applications, "job_apply", f"{job['title']} @ {job['company']}",
                job["url"], "failed", notes="PDF generation failed",
            )
            continue

        # 3c. Aplicar con browser-use
        success = asyncio.run(
            apply_to_job(
                job=job,
                pdf_path=pdf_path,
                headless=not args.headed,
                confirm=args.confirm,
                dry_run=args.dry_run,
            )
        )

        action = "applied" if success else "failed"
        if args.dry_run:
            action = "dry_run"

        record_application(
            applications, "job_apply", f"{job['title']} @ {job['company']}",
            job["url"], action,
        )

        processed += 1

        # Delay entre aplicaciones
        if processed < max_apps:
            delay = random.uniform(*DELAY_BETWEEN_APPLICATIONS)
            log.info(f"Esperando {delay:.0f}s...")
            time.sleep(delay)


# ═══════════════════════════════════════════════
# Pipeline: Modo EMAIL
# ═══════════════════════════════════════════════

def run_email_pipeline(args):
    """Pipeline completo para enviar cold emails a job listings."""
    from agent.scraper.job_scraper import (
        scrape_jobs, filter_jobs_by_relevance, save_jobs, load_jobs,
    )
    from agent.ai.cv_adapter import adapt_cv_for_job
    from agent.ai.email_writer import write_hr_email, write_ceo_email
    from agent.pdf.generator import generate_pdf
    from agent.prospector.email_finder import find_job_emails
    from agent.sender.email_sender import send_job_emails

    applications = load_applications()

    # 1. Scrape o cargar cache
    if args.skip_scrape:
        jobs = load_jobs()
    else:
        search_terms = [args.search] if args.search else None
        locations = [args.location] if args.location else None
        jobs = scrape_jobs(search_terms=search_terms, locations=locations)
        save_jobs(jobs)

    if not jobs:
        log.warning("No se encontraron ofertas. Terminando.")
        return

    # 2. Filtrar por relevancia
    relevant_jobs = filter_jobs_by_relevance(jobs, threshold=args.min_score)

    if not relevant_jobs:
        log.warning("Ninguna oferta pasó el filtro de relevancia.")
        return

    # 3. Procesar cada job
    max_emails = args.max or MAX_EMAILS_PER_RUN
    processed = 0

    for job in relevant_jobs:
        if processed >= max_emails:
            log.info(f"Límite de {max_emails} emails alcanzado.")
            break

        if is_already_processed(job["url"], applications):
            log.info(f"Ya contactado: {job['title']} @ {job['company']}, saltando.")
            continue

        log.info(f"\n{'═' * 60}")
        log.info(f"EMAIL {processed + 1}: {job['title']} @ {job['company']}")
        log.info(f"{'═' * 60}")

        # 3a. Buscar emails
        email_info = find_job_emails(job)
        if not email_info.get("hr_email") and not email_info.get("ceo_email"):
            log.warning(f"No se encontraron emails para {job['company']}, saltando.")
            record_application(
                applications, "job_email", f"{job['title']} @ {job['company']}",
                job["url"], "skipped", notes="No emails found",
            )
            continue

        # 3b. Adaptar CV
        adapted_cv = adapt_cv_for_job(job)

        # 3c. Generar PDF
        pdf_path = generate_pdf(adapted_cv, job["company"])

        # 3d. Escribir emails
        email_data = {}

        if email_info.get("hr_email"):
            hr_email = write_hr_email(job, recipient_email=email_info["hr_email"])
            email_data["hr_email"] = email_info["hr_email"]
            email_data["hr_subject"] = hr_email.get("subject", "")
            email_data["hr_html"] = hr_email.get("body_html", "")
            email_data["hr_text"] = hr_email.get("body_text", "")

        if email_info.get("ceo_email"):
            ceo_email = write_ceo_email(
                job,
                ceo_name=email_info.get("ceo_name", ""),
                ceo_email=email_info["ceo_email"],
            )
            email_data["ceo_email"] = email_info["ceo_email"]
            email_data["ceo_subject"] = ceo_email.get("subject", "")
            email_data["ceo_html"] = ceo_email.get("body_html", "")
            email_data["ceo_text"] = ceo_email.get("body_text", "")

        # 3e. Enviar emails
        results = send_job_emails(
            job=job,
            emails=email_data,
            pdf_path=pdf_path,
            dry_run=args.dry_run,
        )

        emails_sent_to = []
        if results.get("hr_sent"):
            emails_sent_to.append(email_data.get("hr_email", ""))
        if results.get("ceo_sent"):
            emails_sent_to.append(email_data.get("ceo_email", ""))

        action = "emailed" if emails_sent_to else "failed"
        if args.dry_run:
            action = "dry_run"

        record_application(
            applications, "job_email", f"{job['title']} @ {job['company']}",
            job["url"], action, emails_sent_to=emails_sent_to,
        )

        processed += 1

        if processed < max_emails:
            delay = random.uniform(*DELAY_BETWEEN_EMAILS)
            log.info(f"Esperando {delay:.0f}s...")
            time.sleep(delay)


# ═══════════════════════════════════════════════
# Pipeline: Modo PROSPECT
# ═══════════════════════════════════════════════

def run_prospect_pipeline(args):
    """Pipeline completo para deep research y prospección de empresas."""
    from agent.prospector.company_scraper import (
        scrape_all_companies, save_companies, load_companies,
    )
    from agent.prospector.email_crawler import crawl_all_companies
    from agent.prospector.company_ranker import rank_companies
    from agent.ai.cv_adapter import adapt_cv_for_company
    from agent.ai.email_writer import write_prospect_email
    from agent.pdf.generator import generate_pdf
    from agent.sender.email_sender import send_prospect_emails

    applications = load_applications()

    # 1. Obtener empresas
    if args.skip_crawl:
        companies = load_companies()
    else:
        companies = scrape_all_companies(skip_web=False)
        save_companies(companies)

    if not companies:
        log.warning("No se encontraron empresas. Terminando.")
        return

    # 2. Crawl emails si no tienen
    companies_without_emails = [c for c in companies if not c.get("emails")]
    if companies_without_emails and not args.skip_crawl:
        log.info(f"Crawleando emails de {len(companies_without_emails)} empresas...")
        crawl_all_companies(companies_without_emails)
        save_companies(companies)

    # 3. Rankear por relevancia
    companies_to_rank = [c for c in companies if c.get("relevance_score") is None]
    if companies_to_rank:
        ranked = rank_companies(companies_to_rank, threshold=args.min_score)
        # Actualizar scores en la lista original
        score_map = {c["name"]: c for c in ranked}
        for company in companies:
            if company["name"] in score_map:
                company.update(score_map[company["name"]])
        save_companies(companies)
    else:
        ranked = [c for c in companies if (c.get("relevance_score") or 0) >= args.min_score]

    # Filtrar las que tienen emails y son relevantes
    actionable = [
        c for c in ranked
        if c.get("emails") and (c.get("relevance_score") or 0) >= args.min_score
    ]

    if not actionable:
        log.warning("No hay empresas relevantes con emails. Terminando.")
        return

    log.info(f"{len(actionable)} empresas listas para contactar")

    # 4. Procesar cada empresa
    max_emails = args.max or MAX_EMAILS_PER_RUN
    processed = 0

    for company in actionable:
        if processed >= max_emails:
            log.info(f"Límite de {max_emails} emails alcanzado.")
            break

        company_key = company.get("url") or company["name"]
        if is_already_processed(company_key, applications):
            log.info(f"Ya contactado: {company['name']}, saltando.")
            continue

        log.info(f"\n{'═' * 60}")
        log.info(
            f"PROSPECT {processed + 1}: {company['name']} "
            f"[{company.get('relevance_score', '?')}]"
        )
        log.info(f"{'═' * 60}")

        # 4a. Adaptar CV
        adapted_cv = adapt_cv_for_company(company)

        # 4b. Generar PDF
        pdf_path = generate_pdf(adapted_cv, company["name"])

        # 4c. Escribir email
        email_content = write_prospect_email(
            company,
            recipient_email=company["emails"][0].get("email", "")
                if isinstance(company["emails"][0], dict) else company["emails"][0],
        )

        # 4d. Enviar
        sent_to = send_prospect_emails(
            company=company,
            email_content=email_content,
            pdf_path=pdf_path,
            dry_run=args.dry_run,
        )

        action = "emailed" if sent_to else "failed"
        if args.dry_run:
            action = "dry_run"

        record_application(
            applications, "prospect", company["name"],
            company.get("url", ""), action,
            emails_sent_to=sent_to,
        )

        company["contacted"] = True
        processed += 1

        if processed < max_emails:
            delay = random.uniform(*DELAY_BETWEEN_EMAILS)
            log.info(f"Esperando {delay:.0f}s...")
            time.sleep(delay)

    save_companies(companies)


# ═══════════════════════════════════════════════
# CLI + Main
# ═══════════════════════════════════════════════

def parse_args():
    parser = argparse.ArgumentParser(
        description="Pipeline automatizado de búsqueda de empleo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python -m agent.main --mode apply --dry-run
  python -m agent.main --mode email --max 5
  python -m agent.main --mode prospect --skip-crawl
  python -m agent.main --mode full --dry-run --headed
        """,
    )

    # Modo de operación
    parser.add_argument(
        "--mode",
        choices=["apply", "email", "prospect", "full"],
        required=True,
        help="Modo de operación",
    )

    # Opciones generales
    parser.add_argument("--dry-run", action="store_true", help="Hacer todo excepto enviar/aplicar")
    parser.add_argument("--max", type=int, help="Máximo de aplicaciones/emails")
    parser.add_argument("--search", type=str, help="Override search term")
    parser.add_argument("--location", type=str, help="Override location")
    parser.add_argument("--min-score", type=int, default=DEFAULT_RELEVANCE_THRESHOLD, help="Score mínimo de relevancia")

    # Opciones modo apply
    parser.add_argument("--headed", action="store_true", help="Ver browser en tiempo real")
    parser.add_argument("--confirm", action="store_true", help="Pausa antes de cada submit")

    # Opciones modo scrape
    parser.add_argument("--skip-scrape", action="store_true", help="Usar jobs cacheados")
    parser.add_argument("--skip-crawl", action="store_true", help="Usar empresas cacheadas")

    return parser.parse_args()


def main():
    args = parse_args()
    ensure_data_dirs()

    log.info(f"🚀 Pipeline de Búsqueda de Empleo — Modo: {args.mode.upper()}")
    if args.dry_run:
        log.info("🔒 DRY-RUN activado — no se enviarán emails ni aplicaciones")
    log.info("")

    # Validar configuración
    errors = validate_config(args.mode)
    if errors:
        for err in errors:
            log.error(f"Config: {err}")
        log.error("Corregí la configuración en .env y reintentá.")
        sys.exit(1)

    start_time = time.time()

    try:
        if args.mode == "apply":
            run_apply_pipeline(args)

        elif args.mode == "email":
            run_email_pipeline(args)

        elif args.mode == "prospect":
            run_prospect_pipeline(args)

        elif args.mode == "full":
            log.info("━━━ FASE 1: APPLY (portales) ━━━")
            run_apply_pipeline(args)

            log.info("\n━━━ FASE 2: EMAIL (cold emails a listings) ━━━")
            run_email_pipeline(args)

            log.info("\n━━━ FASE 3: PROSPECT (deep research Mendoza) ━━━")
            run_prospect_pipeline(args)

    except KeyboardInterrupt:
        log.warning("\nInterrumpido por el usuario.")
    except Exception as e:
        log.error(f"Error fatal: {e}")
        summary.add_error(f"Fatal: {str(e)[:200]}")
    finally:
        elapsed = time.time() - start_time
        log.info(f"\nTiempo total: {elapsed / 60:.1f} minutos")
        summary.print_summary()


if __name__ == "__main__":
    main()
