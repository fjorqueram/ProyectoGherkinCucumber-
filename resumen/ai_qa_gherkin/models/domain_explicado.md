# Explicacion detallada de domain.py

Este documento explica en detalle que hace `src/ai_qa_gherkin/models/domain.py`, clase por clase, campo por campo y validacion por validacion.

---

## 1) Objetivo del archivo

`domain.py` define los modelos principales de datos del proyecto usando Pydantic.

Su proposito es:

1. Representar datos provenientes de Jira.
2. Representar datos provenientes de Confluence.
3. Representar datos provenientes de Git.
4. Representar respuestas de Xray.
5. Representar contexto enriquecido para analisis de QA.
6. Representar resultados generados por IA, validaciones, publicaciones y ejecuciones.

Estos modelos funcionan como contratos internos. En vez de pasar diccionarios sueltos por todo el sistema, el codigo puede pasar objetos con estructura clara.

---

## 2) Importaciones

```python
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field
```

### `from __future__ import annotations`

Permite usar anotaciones de tipos modernas y evaluarlas de forma diferida.

Ayuda a que los type hints sean mas flexibles y evita algunos problemas de referencias futuras.

### `from datetime import datetime, timezone`

Importa herramientas para manejar fechas y zonas horarias.

Se usa en:

```python
generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

Esto permite guardar la fecha/hora de generacion de una feature en UTC.

### `from typing import Any, Literal`

Importa dos tipos especiales:

- `Any`: representa cualquier tipo de dato.
- `Literal`: restringe un campo a un conjunto exacto de valores permitidos.

Ejemplo de `Any`:

```python
raw: dict[str, Any]
```

Significa que el diccionario puede tener valores de cualquier tipo.

Ejemplo de `Literal`:

```python
destination: Literal["xray", "jira", "confluence", "git", "local"]
```

Significa que `destination` solo puede tener uno de esos valores.

### `from pydantic import BaseModel, Field`

Pydantic permite definir modelos de datos con validacion automatica.

- `BaseModel`: clase base para todos los modelos.
- `Field`: permite configurar valores por defecto, validaciones y metadata.

---

## 3) Modelo `JiraIssue`

```python
class JiraIssue(BaseModel):
    key: str
    summary: str
    description: str = ""
    acceptance_criteria: str = ""
    links: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)
```

Representa una issue de Jira ya normalizada.

### Campo `key`

```python
key: str
```

Clave unica de la issue.

Ejemplo:

```text
PROJ-123
```

Es obligatorio porque no tiene valor por defecto.

### Campo `summary`

```python
summary: str
```

Titulo o resumen de la issue.

Tambien es obligatorio.

### Campo `description`

```python
description: str = ""
```

Descripcion textual de la issue.

Valor por defecto:

```python
""
```

Si Jira no trae descripcion, el objeto sigue siendo valido.

### Campo `acceptance_criteria`

```python
acceptance_criteria: str = ""
```

Criterios de aceptacion en texto.

En este modelo es un solo string, no una lista.

### Campo `links`

```python
links: list[str] = Field(default_factory=list)
```

Lista de enlaces relacionados.

Validacion/default importante:

```python
Field(default_factory=list)
```

Esto crea una lista nueva para cada instancia.

Es mejor que:

```python
links: list[str] = []
```

porque evita compartir la misma lista entre objetos.

### Campo `raw`

```python
raw: dict[str, Any] = Field(default_factory=dict)
```

Guarda la respuesta original o informacion adicional de Jira.

Se usa para trazabilidad o debugging sin perder datos originales.

---

## 4) Modelo `ConfluencePage`

```python
class ConfluencePage(BaseModel):
    id: str
    title: str
    url: str
    content: str = ""
```

Representa una pagina de Confluence.

### `id`

Identificador de la pagina.

Obligatorio.

### `title`

Titulo de la pagina.

Obligatorio.

### `url`

URL navegable de la pagina.

Obligatorio.

### `content`

```python
content: str = ""
```

Contenido textual de la pagina.

Si no se obtiene contenido, queda como string vacio.

---

## 5) Modelo `GitCommit`

```python
class GitCommit(BaseModel):
    sha: str
    message: str
    url: str
```

Representa un commit de Git.

### `sha`

Hash del commit.

Ejemplo:

```text
abc123...
```

### `message`

Mensaje del commit.

### `url`

URL donde se puede consultar el commit en el proveedor Git.

---

## 6) Modelo `PullRequest`

```python
class PullRequest(BaseModel):
    id: str
    title: str
    url: str
    state: str
```

Representa un pull request o merge request.

### `id`

Identificador del PR.

### `title`

Titulo del PR.

### `url`

URL del PR.

### `state`

Estado del PR.

Ejemplos:

- `open`
- `closed`
- `merged`

Este campo es `str`, por lo tanto no restringe valores especificos.

---

## 7) Modelo `XrayImportResponse`

```python
class XrayImportResponse(BaseModel):
    success: bool
    payload: dict[str, Any] = Field(default_factory=dict)
```

Representa el resultado interno de una importacion a Xray.

### `success`

```python
success: bool
```

Indica si la operacion fue exitosa.

Es obligatorio.

### `payload`

```python
payload: dict[str, Any] = Field(default_factory=dict)
```

Guarda la respuesta de Xray.

Usa `default_factory=dict` para crear un diccionario nuevo por instancia.

---

## 8) Comentario `# ===== Nuevos modelos solicitados =====`

```python
# ===== Nuevos modelos solicitados =====
```

Este comentario separa los modelos iniciales de los modelos agregados despues.

No afecta la ejecucion del codigo.

Sirve como marca visual para entender que desde ahi empiezan modelos mas orientados al flujo completo de analisis, generacion, validacion y publicacion.

---

## 9) Modelo `IssueContext`

```python
class IssueContext(BaseModel):
    issue_key: str
    summary: str
    description: str = ""
    acceptance_criteria: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)
```

Representa el contexto enriquecido de una issue.

A diferencia de `JiraIssue`, aqui `acceptance_criteria` es una lista de strings.

### `issue_key`

Clave de Jira.

Ejemplo:

```text
PROJ-123
```

### `summary`

Resumen de la issue.

### `description`

Descripcion de la issue.

Por defecto:

```python
""
```

### `acceptance_criteria`

```python
acceptance_criteria: list[str] = Field(default_factory=list)
```

Lista de criterios de aceptacion.

Ejemplo:

```python
[
    "El usuario debe poder iniciar sesion",
    "El sistema debe mostrar error con credenciales invalidas",
]
```

### `links`

Lista de links relacionados.

### `raw`

Diccionario con informacion cruda de origen.

---

## 10) Modelo `ConfluenceContext`

```python
class ConfluenceContext(BaseModel):
    page_id: str
    title: str
    url: str
    content: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)
```

Representa contexto recuperado desde Confluence.

### `page_id`

Identificador de la pagina.

### `title`

Titulo.

### `url`

URL de la pagina.

### `content`

Contenido textual.

### `raw`

Datos originales completos o parciales.

---

## 11) Modelo `GitContext`

```python
class GitContext(BaseModel):
    repo_url: str = ""
    branch: str = ""
    commit_sha: str = ""
    changed_files: list[str] = Field(default_factory=list)
    diff_summary: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)
```

Representa contexto tecnico obtenido desde Git.

### `repo_url`

URL del repositorio.

Por defecto es string vacio.

### `branch`

Rama relacionada al cambio.

### `commit_sha`

SHA del commit relacionado.

### `changed_files`

```python
changed_files: list[str] = Field(default_factory=list)
```

Lista de archivos modificados.

### `diff_summary`

Resumen textual del diff.

### `raw`

Datos crudos del proveedor Git.

---

## 12) Modelo `AnalysisResult`

```python
class AnalysisResult(BaseModel):
    issue_key: str
    scope_summary: str
    business_rules: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    raw: dict[str, Any] = Field(default_factory=dict)
```

Representa el resultado de analizar una issue y su contexto.

### `issue_key`

Issue analizada.

### `scope_summary`

Resumen del alcance funcional o tecnico.

### `business_rules`

Reglas de negocio detectadas.

Usa lista vacia por defecto.

### `assumptions`

Supuestos asumidos por el analisis.

Esto es importante para QA porque evita presentar inferencias como hechos.

### `risks`

Riesgos identificados.

### `confidence`

```python
confidence: float = Field(default=0.7, ge=0.0, le=1.0)
```

Nivel de confianza del analisis.

Valor por defecto:

```python
0.7
```

Validaciones:

- `ge=0.0`: debe ser mayor o igual a `0.0`.
- `le=1.0`: debe ser menor o igual a `1.0`.

Valores validos:

- `0.0`
- `0.5`
- `0.7`
- `1.0`

Valores invalidos:

- `-0.1`
- `1.2`

### `raw`

Datos adicionales del analisis.

---

## 13) Modelo `GeneratedFeature`

```python
class GeneratedFeature(BaseModel):
    feature_name: str
    gherkin_text: str
    language: str = "es"
    tags: list[str] = Field(default_factory=list)
    scenarios_count: int = 0
    source_issue_key: str = ""
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

Representa una feature Gherkin generada.

### `feature_name`

Nombre de la feature.

### `gherkin_text`

Texto completo en formato Gherkin.

### `language`

```python
language: str = "es"
```

Idioma de la feature.

Por defecto:

```text
es
```

### `tags`

Lista de tags Gherkin.

Ejemplo:

```python
["@smoke", "@login"]
```

### `scenarios_count`

```python
scenarios_count: int = 0
```

Cantidad de escenarios generados.

No tiene validacion explicita de minimo, por lo que Pydantic aceptaria numeros negativos si se entregan manualmente.

### `source_issue_key`

Clave de Jira desde donde se genero la feature.

### `generated_at`

```python
generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

Fecha y hora de generacion.

Validacion/default importante:

`default_factory` ejecuta la funcion en el momento de crear cada instancia.

Esto evita que todas las features compartan la misma fecha fija.

`timezone.utc` asegura que la fecha quede en UTC.

---

## 14) Modelo `ValidationResult`

```python
class ValidationResult(BaseModel):
    valid: bool
    syntax_ok: bool = True
    lint_ok: bool = True
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
```

Representa el resultado de validar una feature o artefacto.

### `valid`

Indica si el resultado general es valido.

Es obligatorio.

### `syntax_ok`

Indica si la sintaxis es correcta.

Por defecto:

```python
True
```

### `lint_ok`

Indica si paso reglas de lint o estilo.

Por defecto:

```python
True
```

### `errors`

Lista de errores encontrados.

### `warnings`

Lista de advertencias encontradas.

---

## 15) Modelo `PublishResult`

```python
class PublishResult(BaseModel):
    success: bool
    destination: Literal["xray", "jira", "confluence", "git", "local"] = "xray"
    project_key: str = ""
    created_keys: list[str] = Field(default_factory=list)
    updated_keys: list[str] = Field(default_factory=list)
    url: str = ""
    message: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
```

Representa el resultado de publicar algo en un destino externo o local.

### `success`

Indica si la publicacion fue exitosa.

### `destination`

```python
destination: Literal["xray", "jira", "confluence", "git", "local"] = "xray"
```

Destino de publicacion.

Valores permitidos:

- `xray`
- `jira`
- `confluence`
- `git`
- `local`

Valor por defecto:

```python
"xray"
```

Validacion:

Pydantic rechazara cualquier valor fuera de esa lista.

### `project_key`

Proyecto relacionado.

### `created_keys`

Lista de claves creadas.

Ejemplo:

```python
["TEST-1", "TEST-2"]
```

### `updated_keys`

Lista de claves actualizadas.

### `url`

URL del recurso publicado.

### `message`

Mensaje humano sobre el resultado.

### `payload`

Respuesta completa o datos adicionales.

---

## 16) Modelo `ExecutionResult`

```python
class ExecutionResult(BaseModel):
    success: bool
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration_seconds: float = 0.0
    execution_key: str = ""
    test_keys: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
```

Representa el resultado de una ejecucion de pruebas.

### `success`

Indica si la ejecucion general fue exitosa.

### `total`

Cantidad total de pruebas.

### `passed`

Cantidad de pruebas exitosas.

### `failed`

Cantidad de pruebas fallidas.

### `skipped`

Cantidad de pruebas omitidas.

### `duration_seconds`

Duracion total en segundos.

### `execution_key`

Clave de ejecucion en Xray/Jira.

### `test_keys`

Lista de tests asociados.

### `payload`

Datos adicionales o respuesta original.

---

## 17) Validaciones principales del archivo

### Campos obligatorios

Un campo sin valor por defecto es obligatorio.

Ejemplo:

```python
key: str
summary: str
```

Si se intenta crear `JiraIssue` sin `key`, Pydantic generara error de validacion.

### Tipos esperados

Pydantic valida los tipos definidos.

Ejemplo:

```python
success: bool
```

El modelo espera un booleano.

### Listas y diccionarios seguros

El codigo usa:

```python
Field(default_factory=list)
Field(default_factory=dict)
```

Esto evita compartir objetos mutables entre instancias.

### Rango de confianza

```python
confidence: float = Field(default=0.7, ge=0.0, le=1.0)
```

Es la validacion numerica mas clara del archivo.

Garantiza que `confidence` este entre `0.0` y `1.0`.

### Destino restringido

```python
Literal["xray", "jira", "confluence", "git", "local"]
```

Evita destinos libres o mal escritos en `PublishResult`.

---

## 18) Resumen mental rapido

`domain.py` es el archivo de contratos de datos.

Los modelos iniciales representan entidades externas:

- `JiraIssue`
- `ConfluencePage`
- `GitCommit`
- `PullRequest`
- `XrayImportResponse`

Los modelos nuevos representan el flujo interno:

- `IssueContext`
- `ConfluenceContext`
- `GitContext`
- `AnalysisResult`
- `GeneratedFeature`
- `ValidationResult`
- `PublishResult`
- `ExecutionResult`

La clave tecnica del archivo es Pydantic: cada clase hereda de `BaseModel`, lo que entrega validacion, serializacion y estructura consistente para el resto del proyecto.
