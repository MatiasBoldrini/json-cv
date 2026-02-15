"""
Configuración central del pipeline de búsqueda de empleo.
Carga variables de entorno y define constantes.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Paths
AGENT_DIR = Path(__file__).parent
PROJECT_ROOT = AGENT_DIR.parent
DATA_DIR = AGENT_DIR / "data"
TEMPLATES_DIR = DATA_DIR / "templates"
CONTEXT_FILE = AGENT_DIR / "context.md"
RESUME_FILE = PROJECT_ROOT / "resume.json"

# Cargar .env desde la raíz del proyecto
load_dotenv(PROJECT_ROOT / ".env")

# ──────────────────────────────────────────────
# API Keys
# ──────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")

# ──────────────────────────────────────────────
# Email
# ──────────────────────────────────────────────
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "matiboldrini7811@gmail.com")
SENDER_NAME = os.getenv("SENDER_NAME", "Matias Boldrini")

# ──────────────────────────────────────────────
# LinkedIn (para modo apply)
# ──────────────────────────────────────────────
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

# ──────────────────────────────────────────────
# LLM Models
# ──────────────────────────────────────────────
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

OPENROUTER_MODEL = "meta-llama/llama-3.2-3b-instruct:free"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# ──────────────────────────────────────────────
# Job Search Defaults
# ──────────────────────────────────────────────
DEFAULT_SEARCH_TERMS = [
    "product engineer",
    "fullstack developer",
    "python developer",
    "AI engineer",
    "desarrollador fullstack",
    "ingeniero de software",
]

DEFAULT_LOCATIONS = [
    "Argentina",
    "Remote",
    "Latin America",
    "Mendoza",
]

DEFAULT_RESULTS_PER_SITE = 15
DEFAULT_RELEVANCE_THRESHOLD = 40

# ──────────────────────────────────────────────
# Rate Limits & Delays
# ──────────────────────────────────────────────
MAX_APPLICATIONS_PER_RUN = 20
MAX_EMAILS_PER_RUN = 50
DELAY_BETWEEN_APPLICATIONS = (30, 90)  # rango en segundos (min, max)
DELAY_BETWEEN_EMAILS = (15, 60)        # rango en segundos (min, max)
DELAY_BETWEEN_CRAWLS = (5, 15)         # rango en segundos (min, max)

# ──────────────────────────────────────────────
# Data files
# ──────────────────────────────────────────────
JOBS_FILE = DATA_DIR / "jobs.json"
COMPANIES_FILE = DATA_DIR / "companies.json"
APPLICATIONS_FILE = DATA_DIR / "applications.json"
SEED_COMPANIES_FILE = DATA_DIR / "seed_companies.json"


def validate_config(mode: str) -> list[str]:
    """
    Valida que las API keys necesarias estén configuradas según el modo.
    Retorna lista de errores (vacía si todo OK).
    """
    errors = []

    # Al menos un LLM provider es requerido siempre
    if not GROQ_API_KEY and not OPENROUTER_API_KEY:
        errors.append(
            "Se necesita al menos GROQ_API_KEY o OPENROUTER_API_KEY. "
            "Configurá al menos una en el archivo .env"
        )

    if mode in ("email", "prospect", "full"):
        if not RESEND_API_KEY:
            errors.append(
                f"RESEND_API_KEY es requerido para el modo '{mode}'. "
                "Registrate gratis en https://resend.com"
            )
        if not SENDER_EMAIL:
            errors.append(
                f"SENDER_EMAIL es requerido para el modo '{mode}'. "
                "Configuralo en el archivo .env"
            )

    if mode in ("apply", "full"):
        if not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD:
            errors.append(
                f"LINKEDIN_EMAIL y LINKEDIN_PASSWORD son requeridos para el modo '{mode}'. "
                "Configurálos en el archivo .env"
            )

    return errors


def ensure_data_dirs():
    """Crea los directorios de datos si no existen."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
