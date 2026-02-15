"""
Logger con colores y timestamps para el pipeline de búsqueda de empleo.
"""

import logging
import sys
from datetime import datetime


class ColorFormatter(logging.Formatter):
    """Formatter con colores ANSI para terminal."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[1;31m",  # Bold Red
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        prefix = f"{color}[{timestamp}] {record.levelname:<8}{self.RESET}"
        message = record.getMessage()
        return f"{prefix} {message}"


def setup_logger(name: str = "agent", level: str = "INFO") -> logging.Logger:
    """Configura y retorna el logger principal."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ColorFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger


log = setup_logger()


class PipelineSummary:
    """Trackea métricas del pipeline para el resumen final."""

    def __init__(self):
        self.jobs_found = 0
        self.jobs_filtered = 0
        self.jobs_relevant = 0
        self.cvs_adapted = 0
        self.pdfs_generated = 0
        self.applications_sent = 0
        self.emails_sent = 0
        self.companies_found = 0
        self.companies_crawled = 0
        self.emails_extracted = 0
        self.errors = []

    def add_error(self, error: str):
        self.errors.append(error)

    def print_summary(self):
        log.info("=" * 50)
        log.info("RESUMEN DEL PIPELINE")
        log.info("=" * 50)

        if self.jobs_found:
            log.info(f"Jobs encontrados:    {self.jobs_found}")
            log.info(f"Jobs relevantes:     {self.jobs_relevant} / {self.jobs_filtered} evaluados")

        if self.companies_found:
            log.info(f"Empresas encontradas: {self.companies_found}")
            log.info(f"Empresas crawleadas:  {self.companies_crawled}")
            log.info(f"Emails extraídos:     {self.emails_extracted}")

        if self.cvs_adapted:
            log.info(f"CVs adaptados:       {self.cvs_adapted}")

        if self.pdfs_generated:
            log.info(f"PDFs generados:      {self.pdfs_generated}")

        if self.applications_sent:
            log.info(f"Aplicaciones enviadas: {self.applications_sent}")

        if self.emails_sent:
            log.info(f"Emails enviados:     {self.emails_sent}")

        if self.errors:
            log.warning(f"Errores:             {len(self.errors)}")
            for err in self.errors[:5]:
                log.warning(f"  → {err}")
            if len(self.errors) > 5:
                log.warning(f"  ... y {len(self.errors) - 5} más")

        log.info("=" * 50)


summary = PipelineSummary()
