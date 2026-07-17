# Explicacion detallada de gherkin_service.py

Este documento explica en detalle que hace `src/ai_qa_gherkin/services/gherkin_service.py`, clase por clase, metodo por metodo, validacion por validacion y variable por variable.

---

## 1) Objetivo del archivo

`gherkin_service.py` se encarga de generar texto Gherkin a partir de un analisis funcional.

Su proposito es:

1. Representar escenarios Gherkin individuales.
2. Representar una feature Gherkin completa.
3. Generar una feature desde un `analysis_result`.
4. Validar sintaxis basica de Gherkin.
5. Guardar una feature en archivo `.feature`.
6. Construir un prompt listo para enviar a un LLM.

Este archivo conecta el analisis QA con un artefacto usable por Cucumber/Xray.

---

## 2) Importaciones

```python
from __future__ import annotations
import re
import os
from datetime import datetime
from typing import Any
from ai_qa_gherkin.logger import get_logger
from ai_qa_gherkin.models import GeneratedFeature
```

### `from __future__ import annotations`

Permite usar anotaciones modernas de tipos.

En este archivo se usa con tipos como:

```python
list[str] | None
dict[str, Any]
```

### `import re`

Importa expresiones regulares.

Nota:

En la version actual del archivo, `re` esta importado pero no se usa.

### `import os`

Se usa para operaciones de sistema de archivos.

En concreto:

```python
os.makedirs(output_dir, exist_ok=True)
os.path.join(output_dir, filename)
```

### `from datetime import datetime`

Importa `datetime`.

Nota:

En la version actual del archivo, `datetime` esta importado pero no se usa directamente.

El modelo `GeneratedFeature` si maneja `generated_at`, pero eso ocurre dentro del modelo.

### `from typing import Any`

`Any` permite representar valores de cualquier tipo.

Se usa en:

```python
dict[str, Any]
```

porque `analysis_result` puede contener strings, listas, diccionarios y otros datos.

### `from ai_qa_gherkin.logger import get_logger`

Importa la funcion para crear un logger contextual.

### `from ai_qa_gherkin.models import GeneratedFeature`

Importa el modelo Pydantic que representa una feature generada.

Campos importantes de `GeneratedFeature`:

- `feature_name`
- `gherkin_text`
- `language`
- `tags`
- `scenarios_count`
- `source_issue_key`
- `generated_at`

---

## 3) Logger contextual

```python
log = get_logger("gherkin_service")
```

Crea un logger identificado como `gherkin_service`.

Se usa para registrar:

- generacion de Gherkin
- cantidad de escenarios generados
- ruta donde se guarda una feature

---

## 4) Clase `GherkinScenario`

```python
class GherkinScenario:
    """Representa un escenario Gherkin individual."""
```

Representa un unico escenario Gherkin.

Contiene:

- nombre
- pasos `Given/Dado`
- pasos `When/Cuando`
- pasos `Then/Entonces`
- tags
- idioma

---

## 5) Constructor `GherkinScenario.__init__`

```python
def __init__(
    self,
    name: str,
    given: list[str],
    when: list[str],
    then: list[str],
    tags: list[str] | None = None,
    language: str = "es",
) -> None:
    self.name = name
    self.given = given
    self.when = when
    self.then = then
    self.tags = tags or []
    self.language = language
```

### Parametro `name`

Nombre del escenario.

Ejemplo:

```text
Login exitoso
```

### Parametro `given`

Lista de precondiciones del escenario.

En Gherkin se renderizan como:

- `Dado`
- `Y`

o en ingles:

- `Given`
- `And`

### Parametro `when`

Lista de acciones ejecutadas.

Se renderizan como:

- `Cuando`
- `Y`

o:

- `When`
- `And`

### Parametro `then`

Lista de resultados esperados.

Se renderizan como:

- `Entonces`
- `Y`

o:

- `Then`
- `And`

### Parametro `tags`

```python
tags: list[str] | None = None
```

Lista opcional de tags del escenario.

Validacion/default:

```python
self.tags = tags or []
```

Si `tags` es `None` o lista vacia, queda como lista vacia.

### Parametro `language`

```python
language: str = "es"
```

Idioma del escenario.

Valores esperados por el codigo:

- `es`: espanol.
- cualquier otro valor: se comporta como ingles en `to_gherkin`.

---

## 6) Metodo `GherkinScenario.to_gherkin`

```python
def to_gherkin(self, indent: int = 4) -> str:
```

Genera el texto Gherkin del escenario.

### Parametro `indent`

```python
indent: int = 4
```

Cantidad de espacios para indentar el escenario.

Valor por defecto:

```python
4
```

### Variable `spacing`

```python
spacing = " " * indent
```

Crea un string de espacios.

Si `indent` es `4`, entonces:

```python
spacing == "    "
```

### Variable `result`

```python
result = ""
```

Acumula el texto Gherkin final.

### Render de tags

```python
if self.tags:
    result += f"{spacing}@" + " @".join(self.tags) + "\n"
```

Validacion:

Solo escribe tags si `self.tags` tiene elementos.

Ejemplo:

```python
tags=["smoke", "regression"]
```

produce:

```gherkin
    @smoke @regression
```

### Palabra clave de escenario

```python
scenario_kw = "Escenario:" if self.language == "es" else "Scenario:"
```

Si el idioma es `es`, usa:

```text
Escenario:
```

Si no, usa:

```text
Scenario:
```

### Nombre del escenario

```python
result += f"{spacing}{scenario_kw} {self.name}\n"
```

Agrega la linea principal del escenario.

### Palabras clave segun idioma

```python
if self.language == "es":
    given_kw, and_kw = "Dado", "Y"
    when_kw = "Cuando"
    then_kw = "Entonces"
else:
    given_kw, and_kw = "Given", "And"
    when_kw = "When"
    then_kw = "Then"
```

Define las palabras Gherkin segun idioma.

### Render de pasos `given`

```python
for i, step in enumerate(self.given):
    keyword = given_kw if i == 0 else and_kw
    result += f"{spacing * 2}{keyword} {step}\n"
```

Recorre cada precondicion.

Validacion logica:

- primer paso usa `Dado` o `Given`.
- pasos siguientes usan `Y` o `And`.

Ejemplo:

```python
given=["usuario autenticado", "sistema disponible"]
```

produce:

```gherkin
        Dado usuario autenticado
        Y sistema disponible
```

### Render de pasos `when`

```python
for i, step in enumerate(self.when):
    keyword = when_kw if i == 0 else and_kw
    result += f"{spacing * 2}{keyword} {step}\n"
```

Misma idea:

- primer paso: `Cuando` o `When`.
- siguientes: `Y` o `And`.

### Render de pasos `then`

```python
for i, step in enumerate(self.then):
    keyword = then_kw if i == 0 else and_kw
    result += f"{spacing * 2}{keyword} {step}\n"
```

Misma idea:

- primer paso: `Entonces` o `Then`.
- siguientes: `Y` o `And`.

### Retorno

```python
return result.strip()
```

Devuelve el texto quitando espacios/saltos al inicio y final.

Nota:

`strip()` tambien elimina la indentacion inicial del primer caracter si el resultado completo empieza con espacios. Por eso el escenario puede quedar sin indentacion inicial externa al devolverlo individualmente.

---

## 7) Clase `GherkinFeature`

```python
class GherkinFeature:
    """Representa un Feature Gherkin completo."""
```

Representa una feature Gherkin completa con:

- encabezado de idioma
- tags
- nombre de feature
- descripcion
- antecedentes
- escenarios

---

## 8) Constructor `GherkinFeature.__init__`

```python
def __init__(
    self,
    feature_name: str,
    description: str = "",
    language: str = "es",
    tags: list[str] | None = None,
) -> None:
    self.feature_name = feature_name
    self.description = description
    self.language = language
    self.tags = tags or []
    self.scenarios: list[GherkinScenario] = []
    self.background_steps: dict[str, list[str]] = {"given": [], "when": [], "then": []}
```

### `feature_name`

Nombre de la feature.

### `description`

Descripcion opcional.

Valor por defecto:

```python
""
```

### `language`

Idioma de la feature.

Por defecto:

```python
"es"
```

### `tags`

Tags de la feature.

Se normaliza con:

```python
tags or []
```

### `self.scenarios`

```python
self.scenarios: list[GherkinScenario] = []
```

Lista de escenarios agregados a la feature.

### `self.background_steps`

```python
self.background_steps: dict[str, list[str]] = {"given": [], "when": [], "then": []}
```

Guarda pasos de antecedentes/background separados por tipo.

Claves:

- `given`
- `when`
- `then`

---

## 9) Metodo `GherkinFeature.add_scenario`

```python
def add_scenario(self, scenario: GherkinScenario) -> None:
    self.scenarios.append(scenario)
```

Agrega un escenario a la feature.

Parametro:

- `scenario`: instancia de `GherkinScenario`.

No retorna nada.

---

## 10) Metodo `GherkinFeature.set_background`

```python
def set_background(
    self,
    given: list[str] | None = None,
    when: list[str] | None = None,
    then: list[str] | None = None,
) -> None:
    if given:
        self.background_steps["given"] = given
    if when:
        self.background_steps["when"] = when
    if then:
        self.background_steps["then"] = then
```

Establece pasos comunes de antecedentes.

### Parametros

- `given`: precondiciones comunes.
- `when`: acciones comunes.
- `then`: resultados comunes.

### Validacion `if given`

Solo actualiza `given` si recibe una lista con contenido.

Lo mismo aplica para `when` y `then`.

Nota:

Si se pasa una lista vacia para limpiar antecedentes, no se limpiara porque `[]` es falsy.

---

## 11) Metodo `GherkinFeature.to_gherkin`

```python
def to_gherkin(self) -> str:
```

Genera el texto completo de la feature.

### Header de idioma

```python
if self.language == "es":
    result += "# language: es\n"
elif self.language == "en":
    result += "# language: en\n"
```

Agrega el encabezado de idioma solo para `es` o `en`.

### Tags de Feature

```python
if self.tags:
    result += "@" + " @".join(self.tags) + "\n"
```

Si hay tags, los escribe en una sola linea.

Ejemplo:

```gherkin
@smoke @regression
```

### Feature

```python
result += f"Caracteristica: {self.feature_name}\n"
```

Agrega el nombre de la feature.

Nota:

En el archivo original aparece `Característica` con tilde. Si tu editor muestra caracteres raros, es un tema de codificacion visual, no necesariamente de logica.

### Descripcion

```python
if self.description:
    result += f"  {self.description}\n"
```

Solo agrega descripcion si existe.

### Background / Antecedentes

```python
if any(self.background_steps.values()):
```

Valida si existe al menos una lista de background con contenido.

Si existe, escribe:

```gherkin
Antecedentes:
```

y luego los pasos:

- `Dado`
- `Cuando`
- `Entonces`

Nota:

El background siempre se renderiza con palabras en espanol, incluso si `language` fuera `en`.

### Escenarios

```python
for scenario in self.scenarios:
    scenario.language = self.language
    result += scenario.to_gherkin()
    result += "\n"
```

Recorre cada escenario.

Antes de renderizar, fuerza el idioma del escenario al idioma de la feature:

```python
scenario.language = self.language
```

Esto asegura consistencia entre feature y escenarios.

### Retorno

```python
return result.strip()
```

Devuelve el texto final sin espacios al inicio/final.

---

## 12) Clase `GherkinService`

```python
class GherkinService:
```

Servicio principal para generar, validar, guardar y construir prompts Gherkin.

---

## 13) Constructor `GherkinService.__init__`

```python
def __init__(self, output_dir: str = "output/features") -> None:
    self.output_dir = output_dir
    self.prompt_template = self._load_prompt_template()
```

### Parametro `output_dir`

Directorio donde se guardaran archivos `.feature`.

Valor por defecto:

```text
output/features
```

### `self.output_dir`

Guarda el directorio de salida.

### `self.prompt_template`

Carga el template de prompt usando:

```python
self._load_prompt_template()
```

---

## 14) Metodo `_load_prompt_template`

```python
def _load_prompt_template(self) -> str:
```

Devuelve el texto base del prompt para LLM.

Actualmente retorna un string hardcoded.

Nota:

Aunque existe `src/ai_qa_gherkin/prompts/gherkin_prompt.txt`, este metodo aun no lo lee. El comentario indica que en produccion deberia cargarse desde archivo.

El template contiene placeholders:

```text
{business_rules}
{preconditions}
{happy_paths}
{error_scenarios}
```

Estos se completan en `get_prompt_for_llm`.

---

## 15) Metodo `generate_from_analysis`

```python
def generate_from_analysis(self, analysis_result: dict[str, Any]) -> GeneratedFeature:
```

Genera una feature Gherkin desde un resultado de analisis.

En la version actual no llama a un LLM. Genera una estructura basica automaticamente.

### Parametro `analysis_result`

Diccionario con resultado de analisis.

Se espera que contenga:

- `issue_key`
- `scope_summary`
- `business_rules`
- `raw.error_scenarios`

### Log inicial

```python
log.info(f"Generating Gherkin for {analysis_result.get('issue_key')}")
```

Registra para que issue se esta generando Gherkin.

### Variable `issue_key`

```python
issue_key = analysis_result.get("issue_key", "UNKNOWN")
```

Clave de Jira origen.

Si no existe, usa:

```text
UNKNOWN
```

### Variable `scope`

```python
scope = analysis_result.get("scope_summary", "Feature")
```

Nombre funcional de la feature.

Si no existe, usa:

```text
Feature
```

### Variable `business_rules`

```python
business_rules = analysis_result.get("business_rules", [])
```

Lista de reglas de negocio detectadas.

Se usa para decidir si agrega escenario de validacion.

### Variable `error_scenarios`

```python
error_scenarios = analysis_result.get("raw", {}).get("error_scenarios", [])
```

Obtiene escenarios de error desde el campo `raw`.

Usa `{}` como fallback si no existe `raw`.

### Construccion de `GherkinFeature`

```python
feature = GherkinFeature(
    feature_name=scope,
    description=f"Feature relacionada a {issue_key}",
    language="es",
    tags=["smoke", "regression"],
)
```

Crea una feature en espanol.

Tags globales:

- `smoke`
- `regression`

Descripcion:

```text
Feature relacionada a <issue_key>
```

### Background

```python
feature.set_background(
    given=[
        "que el sistema esta disponible",
        "que tengo credenciales validas",
    ]
)
```

Agrega antecedentes comunes.

En el archivo original aparecen acentos en `está` y `válidas`.

### Escenario happy path

```python
happy_scenario = GherkinScenario(...)
feature.add_scenario(happy_scenario)
```

Siempre se agrega un escenario de flujo exitoso.

Nombre:

```text
Flujo exitoso de la funcionalidad
```

Tag:

```text
@smoke
```

### Escenario de validacion

```python
if business_rules:
    validation_scenario = GherkinScenario(...)
    feature.add_scenario(validation_scenario)
```

Validacion:

Solo agrega este escenario si existen reglas de negocio.

Nombre:

```text
Validacion de entrada
```

Tag:

```text
@validation
```

### Escenario de error

```python
if error_scenarios:
    error_scenario = GherkinScenario(...)
    feature.add_scenario(error_scenario)
```

Validacion:

Solo agrega este escenario si existen escenarios de error en el analisis.

Nombre:

```text
Manejo de errores
```

Tag:

```text
@error-handling
```

### Variable `gherkin_text`

```python
gherkin_text = feature.to_gherkin()
```

Convierte la feature completa a texto Gherkin.

### Construccion de `GeneratedFeature`

```python
generated = GeneratedFeature(
    feature_name=scope,
    gherkin_text=gherkin_text,
    language="es",
    tags=["smoke", "regression"],
    scenarios_count=len(feature.scenarios),
    source_issue_key=issue_key,
)
```

Empaqueta el resultado en un modelo Pydantic.

Campos:

- `feature_name`: nombre de la feature.
- `gherkin_text`: texto final.
- `language`: `es`.
- `tags`: tags globales.
- `scenarios_count`: cantidad real de escenarios agregados.
- `source_issue_key`: Jira key origen.

### Log final

```python
log.info(f"Generated {len(feature.scenarios)} scenarios for {issue_key}")
```

Registra cuantos escenarios se generaron.

### Retorno

```python
return generated
```

Devuelve la feature generada.

---

## 16) Metodo `validate_gherkin`

```python
def validate_gherkin(self, gherkin_text: str) -> tuple[bool, list[str]]:
```

Valida sintaxis basica de Gherkin.

Retorna una tupla:

```python
(es_valido, lista_de_errores)
```

### Variable `errors`

```python
errors = []
```

Lista de errores detectados.

### Variables de estado

```python
lines = gherkin_text.split("\n")
in_feature = False
in_scenario = False
indent_level = 0
```

### `lines`

Lista de lineas del texto.

### `in_feature`

Indica si ya se encontro una feature.

### `in_scenario`

Indica si ya se entro a un escenario.

### `indent_level`

Variable definida pero no usada actualmente.

### Iteracion por lineas

```python
for line_num, line in enumerate(lines, start=1):
```

Recorre lineas con numero empezando en 1.

### Variable `stripped`

```python
stripped = line.strip()
```

Linea sin espacios al inicio y final.

### Ignorar vacias y comentarios

```python
if not stripped or stripped.startswith("#"):
    continue
```

Ignora:

- lineas vacias
- comentarios
- header `# language: es`

### Detectar Feature

```python
if stripped.startswith("Caracteristica:") or stripped.startswith("Feature:"):
    in_feature = True
    in_scenario = False
    continue
```

Detecta inicio de feature.

En el archivo original se usa `Característica:` con tilde.

Cuando detecta feature:

- `in_feature = True`
- `in_scenario = False`

### Detectar Scenario

```python
if stripped.startswith("Escenario:") or stripped.startswith("Scenario:"):
    if not in_feature:
        errors.append(f"Linea {line_num}: Escenario sin Feature")
    in_scenario = True
    continue
```

Detecta escenarios.

Validacion:

Si aparece un escenario antes de una feature, agrega error.

### Lista `valid_keywords`

```python
valid_keywords = [
    "Dado", "Given",
    "Cuando", "When",
    "Entonces", "Then",
    "Y", "And",
    "Pero", "But",
    "Antecedentes", "Background",
]
```

Palabras clave validas para pasos.

Incluye espanol e ingles.

### Validar pasos dentro de escenario

```python
if in_scenario and stripped and not any(stripped.startswith(kw) for kw in valid_keywords):
    errors.append(f"Linea {line_num}: Paso sin palabra clave valida")
```

Si ya estamos dentro de un escenario, cualquier linea no vacia debe empezar con una palabra clave valida.

Si no empieza con ninguna, se agrega error.

### Validar que exista Feature

```python
if not in_feature:
    errors.append("No se encontro definicion de Feature")
```

Si al final nunca se encontro una feature, agrega error.

### Retorno

```python
return (len(errors) == 0, errors)
```

Si no hay errores:

```python
True
```

Si hay errores:

```python
False
```

---

## 17) Metodo `save_feature_file`

```python
def save_feature_file(
    self,
    generated_feature: GeneratedFeature,
    output_dir: str | None = None,
) -> str:
```

Guarda el texto Gherkin en un archivo `.feature`.

### Parametro `generated_feature`

Modelo `GeneratedFeature` que contiene:

- texto Gherkin
- issue key origen
- nombre de feature

### Parametro `output_dir`

Directorio opcional de salida.

Si no se entrega, usa `self.output_dir`.

### Resolver directorio

```python
output_dir = output_dir or self.output_dir
```

Si `output_dir` viene vacio o `None`, usa el directorio configurado en el servicio.

### Crear directorio

```python
os.makedirs(output_dir, exist_ok=True)
```

Crea el directorio si no existe.

`exist_ok=True` evita error si ya existe.

### Variable `filename`

```python
filename = f"{generated_feature.source_issue_key}.feature"
```

Nombre del archivo basado en la issue.

Ejemplo:

```text
DYF-123.feature
```

### Variable `filepath`

```python
filepath = os.path.join(output_dir, filename)
```

Ruta completa del archivo.

### Escritura del archivo

```python
with open(filepath, "w", encoding="utf-8") as f:
    f.write(generated_feature.gherkin_text)
```

Abre el archivo en modo escritura.

Usa UTF-8 para soportar acentos y caracteres de Gherkin en espanol.

Escribe el texto de la feature.

### Log y retorno

```python
log.info(f"Feature saved to {filepath}")
return filepath
```

Registra la ruta y la devuelve.

---

## 18) Metodo `get_prompt_for_llm`

```python
def get_prompt_for_llm(self, analysis_result: dict[str, Any]) -> str:
```

Construye el prompt que se enviaria a un LLM para generar Gherkin.

### Variable `business_rules`

```python
business_rules = "\n".join(f"- {rule}" for rule in analysis_result.get("business_rules", []))
```

Convierte reglas de negocio en lista Markdown.

Ejemplo:

```text
- Rule 1
- Rule 2
```

### Variable `preconditions`

```python
preconditions = analysis_result.get("raw", {}).get("preconditions", [])
```

Obtiene precondiciones desde `raw`.

### Variable `precond_text`

```python
precond_text = "\n".join(f"- {p.get('precondition', '')}" for p in preconditions)
```

Convierte precondiciones en texto con bullets.

### Variable `happy_paths`

```python
happy_paths = analysis_result.get("raw", {}).get("happy_paths", [])
```

Obtiene caminos felices desde `raw`.

### Variable `happy_text`

```python
happy_text = "\n".join(f"- {h.get('name', '')}" for h in happy_paths)
```

Convierte nombres de happy paths en bullets.

### Variable `error_scenarios`

```python
error_scenarios = analysis_result.get("raw", {}).get("error_scenarios", [])
```

Obtiene escenarios de error.

### Variable `error_text`

```python
error_text = "\n".join(f"- {e.get('description', '')}" for e in error_scenarios)
```

Convierte descripciones de error en bullets.

### Render final del template

```python
return self.prompt_template.format(
    business_rules=business_rules or "N/A",
    preconditions=precond_text or "N/A",
    happy_paths=happy_text or "N/A",
    error_scenarios=error_text or "N/A",
)
```

Reemplaza los placeholders del prompt.

Validacion/default:

Si una seccion queda vacia, usa:

```text
N/A
```

---

## 19) Relacion con gherkin_prompt.txt

Existe el archivo:

```text
src/ai_qa_gherkin/prompts/gherkin_prompt.txt
```

Ese archivo contiene instrucciones versionadas para generar escenarios Gherkin:

- objetivo
- formato obligatorio
- reglas de calidad
- salida esperada

Actualmente `GherkinService._load_prompt_template()` no lee ese archivo. Usa un prompt hardcoded.

Esto significa que modificar `gherkin_prompt.txt` no cambia el prompt usado por el servicio en la version actual.

---

## 20) Relacion con feature.template.j2

Existe el template:

```text
templates/feature.template.j2
```

Ese archivo parece pensado para renderizar features con Jinja2.

Actualmente `gherkin_service.py` no usa Jinja2 ni carga ese template.

La feature se renderiza manualmente con concatenacion de strings en:

- `GherkinScenario.to_gherkin`
- `GherkinFeature.to_gherkin`

---

## 21) Validaciones principales

### Tags opcionales

```python
self.tags = tags or []
```

Evita que `tags` quede como `None`.

### Background opcional

```python
if any(self.background_steps.values()):
```

Solo renderiza antecedentes si hay pasos.

### Escenario de validacion condicional

```python
if business_rules:
```

Solo agrega escenario de validacion si existen reglas.

### Escenario de error condicional

```python
if error_scenarios:
```

Solo agrega escenario de error si el analisis detecto errores.

### Ignorar comentarios y lineas vacias

```python
if not stripped or stripped.startswith("#"):
    continue
```

Permite headers como `# language: es`.

### Feature obligatoria

```python
if not in_feature:
    errors.append("No se encontro definicion de Feature")
```

Un Gherkin sin feature se considera invalido.

### Escenario debe estar dentro de Feature

```python
if not in_feature:
    errors.append(...)
```

Evita escenarios sueltos.

### Pasos con palabra clave valida

```python
not any(stripped.startswith(kw) for kw in valid_keywords)
```

Detecta lineas dentro de escenario que no empiezan con palabra clave Gherkin.

---

## 22) Variables principales y significado

| Variable | Donde aparece | Significado |
| --- | --- | --- |
| `log` | modulo | Logger contextual del servicio. |
| `name` | `GherkinScenario` | Nombre del escenario. |
| `given` | `GherkinScenario`, background | Pasos de precondicion. |
| `when` | `GherkinScenario`, background | Pasos de accion. |
| `then` | `GherkinScenario`, background | Pasos de resultado esperado. |
| `tags` | escenario/feature | Tags Gherkin. |
| `language` | escenario/feature | Idioma del Gherkin. |
| `indent` | `to_gherkin` | Espacios de indentacion. |
| `spacing` | `GherkinScenario.to_gherkin` | String de espacios. |
| `result` | renderizadores | Texto acumulado. |
| `scenario_kw` | `GherkinScenario.to_gherkin` | Keyword `Escenario` o `Scenario`. |
| `given_kw` | `GherkinScenario.to_gherkin` | Keyword `Dado` o `Given`. |
| `when_kw` | `GherkinScenario.to_gherkin` | Keyword `Cuando` o `When`. |
| `then_kw` | `GherkinScenario.to_gherkin` | Keyword `Entonces` o `Then`. |
| `and_kw` | `GherkinScenario.to_gherkin` | Keyword `Y` o `And`. |
| `feature_name` | `GherkinFeature` | Nombre de la feature. |
| `description` | `GherkinFeature` | Descripcion funcional. |
| `scenarios` | `GherkinFeature` | Lista de escenarios. |
| `background_steps` | `GherkinFeature` | Pasos comunes de antecedentes. |
| `output_dir` | `GherkinService` | Carpeta donde se guardan `.feature`. |
| `prompt_template` | `GherkinService` | Template de prompt para LLM. |
| `analysis_result` | generacion/prompt | Resultado del analisis funcional. |
| `issue_key` | `generate_from_analysis` | Issue Jira origen. |
| `scope` | `generate_from_analysis` | Nombre/alcance de la feature. |
| `business_rules` | generacion/prompt | Reglas de negocio. |
| `error_scenarios` | generacion/prompt | Escenarios de error extraidos. |
| `feature` | `generate_from_analysis` | Objeto `GherkinFeature`. |
| `gherkin_text` | generacion/validacion | Texto Gherkin final. |
| `generated` | `generate_from_analysis` | Modelo `GeneratedFeature`. |
| `errors` | `validate_gherkin` | Lista de errores de validacion. |
| `lines` | `validate_gherkin` | Lineas del Gherkin. |
| `in_feature` | `validate_gherkin` | Estado: ya existe Feature. |
| `in_scenario` | `validate_gherkin` | Estado: dentro de Scenario. |
| `stripped` | `validate_gherkin` | Linea limpia. |
| `valid_keywords` | `validate_gherkin` | Keywords aceptadas. |
| `filename` | `save_feature_file` | Nombre del archivo `.feature`. |
| `filepath` | `save_feature_file` | Ruta completa del archivo. |

---

## 23) Relacion con los tests

El archivo `tests/test_gherkin_service.py` cubre:

1. Creacion de `GherkinScenario`.
2. Render de escenario en ingles.
3. Creacion de `GherkinFeature`.
4. Agregado de escenarios.
5. Configuracion de background.
6. Render de feature en espanol.
7. Generacion desde analysis result.
8. Validacion de Gherkin valido.
9. Deteccion de Gherkin sin Feature.
10. Deteccion de pasos sin palabra clave.
11. Guardado de archivo `.feature`.
12. Construccion de prompt para LLM.

---

## 24) Puntos de mejora detectables

1. `re` esta importado pero no se usa.
2. `datetime` esta importado pero no se usa.
3. `_load_prompt_template()` no lee `src/ai_qa_gherkin/prompts/gherkin_prompt.txt`.
4. `feature.template.j2` existe, pero el servicio no lo usa.
5. `validate_gherkin` define `indent_level`, pero no lo usa.
6. `GherkinFeature.to_gherkin()` renderiza `Caracteristica`/`Antecedentes` en espanol incluso si `language` es `en`.
7. `validate_gherkin` es una validacion basica, no un parser Gherkin completo.
8. El nombre del archivo depende de `source_issue_key`; si viene vacio, podria crear `.feature`.

---

## 25) Resumen mental rapido

`gherkin_service.py` tiene tres piezas principales:

1. `GherkinScenario`: arma un escenario.
2. `GherkinFeature`: arma una feature completa.
3. `GherkinService`: genera, valida, guarda y prepara prompts.

El flujo principal es:

1. Recibir `analysis_result`.
2. Crear una `GherkinFeature`.
3. Agregar background.
4. Agregar happy path siempre.
5. Agregar validacion si hay reglas de negocio.
6. Agregar error si hay escenarios de error.
7. Convertir todo a texto Gherkin.
8. Devolver un `GeneratedFeature`.

La idea central es convertir analisis funcional en una feature Cucumber/Xray lista para revisar, guardar o publicar.
