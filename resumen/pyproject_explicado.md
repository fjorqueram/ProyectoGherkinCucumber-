# Explicacion detallada de pyproject.toml

Este documento explica que hace `pyproject.toml`, seccion por seccion y variable por variable.

---

## 1) Objetivo del archivo

`pyproject.toml` es el archivo estandar moderno de configuracion para proyectos Python.

En este proyecto define:

1. Como se construye el paquete.
2. Metadata del proyecto.
3. Version minima de Python.
4. Dependencias de ejecucion.
5. Dependencias opcionales de desarrollo.
6. Configuracion de pytest.
7. Configuracion de Black.
8. Configuracion de Ruff.
9. Configuracion de mypy.
10. Configuracion de coverage.

---

## 2) Seccion `[build-system]`

```toml
[build-system]
requires = ["setuptools>=65", "wheel"]
build-backend = "setuptools.build_meta"
```

Esta seccion indica que herramientas se necesitan para construir el paquete.

### `requires`

```toml
requires = ["setuptools>=65", "wheel"]
```

Lista de paquetes necesarios para hacer build.

### `setuptools>=65`

Indica que se necesita `setuptools` version 65 o superior.

`setuptools` se encarga de empaquetar el proyecto.

### `wheel`

Permite construir distribuciones tipo wheel (`.whl`), que son el formato comun de paquetes Python instalables.

### `build-backend`

```toml
build-backend = "setuptools.build_meta"
```

Define el backend que usara Python para construir el paquete.

En este caso se usa el backend moderno de `setuptools`.

---

## 3) Seccion `[project]`

```toml
[project]
name = "ai-qa-gherkin"
version = "0.1.0"
description = "AI-powered Gherkin feature generation from Jira/Confluence"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
keywords = ["gherkin", "bdd", "jira", "xray", "cucumber", "ai"]
```

Esta seccion describe el proyecto como paquete Python.

### `name`

```toml
name = "ai-qa-gherkin"
```

Nombre del paquete.

Es el nombre con el que podria publicarse o instalarse.

### `version`

```toml
version = "0.1.0"
```

Version actual del proyecto.

Usa formato semantico comun:

```text
MAJOR.MINOR.PATCH
```

### `description`

```toml
description = "AI-powered Gherkin feature generation from Jira/Confluence"
```

Descripcion corta del objetivo del proyecto.

### `readme`

```toml
readme = "README.md"
```

Indica que el README principal del proyecto esta en `README.md`.

### `requires-python`

```toml
requires-python = ">=3.10"
```

Define la version minima de Python requerida.

Este proyecto requiere Python 3.10 o superior.

Esto es coherente con el uso de type hints modernos como:

```python
str | None
list[str]
dict[str, Any]
```

### `license`

```toml
license = {text = "MIT"}
```

Declara la licencia del proyecto.

En este caso:

```text
MIT
```

### `authors`

```toml
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
```

Lista de autores del paquete.

Actualmente usa valores placeholder:

- `Your Name`
- `your.email@example.com`

Si el proyecto se va a publicar o compartir formalmente, conviene reemplazarlos.

### `keywords`

```toml
keywords = ["gherkin", "bdd", "jira", "xray", "cucumber", "ai"]
```

Palabras clave que describen el proyecto.

Ayudan a categorizarlo:

- `gherkin`: lenguaje de especificacion BDD.
- `bdd`: Behavior Driven Development.
- `jira`: fuente de issues.
- `xray`: gestion de pruebas.
- `cucumber`: ejecucion/formato de pruebas BDD.
- `ai`: generacion o asistencia con inteligencia artificial.

---

## 4) Dependencias principales

```toml
dependencies = [
    "httpx>=0.24.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "loguru>=0.7.0",
    "tenacity>=8.2.0",
    "python-dotenv>=1.0.0",
]
```

Estas dependencias son necesarias para que la aplicacion funcione.

### `httpx>=0.24.0`

Cliente HTTP.

Se usa para consumir APIs como Jira, Confluence, Git y Xray.

### `pydantic>=2.0.0`

Libreria de modelos y validacion de datos.

Se usa en archivos como `domain.py`.

### `pydantic-settings>=2.0.0`

Extension de Pydantic para cargar configuracion desde variables de entorno y archivos `.env`.

Se usa en `config.py`.

### `loguru>=0.7.0`

Libreria de logging.

Se usa para registrar eventos de la aplicacion.

### `tenacity>=8.2.0`

Libreria para reintentos.

Se usa en `retry.py` con `retry_policy`.

### `python-dotenv>=1.0.0`

Permite cargar variables desde archivos `.env`.

Complementa la configuracion basada en entorno.

---

## 5) Seccion `[project.optional-dependencies]`

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.5.0",
    "pre-commit>=3.4.0",
]
```

Define dependencias opcionales.

El grupo:

```toml
dev = [...]
```

contiene herramientas utiles para desarrollo, testing, formateo y calidad.

### `pytest>=7.4.0`

Framework para ejecutar tests.

### `pytest-cov>=4.1.0`

Plugin de pytest para medir cobertura.

### `black>=23.0.0`

Formateador automatico de Python.

### `ruff>=0.1.0`

Linter rapido para Python.

Detecta errores de estilo, imports, advertencias y problemas comunes.

### `mypy>=1.5.0`

Analizador estatico de tipos.

Revisa type hints sin ejecutar el programa.

### `pre-commit>=3.4.0`

Herramienta para ejecutar validaciones antes de hacer commits.

---

## 6) Seccion `[tool.pytest.ini_options]`

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
addopts = "-v --tb=short --strict-markers"
markers = [
    "unit: unit tests",
    "integration: integration tests",
    "smoke: smoke tests",
]
```

Configura pytest.

### `pythonpath`

```toml
pythonpath = ["src"]
```

Agrega `src` al path de Python durante los tests.

Esto permite imports como:

```python
from ai_qa_gherkin.models import JiraIssue
```

### `testpaths`

```toml
testpaths = ["tests"]
```

Indica que pytest debe buscar tests en la carpeta `tests`.

### `addopts`

```toml
addopts = "-v --tb=short --strict-markers"
```

Opciones por defecto al ejecutar pytest.

Partes:

- `-v`: modo verbose, muestra mas detalle.
- `--tb=short`: traceback corto cuando falla un test.
- `--strict-markers`: falla si se usa un marker no registrado.

### `markers`

```toml
markers = [
    "unit: unit tests",
    "integration: integration tests",
    "smoke: smoke tests",
]
```

Registra markers permitidos.

Markers definidos:

- `unit`: tests unitarios.
- `integration`: tests de integracion.
- `smoke`: tests smoke.

---

## 7) Seccion `[tool.black]`

```toml
[tool.black]
line-length = 100
target-version = ["py310", "py311", "py312"]
```

Configura Black.

### `line-length`

```toml
line-length = 100
```

Longitud maxima de linea preferida.

### `target-version`

```toml
target-version = ["py310", "py311", "py312"]
```

Versiones de Python objetivo para el formateo.

Black puede usar esta informacion para decidir que sintaxis es valida.

---

## 8) Seccion `[tool.ruff]`

```toml
[tool.ruff]
line-length = 100
target-version = "py310"
select = ["E", "F", "W", "I"]
exclude = [".git", ".venv", "__pycache__", "build", "dist"]
```

Configura Ruff.

### `line-length`

Longitud maxima de linea para lint.

### `target-version`

```toml
target-version = "py310"
```

Indica que el codigo apunta a Python 3.10.

### `select`

```toml
select = ["E", "F", "W", "I"]
```

Reglas activadas.

- `E`: errores de estilo tipo pycodestyle.
- `F`: errores tipo Pyflakes, como imports no usados.
- `W`: advertencias de estilo.
- `I`: ordenamiento de imports.

### `exclude`

```toml
exclude = [".git", ".venv", "__pycache__", "build", "dist"]
```

Carpetas excluidas del analisis.

Motivo:

- `.git`: metadata de Git.
- `.venv`: entorno virtual.
- `__pycache__`: cache Python.
- `build`: salida de build.
- `dist`: paquetes generados.

---

## 9) Seccion `[tool.mypy]`

```toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
ignore_missing_imports = true
```

Configura mypy.

### `python_version`

Version de Python usada para analizar tipos.

### `warn_return_any`

```toml
warn_return_any = true
```

Emite advertencia cuando una funcion retorna `Any`.

### `warn_unused_configs`

```toml
warn_unused_configs = true
```

Advierte si hay configuraciones de mypy que no se estan usando.

### `disallow_untyped_defs`

```toml
disallow_untyped_defs = false
```

Permite funciones sin anotaciones completas de tipos.

Es una configuracion flexible para proyectos en crecimiento.

### `ignore_missing_imports`

```toml
ignore_missing_imports = true
```

Ignora errores cuando una dependencia no tiene stubs de tipos disponibles.

Reduce ruido, pero tambien puede ocultar algunos problemas de tipado en librerias externas.

---

## 10) Seccion `[tool.coverage.run]`

```toml
[tool.coverage.run]
source = ["src/ai_qa_gherkin"]
omit = ["*/tests/*", "*/__pycache__/*"]
```

Configura que codigo se mide para cobertura.

### `source`

```toml
source = ["src/ai_qa_gherkin"]
```

Indica que la cobertura se calcula sobre el paquete principal.

### `omit`

```toml
omit = ["*/tests/*", "*/__pycache__/*"]
```

Excluye:

- archivos dentro de tests
- archivos de cache Python

---

## 11) Seccion `[tool.coverage.report]`

```toml
[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
```

Configura que lineas se excluyen del reporte de cobertura.

### `exclude_lines`

Lista de patrones que coverage debe ignorar.

### `"pragma: no cover"`

Permite marcar lineas manualmente para excluirlas.

### `"def __repr__"`

Excluye metodos de representacion.

### `"raise AssertionError"`

Excluye errores defensivos que normalmente no se testean directamente.

### `"raise NotImplementedError"`

Excluye metodos abstractos o pendientes de implementacion concreta.

### `"if __name__ == .__main__.:"`

Excluye bloques de ejecucion directa.

Nota:

El patron esta escrito con puntos:

```toml
"if __name__ == .__main__.:"
```

En expresiones regulares, `.` significa cualquier caracter. Por eso puede coincidir con comillas simples o dobles alrededor de `__main__`.

---

## 12) Validaciones y decisiones importantes

### Version minima de Python

```toml
requires-python = ">=3.10"
```

El proyecto declara Python 3.10 como minimo.

### Separacion entre dependencias normales y dev

Las dependencias de runtime estan en:

```toml
dependencies
```

Las herramientas de desarrollo estan en:

```toml
[project.optional-dependencies].dev
```

Esto evita instalar herramientas de desarrollo en ambientes productivos si no son necesarias.

### Configuracion centralizada

El mismo archivo concentra configuracion de:

- pytest
- black
- ruff
- mypy
- coverage

Esto reduce archivos sueltos y facilita mantenimiento.

---

## 13) Resumen mental rapido

`pyproject.toml` es el centro de configuracion del proyecto Python.

Define como se instala, que dependencias usa, que version de Python necesita y como se ejecutan herramientas de calidad.

Las secciones mas importantes son:

- `[build-system]`: como construir el paquete.
- `[project]`: metadata y dependencias.
- `[tool.pytest.ini_options]`: testing.
- `[tool.black]`: formato.
- `[tool.ruff]`: lint.
- `[tool.mypy]`: tipos.
- `[tool.coverage.*]`: cobertura.
