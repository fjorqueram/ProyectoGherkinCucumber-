# Explicacion detallada de analysis_service.py

Este documento explica en detalle que hace `src/ai_qa_gherkin/services/analysis_service.py`, clase por clase, metodo por metodo, validacion por validacion y variable por variable.

---

## 1) Objetivo del archivo

`analysis_service.py` analiza contexto ya recolectado y normalizado desde multiples fuentes.

Normalmente recibe el resultado de `ContextCollector.merge_contexts()` y extrae:

1. Reglas de negocio.
2. Precondiciones.
3. Caminos felices.
4. Escenarios de error.
5. Supuestos.
6. Riesgos.
7. Nivel de confianza.
8. Trazabilidad hacia la fuente original.

El resultado final se devuelve como un modelo `AnalysisResult`.

---

## 2) Importaciones

```python
from __future__ import annotations
import json
from typing import Any
from ai_qa_gherkin.logger import get_logger
from ai_qa_gherkin.models import AnalysisResult
```

### `from __future__ import annotations`

Permite usar anotaciones modernas de tipos y evaluarlas de forma diferida.

En este archivo ayuda con tipos como:

```python
int | None
list[BusinessRule]
dict[str, Any]
```

### `import json`

Importa el modulo estandar para trabajar con JSON.

Nota importante:

En la version actual del archivo, `json` esta importado pero no se usa.

Esto no rompe el codigo, pero un linter como Ruff podria marcarlo como import no usado.

### `from typing import Any`

`Any` representa cualquier tipo de dato.

Se usa en retornos como:

```python
dict[str, Any]
```

Esto tiene sentido porque los diccionarios de contexto y trazabilidad pueden contener strings, listas, numeros, `None` u otros diccionarios.

### `from ai_qa_gherkin.logger import get_logger`

Importa la funcion para crear un logger contextual.

### `from ai_qa_gherkin.models import AnalysisResult`

Importa el modelo Pydantic que representa el resultado del analisis.

`AnalysisResult` contiene campos como:

- `issue_key`
- `scope_summary`
- `business_rules`
- `assumptions`
- `risks`
- `confidence`
- `raw`

---

## 3) Logger contextual

```python
log = get_logger("analysis_service")
```

Crea un logger con el contexto `analysis_service`.

Se usa para registrar:

- inicio del analisis
- extraccion desde Jira
- extraccion desde Confluence
- extraccion desde Git
- resumen final del analisis

---

## 4) Clase `TraceabilityLink`

```python
class TraceabilityLink:
    """Representa la trazabilidad de una regla a su origen."""
```

Esta clase representa de donde salio una regla, precondicion, camino feliz o escenario de error.

Sirve para mantener trazabilidad hacia:

- Jira
- Confluence
- Git

---

## 5) Constructor `TraceabilityLink.__init__`

```python
def __init__(
    self,
    source_type: str,
    source_id: str,
    source_name: str,
    line_number: int | None = None,
) -> None:
    self.source_type = source_type
    self.source_id = source_id
    self.source_name = source_name
    self.line_number = line_number
```

### Parametro `source_type`

```python
source_type: str
```

Tipo de fuente.

Ejemplos:

- `jira`
- `confluence`
- `git`

### Parametro `source_id`

```python
source_id: str
```

Identificador de la fuente.

Ejemplos:

- clave Jira: `DYF-4307`
- ID de pagina Confluence: `123456`
- SHA de commit: `abc123`

### Parametro `source_name`

```python
source_name: str
```

Nombre descriptivo de la fuente.

Ejemplos:

- resumen de una issue
- titulo de una pagina
- descripcion de un diff

### Parametro `line_number`

```python
line_number: int | None = None
```

Numero de linea asociado a la evidencia.

Puede ser:

- `int`: si se conoce la linea exacta.
- `None`: si no aplica o no se conoce.

Valor por defecto:

```python
None
```

### Variables de instancia

```python
self.source_type = source_type
self.source_id = source_id
self.source_name = source_name
self.line_number = line_number
```

Guardan los valores recibidos para usarlos despues en `to_dict()`.

---

## 6) Metodo `TraceabilityLink.to_dict`

```python
def to_dict(self) -> dict[str, Any]:
    return {
        "source_type": self.source_type,
        "source_id": self.source_id,
        "source_name": self.source_name,
        "line_number": self.line_number,
    }
```

Convierte el objeto de trazabilidad a diccionario.

Retorna:

- `source_type`
- `source_id`
- `source_name`
- `line_number`

Esto permite insertar la trazabilidad dentro del campo `raw` de `AnalysisResult`.

---

## 7) Clase `BusinessRule`

```python
class BusinessRule:
    """Regla de negocio extraida con trazabilidad."""
```

Representa una regla de negocio detectada durante el analisis.

Cada regla mantiene:

- texto de la regla
- trazabilidad
- categoria

---

## 8) Constructor `BusinessRule.__init__`

```python
def __init__(
    self,
    rule: str,
    traceability: TraceabilityLink,
    category: str = "general",
) -> None:
    self.rule = rule
    self.traceability = traceability
    self.category = category
```

### Parametro `rule`

Texto de la regla.

Ejemplo:

```text
Feature must be valid Gherkin
```

### Parametro `traceability`

Objeto `TraceabilityLink` que indica de donde salio la regla.

### Parametro `category`

Categoria de la regla.

Valor por defecto:

```python
"general"
```

Categorias usadas en el archivo:

- `general`
- `validation`
- `permission`

---

## 9) Metodo `BusinessRule.to_dict`

```python
def to_dict(self) -> dict[str, Any]:
    return {
        "rule": self.rule,
        "traceability": self.traceability.to_dict(),
        "category": self.category,
    }
```

Convierte la regla a diccionario.

Incluye la trazabilidad tambien convertida a diccionario.

---

## 10) Clase `Precondition`

```python
class Precondition:
        """Precondicion para un escenario."""
```

Representa una precondicion detectada para un escenario.

Nota de estilo:

La indentacion interna de esta clase tiene mas espacios que el resto del archivo. Python la acepta porque es consistente dentro de la clase, pero visualmente podria normalizarse.

---

## 11) Constructor `Precondition.__init__`

```python
def __init__(self, precondition: str, traceability: TraceabilityLink) -> None:
    self.precondition = precondition
    self.traceability = traceability
```

### Parametro `precondition`

Texto de la precondicion.

Ejemplo:

```text
User must be logged in
```

### Parametro `traceability`

Origen desde donde se obtuvo la precondicion.

---

## 12) Metodo `Precondition.to_dict`

```python
def to_dict(self) -> dict[str, Any]:
    return {
        "precondition": self.precondition,
        "traceability": self.traceability.to_dict(),
    }
```

Convierte la precondicion a diccionario.

---

## 13) Clase `HappyPath`

```python
class HappyPath:
    """Camino feliz (flujo exitoso) de un escenario."""
```

Representa el flujo exitoso esperado para una funcionalidad.

---

## 14) Constructor `HappyPath.__init__`

```python
def __init__(self, name: str, steps: list[str], traceability: TraceabilityLink) -> None:
    self.name = name
    self.steps = steps
    self.traceability = traceability
```

### Parametro `name`

Nombre del camino feliz.

Ejemplo:

```text
Happy path for Smoke test Xray
```

### Parametro `steps`

Lista de pasos del flujo exitoso.

Ejemplo:

```python
[
    "User initiates the feature",
    "System validates inputs",
    "Feature is executed successfully",
    "Result is returned to user",
]
```

### Parametro `traceability`

Origen del flujo.

---

## 15) Metodo `HappyPath.to_dict`

```python
def to_dict(self) -> dict[str, Any]:
    return {
        "name": self.name,
        "steps": self.steps,
        "traceability": self.traceability.to_dict(),
    }
```

Convierte el camino feliz a diccionario.

---

## 16) Clase `ErrorScenario`

```python
class ErrorScenario:
    """Escenario de error/validacion."""
```

Representa un caso negativo, error o validacion.

---

## 17) Constructor `ErrorScenario.__init__`

```python
def __init__(
    self,
    error_type: str,
    description: str,
    expected_outcome: str,
    traceability: TraceabilityLink,
) -> None:
    self.error_type = error_type
    self.description = description
    self.expected_outcome = expected_outcome
    self.traceability = traceability
```

### Parametro `error_type`

Tipo de error.

Ejemplos usados:

- `validation`
- `boundary`

### Parametro `description`

Descripcion del escenario negativo.

### Parametro `expected_outcome`

Resultado esperado cuando ocurre el error.

### Parametro `traceability`

Origen del escenario.

---

## 18) Metodo `ErrorScenario.to_dict`

```python
def to_dict(self) -> dict[str, Any]:
    return {
        "error_type": self.error_type,
        "description": self.description,
        "expected_outcome": self.expected_outcome,
        "traceability": self.traceability.to_dict(),
    }
```

Convierte el escenario de error a diccionario.

---

## 19) Clase `AnalysisService`

```python
class AnalysisService:
```

Servicio principal del archivo.

Analiza contexto fusionado y va llenando cuatro listas internas:

- `business_rules`
- `preconditions`
- `happy_paths`
- `error_scenarios`

Luego empaqueta todo en un `AnalysisResult`.

---

## 20) Constructor `AnalysisService.__init__`

```python
def __init__(self) -> None:
    self.business_rules: list[BusinessRule] = []
    self.preconditions: list[Precondition] = []
    self.happy_paths: list[HappyPath] = []
    self.error_scenarios: list[ErrorScenario] = []
```

Inicializa el estado interno del servicio.

### `self.business_rules`

Lista de reglas de negocio encontradas.

### `self.preconditions`

Lista de precondiciones encontradas.

### `self.happy_paths`

Lista de caminos felices generados.

### `self.error_scenarios`

Lista de escenarios de error detectados.

---

## 21) Metodo `analyze`

```python
def analyze(self, merged_context: dict[str, Any]) -> AnalysisResult:
```

Metodo principal del servicio.

Recibe un contexto fusionado y devuelve un `AnalysisResult`.

### Parametro `merged_context`

Diccionario con contexto ya fusionado.

Puede contener:

- `issue`
- `confluence`
- `git`
- `primary_scope`
- `issue_key`
- `combined_acceptance_criteria`

### Log inicial

```python
log.info("Starting analysis of merged context")
```

Registra el inicio del analisis.

### Variable `issue_data`

```python
issue_data = merged_context.get("issue") or {}
```

Obtiene el bloque de issue.

Si no existe o es `None`, usa diccionario vacio.

Esto evita errores al hacer:

```python
issue_data.get(...)
```

### Variable `issue_key`

```python
issue_key = issue_data.get("issue_key") or merged_context.get("issue_key", "UNKNOWN")
```

Busca la clave de issue en dos lugares.

Primero:

```python
issue_data.get("issue_key")
```

Si no existe, usa:

```python
merged_context.get("issue_key", "UNKNOWN")
```

Si tampoco existe, queda:

```text
UNKNOWN
```

### Variable `scope`

```python
scope = merged_context.get("primary_scope", "")
```

Obtiene el alcance principal del analisis.

Si no existe, queda string vacio.

### Limpieza de analisis previos

```python
self.business_rules = []
self.preconditions = []
self.happy_paths = []
self.error_scenarios = []
```

Reinicia las listas internas antes de analizar.

Esto es importante porque el mismo objeto `AnalysisService` podria usarse para analizar mas de un contexto.

Sin esta limpieza, se mezclarian resultados viejos con nuevos.

### Extraccion desde Jira

```python
if merged_context.get("issue"):
    self._extract_from_issue(merged_context["issue"])
```

Validacion:

Si existe contexto de issue, llama al metodo privado `_extract_from_issue`.

### Extraccion desde Confluence

```python
if merged_context.get("confluence"):
    self._extract_from_confluence(merged_context["confluence"])
```

Solo analiza Confluence si existe ese bloque.

### Extraccion desde Git

```python
if merged_context.get("git"):
    self._extract_from_git(merged_context["git"])
```

Solo analiza Git si existe ese bloque.

### Construccion de `AnalysisResult`

```python
analysis_result = AnalysisResult(
    issue_key=issue_key,
    scope_summary=scope,
    business_rules=[br.rule for br in self.business_rules],
    assumptions=self._extract_assumptions(merged_context),
    risks=self._extract_risks(merged_context),
    confidence=self._calculate_confidence(),
    raw={
        "business_rules": [br.to_dict() for br in self.business_rules],
        "preconditions": [pc.to_dict() for pc in self.preconditions],
        "happy_paths": [hp.to_dict() for hp in self.happy_paths],
        "error_scenarios": [es.to_dict() for es in self.error_scenarios],
    },
)
```

Campos principales:

- `issue_key`: issue analizada.
- `scope_summary`: alcance principal.
- `business_rules`: lista simple de textos de reglas.
- `assumptions`: supuestos.
- `risks`: riesgos.
- `confidence`: confianza calculada.
- `raw`: detalle completo con trazabilidad.

### Lista simple de reglas

```python
business_rules=[br.rule for br in self.business_rules]
```

Extrae solo el texto de cada `BusinessRule`.

Esto deja el campo principal simple y facil de consumir.

### Detalle completo en `raw`

```python
"business_rules": [br.to_dict() for br in self.business_rules]
```

En `raw` se guarda el detalle completo:

- regla
- categoria
- trazabilidad

Lo mismo se hace con:

- precondiciones
- caminos felices
- escenarios de error

### Log final

```python
log.info(
    f"Analysis complete: {len(self.business_rules)} rules, "
    f"{len(self.preconditions)} preconditions, "
    f"{len(self.happy_paths)} happy paths, "
    f"{len(self.error_scenarios)} error scenarios"
)
```

Registra conteos finales.

### Retorno

```python
return analysis_result
```

Devuelve el resultado Pydantic.

---

## 22) Metodo `_extract_from_issue`

```python
def _extract_from_issue(self, issue: dict[str, Any]) -> None:
```

Extrae reglas, precondiciones y camino feliz desde una issue Jira ya normalizada.

### Variables base

```python
issue_key = issue.get("issue_key", "")
summary = issue.get("summary", "")
description = issue.get("description", "")
```

- `issue_key`: clave Jira.
- `summary`: resumen de la issue.
- `description`: descripcion.

### Variable `trace`

```python
trace = TraceabilityLink(
    source_type="jira",
    source_id=issue_key,
    source_name=summary,
)
```

Crea trazabilidad base para todo lo extraido desde esta issue.

### Regla principal desde summary

```python
if summary:
    main_rule = BusinessRule(
        rule=f"Feature '{summary}' must be implemented",
        traceability=trace,
        category="general",
    )
    self.business_rules.append(main_rule)
```

Validacion:

Solo crea regla principal si existe `summary`.

Regla generada:

```text
Feature '<summary>' must be implemented
```

Categoria:

```python
"general"
```

### Reglas desde acceptance criteria

```python
for ac in issue.get("acceptance_criteria", []):
    rule = BusinessRule(
        rule=ac,
        traceability=trace,
        category="validation",
    )
    self.business_rules.append(rule)
```

Recorre criterios de aceptacion.

Si no existen, usa lista vacia.

Cada criterio se convierte en regla de negocio categoria `validation`.

### Precondiciones desde description

```python
if "precondition" in description.lower() or "prerequisite" in description.lower():
    precond = Precondition(
        precondition=description,
        traceability=trace,
    )
    self.preconditions.append(precond)
```

Validacion:

Convierte la descripcion a minusculas y busca:

- `precondition`
- `prerequisite`

Si encuentra alguna palabra, toda la descripcion se guarda como precondicion.

Nota:

Actualmente busca palabras en ingles. No detecta automaticamente `precondicion` en espanol.

### Camino feliz desde summary

```python
if summary:
    happy_path = HappyPath(
        name=f"Happy path for {summary}",
        steps=[
            "User initiates the feature",
            "System validates inputs",
            "Feature is executed successfully",
            "Result is returned to user",
        ],
        traceability=trace,
    )
    self.happy_paths.append(happy_path)
```

Si hay summary, genera un camino feliz generico.

Pasos generados:

1. El usuario inicia la funcionalidad.
2. El sistema valida entradas.
3. La funcionalidad se ejecuta correctamente.
4. El resultado se devuelve al usuario.

---

## 23) Metodo `_extract_from_confluence`

```python
def _extract_from_confluence(self, confluence: dict[str, Any]) -> None:
```

Extrae reglas y escenarios de error desde contenido de Confluence.

### Variables base

```python
page_id = confluence.get("page_id", "")
title = confluence.get("title", "")
content = confluence.get("content", "")
```

### Variable `trace`

```python
trace = TraceabilityLink(
    source_type="confluence",
    source_id=page_id,
    source_name=title,
)
```

Trazabilidad hacia pagina Confluence.

### Regla de validacion

```python
if "validation" in content.lower():
```

Si el contenido contiene la palabra `validation`, agrega:

```text
Input validation must be performed
```

Categoria:

```python
"validation"
```

### Regla de permisos

```python
if "permission" in content.lower() or "access" in content.lower():
```

Si el contenido menciona permisos o acceso, agrega:

```text
Access control and permissions must be enforced
```

Categoria:

```python
"permission"
```

### Escenario de error

```python
if "error" in content.lower() or "exception" in content.lower():
```

Si el contenido menciona error o exception, crea un `ErrorScenario`.

Valores generados:

- `error_type`: `validation`
- `description`: `Invalid input provided`
- `expected_outcome`: `Error message displayed to user`

---

## 24) Metodo `_extract_from_git`

```python
def _extract_from_git(self, git: dict[str, Any]) -> None:
```

Extrae reglas y escenarios desde datos de Git.

### Variables base

```python
commit_sha = git.get("commit_sha", "")
changed_files = git.get("changed_files", [])
diff_summary = git.get("diff_summary", "")
```

### Variable `trace`

```python
trace = TraceabilityLink(
    source_type="git",
    source_id=commit_sha,
    source_name=diff_summary or "Code changes",
)
```

Trazabilidad hacia commit.

Si no hay `diff_summary`, usa:

```text
Code changes
```

### Variable `test_files`

```python
test_files = [f for f in changed_files if "test" in f.lower()]
```

Filtra archivos cuyo nombre o ruta contiene `test`.

Ejemplos que entran:

- `tests/test_feature.py`
- `src/test_utils.py`

### Regla de cobertura

```python
if test_files:
    rule = BusinessRule(
        rule=f"Feature must have test coverage ({len(test_files)} test files)",
        traceability=trace,
        category="validation",
    )
    self.business_rules.append(rule)
```

Si hay archivos de test, agrega una regla sobre cobertura.

Incluye la cantidad de archivos detectados.

### Escenario boundary

```python
if any("boundary" in f for f in changed_files):
```

Busca si algun archivo contiene la palabra `boundary`.

Si existe, agrega un escenario de error tipo `boundary`.

Nota:

Esta validacion es sensible a mayusculas/minusculas porque no usa `f.lower()`. Un archivo llamado `BoundaryTest.py` no seria detectado por esta condicion.

---

## 25) Metodo `_extract_assumptions`

```python
def _extract_assumptions(self, context: dict[str, Any]) -> list[str]:
```

Devuelve una lista de supuestos.

Actualmente no usa el parametro `context`.

Supuestos retornados:

```python
[
    "Issue is well-defined with clear acceptance criteria",
    "All required integrations are available",
    "Network connectivity is stable",
]
```

Estos supuestos indican condiciones asumidas por el analisis.

---

## 26) Metodo `_extract_risks`

```python
def _extract_risks(self, context: dict[str, Any]) -> list[str]:
```

Devuelve una lista de riesgos potenciales.

Actualmente no usa el parametro `context`.

Riesgos retornados:

```python
[
    "Integration failures with external services",
    "Data validation edge cases",
    "Performance issues with large datasets",
    "Concurrent access conflicts",
]
```

---

## 27) Metodo `_calculate_confidence`

```python
def _calculate_confidence(self) -> float:
```

Calcula nivel de confianza segun la cantidad total de elementos extraidos.

### Variable `total_extractions`

```python
total_extractions = (
    len(self.business_rules)
    + len(self.preconditions)
    + len(self.happy_paths)
    + len(self.error_scenarios)
)
```

Suma:

- cantidad de reglas
- cantidad de precondiciones
- cantidad de caminos felices
- cantidad de escenarios de error

### Variable `confidence`

```python
confidence = min(0.5 + (total_extractions * 0.05), 1.0)
```

Formula:

```text
0.5 + total_extractions * 0.05
```

La confianza base es `0.5`.

Por cada extraccion se suma `0.05`.

La funcion `min(..., 1.0)` limita el maximo a `1.0`.

Ejemplos:

- 0 extracciones: `0.5`
- 2 extracciones: `0.6`
- 6 extracciones: `0.8`
- 20 extracciones: `1.0`

### Retorno redondeado

```python
return round(confidence, 2)
```

Devuelve la confianza con dos decimales.

---

## 28) Metodo `get_summary`

```python
def get_summary(self) -> str:
```

Devuelve un resumen textual del estado actual del servicio.

```python
return (
    f"Analysis Summary:\n"
    f"  Business Rules: {len(self.business_rules)}\n"
    f"  Preconditions: {len(self.preconditions)}\n"
    f"  Happy Paths: {len(self.happy_paths)}\n"
    f"  Error Scenarios: {len(self.error_scenarios)}\n"
    f"  Confidence: {self._calculate_confidence():.1%}"
)
```

Incluye:

- cantidad de reglas
- cantidad de precondiciones
- cantidad de caminos felices
- cantidad de escenarios de error
- confianza en formato porcentaje

Formato de confianza:

```python
{self._calculate_confidence():.1%}
```

Ejemplo:

```text
70.0%
```

---

## 29) Flujo completo del servicio

Flujo tipico:

1. Otro servicio arma un `merged_context`.
2. Se instancia `AnalysisService`.
3. Se llama `analyze(merged_context)`.
4. El servicio limpia resultados anteriores.
5. Extrae informacion desde `issue`, si existe.
6. Extrae informacion desde `confluence`, si existe.
7. Extrae informacion desde `git`, si existe.
8. Calcula supuestos, riesgos y confianza.
9. Devuelve un `AnalysisResult`.
10. Opcionalmente se llama `get_summary()` para ver conteos.

---

## 30) Validaciones principales

### Fallback seguro para issue

```python
issue_data = merged_context.get("issue") or {}
```

Evita errores cuando `issue` es `None`.

### Fallback de issue key

```python
issue_data.get("issue_key") or merged_context.get("issue_key", "UNKNOWN")
```

Busca la clave en mas de un lugar.

### Extraccion condicional por fuente

```python
if merged_context.get("issue"):
if merged_context.get("confluence"):
if merged_context.get("git"):
```

Solo analiza fuentes existentes.

### Summary requerido para regla principal y happy path

```python
if summary:
```

Evita crear regla principal o camino feliz sin nombre.

### Deteccion de precondiciones

```python
"precondition" in description.lower()
"prerequisite" in description.lower()
```

Detecta precondiciones explicitas en ingles.

### Deteccion en Confluence

```python
"validation" in content.lower()
"permission" in content.lower()
"access" in content.lower()
"error" in content.lower()
"exception" in content.lower()
```

Extrae reglas o errores segun palabras clave.

### Deteccion de tests en Git

```python
"test" in f.lower()
```

Detecta archivos de prueba sin distinguir mayusculas/minusculas.

### Limite de confianza

```python
min(..., 1.0)
```

Impide que `confidence` supere `1.0`.

---

## 31) Variables principales y significado

| Variable | Donde aparece | Significado |
| --- | --- | --- |
| `log` | modulo | Logger contextual del servicio. |
| `source_type` | `TraceabilityLink` | Tipo de fuente: Jira, Confluence o Git. |
| `source_id` | `TraceabilityLink` | Identificador de la fuente. |
| `source_name` | `TraceabilityLink` | Nombre descriptivo de la fuente. |
| `line_number` | `TraceabilityLink` | Linea exacta de evidencia si existe. |
| `rule` | `BusinessRule` | Texto de regla de negocio. |
| `traceability` | varias clases | Objeto que indica origen del dato. |
| `category` | `BusinessRule` | Categoria de regla. |
| `precondition` | `Precondition` | Texto de precondicion. |
| `name` | `HappyPath` | Nombre del camino feliz. |
| `steps` | `HappyPath` | Pasos del flujo exitoso. |
| `error_type` | `ErrorScenario` | Tipo de error. |
| `description` | varias clases/metodos | Descripcion de issue o error. |
| `expected_outcome` | `ErrorScenario` | Resultado esperado ante error. |
| `merged_context` | `analyze` | Contexto fusionado de entrada. |
| `issue_data` | `analyze` | Bloque de issue dentro del contexto. |
| `issue_key` | `analyze`, `_extract_from_issue` | Clave Jira. |
| `scope` | `analyze` | Alcance principal. |
| `analysis_result` | `analyze` | Resultado final del analisis. |
| `issue` | `_extract_from_issue` | Diccionario normalizado de Jira. |
| `summary` | `_extract_from_issue` | Resumen de issue. |
| `trace` | extractores | Trazabilidad base de la fuente. |
| `confluence` | `_extract_from_confluence` | Diccionario normalizado de Confluence. |
| `page_id` | `_extract_from_confluence` | ID de pagina. |
| `title` | `_extract_from_confluence` | Titulo de pagina. |
| `content` | `_extract_from_confluence` | Contenido textual. |
| `git` | `_extract_from_git` | Diccionario normalizado de Git. |
| `commit_sha` | `_extract_from_git` | SHA de commit. |
| `changed_files` | `_extract_from_git` | Archivos modificados. |
| `diff_summary` | `_extract_from_git` | Resumen de cambios. |
| `test_files` | `_extract_from_git` | Archivos detectados como tests. |
| `total_extractions` | `_calculate_confidence` | Conteo total de elementos extraidos. |
| `confidence` | `_calculate_confidence` | Nivel de confianza calculado. |

---

## 32) Relacion con los tests

El archivo `tests/test_analysis_service.py` cubre:

1. Creacion de `TraceabilityLink`.
2. Conversion de `TraceabilityLink` a diccionario.
3. Creacion y serializacion de `BusinessRule`.
4. Creacion de `Precondition`.
5. Creacion de `HappyPath`.
6. Creacion de `ErrorScenario`.
7. Analisis con solo issue.
8. Analisis con issue, Confluence y Git.
9. Calculo de confianza entre `0.0` y `1.0`.
10. Presencia de trazabilidad en reglas dentro de `raw`.
11. Salida textual de `get_summary`.

---

## 33) Puntos de mejora detectables

Estos puntos no impiden que los tests actuales pasen, pero ayudan a entender oportunidades futuras:

1. `json` esta importado pero no se usa.
2. `services/__init__.py` actualmente exporta `ContextCollector` y `TextNormalizer`, pero no exporta `AnalysisService`.
3. Las clases auxiliares no heredan de Pydantic, aunque cumplen una funcion parecida de estructura de datos.
4. `_extract_assumptions` y `_extract_risks` reciben `context`, pero actualmente devuelven listas fijas.
5. La deteccion de precondiciones esta en ingles y no detecta `precondicion`.
6. La deteccion de `boundary` en Git es sensible a mayusculas/minusculas.
7. El happy path generado es generico; no deriva pasos especificos desde acceptance criteria.
8. `AnalysisResult.business_rules` guarda solo textos, y la trazabilidad queda dentro de `raw`.

---

## 34) Resumen mental rapido

`analysis_service.py` toma contexto ya recolectado y lo transforma en un analisis QA.

Las clases auxiliares guardan hallazgos con trazabilidad:

- `TraceabilityLink`
- `BusinessRule`
- `Precondition`
- `HappyPath`
- `ErrorScenario`

`AnalysisService.analyze()` coordina todo:

1. Limpia estado previo.
2. Extrae desde Jira.
3. Extrae desde Confluence.
4. Extrae desde Git.
5. Calcula supuestos, riesgos y confianza.
6. Devuelve `AnalysisResult`.

La idea central es que cada hallazgo pueda responder: que se encontro y desde donde salio.

---

## 35) Actualizacion 2026-07-17: integracion con LLMClient

La version actual de `analysis_service.py` ahora importa:

```python
from ai_qa_gherkin.clients.llm_client import LLMClient
```

Esto cambia el comportamiento del servicio: ahora puede analizar con LLM o usar el analisis manual/mock anterior.

### Constructor actualizado

```python
def __init__(self, use_llm: bool = True) -> None:
    self.use_llm = use_llm
    self.llm_client = LLMClient() if use_llm else None
```

Variables nuevas:

- `use_llm`: bandera para decidir si se usa LLM.
- `llm_client`: instancia de `LLMClient` si `use_llm=True`; si no, queda `None`.

Impacto:

- En ejecucion normal, por defecto intenta usar LLM.
- En tests se usa `AnalysisService(use_llm=False)` para evitar llamadas reales a OpenAI.

### Flujo actualizado de `analyze`

Ahora `analyze()` decide entre dos caminos:

```python
if self.use_llm and self.llm_client is not None:
    llm_result = self.llm_client.extract_business_rules(merged_context)
    self._process_llm_result(llm_result, merged_context)
else:
    ...
```

Camino LLM:

1. Llama `LLMClient.extract_business_rules`.
2. Recibe un diccionario estructurado.
3. Procesa ese resultado con `_process_llm_result`.

Camino mock/manual:

1. Usa `_extract_from_issue`.
2. Usa `_extract_from_confluence`.
3. Usa `_extract_from_git`.

### Metodo nuevo `_process_llm_result`

Este metodo transforma la respuesta del LLM en objetos internos:

- `BusinessRule`
- `Precondition`
- `HappyPath`
- `ErrorScenario`

Crea una trazabilidad base:

```python
TraceabilityLink(
    source_type="llm",
    source_id=issue_key,
    source_name="LLM Analysis",
)
```

Esto significa que los hallazgos generados por LLM quedan marcados como fuente `llm`.

### Formatos aceptados

Para `business_rules`, acepta:

- diccionarios con `description` y `category`.
- strings simples.

Para `preconditions`, acepta:

- strings.
- diccionarios con `description`.

Para `happy_paths`, acepta:

- diccionarios con `name` y `steps`.
- strings simples.

Para `error_scenarios`, acepta:

- diccionarios con `error_type`, `description`, `expected_outcome`.
- strings simples.

### Relacion con tests actualizados

`tests/test_analysis_service.py` ahora usa principalmente:

```python
AnalysisService(use_llm=False)
```

Esto mantiene pruebas deterministicas sin depender de red, API keys ni OpenAI.

Tambien prueba directamente:

```python
service._process_llm_result(...)
```

para validar que el resultado del LLM se convierte correctamente en estructuras internas.

### Punto de cuidado

Como `use_llm=True` es el default, instanciar `AnalysisService()` puede intentar crear `LLMClient`, lo que requiere configuracion OpenAI valida. Para ejecucion local sin credenciales, usar:

```python
AnalysisService(use_llm=False)
```
