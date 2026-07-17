# Explicacion detallada de clients/__init__.py

Este documento explica `src/ai_qa_gherkin/clients/__init__.py`.

## 1) Objetivo

El archivo reexporta los clientes disponibles del paquete `clients`.

Permite importar asi:

```python
from ai_qa_gherkin.clients import JiraClient, LLMClient
```

en vez de importar desde cada archivo interno.

## 2) Clientes exportados

Importa:

- `ConfluenceClient`
- `GitClient`
- `JiraClient`
- `LLMClient`
- `XrayClient`

## 3) `LLMClient`

La version actual agrega:

```python
from ai_qa_gherkin.clients.llm_client import LLMClient
```

Esto deja disponible el cliente LLM desde el paquete `clients`.

## 4) `__all__`

Declara la API publica:

```python
__all__ = [
    "JiraClient",
    "ConfluenceClient",
    "GitClient",
    "XrayClient",
    "LLMClient",
]
```

Si alguien usa:

```python
from ai_qa_gherkin.clients import *
```

Python exportara esos cinco nombres.

## 5) Punto de cuidado

Como `LLMClient` importa `openai`, para importar `ai_qa_gherkin.clients` ahora el paquete `openai` debe estar instalado o el import podria fallar antes de instanciar el cliente.
