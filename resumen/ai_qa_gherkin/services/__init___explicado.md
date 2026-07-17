# Explicacion detallada de services/__init__.py

Este documento explica `src/ai_qa_gherkin/services/__init__.py`.

## 1) Objetivo

Este archivo convierte `services` en paquete Python y define que servicios se exportan desde:

```python
from ai_qa_gherkin.services import ...
```

## 2) Importaciones publicas

Importa y reexporta:

- `AnalysisService`
- `ContextCollector`
- `GherkinService`
- `GherkinFeature`
- `GherkinScenario`
- `SummaryService`
- `ExecutiveSummary`
- `TraceabilityMatrix`
- `TraceabilityLink`
- `GherkinValidator`
- `ValidationRule`
- `ValidationError`
- `SeverityLevel`

Esto evita que otros modulos deban importar desde archivos internos como:

```python
ai_qa_gherkin.services.validator_service
```

## 3) `__all__`

`__all__` declara la API publica del paquete.

Si alguien ejecuta:

```python
from ai_qa_gherkin.services import *
```

Python exportara los nombres listados en `__all__`.

## 4) Punto importante

Hay dos clases llamadas `TraceabilityLink` en el proyecto:

1. `analysis_service.TraceabilityLink`
2. `summary_service.TraceabilityLink`

Este `__init__.py` exporta `TraceabilityLink` desde `summary_service`.

Si se necesita la de analisis, conviene importarla explicitamente desde:

```python
from ai_qa_gherkin.services.analysis_service import TraceabilityLink
```
