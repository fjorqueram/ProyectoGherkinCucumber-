# Explicacion detallada de cli.py

Este documento resume `src/ai_qa_gherkin/cli.py`.

## Objetivo

Define una CLI con Click para operar el proyecto desde consola.

Comandos:

- `generate`
- `validate`
- `publish`
- `run-tests`
- `report`
- `init`
- `status`
- `batch`
- `config`

## Configuracion global

El grupo `cli` recibe:

- `--output-dir`
- `--use-llm`
- `--verbose`

Guarda esos valores en `ctx.obj`.

En Windows reconfigura `stdout` y `stderr` a UTF-8 para poder imprimir acentos y simbolos.

## `generate`

Recibe `issue_key`.

Construye un `Orchestrator`, ejecuta `run_pipeline()` y falla si el estado es `FAILED`.

Imprime issue y confianza.

## `validate`

Recibe ruta a feature.

Lee archivo, instancia `GherkinValidator` y valida con criterios opcionales `--criteria`.

Sale con codigo:

- `0` si es valido.
- `1` si es invalido o falla.

## `publish`

Simula publicacion de feature a Xray.

Si no recibe `--feature`, busca:

```text
output/features/<issue_key>.feature
```

Actualmente no llama a `XrayClient`; solo imprime exito.

## `run_tests`

Simula ejecucion de tests Gherkin.

Cuenta apariciones de `Scenario:` y reporta todas como pasadas.

Punto de cuidado: no cuenta `Escenario:` en espanol.

## `report`

Busca summary y traceability en `output`.

Puede imprimir Markdown o JSON.

## `init`

Crea carpetas base y `.gherkin.json`.

Si no existe `.gitignore`, crea uno con:

```text
output/
.gherkin.json
```

## `status`

Lee:

```text
output/state/<issue_key>_state.json
```

Muestra estado, timestamp, duracion, error y rutas.

## `batch`

Procesa multiples issues en secuencia.

El parametro `--parallel` existe, pero actualmente no paraleliza.

## `config`

Con `--show`, muestra configuracion actual.

Sin `--show`, escribe `.gherkin.json`.

## Puntos de cuidado

- Importa `PipelineResult` desde `models.domain`, pero el pipeline real tambien define un `PipelineResult` dataclass en `orchestrator.py`.
- Hay imports duplicados de `sys`.
- Varios comandos simulan comportamiento en vez de ejecutar integraciones reales.
