"""
Generador de PDFs del CV adaptado.
Reutiliza la infraestructura Node.js existente (Puppeteer + Handlebars).
"""

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from agent.config import PROJECT_ROOT, AGENT_DIR
from agent.utils.logger import log, summary


# Script Node.js inline que genera el PDF a partir de un resume.json externo
_NODE_SCRIPT = """
const fs = require('fs');
const path = require('path');

// Args: [resumePath, outputPath, projectRoot]
const resumePath = process.argv[2];
const outputPath = process.argv[3];
const projectRoot = process.argv[4] || __dirname;

// Cargar resume
const resume = JSON.parse(fs.readFileSync(resumePath, 'utf-8'));

// Cargar theme (index.js) desde la raíz del proyecto
const themePath = path.join(projectRoot, 'index.js');
const theme = require(themePath);

// Convertir imagen local a base64
function imageToBase64(imagePath) {
  try {
    const normalizedPath = imagePath.startsWith("/") ? imagePath.slice(1) : imagePath;
    const ext = path.extname(normalizedPath).toLowerCase();
    const mimeType = ext === ".png" ? "image/png" :
      (ext === ".jpg" || ext === ".jpeg") ? "image/jpeg" :
      ext === ".gif" ? "image/gif" : "image/jpeg";
    const candidates = [
      path.join(projectRoot, normalizedPath),
      path.join(projectRoot, "public", normalizedPath),
    ];
    for (const p of candidates) {
      if (fs.existsSync(p)) {
        return "data:" + mimeType + ";base64," + fs.readFileSync(p).toString("base64");
      }
    }
  } catch (e) {}
  return null;
}

if (!resume.basics) resume.basics = {};
if (!resume.basics.image || resume.basics.image.trim() === "") {
  resume.basics.image = "/profile_pic.jpg";
}
if (resume.basics.image && !resume.basics.image.startsWith("http")) {
  const b64 = imageToBase64(resume.basics.image);
  if (b64) resume.basics.image = b64;
}

const html = theme.render(resume);
const htmlPath = path.join(path.dirname(outputPath), 'temp-resume.html');
fs.writeFileSync(htmlPath, html);

(async () => {
  let puppeteer;
  try {
    puppeteer = require('puppeteer');
  } catch (e) {
    puppeteer = require('puppeteer-core');
  }

  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();
  await page.goto('file://' + htmlPath, { waitUntil: 'networkidle0' });

  await page.pdf({
    path: outputPath,
    format: 'A4',
    printBackground: true,
    margin: { top: '10mm', right: '10mm', bottom: '10mm', left: '10mm' }
  });

  await browser.close();
  fs.unlinkSync(htmlPath);
  console.log('PDF generado: ' + outputPath);
})().catch(err => {
  console.error('Error:', err);
  process.exit(1);
});
"""


def _sanitize_filename(name: str) -> str:
    """Convierte un nombre a un filename seguro."""
    name = name.lower().strip()
    name = re.sub(r'[^a-z0-9\s-]', '', name)
    name = re.sub(r'[\s]+', '-', name)
    return name[:50]


def generate_pdf(
    adapted_resume: dict,
    company_name: str,
    output_dir: Path | None = None,
) -> Path | None:
    """
    Genera un PDF del CV adaptado usando la infraestructura Node.js existente.

    Args:
        adapted_resume: dict del resume.json adaptado
        company_name: nombre de la empresa (para el filename)
        output_dir: directorio de salida (default: agent/data/)

    Returns:
        Path al PDF generado, o None si falló
    """
    output_dir = output_dir or (AGENT_DIR / "data")
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_company = _sanitize_filename(company_name) or "general"
    pdf_filename = f"CV-matias-boldrini-{safe_company}.pdf"
    output_path = output_dir / pdf_filename

    log.info(f"Generando PDF para {company_name}...")

    try:
        # Escribir el resume adaptado a un archivo temporal
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False, encoding='utf-8'
        ) as tmp:
            json.dump(adapted_resume, tmp, ensure_ascii=False, indent=2)
            tmp_resume_path = tmp.name

        # Escribir el script Node.js dentro del proyecto (para que encuentre node_modules)
        tmp_script_path = str(PROJECT_ROOT / "_tmp_gen_pdf.js")
        Path(tmp_script_path).write_text(_NODE_SCRIPT, encoding="utf-8")

        # Ejecutar el script Node.js desde la raíz del proyecto
        result = subprocess.run(
            [
                "node", tmp_script_path,
                tmp_resume_path,
                str(output_path.absolute()),
                str(PROJECT_ROOT.absolute()),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(PROJECT_ROOT),
        )

        # Limpiar archivos temporales
        Path(tmp_resume_path).unlink(missing_ok=True)
        Path(tmp_script_path).unlink(missing_ok=True)

        if result.returncode != 0:
            log.error(f"Error generando PDF: {result.stderr}")
            summary.add_error(f"PDF generation failed for {company_name}: {result.stderr[:200]}")
            return None

        if output_path.exists():
            size_kb = output_path.stat().st_size / 1024
            summary.pdfs_generated += 1
            log.info(f"  ✓ PDF generado: {pdf_filename} ({size_kb:.1f} KB)")
            return output_path
        else:
            log.error("PDF no fue creado (archivo no encontrado)")
            return None

    except subprocess.TimeoutExpired:
        log.error("Timeout generando PDF (>60s)")
        summary.add_error(f"PDF generation timeout for {company_name}")
        return None
    except Exception as e:
        log.error(f"Error inesperado generando PDF: {e}")
        summary.add_error(f"PDF error for {company_name}: {str(e)[:100]}")
        return None
