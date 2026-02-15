# 🚀 Agent — Pipeline Automatizado de Búsqueda de Empleo

Sistema autónomo que busca ofertas laborales, adapta tu CV con IA, y aplica o envía cold emails — todo automático y **gratis**.

## 🎯 Modos de Operación

| Modo | Comando | Qué hace |
|------|---------|----------|
| **Apply** | `--mode apply` | Aplica directamente en portales (LinkedIn, Indeed, etc.) usando un agente IA que controla el browser |
| **Email** | `--mode email` | Envía cold emails personalizados (HR + CEO) con CV adaptado adjunto |
| **Prospect** | `--mode prospect` | Deep research: crawlea webs de empresas de Mendoza, extrae emails, rankea y envía |
| **Full** | `--mode full` | Ejecuta los 3 modos en secuencia |

## ⚡ Quick Start

### 1. Instalar dependencias

```bash
cd agent
pip install -r requirements.txt
playwright install chromium
```

> Requiere Python 3.11+

### 2. Configurar API keys

```bash
# Copiar el ejemplo
cp ../.env.example ../.env

# Editar con tus keys (todas son gratis)
nano ../.env
```

**API Keys necesarias:**

| Servicio | Gratis? | Para qué | Obtener |
|----------|---------|----------|---------|
| Groq | ✅ Sin tarjeta | LLM principal (llama-3.3-70b) | [console.groq.com](https://console.groq.com) |
| OpenRouter | ✅ Sin tarjeta | LLM fallback (modelos :free) | [openrouter.ai](https://openrouter.ai) |
| Resend | ✅ 3000/mes | Envío de emails | [resend.com](https://resend.com) |
| Hunter.io | ✅ 25/mes | Buscar emails (opcional) | [hunter.io](https://hunter.io) |

### 3. Personalizar tu perfil

Editá `context.md` con toda tu información. Este archivo es la **fuente de verdad** que el LLM usa para adaptar tu CV y responder preguntas de screening.

Buscá las secciones marcadas con `[COMPLETAR]` y amplialas.

### 4. Ejecutar

```bash
# Desde la raíz del proyecto:

# Modo seguro: todo excepto enviar/aplicar
python -m agent.main --mode email --dry-run

# Aplicar en portales (ves el browser en acción)
python -m agent.main --mode apply --headed --confirm --max 3

# Enviar cold emails a job listings
python -m agent.main --mode email --max 5

# Deep research de empresas de Mendoza
python -m agent.main --mode prospect --max 10

# Todo junto en dry-run
python -m agent.main --mode full --dry-run
```

## 🛠️ Opciones CLI

```
Opciones generales:
  --mode {apply,email,prospect,full}  Modo de operación (requerido)
  --dry-run                           Todo excepto enviar/aplicar
  --max N                             Máximo de aplicaciones/emails
  --search "query"                    Override de búsqueda
  --location "lugar"                  Override de ubicación
  --min-score N                       Score mínimo de relevancia (default: 40)

Modo Apply:
  --headed                            Ver browser en tiempo real
  --confirm                           Pausa antes de cada submit

Caching:
  --skip-scrape                       Usar jobs cacheados
  --skip-crawl                        Usar empresas cacheadas
```

## 📁 Estructura

```
agent/
├── main.py               # Orquestador CLI
├── config.py             # Configuración central
├── context.md            # Tu perfil expandido (fuente de verdad)
├── requirements.txt      # Dependencias Python
│
├── scraper/              # Scraping multi-portal (LinkedIn, Indeed, etc.)
├── prospector/           # Deep research: empresas, emails, ranking
├── ai/                   # LLM client, CV adapter, email writer
├── applier/              # browser-use agent (aplicación autónoma)
├── sender/               # Envío de emails via Resend
├── pdf/                  # Generación de PDF (reutiliza Node.js existente)
├── utils/                # Logger, utilidades
└── data/                 # Cache de jobs, empresas, historial
    ├── seed_companies.json   # Empresas semilla de Mendoza
    └── templates/            # Templates de emails
```

## 🧠 Cómo funciona

### Adaptación de CV
El LLM lee tu `context.md` (toda tu info) y el `resume.json` base. Para cada oferta/empresa, **reordena y enfatiza** lo relevante sin inventar nada. Genera un PDF personalizado.

### browser-use (Modo Apply)
Un agente de IA controla el browser como lo haría un humano. Le das la URL del job y tu CV, y él:
1. Navega al portal
2. Hace click en "Apply"
3. Rellena el formulario con tus datos
4. Sube tu CV
5. Responde preguntas de screening
6. Envía la aplicación

### Deep Research (Modo Prospect)
1. Scrapea directorios de Mendoza (Polo TIC, Competitividad Mendoza)
2. Crawlea cada website de empresa buscando emails
3. El LLM evalúa qué empresas necesitan tu perfil
4. Genera cold emails personalizados
5. Envía con tu CV adaptado adjunto

## 💰 Costo Total: $0

Todo el stack usa tiers gratuitos:
- **Groq**: LLM rápido y gratis (llama-3.3-70b)
- **OpenRouter**: Modelos :free como fallback
- **Resend**: 3000 emails/mes gratis
- **Hunter.io**: 25 búsquedas/mes gratis (opcional)
- **python-jobspy**: Open source
- **browser-use**: Open source
- **Playwright**: Open source

## ⚠️ Notas Importantes

- **Empezá siempre con `--dry-run`** para verificar que todo funcione
- **Usá `--headed --confirm`** en modo apply para ver y aprobar cada aplicación
- **LinkedIn puede bloquear** si aplicás demasiado rápido — el sistema tiene delays automáticos
- **Revisá `context.md`** regularmente — cuanto más completo, mejores resultados
- Los emails se logean en `data/applications.json` para evitar duplicados
