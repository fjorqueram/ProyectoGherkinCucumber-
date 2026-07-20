# Explicacion detallada de comandos.txt

Este documento resume `comandos.txt`.

## 1) Objetivo

Contiene comandos PowerShell usados para crear la estructura inicial del proyecto.

Es una especie de bitacora o script manual de scaffolding.

## 2) Crear carpetas

Usa `New-Item -ItemType Directory -Force` para crear:

- `src/ai_qa_gherkin/clients`
- `src/ai_qa_gherkin/services`
- `src/ai_qa_gherkin/prompts`
- `src/ai_qa_gherkin/utils`
- `templates`
- `output/summaries`
- `output/features`
- `output/xray_payloads`
- `output/traceability`
- `tests/fixtures`
- `features/steps`

## 3) Crear archivos raiz

Crea:

- `README.md`
- `.env.example`
- `.gitignore`
- `requirements.txt`
- `pyproject.toml`
- `Makefile`
- `AGENTS.md`

## 4) Crear paquete principal

Crea archivos como:

- `src/ai_qa_gherkin/__init__.py`
- `config.py`
- `logger.py`
- `models.py`
- `orchestrator.py`
- `cli.py`

Nota:

Actualmente el proyecto usa tambien `src/ai_qa_gherkin/models/domain.py`, por lo que este comando refleja una etapa anterior del scaffolding.

## 5) Crear clients

Crea:

- `jira_client.py`
- `confluence_client.py`
- `git_client.py`
- `xray_client.py`
- `llm_client.py`

## 6) Crear services

Crea:

- `collector_service.py`
- `analysis_service.py`
- `gherkin_service.py`
- `validator_service.py`
- `summary_service.py`
- `publish_service.py`
- `execution_service.py`

## 7) Crear prompts, templates, utils y tests

Incluye:

- `system_prompt.txt`
- `gherkin_prompt.txt`
- `feature.template.j2`
- `text_utils.py`
- `traceability.py`
- tests principales.

## 8) `.gitkeep`

Crea `.gitkeep` en carpetas output para mantenerlas en Git aunque esten vacias.

## 9) Dependencias

Al final incluye:

```powershell
pip install pydantic pydantic-settings python-dotenv loguru tenacity httpx
```

## 10) Punto de cuidado

No es un script idempotente formal con validaciones; es una lista de comandos manuales.
