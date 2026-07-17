# Explicacion detallada de validator_service.py

Este documento explica `src/ai_qa_gherkin/services/validator_service.py`: reglas, validaciones, errores y salida.

## 1) Objetivo

`validator_service.py` valida calidad de archivos Gherkin.

Valida:

1. Estructura basica.
2. Existencia de Feature y Scenarios.
3. Presencia de When y Then.
4. Scenario Outline con Examples.
5. Pasos ambiguos.
6. Nombres poco claros.
7. Pasos duplicados.
8. Cobertura contra acceptance criteria.

## 2) `SeverityLevel`

Enum con severidades:

- `CRITICAL`: bloquea publicacion.
- `ERROR`: bloquea publicacion.
- `WARNING`: advierte, pero permite publicar.
- `INFO`: informacion no bloqueante.

## 3) `ValidationRule`

Define una regla de validacion.

Campos:

- `rule_id`: identificador estable, por ejemplo `FEATURE_REQUIRED`.
- `name`: nombre humano.
- `severity`: valor `SeverityLevel`.
- `description`: explicacion de la regla.

`to_dict()` serializa la regla y convierte severidad a string con `self.severity.value`.

## 4) `ValidationError`

Representa una falla detectada.

Campos:

- `rule`: regla incumplida.
- `message`: mensaje concreto.
- `line_number`: linea asociada, puede ser `None`.
- `suggestion`: sugerencia de correccion.

`to_dict()` devuelve:

- `rule_id`
- `severity`
- `line`
- `message`
- `suggestion`

## 5) `GherkinValidator`

Servicio validador principal.

Constructor:

- `self.errors`: lista de errores detectados.
- `self.rules`: diccionario de reglas inicializadas.

## 6) `_initialize_rules`

Crea reglas:

- `feature_required`
- `scenario_required`
- `when_then_required`
- `ambiguous_step`
- `unclear_name`
- `missing_examples`
- `duplicate_scenario`
- `incomplete_coverage`
- `invalid_syntax`

Cada regla tiene id, nombre, severidad y descripcion.

## 7) `validate`

Firma:

```python
def validate(self, gherkin_text: str, acceptance_criteria: list[str] | None = None) -> ValidationResult:
```

Flujo:

1. Limpia `self.errors`.
2. Normaliza `acceptance_criteria` a lista.
3. Ejecuta `_validate_structure`.
4. Si no hay errores, ejecuta semantica y cobertura.
5. Calcula errores bloqueantes.
6. Define `is_valid`.
7. Calcula `confidence`.
8. Devuelve `ValidationResult`.

Validacion clave:

```python
blocking_errors = [
    e for e in self.errors
    if e.rule.severity in [SeverityLevel.CRITICAL, SeverityLevel.ERROR]
]
```

Solo `CRITICAL` y `ERROR` bloquean.

## 8) `_validate_structure`

Revisa:

- cuantas Feature existen.
- cuantos Scenario existen.
- cuantos Scenario Outline existen.
- si cada outline tiene Examples.
- si cada scenario tiene When y Then.

Variables:

- `feature_count`
- `feature_line`
- `scenario_count`
- `outline_count`

Errores:

- sin Feature: `FEATURE_REQUIRED`.
- mas de una Feature: `FEATURE_REQUIRED`.
- sin Scenarios: `SCENARIO_REQUIRED`.

## 9) `_validate_outline_has_examples`

Desde la linea del outline busca `Examples:` o `Ejemplos:`.

Si encuentra otro scenario antes de examples, corta.

Si no encuentra examples, agrega `MISSING_EXAMPLES`.

## 10) `_validate_when_then`

Controla que cada scenario tenga:

- al menos un `Cuando` o `When`.
- al menos un `Entonces` o `Then`.

Variables:

- `in_scenario`
- `scenario_line`
- `has_when`
- `has_then`

Valida el scenario anterior al encontrar uno nuevo y tambien valida el ultimo al terminar.

## 11) `_validate_semantics`

Busca problemas de calidad.

Patrones ambiguos:

- pasos como `Dado test`.
- pasos con solo numeros.
- pasos demasiado cortos.

Tambien detecta pasos duplicados removiendo la keyword Gherkin y comparando en minusculas.

Valida nombres de scenario:

- menor a 5 caracteres: warning.
- mayor a 100 caracteres: warning.

## 12) `_validate_coverage`

Compara Gherkin contra acceptance criteria.

Si no hay AC, omite validacion.

Para cada AC:

1. Toma primeras 3 palabras.
2. Busca si alguna aparece en el Gherkin.
3. Calcula ratio.

Si cobertura es menor a 80%, agrega `INCOMPLETE_COVERAGE`.

## 13) `_calculate_confidence`

Si el Gherkin es valido:

- base `0.95`.
- resta `0.05` por warning.
- minimo `0.5`.

Si es invalido:

- base `0.2`.
- resta `0.1` por error bloqueante.
- minimo `0.1`.

Siempre limita a maximo `1.0` y redondea a 2 decimales.

## 14) `get_summary`

Devuelve texto con:

- total de issues.
- critical.
- errors.
- warnings.
- estado VALID o INVALID.

## 15) Puntos de mejora

- `invalid_syntax` se inicializa pero no se usa directamente.
- `Scenario Outline` no se integra en `_validate_when_then`, que solo detecta `Escenario:` y `Scenario:`.
- La cobertura por primeras 3 palabras es aproximada y puede dar falsos positivos.
