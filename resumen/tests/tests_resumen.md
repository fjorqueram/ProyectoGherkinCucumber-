# Resumen de todos los tests

Este documento resume los archivos dentro de `tests`.

## 1) `tests/__init__.py`

Archivo vacio.

Sirve para marcar `tests` como paquete Python si se necesita importar desde esa carpeta.

## 2) `tests/smoke.feature`

Feature Gherkin minima.

Contiene:

- `Feature: DYF-4307 Smoke Xray import`
- escenario de importacion minima.
- pasos `Given/When/Then`.

Valida conceptualmente que exista la historia, se importe el feature en Xray y la importacion se complete.

## 3) `test_models.py`

Prueba modelos Pydantic de dominio.

Cubre:

- `JiraIssue`: creacion minima, serializacion y deserializacion.
- `ConfluencePage`: campos basicos.
- `GitCommit`: SHA y mensaje.
- `PullRequest`: ID y estado.
- `XrayImportResponse`: payload exitoso.
- `IssueContext`: criterios y links.
- `ConfluenceContext`: page id y URL.
- `GitContext`: rama, commit y archivos.
- `AnalysisResult`: reglas, riesgos y validacion de `confidence <= 1.0`.
- `GeneratedFeature`: texto Gherkin y `generated_at`.
- `ValidationResult`: valido/invalido con errores.
- `PublishResult`: destino valido y rechazo de destino invalido.
- `ExecutionResult`: conteos de ejecucion.

## 4) `test_collector_service.py`

Prueba `TextNormalizer` y `ContextCollector`.

Cubre:

- limpieza de espacios y saltos.
- manejo de texto vacio o `None`.
- eliminacion de duplicados ignorando mayusculas/minusculas.
- extraccion de AC con prefijos `AC1`, `AC2`.
- extraccion de AC con bullets `-` y `*`.
- normalizacion de issue Jira.
- normalizacion de pagina Confluence.
- normalizacion de contexto Git.
- fusion de contextos.

## 5) `test_analysis_service.py`

Prueba clases de analisis y `AnalysisService`.

Cubre:

- `TraceabilityLink`.
- `BusinessRule`.
- `Precondition`.
- `HappyPath`.
- `ErrorScenario`.
- inicializacion con `use_llm=False`.
- analisis manual/mock con issue.
- analisis con Jira + Confluence + Git.
- reglas desde Confluence.
- reglas desde cambios Git.
- calculo de confianza.
- trazabilidad en reglas y precondiciones.
- resumen textual.
- contexto vacio.
- procesamiento de resultado LLM en formato dict.

Detalle importante:

Los tests fuerzan `AnalysisService(use_llm=False)` para no depender de OpenAI.

## 6) `test_gherkin_service.py`

Prueba generacion y validacion basica Gherkin.

Cubre:

- creacion de `GherkinScenario`.
- render de scenario en ingles.
- creacion de `GherkinFeature`.
- agregado de scenario.
- configuracion de background.
- render completo en espanol.
- generacion desde `analysis_result`.
- validacion de Gherkin valido.
- deteccion de scenario sin feature.
- deteccion de pasos sin keyword.
- guardado de `.feature`.
- construccion de prompt para LLM.

## 7) `test_validator_service.py`

Prueba reglas avanzadas de validacion Gherkin.

Cubre:

- `ValidationRule`.
- `ValidationError`.
- Gherkin valido.
- falta de Feature.
- falta de Scenario.
- falta de When/Then.
- pasos ambiguos.
- nombres de scenario poco claros.
- Scenario Outline sin Examples.
- Scenario Outline con Examples.
- pasos duplicados.
- cobertura baja de acceptance criteria.
- cobertura completa.
- resumen de validacion.

## 8) `test_summary_service.py`

Prueba resumen ejecutivo y matriz de trazabilidad.

Cubre:

- creacion de `ExecutiveSummary`.
- Markdown del resumen.
- creacion y serializacion de `TraceabilityLink`.
- creacion de `TraceabilityMatrix`.
- agregado de links.
- cobertura AC.
- distribucion de fuentes.
- Markdown de matriz.
- generacion de resumen ejecutivo.
- generacion de matriz desde analysis.
- guardado de resumen.
- guardado de trazabilidad.

## 9) `test_llm_client.py`

Prueba `LLMClient` con mocks.

Cubre:

- inicializacion del cliente OpenAI mockeado.
- extraccion de business rules desde una respuesta JSON simulada.

Usa:

- `patch("ai_qa_gherkin.clients.llm_client.openai")`
- `MagicMock`

Esto evita llamadas reales a OpenAI durante el test.
