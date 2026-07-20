# Explicacion detallada de orchestrator.py

Este documento resume `src/ai_qa_gherkin/orchestrator.py`.

## Objetivo

`orchestrator.py` coordina el pipeline end-to-end:

1. recolectar contexto
2. analizar
3. generar Gherkin
4. validar
5. generar resumen y trazabilidad
6. guardar estado para auditoria/idempotencia

## `PipelineState`

Enum de estados:

- `IDLE`: inicial.
- `COLLECTED`: contexto recolectado.
- `ANALYZED`: analisis completado.
- `GENERATED`: feature generada.
- `VALIDATED`: feature validada.
- `PUBLISHED`: pipeline completado.
- `FAILED`: fallo en algun paso.

## `PipelineResult`

Dataclass que guarda el estado completo del pipeline.

Variables principales:

- `issue_key`: issue procesada.
- `state`: estado actual.
- `feature_path`, `summary_path`, `traceability_path`, `state_path`: rutas generadas.
- `collected_context`: contexto combinado.
- `collection_summary`: resumen auditable de Jira/Confluence/Git.
- `analysis_result`: resultado de analisis.
- `feature_content`: Gherkin generado.
- `validation_result`: salida del validador.
- `context_hash`: hash SHA256 del contexto.
- `confidence`: confianza final.
- `llm_*`: metadata auditable de uso de IA.

`to_dict()` serializa el resultado para guardar estado.

## `Orchestrator.__init__`

Recibe:

- `output_dir`: carpeta base.
- `use_llm`: si usa LLM real.

Crea carpetas:

- `features`
- `summaries`
- `traceability`
- `state`

Inicializa servicios:

- `ContextCollector`
- `AnalysisService`
- `GherkinService`
- `GherkinValidator`
- `SummaryService`

## `run_pipeline`

Ejecuta los pasos en orden.

Si un paso deja `state=FAILED`, retorna inmediatamente.

En `finally` calcula duracion y guarda estado.

## `_collect`

Usa `collector.collect()` con:

- `issue_key`
- busqueda Confluence vacia
- repos configurados desde settings

Calcula `context_hash`, intenta cargar cache y, si no existe, guarda contexto y resumen de recoleccion.

## `_analyze`

Llama `self.analyzer.analyze(...)`.

Luego transforma el resultado a `AnalysisResult`.

Punto de cuidado:

El codigo asume que `analyzer.analyze()` devuelve dict. Eso coincide con la version actual de `AnalysisService`, pero no con versiones anteriores donde devolvia modelo.

## `_generate`

Convierte `AnalysisResult` a dict, llama `GherkinService.generate_from_analysis()` y escribe:

```text
output/features/<issue_key>.feature
```

## `_validate`

Valida `feature_content` con `GherkinValidator`.

Si `is_valid=False`, marca el pipeline como `FAILED`.

Actualiza `result.confidence` con la confianza del validador.

## `_summarize`

Genera resumen ejecutivo y trazabilidad.

Punto de cuidado:

Usa `summary_generator.generate_traceability(...)`, que existe en la version actual de `summary_service.py`.

## Idempotencia

`_calculate_context_hash()` serializa el contexto ordenado y calcula SHA256.

`_load_cached_result()` busca:

```text
<issue_key>_<context_hash>.json
```

`_save_state()` guarda:

```text
<issue_key>_state.json
```

Nota: el nombre de cache cargado y el nombre guardado no son iguales; eso puede afectar la idempotencia real.

## Resumen textual

`get_summary()` construye una salida humana con estado, duracion, rutas, conteos de analisis y validacion.

## Riesgos detectables

- Importa `XrayClient`, `PermanentError`, `TransientError`, pero no los usa directamente.
- Si `AnalysisService` o `SummaryService` cambian contrato, el orquestador puede romper.
- La idempotencia parece incompleta por diferencia entre nombre de cache y nombre de estado guardado.
