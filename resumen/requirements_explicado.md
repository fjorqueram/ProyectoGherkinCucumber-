# Explicacion de requirements.txt

Este documento resume `requirements.txt`.

## Objetivo

Define dependencias instalables del proyecto con rangos de versiones.

## Dependencias

- `httpx`: cliente HTTP usado por clientes Jira, Confluence, Git y Xray.
- `pydantic`: modelos y validacion de datos.
- `pydantic-settings`: carga de settings desde entorno y `.env`.
- `tenacity`: reintentos.
- `loguru`: logging.
- `python-dotenv`: carga de variables `.env`.
- `click`: CLI.
- `openai`: SDK OpenAI para `LLMClient`.
- `pytest`: framework de tests.
- `requests`: usado por scripts/debug.
- `ftfy`: reparacion de mojibake/Unicode en `TextCleaner`.

## Rango de versiones

El archivo usa limites inferiores y superiores, por ejemplo:

```text
httpx>=0.27.0,<0.28.0
```

Esto permite parches compatibles, pero evita saltos mayores que podrian romper APIs.
