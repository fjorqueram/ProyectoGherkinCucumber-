# Explicacion detallada de README.md

Este documento resume `README.md`.

## 1) Objetivo

`README.md` documenta el proposito, instalacion, configuracion y uso rapido del proyecto **AI QA Gherkin Generator**.

El proyecto busca automatizar generacion de escenarios Gherkin usando contexto desde:

- Jira.
- Confluence.
- GitHub.
- Xray.
- proveedores LLM.

## 2) Resumen ejecutivo

Explica que el sistema:

1. Recupera contexto real.
2. Consolida informacion.
3. Genera escenarios Gherkin con mejor trazabilidad.
4. Opcionalmente publica artefactos en Xray.

## 3) Arquitectura

Muestra flujo conceptual:

```text
Jira + Confluence + GitHub -> Context Builder -> LLM Prompting -> Gherkin .feature
```

Con salida opcional hacia Xray.

## 4) Requisitos

Declara:

- Python 3.11+.
- acceso API a Jira Cloud.
- acceso API a Confluence Cloud.
- acceso API a GitHub.
- Xray Cloud opcional.

## 5) Instalacion

Indica crear entorno virtual:

```bash
python -m venv .venv
```

Activarlo en Windows o Linux/macOS.

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Opcional:

```bash
pip install -e .
```

## 6) Configuracion

Documenta variables `.env` para:

- Jira.
- Confluence.
- GitHub.
- Xray.
- LLM providers.
- reglas de dominio.

Nota de seguridad:

Indica no subir `.env` al repositorio.

## 7) Proveedores LLM

Describe proveedores:

- GitHub Models.
- Azure OpenAI.
- OpenAI-compatible.
- Ollama.
- LM Studio.

Punto importante:

Si se usa `--use-llm` y falla el proveedor, el pipeline falla explicitamente en vez de usar fallback silencioso.

## 8) Reglas de dominio

Explica `domain_rules.json` y la variable:

```env
GHERKIN_DOMAIN_RULES_FILE=
```

Permite usar reglas propias sin tocar codigo Python.

## 9) Evidencia GitHub

Documenta busqueda por issue key:

- PRs.
- ramas.
- commits.
- archivos modificados.
- comparacion contra branch base.

Tambien indica que `GIT_REPO` acepta multiples repos separados por coma.

## 10) Uso rapido

Incluye smoke tests para:

- Jira.
- Confluence.
- GitHub.

## 11) Troubleshooting

Cubre:

- GitHub `401 Bad credentials`.
- Confluence con URL vacia.
- Acceptance Criteria vacio en Jira.

## 12) Estado y roadmap

Marca clientes validados y pendientes.

Roadmap incluye:

- `build_test_context(issue_key)`.
- prompt productivo.
- export `.feature`.
- publicacion Xray.
- tests CI.

## 13) Punto de cuidado

El README contiene contenido duplicado: despues de la seccion de contacto vuelve a repetir gran parte del documento desde el titulo.
