# AI QA Gherkin Generator

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](#requisitos)
[![Status](https://img.shields.io/badge/status-MVP%20en%20progreso-orange.svg)](#estado-del-proyecto)
[![License](https://img.shields.io/badge/license-Internal-lightgrey.svg)](#)

Automatiza la generación de escenarios **Gherkin** para QA usando contexto de negocio y técnico desde:
- **Jira** (historia, descripción, criterios de aceptación)
- **Confluence** (documentación funcional/técnica)
- **GitHub** (PRs/commits relacionados por issue key)
- **Xray** (opcional: publicación de features/casos)

---

## Tabla de contenido

- [Resumen ejecutivo](#resumen-ejecutivo)
- [Arquitectura](#arquitectura)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Uso rápido](#uso-rápido)
- [Troubleshooting](#troubleshooting)
- [Estado del proyecto](#estado-del-proyecto)
- [Roadmap](#roadmap)

---

## Resumen ejecutivo

Este proyecto busca estandarizar cómo QA construye casos de prueba BDD:
1. Recupera contexto real de Jira/Confluence/GitHub.
2. Consolida información en una sola entrada.
3. Genera escenarios Gherkin de mayor calidad y trazabilidad.
4. (Opcional) publica artefactos en Xray.

> Resultado esperado: menos ambigüedad, mejor cobertura funcional y menor tiempo de preparación de pruebas.

---

## Arquitectura

```text
[Jira] --------\
                \
[Confluence] ----> [Context Builder] ---> [LLM Prompting] ---> [Gherkin .feature]
                /
[GitHub] ------/                               |
                                               +--> (Opcional) [Xray]
```

---

## Requisitos

- Python **3.11+**
- Acceso API a:
  - Jira Cloud
  - Confluence Cloud
  - GitHub
  - Xray Cloud (opcional)

---

## Instalación

```bash
python -m venv .venv
```

### Activar entorno virtual

**Windows (PowerShell)**
```bash
. .venv/Scripts/Activate.ps1
```

**Linux/macOS**
```bash
source .venv/bin/activate
```

### Instalar dependencias

```bash
pip install -r requirements.txt
```

Opcional recomendado (modo editable):
```bash
pip install -e .
```

---

## Configuración

Crear archivo `.env` en la raíz del proyecto:

```env
# Jira
JIRA_BASE_URL=https://<tu-dominio>.atlassian.net
JIRA_EMAIL=<tu-email>
JIRA_API_TOKEN=<tu-token>
JIRA_TIMEOUT_SECONDS=30

# Confluence
CONFLUENCE_BASE_URL=https://<tu-dominio>.atlassian.net/wiki
CONFLUENCE_EMAIL=<tu-email>
CONFLUENCE_API_TOKEN=<tu-token>
CONFLUENCE_TIMEOUT_SECONDS=30

# GitHub
GIT_API_BASE_URL=https://api.github.com
GIT_TOKEN=<github_pat>
GIT_TIMEOUT_SECONDS=30

# Xray (opcional)
XRAY_BASE_URL=https://xray.cloud.getxray.app
XRAY_CLIENT_ID=<client-id>
XRAY_CLIENT_SECRET=<client-secret>
XRAY_TIMEOUT_SECONDS=30
```

### Proveedores LLM

El comando `--use-llm` usa `LLM_PROVIDER` para elegir proveedor. Si se solicita IA y el proveedor falla, el pipeline falla explicitamente en vez de generar escenarios con fallback silencioso.

GitHub Models, recomendado cuando la organizacion tiene acceso empresarial a GitHub Models:

```env
LLM_PROVIDER=github_models
GITHUB_MODELS_TOKEN=<github_pat_con_models_read>
GITHUB_MODELS_MODEL=openai/gpt-4.1
GITHUB_MODELS_ORG=<org-opcional>
```

Azure OpenAI / Microsoft Foundry:

```env
LLM_PROVIDER=azure_openai
AZURE_OPENAI_API_KEY=<azure-key>
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=<deployment-name>
AZURE_OPENAI_API_VERSION=2024-10-21
```

Endpoint compatible con OpenAI, Ollama o LM Studio:

```env
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://<endpoint>/v1
LLM_API_KEY=<api-key>
LLM_MODEL=<model>

# Local sin cuota externa
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=llama3.1
```

### Reglas de dominio Gherkin

Las reglas de dominio usadas para agrupar `Regla:`, tags funcionales, correcciones de redacciÃ³n, escenarios de permisos/i18n y outlines de extensiones viven en:

```text
src/ai_qa_gherkin/resources/domain_rules.json
```

Para usar reglas propias sin tocar cÃ³digo Python, copia ese JSON, ajusta patrones/tags/tÃ­tulos y apunta la variable:

```env
GHERKIN_DOMAIN_RULES_FILE=C:\ruta\mi-domain-rules.json
```

> Seguridad: no subir `.env` al repositorio.

---

## Uso rápido

Si no instalaste en editable (`pip install -e .`), define `PYTHONPATH=src`.

### Smoke Jira
```bash
python scripts/smoke_jira_client.py DYF-4325
```

### Smoke Confluence
```bash
python scripts/smoke_confluence_client.py "DYF-4325" 5
```

### Smoke GitHub
```bash
python scripts/smoke_git_client.py --owner imedcl --repo cme-cme --issue-key DYF-4325 --limit 5
```

---

## Troubleshooting

### 1) GitHub `401 Bad credentials`
**Causas comunes**
- PAT inválido o expirado
- token de una cuenta sin acceso al repo
- token sin autorización SSO para la organización

**Acción**
- generar PAT desde la cuenta correcta
- autorizar SSO (si aplica)
- validar con:
  - `GET /user`
  - `GET /repos/{owner}/{repo}`

---

### 2) Confluence devuelve URL vacía
El cliente ya contempla fallback:
1. `_links.base + _links.webui`
2. `CONFLUENCE_BASE_URL + webui`
3. `viewpage.action?pageId=<id>`

---

### 3) Acceptance Criteria vacío en Jira
Validar que el issue tenga AC en `description` (ADF), idealmente en `codeBlock` con `language=gherkin`.

> Nota: En este entorno, `customfield_10000` corresponde a metadata de development (PRs), no AC.

---

## Estado del proyecto

- ✅ `jira_client.py` validado
- ✅ `confluence_client.py` validado
- ✅ `git_client.py` validado
- ⏳ `xray_client.py` pendiente de smoke/end-to-end
- ⏳ `build_test_context(issue_key)` pendiente
- ⏳ generación automática de `.feature` pendiente

---

## Roadmap

- [ ] Implementar `build_test_context(issue_key)` (Jira + Confluence + GitHub)
- [ ] Definir plantilla de prompt productiva para generación Gherkin
- [ ] Exportar `.feature` con convenciones del equipo
- [ ] Integrar publicación en Xray
- [ ] Agregar tests unitarios y de integración CI
- [ ] Documentar métricas de calidad (cobertura de reglas, duplicados, claridad)

---

## Contribución interna

1. Crear branch feature/fix.
2. Mantener cambios pequeños y trazables.
3. Adjuntar evidencia de smoke en PR.
4. Solicitar revisión cruzada QA + Dev.

---

## Contacto

Equipo QA Automation / Calidad de Software.
# AI QA Gherkin Generator

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](#requisitos)
[![Status](https://img.shields.io/badge/status-MVP%20en%20progreso-orange.svg)](#estado-del-proyecto)
[![License](https://img.shields.io/badge/license-Internal-lightgrey.svg)](#)

Automatiza la generación de escenarios **Gherkin** para QA usando contexto de negocio y técnico desde:
- **Jira** (historia, descripción, criterios de aceptación)
- **Confluence** (documentación funcional/técnica)
- **GitHub** (PRs/commits relacionados por issue key)
- **Xray** (opcional: publicación de features/casos)

---

## Tabla de contenido

- [Resumen ejecutivo](#resumen-ejecutivo)
- [Arquitectura](#arquitectura)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Uso rápido](#uso-rápido)
- [Troubleshooting](#troubleshooting)
- [Estado del proyecto](#estado-del-proyecto)
- [Roadmap](#roadmap)

---

## Resumen ejecutivo

Este proyecto busca estandarizar cómo QA construye casos de prueba BDD:
1. Recupera contexto real de Jira/Confluence/GitHub.
2. Consolida información en una sola entrada.
3. Genera escenarios Gherkin de mayor calidad y trazabilidad.
4. (Opcional) publica artefactos en Xray.

> Resultado esperado: menos ambigüedad, mejor cobertura funcional y menor tiempo de preparación de pruebas.

---

## Arquitectura

```text
[Jira] --------\
                \
[Confluence] ----> [Context Builder] ---> [LLM Prompting] ---> [Gherkin .feature]
                /
[GitHub] ------/                               |
                                               +--> (Opcional) [Xray]
```

---

## Requisitos

- Python **3.11+**
- Acceso API a:
  - Jira Cloud
  - Confluence Cloud
  - GitHub
  - Xray Cloud (opcional)

---

## Instalación

```bash
python -m venv .venv
```

### Activar entorno virtual

**Windows (PowerShell)**
```bash
. .venv/Scripts/Activate.ps1
```

**Linux/macOS**
```bash
source .venv/bin/activate
```

### Instalar dependencias

```bash
pip install -r requirements.txt
```

Opcional recomendado (modo editable):
```bash
pip install -e .
```

---

## Configuración

Crear archivo `.env` en la raíz del proyecto:

```env
# Jira
JIRA_BASE_URL=https://<tu-dominio>.atlassian.net
JIRA_EMAIL=<tu-email>
JIRA_API_TOKEN=<tu-token>
JIRA_TIMEOUT_SECONDS=30

# Confluence
CONFLUENCE_BASE_URL=https://<tu-dominio>.atlassian.net/wiki
CONFLUENCE_EMAIL=<tu-email>
CONFLUENCE_API_TOKEN=<tu-token>
CONFLUENCE_TIMEOUT_SECONDS=30

# GitHub
GIT_API_BASE_URL=https://api.github.com
GIT_TOKEN=<github_pat>
GIT_TIMEOUT_SECONDS=30

# Xray (opcional)
XRAY_BASE_URL=https://xray.cloud.getxray.app
XRAY_CLIENT_ID=<client-id>
XRAY_CLIENT_SECRET=<client-secret>
XRAY_TIMEOUT_SECONDS=30
```

> Seguridad: no subir `.env` al repositorio.

---

## Uso rápido

Si no instalaste en editable (`pip install -e .`), define `PYTHONPATH=src`.

### Smoke Jira
```bash
python scripts/smoke_jira_client.py DYF-4325
```

### Smoke Confluence
```bash
python scripts/smoke_confluence_client.py "DYF-4325" 5
```

### Smoke GitHub
```bash
python scripts/smoke_git_client.py --owner imedcl --repo cme-cme --issue-key DYF-4325 --limit 5
```

---

## Troubleshooting

### 1) GitHub `401 Bad credentials`
**Causas comunes**
- PAT inválido o expirado
- token de una cuenta sin acceso al repo
- token sin autorización SSO para la organización

**Acción**
- generar PAT desde la cuenta correcta
- autorizar SSO (si aplica)
- validar con:
  - `GET /user`
  - `GET /repos/{owner}/{repo}`

---

### 2) Confluence devuelve URL vacía
El cliente ya contempla fallback:
1. `_links.base + _links.webui`
2. `CONFLUENCE_BASE_URL + webui`
3. `viewpage.action?pageId=<id>`

---

### 3) Acceptance Criteria vacío en Jira
Validar que el issue tenga AC en `description` (ADF), idealmente en `codeBlock` con `language=gherkin`.

> Nota: En este entorno, `customfield_10000` corresponde a metadata de development (PRs), no AC.

---

## Estado del proyecto

- ✅ `jira_client.py` validado
- ✅ `confluence_client.py` validado
- ✅ `git_client.py` validado
- ⏳ `xray_client.py` pendiente de smoke/end-to-end
- ⏳ `build_test_context(issue_key)` pendiente
- ⏳ generación automática de `.feature` pendiente

---

## Roadmap

- [ ] Implementar `build_test_context(issue_key)` (Jira + Confluence + GitHub)
- [ ] Definir plantilla de prompt productiva para generación Gherkin
- [ ] Exportar `.feature` con convenciones del equipo
- [ ] Integrar publicación en Xray
- [ ] Agregar tests unitarios y de integración CI
- [ ] Documentar métricas de calidad (cobertura de reglas, duplicados, claridad)

---

## Contribución interna

1. Crear branch feature/fix.
2. Mantener cambios pequeños y trazables.
3. Adjuntar evidencia de smoke en PR.
4. Solicitar revisión cruzada QA + Dev.

---

## Contacto

Equipo QA Automation / Calidad de Software.
