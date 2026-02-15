"""
Ranker de empresas usando LLM.
Evalúa qué empresas podrían necesitar el perfil del candidato.
"""

from agent.config import CONTEXT_FILE
from agent.ai.llm_client import get_llm_client
from agent.utils.logger import log


def rank_companies(companies: list[dict], threshold: int = 40) -> list[dict]:
    """
    Usa el LLM para evaluar qué empresas podrían necesitar el perfil.

    Args:
        companies: lista de empresas con name, sector, url, etc.
        threshold: score mínimo para considerar relevante

    Returns:
        Empresas filtradas y ordenadas por relevancia
    """
    llm = get_llm_client()

    context_summary = ""
    if CONTEXT_FILE.exists():
        context_summary = CONTEXT_FILE.read_text(encoding="utf-8")[:2000]

    log.info(f"Evaluando relevancia de {len(companies)} empresas...")

    # Procesar en batches de 8 (más eficiente que de 5 para este caso)
    batch_size = 8
    for i in range(0, len(companies), batch_size):
        batch = companies[i:i + batch_size]

        companies_text = ""
        for idx, company in enumerate(batch):
            companies_text += (
                f"\n--- EMPRESA {idx + 1} ---\n"
                f"Nombre: {company['name']}\n"
                f"Sector: {company.get('sector', 'N/A')}\n"
                f"URL: {company.get('url', 'N/A')}\n"
                f"Ubicación: {company.get('location', 'Mendoza')}\n"
            )

        messages = [
            {
                "role": "system",
                "content": (
                    "Sos un experto en matcheo de talento tech con empresas. "
                    "Evaluá si cada empresa podría beneficiarse de contratar al candidato.\n"
                    "El candidato es un Product Engineer con foco en IA, automatización y fullstack.\n\n"
                    "Para cada empresa, dá:\n"
                    "- score: 0-100 (qué tan probable es que necesiten este perfil)\n"
                    "- reason: por qué sí o no (1 línea)\n"
                    "- angle: qué ángulo usar para el email (1 línea)\n\n"
                    "Score guide:\n"
                    "- 80-100: Empresa de software/IA que seguro necesita devs\n"
                    "- 60-79: Empresa tech que probablemente contrate\n"
                    "- 40-59: Podría necesitar, depende del momento\n"
                    "- 0-39: Poco probable que necesiten este perfil\n\n"
                    "Respondé SOLO con un JSON array: [{\"index\": N, \"score\": N, \"reason\": \"...\", \"angle\": \"...\"}]"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"PERFIL DEL CANDIDATO (resumen):\n{context_summary}\n\n"
                    f"EMPRESAS A EVALUAR:{companies_text}"
                ),
            },
        ]

        try:
            result = llm.chat_json(messages, temperature=0.2)

            if isinstance(result, dict):
                result = result.get("companies", result.get("results", [result]))
            if not isinstance(result, list):
                result = [result]

            for item in result:
                idx = int(item.get("index", 1)) - 1
                if 0 <= idx < len(batch):
                    batch[idx]["relevance_score"] = int(item.get("score", 0))
                    batch[idx]["relevance_reason"] = str(item.get("reason", ""))
                    batch[idx]["email_angle"] = str(item.get("angle", ""))

        except Exception as e:
            log.error(f"Error rankeando batch de empresas: {e}")
            for company in batch:
                if company["relevance_score"] is None:
                    company["relevance_score"] = 50
                    company["relevance_reason"] = "Score por defecto"

    # Filtrar y ordenar
    relevant = [c for c in companies if (c.get("relevance_score") or 0) >= threshold]
    relevant.sort(key=lambda c: c.get("relevance_score", 0), reverse=True)

    log.info(
        f"Ranking completo: {len(relevant)} empresas relevantes "
        f"de {len(companies)} (threshold: {threshold})"
    )

    for company in relevant[:5]:
        log.info(
            f"  ★ [{company['relevance_score']}] {company['name']} "
            f"— {company.get('relevance_reason', '')[:60]}"
        )

    return relevant
