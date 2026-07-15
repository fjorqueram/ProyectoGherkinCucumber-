# Explicación detallada de confluence_client.py

Este documento explica en detalle qué hace [src/ai_qa_gherkin/clients/confluence_client.py](src/ai_qa_gherkin/clients/confluence_client.py), clase por clase, método por método, validación por validación y variable por variable.

---

## 1) Objetivo del archivo

El archivo implementa un cliente HTTP para consumir la API de Confluence.

Su propósito es:
1. Conectar con Confluence usando credenciales desde configuración.
2. Buscar páginas por texto usando CQL (Confluence Query Language).
3. Construir URLs de páginas desde distintos formatos de respuesta.
4. Transformar resultados al modelo `ConfluencePage`.
5. Manejar errores transitorios (con retry) y permanentes (sin retry).

---

## 2) Importaciones

```python
from __future__ import annotations
import httpx
from ai_qa_gherkin.config import settings
from ai_qa_gherkin.logger import get_logger
from ai_qa_gherkin.models import ConfluencePage
from ai_qa_gherkin.retry import retry_policy, TransientError, PermanentError
```

### `from __future__ import annotations`
- Permite type hints modernos sin importar tipos explícitos.

### `import httpx`
- Librería HTTP para hacer peticiones a Confluence.

### `from ai_qa_gherkin.config import settings`
- Configuración global con URL base, credenciales y timeout de Confluence.

### `from ai_qa_gherkin.logger import get_logger`
- Logger contextual para registrar eventos.

### `from ai_qa_gherkin.models import ConfluencePage`
- Modelo Pydantic destino que el cliente debe generar.

### `from ai_qa_gherkin.retry import retry_policy, TransientError, PermanentError`
- Decorador de retry y tipos de error para clasificar fallos.

---

## 3) Logger contextual

```python
log = get_logger("confluence_client")
```

Crea un logger con contexto operacional `"confluence_client"`.
Cada log llevará automáticamente el nombre del servicio y la operación.

---

## 4) Clase ConfluenceClient

### 4.1 Constructor (`__init__`)

```python
def __init__(self) -> None:
    self.base_url = settings.confluence_base_url.rstrip("/")
    self.auth = (settings.confluence_email, settings.confluence_api_token)
    self.timeout = settings.confluence_timeout_seconds
```

Qué hace:
Inicializa el cliente con valores desde configuración.

#### `self.base_url = settings.confluence_base_url.rstrip("/")`
- Lee URL base de Confluence desde config.
- `.rstrip("/")` elimina trailing slash para evitar doble barra al construir rutas.
- Ejemplo: `"https://imed.atlassian.net/wiki"`.

#### `self.auth = (settings.confluence_email, settings.confluence_api_token)`
- Tupla (email, token) para autenticación HTTP Basic.
- httpx la usa para generar el header `Authorization` automáticamente.

#### `self.timeout = settings.confluence_timeout_seconds`
- Timeout en segundos para las requests (default 20s desde config).
- Previene que la app se cuelgue si Confluence no responde.

Validaciones implícitas:
- Si `confluence_base_url` es vacío, `.rstrip("/")` retorna `""` sin error inmediato.
- La falla real ocurre al ejecutar el primer request.

---

### 4.2 Método `_handle_http_error`

```python
def _handle_http_error(self, response: httpx.Response) -> None:
    if response.status_code in {429, 502, 503, 504}:
        raise TransientError(f"Confluence transient error: {response.status_code}: {response.text[:250]}")
    if response.status_code >= 400:
        raise PermanentError(f"Confluence permanent error: {response.status_code}: {response.text[:250]}")
```

Propósito:
Clasificar errores HTTP de Confluence como transitorios o permanentes.

#### Diferencia con `jira_client._handle_http_error`
- Mismo patrón lógico, pero:
  - Prefijo del mensaje: `"Confluence transient error"` / `"Confluence permanent error"`.
  - Recorte del body: `[:250]` (en Jira es `[:300]`).

#### Clasificación:

1. **Transitorios** (429, 502, 503, 504):
   - 429: Rate limit → retry útil.
   - 502/503/504: Fallos temporales de gateway → retry útil.
   - Lanza `TransientError`.

2. **Permanentes** (resto ≥ 400):
   - 401: No autorizado.
   - 403: Prohibido.
   - 404: No encontrado.
   - Lanza `PermanentError`.

---

### 4.3 Método `build_page_url`

```python
def build_page_url(self, item: dict) -> str:
    links = item.get("_links", {}) or {}
    base = links.get("base", "") or ""
    webui = links.get("webui", "") or ""
    page_id = str(item.get("id", "")) or ""

    # Caso ideal: base + webui
    if base and webui:
        return f"{base}{webui}"
    
    # Caso frecuente cloud: solo webui
    if webui:
        if webui.startswith("/"):
            return f"{self.base_url}{webui}"
        return f"{self.base_url}/{webui}"
    
    # Fallback universal por pageId
    if page_id:
        return f"{self.base_url}/pages/viewpage.action?pageId={page_id}"
    
    return ""  # No se pudo construir la URL
```

Propósito:
Construir la URL de una página de Confluence a partir del JSON de respuesta, manejando distintos formatos que puede devolver la API.

#### Por qué es necesario:
La API de Confluence puede devolver distintas variantes en `_links` según si es Cloud, Data Center, o cómo está configurado el base URL del tenant.

#### Parámetro `item: dict`
- Elemento individual del array `"results"` de la respuesta JSON.

#### Variables extraídas:

##### `links = item.get("_links", {}) or {}`
- Obtiene diccionario de links del item.
- `or {}` protege contra `None`.

##### `base = links.get("base", "") or ""`
- URL base absoluta que devuelve Confluence.
- Ejemplo: `"https://imed.atlassian.net/wiki"`.

##### `webui = links.get("webui", "") or ""`
- Path relativo de la página.
- Ejemplo: `"/spaces/PROJ/pages/123456/Mi+Pagina"`.

##### `page_id = str(item.get("id", "")) or ""`
- ID numérico de la página.
- Ejemplo: `"123456"`.

#### Lógica de construcción (3 casos):

**Caso 1: base + webui (ideal)**
```python
if base and webui:
    return f"{base}{webui}"
```
- Si Confluence devuelve ambos, los concatena.
- Ejemplo: `"https://imed.atlassian.net/wiki/spaces/PROJ/pages/..."`.

**Caso 2: solo webui (Cloud frecuente)**
```python
if webui:
    if webui.startswith("/"):
        return f"{self.base_url}{webui}"
    return f"{self.base_url}/{webui}"
```
- Si solo hay webui (sin base), usa el `base_url` del cliente.
- Si webui empieza con `/`, no agrega slash extra.
- Si no empieza con `/`, agrega `/` entre ambos.

**Caso 3: solo page_id (fallback universal)**
```python
if page_id:
    return f"{self.base_url}/pages/viewpage.action?pageId={page_id}"
```
- Si no hay links pero sí ID, construye URL clásica con query param.
- Funciona en Data Center y versiones antiguas.

**Caso 4: nada disponible**
```python
return ""
```
- Si falta todo, retorna cadena vacía sin fallar.

---

### 4.4 Método `search_pages_by_text` (con retry)

```python
@retry_policy()
def search_pages_by_text(self, text: str, limit: int = 5) -> list[ConfluencePage]:
    """
    Busca páginas por texto usando CQL.
    """
    url = f"{self.base_url}/rest/api/content/search"
    params = {
        "cql": f'text ~ "{text}"',
        "limit": limit,
        "expand": "body.storage"
    }
    log.info(f"Searching Confluence pages for text: {text}")

    try:
        with httpx.Client(auth=self.auth, timeout=self.timeout) as client:
            r = client.get(url, params=params)
            if r.status_code >= 400:
                self._handle_http_error(r)
            data = r.json()
    except httpx.TimeoutException as e:
        raise TransientError(f"Confluence request timed out: {e}") from e
    except httpx.NetworkError as e:
        raise TransientError(f"Confluence network error: {e}") from e
    
    pages: list[ConfluencePage] = []
    for it in data.get("results", []) or []:
        page_id = str(it.get("id", "") or "")
        title = str(it.get("title", "") or "")
        content = ((it.get("body", {}) or {}).get("storage", {}) or {}).get("value", "") or ""
        page_url = self.build_page_url(it)

        pages.append(
            ConfluencePage(
                id=page_id, 
                title=title, 
                content=content, url=page_url
                )
            )
        
    return pages
```

Propósito:
Buscar páginas de Confluence que contengan un texto dado y devolverlas como lista de modelos.

#### Decorador `@retry_policy()`
- Aplica retry automático ante `TransientError`.
- Hasta `retry_max_attempts` veces, con backoff exponencial.

#### Parámetros:

##### `text: str`
- Texto a buscar dentro de páginas de Confluence.
- Se usa como valor en la query CQL.

##### `limit: int = 5`
- Máximo de resultados a devolver.
- Default: 5 páginas.
- Se pasa directamente al API de Confluence.

#### Construcción de URL
```python
url = f"{self.base_url}/rest/api/content/search"
```
- Endpoint de búsqueda de Confluence Cloud.

#### Parámetros de query (`params`)

```python
params = {
    "cql": f'text ~ "{text}"',
    "limit": limit,
    "expand": "body.storage"
}
```

1. **`cql`**: Query CQL.
   - `text ~ "..."` → busca texto en contenido de páginas.
   - Las comillas internas garantizan búsqueda de frase o palabra.

2. **`limit`**: Máximo de resultados.

3. **`expand: "body.storage"`**: Indica a Confluence que incluya el contenido HTML/storage en la respuesta.
   - Sin `expand`, el body viene vacío.

#### Logging
```python
log.info(f"Searching Confluence pages for text: {text}")
```
- Registra inicio de búsqueda con el texto buscado.

#### Request HTTP
```python
with httpx.Client(auth=self.auth, timeout=self.timeout) as client:
    r = client.get(url, params=params)
    if r.status_code >= 400:
        self._handle_http_error(r)
    data = r.json()
```
- Context manager garantiza cierre de conexión.
- Si status ≥ 400, delega a `_handle_http_error`.
- Deserializa JSON de respuesta.

#### Manejo de excepciones de red
```python
except httpx.TimeoutException as e:
    raise TransientError(f"Confluence request timed out: {e}") from e
except httpx.NetworkError as e:
    raise TransientError(f"Confluence network error: {e}") from e
```
- Timeout y errores de red → `TransientError` → retry automático.

#### Transformación de resultados

```python
pages: list[ConfluencePage] = []
for it in data.get("results", []) or []:
    page_id = str(it.get("id", "") or "")
    title = str(it.get("title", "") or "")
    content = ((it.get("body", {}) or {}).get("storage", {}) or {}).get("value", "") or ""
    page_url = self.build_page_url(it)

    pages.append(ConfluencePage(id=page_id, title=title, content=content, url=page_url))
```

##### `data.get("results", []) or []`
- Extrae lista de resultados.
- `or []` protege contra `None`.

##### Extracción de `page_id`
```python
page_id = str(it.get("id", "") or "")
```
- Convierte a string explícitamente.
- `or ""` protege contra `None`.

##### Extracción de `title`
```python
title = str(it.get("title", "") or "")
```
- Igual que page_id: string seguro.

##### Extracción de `content`
```python
content = ((it.get("body", {}) or {}).get("storage", {}) or {}).get("value", "") or ""
```
- Navegación profunda encadenada:
  - `body` → `storage` → `value`.
- Cada nivel tiene `or {}` para proteger contra `None`.
- Si cualquier nivel falta, retorna `""`.
- El contenido es HTML (formato "storage" de Confluence).

##### Construcción de URL
```python
page_url = self.build_page_url(it)
```
- Delega a `build_page_url` que maneja los 4 casos descritos.

##### Construcción del modelo
```python
pages.append(ConfluencePage(id=page_id, title=title, content=content, url=page_url))
```
- Pydantic valida tipos al construir.
- Si falla validación, lanza `ValidationError`.

---

## 5) Validaciones del cliente

Validaciones que SÍ están:
1. Status code HTTP → clasificar transitorio vs permanente.
2. Nil-checks en cada campo con `or {}` / `or ""`.
3. Conversión explícita a `str` para id y title.
4. Navegación segura anidada para content.
5. URL construida con fallback progresivo de 4 casos.

Validaciones que NO están:
1. Que `text` no esté vacío antes de buscar.
2. Que `limit` sea positivo.
3. Que la URL resultante sea válida.
4. Que el content sea HTML válido.
5. Que `data` sea dict (como sí valida `jira_client` con `isinstance`).

---

## 6) Variables clave (resumen)

| Variable | Fuente | Uso |
|---|---|---|
| `settings.confluence_base_url` | Config | URL base de Confluence |
| `settings.confluence_email` | Config | Credencial de autenticación |
| `settings.confluence_api_token` | Config | Token de autenticación |
| `settings.confluence_timeout_seconds` | Config | Timeout de requests (default 20s) |
| `text` | Parámetro | Texto a buscar en CQL |
| `limit` | Parámetro | Máximo de resultados (default 5) |
| `cql` | Query param | Expresión CQL de búsqueda |
| `expand` | Query param | Solicita body.storage en respuesta |
| `_links.base` | Respuesta | URL base absoluta de la página |
| `_links.webui` | Respuesta | Path relativo de la página |
| `page_id` | Respuesta | ID numérico para fallback de URL |

---

## 7) Flujo completo de uso

1. Instanciar: `client = ConfluenceClient()`.
2. Llamar: `pages = client.search_pages_by_text("DYF-4325", limit=5)`.
3. Internamente:
   - Construye URL y query CQL.
   - Hace GET con autenticación y timeout.
   - Si error HTTP → clasifica y lanza excepción.
   - Si timeout/red → `TransientError` → retry automático.
   - Itera resultados y extrae id, title, content, url.
   - Para cada resultado, construye URL con `build_page_url`.
   - Retorna lista de modelos `ConfluencePage`.

---

## 8) Comparación con jira_client

| Aspecto | jira_client | confluence_client |
|---|---|---|
| Modelo destino | `JiraIssue` | `ConfluencePage` |
| Endpoint | `/rest/api/3/issue/{key}` | `/rest/api/content/search` |
| Retry | Sí | Sí |
| Validación tipo respuesta | `isinstance(data, dict)` | Sin check explícito |
| Extracción ADF | Sí (recursivo) | No (HTML storage directo) |
| Construcción URL | No necesaria | Sí (3 fallbacks) |
| Recorte body error | `[:300]` | `[:250]` |

---

## 9) Conclusión práctica

[src/ai_qa_gherkin/clients/confluence_client.py](src/ai_qa_gherkin/clients/confluence_client.py) es un cliente compacto y defensivo:

1. **Búsqueda CQL**: permite buscar contenido relevante por texto libre.
2. **URL robusta**: 4 estrategias de construcción para distintos entornos.
3. **Nil-safe**: uso sistemático de `or {}` / `or ""` en navegación anidada.
4. **Retry automático**: resiliencia ante fallos transitorios.
5. **Tipado**: modelo `ConfluencePage` garantiza estructura uniforme.

Aporta al proyecto la capacidad de recuperar documentación de Confluence relacionada a issues, para enriquecer el contexto de generación de tests Gherkin.
