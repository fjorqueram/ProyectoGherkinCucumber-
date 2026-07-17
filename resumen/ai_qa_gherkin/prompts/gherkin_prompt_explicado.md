# Explicacion detallada de gherkin_prompt.txt

Este documento explica `src/ai_qa_gherkin/prompts/gherkin_prompt.txt`.

## 1) Objetivo

El archivo define instrucciones para generar escenarios Gherkin en espanol desde analisis BDD.

Es un prompt versionado con:

- version
- fecha
- descripcion
- objetivo
- formato obligatorio
- reglas de calidad
- formato de salida

## 2) Metadata

```text
VERSION: 1.0
DATE: 2026-07-16
DESCRIPTION: Generacion de escenarios Gherkin desde analisis BDD
```

Indica version, fecha y objetivo general del prompt.

## 3) Objetivo

Pide cubrir:

1. Flujo exitoso.
2. Validaciones de entrada.
3. Manejo de errores.
4. Casos limite.

Esto alinea el prompt con buenas practicas QA: happy path, negativos y bordes.

## 4) Formato obligatorio

Define:

- idioma espanol.
- estructura Given-When-Then.
- tags esperados: `@smoke`, `@regression`, `@validation`, `@error-handling`.

## 5) Reglas de calidad

Exige:

- maximo 10 pasos por escenario.
- nombres descriptivos en lenguaje de negocio.
- sin detalles tecnicos o de implementacion.
- cada `Then` observable/testeable.
- al menos 1 happy path y 2 errores.

## 6) Salida

Pide solo texto Gherkin valido, sin explicaciones adicionales.

## 7) Relacion con el codigo

Actualmente `GherkinService._load_prompt_template()` no lee este archivo; usa un prompt hardcoded.

Por eso, modificar `gherkin_prompt.txt` todavia no cambia el prompt usado por `GherkinService.get_prompt_for_llm()`.
