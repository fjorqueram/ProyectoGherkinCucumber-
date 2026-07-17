# Explicacion detallada de llm_client.py

Este documento explica `src/ai_qa_gherkin/clients/llm_client.py`: inicializacion, llamada a OpenAI, prompt, parseo y fallback.

## 1) Objetivo

`llm_client.py` encapsula la interaccion con un modelo LLM.

Actualmente soporta OpenAI y se usa para extraer:

- reglas de negocio
- precondiciones
- happy paths
- escenarios de error
- supuestos
- riesgos

## 2) Importaciones

- `json`: construye fragmentos JSON dentro del prompt y parsea respuesta.
- `openai`: SDK oficial usado para `OpenAI`.
- `Any`: tipos flexibles.
- `tenacity.retry`: reintentos en llamadas LLM.
- `settings`: proveedor, modelo, API key, timeouts y retry.
- `get_logger`: logger contextual.

## 3) Constructor `LLMClient.__init__`

Variables:

- `self.provider`: `settings.llm_provider.lower()`.
- `self.timeout`: `settings.llm_timeout_seconds`.
- `self.client`: cliente OpenAI.
- `self.model`: modelo definido en `settings.openai_model`.

Validacion:

```python
if self.provider == "openai":
```

Solo soporta OpenAI. Cualquier otro proveedor lanza:

```python
ValueError("Unsupported LLM provider")
```

Nota de seguridad:

La API key se toma desde `settings.openai_api_key`; no se imprime.

## 4) `extract_business_rules`

Metodo decorado con retry.

Reintenta segun:

- `settings.retry_max_attempts`
- `settings.retry_min_seconds`
- `settings.retry_max_seconds`

Flujo:

1. Construye prompt con `_build_analysis_prompt`.
2. Llama `self.client.chat.completions.create`.
3. Usa mensaje system de experto QA BDD/Gherkin.
4. Usa temperatura `0.7`.
5. Respeta timeout.
6. Lee `response.choices[0].message.content`.
7. Si viene vacio, retorna fallback.
8. Si viene contenido, lo parsea con `_parse_llm_response`.

Si ocurre excepcion, loguea error y relanza.

## 5) `_get_fallback_result`

Devuelve estructura vacia:

```python
{
    "business_rules": [],
    "preconditions": [],
    "happy_paths": [],
    "error_scenarios": [],
    "assumptions": [],
    "risks": [],
}
```

Sirve cuando el LLM no devuelve contenido.

## 6) `_build_analysis_prompt`

Construye el prompt con contexto de:

- Jira issue.
- Confluence.
- Git.

Validaciones/defaults:

```python
confluence = context.get("confluence") or {}
git = context.get("git") or {}
```

Esto evita error si esas fuentes vienen como `None`.

El prompt pide JSON puro con:

- `business_rules`
- `preconditions`
- `happy_paths`
- `error_scenarios`
- `assumptions`
- `risks`

Tambien pide que cada item incluya:

- `description`
- `category`
- `priority`

## 7) `_parse_llm_response`

Intenta convertir texto del LLM a diccionario.

Primero limpia fences Markdown:

- ```json
- ```

Luego hace:

```python
json.loads(content)
```

Validacion minima:

Si faltan claves requeridas, las agrega como listas vacias:

- `business_rules`
- `preconditions`
- `happy_paths`
- `error_scenarios`

Si el JSON es invalido, retorna fallback vacio y loguea una version recortada del contenido.

## 8) Puntos de mejora

- El `try/except ImportError` alrededor de `openai.OpenAI(...)` no captura el import real, porque `openai` ya se importo al cargar el modulo.
- El retry actual reintenta cualquier excepcion del metodo, no solo errores transitorios.
- El prompt incluye contenido de Confluence truncado a 500 caracteres.
- Si el LLM devuelve JSON valido pero no dict, no hay validacion explicita.
