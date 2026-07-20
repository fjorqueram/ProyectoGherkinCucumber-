# AI QA Gherkin Generator

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](#requisitos)
[![Status](https://img.shields.io/badge/status-MVP%20en%20progreso-orange.svg)](#estado)
[![License](https://img.shields.io/badge/license-Internal-lightgrey.svg)](#licencia)

Generador de escenarios **Gherkin** para QA basado en evidencia real de:
- Jira
- Confluence
- GitHub
- Xray (opcional)

## ⚠️ Aviso
Proyecto de referencia técnica. La instalación puede variar por entorno (permisos, SSO, red corporativa, credenciales).

---

## ¿Qué resuelve?
- Reduce ambigüedad al diseñar pruebas BDD.
- Mejora cobertura funcional con contexto consolidado.
- Acelera creación de escenarios `.feature`.

---

## Arquitectura (alto nivel)
```text
[Jira] ----\
[Confluence] ---> [Context Builder] ---> [LLM Prompting] ---> [.feature]
[GitHub] ---/                                  |
                                              +--> [Xray] (opcional)
```

---

## Requisitos
- Python 3.11+
- Acceso API a Jira, Confluence, GitHub
- Xray Cloud (opcional)

---

## Instalación
```bash
python -m venv .venv
# Windows
. .venv/Scripts/Activate.ps1
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
# opcional
pip install -e .
```

---

## Configuración (`.env`)
```env
# Jira
JIRA_BASE_URL=https://<tu-dominio>.atlassian.net
JIRA_EMAIL=<tu-email>
JIRA_API_TOKEN=<tu-token>

# Confluence
CONFLUENCE_BASE_URL=https://<tu-dominio>.atlassian.net/wiki
CONFLUENCE_EMAIL=<tu-email>
CONFLUENCE_API_TOKEN=<tu-token>

# GitHub
GIT_API_BASE_URL=https://api.github.com
GIT_TOKEN=<github_pat>
GIT_OWNER=<org-o-usuario>
GIT_REPO=<repo-o-lista-por-comas>
GIT_BASE_BRANCH=develop

# Xray (opcional)
XRAY_BASE_URL=https://xray.cloud.getxray.app
XRAY_CLIENT_ID=<client-id>
XRAY_CLIENT_SECRET=<client-secret>
```

### Proveedor LLM (ejemplo)
```env
LLM_PROVIDER=github_models
GITHUB_MODELS_TOKEN=<pat_con_models_read>
GITHUB_MODELS_MODEL=openai/gpt-4.1
```

---

## Uso rápido
```bash
gherkin generate DYF-4275 --use-llm
```

Smokes:
```bash
python scripts/smoke_jira_client.py DYF-4325
python scripts/smoke_confluence_client.py "DYF-4325" 5
python scripts/smoke_git_client.py --owner imedcl --repo cme-cme --issue-key DYF-4325 --limit 5
```

---

## Estructura recomendada
```text
src/ai_qa_gherkin/
  clients/
    jira_client.py
    confluence_client.py
    git_client.py
    xray_client.py
  services/
    context_builder.py
    prompt_builder.py
    gherkin_generator.py
  resources/
    domain_rules.json
  cli.py
```

---

## Estado
- ✅ Jira client validado
- ✅ Confluence client validado
- ✅ Git client validado
- ⏳ Xray client e2e pendiente
- ⏳ Context Builder completo pendiente
- ⏳ Exportación automática `.feature` pendiente

---

## Seguridad
- No subir `.env`
- No exponer tokens en logs/salidas
- Usar mínimo privilegio en credenciales

---

## Licencia
Internal.