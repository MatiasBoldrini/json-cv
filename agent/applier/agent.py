"""
Agente de aplicación autónoma usando browser-use.
Controla un browser con IA para aplicar a ofertas laborales en cualquier portal.
"""

import asyncio
import json
import random
import time
from pathlib import Path

from agent.config import (
    CONTEXT_FILE,
    DELAY_BETWEEN_APPLICATIONS,
    GROQ_API_KEY,
    GROQ_MODEL,
    LINKEDIN_EMAIL,
    LINKEDIN_PASSWORD,
    MAX_APPLICATIONS_PER_RUN,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
)
from agent.utils.logger import log, summary


def _get_browser_llm():
    """
    Obtiene el LLM configurado para browser-use.
    Usa langchain_groq o langchain_openai según disponibilidad.
    """
    if GROQ_API_KEY:
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(
                model=GROQ_MODEL,
                api_key=GROQ_API_KEY,
                temperature=0.3,
            )
        except ImportError:
            log.warning("langchain_groq no disponible, intentando OpenRouter...")

    if OPENROUTER_API_KEY:
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=OPENROUTER_MODEL,
                api_key=OPENROUTER_API_KEY,
                base_url=OPENROUTER_BASE_URL,
                temperature=0.3,
            )
        except ImportError:
            log.warning("langchain_openai no disponible")

    raise RuntimeError(
        "No se pudo inicializar LLM para browser-use. "
        "Instalar langchain-groq o langchain-openai."
    )


def _build_apply_task(job: dict, pdf_path: Path, context: str) -> str:
    """Construye la tarea en lenguaje natural para el agente."""

    # Datos personales del contexto para rellenar formularios
    personal_data = (
        "Nombre: Matias Boldrini\n"
        "Email: matiboldrini7811@gmail.com\n"
        "Teléfono: (+54) 261 344 9543\n"
        "Ubicación: Mendoza, Argentina\n"
        "LinkedIn: https://www.linkedin.com/in/mat%C3%ADas-boldrini-93b146192/\n"
        "GitHub: https://github.com/MatiasBoldrini\n"
    )

    task = f"""
Necesito que apliques a esta oferta laboral:

OFERTA:
- Título: {job.get('title', 'N/A')}
- Empresa: {job.get('company', 'N/A')}
- URL: {job.get('url', 'N/A')}
- Portal: {job.get('source', 'N/A')}

PASOS:
1. Navegá a la URL de la oferta: {job.get('url', '')}
2. Buscá el botón de "Apply", "Aplicar", "Easy Apply", "Postularme" o similar.
3. Si pide login y el portal es LinkedIn, usá:
   - Email: {LINKEDIN_EMAIL}
   - Password: {LINKEDIN_PASSWORD}
4. Completá el formulario de aplicación con estos datos:
{personal_data}
5. Si pide subir un CV/Resume, subí el archivo: {pdf_path}
6. Si hay preguntas adicionales, respondé de manera profesional usando este contexto:
   - 3+ años de experiencia en desarrollo
   - Inglés C1 avanzado
   - Disponibilidad inmediata, Full Time
   - Ubicación: Mendoza, Argentina
   - Dispuesto a trabajo remoto
7. Revisá el formulario antes de enviar.
8. Enviá la aplicación (hacé click en Submit/Enviar/Apply).

IMPORTANTE:
- Si encontrás un CAPTCHA, esperá 30 segundos y reintentá.
- Si el formulario tiene múltiples pasos, completá todos.
- Si algo falla, no te trabes, pasá al siguiente paso o reportá el error.
"""
    return task


def _build_apply_task_dry_run(job: dict, pdf_path: Path) -> str:
    """Tarea de dry-run: navega y rellena pero NO envía."""
    task = _build_apply_task(job, pdf_path, "")
    task += (
        "\n\nMODO DRY-RUN: NO envíes la aplicación. "
        "Completá todos los campos pero NO hagas click en el botón final de envío/submit. "
        "Tomá un screenshot del formulario completado antes de enviar."
    )
    return task


async def apply_to_job(
    job: dict,
    pdf_path: Path,
    headless: bool = True,
    confirm: bool = False,
    dry_run: bool = False,
) -> bool:
    """
    Aplica a una oferta laboral usando browser-use.

    Args:
        job: dict con datos del job (url, title, company, etc.)
        pdf_path: Path al PDF del CV adaptado
        headless: si True, browser invisible; si False, se ve en pantalla
        confirm: si True, pausa antes del submit para confirmación humana
        dry_run: si True, completa pero no envía

    Returns:
        bool: True si la aplicación fue exitosa
    """
    try:
        from browser_use import Agent, BrowserConfig
    except ImportError:
        log.error(
            "browser-use no está instalado. "
            "Ejecutá: pip install browser-use"
        )
        return False

    llm = _get_browser_llm()
    context = ""
    if CONTEXT_FILE.exists():
        context = CONTEXT_FILE.read_text(encoding="utf-8")[:2000]

    if dry_run:
        task = _build_apply_task_dry_run(job, pdf_path)
    elif confirm:
        task = _build_apply_task(job, pdf_path, context)
        task += (
            "\n\nMODO CONFIRMACIÓN: Completá todo el formulario pero antes de "
            "hacer click en enviar, esperá 10 segundos para dar tiempo a revisión."
        )
    else:
        task = _build_apply_task(job, pdf_path, context)

    log.info(f"Aplicando a: {job.get('title', '?')} @ {job.get('company', '?')}")
    log.info(f"  URL: {job.get('url', '?')}")
    log.info(f"  PDF: {pdf_path}")

    try:
        browser_config = BrowserConfig(headless=headless)
        agent = Agent(
            task=task,
            llm=llm,
            browser_config=browser_config,
        )
        result = await agent.run()

        # Verificar resultado
        if result:
            summary.applications_sent += 1
            action = "simulada (dry-run)" if dry_run else "completada"
            log.info(f"  ✓ Aplicación {action}")
            return True
        else:
            log.warning(f"  ✗ Aplicación no completada")
            return False

    except Exception as e:
        log.error(f"  ✗ Error aplicando: {e}")
        summary.add_error(
            f"Apply failed: {job.get('company', '?')} - {str(e)[:100]}"
        )
        return False


async def apply_to_jobs(
    jobs: list[dict],
    pdf_paths: dict[str, Path],
    headless: bool = True,
    confirm: bool = False,
    dry_run: bool = False,
    max_applications: int | None = None,
) -> list[dict]:
    """
    Aplica a múltiples ofertas con rate limiting.

    Args:
        jobs: lista de jobs a aplicar
        pdf_paths: dict job_id -> Path al PDF
        headless: browser invisible
        confirm: pausa antes de cada submit
        dry_run: no enviar
        max_applications: límite de aplicaciones

    Returns:
        lista de resultados [{job_id, success, notes}]
    """
    max_apps = max_applications or MAX_APPLICATIONS_PER_RUN
    results = []

    for i, job in enumerate(jobs[:max_apps]):
        job_id = job.get("id", str(i))
        pdf_path = pdf_paths.get(job_id)

        if not pdf_path or not pdf_path.exists():
            log.warning(f"No hay PDF para {job.get('company', '?')}, saltando...")
            results.append({"job_id": job_id, "success": False, "notes": "No PDF"})
            continue

        log.info(f"\n{'='*50}")
        log.info(f"Aplicación {i + 1}/{min(len(jobs), max_apps)}")
        log.info(f"{'='*50}")

        success = await apply_to_job(
            job=job,
            pdf_path=pdf_path,
            headless=headless,
            confirm=confirm,
            dry_run=dry_run,
        )

        results.append({
            "job_id": job_id,
            "success": success,
            "notes": "dry-run" if dry_run else ("ok" if success else "failed"),
        })

        # Delay entre aplicaciones (simular comportamiento humano)
        if i < len(jobs) - 1:
            delay = random.uniform(*DELAY_BETWEEN_APPLICATIONS)
            log.info(f"Esperando {delay:.0f}s antes de la siguiente aplicación...")
            await asyncio.sleep(delay)

    return results


def run_apply_sync(
    jobs: list[dict],
    pdf_paths: dict[str, Path],
    headless: bool = True,
    confirm: bool = False,
    dry_run: bool = False,
    max_applications: int | None = None,
) -> list[dict]:
    """Wrapper sincrónico para apply_to_jobs."""
    return asyncio.run(
        apply_to_jobs(
            jobs=jobs,
            pdf_paths=pdf_paths,
            headless=headless,
            confirm=confirm,
            dry_run=dry_run,
            max_applications=max_applications,
        )
    )
