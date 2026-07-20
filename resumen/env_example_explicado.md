# Explicacion detallada de .env.example

Este documento resume `.env.example`.

## 1) Objetivo

Sirve como plantilla de variables de entorno para configurar el proyecto.

No debe contener secretos reales.

## 2) App

- `APP_ENV`: ambiente, por defecto `dev`.
- `LOG_LEVEL`: nivel de logs.
- `GHERKIN_DOMAIN_RULES_FILE`: ruta opcional a reglas de dominio externas.

## 3) Jira

- `JIRA_BASE_URL`
- `JIRA_EMAIL`
- `JIRA_API_TOKEN`
- `JIRA_TIMEOUT_SECONDS`

Se usan para consultar issues y metadata Jira.

## 4) Confluence

- `CONFLUENCE_BASE_URL`
- `CONFLUENCE_EMAIL`
- `CONFLUENCE_API_TOKEN`
- `CONFLUENCE_TIMEOUT_SECONDS`

Se usan para buscar y leer paginas Confluence.

## 5) GitHub

- `GIT_PROVIDER`
- `GIT_API_BASE_URL`
- `GIT_TOKEN`
- `GIT_TIMEOUT_SECONDS`
- `GIT_OWNER`
- `GIT_REPO`
- `GIT_BASE_BRANCH`

`GIT_REPO` puede tener multiples repos separados por coma.

## 6) Xray

- `XRAY_BASE_URL`
- `XRAY_CLIENT_ID`
- `XRAY_CLIENT_SECRET`
- `XRAY_TIMEOUT_SECONDS`

Usado por `XrayClient`.

## 7) LLM general

- `LLM_PROVIDER`
- `LLM_MODEL`
- `LLM_TIMEOUT_SECONDS`
- `LLM_MAX_TOKENS`
- `LLM_TEMPERATURE`

Permite configurar proveedor y parametros base.

## 8) OpenAI

- `OPENAI_API_KEY`
- `OPENAI_MODEL`

## 9) GitHub Models

- `GITHUB_MODELS_TOKEN`
- `GITHUB_MODELS_MODEL`
- `GITHUB_MODELS_ORG`
- `GITHUB_MODELS_BASE_URL`

Nota:

El comentario indica que `GITHUB_TOKEN` puede usarse si `GITHUB_MODELS_TOKEN` esta vacio.

## 10) Azure OpenAI

- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_OPENAI_API_VERSION`

## 11) OpenAI compatible y local

- `LLM_BASE_URL`
- `LLM_API_KEY`
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `LM_STUDIO_BASE_URL`
- `LM_STUDIO_MODEL`

## 12) Retry

- `RETRY_MAX_ATTEMPTS`
- `RETRY_MIN_SECONDS`
- `RETRY_MAX_SECONDS`

## 13) Seguridad

Los valores `replace_me` son placeholders.

El archivo real `.env` no debe subirse ni imprimirse porque contiene tokens y secretos.
