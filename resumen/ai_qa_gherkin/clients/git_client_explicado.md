# Explicación detallada de git_client.py

Este documento explica en detalle qué hace [src/ai_qa_gherkin/clients/git_client.py](src/ai_qa_gherkin/clients/git_client.py): objetivo, variables, validaciones, manejo de errores y flujo completo.

## 1) Objetivo del archivo

Este módulo implementa un cliente para API de Git (actualmente orientado a GitHub) que:

1. Busca commits relacionados con una clave de Jira.
2. Busca pull requests relacionadas con una clave de Jira.
3. Clasifica errores HTTP en transitorios y permanentes.
4. Convierte respuestas JSON en modelos tipados (`GitCommit`, `PullRequest`).

También aplica política de retry en la búsqueda de commits.

## 2) Importaciones

```python
from __future__ import annotations
import httpx
from ai_qa_gherkin.config import settings
from ai_qa_gherkin.logger import get_logger
from ai_qa_gherkin.models import GitCommit, PullRequest
from ai_qa_gherkin.retry import retry_policy, TransientError, PermanentError
```

### Qué aporta cada import

1. `__future__.annotations`
Permite anotaciones de tipo diferidas.

2. `httpx`
Cliente HTTP para hacer requests a la API GitHub.

3. `settings`
Obtiene configuración de URL base, token y timeout.

4. `get_logger`
Crea logger contextual para trazabilidad.

5. `GitCommit`, `PullRequest`
Modelos de salida tipados para commits y PRs.

6. `retry_policy`, `TransientError`, `PermanentError`
Política de reintentos y taxonomía de errores.

## 3) Logger contextual

```python
log = get_logger("git_client")
```

Se crea un logger con operación `git_client`, útil para filtrar logs por componente.

## 4) Clase GitClient

### 4.1 Docstring de clase

```python
"""
MVP para GitHub API.
Si usas GitLab, luego hacemos adapter.
"""
```

Mensaje de intención arquitectónica:

1. Implementación mínima viable para GitHub.
2. Posibilidad futura de adaptar a GitLab con un adapter.

### 4.2 Constructor `__init__`

```python
def __init__(self) -> None:
    self.base_url = settings.git_api_base_url.rstrip("/")
    self.token = settings.git_token
    self.timeout = settings.git_timeout_seconds
    self.headers = {
        "Authorization": f"Bearer {self.token}",
        "Accept": "application/vnd.github+json",
    }
```

Variables explicadas una por una:

1. `self.base_url`
- Fuente: `settings.git_api_base_url`.
- `rstrip("/")` evita doble slash al construir endpoints.

2. `self.token`
- Fuente: `settings.git_token`.
- Se usa para autenticación Bearer.

3. `self.timeout`
- Fuente: `settings.git_timeout_seconds`.
- Timeout para todas las requests.

4. `self.headers`
- Header `Authorization: Bearer <token>`.
- Header `Accept: application/vnd.github+json` para formato estándar GitHub.

Validación implícita:
- Aquí no valida token vacío ni base_url vacía.
- Los fallos aparecerán al hacer requests (401, 403, URL inválida, etc.).

## 5) Método `_handle_error`

```python
def _handle_error(self, response: httpx.Response) -> None:
    if response.status_code in (429, 502, 503, 504):
        raise TransientError(f"Git Transient: {response.status_code}: {response.text[:250]}")
    if response.status_code >= 400:
        raise PermanentError(f"Git Permanent: {response.status_code}: {response.text[:250]}")
```

Objetivo:
Clasificar errores HTTP según reintentabilidad.

Reglas:

1. Transitorio: 429, 502, 503, 504.
- Se lanza `TransientError`.
- Esto habilita retry en métodos decorados.

2. Permanente: cualquier `>= 400` restante.
- Se lanza `PermanentError`.
- No se debería reintentar automáticamente.

Detalle:
- Recorta `response.text` a 250 chars para evitar logs enormes.

## 6) Método `search_commits_by_issue_key`

```python
@retry_policy()
def search_commits_by_issue_key(self, owner: str, repo: str, issue_key: str, limit: int = 10) -> list[GitCommit]:
```

### 6.1 Qué hace
Busca commits del repo donde el mensaje o metadata coincida con `issue_key` usando endpoint Search Commits de GitHub.

### 6.2 Parámetros

1. `owner: str`
Owner del repositorio (usuario u organización).

2. `repo: str`
Nombre del repo.

3. `issue_key: str`
Clave Jira a buscar (ejemplo: `DYF-4325`).

4. `limit: int = 10`
Cantidad máxima de resultados (`per_page`).

### 6.3 Construcción de request

```python
url = f"{self.base_url}/search/commits"
params = {
    "q": f"{issue_key} repo:{owner}/{repo}",
    "order": "desc",
    "per_page": limit,
}
headers = {**self.headers, "Accept": "application/vnd.github.cloak-preview+json"}
```

Validación/decisiones:

1. Endpoint correcto para buscar commits por query.
2. Query `q` combina issue key + scope de repo.
3. `order=desc` prioriza más recientes.
4. `per_page=limit` controla tamaño de respuesta.
5. Override de `Accept` a `cloak-preview`:
- Importante para Search Commits en ciertos comportamientos/versiones API.

### 6.4 Logging

```python
log.info(f"Searching commits for issue_key {issue_key} in {owner}/{repo}")
```

Registra búsqueda con trazabilidad suficiente.

### 6.5 Ejecución HTTP y errores

```python
with httpx.Client(timeout=self.timeout, headers=headers) as client:
    response = client.get(url, params=params)
    if response.status_code >= 400:
        self._handle_error(response)
    data = response.json()
```

1. Usa timeout y headers configurados.
2. Si status >= 400 delega clasificación a `_handle_error`.
3. Si ok, parsea JSON.

Excepciones de red:

```python
except httpx.TimeoutException as e:
    raise TransientError(f"Git Timeout: {e}") from e
except httpx.NetworkError as e:
    raise TransientError(f"Git Network Error: {e}") from e
```

Se consideran transitorias y por eso, al estar decorado con `@retry_policy()`, se reintenta.

### 6.6 Parseo de salida

```python
commits: list[GitCommit] = []
for it in data.get("items", []) or []:
    commits.append(
        GitCommit(
            sha=it.get("sha", ""),
            message=(it.get("commit", {}).get("message", "") or ""),
            url=it.get("html_url", ""),
        )
    )
return commits
```

Campo por campo:

1. `sha`
Hash del commit.

2. `message`
Mensaje del commit, navegando `commit.message` de forma segura.

3. `url`
URL HTML del commit.

Validación implícita:
- Si faltan campos, usa strings vacíos para evitar `KeyError`.
- Pydantic valida tipos al instanciar `GitCommit`.

## 7) Método `search_prs_by_commit_sha` (nombre y comportamiento)

```python
def search_prs_by_commit_sha(self, owner: str, repo: str, issue_key: str, limit: int = 10) -> list[PullRequest]:
```

### 7.1 Observación importante
El nombre sugiere búsqueda por `commit_sha`, pero el método realmente busca PRs por `issue_key` en Search Issues.

Internamente:

```python
params = {
    "q": f"{issue_key} repo:{owner}/{repo} is:pr",
    "order": "desc",
    "per_page": limit,
}
```

No usa ningún parámetro `commit_sha`.

### 7.2 Qué hace realmente
Busca PRs del repositorio cuyo contenido/metadata coincida con `issue_key` y filtro `is:pr`.

### 7.3 Request y manejo de errores

```python
with httpx.Client(timeout=self.timeout, headers=self.headers) as client:
    response = client.get(url, params=params)
    if response.status_code >= 400:
        self._handle_error(response)
    data = response.json()
```

Excepciones:

```python
except httpx.TimeoutException as e:
    raise TransientError(f"Git Timeout: {e}") from e
except httpx.NetworkError as e:
    raise TransientError(f"Git Network Error: {e}") from e
```

Importante:
- Este método no tiene decorador `@retry_policy()`.
- Aunque lanza `TransientError`, sin decorador no habrá retry automático aquí.

### 7.4 Parseo de PRs

```python
prs: list[PullRequest] = []
for it in data.get("items", []) or []:
    prs.append(
        PullRequest(
            id=str(it.get("number", "")),
            title=it.get("title", ""),
            url=it.get("html_url", ""),
            state=it.get("state", ""),
        )
    )
return prs
```

Campos de salida:

1. `id`
Número de PR convertido a string.

2. `title`
Título de la PR.

3. `url`
URL HTML de la PR.

4. `state`
Estado (`open`, `closed`, etc.).

## 8) Validación por validación

Validaciones que sí existen:

1. Clasificación de status HTTP transitorio/permanente.
2. Manejo explícito de timeouts y network errors.
3. Uso de defaults seguros (`.get(..., "")`, `or []`) al parsear JSON.
4. Tipado de salida mediante modelos Pydantic.

Validaciones que no existen:

1. No valida que `owner`, `repo`, `issue_key` no estén vacíos.
2. No valida que `limit` sea positivo.
3. No valida estructura de `data` como dict antes de `data.get`.
4. En `search_prs_by_commit_sha`, no hay retry automático.
5. El nombre del método no coincide con su comportamiento real.

## 9) Flujo completo

1. Se instancia `GitClient` con config.
2. Se llama `search_commits_by_issue_key(...)`:
- arma query
- consulta API
- clasifica errores
- reintenta si transitorio
- retorna lista `GitCommit`

3. Se llama `search_prs_by_commit_sha(...)`:
- arma query de PRs por issue key
- consulta API
- clasifica errores
- retorna lista `PullRequest`

## 10) Conclusión práctica

[src/ai_qa_gherkin/clients/git_client.py](src/ai_qa_gherkin/clients/git_client.py) provee una capa útil de integración GitHub con manejo básico robusto de errores y transformación tipada.

Sus puntos fuertes:
1. Separación clara de responsabilidades.
2. Taxonomía de errores consistente con el proyecto.
3. Parseo seguro de respuestas JSON.

Puntos a vigilar:
1. Método de PRs sin retry automático.
2. Nombre del método de PRs no refleja exactamente su lógica.
3. Falta validación temprana de parámetros de entrada.
