# Explicación detallada de models.py

Este documento explica en detalle qué hace [src/ai_qa_gherkin/models.py](src/ai_qa_gherkin/models.py), clase por clase, campo por campo y validación por validación.

---

## 1) Objetivo del archivo

El archivo define modelos de datos usando Pydantic (`BaseModel`).

Su propósito es:
1. Estructurar datos que fluyen por la aplicación.
2. Validar tipos y formatos de datos automáticamente.
3. Facilitar serialización/deserialización (JSON, etc.).
4. Centralizar contratos de datos entre servicios e integraciones.

---

## 2) Importaciones

```python
from typing import Any
from pydantic import BaseModel, Field
```

### `from typing import Any`
- Permite usar tipo genérico `Any`.
- Se usa para campos que pueden contener datos heterogéneos sin restricción de tipo (como `raw`, `payload`).

### `from pydantic import BaseModel, Field`
- `BaseModel`: clase base que proporciona validación automática de tipos y serialización.
- `Field`: permite configurar comportamiento adicional de un campo (defaults, factories, etc.).

---

## 3) Modelos explicados uno por uno

## 3.1 Modelo JiraIssue

```python
class JiraIssue(BaseModel):
    key: str
    summary: str
    description: str = ""
    acceptance_criteria: str = ""
    links: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)
```

Propósito:
Representa un issue (problema, tarea) desde Jira.

### Campos:

#### `key: str`
- Tipo: texto obligatorio.
- Ejemplo: `"PROJ-123"`.
- Validación: Pydantic requiere que siempre esté presente y sea `str`.
- Sin default: falla si no se proporciona.

#### `summary: str`
- Tipo: texto obligatorio.
- Ejemplo: `"Implementar login con SSO"`.
- Validación: texto requerido.
- Uso: título del issue.

#### `description: str = ""`
- Tipo: texto opcional.
- Default: cadena vacía.
- Validación: si viene vacío o ausente, se asigna `""`.
- Uso: descripción larga del issue.

#### `acceptance_criteria: str = ""`
- Tipo: texto opcional.
- Default: cadena vacía.
- Validación: texto o vacío.
- Uso: criterios de aceptación del issue.

#### `links: list[str] = Field(default_factory=list)`
- Tipo: lista de textos.
- Default: lista vacía (generada por factory, no reutilizada).
- Validación: Pydantic requiere que cada elemento sea `str`.
- Uso: URLs o referencias relacionadas.
- Nota importante: `default_factory=list` crea una lista nueva cada vez; esto evita problemas de referencia compartida.

#### `raw: dict[str, Any] = Field(default_factory=dict)`
- Tipo: diccionario con claves texto, valores cualquier tipo.
- Default: diccionario vacío (por factory).
- Validación: estructura del diccionario no se valida; se acepta cualquier contenido.
- Uso: almacenar datos adicionales de Jira sin mapeo explícito.
- Ejemplo: `{"customField": 123, "nested": {"key": "value"}}`.

---

## 3.2 Modelo ConfluencePage

```python
class ConfluencePage(BaseModel):
    id: str
    title: str
    url: str
    content: str = ""
```

Propósito:
Representa una página de Confluence (wiki/documentación).

### Campos:

#### `id: str`
- Tipo: texto obligatorio.
- Ejemplo: `"123456"`.
- Validación: requerido.
- Uso: identificador único de la página.

#### `title: str`
- Tipo: texto obligatorio.
- Ejemplo: `"Guía de Test Design"`.
- Validación: requerido.
- Uso: nombre de la página.

#### `url: str`
- Tipo: texto obligatorio.
- Ejemplo: `"https://imed.atlassian.net/wiki/spaces/..."`.
- Validación: texto requerido (no valida formato URL).
- Uso: enlace a la página.

#### `content: str = ""`
- Tipo: texto opcional.
- Default: cadena vacía.
- Validación: si falta, se asigna `""`.
- Uso: contenido HTML o markdown de la página.

---

## 3.3 Modelo GitCommit

```python
class GitCommit(BaseModel):
    sha: str
    message: str
    url: str
```

Propósito:
Representa un commit en un repositorio Git (GitHub/GitLab).

### Campos:

#### `sha: str`
- Tipo: texto obligatorio.
- Ejemplo: `"a1b2c3d4e5f6..."`.
- Validación: requerido.
- Uso: hash único del commit.

#### `message: str`
- Tipo: texto obligatorio.
- Ejemplo: `"feat: agregar validación de config"`.
- Validación: requerido.
- Uso: mensaje/descripción del commit.

#### `url: str`
- Tipo: texto obligatorio.
- Ejemplo: `"https://github.com/...".
- Validación: texto requerido (no valida formato URL).
- Uso: enlace al commit en GitHub/GitLab.

Nota:
Todos los campos son obligatorios; no hay defaults. Un GitCommit incompleto falla instantáneamente.

---

## 3.4 Modelo PullRequest

```python
class PullRequest(BaseModel):
    id: str
    title: str
    url: str
    state: str
```

Propósito:
Representa una pull request (merge request en GitLab).

### Campos:

#### `id: str`
- Tipo: texto obligatorio.
- Ejemplo: `"1234"` o `"PR#42"`.
- Validación: requerido.
- Uso: identificador de PR.

#### `title: str`
- Tipo: texto obligatorio.
- Ejemplo: `"Feat: QA Gherkin automation"`.
- Validación: requerido.
- Uso: asunto de la PR.

#### `url: str`
- Tipo: texto obligatorio.
- Ejemplo: `"https://github.com/...".
- Validación: texto requerido (no valida formato URL).
- Uso: enlace a la PR.

#### `state: str`
- Tipo: texto obligatorio.
- Ejemplo: `"open"`, `"merged"`, `"closed"`.
- Validación: texto requerido (no fuerza valores específicos; cualquier string pasa).
- Uso: estado actual de la PR.

Nota:
No hay enum ni restricción de valores para `state`, por lo que puedes pasar cualquier string. Si quisieras validar que solo sea `"open"`, `"merged"` o `"closed"`, necesitarías un validador adicional.

---

## 3.5 Modelo XrayImportResponse

```python
class XrayImportResponse(BaseModel):
    success: bool
    payload: dict[str, Any] = Field(default_factory=dict)
```

Propósito:
Representa la respuesta al importar tests a Xray.

### Campos:

#### `success: bool`
- Tipo: booleano obligatorio.
- Ejemplo: `True` o `False`.
- Validación: requerido y debe ser booleano.
- Uso: indica si la importación fue exitosa.

#### `payload: dict[str, Any] = Field(default_factory=dict)`
- Tipo: diccionario flexible.
- Default: diccionario vacío (por factory).
- Validación: estructura interna no validada; se acepta cualquier contenido.
- Uso: almacenar datos de respuesta de Xray (IDs creados, errores, etc.).
- Ejemplo: `{"test_ids": ["TEST-1", "TEST-2"], "errors": [...]}`.

---

## 4) Validaciones implícitas de Pydantic en general

Para todos estos modelos, Pydantic automáticamente:

1. **Convierte tipos** (si es posible):
   - Si pases `links=[1, 2, 3]` esperando `list[str]`, fallará por tipo incorrecto.

2. **Requiere campos sin default**:
   - Si creas `JiraIssue()` sin `key`, falla.

3. **Aplica defaults**:
   - Si omites `description`, se asigna `""`.

4. **Genera factories correctamente**:
   - `links=[]` en cada instancia nueva es diferente para evitar mutación compartida.

5. **Serializa a JSON automáticamente**:
   - `JiraIssue(...).model_dump()` genera diccionario.
   - `JiraIssue(...).model_dump_json()` genera JSON string.

---

## 5) Validaciones que NO existen

En estos modelos no se valida:
1. Que URLs sean válidas (formato).
2. Que `sha` tenga longitud correcta de hash.
3. Que `state` en PullRequest esté en conjunto permitido.
4. Que `key` en JiraIssue tenga formato `PROJ-###`.
5. Que campos vacíos sean "realmente requeridos" por negocio.

Si necesitas esas validaciones más estrictas, puedes agregar validadores de Pydantic usando `@field_validator` o `@model_validator`.

---

## 6) Variables y elementos clave

Aunque estos archivos son principalmente clases, resumo elementos clave:

1. **Tipos usados:**
   - `str`: texto
   - `bool`: booleano
   - `list[str]`: lista de textos
   - `dict[str, Any]`: diccionario flexible
   - `Any`: tipo genérico sin restricción

2. **Patterns usados:**
   - `Field(default_factory=list)`: factory para evitar mutación compartida
   - `Field(default_factory=dict)`: idem para diccionarios

3. **Defaults:**
   - Algunos campos tienen defaults (`""`), otros no.

4. **Obligatorios vs Opcionales:**
   - Sin `= ...` → obligatorio.
   - Con `= ""` o `= Field(...)` → opcional con default.

---

## 7) Flujo típico de uso

1. Un cliente (Jira/Git/Confluence/Xray) trae datos en JSON.
2. Se parsean a uno de estos modelos: `JiraIssue(**data)`.
3. Si la estructura es inválida, Pydantic lanza `ValidationError`.
4. Si es válida, el modelo garantiza campos correctos.
5. Se pasan entre servicios tipados: funciones esperan `JiraIssue`, no `dict`.

---

## 8) Conclusión práctica

[src/ai_qa_gherkin/models.py](src/ai_qa_gherkin/models.py) es un conjunto de contratos de datos.

Aporta:
1. Validación automática de tipos al crear instancias.
2. Seguridad de tipos en IDE (type hints).
3. Serialización/deserialización transparente.
4. Documentación implícita de estructura de datos.

Limitación:
No valida reglas de negocio complejas (requeriría validadores adicionales en cada modelo).
