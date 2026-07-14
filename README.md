# ai-qa-gherkin

Generador de escenarios **Gherkin** para QA usando contexto desde:
- Jira (historia + criterios)
- Confluence (documentación funcional/técnica)
- GitHub (PRs/commits relacionados)
- (opcional) Xray para publicación de features/casos

---

## Requisitos

- Python 3.11+
- Cuenta/API access a:
  - Jira Cloud
  - Confluence Cloud
  - GitHub
  - Xray Cloud (opcional)

---

## Instalación

```bash
python -m venv .venv
# Windows (PowerShell)
. .venv/Scripts/Activate.ps1
# Linux/macOS
# source .venv/bin/activate

pip install -r requirements.txt
```

> Opcional recomendado para imports limpios:
```bash
pip install -e .
```

---

## Configuración

Crea `.env` basado en `.env.example`:

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

---

## Smoke tests de clientes

> Si no usas `pip install -e .`, define `PYTHONPATH=src`.

### Jira
```bash
python scripts/smoke_jira_client.py DYF-4325
```

### Confluence
```bash
python scripts/smoke_confluence_client.py "DYF-4325" 5
```

### GitHub
```bash
python scripts/smoke_git_client.py --owner imedcl --repo cme-cme --issue-key DYF-4325 --limit 5
```

---

## Estado actual (validado)

- ✅ `jira_client.py`: obtiene issue y extrae AC desde `description` (ADF/Gherkin).
- ✅ `confluence_client.py`: busca páginas y arma URL navegable.
- ✅ `git_client.py`: encuentra PRs relacionados por issue key.
- ⏳ `xray_client.py`: pendiente smoke/end-to-end.

---

## Notas importantes

- En este proyecto, `customfield_10000` **NO** corresponde a Acceptance Criteria (es campo de development/PRs).
- Los criterios se extraen desde `description` de Jira (bloques `gherkin`).
- Si GitHub devuelve 401/403, validar:
  - token correcto,
  - permisos al repo,
  - SSO autorizado para la organización.

---

## Estructura sugerida

```text
src/ai_qa_gherkin/
  clients/
    jira_client.py
    confluence_client.py
    git_client.py
    xray_client.py
scripts/
  smoke_jira_client.py
  smoke_confluence_client.py
  smoke_git_client.py
```

---

## Próximos pasos

1. Crear `build_test_context(issue_key)` que unifique Jira+Confluence+Git.
2. Generar prompt robusto para LLM con contexto consolidado.
3. Exportar `.feature` y opcionalmente publicar a Xray.
4. Agregar tests unitarios a extractores ADF/Gherkin.
