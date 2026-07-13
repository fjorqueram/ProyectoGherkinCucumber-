# Explicación detallada de jira_client.py

Este documento explica en detalle qué hace [src/ai_qa_gherkin/clients/jira_client.py](src/ai_qa_gherkin/clients/jira_client.py), clase por clase, método por método, validación por validación y variable por variable.

---

## 1) Objetivo del archivo

El archivo implementa un cliente HTTP para consumir la API de Jira.

Su propósito es:
1. Conectar con Jira usando credenciales desde configuración.
2. Obtener datos brutos de issues (JSON).
3. Parsear y transformar esos datos al modelo `JiraIssue`.
4. Extraer texto, criterios de aceptación y enlaces desde formato ADF (Atlassian Document Format).
5. Manejar errores transitorios (con retry) y permanentes (sin retry).

---

## 2) Importaciones

```python
from __future__ import annotations
from typing import Any
import httpx
from ai_qa_gherkin.config import settings
from ai_qa_gherkin.logger import get_logger
from ai_qa_gherkin.models import JiraIssue
from ai_qa_gherkin.retry import retry_policy, TransientError, PermanentError
```

### `from __future__ import annotations`
- Permite usar sintaxis moderna de type hints sin importar tipos explícitamente.
- Mejora compatibilidad con versiones antiguas de Python.

### `from typing import Any`
- Tipo genérico para valores sin restricción de tipo.

### `import httpx`
- Librería HTTP moderna (similar a requests, pero async-ready).
- Se usa para hacer peticiones GET a Jira.

### `from ai_qa_gherkin.config import settings`
- Configuración global con credenciales y timeouts.

### `from ai_qa_gherkin.logger import get_logger`
- Logger contextual para registrar eventos.

### `from ai_qa_gherkin.models import JiraIssue`
- Modelo Pydantic destino que el cliente debe generar.

### `from ai_qa_gherkin.retry import retry_policy, TransientError, PermanentError`
- Decorador de retry y tipos de error para clasificar fallos.

---

## 3) Logger contextual

```python
log = get_logger("jira_client")
```

Crea un logger con contexto operacional `"jira_client"`.

Cada log emitido llevará información de servicio y operación automáticamente.

---

## 4) Clase JiraClient

### 4.1 Constructor (`__init__`)

```python
def __init__(self) -> None:
    self.base_url = settings.jira_base_url.rstrip("/")
    self.auth = (settings.jira_email, settings.jira_api_token)
    self.timeout = settings.jira_timeout_seconds
```

Qué hace:
Inicializa el cliente con valores desde configuración.

#### `self.base_url = settings.jira_base_url.rstrip("/")`
- Lee URL base desde configuración.
- `.rstrip("/")` elimina trailing slash para evitar URLs dobles (`//rest/api...`).
- Ejemplo: `"https://imed.atlassian.net"`.

#### `self.auth = (settings.jira_email, settings.jira_api_token)`
- Tupla (email, token) para autenticación HTTP Basic.
- httpx manejará encoding y header `Authorization` automáticamente.

#### `self.timeout = settings.jira_timeout_seconds`
- Timeout global para requests (por defecto 20 segundos desde config).
- Evita que la app se cuelgue si Jira responde lentamente.

Validaciones implícitas:
- Si `settings.jira_base_url` es vacío, `.rstrip("/")` devuelve vacío (sin error inmediato).
- La validación real ocurre al hacer la primera request.

---

### 4.2 Método `_handle_http_error`

```python
def _handle_http_error(self, response: httpx.Response) -> None:
    code = response.status_code
    msg = f"Jira error: {code} - {response.text[:300]}"

    if code in {429, 502, 503, 504}:
        raise TransientError(msg)
    if code >= 400:
        raise PermanentError(msg)
```

Propósito:
Clasificar errores HTTP como transitorios (reintentables) o permanentes (no reintentables).

#### Parámetro `response: httpx.Response`
- Respuesta HTTP del servidor.

#### Lógica de clasificación:

1. **Códigos transitorios** (429, 502, 503, 504):
   - 429: Rate limiting/throttling → retry útil.
   - 502/503/504: Fallos temporales de gateway → retry útil.
   - Se lanza `TransientError` para activar retry automático.

2. **Códigos de error permanentes** (cualquier ≥ 400 que no sea transitorio):
   - 401: No autorizado.
   - 403: Prohibido.
   - 404: No encontrado.
   - Se lanza `PermanentError` para no reintentar.

#### `msg = f"Jira error: {code} - {response.text[:300]}"`
- Construye mensaje de error.
- `[:300]` limita respuesta a 300 caracteres para evitar logs gigantescos.

---

### 4.3 Método `get_issue_raw` (con retry)

```python
@retry_policy()
def get_issue_raw(self, issue_key: str) -> dict[str, Any]:
    url = f"{self.base_url}/rest/api/3/issue/{issue_key}"

    # Pedimos solo lo necesario. Ojo: customfield_10000 NO es AC en tu caso.
    params = {"fields": "summary,description,issuelinks,labels,project,issuetype"}

    log.info(f"Fetching Jira issue {issue_key}")

    try:
        with httpx.Client(auth=self.auth, timeout=self.timeout) as client:
            r = client.get(url, params=params)
            if r.status_code >= 400:
                self._handle_http_error(r)
            data = r.json()
            if not isinstance(data, dict):
                raise PermanentError(f"Invalid Jira payload for {issue_key}")
            return data
    except httpx.TimeoutException as e:
        raise TransientError(f"Jira request timed out: {e}") from e
    except httpx.NetworkError as e:
        raise TransientError(f"Jira network error: {e}") from e
```

Propósito:
Obtener datos brutos de un issue desde Jira.

#### Decorador `@retry_policy()`
- Envuelve el método con lógica de retry automático.
- Si lanza `TransientError`, reintenta.
- Si agota intentos, relanza la excepción.

#### Parámetro `issue_key: str`
- Identificador del issue (ej: `"DYF-4325"`).

#### Construcción de URL
```python
url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
```
- Ejemplo: `"https://imed.atlassian.net/rest/api/3/issue/DYF-4325"`.

#### Parámetros de query (`params`) - CAMBIO IMPORTANTE

```python
# Pedimos solo lo necesario. Ojo: customfield_10000 NO es AC en tu caso.
params = {"fields": "summary,description,issuelinks,labels,project,issuetype"}
```

**Qué cambió:**
- Antes pedía: `summary,description,issuetype,project,labels,customfield_10000`
- Ahora pide: `summary,description,issuelinks,labels,project,issuetype`

**Cambios específicos:**
1. **Removido**: `customfield_10000` (porque el comentario aclara que NO es el campo de Acceptance Criteria en tu instancia).
2. **Agregado**: `issuelinks` (necesario para extraer issues relacionados).
3. **Orden reorganizado**: para claridad (fields agrupados lógicamente).

**Propósito:**
- Solicita solo campos necesarios a Jira para optimizar.
- `issuelinks` es crítico para el método `_extract_links()`.

#### Logging
```python
log.info(f"Fetching Jira issue {issue_key}")
```
- Registra inicio de fetch.

#### Contexto HTTP con autenticación
```python
with httpx.Client(auth=self.auth, timeout=self.timeout) as client:
```
- Crea cliente HTTP con credenciales y timeout.
- Context manager garantiza cierre de conexión.

#### Obtención y validación de response
```python
r = client.get(url, params=params)
if r.status_code >= 400:
    self._handle_http_error(r)
data = r.json()
if not isinstance(data, dict):
    raise PermanentError(f"Invalid Jira payload for {issue_key}")
return data
```

**Validación nueva agregada:**
```python
if not isinstance(data, dict):
    raise PermanentError(f"Invalid Jira payload for {issue_key}")
```
- Después de deserializar JSON, valida que sea dict.
- Si es lista, string u otro tipo, lanza `PermanentError` (no reintentar).
- Esto evita que errores de tipo se procesen erróneamente.

#### Manejo de excepciones de red
```python
except httpx.TimeoutException as e:
    raise TransientError(f"Jira request timed out: {e}") from e
except httpx.NetworkError as e:
    raise TransientError(f"Jira network error: {e}") from e
```
- Timeout y errores de red se clasifican como transitorios.
- `from e` mantiene cadena de causas para diagnóstico.

---

### 4.4 Método `_extract_text_from_adf` (auxiliar recursivo)

```python
def _extract_text_from_adf(self, node: Any) -> str:
    """Extrae texto plano de ADF."""
    if isinstance(node, dict):
        current = node.get("text", "")
        content = node.get("content", []) or []
        return current + "".join(self._extract_text_from_adf(c) for c in content)
    if isinstance(node, list):
        return "".join(self._extract_text_from_adf(x) for x in node)
    return ""
```

Propósito:
Extraer texto plano desde ADF (Atlassian Document Format, formato de árbol JSON).

ADF es el formato interno de Confluence/Jira para rich text (similar a AST).

Ejemplo de ADF:
```json
{
  "type": "doc",
  "content": [
    {"type": "paragraph", "content": [{"type": "text", "text": "Hola"}]}
  ]
}
```

#### Lógica:

1. Si nodo es dict:
   - Extrae campo "text" si existe.
   - Recursivamente procesa "content" (lista de hijos).

2. Si nodo es lista:
   - Recursivamente procesa cada elemento.

3. Si nodo es otro tipo (string, int, etc.):
   - Retorna cadena vacía.

Resultado:
Concatena todo texto plano encontrado, ignorando estructura ADF.

---

### 4.5 Método `_extract_gherkin_codeblocks_from_adf` (auxiliar)

```python
def _extract_gherkin_codeblocks_from_adf(self, adf: dict[str, Any]) -> str:
    """Devuelve texto de codeBlocks language=gherkin (si hay varios, concatena)."""
    blocks: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "codeBlock":
                attrs = node.get("attrs", {}) or {}
                lang = (attrs.get("language") or "").lower()
                if lang == "gherkin":
                    text = self._extract_text_from_adf(node.get("content", [])).strip()
                    if text:
                        blocks.append(text)

            for c in node.get("content", []) or []:
                walk(c)
        
        elif isinstance(node, list):
            for x in node:
                walk(x)

    walk(adf)
    return "\n\n".join(blocks).strip()
```

Propósito:
Extraer bloques de código con lenguaje "gherkin" desde ADF.

#### Estructura de búsqueda:
1. Recorre ADF recursivamente.
2. Busca nodos de tipo `"codeBlock"`.
3. Verifica que atributo `language` sea `"gherkin"` (case-insensitive).
4. Extrae texto plano del bloque.
5. Acumula en lista.

#### Normalización:
- `lang = (...).lower()` → case-insensitive.
- `.strip()` → elimina espacios alrededor.
- `if text:` → ignora bloques vacíos.

#### Resultado:
Concatena múltiples bloques con `"\n\n"`.

Uso:
Busca explícitamente Gherkin ingresado por usuario en description.

---

### 4.6 Método `_extract_ac_section_from_plain_text` (auxiliar fallback)

```python
def _extract_ac_section_from_plain_text(self, description_text: str) -> str:
    """
    Fallback si no hay codeBlock gherkin:
    intenta cortar desde 'CRITERIOS DE ACEPTACIÓN'.
    """

    if not description_text:
        return ""
    
    normalized = description_text.lower()
    markers = [
        "criterios de aceptación",
        "criterios de aceptacion",
        "acceptance criteria",
    ]

    idx = -1
    for m in markers:
        idx = normalized.find(m)
        if idx != -1:
            break

    if idx == -1:
        return ""
    
    return description_text[idx:].strip()
```

Propósito:
Si no hay codeBlock Gherkin, busca sección textual "CRITERIOS DE ACEPTACIÓN" o similares.

#### Lógica:

1. Si texto vacío, retorna vacío.
2. Normaliza a minúsculas para búsqueda case-insensitive.
3. Busca marcadores en orden:
   - "criterios de aceptación"
   - "criterios de aceptacion" (sin acento)
   - "acceptance criteria" (inglés)
4. Si encuentra, retorna desde esa posición al final.
5. Si no encuentra, retorna vacío.

Caso de uso:
Issues que no tienen bloque Gherkin pero tienen sección textual de criterios.

---

### 4.7 Método `_extract_links` (auxiliar)

```python
def _extract_links(self, fields: dict[str, Any]) -> list[str]:
    links: list[str] = []

    for item in fields.get("issuelinks", []) or []:
        inward = (item.get("inwardIssue") or {})
        outward = (item.get("outwardIssue") or {})
        if inward.get("key"):
            links.append(str(inward["key"]))
        if outward.get("key"):
            links.append(str(outward["key"]))
    return sorted(set(links))
```

Propósito:
Extraer issues relacionados (enlaces bidireccionales).

#### Estructura de issuelinks:
```json
"issuelinks": [
  {
    "inwardIssue": {"key": "PROJ-1"},
    "outwardIssue": {"key": "PROJ-2"}
  }
]
```

#### Lógica:

1. Itera sobre `fields.get("issuelinks", [])`.
2. Por cada enlace, busca `inwardIssue` y `outwardIssue`.
3. Si existen, extrae la clave (`key`).
4. Acumula todas en lista.

#### Normalización final:
```python
return sorted(set(links))
```
- `set(links)` → elimina duplicados.
- `sorted(...)` → ordena alfabéticamente.

---

### 4.8 Método `get_issue` (principal)

```python
def get_issue(self, issue_key: str) -> JiraIssue:
    """
    Siempre retorna JiraIssue o lanza excepción.
    (evita Pylance reportReturnType)
    """

    data = self.get_issue_raw(issue_key)
    if not isinstance(data, dict):
        raise PermanentError(f"Invalid Jira response for {issue_key}")
    
    fields = data.get("fields", {}) or {}
    if not isinstance(fields, dict):
        raise PermanentError(f"Missing fields in Jira response for {issue_key}")
    
    summary = str(fields.get("summary") or "")
    desc_adf = fields.get("description", {}) or {}
    description = self._extract_text_from_adf(desc_adf).strip()

    # 1) preferimos codeBlock gherkin
    acceptance_criteria = self._extract_gherkin_codeblocks_from_adf(desc_adf)

    # 2) fallback por sección textual
    if not acceptance_criteria:
        acceptance_criteria = self._extract_ac_section_from_plain_text(description)

    links = self._extract_links(fields)

    return JiraIssue(
        key=str(data.get("key") or issue_key),
        summary=summary,
        description=description,
        acceptance_criteria=acceptance_criteria,
        links=links,
        raw=data,
    )
```

Propósito:
Orquesta obtención, transformación y validación de un issue completo.

#### Paso 1: Obtener datos brutos
```python
data = self.get_issue_raw(issue_key)
```
- Llama a `get_issue_raw` (con retry automático).

#### Paso 2: Validar estructura
```python
if not isinstance(data, dict):
    raise PermanentError(...)
```
- Si respuesta no es dict, error permanente (no reintentar).

#### Paso 3: Extraer campos
```python
fields = data.get("fields", {}) or {}
```
- Obtiene diccionario de campos.
- Si ausente o None, usa dict vacío.

#### Paso 4: Validar campos
```python
if not isinstance(fields, dict):
    raise PermanentError(...)
```
- Si `fields` no es dict (ej: string), error permanente.

#### Paso 5: Extraer resumen
```python
summary = str(fields.get("summary") or "")
```
- Obtiene resumen o cadena vacía.
- `str()` garantiza que sea texto (evita None).

#### Paso 6: Extraer descripción
```python
desc_adf = fields.get("description", {}) or {}
description = self._extract_text_from_adf(desc_adf).strip()
```
- Obtiene descripción en formato ADF.
- Extrae texto plano.

#### Paso 7: Extraer criterios de aceptación (prioridad)
```python
# 1) preferimos codeBlock gherkin
acceptance_criteria = self._extract_gherkin_codeblocks_from_adf(desc_adf)

# 2) fallback por sección textual
if not acceptance_criteria:
    acceptance_criteria = self._extract_ac_section_from_plain_text(description)
```
- Intenta Gherkin primero (más estructurado).
- Si vacío, fallback a búsqueda de sección textual.

#### Paso 8: Extraer enlaces
```python
links = self._extract_links(fields)
```
- Obtiene issues relacionados.
- Ahora usa field `issuelinks` desde el nuevo parámetro `get_issue_raw()`.

#### Paso 9: Construir modelo
```python
return JiraIssue(
    key=str(data.get("key") or issue_key),
    summary=summary,
    description=description,
    acceptance_criteria=acceptance_criteria,
    links=links,
    raw=data,
)
```
- Instancia modelo `JiraIssue`.
- Si falta `key`, usa el que se pasó por parámetro.

---

## 5) Cambios principales en esta versión

**Cambio 1: Parámetros de `get_issue_raw()`**
- Antes: `customfield_10000` (asumiendo que era AC).
- Ahora: `issuelinks` (para extraer relaciones).
- Comentario aclaratorio agregado: "Ojo: customfield_10000 NO es AC en tu caso".

**Cambio 2: Validación adicional en `get_issue_raw()`**
- Se agregó check: `if not isinstance(data, dict)`.
- Garantiza que JSON deserializado sea dict, no lista u otro tipo.

**Cambio 3: Dependencia en `_extract_links()`**
- Ahora depende de `issuelinks` en campos solicitados.
- Anterior: podría haber faltado el campo.
- Ahora: garantizado que se pide.

---

## 6) Validaciones del cliente

Validaciones que SÍ están:
1. Status code HTTP → clasificar transitorio vs permanente.
2. Tipo de dato (dict) en respuesta y fields.
3. Tipo de dato en JSON deserializado.
4. Presencia de campos críticos (summary, fields).
5. Extracción recursiva segura de ADF.
6. Presencia de `issuelinks` para relaciones.

Validaciones que NO están:
1. Credenciales válidas (se descubre en primer request).
2. URL base es valida/accesible.
3. issue_key tiene formato correcto (Jira lo rechaza si es inválido).
4. Contenido de ADF es realmente válido (se asume que Jira lo genera bien).

---

## 7) Variables clave (resumen)

1. `settings.jira_base_url`
   - URL base de Jira.

2. `settings.jira_email` y `settings.jira_api_token`
   - Credenciales.

3. `settings.jira_timeout_seconds`
   - Timeout (default 20s).

4. `issue_key`
   - Identificador del issue (ej: "DYF-4325").

5. `issuelinks` (fields)
   - Nuevo campo solicitado para relaciones.

6. `ADF` (Atlassian Document Format)
   - Formato de árbol JSON de Jira para rich text.

---

## 8) Flujo completo de uso

1. Instanciar: `client = JiraClient()`.
2. Llamar: `issue = client.get_issue("DYF-4325")`.
3. Internamente:
   - Llama `get_issue_raw()` con retry automático.
   - Valida que sea dict en JSON y fields sean dict.
   - Extrae campos (summary, description, issuelinks).
   - Procesa ADF de descripción.
   - Busca Gherkin o sección de criterios.
   - Extrae enlaces relacionados desde `issuelinks`.
   - Retorna modelo `JiraIssue`.
4. Si error transitorio → retry automático.
5. Si error permanente → excepción inmediata.

---

## 9) Conclusión práctica

[src/ai_qa_gherkin/clients/jira_client.py](src/ai_qa_gherkin/clients/jira_client.py) es un cliente robusto:

1. **Resiliencia**: retry automático para transitorios, fast-fail para permanentes.
2. **Extracción flexible**: busca Gherkin primero, fallback a texto.
3. **Manejo seguro de ADF**: recursión tolerante con nil-checks.
4. **Tipado**: modelos Pydantic garantizan estructura.
5. **Validación mejorada**: ahora valida tipo de datos deserializados.

Aporta al proyecto:
- Abstracción de HTTP/Jira.
- Transformación de ADF a modelo uniforme.
- Clasificación automática de errores.
- Extracción confiable de relaciones entre issues.
