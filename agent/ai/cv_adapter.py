"""
Adaptador de CV usando LLM.
Toma el resume.json base + context.md y lo adapta para un job/empresa específico.
"""

import json
from pathlib import Path

from agent.config import CONTEXT_FILE, RESUME_FILE
from agent.ai.llm_client import get_llm_client
from agent.utils.logger import log, summary


def load_base_resume() -> dict:
    """Carga el resume.json base del proyecto."""
    if not RESUME_FILE.exists():
        raise FileNotFoundError(f"No se encontró resume.json en {RESUME_FILE}")
    return json.loads(RESUME_FILE.read_text(encoding="utf-8"))


def load_context() -> str:
    """Carga el context.md completo."""
    if not CONTEXT_FILE.exists():
        log.warning("context.md no encontrado, usando solo resume.json")
        return ""
    return CONTEXT_FILE.read_text(encoding="utf-8")


def adapt_cv_for_job(job: dict) -> dict:
    """
    Adapta el CV para una oferta laboral específica.

    Args:
        job: dict con al menos 'title', 'company', 'description'

    Returns:
        dict: resume.json adaptado (misma estructura JSON Resume)
    """
    base_resume = load_base_resume()
    context = load_context()
    llm = get_llm_client()

    job_info = (
        f"Título: {job.get('title', 'N/A')}\n"
        f"Empresa: {job.get('company', 'N/A')}\n"
        f"Ubicación: {job.get('location', 'N/A')}\n"
        f"Descripción:\n{job.get('description', 'N/A')[:3000]}"
    )

    messages = [
        {
            "role": "system",
            "content": (
                "Sos un experto en adaptación de CVs para maximizar las chances de "
                "conseguir entrevistas. Tu trabajo es adaptar un CV existente para una "
                "posición específica.\n\n"
                "REGLAS ESTRICTAS:\n"
                "1. NUNCA inventar experiencia, proyectos o habilidades que no estén en "
                "   el contexto del candidato.\n"
                "2. SÍ podés reordenar secciones para poner lo más relevante primero.\n"
                "3. SÍ podés reformular highlights para enfatizar lo que matchea con el job.\n"
                "4. SÍ podés ajustar el summary/perfil para alinearlo con la posición.\n"
                "5. SÍ podés reordenar skills y keywords para poner las relevantes primero.\n"
                "6. MANTENER la estructura exacta de JSON Resume schema.\n"
                "7. El label (título profesional) puede adaptarse al rol.\n"
                "8. Los highlights de cada trabajo pueden reformularse para enfatizar "
                "   lo relevante, pero deben ser verdaderos.\n"
                "9. Respondé SOLO con el JSON del resume adaptado, sin explicación.\n"
                "10. Mantener el idioma original del CV (español)."
            ),
        },
        {
            "role": "user",
            "content": (
                f"CONTEXTO COMPLETO DEL CANDIDATO:\n{context}\n\n"
                f"CV BASE (JSON Resume):\n{json.dumps(base_resume, indent=2, ensure_ascii=False)}\n\n"
                f"OFERTA LABORAL A LA QUE QUIERO APLICAR:\n{job_info}\n\n"
                "Adaptá el CV para esta posición. Respondé SOLO con el JSON adaptado."
            ),
        },
    ]

    log.info(f"Adaptando CV para: {job.get('title', '?')} @ {job.get('company', '?')}...")

    try:
        adapted = llm.chat_json(messages, temperature=0.4, max_tokens=6000)

        # Validar que tiene la estructura mínima
        if "basics" not in adapted:
            log.warning("CV adaptado no tiene 'basics', usando base")
            adapted["basics"] = base_resume["basics"]

        if "basics" in adapted and "name" not in adapted["basics"]:
            adapted["basics"]["name"] = base_resume["basics"]["name"]

        summary.cvs_adapted += 1
        log.info(f"  ✓ CV adaptado exitosamente")
        return adapted

    except Exception as e:
        log.error(f"Error adaptando CV: {e}")
        log.warning("Usando CV base sin adaptar")
        summary.add_error(f"CV adaptation failed for {job.get('company', '?')}: {str(e)[:100]}")
        return base_resume


def adapt_cv_for_company(company: dict) -> dict:
    """
    Adapta el CV para una empresa específica (modo prospect).
    A diferencia de adapt_cv_for_job, no hay un job description específico,
    sino que se adapta basándose en lo que hace la empresa.

    Args:
        company: dict con al menos 'name', 'sector', 'url'

    Returns:
        dict: resume.json adaptado
    """
    base_resume = load_base_resume()
    context = load_context()
    llm = get_llm_client()

    company_info = (
        f"Empresa: {company.get('name', 'N/A')}\n"
        f"Sector: {company.get('sector', 'N/A')}\n"
        f"URL: {company.get('url', 'N/A')}\n"
        f"Ubicación: {company.get('location', 'Mendoza')}\n"
        f"Descripción: {company.get('description', 'Empresa de tecnología en Mendoza')}"
    )

    messages = [
        {
            "role": "system",
            "content": (
                "Sos un experto en adaptación de CVs. Tu trabajo es adaptar un CV "
                "para una empresa específica, aunque no haya una oferta publicada.\n\n"
                "REGLAS:\n"
                "1. NUNCA inventar experiencia o skills.\n"
                "2. Adaptar el summary para mostrar cómo el candidato puede aportar "
                "   valor a esta empresa específica.\n"
                "3. Enfatizar skills y experiencia relevantes para el sector de la empresa.\n"
                "4. Mantener estructura JSON Resume.\n"
                "5. Respondé SOLO con el JSON adaptado."
            ),
        },
        {
            "role": "user",
            "content": (
                f"CONTEXTO DEL CANDIDATO:\n{context}\n\n"
                f"CV BASE:\n{json.dumps(base_resume, indent=2, ensure_ascii=False)}\n\n"
                f"EMPRESA OBJETIVO:\n{company_info}\n\n"
                "Adaptá el CV para esta empresa. Respondé SOLO con el JSON adaptado."
            ),
        },
    ]

    log.info(f"Adaptando CV para empresa: {company.get('name', '?')}...")

    try:
        adapted = llm.chat_json(messages, temperature=0.4, max_tokens=6000)

        if "basics" not in adapted:
            adapted["basics"] = base_resume["basics"]

        summary.cvs_adapted += 1
        log.info(f"  ✓ CV adaptado para {company.get('name', '?')}")
        return adapted

    except Exception as e:
        log.error(f"Error adaptando CV para empresa: {e}")
        summary.add_error(f"CV adaptation failed for company {company.get('name', '?')}: {str(e)[:100]}")
        return base_resume
