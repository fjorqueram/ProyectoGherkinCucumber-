# Explicacion detallada de collector_service.py

Este documento explica en detalle que hace `src/ai_qa_gherkin/services/collector_service.py`, clase por clase, metodo por metodo, validacion por validacion y variable por variable.

---

## 1) Objetivo del archivo

`collector_service.py` se encarga de recolectar y normalizar informacion desde distintas fuentes.

Las fuentes principales son:

1. Jira.
2. Confluence.
3. Git.

El objetivo del archivo es transformar datos crudos, normalmente diccionarios grandes y variables, en modelos internos mas limpios:

- `IssueContext`
- `ConfluenceContext`
- `GitContext`

Tambien puede fusionar esos contextos en un unico diccionario listo para ser usado por un flujo de IA, generacion de Gherkin o analisis QA.

---

## 2) Importaciones

```python
from __future__ import annotations
import re
from typing import Any
from ai_qa_gherkin.logger import get_logger
from ai_qa_gherkin.models import (ConfluenceContext, GitContext, IssueContext)
```

### `from __future__ import annotations`

Permite usar anotaciones modernas de tipos y evaluarlas de forma diferida.

En este archivo ayuda con tipos como:

```python
str | None
IssueContext | None
```

### `import re`

Importa el modulo de expresiones regulares de Python.

Se usa para:

1. Reemplazar espacios repetidos.
2. Detectar lineas que parecen criterios de aceptacion.
3. Remover prefijos como `AC1:`, `Criterio 1:` o bullets.

### `from typing import Any`

`Any` representa cualquier tipo de dato.

Se usa en:

```python
dict[str, Any]
```

Esto indica que el diccionario tiene claves string y valores de cualquier tipo.

Tiene sentido porque los datos crudos de Jira, Confluence o Git pueden traer estructuras distintas.

### `from ai_qa_gherkin.logger import get_logger`

Importa la funcion para crear un logger contextual.

### `from ai_qa_gherkin.models import (...)`

Importa los modelos de dominio usados como salida:

- `ConfluenceContext`
- `GitContext`
- `IssueContext`

Estos modelos estan definidos en `src/ai_qa_gherkin/models/domain.py`.

---

## 3) Logger contextual

```python
log = get_logger("collector_service")
```

Crea un logger con el nombre operacional `collector_service`.

Variable:

- `log`: objeto usado para registrar eventos durante la recoleccion y fusion de contexto.

Ejemplo:

```python
log.info("Merging contexts from multiple sources")
```

---

## 4) Clase `TextNormalizer`

```python
class TextNormalizer:
    """Normaliza y limpia texto (quita ruido, duplicados, espacios extras)."""
```

Esta clase agrupa utilidades de limpieza de texto.

No guarda estado interno.

Por eso sus metodos son `@staticmethod`: se pueden llamar sin crear una instancia.

Ejemplo:

```python
TextNormalizer.normalize("  Hola   mundo ")
```

---

## 5) Metodo `TextNormalizer.normalize`

```python
@staticmethod
def normalize(text: str | None) -> str:
    """Limpia texto: espacios, saltos extra, caracteres especiales."""
    if not text:
        return ""
    
    # Remover espacios extra
    text = re.sub(r"\s+", " ", text).strip()
    # Remover URLs (opcional, segun necesidad)
    # text = re.sub(r'https?://\S+', '', text)
    return text
```

Este metodo limpia texto simple.

### Parametro `text`

```python
text: str | None
```

Puede recibir:

- un string
- `None`

Esto es util porque las APIs pueden devolver campos vacios o ausentes.

### Validacion `if not text`

```python
if not text:
    return ""
```

Valida si el texto esta vacio o es `None`.

Casos que entran:

- `None`
- `""`

Tambien entrarian otros valores falsy si se pasaran por error, aunque el tipo esperado es `str | None`.

Si no hay texto, devuelve string vacio.

Esto evita errores al aplicar expresiones regulares sobre `None`.

### Limpieza con `re.sub`

```python
text = re.sub(r"\s+", " ", text).strip()
```

Esta linea hace dos cosas.

Primero:

```python
re.sub(r"\s+", " ", text)
```

Busca cualquier secuencia de espacios en blanco y la reemplaza por un solo espacio.

El patron:

```regex
\s+
```

significa:

- `\s`: cualquier espacio en blanco, como espacio normal, tab o salto de linea.
- `+`: uno o mas.

Ejemplo:

```text
"  Hello   world  \n\n  test  "
```

queda como:

```text
" Hello world test "
```

Luego:

```python
.strip()
```

elimina espacios al inicio y al final.

Resultado final:

```text
"Hello world test"
```

### Comentario de remover URLs

```python
# text = re.sub(r'https?://\S+', '', text)
```

Esta linea esta comentada.

Si se activara, eliminaria URLs del texto.

Patron:

```regex
https?://\S+
```

Significa:

- `http` seguido opcionalmente de `s`.
- `://`
- caracteres no blancos hasta que termine la URL.

Actualmente no se ejecuta.

### Retorno

```python
return text
```

Devuelve el texto limpio.

---

## 6) Metodo `TextNormalizer.remove_duplicates`

```python
@staticmethod
def remove_duplicates(items: list[str]) -> list[str]:
    """Elimina duplicados manteniendo orden."""
    seen = set()
    result = []
    for item in items:
        normalized = item.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(item.strip())
    return result
```

Este metodo elimina duplicados de una lista de strings.

Mantiene el primer valor encontrado y conserva el orden original.

### Parametro `items`

```python
items: list[str]
```

Lista de strings.

Ejemplo:

```python
["AC1", "ac1", "AC2", "AC1"]
```

### Variable `seen`

```python
seen = set()
```

Conjunto usado para recordar que valores ya aparecieron.

Se usa un `set` porque buscar en un conjunto suele ser rapido.

### Variable `result`

```python
result = []
```

Lista final sin duplicados.

### Iteracion `for item in items`

```python
for item in items:
```

Recorre cada elemento de la lista original.

### Variable `normalized`

```python
normalized = item.strip().lower()
```

Normaliza cada elemento para comparar duplicados.

Partes:

- `strip()`: elimina espacios al inicio y final.
- `lower()`: convierte a minusculas.

Ejemplo:

```text
" AC1 " -> "ac1"
```

Esto permite considerar iguales:

- `"AC1"`
- `"ac1"`
- `" AC1 "`

### Validacion `if normalized and normalized not in seen`

```python
if normalized and normalized not in seen:
```

Tiene dos condiciones:

1. `normalized`: evita agregar strings vacios.
2. `normalized not in seen`: evita duplicados.

Si ambas se cumplen:

```python
seen.add(normalized)
result.append(item.strip())
```

### `seen.add(normalized)`

Registra el valor normalizado como ya visto.

### `result.append(item.strip())`

Agrega el valor limpio, pero conserva la capitalizacion original del primer valor encontrado.

Ejemplo:

```python
["AC1", "ac1"]
```

devuelve:

```python
["AC1"]
```

### Retorno

```python
return result
```

Devuelve la lista sin duplicados.

---

## 7) Metodo `TextNormalizer.extract_ac_lines`

```python
@staticmethod
def extract_ac_lines(text: str) -> list[str]:
```

Extrae lineas que parecen criterios de aceptacion desde texto libre.

Busca patrones como:

- `AC1: ...`
- `Criterio 1: ...`
- `- ...`
- `* ...`

### Parametro `text`

```python
text: str
```

Texto completo desde donde se intentaran extraer criterios.

### Validacion `if not text`

```python
if not text:
    return []
```

Si el texto esta vacio, retorna lista vacia.

Esto evita procesar contenido inexistente.

### Variable `lines`

```python
lines = text.split("\n")
```

Divide el texto en lineas usando salto de linea.

Ejemplo:

```text
AC1: User can login
AC2: Password is required
```

se convierte en:

```python
["AC1: User can login", "AC2: Password is required"]
```

### Variable `criteria`

```python
criteria = []
```

Lista donde se guardan los criterios detectados.

### Iteracion por lineas

```python
for line in lines:
    line = line.strip()
```

Recorre cada linea y elimina espacios iniciales/finales.

### Validacion con `re.match`

```python
if re.match(r"^(AC\d+|Criterio\s+\d+|[-*])\s*[:\s]", line, re.IGNORECASE):
```

Esta es la validacion principal del metodo.

Busca si una linea empieza con alguno de estos prefijos:

1. `AC` seguido de numeros.
2. `Criterio` seguido de espacios y numeros.
3. Bullet `-`.
4. Bullet `*`.

Desglose del patron:

```regex
^
```

Inicio de la linea.

```regex
(AC\d+|Criterio\s+\d+|[-*])
```

Grupo de alternativas:

- `AC\d+`: `AC` seguido de uno o mas digitos. Ejemplo: `AC1`, `AC20`.
- `Criterio\s+\d+`: palabra `Criterio`, espacios y numero. Ejemplo: `Criterio 1`.
- `[-*]`: un guion `-` o asterisco `*`.

```regex
\s*[:\s]
```

Permite espacios y luego exige `:` o un espacio.

Bandera:

```python
re.IGNORECASE
```

Hace la busqueda sin distinguir mayusculas/minusculas.

Ejemplos que matchean:

- `AC1: Usuario puede iniciar sesion`
- `ac2: Password obligatorio`
- `Criterio 1: Debe mostrar error`
- `- Validar email`
- `* Campo requerido`

### Variable `cleaned`

```python
cleaned = re.sub(
    r"^(AC\d+|Criterio\s+\d+|[-*])\s*[:]*\s*",
    "",
    line,
    flags=re.IGNORECASE,
)
```

Remueve el prefijo detectado.

Ejemplo:

```text
"AC1: User can login"
```

queda:

```text
"User can login"
```

Ejemplo:

```text
"- Criteria 1"
```

queda:

```text
"Criteria 1"
```

### Validacion `if cleaned`

```python
if cleaned:
    criteria.append(cleaned)
```

Solo agrega criterios que tengan contenido despues de quitar el prefijo.

Evita agregar strings vacios.

### Retorno con deduplicacion

```python
return TextNormalizer.remove_duplicates(criteria)
```

Antes de devolver, elimina duplicados.

Esto evita repetir criterios iguales escritos con distinta capitalizacion o espacios.

---

## 8) Clase `ContextCollector`

```python
class ContextCollector:
    """
    Recolecta informacion de multiples fuentes (Jira, Confluence, Git)
    y normaliza en un contexto unico para IA.
    """
```

Esta clase usa `TextNormalizer` para convertir datos crudos en modelos de contexto.

Su responsabilidad principal es adaptar datos externos al formato interno del proyecto.

---

## 9) Constructor `ContextCollector.__init__`

```python
def __init__(self) -> None:
    self.normalizer = TextNormalizer()
```

Inicializa el recolector.

### Variable `self.normalizer`

```python
self.normalizer = TextNormalizer()
```

Instancia de `TextNormalizer`.

Aunque los metodos de `TextNormalizer` son estaticos, aqui se guarda una instancia para usarla de forma consistente:

```python
self.normalizer.normalize(...)
self.normalizer.remove_duplicates(...)
self.normalizer.extract_ac_lines(...)
```

---

## 10) Metodo `collect_issue_context`

```python
def collect_issue_context(self, issue_data: dict[str, Any]) -> IssueContext:
```

Normaliza un diccionario de Jira en un modelo `IssueContext`.

### Parametro `issue_data`

```python
issue_data: dict[str, Any]
```

Diccionario con datos de una issue.

Puede venir desde Jira o desde un cliente que ya transformo parcialmente la respuesta.

### Log inicial

```python
log.info(f"Collecting issue context from {issue_data.get('key', 'unknown')}")
```

Registra desde que issue se esta recolectando contexto.

Si no existe `key`, usa:

```text
unknown
```

### Variable `issue_key`

```python
issue_key = issue_data.get("key", "")
```

Obtiene la clave de Jira.

Si no existe, queda como string vacio.

### Variable `summary`

```python
summary = self.normalizer.normalize(issue_data.get("summary", ""))
```

Obtiene el resumen y lo limpia.

Si no existe `summary`, usa string vacio.

### Variable `description`

```python
description = self.normalizer.normalize(issue_data.get("description", ""))
```

Obtiene la descripcion y la normaliza.

Nota:

La normalizacion convierte saltos de linea en espacios. Esto deja la descripcion mas compacta, pero puede perder estructura visual.

### Variable `ac_text`

```python
ac_text = issue_data.get("customfield_acceptance_criteria", "")
if not ac_text:
    ac_text = issue_data.get("description", "")
```

Busca criterios de aceptacion.

Primero intenta leer:

```python
"customfield_acceptance_criteria"
```

Si ese campo no existe o esta vacio, usa la descripcion como fallback.

Validacion:

```python
if not ac_text:
```

Sirve para decidir si hay que usar `description`.

### Variable `acceptance_criteria`

```python
acceptance_criteria = self.normalizer.extract_ac_lines(ac_text)
```

Extrae criterios de aceptacion desde `ac_text`.

Devuelve una lista de strings.

Ejemplo:

Entrada:

```text
AC1: Feature must be valid
AC2: Must import successfully
```

Salida:

```python
["Feature must be valid", "Must import successfully"]
```

### Variable `labels`

```python
labels = issue_data.get("labels", [])
labels = self.normalizer.remove_duplicates(labels)
```

Obtiene labels de Jira y elimina duplicados.

Nota importante:

En la version actual del metodo, `labels` se calcula pero no se usa en el `IssueContext` final, porque el modelo `IssueContext` no tiene campo `labels`.

Esto podria ser preparacion para uso futuro o una oportunidad de mejora.

### Variable `links`

```python
links = []
```

Lista donde se guardaran claves de issues relacionadas.

### Iteracion sobre `issuelinks`

```python
for link in issue_data.get("issuelinks", []):
```

Recorre los enlaces de Jira.

Si `issuelinks` no existe, usa lista vacia.

### Variable `linked_key`

```python
linked_key = (link.get("outwardIssue", {}).get("key") or link.get("inwardIssue", {}).get("key"))
```

Intenta obtener la clave de una issue relacionada.

Primero busca:

```python
link.get("outwardIssue", {}).get("key")
```

Si no existe, usa:

```python
link.get("inwardIssue", {}).get("key")
```

El operador:

```python
or
```

elige el primer valor truthy.

### Validacion `if linked_key`

```python
if linked_key:
    links.append(linked_key)
```

Solo agrega la clave si existe.

### Deduplicacion de `links`

```python
links = self.normalizer.remove_duplicates(links)
```

Elimina enlaces duplicados.

Nota:

Esta linea esta dentro del `for`. Funciona, pero podria ejecutarse una sola vez despues del ciclo para ser mas eficiente.

### Retorno `IssueContext`

```python
return IssueContext(
    issue_key=issue_key,
    summary=summary,
    description=description,
    acceptance_criteria=acceptance_criteria,
    links=links,
    raw=issue_data,
)
```

Construye y devuelve un modelo `IssueContext`.

Campos:

- `issue_key`: clave Jira.
- `summary`: resumen limpio.
- `description`: descripcion limpia.
- `acceptance_criteria`: criterios extraidos.
- `links`: issues relacionadas.
- `raw`: datos originales.

---

## 11) Metodo `collect_confluence_context`

```python
def collect_confluence_context(self, page_data: dict[str, Any]) -> ConfluenceContext:
```

Normaliza una pagina de Confluence en `ConfluenceContext`.

### Parametro `page_data`

Diccionario con datos de pagina Confluence.

### Log inicial

```python
log.info(f"Collecting confluence context from {page_data.get('id', 'unknown')}")
```

Registra la pagina procesada.

### Variable `page_id`

```python
page_id = page_data.get("id", "")
```

Obtiene el ID de pagina.

### Variable `title`

```python
title = self.normalizer.normalize(page_data.get("title", ""))
```

Obtiene y limpia el titulo.

### Variable `url`

```python
url = page_data.get("_links", {}).get("self", "")
```

Obtiene la URL desde `_links.self`.

Si `_links` no existe, usa `{}` para evitar error.

Si `self` no existe, usa string vacio.

### Variable `content`

```python
content = ""
```

Inicializa el contenido como string vacio.

### Validacion `if "body" in page_data`

```python
if "body" in page_data:
```

Solo intenta extraer contenido si existe la clave `body`.

### Variable `body`

```python
body = page_data.get("body", {})
```

Obtiene el body.

Puede ser:

- diccionario
- string
- otra estructura inesperada

### Caso `storage`

```python
if isinstance(body, dict) and "storage" in body:
    content = body["storage"].get("value", "")
```

Si `body` es diccionario y trae `storage`, toma:

```python
body["storage"]["value"]
```

Este formato suele venir desde Confluence cuando el contenido esta en HTML/storage format.

### Caso `plain_text`

```python
elif isinstance(body, dict) and "plain_text" in body:
    content = body["plain_text"].get("value", "")
```

Si no hay `storage`, pero hay `plain_text`, toma el valor de texto plano.

### Caso `body` como string

```python
elif isinstance(body, str):
    content = body
```

Si el body ya viene como texto, se usa directamente.

### Normalizacion de contenido

```python
content = self.normalizer.normalize(content)
```

Limpia espacios repetidos y saltos de linea.

Nota:

Si el contenido viene como HTML, esta normalizacion no elimina tags HTML. Por ejemplo, `<p>texto</p>` seguira teniendo etiquetas.

### Retorno `ConfluenceContext`

```python
return ConfluenceContext(
    page_id=page_id,
    title=title,
    url=url,
    content=content,
    raw=page_data,
)
```

Construye el modelo final con:

- ID.
- titulo limpio.
- URL.
- contenido limpio.
- datos originales.

---

## 12) Metodo `collect_git_context`

```python
def collect_git_context(self, git_data: dict[str, Any]) -> GitContext:
```

Normaliza datos provenientes de Git.

### Parametro `git_data`

Diccionario con informacion de repositorio, rama, commit, archivos y diff.

### Log inicial

```python
log.info(f"Collecting git context from {git_data.get('repo_url', 'unknown')}")
```

Registra el repositorio origen.

### Variable `repo_url`

```python
repo_url = git_data.get("repo_url", "")
```

URL del repositorio.

### Variable `branch`

```python
branch = self.normalizer.normalize(git_data.get("branch", ""))
```

Nombre de rama normalizado.

Ejemplo:

```text
"  main  " -> "main"
```

### Variable `commit_sha`

```python
commit_sha = git_data.get("commit_sha", "")
```

SHA del commit.

### Variable `changed_files`

```python
changed_files = git_data.get("changed_files", [])
changed_files = self.normalizer.remove_duplicates(changed_files)
```

Obtiene archivos modificados y elimina duplicados.

Ejemplo:

```python
["src/main.py", "tests/test.py", "src/main.py"]
```

queda:

```python
["src/main.py", "tests/test.py"]
```

### Variable `diff_summary`

```python
diff_summary = self.normalizer.normalize(git_data.get("diff_summary", ""))
```

Resumen textual del diff, normalizado.

### Retorno `GitContext`

```python
return GitContext(
    repo_url=repo_url,
    branch=branch,
    commit_sha=commit_sha,
    changed_files=changed_files,
    diff_summary=diff_summary,
    raw=git_data,
)
```

Construye el modelo final con:

- repositorio
- rama
- commit
- archivos modificados
- resumen del diff
- datos originales

---

## 13) Metodo `merge_contexts`

```python
def merge_contexts(
    self,
    issue: IssueContext | None = None,
    confluence: ConfluenceContext | None = None,
    git: GitContext | None = None,
) -> dict[str, Any]:
```

Fusiona distintos contextos en un unico diccionario.

Todos los parametros son opcionales.

### Parametro `issue`

```python
issue: IssueContext | None = None
```

Contexto de Jira.

Puede ser:

- `IssueContext`
- `None`

### Parametro `confluence`

```python
confluence: ConfluenceContext | None = None
```

Contexto de Confluence.

### Parametro `git`

```python
git: GitContext | None = None
```

Contexto de Git.

### Log inicial

```python
log.info("Merging contexts from multiple sources")
```

Registra que se esta fusionando informacion.

### Variable `merged`

```python
merged = {
    "issue": issue.model_dump() if issue else None,
    "confluence": confluence.model_dump() if confluence else None,
    "git": git.model_dump() if git else None,
    "primary_scope": "",
    "combined_acceptance_criteria": [],
    "all_labels": [],
    "related_issue": [],
}
```

Diccionario final de salida.

#### Clave `issue`

```python
"issue": issue.model_dump() if issue else None
```

Si existe `issue`, lo convierte a diccionario con `model_dump()`.

Si no existe, deja `None`.

#### Clave `confluence`

Hace lo mismo con `ConfluenceContext`.

#### Clave `git`

Hace lo mismo con `GitContext`.

#### Clave `primary_scope`

```python
"primary_scope": ""
```

Resumen principal del alcance.

Inicialmente queda vacio.

#### Clave `combined_acceptance_criteria`

```python
"combined_acceptance_criteria": []
```

Lista donde se agruparan criterios de aceptacion.

#### Clave `all_labels`

```python
"all_labels": []
```

Lista destinada a agrupar labels.

Nota:

Actualmente se llena con `issue.links`, no con labels reales, porque `IssueContext` no trae campo `labels`.

#### Clave `related_issue`

```python
"related_issue": []
```

Lista de issues relacionadas.

Nota de nombre:

El nombre esta en singular (`related_issue`), aunque contiene una lista. Podria llamarse `related_issues` para ser mas claro.

### Scope principal

```python
if issue:
    merged["primary_scope"] = issue.summary
    merged["related_issue"] = issue.links
```

Si hay contexto de Jira:

- usa el `summary` como alcance principal.
- usa `links` como issues relacionadas.

Prioridad:

La docstring dice que la prioridad es Jira > Confluence > Git.

En la implementacion actual, solo Jira llena `primary_scope`.

Si no hay `issue`, no se usa Confluence ni Git como fallback para `primary_scope`.

### Variable `ac_set`

```python
ac_set = set()
if issue:
    ac_set.update(issue.acceptance_criteria)
merged["combined_acceptance_criteria"].extend(ac_set)
```

Agrupa criterios de aceptacion sin duplicados usando un `set`.

Si existe `issue`, agrega:

```python
issue.acceptance_criteria
```

Luego extiende la lista final con ese set.

Nota:

Un `set` elimina duplicados, pero no garantiza orden estable. Si el orden de criterios importa, convendria usar `TextNormalizer.remove_duplicates`.

### Variable `label_set`

```python
label_set = set()
if issue:
    label_set.update(issue.links)
merged["all_labels"].extend(label_set)
```

Agrupa valores en `all_labels`.

Importante:

Actualmente usa:

```python
issue.links
```

Eso significa que `all_labels` termina conteniendo issues relacionadas, no labels reales.

Puede ser intencional temporalmente, pero por nombre del campo parece una oportunidad de ajuste futuro.

### Retorno

```python
return merged
```

Devuelve el diccionario fusionado.

---

## 14) Flujo completo del servicio

Un flujo tipico seria:

1. Recibir datos crudos desde Jira.
2. Llamar `collect_issue_context(issue_data)`.
3. Recibir datos crudos desde Confluence.
4. Llamar `collect_confluence_context(page_data)`.
5. Recibir datos crudos desde Git.
6. Llamar `collect_git_context(git_data)`.
7. Llamar `merge_contexts(issue, confluence, git)`.
8. Usar el resultado como contexto para IA o generacion de pruebas.

---

## 15) Validaciones principales

### Texto vacio o `None`

```python
if not text:
    return ""
```

Evita errores en limpieza de texto.

### Duplicados

```python
if normalized and normalized not in seen:
```

Evita strings vacios y duplicados.

### Criterios de aceptacion

```python
re.match(r"^(AC\d+|Criterio\s+\d+|[-*])\s*[:\s]", ...)
```

Detecta solo lineas con formatos reconocidos.

### Fallback de acceptance criteria

```python
if not ac_text:
    ac_text = issue_data.get("description", "")
```

Si no hay campo especifico de criterios de aceptacion, se intenta extraer desde la descripcion.

### Extraccion segura de diccionarios anidados

```python
page_data.get("_links", {}).get("self", "")
```

Evita errores si `_links` no existe.

### Validacion de tipo en body de Confluence

```python
isinstance(body, dict)
isinstance(body, str)
```

Permite manejar varias formas de contenido.

### Parametros opcionales en merge

```python
issue.model_dump() if issue else None
```

Evita llamar `model_dump()` sobre `None`.

---

## 16) Variables principales y significado

| Variable | Donde aparece | Significado |
| --- | --- | --- |
| `log` | modulo | Logger contextual del servicio. |
| `text` | `normalize`, `extract_ac_lines` | Texto a limpiar o analizar. |
| `items` | `remove_duplicates` | Lista de strings a deduplicar. |
| `seen` | `remove_duplicates` | Set de valores ya vistos. |
| `result` | `remove_duplicates` | Lista final sin duplicados. |
| `normalized` | `remove_duplicates` | Version limpia y en minusculas para comparar. |
| `lines` | `extract_ac_lines` | Texto separado por saltos de linea. |
| `criteria` | `extract_ac_lines` | Criterios detectados. |
| `line` | `extract_ac_lines` | Linea actual procesada. |
| `cleaned` | `extract_ac_lines` | Linea sin prefijo AC/Criterio/bullet. |
| `self.normalizer` | `ContextCollector` | Utilidad de normalizacion. |
| `issue_data` | `collect_issue_context` | Diccionario crudo de Jira. |
| `issue_key` | `collect_issue_context` | Clave de Jira. |
| `summary` | `collect_issue_context` | Resumen limpio. |
| `description` | `collect_issue_context` | Descripcion limpia. |
| `ac_text` | `collect_issue_context` | Texto fuente para criterios de aceptacion. |
| `acceptance_criteria` | `collect_issue_context` | Lista de criterios extraidos. |
| `labels` | `collect_issue_context` | Labels deduplicados, actualmente no retornados. |
| `links` | `collect_issue_context` | Issues relacionadas. |
| `page_data` | `collect_confluence_context` | Diccionario crudo de Confluence. |
| `page_id` | `collect_confluence_context` | ID de pagina. |
| `title` | `collect_confluence_context` | Titulo limpio. |
| `url` | `collect_confluence_context` | URL de pagina. |
| `content` | `collect_confluence_context` | Contenido limpio. |
| `body` | `collect_confluence_context` | Cuerpo de pagina. |
| `git_data` | `collect_git_context` | Diccionario crudo de Git. |
| `repo_url` | `collect_git_context` | URL del repositorio. |
| `branch` | `collect_git_context` | Rama limpia. |
| `commit_sha` | `collect_git_context` | SHA del commit. |
| `changed_files` | `collect_git_context` | Archivos modificados sin duplicados. |
| `diff_summary` | `collect_git_context` | Resumen limpio del diff. |
| `merged` | `merge_contexts` | Diccionario final fusionado. |
| `ac_set` | `merge_contexts` | Set de criterios de aceptacion. |
| `label_set` | `merge_contexts` | Set usado para llenar `all_labels`. |

---

## 17) Relacion con los tests

El archivo `tests/test_collector_service.py` valida los comportamientos principales:

1. `normalize` limpia espacios y saltos extra.
2. `normalize` retorna `""` con texto vacio o `None`.
3. `remove_duplicates` elimina duplicados ignorando mayusculas/minusculas.
4. `extract_ac_lines` detecta prefijos `AC1`, `AC2`, etc.
5. `extract_ac_lines` detecta bullets `-` y `*`.
6. `collect_issue_context` limpia summary y extrae criterios.
7. `collect_confluence_context` extrae titulo, ID, URL y contenido.
8. `collect_git_context` limpia rama y deduplica archivos.
9. `merge_contexts` fusiona contexto de issue.

---

## 18) Puntos de mejora detectables

Estos no impiden que el codigo funcione, pero ayudan a entenderlo mejor:

1. `labels` se calcula en `collect_issue_context`, pero no se usa en el retorno.
2. `all_labels` en `merge_contexts` se llena con `issue.links`, no con labels.
3. `related_issue` contiene una lista, por claridad podria llamarse `related_issues`.
4. La deduplicacion de `links` ocurre dentro del ciclo; podria hacerse despues.
5. `merge_contexts` dice prioridad Jira > Confluence > Git, pero solo Jira define `primary_scope`.
6. `extract_ac_lines` no detecta criterios escritos sin prefijo o con otros formatos.
7. `collect_confluence_context` normaliza HTML, pero no remueve etiquetas HTML.

---

## 19) Resumen mental rapido

`collector_service.py` tiene dos piezas:

1. `TextNormalizer`: limpia texto, elimina duplicados y extrae criterios de aceptacion.
2. `ContextCollector`: convierte datos crudos de Jira, Confluence y Git en modelos internos.

Los metodos principales son:

- `collect_issue_context`
- `collect_confluence_context`
- `collect_git_context`
- `merge_contexts`

La idea central es preparar informacion limpia y estructurada para que otros servicios puedan analizarla, generar Gherkin o publicarla con mejor trazabilidad.
