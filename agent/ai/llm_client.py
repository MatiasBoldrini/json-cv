"""
Cliente LLM unificado con fallback automático.
Groq (primario) → OpenRouter (fallback).
Compatible con el SDK de OpenAI.
"""

import json
import time
from openai import OpenAI

from agent.config import (
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
)
from agent.utils.logger import log


class LLMClient:
    """
    Cliente LLM con fallback automático entre providers.
    Usa el SDK de OpenAI que es compatible con Groq y OpenRouter.
    """

    def __init__(self):
        self.providers = []
        self._current_provider_idx = 0

        # Groq como primario
        if GROQ_API_KEY:
            self.providers.append({
                "name": "Groq",
                "client": OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL),
                "model": GROQ_MODEL,
            })

        # OpenRouter como fallback
        if OPENROUTER_API_KEY:
            self.providers.append({
                "name": "OpenRouter",
                "client": OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL),
                "model": OPENROUTER_MODEL,
            })

        if not self.providers:
            raise ValueError(
                "No hay providers LLM configurados. "
                "Configurá GROQ_API_KEY o OPENROUTER_API_KEY en .env"
            )

        log.info(
            f"LLM Client inicializado con {len(self.providers)} provider(s): "
            f"{', '.join(p['name'] for p in self.providers)}"
        )

    @property
    def _current(self):
        return self.providers[self._current_provider_idx]

    def _switch_provider(self):
        """Cambia al siguiente provider disponible."""
        if self._current_provider_idx + 1 < len(self.providers):
            self._current_provider_idx += 1
            log.warning(f"Switching a provider: {self._current['name']}")
            return True
        return False

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> str:
        """
        Envía un mensaje al LLM y retorna la respuesta como string.
        Con fallback automático si el provider falla.
        """
        max_retries = 3
        backoff = 2

        for attempt in range(max_retries):
            provider = self._current
            try:
                kwargs = {
                    "model": provider["model"],
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}

                response = provider["client"].chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                return content.strip() if content else ""

            except Exception as e:
                error_msg = str(e)
                is_rate_limit = "429" in error_msg or "rate" in error_msg.lower()

                if is_rate_limit:
                    log.warning(
                        f"Rate limit en {provider['name']} (intento {attempt + 1}/{max_retries})"
                    )
                    # Intentar cambiar de provider
                    if self._switch_provider():
                        continue
                else:
                    log.error(f"Error en {provider['name']}: {error_msg}")

                if attempt < max_retries - 1:
                    wait = backoff ** (attempt + 1)
                    log.info(f"Reintentando en {wait}s...")
                    time.sleep(wait)
                    # Intentar cambiar de provider si no lo hicimos
                    if not is_rate_limit:
                        self._switch_provider()
                else:
                    raise RuntimeError(
                        f"Todos los providers LLM fallaron después de {max_retries} intentos. "
                        f"Último error: {error_msg}"
                    )

        raise RuntimeError("No se pudo obtener respuesta del LLM.")

    def chat_json(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict:
        """
        Envía un mensaje y retorna la respuesta parseada como JSON.
        Usa json_mode si es posible, o parsea manualmente.
        """
        # Intentar con json_mode primero
        try:
            raw = self.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=True,
            )
            return json.loads(raw)
        except (json.JSONDecodeError, Exception):
            # Fallback: pedir sin json_mode y parsear manualmente
            log.warning("json_mode falló, intentando parseo manual...")

        raw = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=False,
        )

        # Intentar extraer JSON de la respuesta
        return self._extract_json(raw)

    @staticmethod
    def _extract_json(text: str) -> dict:
        """Extrae JSON de una respuesta que puede contener markdown o texto extra."""
        # Intentar parsear directamente
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Buscar bloques de código JSON
        for marker in ["```json", "```"]:
            if marker in text:
                start = text.index(marker) + len(marker)
                end = text.index("```", start)
                try:
                    return json.loads(text[start:end].strip())
                except (json.JSONDecodeError, ValueError):
                    pass

        # Buscar el primer { ... } o [ ... ]
        for open_char, close_char in [("{", "}"), ("[", "]")]:
            start = text.find(open_char)
            if start != -1:
                # Encontrar el cierre correspondiente
                depth = 0
                for i in range(start, len(text)):
                    if text[i] == open_char:
                        depth += 1
                    elif text[i] == close_char:
                        depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start:i + 1])
                        except json.JSONDecodeError:
                            break

        raise ValueError(f"No se pudo extraer JSON de la respuesta: {text[:200]}...")


# Singleton
_client = None


def get_llm_client() -> LLMClient:
    """Retorna la instancia singleton del LLM client."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
