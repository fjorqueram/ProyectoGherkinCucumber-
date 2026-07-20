# Explicacion detallada de summary_service.py

Este documento explica `src/ai_qa_gherkin/services/summary_service.py`: clases, metodos, variables y validaciones principales.

## 1) Objetivo

`summary_service.py` genera artefactos de cierre para QA:

1. Resumen ejecutivo de una historia.
2. Matriz de trazabilidad entre AC, escenarios y fuentes.
3. Archivos Markdown o JSON en carpetas de salida.

## 2) Importaciones

- `json`: serializa resumen o matriz cuando el formato no es Markdown.
- `os`: crea carpetas y arma rutas.
- `datetime`: genera timestamp con `datetime.now().isoformat()`.
- `Any`: permite diccionarios flexibles.
- `get_logger`: crea logger contextual `summary_service`.

## 3) `ExecutiveSummary`

Representa un resumen ejecutivo de una historia.

Constructor:

```python
def __init__(self, issue_key: str, summary: str, description: str = "") -> None:
```

Variables:

- `issue_key`: clave Jira o identificador principal.
- `summary`: titulo breve.
- `description`: descripcion enriquecida con metricas.
- `generated_at`: fecha/hora ISO generada automaticamente.

`to_dict()` devuelve un diccionario con esos cuatro campos.

`to_markdown()` genera:

- titulo `# <issue_key>: <summary>`
- descripcion
- timestamp de generacion.

## 4) `TraceabilityLink`

Representa una relacion AC -> Scenario -> Fuente.

Campos:

- `ac_id`: identificador del criterio, por ejemplo `AC-1`.
- `ac_text`: texto del criterio de aceptacion.
- `scenario_name`: escenario asociado.
- `scenario_line`: linea aproximada del escenario.
- `source_type`: fuente, por ejemplo `jira` o `confluence`.
- `source_id`: id de la fuente.
- `source_name`: nombre legible de la fuente.

`to_dict()` agrupa el resultado en:

- datos de AC.
- bloque `scenario`.
- bloque `source`.

## 5) `TraceabilityMatrix`

Agrupa muchos `TraceabilityLink` para una issue.

Variables:

- `issue_key`: historia o issue asociada.
- `links`: lista de enlaces de trazabilidad.
- `generated_at`: timestamp ISO.

`add_link()` agrega un enlace a `links`.

`get_ac_coverage()` construye un mapa:

```python
{
    "AC-1": ["Scenario 1"],
    "AC-2": ["Scenario 2"],
}
```

Validacion/calculo:

- `total_ac`: cantidad de AC unicas.
- `covered_ac`: actualmente igual a `total_ac`, porque solo cuenta AC presentes en enlaces.
- `coverage_ratio`: `1.0` si hay AC, `0.0` si no hay.
- `ac_scenarios`: mapa AC -> escenarios.

`get_source_distribution()` cuenta cuantas trazas vienen de cada fuente.

`to_dict()` serializa matriz completa.

`to_markdown()` crea una tabla Markdown con columnas:

- AC
- Scenario
- Linea
- Fuente
- ID

Tambien agrega secciones de cobertura y distribucion de fuentes.

## 6) `SummaryService`

Servicio principal.

Constructor:

```python
def __init__(
    self,
    output_summary: str = "output/summaries",
    output_traceability: str = "output/traceability",
) -> None:
```

Variables:

- `output_summary`: carpeta para resumenes.
- `output_traceability`: carpeta para matrices.

## 7) `generate_executive_summary`

Genera un `ExecutiveSummary`.

Entradas:

- `issue_key`: clave de issue.
- `analysis_result`: analisis de negocio.
- `validation_result`: resultado de validacion.
- `gherkin_path`: ruta del `.feature`.

Variables:

- `issue`: toma `analysis_result["issue"]`.
- `summary_text`: resumen de la issue.
- `business_rules`: reglas detectadas.
- `scenarios_count`: actualmente se calcula con `raw.detailed_errors`, por nombre parece representar errores detallados mas que escenarios reales.
- `description`: Markdown con negocio, validacion y archivo.

Validaciones/defaults:

- usa `{}` o `[]` si faltan claves.
- `confidence` cae a `0` si no existe.
- el estado usa `is_valid` para mostrar valido/invalido.

## 8) `generate_traceability_matrix`

Crea una matriz desde `analysis_result`.

Flujo:

1. Crea `TraceabilityMatrix(issue_key)`.
2. Lee `issue.acceptance_criteria`.
3. Lee `raw.business_rules`.
4. Por cada AC crea `AC-<numero>`.
5. Intenta usar la trazabilidad de la regla correspondiente.
6. Si no hay trazabilidad, usa defaults Jira.

La linea del escenario se calcula aproximada:

```python
scenario_line=5 + (ac_idx * 5)
```

## 9) `save_summary`

Guarda resumen ejecutivo.

Validaciones:

- crea carpeta con `os.makedirs(..., exist_ok=True)`.
- si `format == "markdown"`, usa `to_markdown()`.
- si no, serializa JSON.

Archivo:

```text
<issue_key>_summary.md
```

## 10) `save_traceability`

Guarda matriz de trazabilidad.

Misma logica que `save_summary`, pero usa:

```text
<issue_key>_traceability.md
```

## 11) Puntos de mejora

- `scenarios_count` se calcula desde `detailed_errors`; el nombre no coincide con la fuente.
- Los archivos siempre terminan en `.md`, incluso cuando `format` no es Markdown.
- `coverage_ratio` siempre es 100% si hay links, no mide AC sin cobertura externa.
- `scenario_line` es aproximado, no calculado desde el archivo Gherkin real.

---

## 12) Actualizacion 2026-07-20: SummaryService actual

`generate_executive_summary` ahora acepta:

- `AnalysisResult` como modelo.
- `dict` como estructura de tests.

Si recibe modelo, toma:

- `business_rules`
- `assumptions`
- `risks`
- `confidence`
- `scope_summary`

Si recibe dict con `validation_result`, mantiene el flujo anterior.

### Metodo nuevo `generate_traceability`

Genera una trazabilidad como `ExecutiveSummary`, no como `TraceabilityMatrix`.

Construye Markdown con:

- tabla AC -> Scenario -> Fuente -> Generado por -> ID.
- cobertura basada en cantidad de happy paths.
- distribucion de fuentes.

Usa `analysis_result.raw["happy_paths"]` cuando recibe modelo.

### `_clean_scenario_name`

Limpia nombres de scenario removiendo fragmentos de pasos como:

- `Dado que`
- `Cuando`
- `Entonces`
- `Given`
- `When`
- `Then`

Tambien limita el nombre a 80 caracteres.

### Compatibilidad

`generate_traceability_matrix` sigue existiendo para tests y flujo anterior.
